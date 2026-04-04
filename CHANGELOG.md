# Changelog

All notable changes to VibesRails will be documented in this file.

## [2.4.0] - 2026-04-04

### Added
- `vibesrails --status [--quiet|--json]` — unified project status report
- `vibesrails --init-hooks [minimal|standard|full]` — tiered Claude Code hook generator
- `vibesrails --check-contracts` — public signature tracking between phases
- OpenSpec interop — detect `openspec/` directory, hard gates, preflight/status integration
- PEV enforcement — Plan→Execute→Verify loop tracking in hooks
- Auto-status injection on SessionStart via generated hooks
- Contract snapshots saved automatically on `--promote`
- Status trigger: periodic status report after 5 commits, 1h, or branch change

### Changed
- Repositioned: "engineering methodology enforcer" not "security scanner"
- README.md rewritten with phase flow diagram and comparison table
- Makefile: force venv Python in all targets (fixes pyenv conflicts)
- `--setup` now delegates to `--init-hooks --standard`
- All hook commands use `sys.executable` (no hardcoded python3)
- Tests: 2283 → 2418 (+135)

## [2.3.0] - 2026-03-06

### Added
- `vibesrails --sync-memory` — auto-generate PROJECT_MEMORY.md from runtime data
- PROJECT_MEMORY.md template with 6 auto-sections (health, drift, quality, flows, baselines, context)
- sync_memory.py module: AST flow analysis, SQLite DB queries, context detection integration

### Fixed
- Claude Code hooks: all python3 refs now use venv path (fixes pyenv conflict)
- subprocess calls use `sys.executable` instead of `"python"` (fixes venv/pyenv mismatch)
- Hooks template test: structural comparison instead of exact match (tolerates venv paths)

## [2.2.2] - 2026-03-05

### Fixed
- **Critical**: semgrep adapter import path broken in PyPI package (moved source to `vibesrails/adapters/`)
- Root `adapters/` re-exports from `vibesrails.adapters` for backward compatibility

## [2.2.1] - 2026-03-04

### Fixed
- Documentation fully synced with context detection features
- All doc freshness preflight checks passing

## [2.2.0] - 2026-03-04

### Added
- `vibesrails --preflight` — pre-session checklist (branch, uncommitted files, test baseline, assertions)
- `vibesrails --check-assertions` — validate project truths from vibesrails.yaml assertions section
- `vibesrails --sync-claude` — auto-generate CLAUDE.md sections from code introspection
- decisions.md template generated via `--init` and `--setup`
- fail_closed_allow mechanism in assertions (allowlist for intentional graceful degradation)
- Context detection: automatic R&D/Mixed/Bugfix session mode (`vibesrails/context/`)
- Context adapter: guards adjust thresholds dynamically per session mode
- `vibesrails --mode rnd|bugfix|auto` — manual session mode override
- Doc freshness checks in preflight (version consistency, test count, CLAUDE.md, changelog)
- `session_profiles` YAML key for custom threshold overrides per mode

### Fixed
- Consolidated duplicated semgrep adapter (single source of truth)
- Modernized typing imports (Python 3.12+ native types)
- Tightened exception handlers in hooks (specific catches + logging)
- Dynamic tools_count in MCP server (no more hardcoded value)
- ObservabilityGuard skip pattern (files only, not directories)
- SignatureIndexer O(1) parent lookup + configurable exact match
- Extracted 8 magic thresholds into named constants
- Reduced audit noise (semgrep FP exclusion, file_too_long threshold 400)

### Changed
- CLAUDE.md rewritten (55/100 → 94/100)
- Learner module marked as experimental (FutureWarning)
- Mutation files consolidated into mutation/ package
- Giant test files split into focused modules
- Upgrade advisor wired into CLI and PreDeployGuard
- Pack manager secured (SHA256 checksums, conflict detection, lockfile)
- monitor_entropy and check_session wired to learning engine

### Metrics
- Tests: 1875 → 2203 (+328)
- Audit findings: 15 gaps → 0

## [0.1.0] - 2026-02-08

### Added
- 12 MCP tools: ping, scan_code, scan_senior, check_session, scan_semgrep,
  monitor_entropy, check_config, deep_hallucination, check_drift, enforce_brief,
  shield_prompt, get_learning
- 4-level deep hallucination analysis with slopsquatting detection
- Session entropy monitoring with AI coding tool detection
- Architecture drift velocity tracking across sessions
- Pre-generation brief enforcement with scoring
- 5-category prompt injection shield (system_override, role_hijack,
  exfiltration, encoding_evasion, delimiter_escape)
- AI config file security scanner (Rules File Backdoor defense)
- Cross-session learning engine with developer profiling
- Structured JSON logging with sensitive data redaction
- Rate limiting (60 RPM/tool, 300 RPM global, token bucket)
- Filesystem sandbox (DENIED_ROOTS + configurable VIBESRAILS_ALLOWED_ROOTS)
- SQLite WAL mode with busy_timeout for concurrent access
- 1700+ tests including 96 security tests and 15 MCP protocol tests

### Security
- Path traversal protection with symlink rejection
- SQL injection protection (parameterized queries verified with 34 deep tests)
- ReDoS protection (all regex patterns verified < 1s with 100K adversarial input)
- Input validation on all tool arguments (strings, ints, dicts, lists, enums)
- Information disclosure prevention (base64 payload redaction, output truncation)
- Structured logging redacts user content, file paths, and code snippets
