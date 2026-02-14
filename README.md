# VibesRails

**The open-source runtime guard for AI coding agents.**

Most security tools scan your code after it's written.
VibesRails intercepts before execution — secrets are blocked
before they touch your files.

![Tests](https://img.shields.io/badge/tests-1822_passing-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-Apache_2.0-orange)

## What makes it different

| Approach | When it acts | Examples |
|----------|-------------|----------|
| Static scanning | After code exists | Semgrep, Snyk, linters |
| Pre-install scanning | Before adding plugins | mcp-scan, Cisco Skill Scanner |
| **Runtime interception** | **Before each write/edit/command** | **VibesRails** |

VibesRails doesn't wait for you to commit bad code. It blocks it
before the file is written.

## 4-layer runtime protection

| Layer | Event | What it does |
|-------|-------|-------------|
| **PreToolUse** | Write/Edit/Bash | Blocks secrets, SQL injection, eval/exec BEFORE your AI writes them |
| **File Size Guard** | Write/Edit | Blocks files exceeding 300 lines (configurable via `guardian.max_file_lines`) |
| **PostToolUse** | Write/Edit | Auto-scans every .py file AFTER write (16 AST guards + 7 senior guards, 5s timeout) |
| **Throttle** | Write/Edit | Forces verification every 5 writes, prevents runaway agents |
| **Scope Guard** | Post-commit | Reminds rules after every commit, prevents scope creep |

## Works with

| Agent | Integration | Level |
|-------|------------|-------|
| Claude Code | Full hooks + MCP | Runtime guard |
| Cursor | MCP server | 12 security tools |
| GitHub Copilot | MCP server | 12 security tools |
| Windsurf | MCP server | 12 security tools |
| Continue.dev | MCP server | 12 security tools |
| Any MCP client | MCP server | 12 security tools |

## Install

> **Note:** PyPI publication pending. For now, install from source:
> ```bash
> git clone https://github.com/VictoHughes/VIBESRAILS.git
> cd VIBESRAILS
> pip install -e ".[mcp]"
> ```

### Quick install (after PyPI publish)

```bash
# pipx (isolated CLI — recommended)
pipx install vibesrails

# uv (fast, modern)
uv tool install vibesrails

# pip (classic)
pip install vibesrails
```

### MCP server (requires mcp extra)

```bash
pipx install vibesrails[mcp]
# or
pip install vibesrails[mcp]
```

### Developer setup (from source)

```bash
git clone https://github.com/VictoHughes/VIBESRAILS.git
cd VIBESRAILS
make install-dev   # installs dev + MCP dependencies
make test          # 1822 tests
```

## Configure (Claude Code)

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "vibesrails": {
      "command": "vibesrails-mcp",
      "args": []
    }
  }
}
```

## 12 Security Tools

| Tool | What it does |
|------|-------------|
| `ping` | Health check |
| `scan_code` | 16 AST guards (eval, hardcoded secrets, binding...) |
| `scan_senior` | 7 senior guards (error handling, hallucination, lazy code...) |
| `scan_semgrep` | Semgrep integration with CWE classification |
| `check_session` | AI session detection (Cursor, Copilot, Claude) |
| `monitor_entropy` | Session entropy tracking with risk levels |
| `check_config` | AI config file attack detection (.cursorrules, CLAUDE.md) |
| `deep_hallucination` | 4-level import verification + slopsquatting detection |
| `check_drift` | Architecture drift velocity monitoring |
| `enforce_brief` | Pre-generation brief quality scoring |
| `shield_prompt` | 5-category prompt injection detection |
| `get_learning` | Cross-session developer profiling + insights |

## What's Inside

**16 V2 Guards** --
dependency_audit, performance, complexity, env_safety, git_workflow,
dead_code, observability, type_safety, docstring, pr_checklist,
database_safety, api_design, pre_deploy, test_integrity, mutation,
architecture_drift.

**7 Senior Guards** --
diff_size, error_handling, hallucination, dependency, test_coverage,
lazy_code, bypass, resilience.

**22 Secret Patterns** --
AWS, OpenAI/Anthropic, Google, GitHub, GitLab, Stripe, SendGrid,
Slack, Telegram, Discord, Twilio, npm, PyPI, Supabase,
Bearer tokens, PEM keys, database URLs, hardcoded passwords.

**8 Hooks Pipeline** --
Pre-tool secrets scan, post-tool guard scan, write throttle, scope guard,
session lock, session scan, queue processor, mobile inbox.

**4 Built-in Config Packs** --
`@vibesrails/security-pack` (OWASP Top 10),
`@vibesrails/web-pack` (Flask/Django),
`@vibesrails/fastapi-pack`,
`@vibesrails/django-pack`.

**Learning Engine** --
Automatic developer profiling, session tracking, improvement metrics,
actionable insights, SQLite persistence across sessions.

## CLI Reference

| Category | Key Commands | Count |
|----------|-------------|-------|
| Setup & Config | `--init`, `--setup`, `--hook`, `--validate` | 7 |
| Scanning | `--all`, `--file`, `--senior`, `--senior-v2` | 7 |
| Auto-fix | `--fix`, `--dry-run`, `--no-backup` | 3 |
| Specialized Guards | `--audit-deps`, `--complexity`, `--mutation` | 9 |
| Community | `--install-pack`, `--learn`, `--upgrade` | 5 |
| Session Management | `--watch`, `--queue`, `--inbox` | 5 |
| Guardian | `--guardian-stats` | 1 |

Run `vibesrails --help` for full details.

## Security

1822 tests including 111 security tests. Path traversal protection,
SQL injection prevention, ReDoS verification, filesystem sandbox,
rate limiting, structured logging with data redaction.

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

Apache 2.0 — free for everyone.
