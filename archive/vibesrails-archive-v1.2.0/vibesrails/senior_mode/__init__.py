"""Senior Mode - Architecture mapping and intelligent guards for AI sessions."""
from .architecture_mapper import ArchitectureMapper
from .claude_reviewer import ClaudeReviewer, ReviewResult
from .guards import (
    DependencyGuard,
    DiffSizeGuard,
    ErrorHandlingGuard,
    GuardIssue,
    HallucinationGuard,
    SeniorGuards,
    TestCoverageGuard,
)

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
