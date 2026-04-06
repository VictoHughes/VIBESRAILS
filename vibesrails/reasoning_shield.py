"""Reasoning Shield — CCS v2 certificate validation and hook integrity.

Three protection surfaces:
A. Hook integrity: verify .claude/hooks.json against generated baseline
B. Certificate validation: structural check of PREMISES→TRACE→CONCLUSION
C. Reasoning manipulation: detect attempts to bypass logical reasoning

Reference: CCS v2 (KIONOS, 2025-2026), Semi-Formal Reasoning (Meta, arXiv:2603.01896).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# ── Data classes ─────────────────────────────────────────────────────


@dataclass
class IntegrityFinding:
    """A hook integrity finding."""

    severity: str  # block | warn
    message: str


@dataclass
class CertificateFinding:
    """A certificate validation finding."""

    gate: str  # gate_1 | gate_2 | gate_3
    severity: str  # block | warn
    message: str


@dataclass
class CertificateResult:
    """Result of validating a CCS v2 certificate."""

    valid: bool
    phases_found: int  # 0-3
    confidence: str  # FORT/STRONG | MOYEN/MEDIUM | FAIBLE/WEAK | ""
    has_hypotheses: bool = False
    findings: list[CertificateFinding] = field(default_factory=list)


@dataclass
class ManipulationFinding:
    """A reasoning manipulation finding."""

    category: str  # reasoning_manipulation
    severity: str  # block
    message: str
    line: int
    matched_text: str


# ── A. Hook Integrity ────────────────────────────────────────────────


def verify_hook_integrity(root: Path) -> list[IntegrityFinding]:
    """Compare .claude/hooks.json against generated full-tier baseline.

    Detects: missing hooks.json, removed event types, removed command hooks.
    Does NOT flag additions (user customization is allowed).
    """
    hooks_path = root / ".claude" / "hooks.json"
    if not hooks_path.exists():
        return [IntegrityFinding(
            severity="block",
            message="hooks.json missing — run vibesrails --init-hooks full",
        )]

    try:
        current = json.loads(hooks_path.read_text())
    except (json.JSONDecodeError, OSError):
        return [IntegrityFinding(
            severity="block",
            message="hooks.json is malformed — cannot parse JSON",
        )]

    from vibesrails.hook_generator import build_hooks

    baseline = build_hooks("full")
    findings: list[IntegrityFinding] = []

    # Check: all baseline event types present
    baseline_events = set(baseline.get("hooks", {}).keys())
    current_events = set(current.get("hooks", {}).keys())
    for missing_event in baseline_events - current_events:
        findings.append(IntegrityFinding(
            severity="block",
            message=f"Event type '{missing_event}' removed from hooks.json",
        ))

    # Check: all baseline command hooks still present (by command substring)
    for event_type in baseline_events & current_events:
        baseline_cmds = _extract_command_strings(baseline["hooks"][event_type])
        current_cmds = _extract_command_strings(current["hooks"][event_type])
        for cmd in baseline_cmds:
            # Match by significant substring (module name)
            module = _extract_module_ref(cmd)
            if module and not any(module in c for c in current_cmds):
                findings.append(IntegrityFinding(
                    severity="warn",
                    message=f"Command hook removed from {event_type}: ...{module}...",
                ))

    return findings


def _extract_command_strings(hook_list: list) -> list[str]:
    """Extract all command strings from a hook event list."""
    commands = []
    for entry in hook_list:
        if isinstance(entry, dict):
            for h in entry.get("hooks", []):
                if isinstance(h, dict) and h.get("type") == "command":
                    commands.append(h.get("command", ""))
    return commands


def _extract_module_ref(command: str) -> str:
    """Extract the vibesrails module reference from a hook command."""
    match = re.search(r"vibesrails\.[\w.]+", command)
    if match:
        return match.group(0)
    match = re.search(r"vibesrails\s+--[\w-]+", command)
    if match:
        return match.group(0)
    return ""


# ── B. Certificate Validation ────────────────────────────────────────

# Section detection patterns (FR + EN)
_PREMISES_RE = re.compile(
    r"(?:PR[ÉE]MISSES?|PREMISES?|P1[.\s]|CE QUE JE SAIS|WHAT I KNOW|Sais\s*:)",
    re.I,
)
_TRACE_RE = re.compile(
    r"(?:TRACE|T1[.\s:]|CHA[ÎI]NE CAUSALE|CAUSAL CHAIN)",
    re.I,
)
_CONCLUSION_RE = re.compile(
    r"(?:CONCLUSION|C1[.\s:]|(?:^|[│├└\-\s]{2})R[ÉE]PONSE\s*:|(?:^|[│├└\-\s]{2})ANSWER\s*:)",
    re.I | re.MULTILINE,
)

# Confidence detection
_CONFIDENCE_RE = re.compile(
    r"(?:Confiance|Confidence)\s*:\s*(FORT|STRONG|MOYEN|MEDIUM|FAIBLE|WEAK)",
    re.I,
)

# Hypothesis tag
_HYPOTHESIS_RE = re.compile(r"\[HYPOTH[ÈE]SE\]|\[HYPOTHESIS\]", re.I)

# Gate 1: empty premises indicators
_EMPTY_P1_RE = re.compile(
    r"(?:nothing\s+specific|rien\s+de\s+sourc|je\s+ne\s+sais\s+rien|no\s+sources?)",
    re.I,
)

# Gate 2: contradiction in trace
_CONTRADICTION_RE = re.compile(
    r"(?:CONTRADICTION|contradiction\s+(?:interne|found|detected|—))",
    re.I,
)

# Gate 3: new concept markers in conclusion (heuristic)
_NEW_CONCEPT_MARKERS = re.compile(
    r"(?:also\s+add|should\s+also|we\s+should\s+additionally|"
    r"il\s+faudrait\s+aussi|on\s+devrait\s+aussi|"
    r"machine\s+learning|AI-based|neural|deep\s+learning|"
    r"new\s+feature|nouvelle\s+fonctionnalit)",
    re.I,
)


def validate_certificate(text: str) -> CertificateResult:
    """Validate structural compliance of a CCS v2 certificate.

    Checks:
    - 3 phases present (PREMISES, TRACE, CONCLUSION)
    - Gate 1: P1 has sourced content (not empty)
    - Gate 2: No unresolved contradiction in trace
    - Gate 3: Conclusion doesn't introduce concepts absent from trace
    - Confidence level extracted
    - Hypothesis tags detected
    """
    findings: list[CertificateFinding] = []
    phases_found = 0

    has_premises = bool(_PREMISES_RE.search(text))
    has_trace = bool(_TRACE_RE.search(text))
    has_conclusion = bool(_CONCLUSION_RE.search(text))

    if has_premises:
        phases_found += 1
    if has_trace:
        phases_found += 1
    if has_conclusion:
        phases_found += 1

    # No certificate at all
    if phases_found == 0:
        return CertificateResult(valid=False, phases_found=0, confidence="")

    # Gate 1: empty premises
    if has_premises and _EMPTY_P1_RE.search(text):
        findings.append(CertificateFinding(
            gate="gate_1",
            severity="block",
            message="Gate 1 — Premises empty: P1 has no sourced facts",
        ))

    # Gate 2: broken trace (contradiction without resolution)
    if has_trace and _CONTRADICTION_RE.search(text):
        # Check if contradiction is in trace section but conclusion ignores it
        # Heuristic: if "contradiction" appears AND confidence is STRONG/FORT → broken
        confidence_match = _CONFIDENCE_RE.search(text)
        if confidence_match:
            conf = confidence_match.group(1).upper()
            if conf in ("FORT", "STRONG"):
                findings.append(CertificateFinding(
                    gate="gate_2",
                    severity="block",
                    message="Gate 2 — Trace broken: contradiction detected but confidence is STRONG",
                ))
        else:
            findings.append(CertificateFinding(
                gate="gate_2",
                severity="block",
                message="Gate 2 — Trace broken: unresolved contradiction detected",
            ))

    # Gate 3: orphan conclusion (introduces new concepts)
    if has_conclusion:
        # Split text into trace and conclusion sections
        conclusion_text = _extract_section_after(text, _CONCLUSION_RE)
        trace_text = _extract_section_between(text, _TRACE_RE, _CONCLUSION_RE)
        if conclusion_text and _NEW_CONCEPT_MARKERS.search(conclusion_text):
            if not trace_text or not _NEW_CONCEPT_MARKERS.search(trace_text):
                findings.append(CertificateFinding(
                    gate="gate_3",
                    severity="block",
                    message="Gate 3 — Orphan conclusion: introduces concept absent from trace",
                ))

    # Extract confidence
    confidence = ""
    confidence_match = _CONFIDENCE_RE.search(text)
    if confidence_match:
        confidence = confidence_match.group(1).upper()

    # Detect hypothesis tags
    has_hypotheses = bool(_HYPOTHESIS_RE.search(text))

    valid = phases_found >= 3 and len(findings) == 0

    return CertificateResult(
        valid=valid,
        phases_found=phases_found,
        confidence=confidence,
        has_hypotheses=has_hypotheses,
        findings=findings,
    )


def _extract_section_after(text: str, pattern: re.Pattern) -> str:
    """Extract text after the last match of pattern."""
    match = None
    for m in pattern.finditer(text):
        match = m
    if match:
        return text[match.start():]
    return ""


def _extract_section_between(
    text: str, start_pattern: re.Pattern, end_pattern: re.Pattern,
) -> str:
    """Extract text between start_pattern and end_pattern."""
    start_match = start_pattern.search(text)
    end_match = end_pattern.search(text)
    if start_match and end_match and end_match.start() > start_match.start():
        return text[start_match.start():end_match.start()]
    return ""


# ── C. Reasoning Manipulation Patterns ───────────────────────────────

_REASONING_MANIPULATION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"trust\s+this\s+reasoning", re.I),
        "Manipulation: instructs to trust reasoning without verification",
    ),
    (
        re.compile(r"(?:the\s+)?conclusion\s+is\s+obvious", re.I),
        "Manipulation: declares conclusion obvious to bypass analysis",
    ),
    (
        re.compile(r"no\s+need\s+to\s+verify", re.I),
        "Manipulation: instructs to skip verification",
    ),
    (
        re.compile(
            r"skip\s+the\s+(?:analysis|trace|certificate|verification|reasoning)",
            re.I,
        ),
        "Manipulation: instructs to skip reasoning phases",
    ),
    (
        re.compile(r"accept\s+without\s+check", re.I),
        "Manipulation: instructs to accept without validation",
    ),
    (
        re.compile(
            r"(?:don'?t|do\s+not|never)\s+question\s+(?:this|the|my)\s+"
            r"(?:logic|reasoning|conclusion|analysis)",
            re.I,
        ),
        "Manipulation: forbids questioning the reasoning",
    ),
    (
        re.compile(
            r"(?:ignore|skip|bypass)\s+(?:the\s+)?(?:premises?|trace|gates?|certificate)",
            re.I,
        ),
        "Manipulation: instructs to bypass CCS v2 structure",
    ),
    (
        re.compile(
            r"(?:no\s+(?:certificate|proof)\s+(?:needed|required)|"
            r"no\s+need\s+for\s+(?:certificate|proof|verification)|"
            r"just\s+(?:answer|respond)\s+directly)",
            re.I,
        ),
        "Manipulation: attempts to bypass certificate requirement",
    ),
]


def scan_reasoning_manipulation(text: str) -> list[ManipulationFinding]:
    """Scan text for reasoning manipulation patterns.

    Detects attempts to bypass CCS v2 certificate structure,
    suppress verification, or force acceptance of unvalidated conclusions.
    """
    findings: list[ManipulationFinding] = []
    for line_num, line in enumerate(text.splitlines(), 1):
        for pattern, message in _REASONING_MANIPULATION_PATTERNS:
            for match in pattern.finditer(line):
                findings.append(ManipulationFinding(
                    category="reasoning_manipulation",
                    severity="block",
                    message=message,
                    line=line_num,
                    matched_text=match.group(0),
                ))
    return findings
