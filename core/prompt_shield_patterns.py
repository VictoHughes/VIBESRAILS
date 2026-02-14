"""Prompt Shield pattern definitions — regex patterns and constants.

Extracted from prompt_shield.py to keep modules under 300 lines.
All pattern lists and the ShieldFinding dataclass live here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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
            r"(?:subprocess|os\.system|os\.popen)\s*\([^)]*(?:curl|wget|nc\s)",
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
