"""
vibesrails Agent Guardian - Safety layer for AI-assisted coding.

Detects AI coding sessions and applies stricter rules.
Tracks patterns that AI agents commonly violate.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .scanner import RED, YELLOW, GREEN, BLUE, NC, ScanResult


# Environment variables that indicate AI coding
AI_ENV_MARKERS = [
    "CLAUDE_CODE",           # Claude Code CLI
    "CURSOR_SESSION",        # Cursor IDE
    "COPILOT_AGENT",         # GitHub Copilot
    "AIDER_SESSION",         # Aider
    "CONTINUE_SESSION",      # Continue.dev
    "CODY_SESSION",          # Sourcegraph Cody
    "VIBESRAILS_AGENT_MODE", # Manual override
]

# Git author patterns that indicate AI
AI_GIT_PATTERNS = [
    "claude",
    "copilot",
    "cursor",
    "ai-assisted",
    "anthropic",
    "openai",
]


def is_ai_session() -> bool:
    """Detect if current session is AI-assisted coding."""
    # Check environment variables
    for marker in AI_ENV_MARKERS:
        if os.environ.get(marker):
            return True

    # Check if running inside Claude Code (common indicator)
    if os.environ.get("TERM_PROGRAM") == "claude-code":
        return True

    # Check for Claude Code specific paths
    if Path.home().joinpath(".claude").exists():
        # Could check for active session, but existence is a good hint
        pass

    return False


def get_ai_agent_name() -> str | None:
    """Get the name of the AI agent if detected."""
    if os.environ.get("CLAUDE_CODE"):
        return "Claude Code"
    if os.environ.get("CURSOR_SESSION"):
        return "Cursor"
    if os.environ.get("COPILOT_AGENT"):
        return "GitHub Copilot"
    if os.environ.get("AIDER_SESSION"):
        return "Aider"
    if os.environ.get("CONTINUE_SESSION"):
        return "Continue"
    if os.environ.get("CODY_SESSION"):
        return "Cody"
    if os.environ.get("VIBESRAILS_AGENT_MODE"):
        return "AI Agent (manual)"
    return None


def get_guardian_config(config: dict) -> dict:
    """Get guardian configuration from vibesrails config."""
    return config.get("guardian", {})


def should_apply_guardian(config: dict) -> bool:
    """Check if guardian mode should be applied."""
    guardian = get_guardian_config(config)

    # Disabled by default, must be explicitly enabled
    if not guardian.get("enabled", False):
        return False

    # Check if AI session detected
    if guardian.get("auto_detect", True) and is_ai_session():
        return True

    # Check if manually forced
    if guardian.get("force", False):
        return True

    return False


def get_stricter_patterns(config: dict) -> list[dict]:
    """Get additional stricter patterns for guardian mode."""
    guardian = get_guardian_config(config)
    return guardian.get("stricter_patterns", [])


def apply_guardian_rules(
    results: list[ScanResult],
    config: dict,
    filepath: str
) -> list[ScanResult]:
    """Apply guardian-specific rules to scan results.

    In guardian mode:
    - Warnings become blocking if configured
    - Additional stricter patterns are applied
    """
    guardian = get_guardian_config(config)

    if not should_apply_guardian(config):
        return results

    # Escalate warnings to blocking if configured
    if guardian.get("warnings_as_blocking", False):
        results = [
            ScanResult(
                file=r.file,
                line=r.line,
                pattern_id=r.pattern_id,
                message=f"[GUARDIAN] {r.message}",
                level="BLOCK" if r.level == "WARN" else r.level
            )
            for r in results
        ]

    return results


def log_guardian_block(result: ScanResult, agent_name: str | None = None):
    """Log when guardian blocks AI-generated code."""
    log_dir = Path(".vibesrails")

    # Symlink protection: ensure log directory is under cwd
    cwd = Path.cwd().resolve()
    log_dir_resolved = (cwd / log_dir).resolve()

    try:
        log_dir_resolved.relative_to(cwd)
    except ValueError:
        # Symlink attack detected - log dir points outside cwd
        print(f"{YELLOW}WARN: Guardian log directory is a symlink outside project{NC}")
        return

    log_dir_resolved.mkdir(exist_ok=True)
    log_file = log_dir_resolved / "guardian.log"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name or "unknown",
        "file": result.file,
        "line": result.line,
        "pattern_id": result.pattern_id,
        "message": result.message,
        "level": result.level,
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_guardian_stats() -> dict[str, Any]:
    """Get statistics from guardian log."""
    # Symlink protection: ensure log file is under cwd
    cwd = Path.cwd().resolve()
    log_file = (cwd / ".vibesrails" / "guardian.log").resolve()

    try:
        log_file.relative_to(cwd)
    except ValueError:
        # Symlink attack - don't read
        return {"total_blocks": 0, "by_pattern": {}, "by_agent": {}, "error": "symlink_detected"}

    if not log_file.exists():
        return {"total_blocks": 0, "by_pattern": {}, "by_agent": {}}

    total = 0
    by_pattern: dict[str, int] = {}
    by_agent: dict[str, int] = {}

    with open(log_file) as f:
        for line in f:
            try:
                entry = json.loads(line)
                total += 1

                pattern = entry.get("pattern_id", "unknown")
                by_pattern[pattern] = by_pattern.get(pattern, 0) + 1

                agent = entry.get("agent", "unknown")
                by_agent[agent] = by_agent.get(agent, 0) + 1

            except json.JSONDecodeError:
                continue

    return {
        "total_blocks": total,
        "by_pattern": by_pattern,
        "by_agent": by_agent,
    }


def show_guardian_stats():
    """Display guardian statistics."""
    stats = get_guardian_stats()

    print(f"\n{BLUE}=== Guardian Statistics ==={NC}\n")

    if stats["total_blocks"] == 0:
        print(f"{GREEN}No AI code blocks recorded yet.{NC}")
        return

    print(f"Total blocks: {stats['total_blocks']}\n")

    print(f"{YELLOW}By Pattern:{NC}")
    for pattern, count in sorted(stats["by_pattern"].items(), key=lambda x: -x[1]):
        print(f"  {pattern}: {count}")

    print(f"\n{YELLOW}By Agent:{NC}")
    for agent, count in sorted(stats["by_agent"].items(), key=lambda x: -x[1]):
        print(f"  {agent}: {count}")


def print_guardian_status(config: dict):
    """Print guardian mode status."""
    if should_apply_guardian(config):
        agent = get_ai_agent_name()
        agent_str = f" ({agent})" if agent else ""
        print(f"{YELLOW}GUARDIAN MODE ACTIVE{agent_str}{NC}")

        guardian = get_guardian_config(config)
        if guardian.get("warnings_as_blocking"):
            print(f"  - Warnings elevated to blocking")
