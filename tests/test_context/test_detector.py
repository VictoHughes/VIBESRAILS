"""Tests for context detector — signal collection from git."""

from unittest import mock

from vibesrails.context.detector import (
    ContextDetector,
    _classify_branch,
    _parse_diff_stat,
)

# ============================================
# _classify_branch
# ============================================


def test_classify_feature_branches():
    """Feature-type branches are detected."""
    assert _classify_branch("feat/new-widget") == "feature"
    assert _classify_branch("feature/auth-flow") == "feature"


def test_classify_fix_branches():
    """Fix-type branches are detected."""
    assert _classify_branch("fix/null-pointer") == "fix"
    assert _classify_branch("bug/crash-on-start") == "fix"
    assert _classify_branch("bugfix/login-issue") == "fix"
    assert _classify_branch("hotfix/security-patch") == "fix"
    assert _classify_branch("patch/typo") == "fix"


def test_classify_spike_branches():
    """Spike/experiment branches are detected."""
    assert _classify_branch("spike/new-db") == "spike"
    assert _classify_branch("exp/ai-scoring") == "spike"
    assert _classify_branch("experiment/new-algo") == "spike"


def test_classify_unknown_branches():
    """Unrecognized prefixes return unknown."""
    assert _classify_branch("main") == "unknown"
    assert _classify_branch("develop") == "unknown"
    assert _classify_branch("my-branch") == "unknown"


def test_classify_case_insensitive():
    """Branch classification is case-insensitive."""
    assert _classify_branch("Fix/uppercase") == "fix"
    assert _classify_branch("FEAT/loud") == "feature"


# ============================================
# _parse_diff_stat
# ============================================


def test_parse_diff_stat_normal():
    """Normal diff stat output is parsed correctly."""
    output = (
        " src/main.py    | 10 +++++++---\n"
        " src/utils.py   | 5 +++++\n"
        " tests/test.py  | 3 +++\n"
        " 3 files changed, 15 insertions(+), 3 deletions(-)\n"
    )
    ratio, spread = _parse_diff_stat(output)
    assert spread == 2  # src, tests
    assert ratio is not None


def test_parse_diff_stat_all_new_files():
    """All new files (insertions only) → ratio = 1.0."""
    output = (
        " new_file.py | 20 ++++++++++++++++++++\n"
        " another.py  | 10 ++++++++++\n"
        " 2 files changed, 30 insertions(+)\n"
    )
    ratio, spread = _parse_diff_stat(output)
    assert ratio == 1.0


def test_parse_diff_stat_empty():
    """Empty output returns None, None."""
    ratio, spread = _parse_diff_stat("")
    assert ratio is None
    assert spread is None


def test_parse_diff_stat_single_line():
    """Single line (only summary) returns None, None."""
    output = " 1 file changed, 5 insertions(+)\n"
    ratio, spread = _parse_diff_stat(output)
    assert ratio is None
    assert spread is None


# ============================================
# ContextDetector.detect
# ============================================


def test_detect_all_signals(tmp_path):
    """All signals collected when git returns data."""
    with mock.patch("vibesrails.context.detector.run_git") as mock_git:
        mock_git.side_effect = [
            (True, "feat/new-widget"),      # branch
            (True, "M foo.py\n?? bar.py"),  # status
            (True, " src/a.py | 5 +++++\n 1 file changed, 5 insertions(+)\n"),  # diff
            (True, "abc1234 commit1\ndef5678 commit2"),  # log
        ]
        detector = ContextDetector(tmp_path)
        signals = detector.detect()

    assert signals.branch_name == "feat/new-widget"
    assert signals.branch_type == "feature"
    assert signals.uncommitted_count == 2
    assert signals.commit_frequency == 2


def test_detect_no_git(tmp_path):
    """All signals None when git fails."""
    with mock.patch("vibesrails.context.detector.run_git", return_value=(False, "")):
        detector = ContextDetector(tmp_path)
        signals = detector.detect()

    assert signals.branch_name == ""
    assert signals.branch_type == "unknown"
    assert signals.uncommitted_count is None
    assert signals.files_created_ratio is None
    assert signals.commit_frequency is None
    assert signals.diff_spread is None


def test_detect_new_repo_no_commits(tmp_path):
    """New repo with no commits: branch ok, diff fails, log empty."""
    with mock.patch("vibesrails.context.detector.run_git") as mock_git:
        mock_git.side_effect = [
            (True, "main"),        # branch
            (True, ""),            # status (clean)
            (False, ""),           # diff HEAD~1 fails (no parent)
            (True, ""),            # log (no commits in last hour)
        ]
        detector = ContextDetector(tmp_path)
        signals = detector.detect()

    assert signals.branch_name == "main"
    assert signals.uncommitted_count == 0
    assert signals.files_created_ratio is None
    assert signals.diff_spread is None
    assert signals.commit_frequency == 0


# ============================================
# Forced mode
# ============================================


def test_read_forced_mode_none(tmp_path):
    """No override file returns None."""
    detector = ContextDetector(tmp_path)
    assert detector.read_forced_mode() is None


def test_read_forced_mode_bugfix(tmp_path):
    """Override file with 'bugfix' returns 'bugfix'."""
    mode_dir = tmp_path / ".vibesrails"
    mode_dir.mkdir()
    (mode_dir / ".session_mode").write_text("bugfix\n")
    detector = ContextDetector(tmp_path)
    assert detector.read_forced_mode() == "bugfix"


def test_read_forced_mode_auto(tmp_path):
    """Override file with 'auto' returns None (auto = no override)."""
    mode_dir = tmp_path / ".vibesrails"
    mode_dir.mkdir()
    (mode_dir / ".session_mode").write_text("auto\n")
    detector = ContextDetector(tmp_path)
    assert detector.read_forced_mode() is None


def test_write_forced_mode(tmp_path):
    """Write and read back forced mode."""
    ContextDetector.write_forced_mode(tmp_path, "rnd")
    detector = ContextDetector(tmp_path)
    assert detector.read_forced_mode() == "rnd"


def test_write_forced_mode_auto_removes(tmp_path):
    """Writing 'auto' removes the override file."""
    ContextDetector.write_forced_mode(tmp_path, "bugfix")
    ContextDetector.write_forced_mode(tmp_path, "auto")
    detector = ContextDetector(tmp_path)
    assert detector.read_forced_mode() is None
