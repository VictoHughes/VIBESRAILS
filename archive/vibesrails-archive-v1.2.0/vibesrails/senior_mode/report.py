"""Senior Mode report generation."""
from dataclasses import dataclass, field

from .claude_reviewer import ReviewResult
from .guards import GuardIssue


@dataclass
class SeniorReport:
    """Senior Mode report."""
    guard_issues: list[GuardIssue] = field(default_factory=list)
    review_result: ReviewResult | None = None
    architecture_updated: bool = False

    def _guard_section(self) -> list[str]:
        """Generate guard issues section."""
        if not self.guard_issues:
            return ["[OK] All guards passed", ""]
        lines = ["-- GUARDS " + "-" * 49]
        for issue in self.guard_issues:
            icon = "[BLOCK]" if issue.severity == "block" else "[WARN]"
            lines.append(f"  {icon} [{issue.guard}] {issue.message}")
            if issue.file:
                lines.append(f"         -> {issue.file}:{issue.line or '?'}")
        lines.append("")
        return lines

    def _review_section(self) -> list[str]:
        """Generate Claude review section."""
        if not self.review_result:
            return []
        if not self.review_result.reviewed:
            return [f"[SKIP] Claude review: {self.review_result.skip_reason}", ""]
        lines = ["-- CLAUDE REVIEW " + "-" * 42]
        lines.append(f"  Score: {self.review_result.score}/10")
        for label, prefix, items in [
            ("Issues", "-", self.review_result.issues),
            ("Strengths", "+", self.review_result.strengths),
            ("Suggestions", ">", self.review_result.suggestions),
        ]:
            if items:
                lines.append(f"  {label}:")
                lines.extend(f"    {prefix} {item}" for item in items)
        lines.append("")
        return lines

    def generate(self) -> str:
        """Generate terminal report."""
        lines = ["", "=" * 60, "                  SENIOR MODE REPORT", "=" * 60, ""]
        lines.extend(self._guard_section())
        lines.extend(self._review_section())

        if self.architecture_updated:
            lines.extend(["[OK] ARCHITECTURE.md updated", ""])

        blocking = [i for i in self.guard_issues if i.severity == "block"]
        warnings = [i for i in self.guard_issues if i.severity == "warn"]
        lines.append("-" * 60)
        lines.append(f"Summary: {len(blocking)} blocking | {len(warnings)} warnings")
        if blocking:
            lines.extend(["", "[BLOCKED] Fix issues before committing"])

        return "\n".join(lines)

    def has_blocking_issues(self) -> bool:
        """Check if any blocking issues exist."""
        return any(i.severity == "block" for i in self.guard_issues)
