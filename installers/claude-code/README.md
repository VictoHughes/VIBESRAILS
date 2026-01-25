# Claude Code Integration

Full installation with Claude Code hooks and integration.

## Quick Install

```bash
./install.sh /path/to/your/project
```

Or in current directory:
```bash
./install.sh
```

## What it does

1. Installs vibesrails (if not already installed)
2. Runs `vibesrails --setup` on your project
3. Creates:
   - `vibesrails.yaml` - Security scanner config
   - `CLAUDE.md` - Instructions for Claude Code
   - `.claude/hooks.json` - Claude Code hooks
   - `.git/hooks/pre-commit` - Auto-scan on commit

## Claude Code Features

After installation, Claude Code will:
- Scan code on every commit
- Show active plan from `docs/plans/` on session start
- Show current task from `.claude/current-task.md`
- Auto-save state before context compaction
- Detect new commits and prompt to update tasks
