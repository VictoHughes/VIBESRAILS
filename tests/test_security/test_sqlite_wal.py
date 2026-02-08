"""SQLite WAL mode and concurrency tests.

Verifies that WAL mode is enabled after migration, and that
concurrent writes from multiple threads don't crash.
"""

from __future__ import annotations

import sqlite3
import threading

from core.session_tracker import SessionTracker
from storage.migrations import migrate


def test_wal_mode_enabled(tmp_path):
    """After migration, journal_mode should be WAL."""
    db = str(tmp_path / "test.db")
    migrate(db_path=db)

    conn = sqlite3.connect(db)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal", f"Expected WAL, got {mode}"
    finally:
        conn.close()


def test_concurrent_writes_no_crash(tmp_path):
    """Two threads writing simultaneously shouldn't crash."""
    db = str(tmp_path / "test.db")
    # Pre-migrate (matches real server: lifespan runs migrate() once at startup)
    migrate(db_path=db)
    errors: list[Exception] = []

    def writer(thread_id: int) -> None:
        try:
            tracker = SessionTracker(db_path=db)
            for i in range(10):
                sid = tracker.start_session(f"/project/thread_{thread_id}")
                tracker.update_session(
                    sid,
                    files_modified=[f"file_{thread_id}_{i}.py"],
                    changes_loc=10,
                    violations=1,
                )
                tracker.end_session(sid)
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=writer, args=(1,))
    t2 = threading.Thread(target=writer, args=(2,))

    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    assert not errors, f"Concurrent writes failed: {errors}"

    # Verify both threads wrote successfully
    conn = sqlite3.connect(db)
    try:
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        assert count == 20, f"Expected 20 sessions (10 per thread), got {count}"
    finally:
        conn.close()
