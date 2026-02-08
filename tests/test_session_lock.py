"""Tests for session lock — multi-window sync (PID-based)."""
import json
import os

import pytest

from vibesrails.hooks.session_lock import (
    LOCK_FILE_NAME,
    acquire_lock,
    check_other_session,
    release_lock,
)


@pytest.fixture
def lock_dir(tmp_path):
    return tmp_path


class TestAcquireLock:
    def test_creates_lock_file(self, lock_dir):
        acquire_lock(lock_dir)
        lock_file = lock_dir / LOCK_FILE_NAME
        assert lock_file.exists()
        data = json.loads(lock_file.read_text())
        assert data["pid"] == os.getpid()

    def test_overwrites_stale_lock(self, lock_dir):
        lock_file = lock_dir / LOCK_FILE_NAME
        lock_file.write_text(json.dumps({"pid": 99999999}))
        acquire_lock(lock_dir)
        data = json.loads(lock_file.read_text())
        assert data["pid"] == os.getpid()


class TestReleaseLock:
    def test_removes_own_lock(self, lock_dir):
        acquire_lock(lock_dir)
        release_lock(lock_dir)
        assert not (lock_dir / LOCK_FILE_NAME).exists()

    def test_ignores_other_pid_lock(self, lock_dir):
        lock_file = lock_dir / LOCK_FILE_NAME
        lock_file.write_text(json.dumps({"pid": 99999999}))
        release_lock(lock_dir)  # our PID != 99999999
        assert lock_file.exists()  # did NOT delete other's lock


class TestCheckOtherSession:
    def test_no_lock_returns_none(self, lock_dir):
        assert check_other_session(lock_dir) is None

    def test_own_lock_returns_none(self, lock_dir):
        acquire_lock(lock_dir)
        assert check_other_session(lock_dir) is None

    def test_other_live_pid_returns_warning(self, lock_dir):
        # Use PID 1 (launchd/init — always alive) to simulate another session
        lock_file = lock_dir / LOCK_FILE_NAME
        lock_file.write_text(json.dumps({"pid": 1}))
        result = check_other_session(lock_dir)
        assert result is not None
        assert "PID 1" in result

    def test_dead_pid_returns_none(self, lock_dir):
        lock_file = lock_dir / LOCK_FILE_NAME
        lock_file.write_text(json.dumps({"pid": 99999999}))
        assert check_other_session(lock_dir) is None
