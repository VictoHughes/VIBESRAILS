"""Learning Engine — cross-session developer profiling.

Aggregates events from all VibesRails tools (violations, brief scores,
drift, hallucinations, config issues, injections) into a developer profile
with actionable insights.

All aggregations use SQL for performance — no bulk Python loading.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from storage.migrations import get_db_path, migrate

logger = logging.getLogger(__name__)

# ── Valid event types ────────────────────────────────────────────────

VALID_EVENT_TYPES = frozenset({
    "violation",
    "brief_score",
    "drift",
    "hallucination",
    "config_issue",
    "injection",
})


class LearningEngine:
    """Cross-session developer profiling engine."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = get_db_path()
        self._db_path = str(db_path)
        migrate(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    # ── record_event ─────────────────────────────────────────────────

    def record_event(
        self,
        session_id: str,
        event_type: str,
        event_data: dict,
    ) -> None:
        """Record a learning event and update the developer profile.

        Args:
            session_id: Session identifier.
            event_type: One of: violation, brief_score, drift,
                hallucination, config_issue, injection.
            event_data: Event payload as dict (stored as JSON).
        """
        if event_type not in VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type '{event_type}'. "
                f"Must be one of: {sorted(VALID_EVENT_TYPES)}"
            )

        conn = self._connect()
        try:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO learning_events (session_id, event_type, event_data, created_at) "
                "VALUES (?, ?, ?, ?)",
                (session_id, event_type, json.dumps(event_data), now),
            )
            conn.commit()
            self._update_profile(conn)
        finally:
            conn.close()

    # ── _update_profile ──────────────────────────────────────────────

    def _update_profile(self, conn: sqlite3.Connection) -> None:
        """Recalculate aggregated metrics from learning_events."""
        now = datetime.now(timezone.utc).isoformat()

        # sessions_count
        row = conn.execute(
            "SELECT COUNT(DISTINCT session_id) AS cnt FROM learning_events"
        ).fetchone()
        sessions_count = row["cnt"] if row else 0
        self._upsert_metric(conn, "sessions_count", sessions_count, now)

        # avg_brief_score
        row = conn.execute(
            "SELECT AVG(CAST(json_extract(event_data, '$.score') AS REAL)) AS avg_score "
            "FROM learning_events WHERE event_type = 'brief_score'"
        ).fetchone()
        avg_brief = round(row["avg_score"], 1) if row and row["avg_score"] is not None else None
        self._upsert_metric(conn, "avg_brief_score", avg_brief, now)

        # top_violations — top 5 violation types by frequency
        rows = conn.execute(
            "SELECT json_extract(event_data, '$.guard_name') AS guard, COUNT(*) AS cnt "
            "FROM learning_events WHERE event_type = 'violation' "
            "AND json_extract(event_data, '$.guard_name') IS NOT NULL "
            "GROUP BY guard ORDER BY cnt DESC LIMIT 5"
        ).fetchall()
        top_violations = [{"guard": r["guard"], "count": r["cnt"]} for r in rows]
        self._upsert_metric(conn, "top_violations", top_violations, now)

        # hallucination_rate
        halluc_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM learning_events WHERE event_type = 'hallucination'"
        ).fetchone()["cnt"]
        if sessions_count > 0:
            halluc_rate = round(halluc_count / sessions_count, 3)
        else:
            halluc_rate = 0.0
        self._upsert_metric(conn, "hallucination_rate", halluc_rate, now)

        # improvement_rate — compare avg brief_score of last 5 sessions vs previous 5
        improvement = self._calc_improvement_rate(conn)
        self._upsert_metric(conn, "improvement_rate", improvement, now)

        # common_drift_areas — top 3 drift metrics
        drift_rows = conn.execute(
            "SELECT json_extract(event_data, '$.highest_metric') AS metric, COUNT(*) AS cnt "
            "FROM learning_events WHERE event_type = 'drift' "
            "AND json_extract(event_data, '$.highest_metric') IS NOT NULL "
            "GROUP BY metric ORDER BY cnt DESC LIMIT 3"
        ).fetchall()
        common_drift = [{"metric": r["metric"], "count": r["cnt"]} for r in drift_rows]
        self._upsert_metric(conn, "common_drift_areas", common_drift, now)

        conn.commit()

    def _calc_improvement_rate(self, conn: sqlite3.Connection) -> float | None:
        """Compare avg brief_score of last 5 sessions vs previous 5.

        Returns positive if improving, negative if regressing, None if
        not enough data.
        """
        # Get distinct sessions ordered by their earliest event
        sessions = conn.execute(
            "SELECT session_id, MIN(created_at) AS first_event "
            "FROM learning_events WHERE event_type = 'brief_score' "
            "GROUP BY session_id ORDER BY first_event DESC"
        ).fetchall()

        if len(sessions) < 2:
            return None

        # Recent 5 sessions
        recent_ids = [s["session_id"] for s in sessions[:5]]
        # Previous 5 sessions (or whatever remains)
        previous_ids = [s["session_id"] for s in sessions[5:10]]

        if not previous_ids:
            return None

        recent_avg = self._avg_brief_for_sessions(conn, recent_ids)
        previous_avg = self._avg_brief_for_sessions(conn, previous_ids)

        if previous_avg is None or recent_avg is None:
            return None

        if previous_avg == 0:
            return None

        return round(((recent_avg - previous_avg) / previous_avg) * 100, 1)

    @staticmethod
    def _avg_brief_for_sessions(
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

    @staticmethod
    def _upsert_metric(
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

    # ── get_profile ──────────────────────────────────────────────────

    def get_profile(self) -> dict:
        """Read the developer profile.

        Returns:
            Dict with all metrics, or {"status": "no_data", "sessions_count": 0}
            if no events have been recorded.
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT metric_name, metric_value FROM developer_profile"
            ).fetchall()
        finally:
            conn.close()

        if not rows:
            return {"status": "no_data", "sessions_count": 0}

        profile: dict = {"status": "ok"}
        for row in rows:
            profile[row["metric_name"]] = json.loads(row["metric_value"])
        return profile

    # ── get_insights ─────────────────────────────────────────────────

    def get_insights(self) -> list[str]:
        """Generate actionable insights based on the developer profile."""
        profile = self.get_profile()

        if profile.get("status") == "no_data":
            return ["Pas encore assez de donnees. Utilisez VibesRails pendant "
                    "quelques sessions pour construire votre profil."]

        insights: list[str] = []
        sessions_count = profile.get("sessions_count", 0)
        avg_brief = profile.get("avg_brief_score")
        halluc_rate = profile.get("hallucination_rate", 0)
        improvement = profile.get("improvement_rate")
        top_violations = profile.get("top_violations", [])
        common_drift = profile.get("common_drift_areas", [])

        # Brief score insight
        if avg_brief is not None and avg_brief < 50:
            insights.append(
                f"Vos briefs sont regulierement incomplets (score moyen: {avg_brief:.0f}/100). "
                "Investir 30 secondes dans un brief complet economise 10 minutes de debug."
            )

        # Hallucination rate insight
        if halluc_rate and halluc_rate > 0.3:
            insights.append(
                f"Des hallucinations sont detectees dans {halluc_rate * 100:.0f}% de vos sessions. "
                "Activez deep_hallucination level 2+ systematiquement."
            )

        # Improvement trend
        if improvement is not None:
            if improvement > 0:
                insights.append(
                    f"Tendance positive: vos scores s'ameliorent de {improvement:.1f}% "
                    "sur les dernieres sessions. Continuez."
                )
            elif improvement < 0:
                guards = [v["guard"] for v in top_violations[:3]] if top_violations else []
                insights.append(
                    f"Attention: regression de {abs(improvement):.1f}%. "
                    f"Les erreurs recentes: {guards}. Revoyez les bases."
                )

        # Top violations insight
        if top_violations:
            guards = [v["guard"] for v in top_violations]
            insights.append(
                f"Vos violations les plus frequentes: {guards}. "
                "Focus sur la premiere pour un impact maximum."
            )

        # Drift areas insight
        if common_drift:
            areas = [d["metric"] for d in common_drift]
            insights.append(
                f"Architecture: vos zones de drift frequentes sont {areas}. "
                "Stabilisez-les avant d'ajouter des features."
            )

        # Positive feedback if everything is good
        if not insights:
            insights.append(
                f"Profil sain sur {sessions_count} sessions. "
                "Aucun pattern problematique detecte."
            )

        return insights

    # ── get_session_summary ──────────────────────────────────────────

    def get_session_summary(self, session_id: str) -> dict:
        """Aggregate all events for a single session.

        Returns:
            Dict with session_id, events_count, violations, brief_score,
            drift_velocity, hallucinations, injections_detected.
        """
        conn = self._connect()
        try:
            # Total events
            total = conn.execute(
                "SELECT COUNT(*) AS cnt FROM learning_events WHERE session_id = ?",
                (session_id,),
            ).fetchone()["cnt"]

            if total == 0:
                return {
                    "session_id": session_id,
                    "events_count": 0,
                    "violations": [],
                    "brief_score": None,
                    "drift_velocity": None,
                    "hallucinations": 0,
                    "injections_detected": 0,
                }

            # Violations
            violations = conn.execute(
                "SELECT json_extract(event_data, '$.guard_name') AS guard "
                "FROM learning_events "
                "WHERE session_id = ? AND event_type = 'violation'",
                (session_id,),
            ).fetchall()
            violation_list = [r["guard"] for r in violations if r["guard"]]

            # Brief score (latest)
            brief_row = conn.execute(
                "SELECT json_extract(event_data, '$.score') AS score "
                "FROM learning_events "
                "WHERE session_id = ? AND event_type = 'brief_score' "
                "ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            brief_score = brief_row["score"] if brief_row and brief_row["score"] is not None else None

            # Drift velocity (latest)
            drift_row = conn.execute(
                "SELECT json_extract(event_data, '$.velocity') AS velocity "
                "FROM learning_events "
                "WHERE session_id = ? AND event_type = 'drift' "
                "ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            drift_velocity = drift_row["velocity"] if drift_row and drift_row["velocity"] is not None else None

            # Hallucination count
            halluc_count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM learning_events "
                "WHERE session_id = ? AND event_type = 'hallucination'",
                (session_id,),
            ).fetchone()["cnt"]

            # Injection count
            inject_count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM learning_events "
                "WHERE session_id = ? AND event_type = 'injection'",
                (session_id,),
            ).fetchone()["cnt"]

            return {
                "session_id": session_id,
                "events_count": total,
                "violations": violation_list,
                "brief_score": brief_score,
                "drift_velocity": drift_velocity,
                "hallucinations": halluc_count,
                "injections_detected": inject_count,
            }
        finally:
            conn.close()
