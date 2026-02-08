"""Tests for write throttle — anti-emballement."""
import pytest

from vibesrails.hooks.throttle import (
    STATE_FILE_NAME,
    get_writes_since_check,
    record_check,
    record_write,
    reset_state,
    should_block,
)


@pytest.fixture
def state_dir(tmp_path):
    """Temp dir simulating .vibesrails/."""
    return tmp_path


class TestRecordWrite:
    def test_increments_counter(self, state_dir):
        reset_state(state_dir)
        record_write(state_dir)
        assert get_writes_since_check(state_dir) == 1

    def test_increments_multiple(self, state_dir):
        reset_state(state_dir)
        record_write(state_dir)
        record_write(state_dir)
        record_write(state_dir)
        assert get_writes_since_check(state_dir) == 3


class TestRecordCheck:
    def test_resets_counter(self, state_dir):
        reset_state(state_dir)
        record_write(state_dir)
        record_write(state_dir)
        record_check(state_dir)
        assert get_writes_since_check(state_dir) == 0


class TestShouldBlock:
    def test_no_block_under_threshold(self, state_dir):
        reset_state(state_dir)
        for _ in range(4):
            record_write(state_dir)
        assert not should_block(state_dir, threshold=5)

    def test_blocks_at_threshold(self, state_dir):
        reset_state(state_dir)
        for _ in range(5):
            record_write(state_dir)
        assert should_block(state_dir, threshold=5)

    def test_no_block_after_check(self, state_dir):
        reset_state(state_dir)
        for _ in range(5):
            record_write(state_dir)
        record_check(state_dir)
        assert not should_block(state_dir, threshold=5)


class TestStateFile:
    def test_missing_state_returns_zero(self, state_dir):
        assert get_writes_since_check(state_dir) == 0

    def test_corrupted_state_returns_zero(self, state_dir):
        state_file = state_dir / STATE_FILE_NAME
        state_file.write_text("not json")
        assert get_writes_since_check(state_dir) == 0
