# pip Installation

The simplest way to install vibesrails.

## Prerequisites

- Python 3.10 or higher
- pip (included with Python)

## Installation

### Option 1: Direct command

```bash
pip install vibesrails
```

### Option 2: Using the installer script

**Unix/Mac:**
```bash
./install.sh
```

**Windows:**
```powershell
python install.py
```

**Or cross-platform:**
```bash
python install.py
```

## After Installation

Navigate to your project and run setup:

```bash
cd your-project
vibesrails --setup
```

This creates a `vibesrails.yaml` configuration tailored to your project.

## Verify Installation

```bash
vibesrails --version
vibesrails --help
```

## Troubleshooting

### "command not found: vibesrails"

Your Python scripts directory isn't in PATH. Try:

```bash
python -m vibesrails --version
```

Or add to PATH:
- **Unix/Mac:** Add `~/.local/bin` to your PATH
- **Windows:** Add `%APPDATA%\Python\Scripts` to your PATH

### Permission denied

Use user install:

```bash
pip install --user vibesrails
```

### Upgrade to latest version

```bash
pip install --upgrade vibesrails
```

## Uninstall

```bash
pip uninstall vibesrails
```
