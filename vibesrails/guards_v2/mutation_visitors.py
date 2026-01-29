"""AST mutation visitors and data classes for the mutation engine."""

import ast
import copy
from dataclasses import dataclass, field


@dataclass
class MutantResult:
    """Result of testing a single mutant."""

    file: str
    function: str
    mutation_type: str
    line: int
    killed: bool


@dataclass
class FileMutationReport:
    """Mutation results for a single file."""

    file: str
    total: int = 0
    killed: int = 0
    survived: int = 0
    results: list[MutantResult] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Mutation score as a ratio (0.0 to 1.0)."""
        if self.total == 0:
            return 1.0
        return self.killed / self.total


class ComparisonSwapper(ast.NodeTransformer):
    """Swap comparison operators."""

    SWAPS = {
        ast.Gt: ast.Lt, ast.Lt: ast.Gt,
        ast.GtE: ast.LtE, ast.LtE: ast.GtE,
        ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
    }

    def __init__(self, target_idx: int) -> None:
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied = False

    def visit_Compare(self, node: ast.Compare) -> ast.Compare:
        for i, op in enumerate(node.ops):
            if type(op) in self.SWAPS:
                if self.current_idx == self.target_idx:
                    node.ops[i] = self.SWAPS[type(op)]()
                    self.applied = True
                    return node
                self.current_idx += 1
        return node


class BooleanSwapper(ast.NodeTransformer):
    """Swap True/False and and/or."""

    def __init__(self, target_idx: int) -> None:
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied = False

    def visit_Constant(self, node: ast.Constant) -> ast.Constant:
        if isinstance(node.value, bool):
            if self.current_idx == self.target_idx:
                node.value = not node.value
                self.applied = True
                return node
            self.current_idx += 1
        return node

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.BoolOp:
        self.generic_visit(node)
        if isinstance(node.op, ast.And):
            if self.current_idx == self.target_idx:
                node.op = ast.Or()
                self.applied = True
                return node
            self.current_idx += 1
        elif isinstance(node.op, ast.Or):
            if self.current_idx == self.target_idx:
                node.op = ast.And()
                self.applied = True
                return node
            self.current_idx += 1
        return node


class ReturnNoneSwapper(ast.NodeTransformer):
    """Replace return values with None."""

    def __init__(self, target_idx: int) -> None:
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied = False

    def visit_Return(self, node: ast.Return) -> ast.Return:
        if node.value is not None:
            if self.current_idx == self.target_idx:
                node.value = ast.Constant(value=None)
                self.applied = True
                return node
            self.current_idx += 1
        return node


class ArithmeticSwapper(ast.NodeTransformer):
    """Swap arithmetic operators."""

    SWAPS = {
        ast.Add: ast.Sub, ast.Sub: ast.Add,
        ast.Mult: ast.Div, ast.Div: ast.Mult,
    }

    def __init__(self, target_idx: int) -> None:
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied = False

    def visit_BinOp(self, node: ast.BinOp) -> ast.BinOp:
        self.generic_visit(node)
        if type(node.op) in self.SWAPS:
            if self.current_idx == self.target_idx:
                node.op = self.SWAPS[type(node.op)]()
                self.applied = True
                return node
            self.current_idx += 1
        return node


class StatementRemover(ast.NodeTransformer):
    """Remove a statement from a function body."""

    def __init__(self, target_idx: int) -> None:
        self.target_idx = target_idx
        self.current_idx = 0
        self.applied = False

    def visit_FunctionDef(
        self, node: ast.FunctionDef
    ) -> ast.FunctionDef:
        if len(node.body) <= 1:
            return node
        new_body = []
        for stmt in node.body:
            if self.current_idx == self.target_idx:
                self.applied = True
                self.current_idx += 1
                continue
            new_body.append(stmt)
            self.current_idx += 1
        if new_body:
            node.body = new_body
        return node


MUTATION_TYPES = {
    "comparison_swap": ComparisonSwapper,
    "boolean_swap": BooleanSwapper,
    "return_none": ReturnNoneSwapper,
    "arithmetic_swap": ArithmeticSwapper,
    "statement_remove": StatementRemover,
}


def _count_targets(tree: ast.Module, mutation_type: str) -> int:
    """Count how many mutation targets exist for a type."""
    counter = MUTATION_TYPES[mutation_type](target_idx=999999)
    counter.visit(copy.deepcopy(tree))
    return counter.current_idx
