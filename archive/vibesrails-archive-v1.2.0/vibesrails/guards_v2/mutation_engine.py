"""Built-in AST-based mutation engine for MutationGuard.

Contains mutation application, test execution, file scanning,
and helper functions. AST visitors live in mutation_visitors.
"""

import ast
import copy
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .mutation_visitors import (
    MUTATION_TYPES,
    ArithmeticSwapper,
    BooleanSwapper,
    ComparisonSwapper,
    FileMutationReport,
    MutantResult,
    ReturnNoneSwapper,
    StatementRemover,
    _count_targets,
)

logger = logging.getLogger(__name__)

MAX_MUTATIONS_PER_FILE = 20
MUTATION_TEST_TIMEOUT = 30
PYTEST_PER_MUTANT_TIMEOUT = 10

SKIP_FILES = {"__init__.py", "conftest.py", "setup.py", "setup.cfg"}

# Re-export visitor symbols for backward compatibility
__all__ = [
    "MutantResult", "FileMutationReport",
    "ComparisonSwapper", "BooleanSwapper", "ReturnNoneSwapper",
    "ArithmeticSwapper", "StatementRemover",
    "MUTATION_TYPES", "_count_targets",
    "apply_mutation", "find_test_file", "run_tests_on_mutant",
    "mutation_in_functions", "scan_file",
    "get_source_files", "get_changed_functions",
    "MAX_MUTATIONS_PER_FILE", "MUTATION_TEST_TIMEOUT",
    "PYTEST_PER_MUTANT_TIMEOUT", "SKIP_FILES",
]


def apply_mutation(
    tree: ast.Module,
    mutation_type: str,
    target_idx: int,
) -> ast.Module | None:
    """Apply a single mutation to an AST tree."""
    tree_copy = copy.deepcopy(tree)
    visitor_cls = MUTATION_TYPES.get(mutation_type)
    if visitor_cls is None:
        return None
    visitor = visitor_cls(target_idx)
    mutated = visitor.visit(tree_copy)
    if not visitor.applied:
        return None
    ast.fix_missing_locations(mutated)
    return mutated


def find_test_file(
    source_path: Path, project_root: Path
) -> Path | None:
    """Find the test file corresponding to a source file."""
    name = source_path.stem
    candidates = [
        project_root / "tests" / f"test_{name}.py",
        project_root / "test" / f"test_{name}.py",
        project_root / f"test_{name}.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def run_tests_on_mutant(
    mutant_path: Path, test_path: Path
) -> bool:
    """Run tests against a mutant. Returns True if mutant survived."""
    env_dir = mutant_path.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(env_dir)
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                str(test_path),
                f"--timeout={PYTEST_PER_MUTANT_TIMEOUT}",
                "--no-header", "-q", "--tb=no", "-x",
            ],
            capture_output=True,
            timeout=MUTATION_TEST_TIMEOUT,
            cwd=str(env_dir),
            env=env,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def mutation_in_functions(
    original: ast.Module,
    mutated: ast.Module,
    functions: set[str],
) -> bool:
    """Check if mutation affects one of the target functions."""
    orig_code = ast.unparse(original)
    mut_code = ast.unparse(mutated)
    if orig_code == mut_code:
        return False
    for node in ast.walk(mutated):
        if isinstance(node, ast.FunctionDef):
            if node.name in functions:
                return True
    return len(functions) == 0


def _collect_mutations(tree: ast.Module) -> list[tuple[str, int]]:
    """Collect all possible mutations from an AST."""
    mutations: list[tuple[str, int]] = []
    for mut_type in MUTATION_TYPES:
        count = _count_targets(tree, mut_type)
        for idx in range(count):
            mutations.append((mut_type, idx))
    return mutations[:MAX_MUTATIONS_PER_FILE]


def _should_skip_mutation(
    mutated, tree, functions_filter: set[str] | None,
) -> bool:
    """Check if a mutation should be skipped."""
    if mutated is None:
        return True
    if functions_filter is not None:
        return not mutation_in_functions(tree, mutated, functions_filter)
    return False


def _run_single_mutation(
    mut_type: str, idx: int, tree: ast.Module,
    functions_filter: set[str] | None,
    tmp_src: Path, tmp_test: Path, report: "FileMutationReport",
) -> None:
    """Run a single mutation and update report."""
    mutated = apply_mutation(tree, mut_type, idx)
    if _should_skip_mutation(mutated, tree, functions_filter):
        return
    report.total += 1
    try:
        mutant_code = ast.unparse(mutated)
    except Exception:
        report.total -= 1
        return
    tmp_src.write_text(mutant_code, encoding="utf-8")
    survived = run_tests_on_mutant(tmp_src, tmp_test)
    report.results.append(MutantResult(
        file=report.file, function="unknown",
        mutation_type=mut_type, line=0, killed=not survived,
    ))
    if survived:
        report.survived += 1
    else:
        report.killed += 1


def scan_file(
    source_path: Path, test_path: Path, project_root: Path,
    functions_filter: set[str] | None = None,
) -> FileMutationReport:
    """Run mutation testing on a single source file."""
    report = FileMutationReport(file=str(source_path.relative_to(project_root)))
    try:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return report

    mutations = _collect_mutations(tree)
    if not mutations:
        return report

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        tmp_test = tmp_dir / "tests" / test_path.name
        tmp_test.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(test_path, tmp_test)

        tmp_src = tmp_dir / source_path.relative_to(project_root)
        tmp_src.parent.mkdir(parents=True, exist_ok=True)

        for mut_type, idx in mutations:
            _run_single_mutation(mut_type, idx, tree, functions_filter, tmp_src, tmp_test, report)

    return report


def get_source_files(project_root: Path) -> list[Path]:
    """Get all Python source files to mutate."""
    files = []
    for f in project_root.rglob("*.py"):
        if f.name in SKIP_FILES:
            continue
        if "test" in f.name.lower():
            continue
        rel_parts = f.relative_to(project_root).parts
        if any("test" in p.lower() for p in rel_parts[:-1]):
            continue
        if ".venv" in str(f) or "__pycache__" in str(f):
            continue
        files.append(f)
    return sorted(set(files))


def _parse_diff_line(line: str, current_file: str | None, changed: dict[str, set[str]]) -> str | None:
    """Parse a single diff line and return updated current_file."""
    if line.startswith("+++ b/"):
        f = line[6:]
        return f if f.endswith(".py") else None
    if line.startswith("@@") and current_file is not None and "def " in line:
        parts = line.split("def ", 1)
        if len(parts) > 1:
            fname = parts[1].split("(")[0].strip()
            changed.setdefault(current_file, set()).add(fname)
    return current_file


def get_changed_functions(project_root: Path) -> dict[str, set[str]]:
    """Get functions changed in the last git diff."""
    try:
        result = subprocess.run(
            ["git", "diff", "--unified=0", "HEAD~1"],
            capture_output=True, text=True,
            cwd=str(project_root), timeout=10,
        )
        if result.returncode != 0:
            return {}
    except (subprocess.TimeoutExpired, OSError):
        return {}

    changed: dict[str, set[str]] = {}
    current_file: str | None = None
    for line in result.stdout.splitlines():
        current_file = _parse_diff_line(line, current_file, changed)
    return changed
