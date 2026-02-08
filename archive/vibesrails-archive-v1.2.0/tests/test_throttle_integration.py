"""Integration test: throttle wired into pre_tool_use."""
from vibesrails.hooks.throttle import (
    get_writes_since_check,
    record_check,
    record_write,
    reset_state,
)


class TestThrottleInPreToolUse:
    def test_write_blocked_after_threshold(self, tmp_path):
        """After 5 writes, pre_tool_use should block Write."""
        reset_state(tmp_path)
        for _ in range(5):
            record_write(tmp_path)
        assert get_writes_since_check(tmp_path) == 5
        from vibesrails.hooks.throttle import should_block
        assert should_block(tmp_path, threshold=5)

    def test_bash_pytest_resets_counter(self, tmp_path):
        """Bash containing 'pytest' should reset the counter."""
        reset_state(tmp_path)
        for _ in range(3):
            record_write(tmp_path)
        record_check(tmp_path)
        assert get_writes_since_check(tmp_path) == 0

    def test_bash_ruff_resets_counter(self, tmp_path):
        """Bash containing 'ruff' should reset the counter."""
        reset_state(tmp_path)
        record_write(tmp_path)
        record_check(tmp_path)
        assert get_writes_since_check(tmp_path) == 0

    def test_write_allowed_under_threshold(self, tmp_path):
        """Under threshold, writes should pass."""
        reset_state(tmp_path)
        for _ in range(4):
            record_write(tmp_path)
        from vibesrails.hooks.throttle import should_block
        assert not should_block(tmp_path, threshold=5)
