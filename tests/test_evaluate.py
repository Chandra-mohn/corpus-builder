import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from corpus_builder.evaluate import (
    RepoMetadata,
    SccStats,
    analyze_structural_depth,
    compute_quality_score,
    count_distinct_dialects,
    count_ecosystem_files,
    detect_anti_patterns,
    detect_training_paths,
    evaluate_repo,
    run_scc,
    score_github_signals,
)


class TestComputeQualityScore:
    def test_empty_repo_scores_zero(self, tmp_path):
        scc = SccStats()
        assert compute_quality_score(scc, training_flag=False, repo_path=tmp_path, scc_languages=[]) == 0

    def test_tiny_repo_gets_penalty(self, tmp_path):
        scc = SccStats(cobol_files=1, cobol_code_lines=50)
        score = compute_quality_score(scc, training_flag=False, repo_path=tmp_path, scc_languages=[])
        assert score < 10

    def test_large_repo_scores_high(self, tmp_path):
        # Create COBOL files with structural content for the new signals
        src = tmp_path / "src"
        src.mkdir()
        for i in range(5):
            f = src / ("PROG%d.cbl" % i)
            f.write_text(
                "       IDENTIFICATION DIVISION.\n"
                "       PROGRAM-ID. PROG%d.\n"
                "       PROCEDURE DIVISION.\n"
                "           PERFORM PARA-A\n"
                "           CALL 'SUBPROG'\n"
                "           COPY COPYBOOK\n"
                "           EXEC SQL SELECT 1 END-EXEC\n"
                "           EXEC CICS SEND END-EXEC\n"
                "           STOP RUN.\n" % i
            )

        scc = SccStats(
            cobol_files=50,
            cobol_code_lines=10000,
            cobol_comment_lines=2000,
            cobol_complexity=80,
            jcl_files=5,
        )
        score = compute_quality_score(scc, training_flag=False, repo_path=tmp_path, scc_languages=[])
        assert score >= 60

    def test_training_flag_reduces_score(self, tmp_path):
        scc = SccStats(
            cobol_files=20,
            cobol_code_lines=3000,
            cobol_comment_lines=500,
            cobol_complexity=10,
        )
        score_clean = compute_quality_score(scc, training_flag=False, repo_path=tmp_path, scc_languages=[])
        score_training = compute_quality_score(scc, training_flag=True, repo_path=tmp_path, scc_languages=[])
        assert score_training < score_clean
        assert score_clean - score_training == 20

    def test_jcl_presence_adds_points(self, tmp_path):
        scc_no_jcl = SccStats(cobol_files=10, cobol_code_lines=2000)
        scc_with_jcl = SccStats(cobol_files=10, cobol_code_lines=2000, jcl_files=3)
        score_no = compute_quality_score(scc_no_jcl, training_flag=False, repo_path=tmp_path, scc_languages=[])
        score_yes = compute_quality_score(scc_with_jcl, training_flag=False, repo_path=tmp_path, scc_languages=[])
        assert score_yes - score_no == 5

    def test_score_clamped_to_0_100(self, tmp_path):
        scc = SccStats(cobol_files=0, cobol_code_lines=0)
        score = compute_quality_score(scc, training_flag=True, repo_path=tmp_path, scc_languages=[])
        assert score == 0

    def test_comment_ratio_sweet_spot(self, tmp_path):
        # 20% comment ratio should get full 5 points
        scc_good = SccStats(
            cobol_files=10, cobol_code_lines=1000, cobol_comment_lines=250,
        )
        # 1% comment ratio should get only 1 point
        scc_low = SccStats(
            cobol_files=10, cobol_code_lines=1000, cobol_comment_lines=10,
        )
        score_good = compute_quality_score(scc_good, training_flag=False, repo_path=tmp_path, scc_languages=[])
        score_low = compute_quality_score(scc_low, training_flag=False, repo_path=tmp_path, scc_languages=[])
        assert score_good > score_low

    def test_fork_penalty(self, tmp_path):
        scc = SccStats(cobol_files=10, cobol_code_lines=2000, cobol_complexity=10)
        meta_normal = RepoMetadata(stars=5, repo_name="github/org/repo")
        meta_fork = RepoMetadata(stars=5, is_fork=True, repo_name="github/org/repo")
        score_normal = compute_quality_score(
            scc, False, tmp_path, [], metadata=meta_normal,
        )
        score_fork = compute_quality_score(
            scc, False, tmp_path, [], metadata=meta_fork,
        )
        assert score_normal - score_fork == 15

    def test_anti_pattern_penalty(self, tmp_path):
        scc = SccStats(cobol_files=10, cobol_code_lines=2000, cobol_complexity=10)
        meta = RepoMetadata(stars=0, repo_name="github/user/hello-world")
        score = compute_quality_score(
            scc, False, tmp_path, [], metadata=meta,
        )
        meta_good = RepoMetadata(stars=0, repo_name="github/corp/enterprise-payroll")
        score_good = compute_quality_score(
            scc, False, tmp_path, [], metadata=meta_good,
        )
        assert score < score_good

    def test_single_trivial_file_penalty(self, tmp_path):
        scc = SccStats(cobol_files=1, cobol_code_lines=30)
        score = compute_quality_score(scc, False, tmp_path, [])
        # Should get both tiny repo (-10) and single trivial (-10) penalties
        assert score == 0


class TestDetectTrainingPaths:
    def test_no_training_paths(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src" / "PAYROLL.cbl").touch()
            (repo / "src" / "ACCTRECV.cbl").touch()
            assert detect_training_paths(repo, ["training", "tutorial"]) is False

    def test_training_paths_detected(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "training").mkdir()
            (repo / "training" / "hello.cbl").touch()
            (repo / "training" / "exercise1.cbl").touch()
            (repo / "training" / "exercise2.cbl").touch()
            assert detect_training_paths(repo, ["training", "exercise"]) is True

    def test_mixed_paths_below_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src" / "PAYROLL.cbl").touch()
            (repo / "src" / "ACCTRECV.cbl").touch()
            (repo / "src" / "BILLING.cbl").touch()
            (repo / "tutorial").mkdir()
            (repo / "tutorial" / "hello.cbl").touch()
            # 1 out of 4 = 25%, below 50% threshold
            assert detect_training_paths(repo, ["tutorial"]) is False

    def test_empty_keywords_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "training").mkdir()
            (repo / "training" / "hello.cbl").touch()
            assert detect_training_paths(repo, []) is False

    def test_empty_repo_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            assert detect_training_paths(Path(td), ["training"]) is False


class TestRunScc:
    def test_parses_scc_json_output(self):
        scc_output = json.dumps([
            {
                "Name": "COBOL",
                "Count": 5,
                "Code": 1000,
                "Comment": 200,
                "Blank": 50,
                "Complexity": 12,
            },
            {
                "Name": "JCL",
                "Count": 2,
                "Code": 100,
                "Comment": 10,
                "Blank": 5,
                "Complexity": 0,
            },
        ])

        with patch("corpus_builder.evaluate.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = scc_output
            mock_run.return_value.stderr = ""

            with patch("corpus_builder.evaluate.shutil.which", return_value="/usr/bin/scc"):
                stats, languages = run_scc(Path("/fake/repo"))

        assert stats.cobol_files == 5
        assert stats.cobol_code_lines == 1000
        assert stats.cobol_comment_lines == 200
        assert stats.cobol_blank_lines == 50
        assert stats.cobol_complexity == 12
        assert stats.jcl_files == 2
        assert len(languages) == 2

    def test_handles_scc_not_found(self):
        with patch("corpus_builder.evaluate.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="scc is not installed"):
                run_scc(Path("/fake/repo"))

    def test_handles_empty_output(self):
        with patch("corpus_builder.evaluate.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""

            with patch("corpus_builder.evaluate.shutil.which", return_value="/usr/bin/scc"):
                stats, languages = run_scc(Path("/fake/repo"))

        assert stats.cobol_files == 0
        assert stats.cobol_code_lines == 0
        assert languages == []

    def test_handles_timeout(self):
        import subprocess as sp

        with patch("corpus_builder.evaluate.subprocess.run", side_effect=sp.TimeoutExpired("scc", 120)):
            with patch("corpus_builder.evaluate.shutil.which", return_value="/usr/bin/scc"):
                stats, languages = run_scc(Path("/fake/repo"))

        assert stats.cobol_files == 0
        assert languages == []

    def test_handles_nonzero_return(self):
        with patch("corpus_builder.evaluate.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "error"

            with patch("corpus_builder.evaluate.shutil.which", return_value="/usr/bin/scc"):
                stats, languages = run_scc(Path("/fake/repo"))

        assert stats.cobol_files == 0
        assert languages == []


class TestEvaluateRepo:
    def test_full_evaluation(self):
        scc_output = json.dumps([
            {"Name": "COBOL", "Count": 10, "Code": 2000, "Comment": 400,
             "Blank": 100, "Complexity": 15},
        ])

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src" / "PAYROLL.cbl").touch()

            with patch("corpus_builder.evaluate.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = scc_output
                mock_run.return_value.stderr = ""

                with patch("corpus_builder.evaluate.shutil.which", return_value="/usr/bin/scc"):
                    ev = evaluate_repo(repo, "github/test/repo", ["training", "tutorial"])

            assert ev.repo_id == "github/test/repo"
            assert ev.quality_score > 0
            assert ev.training_flag is False
            assert ev.scc.cobol_files == 10

    def test_evaluation_with_metadata(self):
        scc_output = json.dumps([
            {"Name": "COBOL", "Count": 10, "Code": 2000, "Comment": 400,
             "Blank": 100, "Complexity": 15},
        ])

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src" / "PAYROLL.cbl").touch()

            meta = RepoMetadata(stars=50, description="enterprise mainframe system")

            with patch("corpus_builder.evaluate.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = scc_output
                mock_run.return_value.stderr = ""

                with patch("corpus_builder.evaluate.shutil.which", return_value="/usr/bin/scc"):
                    ev = evaluate_repo(
                        repo, "github/corp/payroll", ["training"],
                        metadata=meta,
                    )

            assert ev.quality_score > 0
            assert meta.repo_name == "github/corp/payroll"


class TestCountDistinctDialects:
    def test_empty_repo(self, tmp_path):
        assert count_distinct_dialects(tmp_path) == 0

    def test_repo_with_cics_and_sql(self, tmp_path):
        f = tmp_path / "PROG.cbl"
        f.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. PROG.\n"
            "       EXEC CICS SEND END-EXEC\n"
            "       EXEC SQL SELECT 1 END-EXEC\n"
        )
        assert count_distinct_dialects(tmp_path) == 2

    def test_multiple_files_same_dialect(self, tmp_path):
        for name in ("A.cbl", "B.cbl"):
            f = tmp_path / name
            f.write_text("       EXEC SQL SELECT 1 END-EXEC\n")
        assert count_distinct_dialects(tmp_path) == 1

    def test_non_cobol_files_ignored(self, tmp_path):
        (tmp_path / "readme.txt").write_text("EXEC CICS this is not COBOL")
        assert count_distinct_dialects(tmp_path) == 0


class TestAnalyzeStructuralDepth:
    def test_empty_repo(self, tmp_path):
        assert analyze_structural_depth(tmp_path) == 0

    def test_perform_only(self, tmp_path):
        f = tmp_path / "PROG.cbl"
        f.write_text("       PERFORM PARA-A.\n       PERFORM PARA-B.\n")
        # has_perform = True -> 4 pts; avg 2 stmts/file -> +0.5; total 4.5 -> rounds to 4 or 5
        result = analyze_structural_depth(tmp_path)
        assert result >= 4

    def test_all_three_present(self, tmp_path):
        f = tmp_path / "PROG.cbl"
        lines = []
        for i in range(5):
            lines.append("       PERFORM PARA-%d." % i)
            lines.append("       CALL 'SUB%d'" % i)
            lines.append("       COPY BOOK%d." % i)
        f.write_text("\n".join(lines))
        result = analyze_structural_depth(tmp_path)
        assert result == 10  # 4+3+3 = 10, plus frequency bonus but capped at 10

    def test_non_cobol_files_ignored(self, tmp_path):
        (tmp_path / "script.py").write_text("PERFORM CALL COPY")
        assert analyze_structural_depth(tmp_path) == 0


class TestCountEcosystemFiles:
    def test_no_extras(self, tmp_path):
        assert count_ecosystem_files(tmp_path, []) == 0

    def test_with_bms_and_sql(self, tmp_path):
        (tmp_path / "screen.bms").touch()
        (tmp_path / "schema.sql").touch()
        (tmp_path / "another.ddl").touch()
        score = count_ecosystem_files(tmp_path, [])
        assert score > 0

    def test_scc_assembly_counted(self, tmp_path):
        languages = [{"Name": "Assembly", "Count": 8}]
        score = count_ecosystem_files(tmp_path, languages)
        assert score > 0

    def test_high_count_maxes_out(self, tmp_path):
        for i in range(15):
            (tmp_path / ("file%d.sql" % i)).touch()
        score = count_ecosystem_files(tmp_path, [])
        assert score == 10


class TestDetectAntiPatterns:
    def test_hello_world(self):
        assert detect_anti_patterns("github/user/hello-world") is True

    def test_demo_repo(self):
        assert detect_anti_patterns("github/user/cobol-demo") is True

    def test_enterprise_payroll(self):
        assert detect_anti_patterns("github/corp/enterprise-payroll") is False

    def test_custom_keywords(self):
        assert detect_anti_patterns("github/user/test-repo", keywords=["test"]) is True
        assert detect_anti_patterns("github/user/prod-app", keywords=["test"]) is False

    def test_case_insensitive(self):
        assert detect_anti_patterns("github/user/HELLO-COBOL") is True


class TestScoreGithubSignals:
    def test_none_metadata(self):
        assert score_github_signals(None) == 0

    def test_high_stars(self):
        meta = RepoMetadata(stars=200, description="")
        score = score_github_signals(meta)
        assert score == 5  # max stars points

    def test_enterprise_keywords(self):
        meta = RepoMetadata(stars=0, description="enterprise mainframe CICS banking system")
        score = score_github_signals(meta)
        assert score >= 4  # 4 keywords matched

    def test_combined_stars_and_keywords(self):
        meta = RepoMetadata(stars=50, description="legacy mainframe batch processing")
        score = score_github_signals(meta)
        assert score > 0

    def test_zero_stars_no_description(self):
        meta = RepoMetadata(stars=0, description="")
        assert score_github_signals(meta) == 0


class TestResetCommand:
    def test_flag_validation(self):
        """Exactly one of --all, --state-only, --repos-only must be set."""
        from typer.testing import CliRunner
        from corpus_builder.cli import app

        runner = CliRunner()
        # No flags -> error
        result = runner.invoke(app, ["reset", "-c", "corpus_builder.toml"])
        assert result.exit_code != 0

    def test_state_only_removes_data_dir(self, tmp_path):
        from typer.testing import CliRunner
        from corpus_builder.cli import app

        # Create a minimal config
        config = tmp_path / "test.toml"
        config.write_text(
            '[corpus]\noutput_dir = "%s/corpus"\n[logging]\nlevel = "INFO"\n'
            "[sources]\n[evaluate]\n" % str(tmp_path).replace("\\", "/")
        )

        corpus = tmp_path / "corpus"
        data_dir = corpus / "data"
        repos_dir = corpus / "repos"
        data_dir.mkdir(parents=True)
        repos_dir.mkdir(parents=True)
        (data_dir / "test.parquet").touch()
        (repos_dir / "test.txt").touch()

        runner = CliRunner()
        result = runner.invoke(app, ["reset", "-c", str(config), "--state-only", "--force"])
        assert result.exit_code == 0
        assert not data_dir.exists()
        assert repos_dir.exists()  # repos should be untouched

    def test_repos_only_removes_repo_dirs(self, tmp_path):
        from typer.testing import CliRunner
        from corpus_builder.cli import app

        config = tmp_path / "test.toml"
        config.write_text(
            '[corpus]\noutput_dir = "%s/corpus"\n[logging]\nlevel = "INFO"\n'
            "[sources]\n[evaluate]\n" % str(tmp_path).replace("\\", "/")
        )

        corpus = tmp_path / "corpus"
        data_dir = corpus / "data"
        repos_dir = corpus / "repos"
        mirrors_dir = corpus / "mirrors"
        data_dir.mkdir(parents=True)
        repos_dir.mkdir(parents=True)
        mirrors_dir.mkdir(parents=True)

        runner = CliRunner()
        result = runner.invoke(app, ["reset", "-c", str(config), "--repos-only", "--force"])
        assert result.exit_code == 0
        assert data_dir.exists()  # data should be untouched
        assert not repos_dir.exists()
        assert not mirrors_dir.exists()

    def test_all_removes_everything(self, tmp_path):
        from typer.testing import CliRunner
        from corpus_builder.cli import app

        config = tmp_path / "test.toml"
        config.write_text(
            '[corpus]\noutput_dir = "%s/corpus"\n[logging]\nlevel = "INFO"\n'
            "[sources]\n[evaluate]\n" % str(tmp_path).replace("\\", "/")
        )

        corpus = tmp_path / "corpus"
        for name in ("data", "repos", "mirrors", "working"):
            (corpus / name).mkdir(parents=True)

        runner = CliRunner()
        result = runner.invoke(app, ["reset", "-c", str(config), "--all", "--force"])
        assert result.exit_code == 0
        for name in ("data", "repos", "mirrors", "working"):
            assert not (corpus / name).exists()
