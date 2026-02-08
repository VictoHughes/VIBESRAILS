"""ReDoS (Regular Expression Denial of Service) tests.

For every compiled regex in prompt_shield.py, config_shield.py, and
brief_enforcer.py, sends a 100,000-character adversarial input designed
to trigger catastrophic backtracking. Each test must complete in < 1 second.
"""

from __future__ import annotations

import time

# ── brief_enforcer patterns ─────────────────────────────────────────
from core.brief_enforcer import _VAGUE_PATTERNS

# ── config_shield patterns ──────────────────────────────────────────
from core.config_shield import (
    _CONTRADICTION_PATTERNS,
    _SECURITY_OVERRIDE_PATTERNS,
)
from core.config_shield import (
    _EXFILTRATION_PATTERNS as _CS_EXFILTRATION_PATTERNS,
)

# ── prompt_shield patterns ──────────────────────────────────────────
from core.prompt_shield import (
    _BASE64_RE,
    _DELIMITER_ESCAPE_PATTERNS,
    _EXFILTRATION_PATTERNS,
    _ROLE_HIJACK_PATTERNS,
    _SYSTEM_OVERRIDE_PATTERNS,
)

_TIMEOUT = 1.0  # seconds


def _time_regex(pattern, text: str) -> float:
    """Run a regex search and return elapsed time."""
    start = time.monotonic()
    pattern.search(text)
    return time.monotonic() - start


# ── Prompt Shield: system_override patterns ─────────────────────────


def test_system_override_no_redos():
    """System override patterns resist 100K adversarial input."""
    # Adversarial: lots of spaces between words that almost match
    evil = ("ignore " + " " * 99_990 + "x")
    for pattern, _msg in _SYSTEM_OVERRIDE_PATTERNS:
        elapsed = _time_regex(pattern, evil)
        assert elapsed < _TIMEOUT, f"ReDoS in system_override pattern: {pattern.pattern} ({elapsed:.2f}s)"


# ── Prompt Shield: role_hijack patterns ─────────────────────────────


def test_role_hijack_no_redos():
    """Role hijack patterns resist 100K adversarial input."""
    evil = "you are now " + "a " * 50_000
    for pattern, _msg in _ROLE_HIJACK_PATTERNS:
        elapsed = _time_regex(pattern, evil)
        assert elapsed < _TIMEOUT, f"ReDoS in role_hijack pattern: {pattern.pattern} ({elapsed:.2f}s)"


# ── Prompt Shield: exfiltration patterns ────────────────────────────


def test_exfiltration_no_redos():
    """Exfiltration patterns resist 100K adversarial input."""
    evil = "send the " + "code " * 25_000
    for pattern, _msg in _EXFILTRATION_PATTERNS:
        elapsed = _time_regex(pattern, evil)
        assert elapsed < _TIMEOUT, f"ReDoS in exfiltration pattern: {pattern.pattern} ({elapsed:.2f}s)"


# ── Prompt Shield: delimiter_escape patterns ────────────────────────


def test_delimiter_escape_no_redos():
    """Delimiter escape patterns resist 100K adversarial input."""
    evil = "<|" + "x" * 100_000 + "|>"
    for pattern, _msg in _DELIMITER_ESCAPE_PATTERNS:
        elapsed = _time_regex(pattern, evil)
        assert elapsed < _TIMEOUT, f"ReDoS in delimiter_escape pattern: {pattern.pattern} ({elapsed:.2f}s)"


# ── Prompt Shield: base64 pattern ──────────────────────────────────


def test_base64_pattern_no_redos():
    """Base64 regex resists 100K adversarial input."""
    evil = "A" * 100_000 + "=="
    elapsed = _time_regex(_BASE64_RE, evil)
    assert elapsed < _TIMEOUT, f"ReDoS in base64 pattern ({elapsed:.2f}s)"


# ── Config Shield patterns ──────────────────────────────────────────


def test_config_shield_no_redos():
    """config_shield patterns resist 100K adversarial input."""
    evil = "ignore " + "previous " * 12_500
    all_patterns = (
        _CONTRADICTION_PATTERNS
        + _CS_EXFILTRATION_PATTERNS
        + _SECURITY_OVERRIDE_PATTERNS
    )
    for pattern, _msg in all_patterns:
        elapsed = _time_regex(pattern, evil)
        assert elapsed < _TIMEOUT, f"ReDoS in config_shield pattern: {pattern.pattern} ({elapsed:.2f}s)"


# ── Brief Enforcer vague patterns ──────────────────────────────────


def test_brief_enforcer_vague_no_redos():
    """brief_enforcer vague patterns resist 100K adversarial input."""
    evil = "fix " + "it " * 33_333
    for pattern in _VAGUE_PATTERNS:
        elapsed = _time_regex(pattern, evil)
        assert elapsed < _TIMEOUT, f"ReDoS in brief_enforcer pattern: {pattern.pattern} ({elapsed:.2f}s)"


# ── Mixed adversarial: alternating partial matches ──────────────────


def test_alternating_partial_matches_no_redos():
    """Alternating near-matches don't cause backtracking in any pattern."""
    # This pattern is designed to partially match many patterns repeatedly
    evil = "ignore previous " * 6250  # 100K chars of repeated near-match
    for pattern, _msg in _SYSTEM_OVERRIDE_PATTERNS:
        elapsed = _time_regex(pattern, evil)
        assert elapsed < _TIMEOUT, f"ReDoS in alternating partial match: {pattern.pattern} ({elapsed:.2f}s)"
