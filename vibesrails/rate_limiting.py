"""Rate limiting and retry configuration for Claude API in VibesRails.

Prevents rate limit errors with:
- Exponential backoff retry
- Circuit breaker pattern
- Request throttling
- Response caching
"""
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache, wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    # Retry settings
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0

    # Circuit breaker
    failure_threshold: int = 5  # failures before opening circuit
    recovery_timeout: int = 60  # seconds to wait before retry

    # Throttling
    requests_per_minute: int = 50  # Anthropic tier-dependent
    min_request_interval: float = 1.2  # seconds between requests (50/min)

    # Caching
    cache_ttl: int = 3600  # seconds (1 hour)
    cache_enabled: bool = True

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Load configuration from environment variables."""
        return cls(
            max_retries=int(os.getenv("VIBESRAILS_CLAUDE_MAX_RETRIES", "3")),
            initial_delay=float(os.getenv("VIBESRAILS_CLAUDE_INITIAL_DELAY", "1.0")),
            max_delay=float(os.getenv("VIBESRAILS_CLAUDE_MAX_DELAY", "60.0")),
            exponential_base=float(os.getenv("VIBESRAILS_CLAUDE_EXPONENTIAL_BASE", "2.0")),
            failure_threshold=int(os.getenv("VIBESRAILS_CLAUDE_FAILURE_THRESHOLD", "5")),
            recovery_timeout=int(os.getenv("VIBESRAILS_CLAUDE_RECOVERY_TIMEOUT", "60")),
            requests_per_minute=int(os.getenv("VIBESRAILS_CLAUDE_REQUESTS_PER_MINUTE", "50")),
            min_request_interval=float(os.getenv("VIBESRAILS_CLAUDE_MIN_REQUEST_INTERVAL", "1.2")),
            cache_ttl=int(os.getenv("VIBESRAILS_CLAUDE_CACHE_TTL", "3600")),
            cache_enabled=os.getenv("VIBESRAILS_CLAUDE_CACHE_ENABLED", "true").lower() == "true",
        )


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                logger.info("[CIRCUIT] Half-open: attempting reset")
            else:
                raise RuntimeError(
                    f"Circuit breaker OPEN. Wait {self.config.recovery_timeout}s. "
                    f"Last failure: {self.last_failure_time}"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time passed to attempt reset."""
        if not self.last_failure_time:
            return True
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout

    def _on_success(self):
        self.failure_count = 0
        self.state = "closed"
        self.last_failure_time = None

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.config.failure_threshold:
            self.state = "open"
            logger.error(f"[CIRCUIT] OPEN after {self.failure_count} failures")


class RequestThrottler:
    """Throttle requests to respect rate limits."""
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.last_request_time: float = 0
        self.request_times: list[float] = []

    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = time.time()

        # 1. Enforce minimum interval between requests
        time_since_last = now - self.last_request_time
        if time_since_last < self.config.min_request_interval:
            wait_time = self.config.min_request_interval - time_since_last
            logger.debug(f"[THROTTLE] Waiting {wait_time:.2f}s (min interval)")
            time.sleep(wait_time)  # vibesrails: ignore — intentional throttle delay
            now = time.time()

        # 2. Enforce requests per minute limit
        one_minute_ago = now - 60
        self.request_times = [t for t in self.request_times if t > one_minute_ago]

        if len(self.request_times) >= self.config.requests_per_minute:
            oldest = self.request_times[0]
            wait_time = 60 - (now - oldest) + 0.1
            logger.warning(
                f"[THROTTLE] Rate limit approaching: {len(self.request_times)}/{self.config.requests_per_minute} "
                f"requests in last minute. Waiting {wait_time:.2f}s"
            )
            time.sleep(wait_time)  # vibesrails: ignore — intentional rate limit delay
            now = time.time()

        self.last_request_time = now
        self.request_times.append(now)


class ResponseCache:
    """Cache API responses to reduce redundant calls."""
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._cache: dict[str, tuple[Any, float]] = {}

    def get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate cache key from function name and arguments."""
        key_data = {
            "func": func_name,
            "args": args,
            "kwargs": kwargs,
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        if not self.config.cache_enabled:
            return None

        if key in self._cache:
            value, timestamp = self._cache[key]
            age = time.time() - timestamp

            if age < self.config.cache_ttl:
                logger.debug(f"[CACHE] Hit (age: {age:.1f}s): {key}")
                return value
            else:
                del self._cache[key]
                logger.debug(f"[CACHE] Expired: {key}")

        return None

    def set(self, key: str, value: Any) -> None:
        """Cache value with timestamp."""
        if not self.config.cache_enabled:
            return

        self._cache[key] = (value, time.time())
        logger.debug(f"[CACHE] Set: {key}")

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        logger.info("[CACHE] Cleared")


# Global instances (singleton pattern)
_config: RateLimitConfig | None = None
_circuit_breaker: CircuitBreaker | None = None
_throttler: RequestThrottler | None = None
_cache: ResponseCache | None = None


@lru_cache()
def get_rate_limit_config() -> RateLimitConfig:
    """Get global rate limit configuration from environment variables."""
    global _config  # vibesrails: ignore — singleton pattern for rate limit config
    if _config is None:
        _config = RateLimitConfig.from_env()
    return _config


def get_circuit_breaker() -> CircuitBreaker:
    """Get global circuit breaker."""
    global _circuit_breaker  # vibesrails: ignore — singleton pattern
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker(get_rate_limit_config())
    return _circuit_breaker


def get_throttler() -> RequestThrottler:
    """Get global request throttler."""
    global _throttler  # vibesrails: ignore — singleton pattern
    if _throttler is None:
        _throttler = RequestThrottler(get_rate_limit_config())
    return _throttler


def get_cache() -> ResponseCache:
    """Get global response cache."""
    global _cache  # vibesrails: ignore — singleton pattern
    if _cache is None:
        _cache = ResponseCache(get_rate_limit_config())
    return _cache


_RATE_LIMIT_MARKERS = ("rate", "429", "too many requests", "quota")


def _is_rate_limit_error(error: Exception) -> bool:
    """Check if an exception is a rate limit error."""
    error_str = str(error).lower()
    return any(marker in error_str for marker in _RATE_LIMIT_MARKERS)


def with_rate_limiting(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator adding rate limiting, retry, caching to API calls."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        """Decorated function wrapper."""
        config = get_rate_limit_config()
        cache = get_cache()
        cache_key = cache.get_cache_key(func.__name__, *args, **kwargs)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        throttler = get_throttler()
        circuit_breaker = get_circuit_breaker()
        delay = config.initial_delay
        last_exception = None

        for attempt in range(config.max_retries + 1):
            try:
                throttler.wait_if_needed()
                result = circuit_breaker.call(func, *args, **kwargs)
                cache.set(cache_key, result)
                return result
            except Exception as e:
                last_exception = e
                if _is_rate_limit_error(e) and attempt < config.max_retries:
                    logger.warning(
                        "[RETRY] Rate limit hit (attempt %d/%d). Waiting %.1fs. Error: %s",
                        attempt + 1, config.max_retries, delay, e,
                    )
                    time.sleep(delay)  # vibesrails: ignore — intentional retry backoff
                    delay = min(delay * config.exponential_base, config.max_delay)
                else:
                    raise

        raise last_exception

    return wrapper

def reset_rate_limiting() -> None:
    """Reset all rate limiting state (for testing)."""
    global _circuit_breaker, _throttler, _cache  # vibesrails: ignore — test reset function
    _circuit_breaker = None
    _throttler = None
    if _cache:
        _cache.clear()
    _cache = None
    logger.info("[RATE_LIMIT] State reset")
