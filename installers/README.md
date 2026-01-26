# VibesRails Installers

## By Operating System

| OS | Folder | Scripts |
|----|--------|---------|
| **Linux/macOS** | [unix/](./unix/) | `.sh` |
| **Windows** | [windows/](./windows/) | `.bat` |
| **Any** | [cross-platform/](./cross-platform/) | `.py` |

## By Installation Type

| Type | Description | Usage |
|------|-------------|-------|
| **pip** | Standard installation | `pip install vibesrails` |
| **source** | Development / latest | Clone + `pip install -e .` |
| **claude-code** | Full Claude Code integration | Install + setup project |

## Quick Reference

### Unix/Mac
```bash
./unix/pip/install.sh              # Standard
./unix/source/install.sh           # Development
./unix/claude-code/install.sh      # Claude Code
```

### Windows
```cmd
windows\pip\install.bat            # Standard
windows\source\install.bat         # Development
windows\claude-code\install.bat    # Claude Code
```

### Cross-Platform (Python)
```bash
python cross-platform/pip/install.py              # Standard
python cross-platform/source/install.py           # Development
python cross-platform/claude-code/install.py      # Claude Code
```

## Requirements

- Python 3.10+
- pip
- git (for source and claude-code)

## After Installation

```bash
cd your-project
vibesrails --setup
```
