# VibesRails

**Security guardrails for AI-assisted development.**

VibesRails is an MCP server that watches your back while you vibe code.
It detects AI hallucinations, enforces structured briefs, monitors
architecture drift, and blocks prompt injections — all integrated
into your AI coding workflow.

## Install

```bash
pip install vibesrails-mcp
# or from source:
git clone https://github.com/sm/vibesrails.git
cd vibesrails && pip install -e ".[mcp]"
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
| `scan_senior` | 5 senior guards (error handling, hallucination, lazy code...) |
| `scan_semgrep` | Semgrep integration with CWE classification |
| `check_session` | AI session detection (Cursor, Copilot, Claude) |
| `monitor_entropy` | Session entropy tracking with risk levels |
| `check_config` | AI config file attack detection (.cursorrules, CLAUDE.md) |
| `deep_hallucination` | 4-level import verification + slopsquatting detection |
| `check_drift` | Architecture drift velocity monitoring |
| `enforce_brief` | Pre-generation brief quality scoring |
| `shield_prompt` | 5-category prompt injection detection |
| `get_learning` | Cross-session developer profiling + insights |

## What makes VibesRails different

Other tools scan for bugs. VibesRails changes how you code.

- **Session Entropy** — knows when your AI session is getting chaotic
- **Brief Enforcement** — forces you to think before generating
- **Drift Velocity** — catches architecture erosion across sessions
- **Learning Engine** — builds your developer profile over time
- **Pedagogy** — teaches you WHY, not just WHAT

## Security

1729 tests including 96 security tests. Path traversal protection,
SQL injection prevention, ReDoS verification, filesystem sandbox,
rate limiting, structured logging with data redaction.

## License

Apache 2.0 — free for everyone.
