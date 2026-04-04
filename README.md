# VibesRails

**Engineering methodology enforcer for AI-assisted development.**

Your AI agent writes 200 files per hour. VibesRails makes sure it follows your specs, respects your architecture, and doesn't skip the steps that matter.

![Version](https://img.shields.io/badge/version-2.3.0-blue)
![Tests](https://img.shields.io/badge/tests-2283_passing-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-Apache_2.0-orange)
![PyPI](https://img.shields.io/pypi/v/vibesrails)

## The Problem

AI coding agents (Claude Code, Cursor, Copilot) generate code fast. But nobody enforces **how** they work:

- No specs before implementation? The agent codes anyway.
- Architecture not decided? The agent creates 12 files.
- Stabilization phase? The agent adds a new feature.

Fast without structure = technical debt at scale.

## What VibesRails Does

VibesRails detects where you are in your project, adapts its strictness, and enforces engineering discipline automatically.

```
DECIDE  →  SKELETON  →  FLESH OUT  →  STABILIZE  →  DEPLOY
  ↓           ↓            ↓             ↓            ↓
Require     Require     Warn if no     Block new     Limit diff
ADR docs    contracts   test-first     features      size
```

| Capability | How it works |
|------------|-------------|
| **Phase detection** | Reads your project signals (ADRs, tests, CI, tags) to know if you're in R&D or shipping |
| **Context adaptation** | R&D mode = relaxed thresholds; Bugfix mode = surgical precision; 7 signals scored |
| **Gate enforcement** | `--check-gates` shows what's missing; `--promote` advances only when conditions are met |
| **Runtime interception** | Hooks block bad code **before** the file is written — not after commit like linters |
| **Doc sync** | `--sync-claude` auto-generates CLAUDE.md from code; `--preflight` checks doc freshness |
| **Assertions** | Define project truths (version, test count, rules) — VR validates them every session |

## Quick Start

```bash
pip install vibesrails
vibesrails --init-methodology    # Create phase scaffolding (ADR/, methodology.yaml)
vibesrails --preflight           # Check project health before coding
```

That's it. VibesRails now adapts to your project phase and enforces methodology through hooks.

### Claude Code (full integration)

```bash
pip install vibesrails[mcp]      # Also installs MCP server
vibesrails --setup               # Auto-configure hooks + MCP
```

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "vibesrails": {
      "command": "vibesrails-mcp",
      "args": []
    }
  }
}
```

### Other agents (Cursor, Copilot, Windsurf, Continue.dev)

```bash
pip install vibesrails[mcp]
vibesrails-mcp                   # Starts MCP server (stdio)
```

12 tools available over MCP. See [MCP Tools](#mcp-tools) below.

## Features

### Methodology Enforcement

| Command | What it does |
|---------|-------------|
| `--init-methodology` | Create ADR/, methodology.yaml, phase scaffolding |
| `--check-gates` | Show what's blocking next phase advancement |
| `--promote` | Advance to next phase (only if gates pass) |
| `--force-promote` | Force advance (override gates) |
| `--set-phase N` | Manual phase override (-1=auto, 0-4=specific phase) |
| `--check-assertions` | Validate project truths (version, test count, rules) |
| `--preflight` | Pre-session checklist: branch, tests, config, docs, mode |

### Context Detection

| Feature | Description |
|---------|-------------|
| Session modes | Auto-detect R&D / Mixed / Bugfix from 7 signals |
| `--mode rnd\|bugfix\|auto` | Force session mode |
| Phase detection | DECIDE → SKELETON → FLESH OUT → STABILIZE → DEPLOY |
| Threshold adaptation | Thresholds tighten or relax based on mode + phase |

### Security (Runtime)

| Layer | When | What |
|-------|------|------|
| **PreToolUse** | Before Write/Edit/Bash | Blocks secrets, SQL injection, eval/exec |
| **PostToolUse** | After Write/Edit | Auto-scans with 16 AST guards + 7 senior guards |
| **Throttle** | Every 5 writes | Forces verification, prevents runaway agents |
| **Scope Guard** | After commit | Reminds rules, prevents scope creep |

17 regex patterns, 16 AST guards, 7 senior guards, 22 secret patterns, Semgrep integration.

### AI-Aware

| Tool | What it detects |
|------|----------------|
| Guardian Mode | 7 AI agent signatures (Claude, Cursor, Copilot, Windsurf...) |
| `deep_hallucination` | Fake imports, slopsquatting, non-existent packages |
| `shield_prompt` | 5-category prompt injection detection |
| `check_config` | Rules File Backdoor attacks in .cursorrules, CLAUDE.md |

### Developer Experience

| Tool | What it does |
|------|-------------|
| `--sync-claude` | Auto-generate factual CLAUDE.md sections from code |
| `--sync-memory` | Auto-generate PROJECT_MEMORY.md from runtime data |
| `--watch` | Live scanning on file save |
| `--fix` / `--dry-run` | Auto-fix simple patterns |
| `--learn` | Pattern discovery (experimental) |
| Learning Engine | Cross-session profiling, improvement metrics, SQLite persistence |

## How It Compares

| Feature | VibesRails | Semgrep | Snyk | ESLint/Ruff |
|---------|-----------|---------|------|-------------|
| Phase-aware methodology | **Yes** | No | No | No |
| Context adaptation (R&D/Bugfix) | **Yes** | No | No | No |
| Gate-based progression | **Yes** | No | No | No |
| Runtime interception (pre-write) | **Yes** | No | No | No |
| Auto-doc generation | **Yes** | No | No | No |
| Static analysis | Yes | **Yes (deep)** | **Yes** | **Yes** |
| CVE database | Yes (via Semgrep) | **Yes (native)** | **Yes (native)** | No |
| Language coverage | Python | **40+ languages** | **40+ languages** | JS/TS / Python |
| IDE integration | MCP (any agent) | IDE plugins | IDE plugins | IDE plugins |

VibesRails is not a replacement for Semgrep or Snyk. It fills a different gap: **enforcing engineering process**, not just finding bugs.

## MCP Tools

12 tools available over MCP protocol:

| Tool | Category | Description |
|------|----------|-------------|
| `ping` | Health | Server status and version |
| `scan_code` | Security | 16 AST guards on code |
| `scan_senior` | Security | 7 senior guards on code |
| `scan_semgrep` | Security | Semgrep vulnerability scan |
| `check_session` | AI-Aware | Detect AI-assisted session |
| `monitor_entropy` | AI-Aware | Session health tracking |
| `deep_hallucination` | AI-Aware | Multi-level import verification |
| `check_config` | AI-Aware | Config file attack detection |
| `check_drift` | Methodology | Architecture drift velocity |
| `enforce_brief` | Methodology | Pre-generation brief validation |
| `shield_prompt` | Security | Prompt injection detection |
| `get_learning` | DX | Cross-session developer profiling |

## CLI Reference

| Category | Commands | Count |
|----------|---------|-------|
| Methodology | `--init-methodology`, `--check-gates`, `--promote`, `--check-assertions`, `--preflight` | 7 |
| Scanning | `--all`, `--file`, `--senior`, `--senior-v2` | 7 |
| Context | `--mode`, `--sync-claude`, `--sync-memory` | 3 |
| Specialized | `--audit-deps`, `--complexity`, `--mutation`, `--dead-code`, `--test-integrity` | 13 |
| Auto-fix | `--fix`, `--dry-run`, `--no-backup` | 3 |
| Session | `--watch`, `--queue`, `--inbox`, `--throttle-status` | 6 |
| Setup | `--init`, `--setup`, `--hook`, `--validate` | 7 |

Run `vibesrails --help` for full details.

## Install

```bash
# Recommended
pipx install vibesrails

# With MCP server
pipx install vibesrails[mcp]

# From source (developer)
git clone https://github.com/VictoHughes/VIBESRAILS.git
cd VIBESRAILS
make install-dev
make test   # 2283 tests
```

## Security

2283 tests including 111 security-specific tests. Path traversal protection,
SQL injection prevention, ReDoS verification, filesystem sandbox,
rate limiting, structured logging with data redaction.

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

Apache 2.0 — free for everyone.
