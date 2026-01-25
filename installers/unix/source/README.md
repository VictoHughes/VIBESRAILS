# Source Installation (Unix/Mac)

## Quick Start

```bash
./install.sh
```

## What it does

1. Clones repository to `~/.vibesrails`
2. Installs in development mode (`pip install -e .`)

## After Installation

```bash
cd your-project
vibesrails --setup
```

## Update

```bash
cd ~/.vibesrails
git pull
pip install -e .
```

## Troubleshooting

### Fresh install

```bash
rm -rf ~/.vibesrails
./install.sh
```
