"""Database Safety Guard — Detects unsafe SQL and DB patterns."""

import re
from pathlib import Path

from .dependency_audit import V2GuardIssue

GUARD_NAME = "database-safety"

# Raw SQL via string formatting in execute()
RAW_SQL_EXECUTE = re.compile(
    r"""\.execute\(\s*(?:f['"]|['"].*%|.*\.format\()""",
)

# Dangerous DDL/DML without WHERE
DROP_TRUNCATE = re.compile(
    r"""\b(?:DROP\s+TABLE|TRUNCATE\s+TABLE)\b""",
    re.IGNORECASE,
)
DELETE_NO_WHERE = re.compile(
    r"""\bDELETE\s+FROM\s+\w+\s*['";)]\s*$""",
    re.IGNORECASE | re.MULTILINE,
)

# SELECT without LIMIT
SELECT_NO_LIMIT = re.compile(
    r"""\bSELECT\b(?:(?!\bLIMIT\b).)*['";)\s]*$""",
    re.IGNORECASE | re.MULTILINE,
)

# DB connection without timeout
CONN_NO_TIMEOUT = re.compile(
    r"""(?:connect|create_engine)\([^)]*\)""",
)

# Django risky methods
DJANGO_RAW = re.compile(r"""\.raw\(\s*(?:f['"]|['"].*%|.*\+)""")
DJANGO_EXTRA = re.compile(r"""\.extra\(""")

# SQLAlchemy text() with f-string
SQLA_TEXT_FSTRING = re.compile(r"""\btext\(\s*f['"]""")


class DatabaseSafetyGuard:
    """Detects unsafe SQL and database patterns."""

    # Line-level check rules: (regex, severity, message)
    _LINE_CHECKS: list[tuple[re.Pattern, str, str]] = [
        (RAW_SQL_EXECUTE, "block", "Raw SQL without parameterized query in execute()"),
        (DROP_TRUNCATE, "block", "Dangerous DDL: DROP/TRUNCATE detected"),
        (DELETE_NO_WHERE, "block", "DELETE FROM without WHERE clause"),
        (DJANGO_RAW, "block", "Django raw() with string interpolation"),
        (DJANGO_EXTRA, "warn", "Django extra() is error-prone — prefer ORM queries"),
        (SQLA_TEXT_FSTRING, "block", "SQLAlchemy text() with f-string — use bound parameters"),
    ]

    @staticmethod
    def _check_select_no_limit(line: str) -> bool:
        """Check if line has SELECT without LIMIT."""
        return (
            re.search(r"\bSELECT\b", line, re.IGNORECASE) is not None
            and not re.search(r"\bLIMIT\b", line, re.IGNORECASE)
            and not re.search(r"\bCOUNT\(", line, re.IGNORECASE)
            and "execute" not in line.lower()
            and line.rstrip().endswith(('"', "'", ";"))
        )

    @staticmethod
    def _check_conn_no_timeout(line: str) -> bool:
        """Check if line has DB connection without timeout."""
        return (
            re.search(r"(?:connect|create_engine)\(", line) is not None
            and "timeout" not in line.lower()
        )

    def scan_file(
        self, filepath: Path, content: str
    ) -> list[V2GuardIssue]:
        """Scan a single file for database safety issues."""
        issues: list[V2GuardIssue] = []
        fname = str(filepath)

        for lineno, line in enumerate(content.splitlines(), 1):
            if line.strip().startswith("#"):
                continue

            for pattern, severity, message in self._LINE_CHECKS:
                if pattern.search(line):
                    issues.append(V2GuardIssue(
                        guard=GUARD_NAME, severity=severity,
                        message=message, file=fname, line=lineno,
                    ))

            if self._check_select_no_limit(line):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME, severity="warn",
                    message="SELECT query without LIMIT clause",
                    file=fname, line=lineno,
                ))

            if self._check_conn_no_timeout(line):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME, severity="warn",
                    message="DB connection without timeout setting",
                    file=fname, line=lineno,
                ))

        return issues

    def scan(self, project_root: Path) -> list[V2GuardIssue]:
        """Scan entire project for database safety issues."""
        issues: list[V2GuardIssue] = []
        for pyfile in sorted(project_root.rglob("*.py")):
            rel = pyfile.relative_to(project_root)
            parts = rel.parts
            if any(
                p.startswith(".")
                or p in ("node_modules", "__pycache__")
                for p in parts
            ):
                continue
            # Skip test files — they contain intentional SQL fixtures
            if parts[0] == "tests" or pyfile.name.startswith("test_"):
                continue
            try:
                content = pyfile.read_text(
                    encoding="utf-8", errors="ignore"
                )
            except OSError:
                continue
            issues.extend(
                self.scan_file(pyfile, content)
            )
        return issues
