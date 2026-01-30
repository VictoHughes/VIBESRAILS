"""Complexity Guard — Detects overly complex functions using AST analysis."""

import ast
from pathlib import Path

from .dependency_audit import V2GuardIssue

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

    def _cognitive_complexity(self, node: ast.FunctionDef) -> int:
        """Cognitive complexity: like cyclomatic but penalizes nesting."""
        score = 0

        def _walk(n: ast.AST, depth: int) -> None:
            nonlocal score
            for child in ast.iter_child_nodes(n):
                increment = 0
                nesting_bump = 0
                if isinstance(child, (ast.If, ast.IfExp)):
                    increment = 1
                    nesting_bump = depth
                elif isinstance(child, (ast.For, ast.While)):
                    increment = 1
                    nesting_bump = depth
                elif isinstance(child, ast.ExceptHandler):
                    increment = 1
                    nesting_bump = depth
                elif isinstance(child, ast.BoolOp):
                    increment = len(child.values) - 1

                score += increment + nesting_bump

                # Increase depth for nesting constructs
                if isinstance(child, (ast.If, ast.For, ast.While,
                                      ast.ExceptHandler, ast.With)):
                    _walk(child, depth + 1)
                else:
                    _walk(child, depth)

        _walk(node, 0)
        return score

    def _nesting_depth(self, node: ast.FunctionDef) -> int:
        """Max nesting depth inside a function."""
        max_depth = 0

        def _walk(n: ast.AST, depth: int) -> None:
            nonlocal max_depth
            for child in ast.iter_child_nodes(n):
                if isinstance(child, (ast.If, ast.For, ast.While,
                                      ast.ExceptHandler, ast.With,
                                      ast.Try)):
                    new_depth = depth + 1
                    if new_depth > max_depth:
                        max_depth = new_depth
                    _walk(child, new_depth)
                else:
                    _walk(child, depth)

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

    def analyze_function(
        self, node: ast.FunctionDef, filepath: str
    ) -> list[V2GuardIssue]:
        """Analyze a single function node for complexity issues."""
        issues: list[V2GuardIssue] = []
        name = node.name
        line = node.lineno

        # Cyclomatic
        cc = self._cyclomatic_complexity(node)
        if cc > CYCLOMATIC_BLOCK:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="block",
                message=f"'{name}' cyclomatic complexity {cc} > {CYCLOMATIC_BLOCK}",
                file=filepath, line=line,
            ))
        elif cc > CYCLOMATIC_WARN:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="warn",
                message=f"'{name}' cyclomatic complexity {cc} > {CYCLOMATIC_WARN}",
                file=filepath, line=line,
            ))

        # Cognitive
        cog = self._cognitive_complexity(node)
        if cog > COGNITIVE_BLOCK:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="block",
                message=f"'{name}' cognitive complexity {cog} > {COGNITIVE_BLOCK}",
                file=filepath, line=line,
            ))
        elif cog > COGNITIVE_WARN:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="warn",
                message=f"'{name}' cognitive complexity {cog} > {COGNITIVE_WARN}",
                file=filepath, line=line,
            ))

        # Params
        pc = self._param_count(node)
        if pc > PARAM_BLOCK:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="block",
                message=f"'{name}' has {pc} params > {PARAM_BLOCK}",
                file=filepath, line=line,
            ))
        elif pc > PARAM_WARN:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="warn",
                message=f"'{name}' has {pc} params > {PARAM_WARN}",
                file=filepath, line=line,
            ))

        # Nesting
        nd = self._nesting_depth(node)
        if nd > NESTING_BLOCK:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="block",
                message=f"'{name}' nesting depth {nd} > {NESTING_BLOCK}",
                file=filepath, line=line,
            ))
        elif nd > NESTING_WARN:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="warn",
                message=f"'{name}' nesting depth {nd} > {NESTING_WARN}",
                file=filepath, line=line,
            ))

        # Length
        fl = self._function_length(node)
        if fl > LENGTH_BLOCK:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="block",
                message=f"'{name}' is {fl} lines > {LENGTH_BLOCK}",
                file=filepath, line=line,
            ))
        elif fl > LENGTH_WARN:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="warn",
                message=f"'{name}' is {fl} lines > {LENGTH_WARN}",
                file=filepath, line=line,
            ))

        # Returns
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
