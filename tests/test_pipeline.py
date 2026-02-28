"""Integration test: end-to-end pipeline with a real git repo."""
import subprocess
import tempfile
from pathlib import Path

import pytest

from corpus_builder.config import Config
from corpus_builder.orchestrator import CorpusOrchestrator


def _create_test_repo(repo_dir: Path) -> str:
    """Create a tiny git repo with COBOL files and return the path."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", str(repo_dir)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo_dir), "config", "user.email", "test@test.com"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_dir), "config", "user.name", "Test"],
        check=True, capture_output=True,
    )

    # COBOL file with SQL dialect in a subdirectory
    src_dir = repo_dir / "src"
    src_dir.mkdir()
    cobol_file = src_dir / "PAYROLL.CBL"
    cobol_file.write_text(
        "000100 IDENTIFICATION DIVISION.\n"
        "000200 PROGRAM-ID. PAYROLL.\n"
        "000300 PROCEDURE DIVISION.\n"
        "000400     EXEC SQL\n"
        "000500         SELECT SALARY INTO :WS-SAL\n"
        "000600     END-EXEC.\n"
        "000700     STOP RUN.\n"
    )

    # Non-COBOL file (should be ignored)
    (repo_dir / "README.md").write_text("# Test repo")

    # Another COBOL file at root
    batch_file = repo_dir / "BATCH.COB"
    batch_file.write_text(
        "000100 IDENTIFICATION DIVISION.\n"
        "000200 PROGRAM-ID. BATCH.\n"
        "000300 PROCEDURE DIVISION.\n"
        "000400     DISPLAY 'HELLO'.\n"
        "000500     STOP RUN.\n"
    )

    subprocess.run(
        ["git", "-C", str(repo_dir), "add", "."], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(repo_dir), "commit", "-m", "init"],
        check=True, capture_output=True,
    )
    return str(repo_dir)


class TestPipeline:
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            test_repo = td / "test_repo"
            corpus_dir = td / "corpus_output"

            clone_url = _create_test_repo(test_repo)

            cfg = Config(output_dir=str(corpus_dir))
            orchestrator = CorpusOrchestrator(corpus_dir, cfg)

            repo_meta = {
                "id": "github/testorg/test-cobol",
                "clone_url": clone_url,
                "source": "github",
                "vcs": "git",
            }

            orchestrator.register_repo(repo_meta)
            orchestrator.process_repo(repo_meta)
            orchestrator.finish()

            # Verify repo marked done
            assert orchestrator.state.get_repo_status("github/testorg/test-cobol") == "done"

            # Verify files extracted
            stats = orchestrator.state.get_stats()
            assert stats["files_unique"] == 2
            assert stats["repos_done"] == 1

            # Verify files stored in original directory structure
            repo_out = corpus_dir / "repos" / "github" / "testorg" / "test-cobol"
            assert (repo_out / "src" / "PAYROLL.CBL").exists()
            assert (repo_out / "BATCH.COB").exists()
            assert not (repo_out / "README.md").exists()  # non-COBOL filtered out

            # Verify provenance entries
            assert stats["file_provenance_entries"] == 2

            # Verify parquet files exist after flush
            for table in ("runs", "repos", "files", "file_provenance"):
                assert (corpus_dir / "data" / f"{table}.parquet").exists()

            orchestrator.close()

    def test_dedup_tracked_in_db(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            corpus_dir = td / "corpus_output"

            # Create two repos with the same COBOL content
            for i in range(2):
                repo_dir = td / f"repo{i}"
                _create_test_repo(repo_dir)

            cfg = Config(output_dir=str(corpus_dir))
            orchestrator = CorpusOrchestrator(corpus_dir, cfg)

            for i in range(2):
                repo_meta = {
                    "id": f"github/testorg/repo{i}",
                    "clone_url": str(td / f"repo{i}"),
                    "source": "github",
                    "vcs": "git",
                }
                orchestrator.register_repo(repo_meta)
                orchestrator.process_repo(repo_meta)

            orchestrator.finish()
            stats = orchestrator.state.get_stats()

            # Same content -> only 2 unique file hashes in DB
            assert stats["files_unique"] == 2
            # But 4 provenance entries (2 files x 2 repos)
            assert stats["file_provenance_entries"] == 4
            assert stats["repos_done"] == 2

            # Both repos have their own copy on disk
            for i in range(2):
                repo_out = corpus_dir / "repos" / "github" / "testorg" / f"repo{i}"
                assert (repo_out / "src" / "PAYROLL.CBL").exists()
                assert (repo_out / "BATCH.COB").exists()

            orchestrator.close()

    def test_resume_skips_done_repo(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            corpus_dir = td / "corpus_output"
            repo_dir = td / "test_repo"
            _create_test_repo(repo_dir)

            cfg = Config(output_dir=str(corpus_dir))
            orchestrator = CorpusOrchestrator(corpus_dir, cfg)

            repo_meta = {
                "id": "github/testorg/myrepo",
                "clone_url": str(repo_dir),
                "source": "github",
                "vcs": "git",
            }

            orchestrator.register_repo(repo_meta)
            orchestrator.process_repo(repo_meta)
            orchestrator.finish()
            orchestrator.close()

            # Start a new orchestrator (simulates restart)
            orchestrator2 = CorpusOrchestrator(corpus_dir, cfg)
            orchestrator2.process_repo(repo_meta)
            # Should skip since already done
            assert orchestrator2._repos_processed == 0
            orchestrator2.close()

    def test_failed_repo_does_not_crash_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            corpus_dir = td / "corpus_output"

            cfg = Config(output_dir=str(corpus_dir))
            orchestrator = CorpusOrchestrator(corpus_dir, cfg)

            bad_repo = {
                "id": "github/nonexistent/repo",
                "clone_url": "https://nonexistent.invalid/repo.git",
                "source": "github",
                "vcs": "git",
            }

            orchestrator.register_repo(bad_repo)
            orchestrator.process_repo(bad_repo)

            assert orchestrator.state.get_repo_status("github/nonexistent/repo") == "failed"
            assert orchestrator._repos_failed == 1

            orchestrator.close()

    def test_false_positives_filtered(self):
        """Binary .cbl and JSON .cpy are rejected; only real COBOL is extracted."""
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo_dir = td / "mixed_repo"
            corpus_dir = td / "corpus_output"

            # Create a git repo with mixed content
            repo_dir.mkdir(parents=True)
            subprocess.run(["git", "init", str(repo_dir)], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(repo_dir), "config", "user.email", "t@t.com"],
                check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(repo_dir), "config", "user.name", "T"],
                check=True, capture_output=True,
            )

            # Real COBOL file
            real_cobol = repo_dir / "PAYROLL.CBL"
            real_cobol.write_text(
                "000100 IDENTIFICATION DIVISION.\n"
                "000200 PROGRAM-ID. PAYROLL.\n"
                "000300 PROCEDURE DIVISION.\n"
                "000400     STOP RUN.\n"
            )

            # Binary file with COBOL extension (tar header with null bytes)
            binary_cbl = repo_dir / "archive.cbl"
            binary_cbl.write_bytes(b"PK\x03\x04\x00\x00\x00some binary data\x00\x00")

            # JSON file with COBOL extension
            json_cpy = repo_dir / "data.cpy"
            json_cpy.write_text('{"employees": [{"name": "Alice"}]}')

            # Multi-extension file
            multi_ext = repo_dir / "config.json.cpy"
            multi_ext.write_text('{"setting": true}')

            subprocess.run(
                ["git", "-C", str(repo_dir), "add", "."], check=True, capture_output=True
            )
            subprocess.run(
                ["git", "-C", str(repo_dir), "commit", "-m", "init"],
                check=True, capture_output=True,
            )

            cfg = Config(output_dir=str(corpus_dir))
            orchestrator = CorpusOrchestrator(corpus_dir, cfg)

            repo_meta = {
                "id": "github/testorg/mixed",
                "clone_url": str(repo_dir),
                "source": "github",
                "vcs": "git",
            }
            orchestrator.register_repo(repo_meta)
            orchestrator.process_repo(repo_meta)
            orchestrator.finish()

            stats = orchestrator.state.get_stats()
            # Only the real COBOL file should be extracted
            assert stats["files_unique"] == 1
            assert stats["file_provenance_entries"] == 1

            repo_out = corpus_dir / "repos" / "github" / "testorg" / "mixed"
            assert (repo_out / "PAYROLL.CBL").exists()
            assert not (repo_out / "archive.cbl").exists()
            assert not (repo_out / "data.cpy").exists()
            assert not (repo_out / "config.json.cpy").exists()

            orchestrator.close()

    def test_empty_repo_no_cobol_files(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo_dir = td / "empty_repo"
            corpus_dir = td / "corpus_output"

            # Create repo with no COBOL files
            repo_dir.mkdir(parents=True)
            subprocess.run(["git", "init", str(repo_dir)], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(repo_dir), "config", "user.email", "t@t.com"],
                check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(repo_dir), "config", "user.name", "T"],
                check=True, capture_output=True,
            )
            (repo_dir / "README.md").write_text("no cobol here")
            subprocess.run(
                ["git", "-C", str(repo_dir), "add", "."], check=True, capture_output=True
            )
            subprocess.run(
                ["git", "-C", str(repo_dir), "commit", "-m", "init"],
                check=True, capture_output=True,
            )

            cfg = Config(output_dir=str(corpus_dir))
            orchestrator = CorpusOrchestrator(corpus_dir, cfg)

            repo_meta = {
                "id": "github/testorg/empty",
                "clone_url": str(repo_dir),
                "source": "github",
                "vcs": "git",
            }
            orchestrator.register_repo(repo_meta)
            orchestrator.process_repo(repo_meta)

            assert orchestrator.state.get_repo_status("github/testorg/empty") == "done"
            stats = orchestrator.state.get_stats()
            assert stats["files_unique"] == 0

            orchestrator.close()
