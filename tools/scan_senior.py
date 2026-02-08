"""MCP tool: scan_senior — run Senior Mode guards on code.

Wraps vibesrails senior_mode guards as an MCP-callable tool.
Senior guards detect AI-specific coding issues: hallucinations,
lazy patterns, bypass attempts, poor error handling, resilience gaps.
"""

from __future__ import annotations

import logging

from core.input_validator import InputValidationError, validate_list
from core.learning_bridge import record_safe
from core.path_validator import PathValidationError, validate_path
from vibesrails.senior_mode.guards import (
    BypassGuard,
    ErrorHandlingGuard,
    GuardIssue,
    HallucinationGuard,
    LazyCodeGuard,
    ResilienceGuard,
)

logger = logging.getLogger(__name__)

# ── Guard registry ─────────────────────────────────────────────────────
# File-based senior guards: accept (code: str, filepath: str).

_GUARD_CLASSES: dict[str, type] = {
    "error_handling": ErrorHandlingGuard,
    "hallucination": HallucinationGuard,
    "lazy_code": LazyCodeGuard,
    "bypass": BypassGuard,
    "resilience": ResilienceGuard,
}

AVAILABLE_GUARDS = sorted(_GUARD_CLASSES.keys())

# ── Pedagogy messages ──────────────────────────────────────────────────

GUARD_PEDAGOGY: dict[str, dict[str, str]] = {
    "error_handling": {
        "why": (
            "Bare except clauses and silenced errors are the #1 debugging nightmare "
            "in AI-generated code. The AI writes 'except: pass' because it prioritizes "
            "code that doesn't crash over code that reports errors correctly."
        ),
        "how_to_fix": "Catch specific exception types. Log or re-raise — never silently swallow.",
        "prevention": "Ask the AI to always use specific exception types and log errors.",
    },
    "hallucination": {
        "why": (
            "AI models invent module names that sound plausible but don't exist. "
            "This is called 'slopsquatting' — attackers register these fake names on PyPI. "
            "88% of AI sessions produce at least one hallucinated import (Rev 2025, 1038 respondents)."
        ),
        "how_to_fix": "Verify the import exists: pip show <package>. Remove if it doesn't.",
        "prevention": "After every AI session, run: pip check && python -c 'import <module>'.",
    },
    "lazy_code": {
        "why": (
            "AI generators produce placeholder code (pass, ..., NotImplementedError) when they "
            "can't figure out the implementation. This looks like progress but is technical debt "
            "disguised as code."
        ),
        "how_to_fix": "Implement the function body or remove it. No empty functions in production.",
        "prevention": "Review every function body. If the AI wrote 'pass', it gave up — you take over.",
    },
    "bypass": {
        "why": (
            "AI-generated code often includes '# noqa', '# type: ignore', '# nosec' without "
            "specifying which rule. This silences ALL warnings, hiding real problems. "
            "It's the AI taking shortcuts instead of fixing the code."
        ),
        "how_to_fix": "Add the specific rule code: # noqa: E501, # type: ignore[attr-defined].",
        "prevention": "Configure your linter to reject bare suppression comments.",
    },
    "resilience": {
        "why": (
            "AI generates network calls without timeout, file operations without context managers, "
            "and database queries without error handling. The code works in testing but hangs or "
            "crashes in production under real conditions."
        ),
        "how_to_fix": "Add timeout to network calls, 'with' for files, try/except for DB operations.",
        "prevention": "Always specify timeout in HTTP requests. Use context managers by default.",
    },
}

_DEFAULT_PEDAGOGY = {
    "why": "This issue was detected by a senior guard. Review the message for details.",
    "how_to_fix": "Address the specific issue described in the finding message.",
    "prevention": "Run senior guards regularly to catch AI-generated code issues early.",
}


# ── Core logic ─────────────────────────────────────────────────────────

def _resolve_guards(guard_names: list[str] | str) -> list[tuple[str, type]]:
    """Resolve guard slugs to (slug, class) pairs.

    Raises:
        ValueError: If an unknown guard name is provided.
    """
    if guard_names == "all":
        return list(_GUARD_CLASSES.items())

    resolved = []
    for name in guard_names:
        cls = _GUARD_CLASSES.get(name)
        if cls is None:
            raise ValueError(
                f"Unknown senior guard: {name!r}. Available: {', '.join(AVAILABLE_GUARDS)}"
            )
        resolved.append((name, cls))
    return resolved


def _issue_to_finding(issue: GuardIssue, guard_slug: str) -> dict:
    """Convert a GuardIssue to a MCP finding dict with pedagogy."""
    pedagogy = GUARD_PEDAGOGY.get(guard_slug, _DEFAULT_PEDAGOGY)

    finding = {
        "guard": issue.guard,
        "severity": issue.severity,
        "message": issue.message,
        "pedagogy": {
            "why": pedagogy["why"],
            "how_to_fix": pedagogy["how_to_fix"],
            "prevention": pedagogy["prevention"],
        },
    }
    if issue.file is not None:
        finding["file"] = issue.file
    if issue.line is not None:
        finding["line"] = issue.line

    return finding


def _determine_status(findings: list[dict]) -> str:
    """Determine overall status from findings."""
    if not findings:
        return "pass"
    severities = {f["severity"] for f in findings}
    if "block" in severities:
        return "block"
    if "warn" in severities:
        return "warn"
    return "info"


def scan_senior(
    file_path: str | None = None,
    project_path: str | None = None,
    guards: list[str] | str = "all",
) -> dict:
    """Run Senior Mode guards on code files.

    Senior guards detect AI-specific issues: hallucinated imports,
    lazy placeholders, unjustified bypasses, poor error handling,
    and missing resilience patterns.

    Args:
        file_path: Path to a single file to scan.
        project_path: Path to a project directory (scans all .py files).
        guards: "all" or a list of guard slugs.

    Returns:
        Dict with keys: status, findings, guards_run, summary.
    """
    # Validate inputs
    try:
        if isinstance(guards, list):
            validate_list(guards, "guards", max_items=100, item_type=str)
    except InputValidationError as exc:
        return _error_result(str(exc))

    # Validate and determine what to scan
    try:
        if project_path:
            root = validate_path(project_path, must_exist=True, must_be_dir=True)
            py_files = sorted(root.rglob("*.py"))
        elif file_path:
            fp = validate_path(file_path, must_exist=True, must_be_file=True)
            py_files = [fp]
        else:
            return _error_result("Either file_path or project_path is required.")
    except PathValidationError as exc:
        return _error_result(str(exc))

    # Resolve guards
    try:
        guard_pairs = _resolve_guards(guards)
    except ValueError as exc:
        return _error_result(str(exc))

    # Run guards on each file
    findings: list[dict] = []
    guards_run: list[str] = [slug for slug, _ in guard_pairs]

    for py_file in py_files:
        # Skip hidden dirs, venvs, __pycache__
        parts = py_file.parts
        if any(p.startswith(".") or p in ("__pycache__", "venv", ".venv", "node_modules") for p in parts):
            continue

        try:
            code = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        filepath_str = str(py_file)

        for slug, guard_cls in guard_pairs:
            try:
                guard = guard_cls()
                issues = guard.check(code, filepath_str)
            except Exception:
                logger.exception("Senior guard %s raised an exception on %s", slug, py_file)
                continue

            for issue in issues:
                findings.append(_issue_to_finding(issue, slug))

    # Build summary
    by_severity: dict[str, int] = {}
    for f in findings:
        sev = f["severity"]
        by_severity[sev] = by_severity.get(sev, 0) + 1

    # Feed Learning Engine
    for f in findings:
        record_safe(None, "violation", {"guard_name": f["guard"], "severity": f["severity"]})

    return {
        "status": _determine_status(findings),
        "findings": findings,
        "guards_run": guards_run,
        "summary": {
            "total": len(findings),
            "by_severity": by_severity,
        },
    }


def _error_result(message: str) -> dict:
    """Return a standardized error result."""
    return {
        "status": "error",
        "findings": [],
        "guards_run": [],
        "summary": {"total": 0, "by_severity": {}},
        "error": message,
    }
