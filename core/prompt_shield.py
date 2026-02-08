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
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Finding dataclass ────────────────────────────────────────────────


@dataclass
class ShieldFinding:
    """A prompt injection finding."""

    category: str  # system_override | role_hijack | exfiltration | encoding_evasion | delimiter_escape
    severity: str  # block | warn
    message: str
    line: int
    matched_text: str
    context: str = ""


# ── System Override patterns ─────────────────────────────────────────

_SYSTEM_OVERRIDE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"ignore\s+(?:previous|all|any|the\s+above|prior)\s+"
            r"(?:instructions?|rules?|guidelines?|constraints?|directions?)",
            re.I,
        ),
        "Instructs AI to ignore previous instructions",
    ),
    (
        re.compile(
            r"disregard\s+(?:previous|all|any|the)\s+"
            r"(?:instructions?|rules?|context|guidelines?)",
            re.I,
        ),
        "Instructs AI to disregard instructions",
    ),
    (
        re.compile(
            r"forget\s+(?:everything|all\s+(?:previous|prior)|"
            r"what\s+you\s+(?:know|were\s+told)|your\s+(?:instructions?|rules?))",
            re.I,
        ),
        "Instructs AI to forget context",
    ),
    (
        re.compile(
            r"(?:do\s+not|don'?t|never)\s+(?:tell|inform|alert|notify)\s+"
            r"the\s+(?:user|human|developer)",
            re.I,
        ),
        "Instructs AI to hide information from user",
    ),
    (
        re.compile(
            r"(?:never|don'?t|do\s+not)\s+(?:report|flag|warn|alert|mention)\s+"
            r"(?:about\s+)?(?:any\s+)?"
            r"(?:security|issues?|findings?|vulnerabilit(?:y|ies)|errors?|problems?)",
            re.I,
        ),
        "Instructs AI to suppress security findings",
    ),
    (
        re.compile(
            r"(?:skip|disable|turn\s+off|bypass|override)\s+(?:all\s+)?"
            r"(?:security|safety|validation|guardrails?|protections?|checks?)\b",
            re.I,
        ),
        "Instructs AI to bypass security controls",
    ),
    (
        re.compile(
            r"override\s+(?:all|any|the|previous|system)\s+"
            r"(?:rules?|constraints?|policies?|settings?|limits?)",
            re.I,
        ),
        "Instructs AI to override system rules",
    ),
]

# ── Role Hijack patterns ────────────────────────────────────────────

_ROLE_HIJACK_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"you\s+are\s+now\s+(?:a\s+|an?\s+)?", re.I),
        "Role hijacking: reassigns AI identity",
    ),
    (
        re.compile(
            r"(?:act|pretend|behave)\s+as\s+"
            r"(?:if\s+you\s+(?:are|were)|a\s+|an\s+)",
            re.I,
        ),
        "Role hijacking: attempts to change AI behavior",
    ),
    (
        re.compile(
            r"your\s+(?:new\s+)?(?:role|task|purpose|objective|mission)\s+is\b",
            re.I,
        ),
        "Role hijacking: redefines AI purpose",
    ),
    (
        re.compile(
            r"from\s+now\s+on\s+(?:you|your)\s+(?:are|will|must|should)",
            re.I,
        ),
        "Role hijacking: attempts permanent behavior change",
    ),
]

# ── Exfiltration patterns ───────────────────────────────────────────

_EXFILTRATION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"(?:curl|wget|http\.get|requests\.(?:get|post)|"
            r"urllib\.request\.urlopen)\s*\(?\s*['\"]https?://",
            re.I,
        ),
        "Exfiltration: code targets external URL",
    ),
    (
        re.compile(
            r"(?:send|upload|post|transmit|exfiltrate)\s+(?:the\s+)?"
            r"(?:code|context|source|file|data|content|token|key|secret|"
            r"credential|env(?:ironment)?)\s+(?:to|via|through)",
            re.I,
        ),
        "Exfiltration: instructs sending sensitive data externally",
    ),
    (
        re.compile(r"(?:webhook|callback|endpoint)\s*[=:]\s*['\"]?https?://", re.I),
        "Exfiltration: defines external callback URL",
    ),
    (
        re.compile(
            r"(?:subprocess|os\.system|os\.popen)\s*\(.*(?:curl|wget|nc\s)",
            re.I,
        ),
        "Exfiltration: subprocess with network command",
    ),
]

# ── Delimiter Escape patterns ───────────────────────────────────────

_DELIMITER_ESCAPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"</tool_(?:result|use|call)>"),
        "Delimiter escape: MCP/tool result injection",
    ),
    (
        re.compile(
            r"<\|(?:im_start|im_end|system|user|assistant|endoftext)\|>"
        ),
        "Delimiter escape: ChatML delimiter injection",
    ),
    (
        re.compile(r"\[/?INST\]"),
        "Delimiter escape: Llama instruction delimiter",
    ),
    (
        re.compile(r"<</?SYS>>"),
        "Delimiter escape: Llama system delimiter",
    ),
    (
        re.compile(r"<\|(?:begin|end)_of_(?:text|turn)\|>"),
        "Delimiter escape: special token injection",
    ),
]

# ── Invisible Unicode ranges ────────────────────────────────────────

_TAG_RANGE = range(0xE0001, 0xE0080)

_ZERO_WIDTH = {
    0x200B, 0x200C, 0x200D, 0xFEFF, 0x2060,
    0x2061, 0x2062, 0x2063, 0x2064,
}

_BIDI_OVERRIDE = {
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    0x2066, 0x2067, 0x2068, 0x2069,
}

# ── Base64 detection ────────────────────────────────────────────────

_BASE64_RE = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")

_DECODED_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(?:previous|all|any)\s+(?:instructions?|rules?)", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"(?:act|pretend)\s+as\s+", re.I),
    re.compile(r"(?:bypass|override)\s+(?:security|safety)", re.I),
    re.compile(r"(?:do\s+not|don'?t)\s+tell\s+the\s+user", re.I),
    re.compile(r"disregard\s+(?:previous|all)\s+", re.I),
]


# ── PromptShield class ──────────────────────────────────────────────


class PromptShield:
    """Detects prompt injection in text, code files, and MCP inputs."""

    _MAX_TEXT_SIZE = 10 * 1024 * 1024  # 10 MB

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
        path = Path(file_path)
        if path.stat().st_size > self._MAX_TEXT_SIZE:
            return [ShieldFinding(
                category="system_override",
                severity="block",
                message=f"File too large. Maximum: {self._MAX_TEXT_SIZE // (1024*1024)} MB.",
                line=0,
                matched_text="[oversized file]",
            )]
        content = path.read_text(encoding="utf-8")
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
    patterns: list[tuple[re.Pattern, str]],
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
