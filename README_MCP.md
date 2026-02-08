# VibesRails MCP Server

Security guardrails MCP server for AI-assisted development. From KIONOS (free tools).

## Installation

```bash
# Install with MCP support
pip install -e ".[mcp]"

# With Semgrep integration
pip install -e ".[mcp,semgrep]"
```

## Configuration (Claude Code)

Add to your Claude Code MCP settings (`~/.claude/mcp.json` or project `.mcp.json`):

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

## Tools (12)

| Tool | Description |
|------|-------------|
| `ping` | Health check - returns server status and version |
| `scan_code` | Run 16 AST security guards on Python code |
| `scan_senior` | Detect AI-specific issues: hallucinations, lazy code, bypass attempts |
| `check_session` | Detect if current session is AI-assisted |
| `scan_semgrep` | Run Semgrep vulnerability scan (requires semgrep extra) |
| `monitor_entropy` | Track AI coding session entropy and health |
| `check_config` | Scan AI config files for malicious content (Rules File Backdoor defense) |
| `deep_hallucination` | Multi-level import verification (slopsquatting detection) |
| `check_drift` | Measure architectural drift velocity between sessions |
| `enforce_brief` | Validate pre-generation briefs to reduce hallucinations |
| `shield_prompt` | Detect prompt injection in text, files, or MCP inputs |
| `get_learning` | Cross-session developer profiling with actionable insights |

## Usage Example

Once configured, Claude Code will have access to all tools. Example interactions:

```
> scan my code for security issues
  Claude calls scan_code(file_path="app.py")

> check if my AI config files are safe
  Claude calls check_config(project_path=".")

> validate my brief before generating code
  Claude calls enforce_brief(brief={"intent": "...", "constraints": [...]})

> show my developer profile
  Claude calls get_learning(action="profile")
```

## Architecture

- Transport: stdio (standard MCP protocol)
- Database: SQLite at `~/.vibesrails/sessions.db` (auto-created)
- Schema: V3 (5 core tables + 2 learning tables)
- All findings include pedagogical explanations (why, how_to_fix, prevention)
