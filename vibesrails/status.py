"""Unified status report — aggregates preflight, gates, assertions, context.

Provides two output modes:
- Full: grouped sections with box art (for --status)
- Quiet: single compact line < 500 chars (for hooks / CI)

Unlike preflight, status does NOT run the test suite (too slow for hooks).
It reads the last known test state from assertions baseline.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .scanner_types import BLUE, GREEN, NC, YELLOW

logger = logging.getLogger(__name__)


# ── Data collection (fast — no subprocess, no pytest) ──────────


def _git_info(root: Path) -> dict:
    """Collect git state. Returns dict with branch, dirty_count, unpushed."""
    from .guards_v2._git_helpers import run_git

    info: dict = {"branch": "?", "dirty_count": 0, "unpushed": 0}

    ok, branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    if ok:
        info["branch"] = branch

    ok, output = run_git(["status", "--porcelain"], cwd=root)
    if ok:
        info["dirty_count"] = sum(1 for line in output.splitlines() if line.strip())

    ok, output = run_git(
        ["rev-list", "--left-right", "--count", "main...HEAD"], cwd=root
    )
    if ok:
        parts = output.split()
        if len(parts) == 2:
            info["unpushed"] = int(parts[1])

    return info


def _version() -> str:
    """Get vibesrails version."""
    try:
        from . import __version__
        return __version__
    except Exception:
        return "?"


def _context_info(root: Path) -> dict:
    """Collect session context (mode + phase). Fast — no subprocess."""
    info: dict = {
        "mode": "?", "mode_score": 0, "mode_confidence": "?",
        "phase": "?", "phase_num": -1, "phase_total": 4,
        "phase_missing": [], "phase_is_override": False,
    }
    try:
        from .context import SessionMode, get_session_context

        ctx = get_session_context(root)
        mode_labels = {
            SessionMode.RND: "R&D",
            SessionMode.MIXED: "Mixed",
            SessionMode.BUGFIX: "Bugfix",
        }
        info["mode"] = mode_labels.get(ctx.mode, ctx.mode.value)
        info["mode_score"] = ctx.mode_score
        conf = (
            "high" if ctx.mode_confidence >= 0.7
            else "medium" if ctx.mode_confidence >= 0.4
            else "low"
        )
        info["mode_confidence"] = conf
        info["phase"] = ctx.phase_name
        info["phase_num"] = ctx.phase
        info["phase_missing"] = ctx.phase_missing
        info["phase_is_override"] = ctx.phase_is_override
    except Exception:
        pass
    return info


def _gate_info(root: Path) -> dict:
    """Collect gate status. Fast — reads signals, no subprocess."""
    info: dict = {"met": 0, "total": 0, "target": None, "all_met": True}
    try:
        from .gates import check_gates

        report = check_gates(root)
        info["met"] = report.met_count
        info["total"] = report.total_count
        info["all_met"] = report.all_met
        if report.target_phase:
            info["target"] = report.target_phase.name.replace("_", " ")
    except Exception:
        pass
    return info


def _assertions_info(root: Path) -> dict:
    """Collect assertions status. Fast — reads config + files."""
    info: dict = {"passed": 0, "total": 0}
    try:
        from .assertions import run_assertions
        from .cli_setup import find_config
        from .scanner import load_config

        config_path = find_config()
        if config_path and config_path.exists():
            config = load_config(config_path)
            assertions_config = config.get("assertions", {})
            if assertions_config:
                results = run_assertions(root, assertions_config)
                info["total"] = len(results)
                info["passed"] = sum(1 for r in results if r.status == "ok")
    except Exception:
        pass
    return info


def _docs_info(root: Path) -> dict:
    """Check doc freshness. Fast — file reads only."""
    info: dict = {"claude_md": "?", "decisions": False}
    try:
        from .preflight import check_claude_md_freshness, check_decisions_md

        claude_result = check_claude_md_freshness(root)
        info["claude_md"] = "synced" if claude_result.status == "ok" else "stale"

        decisions_result = check_decisions_md(root)
        info["decisions"] = decisions_result.status == "ok"
    except Exception:
        pass
    return info


def _test_baseline_info(root: Path) -> dict:
    """Read test baseline from config (no pytest execution)."""
    info: dict = {"declared": 0, "actual": "?"}
    try:
        from .cli_setup import find_config
        from .scanner import load_config

        config_path = find_config()
        if config_path and config_path.exists():
            config = load_config(config_path)
            baseline = config.get("assertions", {}).get("baselines", {})
            info["declared"] = baseline.get("test_count", 0)
    except Exception:
        pass
    return info


# ── Report collection ──────────────────────────────────────────


def collect_status(root: Path) -> dict:
    """Collect all status data. Fast (no pytest, no subprocess for tests)."""
    return {
        "version": _version(),
        "git": _git_info(root),
        "context": _context_info(root),
        "gates": _gate_info(root),
        "assertions": _assertions_info(root),
        "docs": _docs_info(root),
        "tests": _test_baseline_info(root),
    }


# ── Formatters ─────────────────────────────────────────────────


def format_quiet(data: dict) -> str:
    """Compact single-line format for hooks/CI (< 500 chars)."""
    g = data["git"]
    c = data["context"]
    gt = data["gates"]
    a = data["assertions"]
    t = data["tests"]

    dirty = f" ({g['dirty_count']} dirty)" if g["dirty_count"] else ""
    unpushed = f" +{g['unpushed']} unpushed" if g["unpushed"] else ""

    phase_flag = " [override]" if c.get("phase_is_override") else ""
    gate_str = f"gates {gt['met']}/{gt['total']}" if gt["total"] else "no gates"
    if gt["total"] and not gt["all_met"] and gt.get("target"):
        missing = c.get("phase_missing", [])
        if missing:
            gate_str += f" need: {', '.join(missing[:3])}"

    parts = [
        f"VR {data['version']}",
        f"{g['branch']}{dirty}{unpushed}",
        f"{c['mode']}/{c['phase']}({c['phase_num']}/{c['phase_total']}){phase_flag}",
        gate_str,
        f"{a['passed']}/{a['total']} assertions" if a["total"] else "",
        f"tests baseline: {t['declared']}" if t["declared"] else "",
    ]
    return " | ".join(p for p in parts if p)


def format_full(data: dict) -> str:
    """Full grouped report with box art."""
    g = data["git"]
    c = data["context"]
    gt = data["gates"]
    a = data["assertions"]
    d = data["docs"]
    t = data["tests"]
    v = data["version"]

    lines = [
        f"{BLUE}{'=' * 50}{NC}",
        f"{BLUE} VIBESRAILS STATUS REPORT{NC}",
        f"{BLUE}{'=' * 50}{NC}",
        "",
    ]

    # REPO
    dirty_str = f"{YELLOW}{g['dirty_count']} files uncommitted{NC}" if g["dirty_count"] else f"{GREEN}clean{NC}"
    unpushed_str = f"{YELLOW}{g['unpushed']} commits ahead{NC}" if g["unpushed"] else f"{GREEN}up to date{NC}"
    lines.extend([
        f"{BLUE}REPO{NC}",
        f"  Branch    : {g['branch']}",
        f"  Working   : {dirty_str}",
        f"  Unpushed  : {unpushed_str}",
        f"  Version   : {v}",
        "",
    ])

    # CONTEXT
    phase_flag = " [override]" if c.get("phase_is_override") else ""
    lines.extend([
        f"{BLUE}CONTEXT{NC}",
        f"  Mode      : {c['mode']} (score: {c['mode_score']:.2f}, {c['mode_confidence']})",
        f"  Phase     : {c['phase']} ({c['phase_num']}/{c['phase_total']}){phase_flag}",
    ])
    if gt["total"]:
        met_color = GREEN if gt["all_met"] else YELLOW
        lines.append(
            f"  Gates     : {met_color}{gt['met']}/{gt['total']} met{NC}"
        )
        if not gt["all_met"] and c.get("phase_missing"):
            lines.append(
                f"              need: {', '.join(c['phase_missing'])}"
            )
    lines.append("")

    # TESTS
    lines.extend([
        f"{BLUE}TESTS{NC}",
        f"  Baseline  : {t['declared']} declared",
    ])
    lines.append("")

    # DOCS
    claude_icon = f"{GREEN}synced{NC}" if d["claude_md"] == "synced" else f"{YELLOW}stale{NC}"
    decisions_icon = f"{GREEN}exists{NC}" if d["decisions"] else f"{YELLOW}missing{NC}"
    lines.extend([
        f"{BLUE}DOCS{NC}",
        f"  CLAUDE.md : {claude_icon}",
        f"  decisions : {decisions_icon}",
    ])
    lines.append("")

    # ASSERTIONS
    if a["total"]:
        a_color = GREEN if a["passed"] == a["total"] else YELLOW
        lines.extend([
            f"{BLUE}ASSERTIONS{NC}",
            f"  Result    : {a_color}{a['passed']}/{a['total']} passed{NC}",
            "",
        ])

    # ACTIONS
    actions = []
    if g["dirty_count"]:
        actions.append(f"{YELLOW}  {g['dirty_count']} files uncommitted{NC}")
    if g["unpushed"]:
        actions.append(f"{YELLOW}  {g['unpushed']} commits not pushed{NC}")
    if d["claude_md"] == "stale":
        actions.append(f"{YELLOW}  CLAUDE.md stale — run: vibesrails --sync-claude{NC}")
    if gt["total"] and not gt["all_met"]:
        actions.append(f"{YELLOW}  Gate blocked — run: vibesrails --check-gates{NC}")

    if actions:
        lines.append(f"{BLUE}ACTIONS REQUIRED{NC}")
        lines.extend(actions)
    else:
        lines.append(f"{GREEN}No blockers — ready to code!{NC}")

    lines.extend([
        "",
        f"{BLUE}{'=' * 50}{NC}",
    ])
    return "\n".join(lines)


def format_json(data: dict) -> str:
    """JSON output for CI/CD."""
    return json.dumps(data, indent=2, default=str)


def exit_code(data: dict) -> int:
    """0 = all green, 1 = warnings, 2 = blockers."""
    g = data["git"]
    a = data["assertions"]

    # Blocker: zero assertions passing when some are defined
    if a["total"] and a["passed"] == 0:
        return 2
    # Warnings: partial assertions, dirty tree, unpushed commits
    if a["total"] and a["passed"] < a["total"]:
        return 1
    if g["dirty_count"] or g["unpushed"]:
        return 1
    return 0
