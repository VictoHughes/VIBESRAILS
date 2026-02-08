# Changelog

All notable changes to the VibesRails MCP Server will be documented in this file.

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
