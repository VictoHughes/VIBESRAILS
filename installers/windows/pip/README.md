# pip Installation (Windows)

## Quick Start

Double-click `install.bat` or:

```cmd
install.bat
```

Or directly:
```cmd
pip install vibesrails
```

## After Installation

```cmd
cd your-project
vibesrails --setup
```

## Troubleshooting

### "vibesrails is not recognized"

Add Python Scripts to PATH:
1. Open System Properties > Environment Variables
2. Add `%APPDATA%\Python\Scripts` to PATH

### Permission denied

```cmd
pip install --user vibesrails
```
