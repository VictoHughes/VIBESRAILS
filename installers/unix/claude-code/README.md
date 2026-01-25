# Claude Code Integration (Unix/Mac)

## Quick Start

```bash
cd your-project
/path/to/install.sh
```

Or with path:
```bash
./install.sh /path/to/your/project
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
ls -la vibesrails.yaml CLAUDE.md .claude/hooks.json
```

## Troubleshooting

### Pre-commit hook not running

```bash
chmod +x .git/hooks/pre-commit
```
