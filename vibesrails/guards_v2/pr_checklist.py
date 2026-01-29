"""PR Checklist Guard — Auto-generates a checklist from git diff."""

import re
import subprocess
from pathlib import Path

from .dependency_audit import V2GuardIssue

GUARD_NAME = "pr-checklist"

# Patterns for security-sensitive files
SECURITY_PATTERNS = re.compile(
    r"(auth|crypto|payment|security|token|session|password|secret)",
    re.IGNORECASE,
)

# Patterns for model/schema files
MIGRATION_PATTERNS = re.compile(
    r"(models?\.py|schema\.py|migrations?/|alembic/)",
    re.IGNORECASE,
)

# Patterns for public API indicators
PUBLIC_API_PATTERNS = re.compile(
    r"(^[\+\-]\s*def\s+[a-z_]\w*\s*\(|^[\+\-]\s*class\s+\w+)",
    re.MULTILINE,
)

# Detect function signature changes (removed then added)
FUNC_SIG_REMOVED = re.compile(
    r"^-\s*def\s+([a-z_]\w*)\s*\((.+?)\)",
    re.MULTILINE,
)
FUNC_SIG_ADDED = re.compile(
    r"^\+\s*def\s+([a-z_]\w*)\s*\((.+?)\)",
    re.MULTILINE,
)

# Env var usage
ENV_VAR_PATTERN = re.compile(
    r"^\+.*(?:os\.environ|os\.getenv)\b",
    re.MULTILINE,
)

# Dependency files
DEP_FILE_PATTERN = re.compile(
    r"(requirements.*\.txt|pyproject\.toml|setup\.cfg|Pipfile)",
)

# Test file pattern
TEST_FILE_PATTERN = re.compile(r"test[s_].*\.py|.*_test\.py")

# Source code file pattern
SOURCE_FILE_PATTERN = re.compile(r"\.py$")

# Diff file header
DIFF_FILE_HEADER = re.compile(r"^(?:diff --git a/|[+]{3} b/)(.+)$", re.MULTILINE)


class PRChecklistGuard:
    """Analyzes git diffs to generate PR review checklists."""

    def _extract_files(self, diff: str) -> list[str]:
        """Extract file paths from a diff."""
        return DIFF_FILE_HEADER.findall(diff)

    def _has_code_but_no_tests(self, diff: str) -> bool:
        """Check if code changed but no test files touched."""
        files = self._extract_files(diff)
        has_source = any(
            SOURCE_FILE_PATTERN.search(f)
            and not TEST_FILE_PATTERN.search(f)
            for f in files
        )
        has_tests = any(TEST_FILE_PATTERN.search(f) for f in files)
        return has_source and not has_tests

    def _has_breaking_changes(self, diff: str) -> bool:
        """Check if public function signatures changed."""
        removed = {
            (m.group(1), m.group(2))
            for m in FUNC_SIG_REMOVED.finditer(diff)
            if not m.group(1).startswith("_")
        }
        added = {
            (m.group(1), m.group(2))
            for m in FUNC_SIG_ADDED.finditer(diff)
            if not m.group(1).startswith("_")
        }
        # Same function name but different signature
        removed_names = {name for name, _ in removed}
        added_names = {name for name, _ in added}
        shared = removed_names & added_names
        for name in shared:
            old_sig = next(s for n, s in removed if n == name)
            new_sig = next(s for n, s in added if n == name)
            if old_sig != new_sig:
                return True
        return False

    def _has_new_env_vars(self, diff: str) -> bool:
        """Check if new env var usage was added."""
        return bool(ENV_VAR_PATTERN.search(diff))

    def _needs_migration(self, diff: str) -> bool:
        """Check if model/schema files changed."""
        files = self._extract_files(diff)
        return any(MIGRATION_PATTERNS.search(f) for f in files)

    def _has_api_changes(self, diff: str) -> bool:
        """Check if public API changed."""
        return bool(PUBLIC_API_PATTERNS.search(diff))

    def _needs_security_review(self, diff: str) -> bool:
        """Check if security-sensitive files touched."""
        files = self._extract_files(diff)
        return any(SECURITY_PATTERNS.search(f) for f in files)

    def _has_new_deps(self, diff: str) -> bool:
        """Check if dependency files changed."""
        files = self._extract_files(diff)
        return any(DEP_FILE_PATTERN.search(f) for f in files)

    def analyze_diff(self, diff: str) -> list[V2GuardIssue]:
        """Analyze a diff and return checklist issues."""
        issues: list[V2GuardIssue] = []

        checks = [
            (self._has_code_but_no_tests, "Add tests"),
            (self._has_breaking_changes, "Document breaking changes"),
            (self._has_new_env_vars, "Update .env.example"),
            (self._needs_migration, "Create migration"),
            (self._has_api_changes, "Update documentation"),
            (self._needs_security_review, "Security review needed"),
            (self._has_new_deps, "Audit new deps"),
        ]

        for check_fn, message in checks:
            if check_fn(diff):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="info",
                    message=message,
                ))

        return issues

    def generate_checklist(self, diff: str) -> str:
        """Generate a markdown checklist from a diff."""
        issues = self.analyze_diff(diff)
        if not issues:
            return "No checklist items detected."
        lines = ["## PR Checklist", ""]
        for issue in issues:
            lines.append(f"- [ ] {issue.message}")
        return "\n".join(lines)

    def scan(self, project_root: Path) -> list[V2GuardIssue]:
        """Scan staged git diff for checklist items."""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=30,
            )
            if result.returncode != 0:
                return []
            return self.analyze_diff(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
