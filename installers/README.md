# VibesRails - Installation Guide

> Security scanner + Claude Code integration — one command, everything is set up.

## TL;DR

```bash
pip install vibesrails
cd your-project
vibesrails --setup
```

That's it. `--setup` creates everything: config, hooks, pre-commit.

---

## What Gets Installed

| File | Purpose |
|------|---------|
| `vibesrails.yaml` | Security patterns, bugs, architecture (DIP), complexity |
| `CLAUDE.md` | Instructions for Claude Code sessions |
| `.claude/hooks.json` | Session automation (plans, tasks, scan reminders) |
| `.git/hooks/pre-commit` | Auto-scan on every commit |

## Installation Methods

### 1. `vibesrails --setup` (recommended)

```bash
pip install vibesrails
cd your-project
vibesrails --setup
```

- Detects your project type (Django, FastAPI, Flask, etc.)
- Detects architecture layers (domain, infrastructure, application)
- Generates DIP rules automatically if layers found
- Creates all 4 files
- Interactive: asks what protections you want

### 2. Installer Scripts

For automated/CI environments or if you want the bundled templates.

**Mac/Linux:**
```bash
bash installers/unix/claude-code/install.sh /path/to/project
```

**Windows:**
```cmd
installers\windows\claude-code\install.bat C:\path\to\project
```

**Any OS (Python):**
```bash
python3 installers/cross-platform/claude-code/install.py /path/to/project
```

### 3. Offline / Air-gapped

For environments without internet. Requires the `.whl` file in `complete-package/`.

```bash
bash installers/complete-package/INSTALL.sh /path/to/project
```

### 4. Pip Only (no Claude Code config)

Just the scanner, no hooks/CLAUDE.md:

```bash
pip install vibesrails
```

### 5. From Source (development)

```bash
bash installers/unix/source/install.sh
# or
python3 installers/cross-platform/source/install.py
```

---

## What It Does After Install

### Security Scanning (automatic on commit)

- Blocks: hardcoded secrets, SQL/command/shell injection, unsafe yaml/numpy, debug mode
- Warns: star imports, bare except, print statements, TODOs, None comparison

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
- Generates `ARCHITECTURE.md`

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
├── README.md                              # This file
├── templates/claude-code/                 # Source templates (single source of truth)
│   ├── vibesrails.yaml                    #   Full config (security + bugs + DIP + complexity)
│   ├── CLAUDE.md                          #   Claude Code instructions
│   └── .claude/hooks.json                 #   Session automation
├── unix/                                  # Mac/Linux scripts
│   ├── pip/install.sh                     #   pip install
│   ├── source/install.sh                  #   git clone + editable install
│   └── claude-code/install.sh             #   Full setup (pip + templates + hook)
├── windows/                               # Windows scripts
│   ├── pip/install.bat
│   ├── source/install.bat
│   └── claude-code/install.bat
├── cross-platform/                        # Python scripts (any OS)
│   ├── pip/install.py
│   ├── source/install.py
│   └── claude-code/install.py
└── complete-package/                      # Offline install (includes .whl)
    ├── INSTALL.sh
    ├── INSTALL.bat
    └── claude-code/                       #   Bundled templates
```

## Support

- https://github.com/VictoHughes/VIBESRAILS
- https://github.com/VictoHughes/VIBESRAILS/issues
