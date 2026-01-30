"""Tests for GitWorkflowGuard — real git repos, minimal mocking."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from vibesrails.guards_v2.git_workflow import GitWorkflowGuard, _run_git


def _init_git(tmp_path: Path, branch: str = "main") -> None:
    """Initialize a real git repo with an initial commit."""
    subprocess.run(["git", "init", "-b", branch], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True,
    )
    # Need at least one commit for branch to exist
    (tmp_path / "README.md").write_text("# test\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: initial commit"],
        cwd=tmp_path, capture_output=True,
    )


# ── check_branch (real git) ─────────────────────────────────


def test_branch_main_warns(tmp_path: Path):
    """Working on main should warn."""
    _init_git(tmp_path, branch="main")
    guard = GitWorkflowGuard(tmp_path)
    issues = guard.check_branch()
    assert len(issues) == 1
    assert issues[0].severity == "warn"
    assert "main" in issues[0].message


def test_branch_master_warns(tmp_path: Path):
    """Working on master should warn."""
    _init_git(tmp_path, branch="master")
    guard = GitWorkflowGuard(tmp_path)
    issues = guard.check_branch()
    assert len(issues) == 1
    assert "master" in issues[0].message


def test_branch_feature_ok(tmp_path: Path):
    """feature/ branch should pass."""
    _init_git(tmp_path, branch="main")
    subprocess.run(
        ["git", "checkout", "-b", "feature/add-login"],
        cwd=tmp_path, capture_output=True,
    )
    guard = GitWorkflowGuard(tmp_path)
    assert guard.check_branch() == []


def test_branch_fix_ok(tmp_path: Path):
    """fix/ branch should pass."""
    _init_git(tmp_path, branch="main")
    subprocess.run(
        ["git", "checkout", "-b", "fix/broken-auth"],
        cwd=tmp_path, capture_output=True,
    )
    guard = GitWorkflowGuard(tmp_path)
    assert guard.check_branch() == []


def test_branch_bad_name_info(tmp_path: Path):
    """Non-conventional branch name emits info."""
    _init_git(tmp_path, branch="main")
    subprocess.run(
        ["git", "checkout", "-b", "my-random-stuff"],
        cwd=tmp_path, capture_output=True,
    )
    guard = GitWorkflowGuard(tmp_path)
    issues = guard.check_branch()
    assert len(issues) == 1
    assert issues[0].severity == "info"


# ── check_commit_message (no git needed) ─────────────────────


def test_commit_msg_empty_blocks(tmp_path: Path):
    """Empty message should block."""
    guard = GitWorkflowGuard(tmp_path)
    issues = guard.check_commit_message("")
    assert len(issues) == 1
    assert issues[0].severity == "block"


def test_commit_msg_whitespace_blocks(tmp_path: Path):
    """Whitespace-only message should block."""
    guard = GitWorkflowGuard(tmp_path)
    issues = guard.check_commit_message("   \n  ")
    assert len(issues) == 1
    assert issues[0].severity == "block"


def test_commit_msg_conventional_valid(tmp_path: Path):
    """Conventional commit message passes."""
    guard = GitWorkflowGuard(tmp_path)
    assert guard.check_commit_message("feat(cli): add flag") == []


def test_commit_msg_no_scope_valid(tmp_path: Path):
    """Conventional commit without scope passes."""
    guard = GitWorkflowGuard(tmp_path)
    assert guard.check_commit_message("fix: typo in docs") == []


def test_commit_msg_bad_format_warns(tmp_path: Path):
    """Non-conventional message warns."""
    guard = GitWorkflowGuard(tmp_path)
    issues = guard.check_commit_message("updated stuff")
    assert len(issues) == 1
    assert issues[0].severity == "warn"


def test_commit_msg_all_types_valid(tmp_path: Path):
    """All conventional commit types pass."""
    guard = GitWorkflowGuard(tmp_path)
    for ctype in ("feat", "fix", "refactor", "test", "docs", "chore", "style", "perf", "ci", "build"):
        assert guard.check_commit_message(f"{ctype}: something") == [], f"Failed for {ctype}"


# ── check_staged_files (real git) ────────────────────────────


def test_mixed_staged_unstaged_warns(tmp_path: Path):
    """Mixed staged and unstaged changes should warn."""
    _init_git(tmp_path)
    # Create and stage one file
    (tmp_path / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "a.py"], cwd=tmp_path, capture_output=True)
    # Create another file and modify without staging
    (tmp_path / "b.py").write_text("y = 2\n")
    subprocess.run(["git", "add", "b.py"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: add b"],
        cwd=tmp_path, capture_output=True,
    )
    # Now stage a.py change, leave b.py unstaged change
    (tmp_path / "a.py").write_text("x = 10\n")
    subprocess.run(["git", "add", "a.py"], cwd=tmp_path, capture_output=True)
    (tmp_path / "b.py").write_text("y = 20\n")  # unstaged

    guard = GitWorkflowGuard(tmp_path)
    issues = guard.check_staged_files()
    assert any("Mixed" in i.message for i in issues)


def test_unfocused_commit_warns(tmp_path: Path):
    """Staged files in >3 dirs should warn."""
    _init_git(tmp_path)
    for d in ("a", "b", "c", "d"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "file.py").write_text(f"{d} = 1\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)

    guard = GitWorkflowGuard(tmp_path)
    issues = guard.check_staged_files()
    assert any("directories" in i.message for i in issues)


def test_focused_commit_ok(tmp_path: Path):
    """Staged files in <=3 dirs is fine."""
    _init_git(tmp_path)
    for d in ("src", "tests"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "file.py").write_text(f"{d} = 1\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)

    guard = GitWorkflowGuard(tmp_path)
    issues = guard.check_staged_files()
    assert not any("directories" in i.message for i in issues)


# ── scan (real git) ──────────────────────────────────────────


def test_scan_not_git_repo(tmp_path: Path):
    """Non-git directory returns empty."""
    guard = GitWorkflowGuard(tmp_path)
    assert guard.scan(tmp_path) == []


def test_scan_runs_all_checks_real(tmp_path: Path):
    """scan on a real repo on main triggers branch warning."""
    _init_git(tmp_path, branch="main")
    guard = GitWorkflowGuard(tmp_path)
    issues = guard.scan(tmp_path)
    assert any("main" in i.message for i in issues)


def test_scan_feature_branch_clean(tmp_path: Path):
    """scan on a real feature branch with good commit is clean."""
    _init_git(tmp_path, branch="main")
    subprocess.run(
        ["git", "checkout", "-b", "feature/new-thing"],
        cwd=tmp_path, capture_output=True,
    )
    # Make a proper commit on the feature branch
    (tmp_path / "new.py").write_text("print('new')\n")
    subprocess.run(["git", "add", "new.py"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: add new module"],
        cwd=tmp_path, capture_output=True,
    )
    guard = GitWorkflowGuard(tmp_path)
    issues = guard.scan(tmp_path)
    # Should be clean — good branch, good commit msg, no mixed files
    assert not any(i.severity == "block" for i in issues)


# ── Force push detection (mock only — can't safely test) ─────


@patch("subprocess.run")
def test_force_push_detected(mock_run, tmp_path: Path):
    """Force push in reflog should warn (mocked for safety)."""
    def _side_effect(args, **kwargs):
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        r = R()
        if "reflog" in args:
            r.stdout = "push --force\ncommit: feat: add x"
        elif "rev-parse" in args and "--git-dir" in args:
            r.stdout = ".git"
        elif "rev-parse" in args and "--abbrev-ref" in args:
            r.stdout = "feature/ok"
        elif "diff" in args:
            r.stdout = ""
        elif "log" in args:
            r.stdout = "feat: ok"
        return r
    mock_run.side_effect = _side_effect

    guard = GitWorkflowGuard(tmp_path)
    issues = guard.check_force_push()
    assert any("Force push" in i.message for i in issues)


# ── _run_git edge cases ──────────────────────────────────────


def test_run_git_timeout(tmp_path: Path):
    """Timeout returns (False, '')."""
    with patch("subprocess.run",
               side_effect=subprocess.TimeoutExpired("git", 10)):
        ok, out = _run_git(["status"], tmp_path)
    assert ok is False
    assert out == ""


def test_run_git_real_command(tmp_path: Path):
    """_run_git works on a real git repo."""
    _init_git(tmp_path)
    ok, out = _run_git(["rev-parse", "--git-dir"], tmp_path)
    assert ok is True
    assert ".git" in out
