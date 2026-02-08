"""API Design Guard — Detects common API design issues."""

import ast
import logging
import re
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

GUARD_NAME = "api-design"

# Route decorator patterns for FastAPI and Flask
ROUTE_DECORATOR_RE = re.compile(
    r"""@\w+\.(get|post|put|delete|patch|route)\s*\("""
    r"""\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)

# CORS wildcard origin
CORS_WILDCARD_RE = re.compile(
    r"""allow_origins\s*=\s*\[\s*['"]?\*['"]?\s*\]"""
)

# camelCase identifier pattern
CAMEL_RE = re.compile(r"\b[a-z]+[A-Z][a-zA-Z]*\b")

# snake_case identifier pattern (at least one underscore)
SNAKE_RE = re.compile(r"\b[a-z]+_[a-z][a-z0-9_]*\b")

# API versioning prefix
VERSIONED_ROUTE_RE = re.compile(r"""/v\d+/""")

# Response with explicit status_code
STATUS_CODE_RE = re.compile(
    r"""status_code\s*=|\.status_code\s*=|"""
    r"""HTTPException|JSONResponse|Response\s*\("""
)


def _is_api_file(filepath: Path, content: str) -> bool:
    """Check if file uses FastAPI or Flask."""
    name = filepath.name
    if name.startswith("test_") or name.endswith("_test.py"):
        return False
    return bool(
        re.search(
            r"from\s+(?:fastapi|flask)\s+import|"
            r"import\s+(?:fastapi|flask)",
            content,
        )
    )


def _has_type_hints(node: ast.FunctionDef) -> bool:
    """Check if function params have type hints."""
    for arg in node.args.args:
        if arg.arg in ("self", "cls"):
            continue
        if arg.annotation is not None:
            return True
    return len(node.args.args) <= 1  # no params besides self


def _has_error_handling(node: ast.FunctionDef) -> bool:
    """Check if function body contains error handling."""
    for child in ast.walk(node):
        if isinstance(child, ast.Try):
            return True
        if isinstance(child, ast.Raise):
            return True
    return False


class APIDesignGuard:
    """Detects API design issues in FastAPI/Flask projects."""

    def scan_file(
        self, filepath: Path, content: str
    ) -> list[V2GuardIssue]:
        """Scan a single file for API design issues."""
        issues: list[V2GuardIssue] = []
        fname = str(filepath)

        if not _is_api_file(filepath, content):
            return issues

        lines = content.splitlines()

        # Check CORS wildcard
        issues.extend(self._check_cors(fname, lines))

        # AST-based checks on route handlers
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return issues

        route_funcs = self._find_route_functions(tree, lines)
        for func_node, route_path in route_funcs:
            issues.extend(
                self._check_route_handler(
                    func_node, route_path, fname, content
                )
            )

        # Mixed naming conventions
        issues.extend(self._check_mixed_naming(fname, lines))
        return issues

    @staticmethod
    def _check_cors(
        fname: str, lines: list[str]
    ) -> list[V2GuardIssue]:
        """Check for CORS wildcard origins."""
        issues: list[V2GuardIssue] = []
        for lineno, line in enumerate(lines, 1):
            if CORS_WILDCARD_RE.search(line):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="block",
                    message=(
                        "CORS allow_origins=['*'] is too "
                        "permissive — restrict to specific domains"
                    ),
                    file=fname,
                    line=lineno,
                ))
        return issues

    @staticmethod
    def _check_route_handler(
        func_node: ast.FunctionDef,
        route_path: str,
        fname: str,
        content: str,
    ) -> list[V2GuardIssue]:
        """Check a single route handler for issues."""
        issues: list[V2GuardIssue] = []
        lineno = func_node.lineno

        if not _has_type_hints(func_node):
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="warn",
                message=f"Route handler '{func_node.name}' lacks type hints for input validation",
                file=fname, line=lineno,
            ))

        if not _has_error_handling(func_node):
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="warn",
                message=f"Route handler '{func_node.name}' has no error handling (try/except or raise)",
                file=fname, line=lineno,
            ))

        if route_path and not VERSIONED_ROUTE_RE.search(route_path):
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="info",
                message=f"Route '{route_path}' has no API version prefix (/v1/, /v2/)",
                file=fname, line=lineno,
            ))

        func_src = ast.get_source_segment(content, func_node)
        if func_src and not STATUS_CODE_RE.search(func_src):
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="info",
                message=f"Route handler '{func_node.name}' returns no explicit status code",
                file=fname, line=lineno,
            ))

        return issues

    def scan(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Scan entire project for API design issues."""
        issues: list[V2GuardIssue] = []
        for pyfile in project_root.rglob("*.py"):
            if ".venv" in pyfile.parts:
                continue
            if "node_modules" in pyfile.parts:
                continue
            try:
                content = pyfile.read_text(
                    encoding="utf-8", errors="ignore"
                )
            except OSError:
                continue
            issues.extend(self.scan_file(pyfile, content))
        return issues

    @staticmethod
    def _find_route_functions(
        tree: ast.Module, lines: list[str]
    ) -> list[tuple[ast.FunctionDef, str]]:
        """Find functions decorated with route decorators."""
        results: list[tuple[ast.FunctionDef, str]] = []
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            for dec in node.decorator_list:
                dec_line = lines[dec.lineno - 1] if (
                    dec.lineno <= len(lines)
                ) else ""
                m = ROUTE_DECORATOR_RE.search(dec_line)
                if m:
                    results.append((node, m.group(2)))
                    break
        return results

    @staticmethod
    def _check_mixed_naming(
        fname: str, lines: list[str]
    ) -> list[V2GuardIssue]:
        """Detect mixed camelCase and snake_case."""
        has_camel = False
        has_snake = False
        # Ignore imports, comments, strings
        for line in lines:
            stripped = line.strip()
            if (
                stripped.startswith("#")
                or stripped.startswith("import ")
                or stripped.startswith("from ")
            ):
                continue
            if CAMEL_RE.search(stripped):
                has_camel = True
            if SNAKE_RE.search(stripped):
                has_snake = True
            if has_camel and has_snake:
                return [V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="info",
                    message=(
                        "Mixed naming conventions "
                        "(camelCase and snake_case) detected"
                    ),
                    file=fname,
                    line=1,
                )]
        return []
