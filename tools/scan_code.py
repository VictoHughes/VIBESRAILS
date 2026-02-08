"""MCP tool: scan_code — run Guards V2 AST analysis on code.

Wraps vibesrails guards_v2 as an MCP-callable tool.
Guards stay in vibesrails/guards_v2/ — this is a thin orchestration layer.
"""

from __future__ import annotations

import logging
from pathlib import Path

from core.input_validator import InputValidationError, validate_list
from core.learning_bridge import record_safe
from core.path_validator import PathValidationError, validate_path
from vibesrails.guards_v2 import ALL_GUARD_CLASSES, V2GuardIssue

logger = logging.getLogger(__name__)

# ── Guard registry ─────────────────────────────────────────────────────
# Explicit slug → class mapping (auto-generated slugs are ugly for
# acronyms like API, PR).  Users pass these slugs in the "guards" param.

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

# Populate from ALL_GUARD_CLASSES — keeps the mapping DRY.
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

# ── Pedagogy messages ──────────────────────────────────────────────────
# Per-guard educational context.  Each finding gets a "pedagogy" dict
# explaining WHY the issue matters, HOW to fix, and HOW to prevent.

GUARD_PEDAGOGY: dict[str, dict[str, str]] = {
    "dependency_audit": {
        "why": (
            "AI code generators often suggest packages by name without verifying "
            "they exist or are safe. Typosquatting and abandoned packages are real "
            "supply-chain attack vectors."
        ),
        "how_to_fix": "Pin the dependency to a known-good version in requirements.txt or pyproject.toml.",
        "prevention": "Always verify packages on PyPI before adding them. Use pip-audit regularly.",
    },
    "performance": {
        "why": (
            "AI-generated code frequently contains N+1 queries, string concatenation "
            "in loops, and other patterns that are correct but slow at scale."
        ),
        "how_to_fix": "Replace the anti-pattern with the suggested alternative in the finding message.",
        "prevention": "Review generated code for loops that hit I/O. Prefer batch operations.",
    },
    "complexity": {
        "why": (
            "High cyclomatic complexity makes code hard to test and maintain. "
            "AI generators tend to produce deeply nested conditionals instead of "
            "early returns or strategy patterns."
        ),
        "how_to_fix": "Extract nested logic into helper functions. Use early returns to flatten conditionals.",
        "prevention": "Ask the AI to keep functions under 10 cyclomatic complexity.",
    },
    "env_safety": {
        "why": (
            "Secrets leaked in code, environment variables, or __repr__ methods "
            "are the #1 cause of security breaches in AI-assisted projects."
        ),
        "how_to_fix": "Move secrets to environment variables. Never hardcode credentials.",
        "prevention": "Use a .env file with python-dotenv. Add .env to .gitignore.",
    },
    "git_workflow": {
        "why": (
            "AI sessions can produce large, unfocused commits that are hard to review. "
            "Proper git hygiene prevents sneaking bad code into production."
        ),
        "how_to_fix": "Follow the commit message convention. Keep commits focused on one change.",
        "prevention": "Commit after each logical change, not at the end of a long session.",
    },
    "dead_code": {
        "why": (
            "AI generators add unused imports and variables as artifacts of their "
            "generation process. Dead code obscures the real logic and creates "
            "false dependencies."
        ),
        "how_to_fix": "Remove the unused import or variable identified in the finding.",
        "prevention": "Run dead code detection after every AI generation session.",
    },
    "observability": {
        "why": (
            "print() statements left in production code leak internal state and "
            "bypass structured logging. AI generators use print() for debugging "
            "but forget to remove it."
        ),
        "how_to_fix": "Replace print() with logging.getLogger(__name__).info() or .debug().",
        "prevention": "Configure a linter rule to forbid print() in non-test code.",
    },
    "type_safety": {
        "why": (
            "Missing type annotations make AI-generated code harder to validate. "
            "Type checkers catch bugs that tests miss — especially None-safety issues."
        ),
        "how_to_fix": "Add type annotations to the function signatures identified in the finding.",
        "prevention": "Ask the AI to always include type annotations. Run mypy in CI.",
    },
    "docstring": {
        "why": (
            "Public functions without docstrings are opaque to both humans and AI tools. "
            "The next AI session will misunderstand undocumented code."
        ),
        "how_to_fix": "Add a docstring explaining what the function does, its params, and return value.",
        "prevention": "Enforce docstrings for public functions in your linter config.",
    },
    "pr_checklist": {
        "why": (
            "Pull requests from AI sessions often include unrelated changes, "
            "debug artifacts, or incomplete implementations."
        ),
        "how_to_fix": "Review the staged diff and remove anything not related to the PR's purpose.",
        "prevention": "Use a PR template. Limit AI sessions to one feature per PR.",
    },
    "database_safety": {
        "why": (
            "SQL injection is the most common vulnerability in AI-generated code. "
            "AI tools frequently use f-strings or .format() in SQL queries."
        ),
        "how_to_fix": "Use parameterized queries (?, %s) instead of string interpolation.",
        "prevention": "Use an ORM or query builder. Never pass user input directly into SQL.",
    },
    "api_design": {
        "why": (
            "AI generators produce API endpoints that lack authentication, validation, "
            "or proper error handling — patterns that look correct but are insecure."
        ),
        "how_to_fix": "Add input validation, authentication checks, and proper HTTP status codes.",
        "prevention": "Define API contracts (OpenAPI spec) before generating implementation.",
    },
    "pre_deploy": {
        "why": (
            "Pre-deploy checks catch issues that individual guards miss — like version "
            "mismatches, failing tests, or missing changelog entries."
        ),
        "how_to_fix": "Fix the specific pre-deploy check that failed (see finding message).",
        "prevention": "Run pre-deploy checks in CI before every merge to main.",
    },
    "test_integrity": {
        "why": (
            "AI-generated tests often mock too aggressively, test the mock instead of "
            "the code, or contain no real assertions — giving false confidence."
        ),
        "how_to_fix": "Reduce mocking. Assert real behavior, not mock call counts.",
        "prevention": "Review AI-generated tests manually. Run mutation testing to verify test quality.",
    },
    "mutation": {
        "why": (
            "Mutation testing reveals tests that pass even when the code is broken. "
            "AI-generated test suites frequently have low mutation kill rates."
        ),
        "how_to_fix": "Add assertions that catch the surviving mutants listed in the finding.",
        "prevention": "Target 80%+ mutation kill rate. Focus on business logic, not boilerplate.",
    },
    "architecture_drift": {
        "why": (
            "AI generators ignore layer boundaries, importing freely across modules. "
            "This creates spaghetti dependencies that are hard to untangle later."
        ),
        "how_to_fix": "Move the import to the correct layer or create a proper interface.",
        "prevention": "Define architecture rules (import-linter) and enforce them in CI.",
    },
}

# Fallback for guards not in the pedagogy dict
_DEFAULT_PEDAGOGY = {
    "why": "This issue was detected by an automated guard. Review the finding message for details.",
    "how_to_fix": "Address the specific issue described in the finding message.",
    "prevention": "Run vibesrails guards regularly to catch issues early.",
}


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
        finding["file"] = issue.file
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
