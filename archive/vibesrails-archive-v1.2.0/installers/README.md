# VibesRails 2.0 - Installation Guide

> 3-layer code protection (V1 regex + V2 AST guards + Senior Mode) with Claude Code integration — one command, everything is set up.

## TL;DR

```bash
pip install vibesrails
cd your-project
vibesrails --setup
```

`--setup` detects your project, generates config, installs hooks, wires Claude Code. Done.

---

## What Gets Installed

| File | Purpose |
|------|---------|
| `vibesrails.yaml` | V1 patterns: secrets, injection, architecture (DIP), complexity |
| `CLAUDE.md` | Instructions for Claude Code sessions |
| `.claude/hooks.json` | Full hook pipeline (SessionStart, Pre/PostToolUse, PreCompact) |
| `.git/hooks/pre-commit` | Auto-scan on every commit |

---

## Installation Methods

### 1. `vibesrails --setup` (recommended)

```bash
pip install vibesrails
cd your-project
vibesrails --setup
```

### 2. Self-contained installers

Each folder is **plug-and-play** — grab the folder, run the script, done.

| Folder | Platform | Script |
|--------|----------|--------|
| `mac-linux/` | macOS, Linux | `bash install.sh /path/to/project` |
| `windows/` | Windows | `install.bat C:\path\to\project` |
| `python/` | Any OS | `python install.py /path/to/project` |
| `offline/` | Air-gapped | `bash INSTALL.sh` (needs `.whl` in folder) |
| `drag-and-drop/` | macOS, Linux | Drag folder into project |

Each folder contains:
- `install.sh` / `install.bat` / `install.py` — the installer
- `vibesrails.yaml` — full config (security + bugs + DIP + guardian)
- `CLAUDE.md` — Claude Code instructions
- `.claude/hooks.json` — full session automation hooks

### 3. Pip only (no Claude Code config)

```bash
pip install vibesrails
```

---

## What It Does

### Layer 1: V1 Regex Scanner (automatic on commit)

- **Blocks:** hardcoded secrets, SQL/command/shell injection, unsafe yaml/numpy, debug mode, mutable defaults
- **Warns:** star imports, bare except, print statements, TODOs, None comparison

### Layer 2: V2 AST Guards (automatic on Write/Edit + SessionStart)

16 guards that analyze your code's AST:

| Guard | What it catches |
|-------|----------------|
| DeadCode | Unused imports, variables, functions |
| Observability | Missing logging, error tracking |
| Complexity | High cyclomatic complexity |
| Performance | N+1 queries, blocking I/O, unnecessary copies |
| TypeSafety | Missing type hints, unsafe casts |
| APIDesign | Inconsistent API patterns |
| DatabaseSafety | Raw SQL, missing transactions |
| EnvSafety | Hardcoded config, missing env validation |
| ArchitectureDrift | Layer violations (domain importing infra) |
| TestIntegrity | Weak assertions, test smells |
| Mutation | Dead code via mutation testing |
| DependencyAudit | CVEs, outdated packages |
| Docstring | Missing or outdated docstrings |
| GitWorkflow | Branch naming, commit messages |
| PRChecklist | PR completeness |
| PreDeploy | Production readiness |

### Layer 3: Senior Mode / Guardian (automatic)

8 AI-specific guards that detect AI coding mistakes:

| Guard | What it catches |
|-------|----------------|
| DiffSize | Oversized commits (> 400 lines) |
| ErrorHandling | Bare except, swallowed errors |
| Hallucination | Imports/calls to nonexistent modules |
| Dependency | Undeclared or unused dependencies |
| TestCoverage | Modified code without test updates |
| LazyCode | TODO/FIXME, pass, placeholder code |
| Bypass | Attempts to disable security |
| Resilience | Missing retry, timeout, circuit breaker |

### Claude Code Hook Pipeline

| Hook | When | What |
|------|------|------|
| **SessionStart** | Open Claude Code | Full project scan (V2 + Senior), plan detection, task restore, session lock |
| **PreToolUse** | Before Write/Edit/Bash | Blocks secrets, injection, eval/exec |
| **PostToolUse** (Write/Edit) | After file changes | V1 + 8 V2 guards + 5 Senior guards per file |
| **PostToolUse** (Bash) | After git commit | DiffSize + TestCoverage + ArchitectureDrift |
| **PreCompact** | Before compaction | Auto-saves task state to `.claude/current-task.md` |
| **SessionEnd** | Close session | Releases session lock |

### Additional Features

- **Session lock** — detects multiple Claude Code sessions on same project
- **Throttle** — prevents write storms
- **Inbox** — async instructions between sessions (`.claude/inbox.md`)
- **Queue** — deferred tasks (`.claude/queue.jsonl`)
- **Plan detection** — finds active plans in `docs/plans/`
- **Task restore** — recreates TaskList from `.claude/current-task.md` after compaction

---

## Commands Reference

```bash
# Core
vibesrails              # Scan staged files (pre-commit)
vibesrails --all        # Scan entire project
vibesrails --setup      # Smart auto-setup
vibesrails --show       # Show configured patterns
vibesrails --fix        # Auto-fix simple issues
vibesrails --watch      # Live scanning on file save

# V2 Guards
vibesrails --senior-v2  # Run all 16 V2 guards
vibesrails --dead-code  # Detect unused code
vibesrails --complexity # Analyze complexity
vibesrails --env-check  # Environment safety
vibesrails --audit-deps # Dependency audit (CVEs)
vibesrails --mutation   # Mutation testing
vibesrails --pr-check   # PR checklist
vibesrails --pre-deploy # Pre-deploy checks
vibesrails --test-integrity  # Test quality

# Senior Mode
vibesrails --senior     # Run all 8 Senior guards

# Utils
vibesrails --stats      # Scan statistics
vibesrails --learn      # AI-powered pattern discovery
vibesrails --hook       # Install/update git hook
vibesrails --validate   # Validate config
```

---

## Verify Installation

```bash
vibesrails --all          # Scan project
vibesrails --show         # Show all patterns
vibesrails --validate     # Check config
vibesrails --senior-v2    # Run V2 guards
```

---

## Directory Structure

```
installers/
├── README.md              # This file
├── claude-code/           # Claude Code specific hooks
│   └── hooks/ptuh.py      # Self-protection hook
├── mac-linux/             # macOS/Linux installer
│   ├── install.sh
│   ├── vibesrails.yaml
│   ├── CLAUDE.md
│   └── .claude/hooks.json
├── windows/               # Windows installer
│   ├── install.bat
│   ├── vibesrails.yaml
│   ├── CLAUDE.md
│   └── .claude/hooks.json
├── python/                # Cross-platform installer
│   ├── install.py
│   ├── vibesrails.yaml
│   ├── CLAUDE.md
│   └── .claude/hooks.json
├── offline/               # Air-gapped installer
│   ├── INSTALL.sh
│   ├── INSTALL.bat
│   ├── vibesrails.yaml
│   ├── CLAUDE.md
│   ├── .claude/hooks.json
│   └── vibesrails-*.whl   # (add before use)
└── drag-and-drop/         # Drag-and-drop installer
    ├── vibesrails.yaml
    ├── CLAUDE.md
    └── .claude/hooks.json
```

## Support

- https://github.com/VictoHughes/VIBESRAILS
- https://github.com/VictoHughes/VIBESRAILS/issues
