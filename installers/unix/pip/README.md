# pip Installation (Unix/Mac)

## Quick Start

```bash
./install.sh
```

Or directly:
```bash
pip install vibesrails
```

## After Installation

```bash
cd your-project
vibesrails --setup
```

## Troubleshooting

### "command not found: vibesrails"

Add `~/.local/bin` to your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Permission denied

```bash
pip install --user vibesrails
```
