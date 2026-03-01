from __future__ import annotations

import logging
import time

import requests

from ..rate_limiter import TokenBucketRateLimiter, backoff_sleep, get_retry_after
from .base import SourceAdapter

log = logging.getLogger(__name__)

MAX_RETRIES = 5
MAX_RATE_LIMIT_RETRIES = 10


class GitHubAdapter(SourceAdapter):

    def __init__(
        self,
        token: str,
        query: str,
        max_repos: int = 0,
        requests_per_minute: int = 30,
    ):
        self.token = token
        self.query = query
        self.max_repos = max_repos  # 0 = no limit
        self.limiter = TokenBucketRateLimiter(rate=requests_per_minute, period=60.0)

    def discover_repositories(self):
        url = "https://api.github.com/search/repositories"
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        page = 1
        collected = 0

        while self.max_repos == 0 or collected < self.max_repos:
            params = {
                "q": self.query,
                "per_page": 50,
                "page": page,
            }

            data = self._request_with_retry(url, headers, params)
            if data is None:
                break

            if page == 1 and "total_count" in data:
                log.info(
                    "GitHub reports %d total matches for query",
                    data["total_count"],
                )

            items = data.get("items", [])
            if not items:
                log.debug("No more results from GitHub")
                break

            for repo in items:
                yield {
                    "id": f"github/{repo['full_name']}",
                    "clone_url": repo["clone_url"],
                    "vcs": "git",
                    "source": "github",
                    "license_spdx": _extract_license(repo),
                    "stars": repo.get("stargazers_count"),
                    "description": repo.get("description"),
                    "default_branch": repo.get("default_branch"),
                    "last_pushed_at": repo.get("pushed_at"),
                    "repo_size_kb": repo.get("size"),
                    "is_fork": repo.get("fork", False),
                }
                collected += 1
                if self.max_repos and collected >= self.max_repos:
                    break

            page += 1

        log.info("Discovered %d repos from GitHub", collected)

    def _request_with_retry(
        self, url: str, headers: dict, params: dict
    ) -> dict | None:
        error_attempts = 0
        rate_limit_retries = 0

        while error_attempts < MAX_RETRIES:
            self.limiter.acquire()
            log.debug(
                "GitHub search page %d (attempt %d, rl_retry %d)",
                params.get("page"),
                error_attempts,
                rate_limit_retries,
            )

            try:
                r = requests.get(url, headers=headers, params=params, timeout=30)
            except requests.RequestException as exc:
                log.warning("GitHub request error: %s", exc)
                error_attempts += 1
                backoff_sleep(error_attempts)
                continue

            if r.status_code == 200:
                return r.json()

            if r.status_code in (403, 429):
                rate_limit_retries += 1
                if rate_limit_retries > MAX_RATE_LIMIT_RETRIES:
                    log.error(
                        "Rate limit retries exhausted (%d)",
                        MAX_RATE_LIMIT_RETRIES,
                    )
                    return None
                wait = get_retry_after(r)
                if wait is not None:
                    log.info(
                        "Rate limited (HTTP %d), server says wait %.0fs",
                        r.status_code,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    log.warning(
                        "Rate limited (HTTP %d), using backoff",
                        r.status_code,
                    )
                    backoff_sleep(rate_limit_retries)
                continue  # does NOT increment error_attempts

            if r.status_code >= 500:
                error_attempts += 1
                log.warning(
                    "GitHub server error (HTTP %d), retrying", r.status_code
                )
                backoff_sleep(error_attempts)
                continue

            r.raise_for_status()

        log.error(
            "GitHub request failed after %d error retries "
            "(%d rate-limit retries)",
            MAX_RETRIES,
            rate_limit_retries,
        )
        return None


def _extract_license(repo: dict) -> str | None:
    lic = repo.get("license")
    if lic and isinstance(lic, dict):
        return lic.get("spdx_id")
    return None
