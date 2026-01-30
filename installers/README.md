# VibesRails - Installation Guide

> Security scanner + Claude Code integration — one command, everything is set up.

## TL;DR (recommended)

```bash
pip install vibesrails
cd your-project
vibesrails --setup
```

`--setup` detects your project, generates config, installs hooks. Done.

---

## What Gets Installed

| File | Purpose |
|------|---------|
| `vibesrails.yaml` | Security patterns, bugs, architecture (DIP), complexity |
| `CLAUDE.md` | Instructions for Claude Code sessions |
| `.claude/hooks.json` | Session automation (plans, tasks, scan reminders) |
| `.git/hooks/pre-commit` | Auto-scan on every commit |

---

## Installation Methods

### 1. `vibesrails --setup` (recommended)

Interactive setup that detects your project structure:

```bash
pip install vibesrails
cd your-project
vibesrails --setup
```

### 2. Self-contained installers

Each folder below is **plug-and-play** — grab the folder, run the script, done.

| Folder | Platform | Script |
|--------|----------|--------|
| `mac-linux/` | macOS, Linux | `bash install.sh /path/to/project` |
| `windows/` | Windows | `install.bat C:\path\to\project` |
| `python/` | Any OS | `python install.py /path/to/project` |
| `offline/` | Air-gapped | `bash INSTALL.sh` (needs `.whl` in folder) |

Each folder contains:
- `install.sh` / `install.bat` / `install.py` — the installer
- `vibesrails.yaml` — full config (security + bugs + DIP + guardian)
- `CLAUDE.md` — Claude Code instructions
- `.claude/hooks.json` — session automation hooks

### 3. Pip only (no Claude Code config)

```bash
pip install vibesrails
```

---

## What It Does

### Security Scanning (automatic on commit)

- **Blocks:** hardcoded secrets, SQL/command/shell injection, unsafe yaml/numpy, debug mode
- **Warns:** star imports, bare except, print statements, TODOs, None comparison

### Bug Detection

- Mutable default arguments (blocks)
- Assert in production code (warns)

### Architecture Enforcement (DIP)

- Domain cannot import Infrastructure
- Domain cannot import Application
- Auto-detected from project structure by `--setup`

### Claude Code Integration

| Hook | When | What |
|------|------|------|
| SessionStart | Open Claude Code | Shows active plan + current task |
| PreCompact | Before compaction | Auto-saves task state |
| PostToolUse (Write) | First edit | Reminds about scanning |
| PostToolUse (Bash) | After commands | Detects new commits |

### Guardian / Senior Mode

- Auto-detects AI coding sessions
- Runs 8 guards: DiffSize, ErrorHandling, Hallucination, Dependency, TestCoverage, LazyCode, Bypass, Resilience

---

## Verify Installation

```bash
vibesrails --all          # Scan project
vibesrails --show         # Show all patterns
vibesrails --validate     # Check config
```

## Commands Reference

```bash
vibesrails                # Scan staged files (pre-commit)
vibesrails --all          # Scan entire project
vibesrails --setup        # Setup new project
vibesrails --show         # Show configured patterns
vibesrails --watch        # Live scanning on file save
vibesrails --learn        # AI-powered pattern discovery
vibesrails --fix          # Auto-fix simple issues
vibesrails --senior       # Manual Senior Mode
vibesrails --stats        # View scan statistics
vibesrails --hook         # Install/update git hook
```

---

## Directory Structure

```
installers/
├── README.md              # This file
├── mac-linux/             # Self-contained Mac/Linux installer
│   ├── install.sh
│   ├── vibesrails.yaml
│   ├── CLAUDE.md
│   └── .claude/hooks.json
├── windows/               # Self-contained Windows installer
│   ├── install.bat
│   ├── vibesrails.yaml
│   ├── CLAUDE.md
│   └── .claude/hooks.json
├── python/                # Self-contained cross-platform installer
│   ├── install.py
│   ├── vibesrails.yaml
│   ├── CLAUDE.md
│   └── .claude/hooks.json
└── offline/               # Self-contained offline installer
    ├── INSTALL.sh
    ├── INSTALL.bat
    ├── vibesrails.yaml
    ├── CLAUDE.md
    ├── .claude/hooks.json
    └── vibesrails-*.whl   # (add before use)
```

## Support

- https://github.com/VictoHughes/VIBESRAILS
- https://github.com/VictoHughes/VIBESRAILS/issues
