"""Tests for core/rate_limiter.py — token bucket rate limiting."""

from __future__ import annotations

import threading

import pytest

from core.rate_limiter import RateLimiter


@pytest.fixture(autouse=True)
def _enable_rate_limiting(monkeypatch):
    """Remove VIBESRAILS_RATE_LIMIT=0 so tests exercise real limiting."""
    monkeypatch.delenv("VIBESRAILS_RATE_LIMIT", raising=False)


# ── Under limit ──────────────────────────────────────────────────────


def test_single_call_allowed():
    """A single call is always allowed."""
    limiter = RateLimiter(per_tool_rpm=60, global_rpm=300)
    assert limiter.check("ping") is True


def test_many_calls_under_limit():
    """Multiple calls under the per-tool limit are allowed."""
    limiter = RateLimiter(per_tool_rpm=10, global_rpm=300)
    for _ in range(10):
        assert limiter.check("ping") is True


# ── Over limit ───────────────────────────────────────────────────────


def test_per_tool_limit_exceeded():
    """Calls beyond per-tool capacity are rejected."""
    limiter = RateLimiter(per_tool_rpm=5, global_rpm=300)
    for _ in range(5):
        limiter.check("scan_code")
    assert limiter.check("scan_code") is False


def test_global_limit_exceeded():
    """Global limit applies across all tools."""
    limiter = RateLimiter(per_tool_rpm=100, global_rpm=5)
    # Use different tools to stay under per-tool limit
    for i in range(5):
        assert limiter.check(f"tool_{i}") is True
    # 6th call to a new tool exceeds global
    assert limiter.check("tool_extra") is False


# ── Per-tool isolation ───────────────────────────────────────────────


def test_separate_tool_budgets():
    """Different tools have independent per-tool budgets."""
    limiter = RateLimiter(per_tool_rpm=3, global_rpm=300)
    # Exhaust tool A
    for _ in range(3):
        limiter.check("tool_a")
    assert limiter.check("tool_a") is False
    # Tool B still has its full budget
    assert limiter.check("tool_b") is True


# ── Reset ────────────────────────────────────────────────────────────


def test_reset_restores_budgets():
    """reset() refills all buckets."""
    limiter = RateLimiter(per_tool_rpm=3, global_rpm=300)
    for _ in range(3):
        limiter.check("ping")
    assert limiter.check("ping") is False
    limiter.reset()
    assert limiter.check("ping") is True


# ── Token refill ─────────────────────────────────────────────────────


def test_tokens_refill_over_time():
    """After waiting, tokens should refill and allow new calls."""
    # 60 RPM = 1 token/second refill
    limiter = RateLimiter(per_tool_rpm=60, global_rpm=300)
    # Exhaust all tokens
    for _ in range(60):
        limiter.check("scan_code")
    assert limiter.check("scan_code") is False

    # Manually advance bucket time to simulate 2 seconds passing
    with limiter._lock:
        bucket = limiter._get_tool_bucket("scan_code")
        bucket.last_refill -= 2.0
        limiter._global_bucket.last_refill -= 2.0

    # Should now have ~2 tokens
    assert limiter.check("scan_code") is True


# ── Disable via env var ──────────────────────────────────────────────


def test_disabled_via_env_var(monkeypatch):
    """VIBESRAILS_RATE_LIMIT=0 disables all rate limiting."""
    monkeypatch.setenv("VIBESRAILS_RATE_LIMIT", "0")
    limiter = RateLimiter(per_tool_rpm=1, global_rpm=1)
    # Even with capacity=1, unlimited calls should pass
    for _ in range(100):
        assert limiter.check("scan_code") is True


def test_enabled_when_env_var_absent():
    """Without env var, rate limiting is active."""
    limiter = RateLimiter(per_tool_rpm=2, global_rpm=300)
    limiter.check("ping")
    limiter.check("ping")
    assert limiter.check("ping") is False


# ── retry_after ──────────────────────────────────────────────────────


def test_retry_after_when_limited():
    """retry_after returns positive seconds when limited."""
    limiter = RateLimiter(per_tool_rpm=1, global_rpm=300)
    limiter.check("ping")  # exhaust
    assert limiter.check("ping") is False
    wait = limiter.retry_after("ping")
    assert wait >= 1


def test_retry_after_when_available():
    """retry_after returns 0 when tokens are available."""
    limiter = RateLimiter(per_tool_rpm=60, global_rpm=300)
    assert limiter.retry_after("ping") == 0


# ── Thread safety ────────────────────────────────────────────────────


def test_concurrent_access():
    """Multiple threads can safely access the limiter."""
    limiter = RateLimiter(per_tool_rpm=100, global_rpm=1000)
    results: list[bool] = []
    errors: list[Exception] = []

    def worker():
        try:
            for _ in range(50):
                results.append(limiter.check("concurrent_tool"))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"Thread errors: {errors}"
    # All 100 per-tool calls should succeed (capacity=100)
    assert sum(results) == 100
