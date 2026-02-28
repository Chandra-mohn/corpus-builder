import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from corpus_builder.evaluate import (
    SccStats,
    compute_quality_score,
    detect_training_paths,
    evaluate_repo,
    run_scc,
)


class TestComputeQualityScore:
    def test_empty_repo_scores_zero(self):
        scc = SccStats()
        assert compute_quality_score(scc, training_flag=False) == 0

    def test_tiny_repo_gets_penalty(self):
        scc = SccStats(cobol_files=1, cobol_code_lines=50)
        score = compute_quality_score(scc, training_flag=False)
        assert score < 10

    def test_large_repo_scores_high(self):
        scc = SccStats(
            cobol_files=50,
            cobol_code_lines=10000,
            cobol_comment_lines=2000,
            cobol_complexity=80,
            jcl_files=5,
        )
        score = compute_quality_score(scc, training_flag=False)
        assert score >= 70

    def test_training_flag_reduces_score(self):
        scc = SccStats(
            cobol_files=20,
            cobol_code_lines=3000,
            cobol_comment_lines=500,
            cobol_complexity=10,
        )
        score_clean = compute_quality_score(scc, training_flag=False)
        score_training = compute_quality_score(scc, training_flag=True)
        assert score_training < score_clean
        assert score_clean - score_training == 20

    def test_jcl_presence_adds_points(self):
        scc_no_jcl = SccStats(cobol_files=10, cobol_code_lines=2000)
        scc_with_jcl = SccStats(cobol_files=10, cobol_code_lines=2000, jcl_files=3)
        score_no = compute_quality_score(scc_no_jcl, training_flag=False)
        score_yes = compute_quality_score(scc_with_jcl, training_flag=False)
        assert score_yes - score_no == 10

    def test_score_clamped_to_0_100(self):
        # Even with maximum penalties, score should not go below 0
        scc = SccStats(cobol_files=0, cobol_code_lines=0)
        score = compute_quality_score(scc, training_flag=True)
        assert score == 0

    def test_comment_ratio_sweet_spot(self):
        # 20% comment ratio should get full 10 points
        scc_good = SccStats(
            cobol_files=10, cobol_code_lines=1000, cobol_comment_lines=250,
        )
        # 1% comment ratio should get only 2 points
        scc_low = SccStats(
            cobol_files=10, cobol_code_lines=1000, cobol_comment_lines=10,
        )
        score_good = compute_quality_score(scc_good, training_flag=False)
        score_low = compute_quality_score(scc_low, training_flag=False)
        assert score_good > score_low


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
                stats = run_scc(Path("/fake/repo"))

        assert stats.cobol_files == 5
        assert stats.cobol_code_lines == 1000
        assert stats.cobol_comment_lines == 200
        assert stats.cobol_blank_lines == 50
        assert stats.cobol_complexity == 12
        assert stats.jcl_files == 2

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
                stats = run_scc(Path("/fake/repo"))

        assert stats.cobol_files == 0
        assert stats.cobol_code_lines == 0


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
