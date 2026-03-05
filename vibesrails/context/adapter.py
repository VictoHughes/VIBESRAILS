"""Context adapter — adjusts guard thresholds based on session mode."""

from __future__ import annotations

import copy
import logging
from typing import Any

from .mode import SessionMode

logger = logging.getLogger(__name__)

# ── Default profiles per mode ────────────────────────────────────
# MIXED is empty: it preserves current defaults (zero regression).
# Keys map to guard identifiers used throughout the codebase.
PROFILES: dict[SessionMode, dict[str, Any]] = {
    SessionMode.RND: {
        "file_too_long": {"threshold": 600, "severity": "WARN"},
        "diff_size": {"warn": 300, "block": 500},
        "complexity": {
            "cyclomatic_warn": 15,
            "cyclomatic_block": 25,
            "cognitive_warn": 20,
            "cognitive_block": 40,
            "length_warn": 80,
            "length_block": 150,
        },
        "brief_enforcer": {"min_score": 30},
    },
    SessionMode.MIXED: {},
    SessionMode.BUGFIX: {
        "file_too_long": {"threshold": 300, "severity": "BLOCK"},
        "diff_size": {"warn": 50, "block": 100},
        "complexity": {
            "cyclomatic_warn": 8,
            "cyclomatic_block": 12,
            "cognitive_warn": 10,
            "cognitive_block": 20,
            "length_warn": 40,
            "length_block": 80,
        },
        "brief_enforcer": {"min_score": 70},
    },
    SessionMode.FORCED: {},  # FORCED uses same as the underlying mode
}


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base. Returns a new dict."""
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class ContextAdapter:
    """Adjusts guard thresholds based on SessionMode.

    Usage:
        adapter = ContextAdapter()
        profile = adapter.get_profile(mode)
        config = adapter.adapt_config(mode, config)
    """

    def __init__(self, yaml_overrides: dict[str, Any] | None = None):
        """Initialize with optional YAML overrides from session_profiles key.

        Args:
            yaml_overrides: dict like {"rnd": {"file_too_long": {"threshold": 800}}}
        """
        self._overrides = yaml_overrides or {}

    def get_profile(self, mode: SessionMode) -> dict[str, Any]:
        """Get the effective profile for a mode (built-in + YAML overrides).

        Returns a fresh copy — safe to mutate.
        """
        base = copy.deepcopy(PROFILES.get(mode, {}))

        # Apply YAML overrides if present
        mode_key = mode.value  # "rnd", "bugfix", "mixed"
        if mode_key in self._overrides:
            base = _deep_merge(base, self._overrides[mode_key])

        return base

    def adapt_config(self, mode: SessionMode, config: dict) -> dict:
        """Return a modified copy of the scanner config for the given mode.

        Adjusts complexity.max_file_lines and its severity based on the profile.
        Never mutates the original config.
        """
        profile = self.get_profile(mode)
        if not profile:
            return copy.deepcopy(config)

        adapted = copy.deepcopy(config)

        # Adapt file_too_long → complexity.max_file_lines
        ftl = profile.get("file_too_long")
        if ftl:
            if "complexity" not in adapted:
                adapted["complexity"] = {}
            adapted["complexity"]["max_file_lines"] = ftl.get(
                "threshold", adapted.get("complexity", {}).get("max_file_lines", 400)
            )
            # Store severity for scanner to pick up
            adapted["complexity"]["file_too_long_severity"] = ftl.get(
                "severity", "WARN"
            )

        # Adapt guardian.max_file_lines (used by pre_tool_use hook)
        if ftl:
            if "guardian" not in adapted:
                adapted["guardian"] = {}
            adapted["guardian"]["max_file_lines"] = ftl.get("threshold", 300)

        return adapted

    def format_adjustments(self, mode: SessionMode) -> list[str]:
        """Return human-readable lines describing the adjustments for a mode."""
        profile = self.get_profile(mode)
        if not profile:
            return ["No threshold adjustments (default mode)"]

        lines: list[str] = []
        ftl = profile.get("file_too_long")
        if ftl:
            lines.append(
                f"file_too_long: {ftl.get('threshold')} lines "
                f"({ftl.get('severity', 'WARN')})"
            )

        ds = profile.get("diff_size")
        if ds:
            lines.append(
                f"diff_size: warn={ds.get('warn')}, block={ds.get('block')}"
            )

        cx = profile.get("complexity")
        if cx:
            lines.append(
                f"complexity: cyclomatic warn={cx.get('cyclomatic_warn')}"
                f"/block={cx.get('cyclomatic_block')}"
            )

        bf = profile.get("brief_enforcer")
        if bf:
            lines.append(f"brief_enforcer: min_score={bf.get('min_score')}")

        return lines or ["No threshold adjustments"]
