"""In-memory rate limiter for MCP tool calls.

Uses the token bucket algorithm: each bucket refills at a constant rate
and holds up to `capacity` tokens. One token consumed per call.

Disabled when VIBESRAILS_RATE_LIMIT=0 environment variable is set.
Resets on server restart (in-memory only, no persistence).
"""

from __future__ import annotations

import os
import threading
import time


class _Bucket:
    """Single token bucket for one rate limit scope."""

    __slots__ = ("capacity", "tokens", "refill_rate", "last_refill")

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        """Try to consume one token. Returns True if allowed."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def seconds_until_available(self) -> int:
        """Seconds until at least 1 token is available."""
        if self.tokens >= 1.0:
            return 0
        deficit = 1.0 - self.tokens
        return max(1, int(deficit / self.refill_rate) + 1)


class RateLimiter:
    """Rate limiter with per-tool and global buckets.

    Args:
        per_tool_rpm: Max requests per minute per tool (default 60).
        global_rpm: Max requests per minute across all tools (default 300).
    """

    def __init__(
        self,
        per_tool_rpm: int = 60,
        global_rpm: int = 300,
    ) -> None:
        self._per_tool_rpm = per_tool_rpm
        self._global_rpm = global_rpm
        self._tool_buckets: dict[str, _Bucket] = {}
        self._global_bucket = _Bucket(
            capacity=global_rpm,
            refill_rate=global_rpm / 60.0,
        )
        self._lock = threading.Lock()

    @property
    def disabled(self) -> bool:
        """Check if rate limiting is disabled via environment variable."""
        return os.environ.get("VIBESRAILS_RATE_LIMIT") == "0"

    def _get_tool_bucket(self, tool_name: str) -> _Bucket:
        if tool_name not in self._tool_buckets:
            self._tool_buckets[tool_name] = _Bucket(
                capacity=self._per_tool_rpm,
                refill_rate=self._per_tool_rpm / 60.0,
            )
        return self._tool_buckets[tool_name]

    def check(self, tool_name: str) -> bool:
        """Check if a tool call is allowed.

        Returns True if allowed, False if rate limited.
        Thread-safe.
        """
        if self.disabled:
            return True

        with self._lock:
            tool_bucket = self._get_tool_bucket(tool_name)
            if not tool_bucket.consume():
                return False
            if not self._global_bucket.consume():
                # Refund the tool token since global is exhausted
                tool_bucket.tokens = min(
                    tool_bucket.capacity, tool_bucket.tokens + 1.0
                )
                return False
            return True

    def retry_after(self, tool_name: str) -> int:
        """Seconds until the next call would be allowed."""
        if self.disabled:
            return 0
        with self._lock:
            tool_bucket = self._get_tool_bucket(tool_name)
            tool_wait = tool_bucket.seconds_until_available()
            global_wait = self._global_bucket.seconds_until_available()
            return max(tool_wait, global_wait)

    def reset(self) -> None:
        """Reset all buckets (for testing)."""
        with self._lock:
            self._tool_buckets.clear()
            self._global_bucket = _Bucket(
                capacity=self._global_rpm,
                refill_rate=self._global_rpm / 60.0,
            )
