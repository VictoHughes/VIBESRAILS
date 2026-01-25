# Claude Code Integration

Full installation with Claude Code hooks and project integration.

## Prerequisites

- Python 3.10 or higher
- pip
- git (for pre-commit hooks)
- Claude Code CLI (optional but recommended)

## Installation

### Option 1: In your project directory

**Unix/Mac:**
```bash
cd your-project
/path/to/install.sh
```

**Windows:**
```cmd
cd your-project
\path\to\install.bat
```

**Cross-platform:**
```bash
cd your-project
python /path/to/install.py
```

### Option 2: Specify project path

**Unix/Mac:**
```bash
./install.sh /path/to/your/project
```

**Windows:**
```cmd
install.bat C:\path\to\your\project
```

**Cross-platform:**
```bash
python install.py /path/to/your/project
```

## What it does

1. **Installs vibesrails** (if not already installed)
2. **Runs `vibesrails --setup`** with smart auto-configuration
3. **Creates these files:**

| File | Purpose |
|------|---------|
| `vibesrails.yaml` | Security scanner configuration |
| `CLAUDE.md` | Instructions for Claude Code |
| `.claude/hooks.json` | Claude Code hooks |
| `.git/hooks/pre-commit` | Auto-scan on commit |

## Claude Code Features After Installation

| Feature | Description |
|---------|-------------|
| **Auto-scan on commit** | Blocks commits with security issues |
| **Active plan display** | Shows current plan from `docs/plans/` |
| **Task tracking** | Reads `.claude/current-task.md` |
| **State preservation** | Auto-saves before context compaction |
| **Commit detection** | Prompts to update tasks after commits |

## Verify Installation

```bash
# Check vibesrails
vibesrails --version

# Run a scan
vibesrails --all

# Check created files
ls -la vibesrails.yaml CLAUDE.md .claude/hooks.json
```

## Troubleshooting

### "vibesrails.yaml not found" in Claude Code

The hooks expect to be run from your project root. Make sure you're in the correct directory.

### Pre-commit hook not running

Make sure the hook is executable:

```bash
chmod +x .git/hooks/pre-commit
```

### Claude Code doesn't see hooks

Restart Claude Code or reload the session. Hooks are loaded at session start.

### Want to customize hooks

Edit `.claude/hooks.json` directly. See [Claude Code hooks documentation](https://docs.anthropic.com/claude-code/hooks).

## Customization

### Add custom scan rules

Edit `vibesrails.yaml`:

```yaml
custom:
  - id: my_rule
    regex: "pattern"
    message: "Description"
```

### Skip certain files

```yaml
skip_dirs:
  - vendor
  - node_modules
  - .git

skip_files:
  - "*.min.js"
  - "package-lock.json"
```

### Change blocking behavior

```yaml
blocking:
  - hardcoded_password
  - api_key_exposed

non_blocking:
  - todo_fixme
```

## Uninstall

Remove created files:

```bash
rm vibesrails.yaml CLAUDE.md
rm -rf .claude
rm .git/hooks/pre-commit
pip uninstall vibesrails
```

## Manual Setup

If you prefer manual setup:

```bash
# Install
pip install vibesrails

# Setup project
cd your-project
vibesrails --setup

# This runs interactive setup with:
# - Project type detection
# - Language detection
# - Secret scanning
# - Claude Code hooks installation
```
