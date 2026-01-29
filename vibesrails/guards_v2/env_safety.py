"""Env Safety Guard — Detects environment variable misuse and secret leaks."""

import re
import subprocess
from pathlib import Path

from .dependency_audit import V2GuardIssue

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
            # Check unsafe os.environ["KEY"]
            for match in UNSAFE_ENVIRON_RE.finditer(line):
                key = match.group(1)
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        f'os.environ["{key}"] crashes if missing'
                        f' — use os.environ.get("{key}")'
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
            pass
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
            try:
                content = pyfile.read_text(errors="ignore")
            except OSError:
                continue
            issues.extend(self.scan_file(pyfile, content))
        return issues
