# vibesrails 2.0

<a href="https://buymeacoffee.com/vibesrails" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40">
</a>

**Scale up your vibe coding - safely.** From KIONOS.

Code fast, ship faster. vibesrails catches security issues, logic bugs, and architecture violations automatically so you can focus on building.

## Philosophy

Vibe coding = flow state, rapid iteration, creative momentum.

vibesrails **protects your flow** with 3 layers of defense:
- **V1** - Regex scanner: secrets, injection, unsafe patterns (instant)
- **V2** - 16 AST guards: dead code, complexity, performance, type safety, architecture drift (fast)
- **Senior Mode** - 8 AI-specific guards: diff size, hallucination, lazy code, bypass detection (thorough)

Zero config to start. Single YAML to customize. Works with Claude Code.

**You code. vibesrails watches your back.**

## Quick Start

```bash
pip install git+https://github.com/VictoHughes/VIBESRAILS.git
cd your-project
vibesrails --setup
```

`--setup` detects your project, generates config, installs hooks, wires Claude Code integration. Done.

## Usage

```bash
# Core
vibesrails              # Scan staged files (pre-commit)
vibesrails --all        # Scan entire project
vibesrails --show       # See what's configured
vibesrails --fix        # Auto-fix simple issues

# Setup
vibesrails --init       # Create vibesrails.yaml
vibesrails --hook       # Install git pre-commit hook
vibesrails --setup      # Smart auto-setup (recommended)
vibesrails --validate   # Validate YAML config

# V2 Guards (AST-based)
vibesrails --senior-v2  # Run all 16 V2 guards
vibesrails --dead-code  # Detect unused code
vibesrails --complexity # Analyze code complexity
vibesrails --env-check  # Check environment safety
vibesrails --audit-deps # Audit dependencies for CVEs
vibesrails --mutation   # Mutation testing
vibesrails --pr-check   # PR checklist validation
vibesrails --pre-deploy # Pre-deploy checks
vibesrails --test-integrity  # Test quality analysis

# Senior Mode
vibesrails --senior     # Run all 8 Senior guards

# Monitoring
vibesrails --watch      # Live scanning on file save
vibesrails --stats      # Scan statistics
vibesrails --learn      # AI-powered pattern discovery
```

## How It Works

```
                    vibesrails 2.0 — 3-Layer Protection
                    ===================================

Layer 1: V1 Regex Scanner (vibesrails.yaml)
  git commit --> pre-commit hook --> regex scan --> block/warn

Layer 2: V2 AST Guards (16 guards)
  Write/Edit --> PostToolUse hook --> AST analysis --> warn
  SessionStart --> session_scan --> full project audit

Layer 3: Senior Mode (8 guards)
  Write/Edit --> PostToolUse hook --> AI-specific checks --> warn
  git commit --> PostToolUse Bash --> post-commit guards --> warn
```

## V2 Guards (AST-based)

| Guard | What it catches |
|-------|----------------|
| DeadCode | Unused imports, variables, functions |
| Observability | Missing logging, error tracking |
| Complexity | Cyclomatic complexity > threshold |
| Performance | N+1 queries, unnecessary copies, blocking I/O |
| TypeSafety | Missing type hints, unsafe casts |
| APIDesign | Inconsistent API patterns |
| DatabaseSafety | Raw SQL, missing transactions, N+1 |
| EnvSafety | Hardcoded config, missing env validation |
| ArchitectureDrift | Layer violations (domain importing infra) |
| TestIntegrity | Weak assertions, test smells |
| Mutation | Dead code via mutation testing |
| DependencyAudit | CVEs, outdated packages, license risks |
| Docstring | Missing or outdated docstrings |
| GitWorkflow | Branch naming, commit message quality |
| PRChecklist | PR completeness checks |
| PreDeploy | Production readiness validation |

## Senior Mode Guards (AI-specific)

| Guard | What it catches |
|-------|----------------|
| DiffSize | Oversized commits (> 400 lines) |
| ErrorHandling | Bare except, swallowed errors |
| Hallucination | Imports/calls to nonexistent modules |
| Dependency | Undeclared or unused dependencies |
| TestCoverage | Modified code without test updates |
| LazyCode | TODO/FIXME, pass, placeholder code |
| Bypass | Attempts to disable security (--no-verify) |
| Resilience | Missing retry, timeout, circuit breaker |

## Claude Code Integration

### Automatic Hooks (4-layer protection)

| Hook | When | What |
|------|------|------|
| **SessionStart** | Open Claude Code | Full project scan (V2 + Senior), shows blocking/warnings |
| **PreToolUse** | Before Write/Edit/Bash | Blocks secrets, injection, eval/exec |
| **PostToolUse** (Write/Edit) | After file changes | V1 regex + 8 V2 guards + 5 Senior guards per file |
| **PostToolUse** (Bash) | After git commit | DiffSize + TestCoverage + ArchitectureDrift |
| **PreCompact** | Before compaction | Auto-saves task state |
| **Pre-commit** | git commit | Full V1 scan, blocks issues |

### Self-Protection (ptuh.py)

Prevents AI from:
- Deleting or modifying hooks/config
- Using `--no-verify` to skip checks
- Uninstalling vibesrails
- Altering CI workflows

### Setup

```bash
vibesrails --setup   # Installs everything: yaml, hooks, CLAUDE.md, pre-commit
```

Or manual:
```bash
mkdir -p ~/.claude/hooks
cp installers/claude-code/hooks/ptuh.py ~/.claude/hooks/ptuh.py
```

## Configuration

One file: `vibesrails.yaml`

```yaml
version: "1.0"

blocking:
  - id: hardcoded_secret
    name: "Hardcoded Secret"
    regex: "(password|api_key)\\s*=\\s*[\"'][^\"']{4,}"
    flags: "i"
    message: "Move to environment variables"

warning:
  - id: star_import
    name: "Star Import"
    regex: "from\\s+\\S+\\s+import\\s+\\*"
    message: "Consider explicit imports"
    skip_in_tests: true

exceptions:
  test_files:
    patterns: ["test_*.py"]
    allowed: ["hardcoded_secret"]
    reason: "Tests can mock secrets"
```

## Architecture

```
vibesrails/
├── scanner.py           # V1 regex engine
├── guards_v2/           # 16 AST-based guards
│   ├── dead_code.py
│   ├── complexity.py
│   ├── performance.py
│   ├── type_safety.py
│   ├── database_safety.py
│   ├── env_safety.py
│   ├── architecture_drift.py
│   └── ... (16 total)
├── senior/              # 8 AI-specific guards
│   ├── diff_size.py
│   ├── hallucination.py
│   ├── test_coverage.py
│   └── ... (8 total)
├── hooks/               # Claude Code hook handlers
│   ├── pre_tool_use.py  # PreToolUse handler
│   ├── post_tool_use.py # PostToolUse handler (V1+V2+Senior)
│   ├── session_scan.py  # SessionStart full project scan
│   ├── session_lock.py  # Multi-session conflict detection
│   ├── throttle.py      # Write throttling
│   └── ptuh.py          # Self-protection
├── cli.py               # CLI interface
└── vibesrails.yaml      # Config (per project)
```

## Why "vibesrails"?

- **Vibe** = coding in flow, fast iteration
- **Rails** = safety guardrails that keep you on track

Not restrictions. **Freedom with protection.**

## Support

VibesRails is free and open source. If it helps you ship safer code, consider supporting:

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://buymeacoffee.com/vibesrails)

Star this repo - it helps others discover vibesrails.

## License

MIT - Use it, fork it, improve it.

---

**Ship fast. Ship safe.**
