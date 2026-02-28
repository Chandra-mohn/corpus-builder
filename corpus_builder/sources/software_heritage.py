from __future__ import annotations

import logging
import re
import time
from urllib.parse import urlparse

import requests

from ..rate_limiter import TokenBucketRateLimiter, backoff_sleep, get_retry_after
from .base import SourceAdapter

log = logging.getLogger(__name__)

MAX_RETRIES = 5
MAX_RATE_LIMIT_RETRIES = 10

_LINK_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


class SoftwareHeritageAdapter(SourceAdapter):

    def __init__(self, query: str, max_repos: int = 0, requests_per_minute: int = 2):
        self.query = query
        self.max_repos = max_repos  # 0 = no limit
        self.limiter = TokenBucketRateLimiter(rate=requests_per_minute, period=60.0)

    def discover_repositories(self):
        # SWH search uses the query as a path segment, not a query param.
        # limit=1000 is the API max -- minimises requests under tight rate limits.
        base = "https://archive.softwareheritage.org/api/1/origin/search"
        url = f"{base}/{self.query}/"
        params: dict = {"limit": 1000}

        count = 0

        while url and (self.max_repos == 0 or count < self.max_repos):
            data, next_url = self._request_with_retry(url, params)
            if data is None:
                break

            if count == 0 and isinstance(data, list):
                log.info(
                    "SWH returned %d origins on first page", len(data)
                )

            origins = data if isinstance(data, list) else data.get("results", [])

            for origin in origins:
                repo_name = _name_from_url(origin["url"])
                yield {
                    "id": f"software_heritage/{repo_name}",
                    "clone_url": origin["url"],
                    "vcs": "git",
                    "source": "software_heritage",
                }
                count += 1
                if self.max_repos and count >= self.max_repos:
                    break

            # Follow pagination via Link header
            url = next_url
            params = {}  # next_url already contains page_token

        log.info("Discovered %d repos from Software Heritage", count)

    def _request_with_retry(
        self, url: str, params: dict
    ) -> tuple[list | dict | None, str | None]:
        """Return (json_body, next_page_url) or (None, None) on failure."""
        error_attempts = 0
        rate_limit_retries = 0

        while error_attempts < MAX_RETRIES:
            self.limiter.acquire()
            log.debug(
                "SWH request (attempt %d, rl_retry %d)",
                error_attempts,
                rate_limit_retries,
            )

            try:
                r = requests.get(url, params=params, timeout=30)
            except requests.RequestException as exc:
                log.warning("SWH request error: %s", exc)
                error_attempts += 1
                backoff_sleep(error_attempts)
                continue

            if r.status_code == 200:
                next_url = _parse_link_next(r.headers.get("Link", ""))
                return r.json(), next_url

            if r.status_code in (429,):
                rate_limit_retries += 1
                if rate_limit_retries > MAX_RATE_LIMIT_RETRIES:
                    log.error(
                        "Rate limit retries exhausted (%d)",
                        MAX_RATE_LIMIT_RETRIES,
                    )
                    return None, None
                wait = get_retry_after(r)
                if wait is not None:
                    log.info(
                        "SWH rate limited, server says wait %.0fs", wait
                    )
                    time.sleep(wait)
                else:
                    log.warning("SWH rate limited, using backoff")
                    backoff_sleep(rate_limit_retries)
                continue  # does NOT increment error_attempts

            if r.status_code >= 500:
                error_attempts += 1
                log.warning(
                    "SWH server error (HTTP %d), retrying", r.status_code
                )
                backoff_sleep(error_attempts)
                continue

            # 4xx client errors (404, 422, etc.) -- not retryable
            log.error(
                "SWH client error (HTTP %d) for %s", r.status_code, url
            )
            return None, None

        log.error(
            "SWH request failed after %d error retries "
            "(%d rate-limit retries)",
            MAX_RETRIES,
            rate_limit_retries,
        )
        return None, None


def _parse_link_next(link_header: str) -> str | None:
    """Extract the 'next' URL from a Link header."""
    match = _LINK_NEXT_RE.search(link_header)
    return match.group(1) if match else None


def _name_from_url(url: str) -> str:
    """Extract a meaningful name from an origin URL.

    e.g. 'https://github.com/foo/bar.git' -> 'foo/bar'
         'https://gitlab.com/org/sub/repo' -> 'org/sub/repo'
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path or url
