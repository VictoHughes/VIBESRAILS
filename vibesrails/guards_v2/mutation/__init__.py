"""Mutation testing package for VibesRails guards v2.

Re-exports all public symbols for backward compatibility.
Internal modules: guard, engine, visitors, mutmut.
"""

from .engine import (
    MAX_MUTATIONS_PER_FILE,
    MUTATION_TEST_TIMEOUT,
    MUTATION_TYPES,
    PYTEST_PER_MUTANT_TIMEOUT,
    SKIP_FILES,
    ArithmeticSwapper,
    BooleanSwapper,
    ComparisonSwapper,
    FileMutationReport,
    MutantResult,
    ReturnNoneSwapper,
    StatementRemover,
    _collect_mutations,
    _count_targets,
    _parse_diff_line,
    _should_skip_mutation,
    apply_mutation,
    find_test_file,
    get_changed_functions,
    get_source_files,
    mutation_in_functions,
    run_tests_on_mutant,
    scan_file,
)
from .guard import (
    BLOCK_THRESHOLD,
    GUARD_NAME,
    WARN_THRESHOLD,
    MutationGuard,
)
from .mutmut import _parse_mutmut_results, scan_with_mutmut

__all__ = [
    # Guard
    "MutationGuard",
    "GUARD_NAME",
    "WARN_THRESHOLD",
    "BLOCK_THRESHOLD",
    # Data classes
    "MutantResult",
    "FileMutationReport",
    # Visitors
    "ComparisonSwapper",
    "BooleanSwapper",
    "ReturnNoneSwapper",
    "ArithmeticSwapper",
    "StatementRemover",
    "MUTATION_TYPES",
    "_count_targets",
    # Engine
    "apply_mutation",
    "find_test_file",
    "run_tests_on_mutant",
    "mutation_in_functions",
    "scan_file",
    "get_source_files",
    "get_changed_functions",
    "_collect_mutations",
    "_should_skip_mutation",
    "_parse_diff_line",
    # Constants
    "MAX_MUTATIONS_PER_FILE",
    "MUTATION_TEST_TIMEOUT",
    "PYTEST_PER_MUTANT_TIMEOUT",
    "SKIP_FILES",
    # Mutmut
    "scan_with_mutmut",
    "_parse_mutmut_results",
]
