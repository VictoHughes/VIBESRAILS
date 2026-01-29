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

    def scan_file(
        self, filepath: Path, content: str
    ) -> list[V2GuardIssue]:
        """Scan a single file for database safety issues."""
        issues: list[V2GuardIssue] = []
        fname = str(filepath)
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            lineno = i
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            # 1. Raw SQL in execute()
            if RAW_SQL_EXECUTE.search(line):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="block",
                    message="Raw SQL without parameterized query"
                    " in execute()",
                    file=fname,
                    line=lineno,
                ))

            # 2. DROP/TRUNCATE
            if DROP_TRUNCATE.search(line):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="block",
                    message="Dangerous DDL: DROP/TRUNCATE"
                    " detected",
                    file=fname,
                    line=lineno,
                ))

            # 3. DELETE without WHERE
            if DELETE_NO_WHERE.search(line):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="block",
                    message="DELETE FROM without WHERE clause",
                    file=fname,
                    line=lineno,
                ))

            # 4. SELECT without LIMIT
            if (
                re.search(r"\bSELECT\b", line, re.IGNORECASE)
                and not re.search(
                    r"\bLIMIT\b", line, re.IGNORECASE
                )
                and not re.search(
                    r"\bCOUNT\(", line, re.IGNORECASE
                )
                and "execute" not in line.lower()
                and (
                    line.rstrip().endswith(('"', "'", ";"))
                )
            ):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message="SELECT query without LIMIT"
                    " clause",
                    file=fname,
                    line=lineno,
                ))

            # 5. Connection without timeout
            if re.search(
                r"(?:connect|create_engine)\(", line
            ):
                if "timeout" not in line.lower():
                    issues.append(V2GuardIssue(
                        guard=GUARD_NAME,
                        severity="warn",
                        message="DB connection without"
                        " timeout setting",
                        file=fname,
                        line=lineno,
                    ))

            # 6. Django raw() with interpolation
            if DJANGO_RAW.search(line):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="block",
                    message="Django raw() with string"
                    " interpolation",
                    file=fname,
                    line=lineno,
                ))

            # 7. Django extra()
            if DJANGO_EXTRA.search(line):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message="Django extra() is error-prone"
                    " — prefer ORM queries",
                    file=fname,
                    line=lineno,
                ))

            # 8. SQLAlchemy text() with f-string
            if SQLA_TEXT_FSTRING.search(line):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="block",
                    message="SQLAlchemy text() with f-string"
                    " — use bound parameters",
                    file=fname,
                    line=lineno,
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
