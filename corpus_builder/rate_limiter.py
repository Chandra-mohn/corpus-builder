from __future__ import annotations

import logging
import random
import time
from typing import Any

log = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """Simple token-bucket rate limiter.

    Allows up to `rate` requests per `period` seconds.
    Calls to `acquire` block until a token is available.
    """

    def __init__(self, rate: int, period: float = 60.0):
        self.rate = rate
        self.period = period
        self.tokens = float(rate)
        self.max_tokens = float(rate)
        self.last_refill = time.monotonic()

    def acquire(self) -> None:
        self._refill()
        while self.tokens < 1.0:
            deficit = 1.0 - self.tokens
            wait = deficit * (self.period / self.rate)
            log.debug("Rate limiter: waiting %.2fs for token", wait)
            time.sleep(wait)
            self._refill()
        self.tokens -= 1.0

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * (self.rate / self.period))
        self.last_refill = now


def backoff_sleep(attempt: int, base: float = 2.0, max_wait: float = 60.0) -> None:
    """Exponential backoff with jitter."""
    wait = min(base ** attempt, max_wait)
    jitter = random.uniform(0, wait * 0.5)
    total = wait + jitter
    log.info("Backoff: attempt %d, sleeping %.1fs", attempt, total)
    time.sleep(total)


def get_retry_after(response: Any) -> float | None:
    """Extract wait time from rate-limit response headers.

    Checks ``Retry-After`` (seconds) first, then ``X-RateLimit-Reset``
    (unix timestamp).  Returns *None* when neither header is present so
    callers can fall back to generic backoff.
    """
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return float(retry_after)
        except (ValueError, TypeError):
            pass

    reset_at = response.headers.get("X-RateLimit-Reset")
    if reset_at is not None:
        try:
            wait = int(reset_at) - time.time()
            return max(wait, 0) + 1  # +1s buffer
        except (ValueError, TypeError):
            pass

    return None
