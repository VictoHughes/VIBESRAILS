"""Structured JSON logging for the VibesRails MCP server.

All output goes to stderr (stdout is reserved for MCP stdio transport).
Sensitive data (user text, file contents, full paths) is redacted.

Configuration via environment variables:
  VIBESRAILS_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default: INFO)
  VIBESRAILS_LOG_FILE: optional path to also write logs to a file
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import PurePosixPath, PureWindowsPath

# ── Redaction helpers ─────────────────────────────────────────────────

# Keys whose values contain user content and must be redacted.
_REDACT_CONTENT_KEYS = frozenset({
    "text", "brief", "content", "code", "code_snippet",
    "file_content", "source", "body", "prompt",
})

# Keys that contain filesystem paths — redact to basename only.
_PATH_KEYS = frozenset({
    "file_path", "project_path", "path", "rules",
})


def redact_value(key: str, value: object) -> object:
    """Redact a single key-value pair for safe logging.

    - Content keys: replaced with length indicator like "<512 chars>"
    - Path keys: replaced with basename only
    - Everything else: passed through unchanged
    """
    if key in _REDACT_CONTENT_KEYS:
        if isinstance(value, str):
            return f"<{len(value)} chars>"
        if isinstance(value, dict):
            return f"<dict with {len(value)} keys>"
        if isinstance(value, list):
            return f"<list with {len(value)} items>"
        return "<redacted>"

    if key in _PATH_KEYS and isinstance(value, str) and value:
        # Extract basename, handling both Unix and Windows paths
        name = PurePosixPath(value).name or PureWindowsPath(value).name
        return name if name else value

    return value


def redact_args(args: dict | None) -> dict:
    """Redact a tool arguments dict for safe logging."""
    if not args:
        return {}
    redacted = {}
    for key, value in args.items():
        redacted[key] = redact_value(key, value)
    return redacted


# ── JSON formatter ────────────────────────────────────────────────────


class _JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "tool": getattr(record, "tool", None),
            "event": record.getMessage(),
        }
        # Merge extra structured data if present
        data = getattr(record, "data", None)
        if data is not None:
            entry["data"] = data
        return json.dumps(entry, default=str, ensure_ascii=False)


# ── Logger setup ──────────────────────────────────────────────────────

_CONFIGURED = False


def _configure_root() -> None:
    """Configure the vibesrails root logger (idempotent)."""
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return
    _CONFIGURED = True

    root = logging.getLogger("vibesrails")

    # Level from env var
    level_name = os.environ.get("VIBESRAILS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)

    # Stderr handler (structured JSON)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(_JSONFormatter())
    root.addHandler(stderr_handler)

    # Optional file handler
    log_file = os.environ.get("VIBESRAILS_LOG_FILE")
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(_JSONFormatter())
        root.addHandler(file_handler)

    root.propagate = False


def get_logger(tool_name: str) -> logging.Logger:
    """Get a named logger under the vibesrails hierarchy.

    Args:
        tool_name: Name of the MCP tool (e.g. "scan_code").

    Returns:
        A Logger that inherits the vibesrails root configuration.
    """
    _configure_root()
    return logging.getLogger(f"vibesrails.{tool_name}")


# ── Tool call logging ─────────────────────────────────────────────────


def _log(
    tool_name: str,
    level: int,
    event: str,
    data: dict | None = None,
) -> None:
    """Internal: emit a structured log entry."""
    logger = get_logger(tool_name)
    logger.log(level, event, extra={"tool": tool_name, "data": data})


def log_tool_call(
    tool_name: str,
    arguments: dict | None,
    result_status: str,
    duration_ms: float,
) -> None:
    """Log a completed MCP tool call with redacted arguments.

    Args:
        tool_name: Name of the tool that was called.
        arguments: Raw arguments dict (will be redacted).
        result_status: Result status ("pass", "warn", "block", "error", "ok").
        duration_ms: Execution time in milliseconds.
    """
    _log(tool_name, logging.INFO, "tool_call_complete", {
        "args": redact_args(arguments),
        "status": result_status,
        "duration_ms": round(duration_ms, 1),
    })


def log_security_event(
    tool_name: str,
    event_type: str,
    detail: str,
) -> None:
    """Log a security-relevant event.

    Args:
        tool_name: Tool that triggered the event.
        event_type: Category (e.g. "path_traversal_blocked", "injection_detected").
        detail: Short description (must not contain user content).
    """
    _log(tool_name, logging.WARNING, "security_event", {
        "event_type": event_type, "detail": detail,
    })


def log_rate_limit(tool_name: str, retry_after: int) -> None:
    """Log a rate limit hit."""
    _log(tool_name, logging.WARNING, "rate_limited", {
        "retry_after_seconds": retry_after,
    })


def log_server_start(version: str, tools_count: int) -> None:
    """Log server startup."""
    _log("server", logging.INFO, "server_started", {
        "version": version, "tools_count": tools_count,
    })


def log_error(tool_name: str, error: str) -> None:
    """Log an unexpected error (message only, no stack trace to client)."""
    _log(tool_name, logging.ERROR, "unexpected_error", {"error": error})


# ── Timer context ─────────────────────────────────────────────────────


class tool_timer:
    """Context manager that measures tool execution time in milliseconds.

    Usage:
        with tool_timer() as t:
            result = do_work()
        elapsed = t.ms  # elapsed milliseconds
    """

    __slots__ = ("_start", "ms")

    def __enter__(self) -> tool_timer:
        self._start = time.monotonic()
        self.ms = 0.0
        return self

    def __exit__(self, *_: object) -> None:
        self.ms = (time.monotonic() - self._start) * 1000
