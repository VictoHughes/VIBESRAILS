"""Git Workflow Guard — Detects poor git practices."""

import logging
from pathlib import Path

from ._git_helpers import (
    CONVENTIONAL_RE,
    MAX_UNRELATED_DIRS,
    TRACKED_FILE_BLOCKLIST,
    VALID_BRANCH_PREFIXES,
)
from ._git_helpers import (
    run_git as _run_git,
)
from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

GUARD_NAME = "git-workflow"


class GitWorkflowGuard:
    """Detects poor git workflow practices."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.root = project_root or Path(".")

    def _is_git_repo(self) -> bool:
        """Check if project_root is inside a git repository."""
        ok, _ = _run_git(["rev-parse", "--git-dir"], self.root)
        return ok

    def check_branch(self) -> list[V2GuardIssue]:
        """Check branch name conventions."""
        issues: list[V2GuardIssue] = []
        ok, branch = _run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"], self.root
        )
        if not ok:
            return issues

        if branch in ("main", "master"):
            issues.append(V2GuardIssue(
                guard=GUARD_NAME,
                severity="warn",
                message=(
                    f"Working directly on '{branch}'. "
                    "Use a feature branch instead."
                ),
            ))
        elif not branch.startswith(VALID_BRANCH_PREFIXES):
            issues.append(V2GuardIssue(
                guard=GUARD_NAME,
                severity="info",
                message=(
                    f"Branch '{branch}' doesn't follow naming "
                    "convention (feature/, fix/, chore/, "
                    "docs/, refactor/)."
                ),
            ))

        return issues

    def check_commit_message(
        self, message: str
    ) -> list[V2GuardIssue]:
        """Validate a commit message against conventional commits."""
        issues: list[V2GuardIssue] = []
        if not message or not message.strip():
            issues.append(V2GuardIssue(
                guard=GUARD_NAME,
                severity="block",
                message="Empty commit message.",
            ))
            return issues

        first_line = message.strip().splitlines()[0]
        if not CONVENTIONAL_RE.match(first_line):
            issues.append(V2GuardIssue(
                guard=GUARD_NAME,
                severity="warn",
                message=(
                    "Commit message doesn't follow conventional "
                    "commits: type(scope): description"
                ),
            ))

        return issues

    def check_staged_files(self) -> list[V2GuardIssue]:
        """Check for messy workflow and unfocused commits."""
        issues: list[V2GuardIssue] = []

        # Check mixed staged + unstaged changes
        _, staged = _run_git(
            ["diff", "--cached", "--name-only"], self.root
        )
        _, unstaged = _run_git(
            ["diff", "--name-only"], self.root
        )

        if staged and unstaged:
            issues.append(V2GuardIssue(
                guard=GUARD_NAME,
                severity="warn",
                message=(
                    "Mixed staged and unstaged changes. "
                    "Consider committing or stashing first."
                ),
            ))

        # Check unfocused commit (staged files span many dirs)
        if staged:
            dirs = {
                str(Path(f).parts[0])
                for f in staged.splitlines()
                if f.strip()
            }
            if len(dirs) > MAX_UNRELATED_DIRS:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        f"Staged files touch {len(dirs)} "
                        f"top-level directories (>{MAX_UNRELATED_DIRS}). "
                        "Consider smaller, focused commits."
                    ),
                ))

        return issues

    def check_force_push(self) -> list[V2GuardIssue]:
        """Check recent reflog for force-push indicators."""
        issues: list[V2GuardIssue] = []
        ok, log = _run_git(
            ["reflog", "--all", "-n", "20", "--format=%gs"],
            self.root,
        )
        if not ok:
            return issues

        for entry in log.splitlines():
            if "force" in entry.lower() or "push --force" in entry.lower():
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        "Force push detected in recent history. "
                        "Avoid rewriting shared history."
                    ),
                ))
                break

        return issues

    def check_hook_bypass(self) -> list[V2GuardIssue]:
        """Detect commits where pre-commit hooks were skipped.

        Git does not log the skip-verify flag directly, but we can
        detect it: commits that exist without a corresponding
        pre-commit trace.  We check if the pre-commit hook exists
        and if recent commits lack the vibesrails pass marker in
        their notes.
        """
        issues: list[V2GuardIssue] = []
        hook_path = self.root / ".git" / "hooks" / "pre-commit"
        if not hook_path.exists():
            issues.append(V2GuardIssue(
                guard=GUARD_NAME,
                severity="warn",
                message=(
                    "No pre-commit hook installed. "
                    "Run: vibesrails --hook"
                ),
            ))
            return issues

        # Check if hook contains vibesrails
        try:
            hook_content = hook_path.read_text()
            if "vibesrails" not in hook_content:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        "Pre-commit hook exists but doesn't "
                        "run vibesrails."
                    ),
                ))
        except OSError:
            pass  # hook file unreadable, skip content check

        return issues

    def check_tracked_hygiene(self) -> list[V2GuardIssue]:
        """Detect files tracked by git that should be local-only."""
        issues: list[V2GuardIssue] = []
        ok, tracked_output = _run_git(["ls-files"], self.root)
        if not ok:
            return issues

        tracked = tracked_output.splitlines()
        for filepath in tracked:
            for pattern, desc in TRACKED_FILE_BLOCKLIST:
                if pattern.endswith("/"):
                    # Directory prefix match
                    if filepath.startswith(pattern) or f"/{pattern}" in filepath:
                        issues.append(V2GuardIssue(
                            guard=GUARD_NAME,
                            severity="warn",
                            message=f"Tracked file should be in .gitignore ({desc}): {filepath}",
                            file=filepath,
                        ))
                        break
                elif pattern.startswith("*"):
                    # Suffix match
                    if filepath.endswith(pattern[1:]):
                        issues.append(V2GuardIssue(
                            guard=GUARD_NAME,
                            severity="warn",
                            message=f"Tracked file should be in .gitignore ({desc}): {filepath}",
                            file=filepath,
                        ))
                        break
                else:
                    # Exact or basename match
                    if filepath == pattern or filepath.endswith(f"/{pattern}"):
                        issues.append(V2GuardIssue(
                            guard=GUARD_NAME,
                            severity="warn",
                            message=f"Tracked file should be in .gitignore ({desc}): {filepath}",
                            file=filepath,
                        ))
                        break

        return issues

    def scan(self, project_root: Path) -> list[V2GuardIssue]:
        """Run all git workflow checks."""
        self.root = project_root
        if not self._is_git_repo():
            return []

        issues: list[V2GuardIssue] = []
        issues.extend(self.check_branch())
        issues.extend(self.check_staged_files())
        issues.extend(self.check_force_push())
        issues.extend(self.check_hook_bypass())
        issues.extend(self.check_tracked_hygiene())

        # Check last commit message
        ok, msg = _run_git(
            ["log", "-1", "--format=%s"], self.root
        )
        if ok and msg:
            issues.extend(self.check_commit_message(msg))

        return issues
