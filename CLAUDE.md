# VibesRails - Development Guidelines

> VibesRails 2.1.5 — by SM

## Project Overview

VibesRails is a security guardrails platform for AI-assisted Python development. It combines a YAML-driven CLI scanner (17 patterns, 16 AST guards, 8 senior guards), an MCP server (12 tools with pedagogy and learning engine), and a 4-layer hook system that protects Claude Code sessions in real-time.

**Key numbers:** 1875 tests | 12 MCP tools | 16 V2 guards | 7 AI agents detected | 4-layer hooks

## Setup

```bash
pip install -e ".[dev,mcp]"        # Dev + MCP server
pip install -e ".[all,mcp]"        # Everything (watch, audit, typing, deadcode, semgrep)
python -m pytest -v --timeout=60   # Verify install
```

Requires Python >=3.10. Config: `vibesrails.yaml` (auto-generated via `vibesrails --setup`).

## Architecture

```
vibesrails/                  # CLI package (scanner, guards, hooks, senior mode, learner)
├── cli.py + cli_v2.py       # CLI entry point (40+ commands)
├── scanner.py               # Regex scanner (17 patterns)
├── ai_guardian.py            # AI session detection (7 agents)
├── guards_v2/               # 16 AST guards (complexity, dead code, perf, etc.)
├── senior_mode/              # 8 senior guards (hallucination, bypass, lazy code, etc.)
├── hooks/                   # 4-layer protection system
│   ├── pre_tool_use.py      # BLOCKS before Write/Edit/Bash (secrets, SQL, eval)
│   ├── post_tool_use.py     # WARNS after write (full scan, non-blocking)
│   ├── throttle.py          # Anti-runaway (max 5 writes before check)
│   └── session_lock.py      # Concurrent session protection
├── learner/                 # Pattern detection & signature indexing (experimental)
├── community/               # Pack manager (install/remove GitHub packs)
├── advisors/                # Upgrade advisor (PyPI check)
├── autofix.py               # Auto-correction of simple patterns
└── watch.py                 # Live scan on file save (watchdog)

core/                        # MCP server logic
├── guardian.py              # AI session detection (for MCP)
├── hallucination_deep.py    # 4-level import verification + slopsquatting
├── prompt_shield.py         # Prompt injection detection (5 categories)
├── config_shield.py         # AI config file scanning
├── brief_enforcer.py        # Pre-generation brief validation
├── drift_tracker.py         # Architecture drift velocity
├── session_tracker.py       # Session entropy scoring (0-1)
├── learning_engine.py       # Cross-session learning (SQLite)
├── learning_bridge.py       # Fire-and-forget bridge to learning engine
├── rate_limiter.py          # 60 calls/min per tool
├── input_validator.py       # Anti-injection input validation
├── path_validator.py        # Anti-traversal path validation
└── logger.py                # MCP logging (stderr only, never stdout)

tools/                       # 12 MCP tool implementations
adapters/                    # External integrations (semgrep)
storage/                     # SQLite persistence + migrations (V1→V2→V3)
mcp_server.py                # MCP entry point (FastMCP, stdio transport)
mcp_tools.py                 # 6 tools (scan_code, scan_senior, scan_semgrep, etc.)
mcp_tools_ext.py             # 6 tools (enforce_brief, shield_prompt, etc.)
```

### Entry Points

| Command | Module | Purpose |
|---------|--------|---------|
| `vibesrails` | `vibesrails.cli:main` | CLI scanner |
| `vibesrails-mcp` | `mcp_server:main` | MCP server (stdio) |

### Module Dependencies (enforced by import-linter)

```
scanner.py    → (no deps on cli, smart_setup, guardian)
config.py     → (no deps on cli)
guardian.py   → (no deps on cli, smart_setup, learner, ai_guardian)
cli.py        → can import all
smart_setup.py → can import all
```

## Behavior Standards

<investigate_before_answering>
ALWAYS read and understand relevant files before proposing edits. Never speculate about code you have not opened. If a file is referenced, you MUST read it first. Never claim something works without running the test. Give grounded, hallucination-free answers only.
</investigate_before_answering>

<no_lazy_work>
Never take shortcuts. Never skip tests. Never produce incomplete implementations. Never say "I'll leave that as an exercise" or "you can add more later." Every piece of code you write must be complete, tested, and production-ready. If you are unsure about something, say "I don't know" rather than guessing. Uncertainty is acceptable; hallucination is not.
</no_lazy_work>

<scope_discipline>
NEVER modify code without explicit user permission.
A diagnostic is NOT permission to fix.
"Audit" means document findings — zero modifications.
"Fix X" means fix X only — nothing else.
If intent is unclear, ASK before acting.
Zero commits without explicit user validation.
If the user says "investigate" or "diagnose" or "audit",
you READ and REPORT. You do NOT write, edit, or commit.
</scope_discipline>

<anti_bypass>
Never disable, remove, skip, or work around vibesrails hooks, pre-commit hooks, or security checks. If vibesrails blocks your code, fix the code — do not bypass the guard. Never use --no-verify, never delete hook files, never modify .claude/hooks.json or vibesrails.yaml to weaken protections.
</anti_bypass>

## CLI Commands

### Core Scanning
```bash
vibesrails --all              # Scan all Python files
vibesrails --file <path>      # Scan specific file
vibesrails --senior           # Senior Mode (archi + guards + review)
vibesrails --senior-v2        # All 16 V2 guards (comprehensive)
vibesrails --show             # Show active patterns
vibesrails --stats            # Scan statistics
vibesrails --fixable          # Show auto-fixable patterns
```

### Auto-fix
```bash
vibesrails --fix              # Auto-fix simple patterns
vibesrails --fix --dry-run    # Preview corrections
```

### Specialized Guards (V2)
```bash
vibesrails --audit-deps       # CVE audit on dependencies
vibesrails --complexity       # Cyclomatic complexity analysis
vibesrails --dead-code        # Unused code detection
vibesrails --env-check        # Environment variable safety
vibesrails --test-integrity   # Detect fake/lazy tests
vibesrails --mutation         # Mutation testing (full)
vibesrails --mutation-quick   # Mutation testing (changed functions only)
vibesrails --pr-check         # PR review checklist
vibesrails --pre-deploy       # Pre-deployment verification
```

### Setup & Config
```bash
vibesrails --setup            # Smart auto-setup (analyzes project)
vibesrails --init             # Initialize vibesrails.yaml
vibesrails --hook             # Install git pre-commit hook
vibesrails --validate         # Validate YAML config
vibesrails --uninstall        # Remove from project
```

### Session & Community
```bash
vibesrails --watch            # Live scanning on file save
vibesrails --queue <msg>      # Send task to other Claude sessions
vibesrails --inbox <msg>      # Add instruction to mobile inbox
vibesrails --guardian-stats   # AI coding block statistics
vibesrails --install-pack @u/r # Install community pack
vibesrails --upgrade          # Check dependency upgrades
vibesrails --learn            # Claude-powered pattern discovery
vibesrails --version          # Show version
```

## MCP Server (12 Tools)

| Tool | Description | Learning |
|------|-------------|----------|
| `ping` | Health check | — |
| `scan_code` | AST scan (16 V2 guards) | Wired |
| `scan_senior` | AI-specific guards (hallucination, bypass, lazy code) | Wired |
| `scan_semgrep` | Semgrep static analysis (security, secrets) | Wired |
| `deep_hallucination` | Import verification (4 levels + slopsquatting) | Wired |
| `monitor_entropy` | Session health scoring (0.0-1.0) | — |
| `check_drift` | Architecture drift velocity | Wired |
| `enforce_brief` | Pre-generation brief validation | Wired |
| `shield_prompt` | Prompt injection detection (5 categories) | Wired |
| `check_config` | AI config file scanning (.cursorrules, CLAUDE.md) | Wired |
| `check_session` | AI session detection (7 agents) | — |
| `get_learning` | Cross-session profiling & insights | Manual |

All tools include pedagogy (why, how_to_fix, prevention). 8/12 auto-feed the learning engine.

## Security Hooks (4-layer protection)

| Layer | Hook | Behavior |
|-------|------|----------|
| 1 | **PreToolUse** (`pre_tool_use.py`) | BLOCKS Write/Edit/Bash: secrets, SQL injection, eval/exec, file size |
| 2 | **PostToolUse** (`post_tool_use.py`) | WARNS after write: full V1+V2+Senior scan (non-blocking) |
| 3 | **Pre-commit** (git hook) | BLOCKS commits with issues (install via `--hook`) |
| 4 | **Throttle** (`throttle.py`) | Anti-runaway: max 5 writes before requiring verification |

Self-protection: the `<anti_bypass>` directive above prevents Claude from weakening hooks or config. If a hook blocks you: **fix the code, never bypass.**

## Testing (MANDATORY)

Coverage minimum: 80%. Always use `--timeout=60`.

```bash
# CLI package only
pytest tests/ --cov=vibesrails --cov-report=term --timeout=60

# Full coverage (CLI + MCP)
pytest tests/ --cov=vibesrails --cov=tools --cov=core --cov-report=term --timeout=60

# With minimum threshold
pytest tests/ --cov=vibesrails --cov-fail-under=80 --timeout=60
```

Use `--cov-report=term` (NOT `term-missing` — too slow). pyproject.toml default timeout=30.

Naming: `tests/test_<module>.py`, functions: `test_<function>_<scenario>`

## Code Quality

Run before every commit:
```bash
ruff check vibesrails/ --fix
bandit -r vibesrails/ -ll
vibesrails --all
```

## Commit Standards

Pre-commit checklist:
1. Tests + coverage pass at 80%
2. Lint clean (`ruff check`)
3. `vibesrails --all` clean
4. No secrets in code

Format: `type(scope): description` — types: feat, fix, refactor, test, docs, chore, style

## Gotchas

- **NEVER `cd` in Bash tool** — if the target dir is deleted, ALL subsequent Bash calls fail. Use absolute paths everywhere: `git -C /path init` not `cd /path && git init`
- **ruff I001** — import ordering error, happens on every new file. Fix: `ruff check --fix`
- **pytest tmp_path** — dirs named `test_<name>0/` match `**/test_*` in fnmatch guards, causing false positives
- **MCP logs on stderr** — MCP protocol uses stdout for JSON-RPC. All logging MUST go to stderr
- **Test fixtures with "eval"/"exec"** — strings containing these trigger PreToolUse Write hook. Rephrase or use `# vibesrails: ignore`
- **Coverage module path** — use `--cov=tools` not `--cov=tools/scan_code` (module not file)
- **f-strings with Unicode escapes** — `\u200B`, `\U000E0041` flagged F541 by ruff. Use plain strings
- **regex.search()** — only finds FIRST match per line. Use `finditer()` for multiple matches on same line
- **Migration version** — when adding new migration, update SCHEMA_VERSION AND existing test assertions
- **DB location** — `~/.vibesrails/sessions.db` (SQLite, schema V3)

## Session Continuity

Les todos en mémoire ne survivent pas aux crashes. Toujours persister dans des fichiers.

**Workflow obligatoire :**
1. **Début de session** → écrire/relire le plan dans `docs/plans/YYYY-MM-DD-<sujet>.md`
2. **Pendant le travail** → cocher les étapes terminées dans le fichier plan
3. **Nouvelle session / crash** → relire `docs/plans/` pour reprendre

Le fichier dans `docs/plans/` est la source de vérité (pas les todos en mémoire).

## Project Tree

Maintenir `docs/PROJECT_TREE.md` à jour avant chaque commit/push et en fin de session.

```bash
tree -I '__pycache__|*.pyc|.git|*.egg-info|node_modules|.ruff_cache|dist|build|.pytest_cache' --dirsfirst > docs/PROJECT_TREE.md
```
