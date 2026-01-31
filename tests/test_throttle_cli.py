"""Tests for throttle CLI commands."""
import pytest
from pathlib import Path
from vibesrails.hooks.throttle import record_write, reset_state, get_writes_since_check


class TestThrottleCLI:
    def test_throttle_status_shows_count(self, tmp_path):
        reset_state(tmp_path)
        record_write(tmp_path)
        record_write(tmp_path)
        assert get_writes_since_check(tmp_path) == 2

    def test_throttle_reset_clears_count(self, tmp_path):
        reset_state(tmp_path)
        record_write(tmp_path)
        record_write(tmp_path)
        reset_state(tmp_path)
        assert get_writes_since_check(tmp_path) == 0
