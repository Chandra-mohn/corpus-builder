"""Tests for the discover CLI command and two-phase workflow."""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from corpus_builder.config import Config, SourceConfig
from corpus_builder.state import StateManager


def _make_config(output_dir: str) -> Config:
    return Config(
        output_dir=output_dir,
        sources={
            "github": SourceConfig(
                enabled=True,
                query="language:cobol",
                max_repos=2,
                token="fake",
            ),
        },
    )


def _fake_repos(count: int = 2):
    """Return a list of fake repo dicts as an adapter would yield."""
    for i in range(count):
        yield {
            "id": f"github/org/repo{i}",
            "clone_url": f"https://github.com/org/repo{i}.git",
            "source": "github",
            "vcs": "git",
            "license_spdx": "MIT",
            "stars": i * 10,
            "description": f"Repo {i}",
            "default_branch": "main",
            "repo_size_kb": (i + 1) * 100,
        }


class TestDiscoverPopulatesManifest:
    def test_discover_adds_repos_to_state(self):
        """Discover should populate repos table without extracting."""
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "data"
            state = StateManager(data_dir)

            for repo in _fake_repos(3):
                state.upsert_repo(repo, run_id=None)

            state.flush()

            count = state.con.execute("SELECT count(*) FROM repos").fetchone()[0]
            assert count == 3

            # All should be in 'discovered' status
            statuses = state.con.execute(
                "SELECT DISTINCT status FROM repos"
            ).fetchall()
            assert statuses == [("discovered",)]

            # No extraction should have happened -- no files, no provenance
            assert state.con.execute("SELECT count(*) FROM files").fetchone()[0] == 0
            assert state.con.execute("SELECT count(*) FROM file_provenance").fetchone()[0] == 0

            state.close()


class TestDiscoverIdempotency:
    def test_discover_twice_no_duplicate_repos(self):
        """Running discover twice should not duplicate repos."""
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "data"
            state = StateManager(data_dir)

            repos = list(_fake_repos(2))
            for repo in repos:
                state.upsert_repo(repo, run_id=None)
            state.flush()

            count1 = state.con.execute("SELECT count(*) FROM repos").fetchone()[0]
            assert count1 == 2

            # Second discovery pass with same repos
            for repo in repos:
                state.upsert_repo(repo, run_id=None)
            state.flush()

            count2 = state.con.execute("SELECT count(*) FROM repos").fetchone()[0]
            assert count2 == 2  # no duplicates

            state.close()

    def test_discover_preserves_done_repos(self):
        """Re-discovering a done repo should not reset its status."""
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "data"
            state = StateManager(data_dir)

            repos = list(_fake_repos(2))
            for repo in repos:
                state.upsert_repo(repo, run_id=None)

            # Mark first repo as done
            state.set_repo_status("github/org/repo0", "done")

            # Re-discover
            for repo in repos:
                state.upsert_repo(repo, run_id=None)

            assert state.get_repo_status("github/org/repo0") == "done"
            assert state.get_repo_status("github/org/repo1") == "discovered"

            state.close()

    def test_discover_captures_repo_size(self):
        """repo_size_kb from adapter should be stored."""
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "data"
            state = StateManager(data_dir)

            state.upsert_repo(
                {
                    "id": "github/org/sized",
                    "clone_url": "https://github.com/org/sized.git",
                    "source": "github",
                    "repo_size_kb": 2048,
                },
                run_id=None,
            )

            row = state.con.execute(
                "SELECT repo_size_kb FROM repos WHERE repo_id = 'github/org/sized'"
            ).fetchone()
            assert row[0] == 2048

            state.close()
