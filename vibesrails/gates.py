"""Gate checking and phase promotion for the methodology lifecycle."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from .context.phase import (
    _GATE_ORDER,
    _GATES,
    PhaseDetector,
    ProjectPhase,
    get_effective_gates,
)
from .scanner_types import BLUE, GREEN, NC, RED, YELLOW

logger = logging.getLogger(__name__)


@dataclass
class GateCondition:
    """A single gate condition with its status."""

    label: str
    met: bool


@dataclass
class GateReport:
    """Full gate report for the current phase."""

    current_phase: ProjectPhase
    is_override: bool
    target_phase: ProjectPhase | None  # None if at DEPLOY
    gate_name: str | None
    conditions: list[GateCondition]

    @property
    def all_met(self) -> bool:
        return all(c.met for c in self.conditions)

    @property
    def met_count(self) -> int:
        return sum(1 for c in self.conditions if c.met)

    @property
    def total_count(self) -> int:
        return len(self.conditions)


def check_gates(root: Path) -> GateReport:
    """Check all gate conditions for advancing to the next phase."""
    detector = PhaseDetector(root)
    result = detector.detect()
    signals = detector.collect_signals()
    phase = result.phase

    if phase >= ProjectPhase.DEPLOY:
        return GateReport(
            current_phase=phase,
            is_override=result.is_override,
            target_phase=None,
            gate_name=None,
            conditions=[],
        )

    gate_index = phase.value
    if gate_index >= len(_GATE_ORDER):
        return GateReport(
            current_phase=phase,
            is_override=result.is_override,
            target_phase=None,
            gate_name=None,
            conditions=[],
        )

    gate_name, target_phase = _GATE_ORDER[gate_index]
    effective = get_effective_gates(signals)
    raw_conditions = effective.get(gate_name, _GATES[gate_name])

    conditions = [
        GateCondition(label=label, met=bool(check(signals)))
        for label, check in raw_conditions
    ]

    return GateReport(
        current_phase=phase,
        is_override=result.is_override,
        target_phase=target_phase,
        gate_name=gate_name,
        conditions=conditions,
    )


def format_gate_report(report: GateReport) -> str:
    """Format a gate report as a colored terminal string."""
    phase_label = report.current_phase.name.replace("_", " ")
    phase_num = report.current_phase.value
    override = " (override)" if report.is_override else ""

    lines = [
        f"{BLUE}Current phase: {phase_label} ({phase_num}/4){override}{NC}",
        "",
    ]

    if report.target_phase is None:
        lines.append(f"{GREEN}Phase DEPLOY reached — no further gates.{NC}")
        return "\n".join(lines)

    target_label = report.target_phase.name.replace("_", " ")
    lines.append(f"Gates to {target_label}:")

    for cond in report.conditions:
        if cond.met:
            lines.append(f"  {GREEN}\u2705 {cond.label}{NC}")
        else:
            lines.append(f"  {RED}\u274c {cond.label}{NC}")

    lines.append("")
    if report.all_met:
        lines.append(
            f"{GREEN}Status: {report.met_count}/{report.total_count} gates met"
            f" \u2014 READY TO PROMOTE{NC}"
        )
    else:
        lines.append(
            f"{YELLOW}Status: {report.met_count}/{report.total_count} gates met"
            f" \u2014 CANNOT PROMOTE{NC}"
        )

    return "\n".join(lines)


def promote_phase(root: Path, force: bool = False) -> bool:
    """Attempt to promote to the next phase.

    Returns True if promotion succeeded, False if blocked.
    """
    report = check_gates(root)

    if report.target_phase is None:
        logger.info("Already at DEPLOY — nothing to promote.")
        return False

    if not report.all_met and not force:
        return False

    # Update methodology.yaml
    target = report.target_phase
    methodology_path = root / ".vibesrails" / "methodology.yaml"

    if methodology_path.exists():
        content = yaml.safe_load(methodology_path.read_text())
        if not isinstance(content, dict):
            content = {}
    else:
        (root / ".vibesrails").mkdir(exist_ok=True)
        content = {}

    if "methodology" not in content:
        content["methodology"] = {}
    content["methodology"]["current_phase"] = target.value

    methodology_path.write_text(yaml.dump(content, default_flow_style=False))
    return True


def set_phase(root: Path, phase_num: int) -> bool:
    """Set the current phase override in methodology.yaml.

    Args:
        phase_num: Phase number 0-4, or -1 for 'auto'.

    Returns True if set successfully.
    """
    methodology_path = root / ".vibesrails" / "methodology.yaml"

    if methodology_path.exists():
        content = yaml.safe_load(methodology_path.read_text())
        if not isinstance(content, dict):
            content = {}
    else:
        (root / ".vibesrails").mkdir(exist_ok=True)
        content = {}

    if "methodology" not in content:
        content["methodology"] = {}

    if phase_num == -1:
        content["methodology"]["current_phase"] = "auto"
    else:
        content["methodology"]["current_phase"] = phase_num

    methodology_path.write_text(yaml.dump(content, default_flow_style=False))
    return True
