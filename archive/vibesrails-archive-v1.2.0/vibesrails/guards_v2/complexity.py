"""Complexity Guard — Detects overly complex functions using AST analysis."""

import ast
import logging
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

# Thresholds
CYCLOMATIC_WARN = 10
CYCLOMATIC_BLOCK = 20
COGNITIVE_WARN = 15
COGNITIVE_BLOCK = 30
PARAM_WARN = 5
PARAM_BLOCK = 8
NESTING_WARN = 4
NESTING_BLOCK = 6
LENGTH_WARN = 50
LENGTH_BLOCK = 100
RETURN_WARN = 5

GUARD_NAME = "complexity"


class ComplexityGuard:
    """Analyzes Python code complexity using AST."""

    _BRANCH_TYPES = (ast.If, ast.IfExp, ast.For, ast.While, ast.ExceptHandler, ast.With)

    def _cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Count cyclomatic complexity: 1 + branches."""
        count = 1
        for child in ast.walk(node):
            if isinstance(child, self._BRANCH_TYPES):
                count += 1
            elif isinstance(child, ast.BoolOp):
                count += len(child.values) - 1
        return count

    @staticmethod
    def _cognitive_increment(child: ast.AST, depth: int) -> int:
        """Calculate cognitive complexity increment for a node."""
        if isinstance(child, (ast.If, ast.IfExp, ast.For, ast.While, ast.ExceptHandler)):
            return 1 + depth
        if isinstance(child, ast.BoolOp):
            return len(child.values) - 1
        return 0

    _NESTING_TYPES = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)

    def _cognitive_complexity(self, node: ast.FunctionDef) -> int:
        """Cognitive complexity: like cyclomatic but penalizes nesting."""
        score = 0

        def _walk(n: ast.AST, depth: int) -> None:
            nonlocal score
            for child in ast.iter_child_nodes(n):
                score += self._cognitive_increment(child, depth)
                next_depth = depth + 1 if isinstance(child, self._NESTING_TYPES) else depth
                _walk(child, next_depth)

        _walk(node, 0)
        return score

    _DEPTH_TYPES = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Try)

    def _nesting_depth(self, node: ast.FunctionDef) -> int:
        """Max nesting depth inside a function."""
        max_depth = 0

        def _walk(n: ast.AST, depth: int) -> None:
            nonlocal max_depth
            for child in ast.iter_child_nodes(n):
                is_nesting = isinstance(child, self._DEPTH_TYPES)
                next_depth = depth + 1 if is_nesting else depth
                if next_depth > max_depth:
                    max_depth = next_depth
                _walk(child, next_depth)

        _walk(node, 0)
        return max_depth

    def _param_count(self, node: ast.FunctionDef) -> int:
        """Count parameters excluding self/cls."""
        args = node.args
        all_args = (
            args.posonlyargs + args.args + args.kwonlyargs
        )
        names = [a.arg for a in all_args]
        count = len(names)
        if names and names[0] in ("self", "cls"):
            count -= 1
        return count

    def _function_length(self, node: ast.FunctionDef) -> int:
        """Line count of a function."""
        return node.end_lineno - node.lineno + 1  # type: ignore[operator]

    def _return_count(self, node: ast.FunctionDef) -> int:
        """Count return statements in a function."""
        return sum(
            1 for child in ast.walk(node)
            if isinstance(child, ast.Return)
        )

    @staticmethod
    def _check_metric(
        value: int, warn_limit: int, block_limit: int,
        name: str, msg_template: str, filepath: str, line: int,
    ) -> V2GuardIssue | None:
        """Check a metric against thresholds. msg_template uses {val} and {limit}."""
        if value > block_limit:
            return V2GuardIssue(
                guard=GUARD_NAME, severity="block",
                message=msg_template.format(name=name, val=value, limit=block_limit),
                file=filepath, line=line,
            )
        if value > warn_limit:
            return V2GuardIssue(
                guard=GUARD_NAME, severity="warn",
                message=msg_template.format(name=name, val=value, limit=warn_limit),
                file=filepath, line=line,
            )
        return None

    def analyze_function(
        self, node: ast.FunctionDef, filepath: str,
    ) -> list[V2GuardIssue]:
        """Analyze a single function node for complexity issues."""
        issues: list[V2GuardIssue] = []
        name = node.name
        line = node.lineno

        metric_checks = [
            (self._cyclomatic_complexity(node), CYCLOMATIC_WARN, CYCLOMATIC_BLOCK,
             "'{name}' cyclomatic complexity {val} > {limit}"),
            (self._cognitive_complexity(node), COGNITIVE_WARN, COGNITIVE_BLOCK,
             "'{name}' cognitive complexity {val} > {limit}"),
            (self._param_count(node), PARAM_WARN, PARAM_BLOCK,
             "'{name}' has {val} params > {limit}"),
            (self._nesting_depth(node), NESTING_WARN, NESTING_BLOCK,
             "'{name}' nesting depth {val} > {limit}"),
            (self._function_length(node), LENGTH_WARN, LENGTH_BLOCK,
             "'{name}' is {val} lines > {limit}"),
        ]

        for value, warn_limit, block_limit, template in metric_checks:
            issue = self._check_metric(value, warn_limit, block_limit, name, template, filepath, line)
            if issue:
                issues.append(issue)

        rc = self._return_count(node)
        if rc > RETURN_WARN:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="warn",
                message=f"'{name}' has {rc} returns > {RETURN_WARN}",
                file=filepath, line=line,
            ))

        return issues

    def scan_file(
        self, filepath: Path, content: str
    ) -> list[V2GuardIssue]:
        """Scan a single file's content for complexity issues."""
        try:
            tree = ast.parse(content, filename=str(filepath))
        except SyntaxError:
            return []

        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                issues.extend(
                    self.analyze_function(node, str(filepath))
                )
        return issues

    def scan(self, project_root: Path) -> list[V2GuardIssue]:
        """Scan all Python files under project_root."""
        issues: list[V2GuardIssue] = []
        for py_file in sorted(project_root.rglob("*.py")):
            # Skip hidden dirs and common non-project dirs
            parts = py_file.parts
            if any(
                p.startswith(".") or p in (
                    "venv", ".venv", "node_modules", "__pycache__",
                    ".tox", ".nox", "dist", "build",
                )
                for p in parts
            ):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            issues.extend(self.scan_file(py_file, content))
        return issues
