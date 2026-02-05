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
        """Detect Settings/Config classes with secret fields that lack masked __repr__.

        If a class has fields like 'api_key', 'password', 'secret', etc. but no
        __repr__ or __str__ override, pytest/logs can leak secrets in output.
        """
        issues: list[V2GuardIssue] = []
        fname = str(filepath)

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            # Check if class name suggests it holds config/secrets
            class_name = node.name.lower()
            is_config_class = any(
                kw in class_name
                for kw in ("settings", "config", "credentials", "secrets")
            )

            # Find secret-like field names in class
            secret_fields: list[str] = []
            for child in ast.walk(node):
                # Check class-level assignments: field_name = ...
                if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    field = child.target.id.lower()
                    if field in SECRET_FIELD_NAMES or any(
                        s in field for s in ("key", "secret", "password", "token")
                    ):
                        secret_fields.append(child.target.id)
                # Check __init__ assignments: self.field_name = ...
                elif isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                            if target.value.id == "self":
                                field = target.attr.lower()
                                if field in SECRET_FIELD_NAMES or any(
                                    s in field for s in ("key", "secret", "password", "token")
                                ):
                                    secret_fields.append(target.attr)

            if not secret_fields:
                continue

            # Check if __repr__ or __str__ exists
            has_repr = False
            has_str = False
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    if child.name == "__repr__":
                        has_repr = True
                    elif child.name == "__str__":
                        has_str = True

            # If has secret fields but no __repr__, it can leak in logs/pytest output
            if not has_repr and not has_str:
                severity = "block" if is_config_class else "warn"
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity=severity,
                    message=(
                        f"Class '{node.name}' has secret fields ({', '.join(secret_fields[:3])}) "
                        f"but no __repr__ — secrets can leak in logs/pytest output. "
                        f"Add __repr__ that masks sensitive values."
                    ),
                    file=fname,
                    line=node.lineno,
                ))

        return issues

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
