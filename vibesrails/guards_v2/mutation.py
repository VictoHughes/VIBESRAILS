"""MutationGuard — Scientifically unfakeable test quality checker.

Uses mutation testing to verify tests actually check logic.
"""

from pathlib import Path

from .dependency_audit import V2GuardIssue
from .mutation_engine import (  # noqa: F401
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
    _count_targets,
    apply_mutation,
    find_test_file,
    get_changed_functions,
    get_source_files,
    mutation_in_functions,
    run_tests_on_mutant,
    scan_file,
)
from .mutation_mutmut import _parse_mutmut_results
from .mutation_mutmut import scan_with_mutmut as _scan_with_mutmut

GUARD_NAME = "MutationGuard"
WARN_THRESHOLD = 0.60
BLOCK_THRESHOLD = 0.30

# Re-export for backward compatibility
__all__ = [
    "MutationGuard",
    "MutantResult",
    "FileMutationReport",
    "MUTATION_TYPES",
    "ComparisonSwapper",
    "BooleanSwapper",
    "ReturnNoneSwapper",
    "ArithmeticSwapper",
    "StatementRemover",
    "GUARD_NAME",
    "MAX_MUTATIONS_PER_FILE",
    "MUTATION_TEST_TIMEOUT",
    "PYTEST_PER_MUTANT_TIMEOUT",
    "WARN_THRESHOLD",
    "BLOCK_THRESHOLD",
    "SKIP_FILES",
]

class MutationGuard:
    """Mutation testing guard for verifying test quality."""

    def _apply_mutation(self, tree, mutation_type, target_idx):
        """Apply a single mutation to an AST tree."""
        return apply_mutation(tree, mutation_type, target_idx)

    def _find_test_file(self, source_path, project_root):
        """Find the test file corresponding to a source file."""
        return find_test_file(source_path, project_root)

    def _run_tests_on_mutant(self, mutant_path, test_path):
        """Run tests against a mutant file."""
        return run_tests_on_mutant(mutant_path, test_path)

    def _scan_file(self, source_path, test_path, project_root,
                   functions_filter=None):
        """Run mutation testing on a single source file."""
        return scan_file(
            source_path, test_path, project_root, functions_filter
        )

    @staticmethod
    def _mutation_in_functions(original, mutated, functions):
        """Check if mutation affects one of the target functions."""
        return mutation_in_functions(original, mutated, functions)

    def _get_source_files(self, project_root):
        """Get all Python source files to mutate."""
        return get_source_files(project_root)

    def _get_changed_functions(self, project_root):
        """Get functions changed in the last git diff."""
        return get_changed_functions(project_root)

    def scan(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Run full mutation testing with built-in engine.

        Args:
            project_root: Root path of the project.

        Returns:
            List of guard issues found.
        """
        issues: list[V2GuardIssue] = []
        reports: list[FileMutationReport] = []
        sources = self._get_source_files(project_root)

        for src in sources:
            test_file = self._find_test_file(src, project_root)
            if test_file is None:
                continue
            report = self._scan_file(
                src, test_file, project_root
            )
            if report.total > 0:
                reports.append(report)

        total_killed = sum(r.killed for r in reports)
        total_all = sum(r.total for r in reports)
        overall = (
            total_killed / total_all if total_all > 0 else 1.0
        )

        for r in reports:
            if r.score < BLOCK_THRESHOLD:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="block",
                    message=(
                        f"{r.file}: mutation score "
                        f"{r.score:.0%} < 30% — "
                        f"tests do not verify logic"
                    ),
                    file=r.file,
                ))
            elif r.score < WARN_THRESHOLD:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        f"{r.file}: mutation score "
                        f"{r.score:.0%} — "
                        f"tests are weak"
                    ),
                    file=r.file,
                ))

            for m in r.results:
                if not m.killed:
                    issues.append(V2GuardIssue(
                        guard=GUARD_NAME,
                        severity="info",
                        message=(
                            f"Surviving mutant in {r.file}: "
                            f"{m.mutation_type}"
                        ),
                        file=r.file,
                        line=m.line,
                    ))

        if total_all > 0 and overall < BLOCK_THRESHOLD:
            issues.insert(0, V2GuardIssue(
                guard=GUARD_NAME,
                severity="block",
                message=(
                    f"Overall mutation score {overall:.0%} "
                    f"< 30% — project tests are unreliable"
                ),
            ))
        elif total_all > 0 and overall < WARN_THRESHOLD:
            issues.insert(0, V2GuardIssue(
                guard=GUARD_NAME,
                severity="warn",
                message=(
                    f"Overall mutation score {overall:.0%} "
                    f"< 60% — project tests need improvement"
                ),
            ))

        return issues

    def scan_quick(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Scan only functions changed in the last git diff."""
        changed = self._get_changed_functions(project_root)
        if not changed:
            return []

        issues: list[V2GuardIssue] = []
        for src_rel, funcs in changed.items():
            src = project_root / src_rel
            if not src.exists():
                continue
            test_file = self._find_test_file(src, project_root)
            if test_file is None:
                continue
            report = self._scan_file(
                src, test_file, project_root,
                functions_filter=funcs,
            )
            if report.total == 0:
                continue
            if report.score < BLOCK_THRESHOLD:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="block",
                    message=(
                        f"{report.file}: mutation score "
                        f"{report.score:.0%} on changed "
                        f"functions — tests unreliable"
                    ),
                    file=report.file,
                ))
            elif report.score < WARN_THRESHOLD:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        f"{report.file}: mutation score "
                        f"{report.score:.0%} on changed "
                        f"functions — tests weak"
                    ),
                    file=report.file,
                ))
        return issues

    def scan_with_mutmut(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Run mutation testing using mutmut if available."""
        return _scan_with_mutmut(project_root)

    def _parse_mutmut_results(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Parse mutmut results output."""
        return _parse_mutmut_results(project_root)

    def generate_report(
        self, project_root: Path
    ) -> str:
        """Generate a human-readable mutation testing report."""
        sources = self._get_source_files(project_root)
        reports: list[FileMutationReport] = []

        for src in sources:
            test_file = self._find_test_file(src, project_root)
            if test_file is None:
                continue
            report = self._scan_file(
                src, test_file, project_root
            )
            if report.total > 0:
                reports.append(report)

        if not reports:
            return "No mutation testing results available."

        total_killed = sum(r.killed for r in reports)
        total_all = sum(r.total for r in reports)
        overall = (
            total_killed / total_all if total_all > 0 else 1.0
        )

        lines = [
            "=== Mutation Testing Report ===",
            f"Overall score: {overall:.0%} "
            f"({total_killed}/{total_all} mutants killed)",
            "",
            "Per-file results:",
        ]

        for r in reports:
            lines.append(
                f"  {r.file}: {r.score:.0%} "
                f"({r.killed}/{r.total})"
            )
            survivors = [
                m for m in r.results if not m.killed
            ]
            if survivors:
                lines.append("    Surviving mutants:")
                for m in survivors:
                    lines.append(
                        f"      - {m.mutation_type}"
                    )

        weak = [r for r in reports if r.score < WARN_THRESHOLD]
        if weak:
            lines.append("")
            lines.append("Advice:")
            for r in weak:
                lines.append(
                    f"  {r.file} has {r.score:.0%} "
                    f"mutation score — tests don't verify its logic"
                )

        return "\n".join(lines)
