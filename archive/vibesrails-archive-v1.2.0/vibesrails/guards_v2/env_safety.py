"""Env Safety Guard — Detects environment variable misuse and secret leaks."""

import ast
import logging
import re
import subprocess
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

GUARD_NAME = "env-safety"

# Patterns for hardcoded secrets in source code
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS access key", re.compile(r"""(?:=|:)\s*['"]?(AKIA[0-9A-Z]{16})""")),
    (
        "Hardcoded password",
        re.compile(
            r"""(?:password|passwd|pwd)\s*=\s*['"][^'"]{4,}['"]""",
            re.IGNORECASE,
        ),
    ),
    (
        "Hardcoded token",
        re.compile(
            r"""(?:token|secret|api_key)\s*=\s*['"](?:sk-|ghp_|gho_)[^'"]+['"]""",
            re.IGNORECASE,
        ),
    ),
]

# Field names that should be masked in __repr__/__str__
SECRET_FIELD_NAMES: set[str] = {
    "api_key", "apikey", "api_secret", "apisecret",
    "openai_api_key", "anthropic_api_key", "google_api_key",
    "secret", "secret_key", "secretkey",
    "password", "passwd", "pwd",
    "token", "access_token", "refresh_token", "auth_token",
    "private_key", "privatekey",
    "aws_secret_access_key", "aws_access_key_id",
    "database_url", "db_password", "db_url",
    "smtp_password", "email_password",
    "encryption_key", "signing_key",
}

# File extensions that should never be tracked in git
SECRET_FILE_EXTS: set[str] = {".pem", ".key", ".p12"}

# Patterns that should be in .gitignore
GITIGNORE_SECRET_PATTERNS: list[str] = [
    "*.pem", "*.key", "*.p12",
]

# Pattern for unsafe os.environ usage
UNSAFE_ENVIRON_RE: re.Pattern[str] = re.compile(
    r"""os\.environ\s*\[\s*['"]([^'"]+)['"]\s*\]"""
)


class EnvSafetyGuard:
    """Detects env variable misuse, missing .env safety, and secrets."""

    def scan(self, project_root: Path) -> list[V2GuardIssue]:
        """Scan the entire project for env safety issues.

        Args:
            project_root: Root directory of the project.

        Returns:
            List of detected issues.
        """
        issues: list[V2GuardIssue] = []
        issues.extend(self._check_gitignore(project_root))
        issues.extend(self._check_env_example(project_root))
        issues.extend(self._check_tracked_secret_files(project_root))
        issues.extend(self._scan_source_files(project_root))
        return issues

    def scan_file(
        self, filepath: Path, content: str
    ) -> list[V2GuardIssue]:
        """Scan a single file's content for env safety issues.

        Args:
            filepath: Path to the file being scanned.
            content: The file's text content.

        Returns:
            List of detected issues.
        """
        issues: list[V2GuardIssue] = []
        fname = str(filepath)

        for lineno, line in enumerate(content.splitlines(), 1):
            # Detect unsafe direct-subscript environ access
            for match in UNSAFE_ENVIRON_RE.finditer(line):
                key = match.group(1)
                # Build message without triggering our own regex
                env_call = "os.environ" + '["{k}"]'.format(k=key)
                safe_call = "os.environ.get" + '("{k}")'.format(k=key)
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        f'{env_call} crashes if missing'
                        f' \u2014 use {safe_call}'
                    ),
                    file=fname,
                    line=lineno,
                ))

            # Check hardcoded secrets
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    issues.append(V2GuardIssue(
                        guard=GUARD_NAME,
                        severity="block",
                        message=f"{label} detected in source",
                        file=fname,
                        line=lineno,
                    ))

        # Check for Settings/Config classes that may leak secrets in __repr__
        issues.extend(self._check_secret_leak_in_repr(filepath, content))

        return issues

    def _check_secret_leak_in_repr(
        self, filepath: Path, content: str
    ) -> list[V2GuardIssue]:
        """Detect Settings/Config classes with secret fields that lack masked __repr__."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        issues: list[V2GuardIssue] = []
        fname = str(filepath)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                issue = self._check_class_for_secret_leak(node, fname)
                if issue:
                    issues.append(issue)

        return issues

    def _check_class_for_secret_leak(
        self, node: ast.ClassDef, fname: str
    ) -> V2GuardIssue | None:
        """Check a single class for secret field leaks."""
        secret_fields = self._find_secret_fields(node)
        if not secret_fields:
            return None

        if self._has_repr_or_str(node):
            return None

        is_config_class = self._is_config_class(node.name)
        severity = "block" if is_config_class else "warn"

        return V2GuardIssue(
            guard=GUARD_NAME,
            severity=severity,
            message=(
                f"Class '{node.name}' has secret fields ({', '.join(secret_fields[:3])}) "
                f"but no __repr__ — secrets can leak in logs/pytest output. "
                f"Add __repr__ that masks sensitive values."
            ),
            file=fname,
            line=node.lineno,
        )

    def _is_config_class(self, class_name: str) -> bool:
        """Check if class name suggests it holds config/secrets."""
        name_lower = class_name.lower()
        return any(kw in name_lower for kw in ("settings", "config", "credentials", "secrets"))

    def _is_secret_field(self, field_name: str) -> bool:
        """Check if field name suggests it holds secrets."""
        field_lower = field_name.lower()
        if field_lower in SECRET_FIELD_NAMES:
            return True
        return any(s in field_lower for s in ("key", "secret", "password", "token"))

    def _find_secret_fields(self, node: ast.ClassDef) -> list[str]:
        """Find secret-like field names in a class."""
        secret_fields: list[str] = []

        for child in ast.walk(node):
            field_name = self._extract_field_name(child)
            if field_name and self._is_secret_field(field_name):
                secret_fields.append(field_name)

        return secret_fields

    def _extract_field_name(self, node: ast.AST) -> str | None:
        """Extract field name from AST node if it's a class/instance attribute."""
        # Class-level annotation: field_name: type = ...
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            return node.target.id

        # Instance attribute in __init__: self.field_name = ...
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Attribute) and
                    isinstance(target.value, ast.Name) and
                    target.value.id == "self"):
                    return target.attr

        return None

    def _has_repr_or_str(self, node: ast.ClassDef) -> bool:
        """Check if class has __repr__ or __str__ method."""
        for child in node.body:
            if isinstance(child, ast.FunctionDef) and child.name in ("__repr__", "__str__"):
                return True
        return False

    # ── Private helpers ──────────────────────────────────────────

    def _check_gitignore(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Check that .env is listed in .gitignore."""
        gitignore = project_root / ".gitignore"
        if not gitignore.exists():
            return [V2GuardIssue(
                guard=GUARD_NAME,
                severity="block",
                message=".gitignore missing — .env may be committed",
                file=".gitignore",
            )]

        content = gitignore.read_text()
        lines = [
            ln.strip() for ln in content.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        issues: list[V2GuardIssue] = []

        if ".env" not in lines:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME,
                severity="block",
                message=".env not in .gitignore",
                file=".gitignore",
            ))

        for pat in GITIGNORE_SECRET_PATTERNS:
            if pat not in lines:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=f"{pat} not in .gitignore",
                    file=".gitignore",
                ))

        return issues

    def _check_env_example(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Check that .env.example exists for team onboarding."""
        if not (project_root / ".env.example").exists():
            return [V2GuardIssue(
                guard=GUARD_NAME,
                severity="warn",
                message=(
                    ".env.example missing"
                    " — teammates won't know required vars"
                ),
            )]
        return []

    def _check_tracked_secret_files(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Detect .pem/.key/.p12 files tracked by git."""
        issues: list[V2GuardIssue] = []
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=10,
            )
            if result.returncode != 0:
                return []
            for tracked in result.stdout.splitlines():
                p = Path(tracked)
                if p.suffix in SECRET_FILE_EXTS:
                    issues.append(V2GuardIssue(
                        guard=GUARD_NAME,
                        severity="block",
                        message=(
                            f"Secret file tracked in git: {tracked}"
                        ),
                        file=tracked,
                    ))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # git not available or timed out, skip check
        return issues

    def _scan_source_files(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Walk Python source files and scan each."""
        issues: list[V2GuardIssue] = []
        for pyfile in project_root.rglob("*.py"):
            # Skip venv / hidden dirs
            parts = pyfile.relative_to(project_root).parts
            if any(p.startswith(".") or p == "venv" for p in parts):
                continue
            # Skip test files — they contain intentional secret fixtures
            if parts[0] == "tests" or pyfile.name.startswith("test_"):
                continue
            try:
                content = pyfile.read_text(errors="ignore")
            except OSError:
                continue
            issues.extend(self.scan_file(pyfile, content))
        return issues
