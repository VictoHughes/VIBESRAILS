# Claude Code Integration (Cross-Platform)

## Quick Start

```bash
cd your-project
python /path/to/install.py
```

Or with path:
```bash
python install.py /path/to/your/project
```

## What it creates

| File | Purpose |
|------|---------|
| `vibesrails.yaml` | Security scanner config |
| `CLAUDE.md` | Claude Code instructions |
| `.claude/hooks.json` | Claude Code hooks |
| `.git/hooks/pre-commit` | Auto-scan on commit |

## Features

- Auto-scan on every commit
- Active plan display from `docs/plans/`
- Task tracking via `.claude/current-task.md`
- State preservation before compaction

## Verify

```bash
vibesrails --all
```
