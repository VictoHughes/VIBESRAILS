"""Tests for core/logger.py — structured JSON logging with redaction."""

from __future__ import annotations

import json
import logging

import pytest

from core.logger import (
    get_logger,
    log_error,
    log_rate_limit,
    log_security_event,
    log_server_start,
    log_tool_call,
    redact_args,
    tool_timer,
)

# ── Fixture: capture structured log output ────────────────────────────


class _CaptureHandler(logging.Handler):
    """Handler that stores formatted log strings in a list."""

    def __init__(self):
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.format(record))


@pytest.fixture()
def log_capture():
    """Attach a capture handler to the vibesrails logger hierarchy."""
    from core.logger import _JSONFormatter

    handler = _CaptureHandler()
    handler.setFormatter(_JSONFormatter())

    root = logging.getLogger("vibesrails")
    original_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    yield handler

    root.removeHandler(handler)
    root.setLevel(original_level)


# ── get_logger ────────────────────────────────────────────────────────


def test_get_logger_returns_logger():
    """get_logger returns a standard Logger."""
    logger = get_logger("test_tool")
    assert isinstance(logger, logging.Logger)
    assert "vibesrails.test_tool" in logger.name


# ── JSON format ───────────────────────────────────────────────────────


def test_log_output_is_valid_json(log_capture):
    """Log output can be parsed as JSON."""
    log_tool_call("ping", {}, "ok", 1.5)
    assert len(log_capture.records) >= 1
    entry = json.loads(log_capture.records[-1])
    assert "timestamp" in entry
    assert "level" in entry
    assert "event" in entry


def test_log_contains_tool_and_data(log_capture):
    """Log entry contains tool name and data payload."""
    log_tool_call("scan_code", {"file_path": "/tmp/test.py"}, "pass", 42.3)
    entry = json.loads(log_capture.records[-1])
    assert entry["tool"] == "scan_code"
    assert entry["data"]["status"] == "pass"
    assert entry["data"]["duration_ms"] == 42.3


# ── Redaction: content keys ──────────────────────────────────────────


def test_redact_long_text():
    """Long text values are replaced with length indicator."""
    result = redact_args({"text": "A" * 1000})
    assert result["text"] == "<1000 chars>"


def test_redact_brief_dict():
    """Dict values for content keys show key count."""
    result = redact_args({"brief": {"intent": "x", "constraints": ["a"]}})
    assert result["brief"] == "<dict with 2 keys>"


def test_redact_content_list():
    """List values for content keys show item count."""
    result = redact_args({"content": ["line1", "line2", "line3"]})
    assert result["content"] == "<list with 3 items>"


def test_redact_code_snippet():
    """code_snippet key is redacted."""
    result = redact_args({"code_snippet": "def foo(): pass"})
    assert "def foo" not in result["code_snippet"]
    assert "chars>" in result["code_snippet"]


# ── Redaction: path keys ─────────────────────────────────────────────


def test_redact_file_path_to_basename():
    """Full file paths are redacted to basename only."""
    result = redact_args({"file_path": "/home/user/secret/project/main.py"})
    assert result["file_path"] == "main.py"
    assert "/home" not in str(result)


def test_redact_project_path_to_basename():
    """Project paths are redacted to basename."""
    result = redact_args({"project_path": "/Users/dev/myproject"})
    assert result["project_path"] == "myproject"


# ── Redaction: non-sensitive keys pass through ───────────────────────


def test_non_sensitive_keys_unchanged():
    """Keys not in redaction lists pass through unchanged."""
    result = redact_args({"action": "start", "max_level": 2, "guards": "all"})
    assert result == {"action": "start", "max_level": 2, "guards": "all"}


def test_redact_args_handles_none():
    """redact_args handles None gracefully."""
    assert redact_args(None) == {}


def test_redact_args_handles_empty():
    """redact_args handles empty dict."""
    assert redact_args({}) == {}


# ── log_tool_call ────────────────────────────────────────────────────


def test_log_tool_call_contains_required_fields(log_capture):
    """log_tool_call output contains tool, status, and duration."""
    log_tool_call("shield_prompt", {"text": "hello"}, "warn", 15.7)
    entry = json.loads(log_capture.records[-1])
    assert entry["tool"] == "shield_prompt"
    assert entry["event"] == "tool_call_complete"
    assert entry["data"]["status"] == "warn"
    assert entry["data"]["duration_ms"] == 15.7
    # Text should be redacted in args
    assert "hello" not in str(entry["data"]["args"])


def test_log_tool_call_no_crash_with_none_args(log_capture):
    """log_tool_call doesn't crash with args=None."""
    log_tool_call("ping", None, "ok", 0.1)
    entry = json.loads(log_capture.records[-1])
    assert entry["data"]["args"] == {}


# ── Log level control ────────────────────────────────────────────────


def test_debug_level_visible_when_set(log_capture, monkeypatch):
    """DEBUG messages appear when level is DEBUG."""
    root = logging.getLogger("vibesrails")
    root.setLevel(logging.DEBUG)
    logger = get_logger("test")
    logger.debug("debug_event", extra={"tool": "test", "data": None})
    found = any("debug_event" in r for r in log_capture.records)
    assert found


def test_info_hidden_at_error_level(log_capture):
    """INFO messages are suppressed when level is ERROR."""
    root = logging.getLogger("vibesrails")
    original = root.level
    root.setLevel(logging.ERROR)
    try:
        log_tool_call("ping", {}, "ok", 0.1)
        found = any("tool_call_complete" in r for r in log_capture.records)
        assert not found
    finally:
        root.setLevel(original)


# ── Helper functions ─────────────────────────────────────────────────


def test_log_security_event(log_capture):
    """log_security_event produces structured output."""
    log_security_event("scan_code", "path_traversal_blocked", "rejected /etc/passwd")
    entry = json.loads(log_capture.records[-1])
    assert entry["level"] == "WARNING"
    assert entry["data"]["event_type"] == "path_traversal_blocked"


def test_log_rate_limit(log_capture):
    """log_rate_limit logs retry_after."""
    log_rate_limit("ping", 30)
    entry = json.loads(log_capture.records[-1])
    assert entry["event"] == "rate_limited"
    assert entry["data"]["retry_after_seconds"] == 30


def test_log_server_start(log_capture):
    """log_server_start logs version and tool count."""
    log_server_start("0.1.0", 12)
    entry = json.loads(log_capture.records[-1])
    assert entry["data"]["version"] == "0.1.0"
    assert entry["data"]["tools_count"] == 12


def test_log_error(log_capture):
    """log_error produces ERROR level entry."""
    log_error("scan_code", "something went wrong")
    entry = json.loads(log_capture.records[-1])
    assert entry["level"] == "ERROR"
    assert entry["data"]["error"] == "something went wrong"


# ── tool_timer ───────────────────────────────────────────────────────


def test_tool_timer_measures_duration():
    """tool_timer records positive milliseconds."""
    with tool_timer() as t:
        total = sum(range(1000))  # noqa: F841
    assert t.ms > 0
    assert isinstance(t.ms, float)
