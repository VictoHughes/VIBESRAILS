"""Tests for inter-session task queue."""

from vibesrails.hooks.queue_processor import (
    add_task,
    format_pending_summary,
    get_pending_tasks,
    mark_done,
)


def test_add_and_read_task(tmp_path):
    """Add a task and read it back."""
    qf = tmp_path / "queue.jsonl"
    task_id = add_task(qf, "Fix login", source="window-2", priority="high")
    assert len(task_id) == 8
    tasks = get_pending_tasks(qf)
    assert len(tasks) == 1
    t = tasks[0]
    assert t["id"] == task_id
    assert t["message"] == "Fix login"
    assert t["source"] == "window-2"
    assert t["priority"] == "high"
    assert t["status"] == "pending"
    assert "created" in t


def test_mark_done(tmp_path):
    """Mark first of two tasks done, verify only second remains."""
    qf = tmp_path / "queue.jsonl"
    id1 = add_task(qf, "Task 1", source="a")
    add_task(qf, "Task 2", source="b")
    assert mark_done(qf, id1) is True
    pending = get_pending_tasks(qf)
    assert len(pending) == 1
    assert pending[0]["message"] == "Task 2"


def test_empty_queue(tmp_path):
    """No file returns empty list."""
    qf = tmp_path / "nonexistent.jsonl"
    assert get_pending_tasks(qf) == []


def test_multiple_tasks_ordered(tmp_path):
    """Three tasks returned in insertion order."""
    qf = tmp_path / "queue.jsonl"
    ids = [add_task(qf, f"Task {i}", source=f"s{i}") for i in range(3)]
    tasks = get_pending_tasks(qf)
    assert [t["id"] for t in tasks] == ids


def test_format_pending_summary(tmp_path):
    """Verify formatted output."""
    qf = tmp_path / "queue.jsonl"
    add_task(qf, "Fix bug", source="window-2")
    add_task(qf, "Add tests", source="window-3")
    summary = format_pending_summary(qf)
    assert summary.startswith("2 pending tasks from other sessions:")
    assert "Fix bug" in summary
    assert "window-2" in summary
    # Empty case
    qf2 = tmp_path / "empty.jsonl"
    assert format_pending_summary(qf2) == ""
