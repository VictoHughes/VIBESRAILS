# Claude Code Integration (Windows)

## Quick Start

```cmd
cd your-project
\path\to\install.bat
```

Or with path:
```cmd
install.bat C:\path\to\your\project
```

## What it creates

| File | Purpose |
|------|---------|
| `vibesrails.yaml` | Security scanner config |
| `CLAUDE.md` | Claude Code instructions |
| `.claude\hooks.json` | Claude Code hooks |
| `.git\hooks\pre-commit` | Auto-scan on commit |

## Features

- Auto-scan on every commit
- Active plan display from `docs\plans\`
- Task tracking via `.claude\current-task.md`
- State preservation before compaction

## Verify

```cmd
vibesrails --all
dir vibesrails.yaml CLAUDE.md .claude\hooks.json
```
