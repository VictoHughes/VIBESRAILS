"""Prompt Shield — prompt injection detection for text, code, and MCP inputs.

Detects 5 categories of prompt injection:
  1. system_override — ignore/bypass/override instructions
  2. role_hijack — reassign AI identity or behavior
  3. exfiltration — send data to external endpoints
  4. encoding_evasion — base64/hex/Unicode-hidden instructions
  5. delimiter_escape — LLM tokenizer delimiter injection

Reference: "Rules File Backdoor" attack (Pillar Security, March 2025).
"""

from __future__ import annotations

import base64
import binascii
import logging
from pathlib import Path

from core.prompt_shield_patterns import (
    _BASE64_RE,
    _BIDI_OVERRIDE,
    _DECODED_INJECTION_PATTERNS,
    _DELIMITER_ESCAPE_PATTERNS,
    _EXFILTRATION_PATTERNS,
    _ROLE_HIJACK_PATTERNS,
    _SYSTEM_OVERRIDE_PATTERNS,
    _TAG_RANGE,
    _ZERO_WIDTH,
    ShieldFinding,
)

# Re-export all pattern names so existing imports from core.prompt_shield still work
__all__ = [
    "ShieldFinding",
    "PromptShield",
    "_BASE64_RE",
    "_BIDI_OVERRIDE",
    "_DECODED_INJECTION_PATTERNS",
    "_DELIMITER_ESCAPE_PATTERNS",
    "_EXFILTRATION_PATTERNS",
    "_ROLE_HIJACK_PATTERNS",
    "_SYSTEM_OVERRIDE_PATTERNS",
    "_TAG_RANGE",
    "_ZERO_WIDTH",
    "_extract_strings",
    "_MAX_EXTRACT_DEPTH",
]

logger = logging.getLogger(__name__)


# ── PromptShield class ──────────────────────────────────────────────


class PromptShield:
    """Detects prompt injection in text, code files, and MCP inputs."""

    _MAX_TEXT_SIZE = 1 * 1024 * 1024  # 1 MB

    def scan_text(self, text: str) -> list[ShieldFinding]:
        """Scan arbitrary text for all 5 injection categories."""
        if len(text) > self._MAX_TEXT_SIZE:
            return [ShieldFinding(
                category="system_override",
                severity="block",
                message=f"Text too large ({len(text)} bytes). Maximum: {self._MAX_TEXT_SIZE} bytes.",
                line=0,
                matched_text="[oversized input]",
            )]
        findings: list[ShieldFinding] = []
        findings.extend(self._check_system_override(text))
        findings.extend(self._check_role_hijack(text))
        findings.extend(self._check_exfiltration(text))
        findings.extend(self._check_encoding_evasion(text))
        findings.extend(self._check_delimiter_escape(text))
        return findings

    def scan_file(self, file_path: str | Path) -> list[ShieldFinding]:
        """Read and scan a file for prompt injection."""
        from core.path_validator import PathValidationError, validate_path
        try:
            path = validate_path(str(file_path), must_exist=True, must_be_file=True)
        except PathValidationError as exc:
            return [ShieldFinding(
                category="system_override",
                severity="block",
                message=f"Path validation failed: {exc}",
                line=0,
                matched_text="[invalid path]",
            )]
        if path.stat().st_size > self._MAX_TEXT_SIZE:
            return [ShieldFinding(
                category="system_override",
                severity="block",
                message=f"File too large. Maximum: {self._MAX_TEXT_SIZE // (1024*1024)} MB.",
                line=0,
                matched_text="[oversized file]",
            )]
        content = path.read_text(encoding="utf-8", errors="replace")
        return self.scan_text(content)

    def scan_mcp_input(
        self, tool_name: str, arguments: dict,
    ) -> list[ShieldFinding]:
        """Scan MCP tool arguments for prompt injection.

        Recursively extracts all string values from arguments and scans each.
        """
        findings: list[ShieldFinding] = []

        for key, value in arguments.items():
            strings = _extract_strings(value)
            for text in strings:
                text_findings = self.scan_text(text)
                for f in text_findings:
                    f.context = f"tool={tool_name}, arg={key}"
                findings.extend(text_findings)

        return findings

    # ── Category checkers ────────────────────────────────────────────

    def _check_system_override(self, text: str) -> list[ShieldFinding]:
        return _scan_patterns(text, _SYSTEM_OVERRIDE_PATTERNS, "system_override", "block")

    def _check_role_hijack(self, text: str) -> list[ShieldFinding]:
        return _scan_patterns(text, _ROLE_HIJACK_PATTERNS, "role_hijack", "block")

    def _check_exfiltration(self, text: str) -> list[ShieldFinding]:
        return _scan_patterns(text, _EXFILTRATION_PATTERNS, "exfiltration", "block")

    def _check_delimiter_escape(self, text: str) -> list[ShieldFinding]:
        return _scan_patterns(text, _DELIMITER_ESCAPE_PATTERNS, "delimiter_escape", "block")

    def _check_encoding_evasion(self, text: str) -> list[ShieldFinding]:
        findings: list[ShieldFinding] = []
        findings.extend(self._check_invisible_unicode(text))
        findings.extend(self._check_encoded_instructions(text))
        return findings

    def _check_invisible_unicode(self, text: str) -> list[ShieldFinding]:
        findings: list[ShieldFinding] = []
        for line_num, line in enumerate(text.splitlines(), 1):
            for char_idx, char in enumerate(line):
                cp = ord(char)
                if cp in _TAG_RANGE:
                    findings.append(ShieldFinding(
                        category="encoding_evasion",
                        severity="block",
                        message=f"Unicode Tag U+{cp:04X} — hides instructions from humans",
                        line=line_num,
                        matched_text=f"U+{cp:04X} at position {char_idx}",
                        context=line.strip()[:80],
                    ))
                elif cp in _ZERO_WIDTH:
                    findings.append(ShieldFinding(
                        category="encoding_evasion",
                        severity="block",
                        message=f"Zero-width U+{cp:04X} — invisible to humans, read by LLMs",
                        line=line_num,
                        matched_text=f"U+{cp:04X} at position {char_idx}",
                        context=line.strip()[:80],
                    ))
                elif cp in _BIDI_OVERRIDE:
                    findings.append(ShieldFinding(
                        category="encoding_evasion",
                        severity="block",
                        message=f"Bidi override U+{cp:04X} — can reverse text display",
                        line=line_num,
                        matched_text=f"U+{cp:04X} at position {char_idx}",
                        context=line.strip()[:80],
                    ))
        return findings

    def _check_encoded_instructions(self, text: str) -> list[ShieldFinding]:
        findings: list[ShieldFinding] = []
        for line_num, line in enumerate(text.splitlines(), 1):
            for match in _BASE64_RE.finditer(line):
                candidate = match.group(0)
                try:
                    decoded = base64.b64decode(candidate).decode(
                        "utf-8", errors="ignore",
                    )
                except (binascii.Error, ValueError):
                    continue

                for injection_pat in _DECODED_INJECTION_PATTERNS:
                    if injection_pat.search(decoded):
                        findings.append(ShieldFinding(
                            category="encoding_evasion",
                            severity="block",
                            message="Base64-encoded injection — decodes to suspicious instruction",
                            line=line_num,
                            matched_text=candidate[:40] + ("..." if len(candidate) > 40 else ""),
                            context="[base64 injection detected - content redacted]",
                        ))
                        break  # one finding per base64 string
        return findings


# ── Helpers ──────────────────────────────────────────────────────────


def _scan_patterns(
    text: str,
    patterns: list[tuple],
    category: str,
    severity: str,
) -> list[ShieldFinding]:
    """Scan text line-by-line against a set of regex patterns."""
    findings: list[ShieldFinding] = []
    for line_num, line in enumerate(text.splitlines(), 1):
        for pattern, message in patterns:
            for match in pattern.finditer(line):
                findings.append(ShieldFinding(
                    category=category,
                    severity=severity,
                    message=message,
                    line=line_num,
                    matched_text=match.group(0),
                    context=line.strip(),
                ))
    return findings


_MAX_EXTRACT_DEPTH = 50


def _extract_strings(value: object, _depth: int = 0) -> list[str]:
    """Recursively extract all string values from a nested structure.

    Stops at _MAX_EXTRACT_DEPTH to prevent stack overflow on deeply
    nested attacker-crafted payloads.
    """
    if _depth > _MAX_EXTRACT_DEPTH:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_extract_strings(item, _depth + 1))
        return result
    if isinstance(value, dict):
        result = []
        for v in value.values():
            result.extend(_extract_strings(v, _depth + 1))
        return result
    return []
