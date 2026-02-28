import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from corpus_builder.sources.github import (
    GitHubAdapter,
    MAX_RATE_LIMIT_RETRIES,
    MAX_RETRIES,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _mock_response(
    status_code: int, json_data: dict, headers: dict | None = None
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.headers = headers or {}
    return resp


class TestGitHubAdapter:
    def test_discovers_repos(self):
        page1 = _load_fixture("github_search_page1.json")
        empty = _load_fixture("github_search_empty.json")

        with patch("corpus_builder.sources.github.requests.get") as mock_get:
            mock_get.side_effect = [
                _mock_response(200, page1),
                _mock_response(200, empty),
            ]
            adapter = GitHubAdapter(
                token="test-token", query="language:COBOL", max_repos=10
            )
            repos = list(adapter.discover_repositories())

        assert len(repos) == 2
        assert repos[0]["id"] == "github/test/cobol-payroll"
        assert repos[0]["source"] == "github"
        assert repos[0]["license_spdx"] == "MIT"
        assert repos[0]["stars"] == 15
        assert repos[1]["id"] == "github/test/cobol-banking"
        assert repos[1]["license_spdx"] is None

    def test_respects_max_repos(self):
        page1 = _load_fixture("github_search_page1.json")

        with patch("corpus_builder.sources.github.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, page1)
            adapter = GitHubAdapter(
                token="test-token", query="language:COBOL", max_repos=1
            )
            repos = list(adapter.discover_repositories())

        assert len(repos) == 1

    def test_handles_empty_results(self):
        empty = _load_fixture("github_search_empty.json")

        with patch("corpus_builder.sources.github.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, empty)
            adapter = GitHubAdapter(
                token="test-token", query="language:COBOL", max_repos=10
            )
            repos = list(adapter.discover_repositories())

        assert len(repos) == 0

    def test_retries_on_rate_limit(self):
        page1 = _load_fixture("github_search_page1.json")
        empty = _load_fixture("github_search_empty.json")

        rate_limited = _mock_response(429, {})
        ok_response = _mock_response(200, page1)
        empty_response = _mock_response(200, empty)

        with patch("corpus_builder.sources.github.requests.get") as mock_get, \
             patch("corpus_builder.sources.github.backoff_sleep"):
            mock_get.side_effect = [rate_limited, ok_response, empty_response]
            adapter = GitHubAdapter(
                token="test-token", query="language:COBOL", max_repos=10
            )
            repos = list(adapter.discover_repositories())

        assert len(repos) == 2

    def test_returns_none_after_max_error_retries(self):
        """Exhausting error retries (5xx) returns None."""
        server_error = _mock_response(500, {})

        with patch("corpus_builder.sources.github.requests.get") as mock_get, \
             patch("corpus_builder.sources.github.backoff_sleep"):
            mock_get.return_value = server_error
            adapter = GitHubAdapter(
                token="test-token", query="language:COBOL", max_repos=10
            )
            repos = list(adapter.discover_repositories())

        assert len(repos) == 0
        assert mock_get.call_count == MAX_RETRIES

    def test_returns_none_after_max_rate_limit_retries(self):
        """Exhausting rate-limit retries returns None."""
        rate_limited = _mock_response(429, {})

        with patch("corpus_builder.sources.github.requests.get") as mock_get, \
             patch("corpus_builder.sources.github.backoff_sleep"):
            mock_get.return_value = rate_limited
            adapter = GitHubAdapter(
                token="test-token", query="language:COBOL", max_repos=10
            )
            repos = list(adapter.discover_repositories())

        assert len(repos) == 0
        # 1 initial + MAX_RATE_LIMIT_RETRIES more
        assert mock_get.call_count == MAX_RATE_LIMIT_RETRIES + 1

    def test_rate_limit_retries_do_not_count_against_error_retries(self):
        """Rate-limit 429s should not exhaust the error budget."""
        page1 = _load_fixture("github_search_page1.json")
        empty = _load_fixture("github_search_empty.json")

        # More 429s than MAX_RETRIES, but fewer than MAX_RATE_LIMIT_RETRIES
        responses = [_mock_response(429, {}) for _ in range(MAX_RETRIES + 2)]
        responses.append(_mock_response(200, page1))
        responses.append(_mock_response(200, empty))

        with patch("corpus_builder.sources.github.requests.get") as mock_get, \
             patch("corpus_builder.sources.github.backoff_sleep"):
            mock_get.side_effect = responses
            adapter = GitHubAdapter(
                token="test-token", query="language:COBOL", max_repos=10
            )
            repos = list(adapter.discover_repositories())

        # Should succeed despite more 429s than MAX_RETRIES
        assert len(repos) == 2

    def test_uses_retry_after_header(self):
        """When server provides Retry-After, use that instead of backoff."""
        page1 = _load_fixture("github_search_page1.json")
        empty = _load_fixture("github_search_empty.json")

        rate_limited = _mock_response(
            429, {}, headers={"Retry-After": "2"}
        )
        ok_response = _mock_response(200, page1)
        empty_response = _mock_response(200, empty)

        with patch("corpus_builder.sources.github.requests.get") as mock_get, \
             patch("corpus_builder.sources.github.time.sleep") as mock_sleep, \
             patch("corpus_builder.sources.github.backoff_sleep"):
            mock_get.side_effect = [rate_limited, ok_response, empty_response]
            adapter = GitHubAdapter(
                token="test-token", query="language:COBOL", max_repos=10
            )
            repos = list(adapter.discover_repositories())

        assert len(repos) == 2
        # time.sleep should have been called with 2.0 for the Retry-After
        mock_sleep.assert_called_once_with(2.0)

    def test_uses_x_ratelimit_reset_header(self):
        """When server provides X-RateLimit-Reset, compute wait from it."""
        page1 = _load_fixture("github_search_page1.json")
        empty = _load_fixture("github_search_empty.json")

        future_ts = str(int(time.time()) + 5)
        rate_limited = _mock_response(
            403, {}, headers={"X-RateLimit-Reset": future_ts}
        )
        ok_response = _mock_response(200, page1)
        empty_response = _mock_response(200, empty)

        with patch("corpus_builder.sources.github.requests.get") as mock_get, \
             patch("corpus_builder.sources.github.time.sleep") as mock_sleep, \
             patch("corpus_builder.sources.github.backoff_sleep"):
            mock_get.side_effect = [rate_limited, ok_response, empty_response]
            adapter = GitHubAdapter(
                token="test-token", query="language:COBOL", max_repos=10
            )
            repos = list(adapter.discover_repositories())

        assert len(repos) == 2
        # Should have slept approximately 5+1 seconds (with buffer)
        sleep_val = mock_sleep.call_args[0][0]
        assert 4 <= sleep_val <= 8

    def test_logs_total_count_on_first_page(self, caplog):
        """Should log the total_count from GitHub's first page response."""
        page1 = _load_fixture("github_search_page1.json")
        page1["total_count"] = 42
        empty = _load_fixture("github_search_empty.json")

        with patch("corpus_builder.sources.github.requests.get") as mock_get, \
             caplog.at_level("INFO", logger="corpus_builder.sources.github"):
            mock_get.side_effect = [
                _mock_response(200, page1),
                _mock_response(200, empty),
            ]
            adapter = GitHubAdapter(
                token="test-token", query="language:COBOL", max_repos=100
            )
            list(adapter.discover_repositories())

        assert "42 total matches" in caplog.text
