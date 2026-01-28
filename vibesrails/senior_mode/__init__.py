"""Senior Mode - Architecture mapping and intelligent guards for AI sessions."""
from .architecture_mapper import ArchitectureMapper
from .guards import (
    DiffSizeGuard,
    ErrorHandlingGuard,
    HallucinationGuard,
    DependencyGuard,
    TestCoverageGuard,
    SeniorGuards,
    GuardIssue,
)
from .claude_reviewer import ClaudeReviewer, ReviewResult

__all__ = [
    "ArchitectureMapper",
    "DiffSizeGuard",
    "ErrorHandlingGuard",
    "HallucinationGuard",
    "DependencyGuard",
    "TestCoverageGuard",
    "SeniorGuards",
    "GuardIssue",
    "ClaudeReviewer",
    "ReviewResult",
]
