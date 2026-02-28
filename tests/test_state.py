import tempfile
from pathlib import Path

import pytest

from corpus_builder.state import StateManager


@pytest.fixture
def state_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td) / "data"


@pytest.fixture
def state(state_dir):
    sm = StateManager(state_dir)
    yield sm
    sm.close()


class TestRuns:
    def test_create_run(self, state):
        state.create_run("run-1", '{"test": true}')
        row = state.con.execute("SELECT * FROM runs WHERE run_id = 'run-1'").fetchone()
        assert row is not None

    def test_finish_run(self, state):
        state.create_run("run-1", "{}")
        state.finish_run("run-1", 10, 2, 50)
        row = state.con.execute(
            "SELECT repos_processed, repos_failed, files_extracted FROM runs WHERE run_id = 'run-1'"
        ).fetchone()
        assert row == (10, 2, 50)


class TestRepos:
    def test_upsert_new_repo(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo(
            {"id": "gh_1", "clone_url": "https://x.git", "source": "github"}, "r1"
        )
        assert state.get_repo_status("gh_1") == "discovered"

    def test_upsert_existing_non_done_repo(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo(
            {"id": "gh_1", "clone_url": "https://x.git", "source": "github"}, "r1"
        )
        state.set_repo_status("gh_1", "failed", "timeout")
        # Re-upsert resets non-done repos to discovered
        state.upsert_repo(
            {"id": "gh_1", "clone_url": "https://x.git", "source": "github"}, "r1"
        )
        assert state.get_repo_status("gh_1") == "discovered"

    def test_upsert_preserves_done_status(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo(
            {"id": "gh_1", "clone_url": "https://x.git", "source": "github", "stars": 10}, "r1"
        )
        state.set_repo_status("gh_1", "done")
        # Re-upsert should preserve done status but update metadata
        state.upsert_repo(
            {"id": "gh_1", "clone_url": "https://x.git", "source": "github", "stars": 42}, "r1"
        )
        assert state.get_repo_status("gh_1") == "done"
        row = state.con.execute(
            "SELECT stars FROM repos WHERE repo_id = 'gh_1'"
        ).fetchone()
        assert row[0] == 42

    def test_upsert_with_none_run_id(self, state):
        state.upsert_repo(
            {"id": "gh_1", "clone_url": "https://x.git", "source": "github"}, run_id=None
        )
        assert state.get_repo_status("gh_1") == "discovered"
        row = state.con.execute(
            "SELECT last_run_id FROM repos WHERE repo_id = 'gh_1'"
        ).fetchone()
        assert row[0] is None

    def test_rich_metadata_stored(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo(
            {
                "id": "gh_1",
                "clone_url": "https://x.git",
                "source": "github",
                "license_spdx": "MIT",
                "stars": 42,
                "description": "Test repo",
                "default_branch": "main",
                "repo_size_kb": 1024,
            },
            "r1",
        )
        row = state.con.execute(
            "SELECT license_spdx, stars, description, repo_size_kb FROM repos WHERE repo_id = 'gh_1'"
        ).fetchone()
        assert row == ("MIT", 42, "Test repo", 1024)

    def test_metadata_preserved_on_update(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo(
            {"id": "gh_1", "clone_url": "u", "source": "gh", "stars": 10}, "r1"
        )
        state.upsert_repo({"id": "gh_1", "clone_url": "u", "source": "gh"}, "r1")
        row = state.con.execute(
            "SELECT stars FROM repos WHERE repo_id = 'gh_1'"
        ).fetchone()
        assert row[0] == 10

    def test_status_transitions(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo({"id": "x", "clone_url": "u", "source": "gh"}, "r1")
        for s in ("cloning", "cloned", "extracting", "done"):
            state.set_repo_status("x", s)
            assert state.get_repo_status("x") == s

    def test_failed_status(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo({"id": "x", "clone_url": "u", "source": "gh"}, "r1")
        state.set_repo_status("x", "failed", "timeout")
        assert state.get_repo_status("x") == "failed"
        failed = state.get_failed_repos()
        assert len(failed) == 1
        assert failed[0]["error_msg"] == "timeout"

    def test_incomplete_repos(self, state):
        state.create_run("r1", "{}")
        for i in range(3):
            state.upsert_repo({"id": f"r{i}", "clone_url": "u", "source": "gh"}, "r1")
        state.set_repo_status("r0", "done")
        incomplete = state.get_incomplete_repos()
        ids = [r["id"] for r in incomplete]
        assert "r0" not in ids
        assert "r1" in ids
        assert "r2" in ids

    def test_unknown_repo_status_is_none(self, state):
        assert state.get_repo_status("nonexistent") is None


class TestFiles:
    def test_add_and_check_file(self, state):
        state.add_file("abc123", "ab/abc123.cbl", 1000, 50, file_type="cbl", dialect_tags="SQL")
        assert state.file_exists("abc123")

    def test_nonexistent_file(self, state):
        assert not state.file_exists("nope")


class TestProvenance:
    def test_add_provenance(self, state):
        state.create_run("r1", "{}")
        state.add_file("abc", "ab/abc.cbl", 100, 10, file_type="cbl")
        state.upsert_repo({"id": "gh_1", "clone_url": "u", "source": "gh"}, "r1")
        state.add_provenance("abc", "gh_1", "r1", "src/PAY.CBL")
        row = state.con.execute(
            "SELECT original_path FROM file_provenance WHERE sha256 = 'abc'"
        ).fetchone()
        assert row[0] == "src/PAY.CBL"

    def test_add_provenance_skips_duplicates(self, state):
        state.create_run("r1", "{}")
        state.add_file("abc", "ab/abc.cbl", 100, 10, file_type="cbl")
        state.upsert_repo({"id": "gh_1", "clone_url": "u", "source": "gh"}, "r1")
        state.add_provenance("abc", "gh_1", "r1", "src/PAY.CBL")
        # Second insert with same (sha256, repo_id) should be skipped
        state.add_provenance("abc", "gh_1", "r1", "src/PAY.CBL")
        count = state.con.execute(
            "SELECT count(*) FROM file_provenance WHERE sha256 = 'abc' AND repo_id = 'gh_1'"
        ).fetchone()[0]
        assert count == 1

    def test_provenance_allows_different_repos(self, state):
        state.create_run("r1", "{}")
        state.add_file("abc", "ab/abc.cbl", 100, 10, file_type="cbl")
        state.upsert_repo({"id": "gh_1", "clone_url": "u", "source": "gh"}, "r1")
        state.upsert_repo({"id": "gh_2", "clone_url": "u2", "source": "gh"}, "r1")
        state.add_provenance("abc", "gh_1", "r1", "src/PAY.CBL")
        state.add_provenance("abc", "gh_2", "r1", "src/PAY.CBL")
        count = state.con.execute(
            "SELECT count(*) FROM file_provenance WHERE sha256 = 'abc'"
        ).fetchone()[0]
        assert count == 2


class TestPersistence:
    def test_flush_and_reload(self, state_dir):
        sm = StateManager(state_dir)
        sm.create_run("r1", "{}")
        sm.upsert_repo(
            {"id": "gh_1", "clone_url": "u", "source": "gh", "repo_size_kb": 512}, "r1"
        )
        sm.set_repo_status("gh_1", "done")
        sm.add_file("hash1", "ha/hash1.cbl", 500, 25, file_type="cbl", dialect_tags="CICS")
        sm.add_provenance("hash1", "gh_1", "r1", "src/X.CBL")
        sm.flush()
        sm.close()

        # Verify parquet files exist
        for table in ("runs", "repos", "files", "file_provenance"):
            assert (state_dir / f"{table}.parquet").exists()

        # Reload and verify data survived
        sm2 = StateManager(state_dir)
        assert sm2.get_repo_status("gh_1") == "done"
        assert sm2.file_exists("hash1")
        stats = sm2.get_stats()
        assert stats["repos_total"] == 1
        assert stats["files_unique"] == 1
        # Verify repo_size_kb round-trips
        row = sm2.con.execute(
            "SELECT repo_size_kb FROM repos WHERE repo_id = 'gh_1'"
        ).fetchone()
        assert row[0] == 512
        sm2.close()


class TestStats:
    def test_stats(self, state):
        state.create_run("r1", "{}")
        for i in range(5):
            state.upsert_repo({"id": f"r{i}", "clone_url": "u", "source": "gh"}, "r1")
        state.set_repo_status("r0", "done")
        state.set_repo_status("r1", "done")
        state.set_repo_status("r2", "failed", "err")
        state.add_file("f1", "f1/f1.cbl", 100, 10, file_type="cbl")
        state.add_file("f2", "f2/f2.cbl", 200, 20, file_type="cbl")

        stats = state.get_stats()
        assert stats["repos_total"] == 5
        assert stats["repos_done"] == 2
        assert stats["repos_failed"] == 1
        assert stats["repos_pending"] == 2
        assert stats["files_unique"] == 2
        assert stats["runs_total"] == 1


class TestReferenceTables:
    def test_ref_file_types_populated(self, state):
        rows = state.con.execute("SELECT * FROM ref_file_types").fetchall()
        assert len(rows) == 11
        extensions = {r[0] for r in rows}
        assert "cbl" in extensions
        assert "cpy" in extensions
        assert "jcl" in extensions

    def test_ref_dialect_tags_populated(self, state):
        rows = state.con.execute("SELECT * FROM ref_dialect_tags").fetchall()
        assert len(rows) == 6
        tags = {r[0] for r in rows}
        assert "CICS" in tags
        assert "SQL" in tags
        assert "BATCH" in tags

    def test_ref_tables_idempotent(self, state_dir):
        sm1 = StateManager(state_dir)
        sm1.flush()
        sm1.close()
        sm2 = StateManager(state_dir)
        assert sm2.con.execute("SELECT count(*) FROM ref_file_types").fetchone()[0] == 11
        assert sm2.con.execute("SELECT count(*) FROM ref_dialect_tags").fetchone()[0] == 6
        sm2.close()

    def test_ref_tables_persist(self, state_dir):
        sm = StateManager(state_dir)
        sm.flush()
        sm.close()
        # Verify parquet files created
        assert (state_dir / "ref_file_types.parquet").exists()
        assert (state_dir / "ref_dialect_tags.parquet").exists()


class TestRejectedStatus:
    def test_get_rejectable_repos_returns_done_with_zero_files(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo({"id": "empty_repo", "clone_url": "u", "source": "gh"}, "r1")
        state.set_repo_status("empty_repo", "done")
        # No provenance added -- this repo should be rejectable
        rejectable = state.get_rejectable_repos()
        assert "empty_repo" in rejectable

    def test_get_rejectable_repos_excludes_done_with_files(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo({"id": "has_files", "clone_url": "u", "source": "gh"}, "r1")
        state.set_repo_status("has_files", "done")
        state.add_file("abc", "ab/abc.cbl", 100, 10, file_type="cbl")
        state.add_provenance("abc", "has_files", "r1", "src/X.CBL")
        rejectable = state.get_rejectable_repos()
        assert "has_files" not in rejectable

    def test_get_rejectable_repos_excludes_non_done(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo({"id": "pending", "clone_url": "u", "source": "gh"}, "r1")
        # Status is 'discovered' (not done) -- should not appear
        rejectable = state.get_rejectable_repos()
        assert "pending" not in rejectable

    def test_upsert_preserves_rejected_status(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo(
            {"id": "rej", "clone_url": "u", "source": "gh", "stars": 5}, "r1"
        )
        state.set_repo_status("rej", "rejected")
        # Re-upsert should preserve rejected status (like done)
        state.upsert_repo(
            {"id": "rej", "clone_url": "u", "source": "gh", "stars": 99}, "r1"
        )
        assert state.get_repo_status("rej") == "rejected"
        row = state.con.execute(
            "SELECT stars FROM repos WHERE repo_id = 'rej'"
        ).fetchone()
        assert row[0] == 99

    def test_get_incomplete_repos_excludes_rejected(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo({"id": "a", "clone_url": "u", "source": "gh"}, "r1")
        state.upsert_repo({"id": "b", "clone_url": "u", "source": "gh"}, "r1")
        state.set_repo_status("a", "rejected")
        incomplete = state.get_incomplete_repos()
        ids = [r["id"] for r in incomplete]
        assert "a" not in ids
        assert "b" in ids

    def test_stats_include_rejected(self, state):
        state.create_run("r1", "{}")
        state.upsert_repo({"id": "r0", "clone_url": "u", "source": "gh"}, "r1")
        state.upsert_repo({"id": "r1", "clone_url": "u", "source": "gh"}, "r1")
        state.set_repo_status("r0", "done")
        state.set_repo_status("r1", "rejected")
        stats = state.get_stats()
        assert stats["repos_rejected"] == 1
        assert stats["repos_pending"] == 0


class TestCleanupDiskScan:
    def test_scan_finds_stale_repos_dir(self, state, state_dir):
        """Disk scan detects repos/ directory for repo with no provenance."""
        from corpus_builder.cli import _scan_stale_disk_repos

        base = state_dir.parent  # state_dir is data/, base is the corpus root
        state.create_run("r1", "{}")
        state.upsert_repo({"id": "github/owner/stale", "clone_url": "u", "source": "gh"}, "r1")
        state.set_repo_status("github/owner/stale", "done")
        # Create directory on disk but no provenance
        repo_dir = base / "repos" / "github" / "owner" / "stale"
        repo_dir.mkdir(parents=True)
        (repo_dir / "dummy.cbl").touch()

        stale = _scan_stale_disk_repos(base, provenance_repo_ids=set())
        assert "github/owner/stale" in stale
        assert repo_dir in stale["github/owner/stale"]

    def test_scan_finds_stale_mirrors_with_git_suffix(self, state, state_dir):
        """Disk scan strips .git suffix from mirror bare clone directories."""
        from corpus_builder.cli import _scan_stale_disk_repos

        base = state_dir.parent
        mirror_dir = base / "mirrors" / "github" / "owner" / "myrepo.git"
        mirror_dir.mkdir(parents=True)

        stale = _scan_stale_disk_repos(base, provenance_repo_ids=set())
        assert "github/owner/myrepo" in stale
        assert mirror_dir in stale["github/owner/myrepo"]

    def test_scan_skips_repos_with_provenance(self, state, state_dir):
        """Disk scan ignores directories for repos that have provenance."""
        from corpus_builder.cli import _scan_stale_disk_repos

        base = state_dir.parent
        state.create_run("r1", "{}")
        state.upsert_repo({"id": "github/owner/good", "clone_url": "u", "source": "gh"}, "r1")
        state.set_repo_status("github/owner/good", "done")
        state.add_file("abc", "ab/abc.cbl", 100, 10, file_type="cbl")
        state.add_provenance("abc", "github/owner/good", "r1", "src/X.CBL")

        repo_dir = base / "repos" / "github" / "owner" / "good"
        repo_dir.mkdir(parents=True)
        mirror_dir = base / "mirrors" / "github" / "owner" / "good.git"
        mirror_dir.mkdir(parents=True)

        provenance = {"github/owner/good"}
        stale = _scan_stale_disk_repos(base, provenance_repo_ids=provenance)
        assert "github/owner/good" not in stale

    def test_prune_empty_parents(self, state_dir):
        """_remove_dir_and_prune_parents cleans up empty ancestor dirs."""
        from corpus_builder.cli import _remove_dir_and_prune_parents

        base = state_dir.parent
        stop_at = base / "repos"
        leaf = stop_at / "github" / "owner" / "repo"
        leaf.mkdir(parents=True)
        (leaf / "file.txt").touch()

        _remove_dir_and_prune_parents(leaf, stop_at)

        assert not leaf.exists()
        assert not (stop_at / "github" / "owner").exists()
        assert not (stop_at / "github").exists()
        assert stop_at.exists()  # stop_at itself is preserved


class TestFileTypeMigration:
    def test_migrate_files_without_file_type(self, state_dir):
        """Old Parquet without file_type column gets migrated with 'unknown'."""
        import duckdb

        state_dir.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(":memory:")
        # Create old-schema files table (no file_type column)
        con.execute("""
            CREATE TABLE files (
                sha256 VARCHAR PRIMARY KEY,
                store_path VARCHAR NOT NULL,
                byte_size INTEGER NOT NULL,
                line_count INTEGER NOT NULL,
                dialect_tags VARCHAR DEFAULT '',
                first_seen_at TIMESTAMP NOT NULL
            )
        """)
        con.execute(
            "INSERT INTO files VALUES ('oldhash', 'old/path.cbl', 500, 25, 'SQL', '2025-01-01')"
        )
        parquet_path = state_dir / "files.parquet"
        con.execute(f"COPY files TO '{parquet_path}' (FORMAT parquet)")
        con.close()

        sm = StateManager(state_dir)
        row = sm.con.execute(
            "SELECT file_type FROM files WHERE sha256 = 'oldhash'"
        ).fetchone()
        assert row[0] == "unknown"
        sm.close()


class TestRemoveProvenance:
    def test_remove_provenance_deletes_entry(self, state):
        state.create_run("r1", "{}")
        state.add_file("abc", "ab/abc.cbl", 100, 10, file_type="cbl")
        state.upsert_repo({"id": "gh_1", "clone_url": "u", "source": "gh"}, "r1")
        state.add_provenance("abc", "gh_1", "r1", "src/PAY.CBL")
        # Verify it exists
        count = state.con.execute(
            "SELECT count(*) FROM file_provenance WHERE sha256 = 'abc' AND repo_id = 'gh_1'"
        ).fetchone()[0]
        assert count == 1
        # Remove it
        state.remove_provenance("abc", "gh_1")
        count = state.con.execute(
            "SELECT count(*) FROM file_provenance WHERE sha256 = 'abc' AND repo_id = 'gh_1'"
        ).fetchone()[0]
        assert count == 0

    def test_remove_provenance_leaves_other_repos(self, state):
        state.create_run("r1", "{}")
        state.add_file("abc", "ab/abc.cbl", 100, 10, file_type="cbl")
        state.upsert_repo({"id": "gh_1", "clone_url": "u", "source": "gh"}, "r1")
        state.upsert_repo({"id": "gh_2", "clone_url": "u2", "source": "gh"}, "r1")
        state.add_provenance("abc", "gh_1", "r1", "src/PAY.CBL")
        state.add_provenance("abc", "gh_2", "r1", "src/PAY.CBL")
        state.remove_provenance("abc", "gh_1")
        count = state.con.execute(
            "SELECT count(*) FROM file_provenance WHERE sha256 = 'abc'"
        ).fetchone()[0]
        assert count == 1


class TestRemoveFileIfOrphaned:
    def test_removes_orphaned_file(self, state):
        state.add_file("abc", "ab/abc.cbl", 100, 10, file_type="cbl")
        # No provenance -- should be orphaned
        removed = state.remove_file_if_orphaned("abc")
        assert removed is True
        assert not state.file_exists("abc")

    def test_preserves_file_with_provenance(self, state):
        state.create_run("r1", "{}")
        state.add_file("abc", "ab/abc.cbl", 100, 10, file_type="cbl")
        state.upsert_repo({"id": "gh_1", "clone_url": "u", "source": "gh"}, "r1")
        state.add_provenance("abc", "gh_1", "r1", "src/PAY.CBL")
        removed = state.remove_file_if_orphaned("abc")
        assert removed is False
        assert state.file_exists("abc")

    def test_nonexistent_hash_returns_true(self, state):
        # No file record, no provenance -- delete is a no-op but returns True
        removed = state.remove_file_if_orphaned("nonexistent")
        assert removed is True


class TestRepoSizeKbMigration:
    def test_migrate_repos_without_repo_size_kb(self, state_dir):
        """Old Parquet without repo_size_kb column gets migrated with NULL."""
        import duckdb

        state_dir.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(":memory:")
        con.execute("""
            CREATE TABLE repos (
                repo_id         VARCHAR PRIMARY KEY,
                clone_url       VARCHAR NOT NULL,
                source          VARCHAR NOT NULL,
                status          VARCHAR NOT NULL DEFAULT 'discovered',
                error_msg       VARCHAR,
                license_spdx    VARCHAR,
                stars           INTEGER,
                description     VARCHAR,
                default_branch  VARCHAR,
                last_pushed_at  TIMESTAMP,
                discovered_at   TIMESTAMP NOT NULL,
                completed_at    TIMESTAMP,
                last_run_id     VARCHAR
            )
        """)
        con.execute(
            "INSERT INTO repos (repo_id, clone_url, source, status, discovered_at) "
            "VALUES ('gh/old', 'https://x.git', 'github', 'done', '2025-01-01')"
        )
        parquet_path = state_dir / "repos.parquet"
        con.execute(f"COPY repos TO '{parquet_path}' (FORMAT parquet)")
        con.close()

        sm = StateManager(state_dir)
        row = sm.con.execute(
            "SELECT repo_size_kb FROM repos WHERE repo_id = 'gh/old'"
        ).fetchone()
        assert row[0] is None
        sm.close()
