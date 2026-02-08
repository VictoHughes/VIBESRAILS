"""Inter-session task queue via .claude/queue.jsonl."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def add_task(
    queue_file: Path,
    message: str,
    source: str = "unknown",
    priority: str = "normal",
) -> str:
    """Append a task to the queue file. Returns task_id."""
    task_id = uuid.uuid4().hex[:8]
    entry = {
        "id": task_id,
        "message": message,
        "source": source,
        "priority": priority,
        "status": "pending",
        "created": datetime.now(timezone.utc).isoformat(),
    }
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    with open(queue_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return task_id


def get_pending_tasks(queue_file: Path) -> list[dict]:
    """Read all pending tasks from the queue file."""
    if not queue_file.exists():
        return []
    tasks = []
    with open(queue_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                task = json.loads(line)
            except json.JSONDecodeError:
                continue
            if task.get("status") == "pending":
                tasks.append(task)
    return tasks


def mark_done(queue_file: Path, task_id: str) -> bool:
    """Mark a task as done. Returns True if found."""
    if not queue_file.exists():
        return False
    lines = queue_file.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            task = json.loads(line)
        except json.JSONDecodeError:
            new_lines.append(line)
            continue
        if task.get("id") == task_id:
            task["status"] = "done"
            found = True
        new_lines.append(json.dumps(task))
    queue_file.write_text("\n".join(new_lines) + "\n" if new_lines else "")
    return found


def format_pending_summary(queue_file: Path) -> str:
    """Return human-readable summary of pending tasks."""
    tasks = get_pending_tasks(queue_file)
    if not tasks:
        return ""
    count = len(tasks)
    label = "task" if count == 1 else "tasks"
    lines = [f"{count} pending {label} from other sessions:"]
    for t in tasks:
        lines.append(f"  - [{t['id']}] {t['message']} (from {t['source']})")
    return "\n".join(lines)
