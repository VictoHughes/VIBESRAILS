"""VibesRails v2 Guards — Senior-level checks for vibe coders."""

from pathlib import Path

from .api_design import APIDesignGuard
from .architecture_drift import ArchitectureDriftGuard
from .complexity import ComplexityGuard
from .database_safety import DatabaseSafetyGuard
from .dead_code import DeadCodeGuard
from .dependency_audit import DependencyAuditGuard, V2GuardIssue
from .docstring import DocstringGuard
from .env_safety import EnvSafetyGuard
from .git_workflow import GitWorkflowGuard
from .mutation import MutationGuard
from .observability import ObservabilityGuard
from .performance import PerformanceGuard
from .pr_checklist import PRChecklistGuard
from .pre_deploy import PreDeployGuard
from .test_integrity import TestIntegrityGuard
from .type_safety import TypeSafetyGuard

GUARDS_V2_VERSION = "2.0.0"

GUARD_COUNT = 16

ALL_GUARD_CLASSES = (
    DependencyAuditGuard,
    PerformanceGuard,
    ComplexityGuard,
    EnvSafetyGuard,
    GitWorkflowGuard,
    DeadCodeGuard,
    ObservabilityGuard,
    TypeSafetyGuard,
    DocstringGuard,
    PRChecklistGuard,
    DatabaseSafetyGuard,
    APIDesignGuard,
    PreDeployGuard,
    TestIntegrityGuard,
    MutationGuard,
    ArchitectureDriftGuard,
)


def run_all_guards(project_root: Path) -> list[V2GuardIssue]:
    """Run all v2 guards on a project and return combined issues."""
    issues: list[V2GuardIssue] = []
    for guard_cls in ALL_GUARD_CLASSES:
        guard = guard_cls()
        issues.extend(guard.scan(project_root))
    return issues


__all__ = [
    "GUARDS_V2_VERSION",
    "ALL_GUARD_CLASSES",
    "run_all_guards",
    "V2GuardIssue",
    "DependencyAuditGuard",
    "PerformanceGuard",
    "ComplexityGuard",
    "EnvSafetyGuard",
    "GitWorkflowGuard",
    "DeadCodeGuard",
    "ObservabilityGuard",
    "TypeSafetyGuard",
    "DocstringGuard",
    "PRChecklistGuard",
    "DatabaseSafetyGuard",
    "APIDesignGuard",
    "PreDeployGuard",
    "TestIntegrityGuard",
    "MutationGuard",
    "ArchitectureDriftGuard",
]
