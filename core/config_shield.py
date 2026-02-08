"""AI Config Shield — detects malicious content in AI configuration files.

Scans .cursorrules, CLAUDE.md, .github/copilot-instructions.md, and other
AI tool config files for hidden Unicode, prompt injection, exfiltration
attempts, and security override instructions.

Reference: "Rules File Backdoor" attack (Pillar Security, March 2025).
"""

from __future__ import annotations

import glob
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Finding dataclass ─────────────────────────────────────────────────


@dataclass
class ConfigFinding:
    """A finding from a config shield check."""

    check_type: str  # invisible_unicode | contradictory | exfiltration | security_override
    severity: str  # block | warn | info
    message: str
    file: str
    line: int
    matched_text: str


# ── AI config file patterns ──────────────────────────────────────────

AI_CONFIG_PATTERNS: list[str] = [
    ".cursorrules",
    ".cursor/rules/*.mdc",
    "CLAUDE.md",
    ".claude/settings.json",
    ".github/copilot-instructions.md",
    "mcp.json",
    ".mcp.json",
    ".continue/config.json",
    ".windsurfrules",
    ".clinerules",
]


# ── Invisible Unicode ranges ──────────────────────────────────────────

# Unicode Tags (U+E0001 to U+E007F) — encode ASCII as invisible tags
_TAG_RANGE = range(0xE0001, 0xE0080)

# Zero-width characters
_ZERO_WIDTH = {
    0x200B,  # Zero Width Space
    0x200C,  # Zero Width Non-Joiner
    0x200D,  # Zero Width Joiner
    0xFEFF,  # Zero Width No-Break Space (BOM)
    0x2060,  # Word Joiner
    0x2061,  # Function Application
    0x2062,  # Invisible Times
    0x2063,  # Invisible Separator
    0x2064,  # Invisible Plus
}

# Bidirectional override characters
_BIDI_OVERRIDE = {
    0x202A,  # Left-to-Right Embedding
    0x202B,  # Right-to-Left Embedding
    0x202C,  # Pop Directional Formatting
    0x202D,  # Left-to-Right Override
    0x202E,  # Right-to-Left Override
    0x2066,  # Left-to-Right Isolate
    0x2067,  # Right-to-Left Isolate
    0x2068,  # First Strong Isolate
    0x2069,  # Pop Directional Isolate
}


# ── Contradiction patterns ────────────────────────────────────────────

_CONTRADICTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"ignore\s+(previous|all|any)\s+(instructions?|rules?|guidelines?)", re.I),
     "Prompt injection: instructs AI to ignore previous instructions"),
    (re.compile(r"disregard\s+(previous|all|any|the)\s+(instructions?|rules?|context)", re.I),
     "Prompt injection: instructs AI to disregard instructions"),
    (re.compile(r"forget\s+(everything|all|previous|what)", re.I),
     "Prompt injection: instructs AI to forget context"),
    (re.compile(r"you\s+are\s+now\s+", re.I),
     "Role hijacking: attempts to reassign AI identity"),
    (re.compile(r"(?:act|pretend|behave)\s+as\s+(?:if\s+you\s+(?:are|were)|a\s+)", re.I),
     "Role hijacking: attempts to change AI behavior"),
    (re.compile(r"do\s+not\s+tell\s+the\s+user", re.I),
     "Concealment: instructs AI to hide information from user"),
    (re.compile(r"(?:hide|conceal|don'?t\s+(?:show|reveal|mention))\s+(?:this|these|the\s+(?:error|warning|issue))", re.I),
     "Concealment: instructs AI to suppress findings"),
    (re.compile(r"(?:never|don'?t)\s+(?:report|flag|warn|alert)\s+(?:about|on|for)", re.I),
     "Suppression: instructs AI to not report issues"),
]


# ── Exfiltration patterns ─────────────────────────────────────────────

_EXFILTRATION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?:fetch|curl|wget|http\.get|requests\.(?:get|post))\s*\(?\s*['\"]https?://", re.I),
     "Exfiltration: instructs to fetch/send data to external URL"),
    (re.compile(r"(?:send|upload|post|transmit|exfiltrate)\s+(?:the\s+)?(?:code|context|file|data|content|source|token|key|secret)\s+(?:to|via|through)", re.I),
     "Exfiltration: instructs to send code/data externally"),
    (re.compile(r"(?:webhook|callback|endpoint)[:\s]+https?://", re.I),
     "Exfiltration: defines external webhook/callback URL"),
    (re.compile(r"https?://(?!(?:github\.com|docs\.|stackoverflow\.com|pypi\.org|npmjs\.com|localhost|127\.0\.0\.1)\b)\S+\.(?:php|asp|cgi)\b", re.I),
     "Suspicious URL: points to dynamic server-side script"),
]


# ── Security override patterns ────────────────────────────────────────

_SECURITY_OVERRIDE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?:skip|disable|turn\s+off|bypass|ignore)\s+(?:security|safety|validation|auth|ssl|tls|certificate)", re.I),
     "Security override: instructs to bypass security checks"),
    (re.compile(r"(?:allow|trust|accept|permit)\s+(?:all|any|everything|every)\b", re.I),
     "Security override: removes restrictions"),
    (re.compile(r"no\s+(?:restrictions?|validation|verification|security|checks?|limits?)\b", re.I),
     "Security override: disables restrictions"),
    (re.compile(r"(?:hardcode|hard[\s-]?code)\s+(?:the\s+)?(?:password|secret|key|token|credential)", re.I),
     "Security override: instructs to hardcode credentials"),
    (re.compile(r"(?:use|add|write)\s+(?:eval|exec)\s*\(", re.I),
     "Security override: instructs to use dangerous eval/exec"),
    (re.compile(r"--no[\s-]?verify\b", re.I),
     "Security override: instructs to skip verification"),
]


# ── ConfigShield class ────────────────────────────────────────────────


class ConfigShield:
    """Scans AI configuration files for malicious content."""

    def find_config_files(self, project_path: str | Path) -> list[Path]:
        """Find all AI config files in a project directory."""
        root = Path(project_path)
        found: list[Path] = []

        for pattern in AI_CONFIG_PATTERNS:
            if "*" in pattern:
                # Glob pattern
                for match in glob.glob(str(root / pattern)):
                    p = Path(match)
                    if p.is_file():
                        found.append(p)
            else:
                p = root / pattern
                if p.is_file():
                    found.append(p)

        return sorted(set(found))

    def check_invisible_unicode(self, content: str, filepath: str) -> list[ConfigFinding]:
        """Detect invisible Unicode characters that can hide LLM instructions."""
        findings: list[ConfigFinding] = []

        for line_num, line in enumerate(content.splitlines(), 1):
            for char_idx, char in enumerate(line):
                cp = ord(char)

                if cp in _TAG_RANGE:
                    findings.append(ConfigFinding(
                        check_type="invisible_unicode",
                        severity="block",
                        message=f"Unicode Tag character U+{cp:04X} detected — can hide LLM instructions",
                        file=filepath,
                        line=line_num,
                        matched_text=f"U+{cp:04X} at position {char_idx}",
                    ))
                elif cp in _ZERO_WIDTH:
                    findings.append(ConfigFinding(
                        check_type="invisible_unicode",
                        severity="block",
                        message=f"Zero-width character U+{cp:04X} detected — invisible to humans, read by LLMs",
                        file=filepath,
                        line=line_num,
                        matched_text=f"U+{cp:04X} at position {char_idx}",
                    ))
                elif cp in _BIDI_OVERRIDE:
                    findings.append(ConfigFinding(
                        check_type="invisible_unicode",
                        severity="block",
                        message=f"Bidirectional override U+{cp:04X} detected — can reverse text display",
                        file=filepath,
                        line=line_num,
                        matched_text=f"U+{cp:04X} at position {char_idx}",
                    ))

        return findings

    def check_contradictory_instructions(self, content: str, filepath: str) -> list[ConfigFinding]:
        """Detect prompt injection and contradiction patterns."""
        findings: list[ConfigFinding] = []

        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern, message in _CONTRADICTION_PATTERNS:
                match = pattern.search(line)
                if match:
                    findings.append(ConfigFinding(
                        check_type="contradictory",
                        severity="block",
                        message=message,
                        file=filepath,
                        line=line_num,
                        matched_text=match.group(0),
                    ))

        return findings

    def check_exfiltration(self, content: str, filepath: str) -> list[ConfigFinding]:
        """Detect data exfiltration instructions."""
        findings: list[ConfigFinding] = []

        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern, message in _EXFILTRATION_PATTERNS:
                match = pattern.search(line)
                if match:
                    findings.append(ConfigFinding(
                        check_type="exfiltration",
                        severity="block",
                        message=message,
                        file=filepath,
                        line=line_num,
                        matched_text=match.group(0),
                    ))

        return findings

    def check_security_overrides(self, content: str, filepath: str) -> list[ConfigFinding]:
        """Detect instructions that weaken security guardrails."""
        findings: list[ConfigFinding] = []

        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern, message in _SECURITY_OVERRIDE_PATTERNS:
                match = pattern.search(line)
                if match:
                    findings.append(ConfigFinding(
                        check_type="security_override",
                        severity="warn",
                        message=message,
                        file=filepath,
                        line=line_num,
                        matched_text=match.group(0),
                    ))

        return findings

    def scan_content(self, content: str, filepath: str) -> list[ConfigFinding]:
        """Run all checks on a single file's content."""
        findings: list[ConfigFinding] = []
        findings.extend(self.check_invisible_unicode(content, filepath))
        findings.extend(self.check_contradictory_instructions(content, filepath))
        findings.extend(self.check_exfiltration(content, filepath))
        findings.extend(self.check_security_overrides(content, filepath))
        return findings

    def scan_project(self, project_path: str | Path) -> dict:
        """Scan all AI config files in a project.

        Returns:
            Dict with files_scanned, files_found, findings.
        """
        config_files = self.find_config_files(project_path)

        all_findings: list[ConfigFinding] = []
        files_scanned: list[str] = []

        for config_file in config_files:
            try:
                content = config_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            filepath_str = str(config_file)
            files_scanned.append(filepath_str)
            all_findings.extend(self.scan_content(content, filepath_str))

        return {
            "files_scanned": files_scanned,
            "files_found": len(files_scanned),
            "findings": all_findings,
        }
