# Design: PROJECT_MEMORY.md — Auto-generated Project Memory

**Date:** 2026-03-06
**Approach:** B — Dedicated `sync_memory.py` module

## Problem

CLAUDE.md = work instructions (prescriptive). No file captures institutional memory:
decisions, drift history, quality trends, execution flows, known issues.

## Solution

New `vibesrails/sync_memory.py` module + `--sync-memory` CLI command.
Generates/updates `PROJECT_MEMORY.md` at project root using `<!-- AUTO:section -->` markers.

## Sections

| Section | Source | Data |
|---------|--------|------|
| `AUTO:drift` | SQLite drift_snapshots | velocity, trend, consecutive high-drift |
| `AUTO:quality` | SQLite learning_events + developer_profile | top violations, hallucination rate, improvement |
| `AUTO:flows` | Static AST introspection | module dependency map, data flow |
| `AUTO:health` | SQLite sessions | entropy avg, session count, brief scores |
| `AUTO:baselines` | vibesrails.yaml assertions | test count, version, fail_closed |
| `AUTO:context` | Context detector | current mode, signals, thresholds |
| MANUAL: Decisions Log | Human-written | Architecture decisions with date/context |
| MANUAL: Known Issues | Human-written | Bugs, workarounds |

## Architecture

- `vibesrails/sync_memory.py` — section generators + merge engine (reuse pattern from sync_claude.py)
- CLI: `vibesrails --sync-memory` in cli.py
- Graceful degradation: no DB → "No data yet" per section
- No new dependencies

## Trigger

- Manual: `vibesrails --sync-memory`
- Optional: SessionEnd hook (future)
