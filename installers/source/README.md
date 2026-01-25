# Source Installation

Install from source for development or to get the latest features before PyPI release.

## Prerequisites

- Python 3.10 or higher
- pip
- git

## Installation

### Option 1: Automatic (recommended)

**Unix/Mac:**
```bash
./install.sh
```

**Windows:**
```cmd
install.bat
```

**Cross-platform:**
```bash
python install.py
```

### Option 2: Manual

```bash
# Clone the repository
git clone https://github.com/VictoHughes/VIBESRAILS.git ~/.vibesrails

# Install in development mode
cd ~/.vibesrails
pip install -e .
```

## What the installer does

1. Clones the repository to `~/.vibesrails`
2. Installs in development mode (`pip install -e .`)
3. Creates command `vibesrails` available globally

## After Installation

```bash
cd your-project
vibesrails --setup
```

## Verify Installation

```bash
vibesrails --version
vibesrails --help
```

## Update to Latest

```bash
cd ~/.vibesrails
git pull
pip install -e .
```

## Troubleshooting

### "command not found: vibesrails"

The scripts directory isn't in your PATH:

```bash
# Check if installed
python -m vibesrails --version

# Add to PATH (Unix/Mac - add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Windows - add %APPDATA%\Python\Scripts to PATH
```

### Permission denied on clone

Make sure you have git configured:

```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

### Already installed, want fresh install

```bash
rm -rf ~/.vibesrails
./install.sh
```

## Uninstall

```bash
pip uninstall vibesrails
rm -rf ~/.vibesrails
```

## Development

If you want to contribute:

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR-USERNAME/VIBESRAILS.git
cd VIBESRAILS
pip install -e ".[dev]"
pytest
```
