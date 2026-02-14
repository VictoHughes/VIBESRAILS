"""Profile update logic for LearningEngine — extracted from learning_engine.py."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


def update_profile(conn: sqlite3.Connection) -> None:
    """Recalculate aggregated metrics from learning_events."""
    now = datetime.now(timezone.utc).isoformat()

    # sessions_count
    row = conn.execute(
        "SELECT COUNT(DISTINCT session_id) AS cnt FROM learning_events"
    ).fetchone()
    sessions_count = row["cnt"] if row else 0
    upsert_metric(conn, "sessions_count", sessions_count, now)

    # avg_brief_score
    row = conn.execute(
        "SELECT AVG(CAST(json_extract(event_data, '$.score') AS REAL)) AS avg_score "
        "FROM learning_events WHERE event_type = 'brief_score'"
    ).fetchone()
    avg_brief = round(row["avg_score"], 1) if row and row["avg_score"] is not None else None
    upsert_metric(conn, "avg_brief_score", avg_brief, now)

    # top_violations — top 5 violation types by frequency
    rows = conn.execute(
        "SELECT json_extract(event_data, '$.guard_name') AS guard, COUNT(*) AS cnt "
        "FROM learning_events WHERE event_type = 'violation' "
        "AND json_extract(event_data, '$.guard_name') IS NOT NULL "
        "GROUP BY guard ORDER BY cnt DESC LIMIT 5"
    ).fetchall()
    top_violations = [{"guard": r["guard"], "count": r["cnt"]} for r in rows]
    upsert_metric(conn, "top_violations", top_violations, now)

    # hallucination_rate
    halluc_count = conn.execute(
        "SELECT COUNT(*) AS cnt FROM learning_events WHERE event_type = 'hallucination'"
    ).fetchone()["cnt"]
    if sessions_count > 0:
        halluc_rate = round(halluc_count / sessions_count, 3)
    else:
        halluc_rate = 0.0
    upsert_metric(conn, "hallucination_rate", halluc_rate, now)

    # improvement_rate — compare avg brief_score of last 5 sessions vs previous 5
    improvement = calc_improvement_rate(conn)
    upsert_metric(conn, "improvement_rate", improvement, now)

    # common_drift_areas — top 3 drift metrics
    drift_rows = conn.execute(
        "SELECT json_extract(event_data, '$.highest_metric') AS metric, COUNT(*) AS cnt "
        "FROM learning_events WHERE event_type = 'drift' "
        "AND json_extract(event_data, '$.highest_metric') IS NOT NULL "
        "GROUP BY metric ORDER BY cnt DESC LIMIT 3"
    ).fetchall()
    common_drift = [{"metric": r["metric"], "count": r["cnt"]} for r in drift_rows]
    upsert_metric(conn, "common_drift_areas", common_drift, now)

    conn.commit()


def calc_improvement_rate(conn: sqlite3.Connection) -> float | None:
    """Compare avg brief_score of last 5 sessions vs previous 5.

    Returns positive if improving, negative if regressing, None if
    not enough data.
    """
    sessions = conn.execute(
        "SELECT session_id, MIN(created_at) AS first_event "
        "FROM learning_events WHERE event_type = 'brief_score' "
        "GROUP BY session_id ORDER BY first_event DESC"
    ).fetchall()

    if len(sessions) < 2:
        return None

    recent_ids = [s["session_id"] for s in sessions[:5]]
    previous_ids = [s["session_id"] for s in sessions[5:10]]

    if not previous_ids:
        return None

    recent_avg = avg_brief_for_sessions(conn, recent_ids)
    previous_avg = avg_brief_for_sessions(conn, previous_ids)

    if previous_avg is None or recent_avg is None:
        return None

    if previous_avg == 0:
        return None

    return round(((recent_avg - previous_avg) / previous_avg) * 100, 1)


def avg_brief_for_sessions(
    conn: sqlite3.Connection, session_ids: list[str],
) -> float | None:
    """Calculate average brief_score for a set of sessions."""
    placeholders = ",".join("?" for _ in session_ids)
    row = conn.execute(
        f"SELECT AVG(CAST(json_extract(event_data, '$.score') AS REAL)) AS avg_score "
        f"FROM learning_events WHERE event_type = 'brief_score' "
        f"AND session_id IN ({placeholders})",
        session_ids,
    ).fetchone()
    return row["avg_score"] if row and row["avg_score"] is not None else None


def upsert_metric(
    conn: sqlite3.Connection,
    metric_name: str,
    metric_value: object,
    updated_at: str,
) -> None:
    """Insert or replace a metric in developer_profile."""
    conn.execute(
        "INSERT OR REPLACE INTO developer_profile (metric_name, metric_value, updated_at) "
        "VALUES (?, ?, ?)",
        (metric_name, json.dumps(metric_value), updated_at),
    )
