"""Senior Mode report generation."""
from dataclasses import dataclass, field
from .guards import GuardIssue
from .claude_reviewer import ReviewResult


@dataclass
class SeniorReport:
    """Senior Mode report."""
    guard_issues: list[GuardIssue] = field(default_factory=list)
    review_result: ReviewResult | None = None
    architecture_updated: bool = False

    def generate(self) -> str:
        """Generate terminal report."""
        lines = [
            "",
            "=" * 60,
            "                  SENIOR MODE REPORT",
            "=" * 60,
            "",
        ]

        # Guard issues
        if self.guard_issues:
            lines.append("-- GUARDS " + "-" * 49)
            for issue in self.guard_issues:
                icon = "[BLOCK]" if issue.severity == "block" else "[WARN]"
                lines.append(f"  {icon} [{issue.guard}] {issue.message}")
                if issue.file:
                    lines.append(f"         -> {issue.file}:{issue.line or '?'}")
            lines.append("")
        else:
            lines.append("[OK] All guards passed")
            lines.append("")

        # Claude review
        if self.review_result and self.review_result.reviewed:
            lines.append("-- CLAUDE REVIEW " + "-" * 42)
            lines.append(f"  Score: {self.review_result.score}/10")

            if self.review_result.issues:
                lines.append("  Issues:")
                for issue in self.review_result.issues:
                    lines.append(f"    - {issue}")

            if self.review_result.strengths:
                lines.append("  Strengths:")
                for s in self.review_result.strengths:
                    lines.append(f"    + {s}")

            if self.review_result.suggestions:
                lines.append("  Suggestions:")
                for s in self.review_result.suggestions:
                    lines.append(f"    > {s}")

            lines.append("")
        elif self.review_result and not self.review_result.reviewed:
            lines.append(f"[SKIP] Claude review: {self.review_result.skip_reason}")
            lines.append("")

        # Architecture
        if self.architecture_updated:
            lines.append("[OK] ARCHITECTURE.md updated")
            lines.append("")

        # Summary
        blocking = [i for i in self.guard_issues if i.severity == "block"]
        warnings = [i for i in self.guard_issues if i.severity == "warn"]

        lines.append("-" * 60)
        lines.append(f"Summary: {len(blocking)} blocking | {len(warnings)} warnings")

        if blocking:
            lines.append("")
            lines.append("[BLOCKED] Fix issues before committing")

        return "\n".join(lines)

    def has_blocking_issues(self) -> bool:
        """Check if any blocking issues exist."""
        return any(i.severity == "block" for i in self.guard_issues)
