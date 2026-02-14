"""MCP tool: scan_code — run Guards V2 AST analysis on code.

Wraps vibesrails guards_v2 as an MCP-callable tool.
Guards stay in vibesrails/guards_v2/ — this is a thin orchestration layer.
"""

from __future__ import annotations

import logging
from pathlib import Path

from core.input_validator import InputValidationError, sanitize_for_output, validate_list
from core.learning_bridge import record_safe
from core.path_validator import PathValidationError, validate_path
from vibesrails.guards_v2 import ALL_GUARD_CLASSES, V2GuardIssue

from .scan_code_pedagogy import DEFAULT_PEDAGOGY as _DEFAULT_PEDAGOGY
from .scan_code_pedagogy import GUARD_PEDAGOGY

logger = logging.getLogger(__name__)

# ── Guard registry ─────────────────────────────────────────────────────

GUARD_REGISTRY: dict[str, type] = {
    "dependency_audit": None,
    "performance": None,
    "complexity": None,
    "env_safety": None,
    "git_workflow": None,
    "dead_code": None,
    "observability": None,
    "type_safety": None,
    "docstring": None,
    "pr_checklist": None,
    "database_safety": None,
    "api_design": None,
    "pre_deploy": None,
    "test_integrity": None,
    "mutation": None,
    "architecture_drift": None,
}

_CLASS_NAME_TO_SLUG = {
    "DependencyAuditGuard": "dependency_audit",
    "PerformanceGuard": "performance",
    "ComplexityGuard": "complexity",
    "EnvSafetyGuard": "env_safety",
    "GitWorkflowGuard": "git_workflow",
    "DeadCodeGuard": "dead_code",
    "ObservabilityGuard": "observability",
    "TypeSafetyGuard": "type_safety",
    "DocstringGuard": "docstring",
    "PRChecklistGuard": "pr_checklist",
    "DatabaseSafetyGuard": "database_safety",
    "APIDesignGuard": "api_design",
    "PreDeployGuard": "pre_deploy",
    "TestIntegrityGuard": "test_integrity",
    "MutationGuard": "mutation",
    "ArchitectureDriftGuard": "architecture_drift",
}

for _cls in ALL_GUARD_CLASSES:
    _slug = _CLASS_NAME_TO_SLUG.get(_cls.__name__)
    if _slug and _slug in GUARD_REGISTRY:
        GUARD_REGISTRY[_slug] = _cls


# ── Core logic ─────────────────────────────────────────────────────────

def _resolve_guards(guard_names: list[str] | str) -> list[tuple[str, type]]:
    """Resolve guard slugs to (slug, class) pairs.

    Args:
        guard_names: "all" or a list of guard slug strings.

    Returns:
        List of (slug, guard_class) tuples.

    Raises:
        ValueError: If an unknown guard name is provided.
    """
    if guard_names == "all":
        return [(slug, cls) for slug, cls in GUARD_REGISTRY.items() if cls is not None]

    resolved = []
    for name in guard_names:
        cls = GUARD_REGISTRY.get(name)
        if cls is None:
            available = sorted(k for k, v in GUARD_REGISTRY.items() if v is not None)
            raise ValueError(
                f"Unknown guard: {name!r}. Available: {', '.join(available)}"
            )
        resolved.append((name, cls))
    return resolved


def _issue_to_finding(issue: V2GuardIssue, guard_slug: str) -> dict:
    """Convert a V2GuardIssue to a MCP finding dict with pedagogy."""
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
        finding["file"] = sanitize_for_output(issue.file)
    if issue.line is not None:
        finding["line"] = issue.line

    return finding


def _determine_status(findings: list[dict]) -> str:
    """Determine overall status from findings.

    Returns: "pass", "warn", "fail", or "block".
    """
    if not findings:
        return "pass"

    severities = {f["severity"] for f in findings}
    if "block" in severities:
        return "block"
    if "warn" in severities:
        return "warn"
    return "info"


def scan_code(
    file_path: str | None = None,
    project_path: str | None = None,
    guards: list[str] | str = "all",
) -> dict:
    """Run Guards V2 AST analysis and return findings with pedagogy.

    Args:
        file_path: Path to a single file to scan.  The file's parent
            directory is used as project_root, then results are filtered
            to only include findings for this file.
        project_path: Path to a project directory to scan.  Takes
            precedence over file_path if both are provided.
        guards: "all" to run every guard, or a list of guard slugs
            (e.g. ["dead_code", "complexity"]).

    Returns:
        Dict with keys: status, findings, guards_run, summary.
    """
    # Validate inputs
    try:
        if isinstance(guards, list):
            validate_list(guards, "guards", max_items=100, item_type=str)
    except InputValidationError as exc:
        return {
            "status": "error",
            "findings": [],
            "guards_run": [],
            "summary": {"total": 0, "by_severity": {}},
            "error": str(exc),
        }

    # Validate paths
    try:
        if project_path:
            root = validate_path(project_path, must_exist=True, must_be_dir=True)
        elif file_path:
            validate_path(file_path, must_exist=True, must_be_file=True)
            root = Path(file_path).parent
        else:
            root = Path.cwd()
    except PathValidationError as exc:
        return {
            "status": "error",
            "findings": [],
            "guards_run": [],
            "summary": {"total": 0, "by_severity": {}},
            "error": str(exc),
        }

    # Resolve guards
    try:
        guard_pairs = _resolve_guards(guards)
    except ValueError as exc:
        return {
            "status": "error",
            "findings": [],
            "guards_run": [],
            "summary": {"total": 0, "by_severity": {}},
            "error": str(exc),
        }

    # Run guards
    findings: list[dict] = []
    guards_run: list[str] = []
    target_file = Path(file_path).name if file_path else None

    for slug, guard_cls in guard_pairs:
        guards_run.append(slug)
        try:
            guard = guard_cls()
            issues = guard.scan(root)
        except Exception:
            logger.exception("Guard %s raised an exception", slug)
            continue

        for issue in issues:
            finding = _issue_to_finding(issue, slug)

            # Filter by file_path if scanning a single file
            if target_file and finding.get("file"):
                if not finding["file"].endswith(target_file):
                    continue

            findings.append(finding)

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
