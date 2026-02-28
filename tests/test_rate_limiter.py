import time
from unittest.mock import MagicMock

from corpus_builder.rate_limiter import TokenBucketRateLimiter, get_retry_after


def test_burst_allowed():
    rl = TokenBucketRateLimiter(rate=10, period=1.0)
    start = time.monotonic()
    for _ in range(10):
        rl.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.5, f"Burst of 10 took too long: {elapsed:.2f}s"


def test_throttles_after_burst():
    rl = TokenBucketRateLimiter(rate=5, period=1.0)
    for _ in range(5):
        rl.acquire()
    start = time.monotonic()
    rl.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.1, f"Throttle too fast: {elapsed:.4f}s"


def test_tokens_refill():
    rl = TokenBucketRateLimiter(rate=10, period=1.0)
    for _ in range(10):
        rl.acquire()
    time.sleep(0.5)
    start = time.monotonic()
    rl.acquire()
    elapsed = time.monotonic() - start
    # After 0.5s, ~5 tokens should have refilled
    assert elapsed < 0.2, f"Token refill too slow: {elapsed:.2f}s"


# -- get_retry_after tests --


def _resp_with_headers(headers: dict) -> MagicMock:
    resp = MagicMock()
    resp.headers = headers
    return resp


def test_get_retry_after_with_retry_after_header():
    resp = _resp_with_headers({"Retry-After": "30"})
    assert get_retry_after(resp) == 30.0


def test_get_retry_after_with_fractional_retry_after():
    resp = _resp_with_headers({"Retry-After": "1.5"})
    assert get_retry_after(resp) == 1.5


def test_get_retry_after_with_x_ratelimit_reset():
    future = int(time.time()) + 10
    resp = _resp_with_headers({"X-RateLimit-Reset": str(future)})
    wait = get_retry_after(resp)
    assert wait is not None
    # Should be roughly 10 + 1 (buffer), give some slack for test execution
    assert 9 <= wait <= 13


def test_get_retry_after_with_past_reset_timestamp():
    """If the reset timestamp is in the past, wait should be ~1s (the buffer)."""
    past = int(time.time()) - 100
    resp = _resp_with_headers({"X-RateLimit-Reset": str(past)})
    wait = get_retry_after(resp)
    assert wait is not None
    assert wait == 1  # max(negative, 0) + 1


def test_get_retry_after_prefers_retry_after_over_reset():
    """Retry-After takes precedence over X-RateLimit-Reset."""
    future = int(time.time()) + 100
    resp = _resp_with_headers({
        "Retry-After": "5",
        "X-RateLimit-Reset": str(future),
    })
    assert get_retry_after(resp) == 5.0


def test_get_retry_after_returns_none_when_no_headers():
    resp = _resp_with_headers({})
    assert get_retry_after(resp) is None


def test_get_retry_after_handles_invalid_retry_after():
    resp = _resp_with_headers({"Retry-After": "not-a-number"})
    assert get_retry_after(resp) is None


def test_get_retry_after_handles_invalid_reset():
    resp = _resp_with_headers({"X-RateLimit-Reset": "not-a-number"})
    assert get_retry_after(resp) is None
