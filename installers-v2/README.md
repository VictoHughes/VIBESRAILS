# VibesRails v2.0 - Installation Guide

> From KIONOS (free tools) - Developed by SM

## What's New in v2.0

VibesRails v2.0 introduces **15 security & quality guards**, **Senior Mode** for AI coding safety, and **architecture mapping** to keep your codebase clean and secure.

### v2.0 Features

- **15 Guards**: Security, performance, complexity, dependency audit, env safety, dead code, observability, error handling, type safety, PR checklist, API design, pre-deploy checklist, upgrade advisor, community packs
- **Senior Mode**: AI coding safety with hallucination detection, bypass detection, lazy code detection, and resilience checks
- **Architecture Mapping**: Auto-generates `ARCHITECTURE.md` so AI tools know where to put code
- **Community Packs**: Share and install custom pattern packs

### v2.0 CLI Commands

```bash
vibesrails --all          # Scan entire project
vibesrails --setup        # Setup new project
vibesrails --senior       # Run Senior Mode analysis
vibesrails --show         # Show configured patterns
vibesrails --watch        # Live scanning mode
vibesrails --learn        # AI pattern discovery
vibesrails --fix          # Auto-fix issues
vibesrails --audit        # Dependency audit
vibesrails --upgrade      # Upgrade advisor
vibesrails --stats        # View scan statistics
```

## Installation Options

### Quick Install (pip)

The fastest way to get started:

| Platform | Command |
|----------|---------|
| **Unix/macOS** | `bash unix/pip/install.sh` |
| **Windows** | `windows\pip\install.bat` |
| **Any (Python)** | `python3 cross-platform/pip/install.py` |

### From Source

Install from the GitHub repository for development or latest changes:

| Platform | Command |
|----------|---------|
| **Unix/macOS** | `bash unix/source/install.sh` |
| **Windows** | `windows\source\install.bat` |
| **Any (Python)** | `python3 cross-platform/source/install.py` |

### Claude Code Integration

Installs VibesRails AND sets up Claude Code hooks, templates, and pre-commit scanning:

| Platform | Command |
|----------|---------|
| **Unix/macOS** | `bash unix/claude-code/install.sh [project-path]` |
| **Windows** | `windows\claude-code\install.bat [project-path]` |
| **Any (Python)** | `python3 cross-platform/claude-code/install.py [project-path]` |

This installs:
- `vibesrails.yaml` - Security patterns configuration
- `CLAUDE.md` - Claude Code instructions
- `.claude/hooks.json` - Session automation hooks
- `.git/hooks/pre-commit` - Pre-commit security scanning

### Complete Package (Offline)

For air-gapped or offline installations. Includes the `.whl` file and all templates:

| Platform | Command |
|----------|---------|
| **Unix/macOS** | `bash complete-package/INSTALL.sh /path/to/project` |
| **Windows** | `complete-package\INSTALL.bat C:\path\to\project` |

Requires the wheel file `vibesrails-2.0.0-py3-none-any.whl` in the `complete-package/` directory.

## Directory Structure

```
installers-v2/
├── README.md                          # This file
├── unix/
│   ├── pip/install.sh                 # pip install (Unix/macOS)
│   ├── source/install.sh              # Source install (Unix/macOS)
│   └── claude-code/install.sh         # Claude Code integration (Unix/macOS)
├── windows/
│   ├── pip/install.bat                # pip install (Windows)
│   ├── source/install.bat             # Source install (Windows)
│   └── claude-code/install.bat        # Claude Code integration (Windows)
├── cross-platform/
│   ├── pip/install.py                 # pip install (Python, any OS)
│   ├── source/install.py              # Source install (Python, any OS)
│   └── claude-code/install.py         # Claude Code integration (Python, any OS)
└── complete-package/
    ├── INSTALL.sh                     # Complete offline install (Unix/macOS)
    └── INSTALL.bat                    # Complete offline install (Windows)
```

## Requirements

- Python 3.10+
- pip (for pip and complete-package installers)
- git (for source installers and Claude Code integration)

## Manual Install

If you prefer to install manually:

```bash
pip install "vibesrails[all]>=2.0.0"
cd your-project
vibesrails --setup
```

## Support

- **Repository**: https://github.com/VictoHughes/VIBESRAILS
- **Issues**: https://github.com/VictoHughes/VIBESRAILS/issues
- **Support**: https://buymeacoffee.com/vibesrails
