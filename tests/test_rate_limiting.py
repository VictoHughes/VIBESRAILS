"""Tests for rate limiting in VibesRails."""
import time
import pytest

from vibesrails.rate_limiting import (
    CircuitBreaker,
    RateLimitConfig,
    RequestThrottler,
    ResponseCache,
    with_rate_limiting,
    reset_rate_limiting,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset rate limiting state before each test."""
    reset_rate_limiting()
    yield
    reset_rate_limiting()


class TestResponseCache:
    """Test response caching."""

    def test_cache_hit(self):
        """Cache should return cached value for valid key."""
        config = RateLimitConfig(cache_enabled=True, cache_ttl=3600)
        cache = ResponseCache(config)

        cache.set("test-key", "test-value")
        result = cache.get("test-key")
        assert result == "test-value"

    def test_cache_expiration(self):
        """Cache should expire after TTL."""
        config = RateLimitConfig(cache_enabled=True, cache_ttl=1)
        cache = ResponseCache(config)

        cache.set("test-key", "test-value")
        time.sleep(1.1)
        result = cache.get("test-key")
        assert result is None


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_closed_state_allows_calls(self):
        """Circuit should allow calls in closed state."""
        config = RateLimitConfig(failure_threshold=3)
        circuit = CircuitBreaker(config)

        result = circuit.call(lambda: "success")
        assert result == "success"
        assert circuit.state == "closed"

    def test_open_after_threshold(self):
        """Circuit should open after failure threshold."""
        config = RateLimitConfig(failure_threshold=3, recovery_timeout=60)
        circuit = CircuitBreaker(config)

        for _ in range(3):
            try:
                circuit.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
            except RuntimeError:
                pass

        assert circuit.state == "open"

        with pytest.raises(RuntimeError, match="Circuit breaker OPEN"):
            circuit.call(lambda: "success")


class TestRequestThrottler:
    """Test request throttling."""

    def test_min_interval_enforced(self):
        """Throttler should enforce minimum interval between requests."""
        config = RateLimitConfig(min_request_interval=0.5, requests_per_minute=100)
        throttler = RequestThrottler(config)

        start = time.time()
        throttler.wait_if_needed()
        throttler.wait_if_needed()
        throttler.wait_if_needed()
        elapsed = time.time() - start

        assert elapsed >= 1.0


class TestRateLimitingDecorator:
    """Test the @with_rate_limiting decorator."""

    def test_decorator_caches_results(self):
        """Decorator should cache results for identical calls."""
        reset_rate_limiting()

        call_count = 0

        @with_rate_limiting
        def expensive_call(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_call(5)
        assert result1 == 10
        assert call_count == 1

        result2 = expensive_call(5)
        assert result2 == 10
        assert call_count == 1  # No additional call

    def test_decorator_retries_on_rate_limit(self):
        """Decorator should retry on rate limit errors."""
        reset_rate_limiting()

        attempt_count = 0

        @with_rate_limiting
        def failing_call():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise RuntimeError("429 rate limit exceeded")
            return "success"

        result = failing_call()
        assert result == "success"
        assert attempt_count == 3


class TestRateLimitConfig:
    """Test rate limit configuration."""

    def test_from_env_defaults(self, monkeypatch):
        """Config should use defaults when env vars not set."""
        for key in [
            "VIBESRAILS_CLAUDE_MAX_RETRIES",
            "VIBESRAILS_CLAUDE_CACHE_ENABLED",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = RateLimitConfig.from_env()
        assert config.max_retries == 3
        assert config.cache_enabled is True

    def test_from_env_custom(self, monkeypatch):
        """Config should load custom values from env."""
        monkeypatch.setenv("VIBESRAILS_CLAUDE_MAX_RETRIES", "5")
        monkeypatch.setenv("VIBESRAILS_CLAUDE_CACHE_ENABLED", "false")

        config = RateLimitConfig.from_env()
        assert config.max_retries == 5
        assert config.cache_enabled is False
