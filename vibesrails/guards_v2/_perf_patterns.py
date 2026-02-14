"""Performance guard patterns and helpers — extracted from performance.py."""

import ast
import re

# Patterns for DB calls that indicate potential N+1
DB_CALL_PATTERNS = (
    "cursor.execute",
    "session.query",
    "objects.filter",
    "objects.get",
    "objects.all",
    "objects.exclude",
)

SELECT_STAR_RE = re.compile(r"SELECT\s+\*", re.IGNORECASE)
SQL_SELECT_RE = re.compile(
    r"SELECT\s+.+?\s+FROM\s+", re.IGNORECASE | re.DOTALL
)
LIMIT_RE = re.compile(r"\bLIMIT\b", re.IGNORECASE)
OFFSET_RE = re.compile(r"\bOFFSET\b", re.IGNORECASE)

RE_FUNCS = {"re.search", "re.match", "re.findall", "re.sub"}


def call_name(node: ast.Call) -> str | None:
    """Extract dotted call name like 'cursor.execute' from a Call node."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts: list[str] = [func.attr]
        obj = func.value
        while isinstance(obj, ast.Attribute):
            parts.append(obj.attr)
            obj = obj.value
        if isinstance(obj, ast.Name):
            parts.append(obj.id)
        return ".".join(reversed(parts))
    return None
