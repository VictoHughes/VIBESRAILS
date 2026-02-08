# Plan: MCP Server Migration

Date: 2026-02-07

## Semaine 1: Fondation

### J1 — Scaffold + Migrations
- [x] Archive v2.0.0 (done previously)
- [x] pip install mcp (already installed, v1.23.3)
- [x] Creer structure dossiers (tools/, core/, adapters/, storage/, pedagogy/, config/)
- [x] Creer storage/migrations.py (5 tables, idempotent)
- [x] Creer mcp_server.py (FastMCP, stdio, ping tool, lifespan migrate)
- [x] Creer tests (20 tests: 7 server + 13 migrations)
- [x] Tous les tests passent (1144 = 1124 anciens + 20 nouveaux)
- [x] ruff clean (0 erreurs)
- [x] Coverage: migrations.py 97%, mcp_server.py 76%

### J2 — Migration Guards V2
- [x] Fix B4: PreDeployGuard.scan() — 3 lignes, 29 tests existants toujours OK
- [x] Creer tools/scan_code.py (wrapper MCP pour guards V2, 16 guards, pedagogy)
- [x] Enregistrer scan_code dans mcp_server.py
- [x] Tests scan_code: 26 tests, 95% coverage sur scan_code.py
- [x] Tous les tests passent: 1170 (1124 + 20 scaffold + 26 scan_code)
- [x] ruff clean

### J3 — Senior Guards + Guardian
- [x] Creer tools/scan_senior.py (wrapper MCP, 5 file-based guards, pedagogy)
- [x] Copier ai_guardian.py -> core/guardian.py (import path: vibesrails.scanner)
- [x] Creer tools/check_session.py (detection AI session, guardian stats, pedagogy)
- [x] Enregistrer scan_senior + check_session dans mcp_server.py (4 tools total)
- [x] Tests: 32 scan_senior + 12 check_session = 44 nouveaux tests
- [x] Tous les tests passent: 1214 (1170 + 44 nouveaux)
- [x] ruff clean
- [x] Coverage: scan_senior.py 92%, check_session.py 100%

### J4-J5 — Semgrep + Integration
- [x] Copier semgrep_adapter.py -> adapters/ (copie exacte, 0 modifs)
- [x] Creer tools/scan_semgrep.py (wrapper MCP, auto/custom rules, pedagogy par categorie CWE)
- [x] Enregistrer scan_semgrep dans mcp_server.py (5 tools total)
- [x] Tests scan_semgrep: 24 tests (5 classify, 4 convert, 4 status, 1 error, 2 not-installed, 6 live, 2 mocked findings)
- [x] Tests integration: 10 tests (3 registration, 5 format consistency, 2 combined scan)
- [x] Tous les tests passent: 1248 (1214 + 24 semgrep + 10 integration)
- [x] ruff clean
- [x] Coverage: scan_semgrep.py 95%, semgrep_adapter.py 61%
- [x] MCP server: 5 tools (ping, scan_code, scan_senior, check_session, scan_semgrep)

## SEMAINE 1 TERMINÉE

## Semaine 2: Concepts Uniques

### Concept 1 — Session Entropy Monitor
- [x] Creer core/session_tracker.py (SessionTracker, calculate_entropy, classify_entropy)
- [x] Creer tools/monitor_entropy.py (4 actions: start/update/status/end, pedagogy contextuelle)
- [x] Enregistrer monitor_entropy dans mcp_server.py (6 tools total)
- [x] Tests session_tracker: 28 tests (7 entropy, 4 classify, 7 lifecycle, 3 time-mocked, 4 errors, 2 multi-session, 1 persistence)
- [x] Tests monitor_entropy: 16 tests (4 start, 3 update, 3 status, 2 end, 1 invalid, 3 pedagogy)
- [x] Integration tests mis a jour: 6 tools, + test lifecycle monitor_entropy
- [x] Tous les tests passent: 1293 (1248 + 28 session_tracker + 16 monitor_entropy + 1 integration)
- [x] ruff clean
- [x] Coverage: session_tracker.py 99%, monitor_entropy.py 93%

### Concept 2 — AI Config Shield
- [x] Creer core/config_shield.py (ConfigShield, ConfigFinding dataclass, 4 checks)
- [x] Creer tools/check_config.py (wrapper MCP, pedagogy par check_type, _NO_FILES_PEDAGOGY)
- [x] Enregistrer check_config dans mcp_server.py (7 tools total)
- [x] Tests config_shield: 38 tests (8 invisible_unicode, 7 contradictory, 5 exfiltration, 7 security_overrides, 2 scan_content, 9 find_config_files)
- [x] Tests check_config: 13 tests (5 malicious, 1 no_files, 2 clean, 2 errors, 2 structure, 1 pedagogy)
- [x] Integration tests mis a jour: 7 tools, tool count + names
- [x] Tous les tests passent: 1344 (1293 + 38 config_shield + 13 check_config)
- [x] ruff clean
- [x] 4 checks: invisible_unicode, contradictory, exfiltration, security_override
- [x] 10 AI config patterns: .cursorrules, .cursor/rules/*.mdc, CLAUDE.md, mcp.json, etc.

### Concept 3 — Deep Hallucination Analysis
- [x] Creer core/hallucination_deep.py (DeepHallucinationChecker, 4 niveaux, cache SQLite)
- [x] Creer tools/deep_hallucination.py (wrapper MCP, AST import parser, pedagogy par niveau)
- [x] Enregistrer deep_hallucination dans mcp_server.py (8 tools total)
- [x] Tests hallucination_deep: 21 tests (6 level1, 6 level2, 3 level3, 4 level4, 2 cache)
- [x] Tests deep_hallucination: 14 tests (3 valid, 3 hallucinated, 4 max_level, 2 errors, 2 structure)
- [x] Integration tests mis a jour: 8 tools, tool count + names
- [x] Tous les tests passent: 1379 (1344 + 21 core + 14 tool)
- [x] ruff clean
- [x] 4 niveaux: import_exists, package_registry (PyPI+bloom+slopsquatting), symbol_exists, version_compat
- [x] Cache TTL: 24h existence, 7j api_surface (table package_cache)

### Concept 4 — Drift Velocity Index
- [x] Creer core/drift_tracker.py (DriftTracker, AST metrics, velocity calculation)
- [x] Creer tools/check_drift.py (wrapper MCP, pedagogy par velocity level)
- [x] Enregistrer check_drift dans mcp_server.py (9 tools total)
- [x] Tests drift_tracker: 26 tests (6 analyze_file, 3 complexity, 3 aggregate, 3 classify, 3 snapshot, 4 velocity, 1 trend, 2 consecutive)
- [x] Tests check_drift: 10 tests (2 baseline, 3 velocity, 2 pedagogy, 2 errors, 1 structure)
- [x] Integration tests mis a jour: 9 tools, tool count + names
- [x] Tous les tests passent: 1415 (1379 + 26 drift_tracker + 10 check_drift)
- [x] ruff clean
- [x] Seuils: normal 0-5%, warning 5-15%, critical 15%+
- [x] Trend: accelerating/stable/decelerating (±2% threshold)
- [x] review_required flag: 3+ consecutive sessions >10%

### Concept 5 — Pre-Generation Discipline (enforce_brief)
- [x] Ajouter migration V2: table brief_history + index session_id (storage/migrations.py)
- [x] Creer core/brief_enforcer.py (BriefEnforcer, validate_brief, score_quality, suggest_improvement, history)
- [x] Creer tools/enforce_brief.py (wrapper MCP, strict/normal mode, pedagogy par niveau)
- [x] Enregistrer enforce_brief dans mcp_server.py (10 tools total)
- [x] Tests brief_enforcer: 23 tests (4 classify, 5 validate, 8 score_quality, 3 suggest, 3 history)
- [x] Tests enforce_brief: 12 tests (2 strong, 2 weak, 2 insufficient, 1 pedagogy, 2 suggestions, 2 session, 1 structure)
- [x] Tests migrations_v2: 6 tests (table, idempotent, index, version, columns, v1 tables preserved)
- [x] Mise a jour test_migrations.py: EXPECTED_TABLES + brief_history, version dynamic
- [x] Integration tests mis a jour: 10 tools
- [x] Tous les tests passent: 1456 (1415 + 23 brief_enforcer + 12 enforce_brief + 6 migrations_v2)
- [x] ruff clean
- [x] Score 0-100: required (intent/constraints/affects) * 20 + optional (tradeoffs/rollback/dependencies) * 13.33
- [x] Niveaux: insufficient (0-39), minimal (40-59), adequate (60-79), strong (80-100)
- [x] Vague detection: regex patterns ("fix it", "make it work", "do the thing", etc.)

### Concept 6 — Prompt Shield
- [x] Creer core/prompt_shield.py (PromptShield, 5 categories, scan_text/scan_file/scan_mcp_input)
- [x] Creer tools/shield_prompt.py (wrapper MCP, pedagogy par categorie, text/file/mcp_input modes)
- [x] Enregistrer shield_prompt dans mcp_server.py (11 tools total)
- [x] Tests prompt_shield: 37 tests (6 system_override, 4 role_hijack, 3 exfiltration, 5 encoding_evasion, 5 delimiter_escape, 3 false_positive, 2 scan_file, 4 scan_mcp_input, 5 extract_strings)
- [x] Tests shield_prompt: 15 tests (2 clean, 5 injection, 2 mcp_input, 2 error, 2 pedagogy, 2 structure)
- [x] Integration tests mis a jour: 11 tools
- [x] Tous les tests passent: 1508 (1456 + 37 prompt_shield + 15 shield_prompt)
- [x] ruff clean
- [x] 5 categories: system_override, role_hijack, exfiltration, encoding_evasion, delimiter_escape
- [x] Base64 encoded injection detection (decode + match against injection patterns)
- [x] False positive avoidance: "ignore the error" does NOT trigger

### Concept 7 — Learning Engine (Cross-Session Profiling)
- [x] Ajouter migration V3: tables learning_events + developer_profile + index (storage/migrations.py)
- [x] Creer core/learning_engine.py (LearningEngine, record_event, get_profile, get_insights, get_session_summary)
- [x] Creer tools/get_learning.py (wrapper MCP, 4 actions: profile/insights/session_summary/record)
- [x] Enregistrer get_learning dans mcp_server.py (12 tools total)
- [x] Tests migrations_v3: 8 tests (2 tables, idempotent, index, version, 2 columns, v1+v2 preserved)
- [x] Tests learning_engine: 26 tests (4 record, 3 profile, 3 avg_brief, 2 top_violations, 2 halluc_rate, 3 improvement_rate, 5 insights, 3 session_summary, 1 drift_areas)
- [x] Tests get_learning: 14 tests (3 profile, 3 insights, 2 session_summary, 4 record, 1 invalid, 1 structure)
- [x] Mise a jour test_migrations.py: EXPECTED_TABLES + learning_events + developer_profile
- [x] Mise a jour test_migrations_v2.py: version >= 2 (dynamic)
- [x] Integration tests mis a jour: 12 tools
- [x] Tous les tests passent: 1556 (1508 + 8 migrations_v3 + 26 learning_engine + 14 get_learning)
- [x] ruff clean
- [x] Schema V3: learning_events + developer_profile (additive, V1+V2 intactes)
- [x] SQL aggregations: AVG, COUNT, GROUP BY, ORDER BY (pas de bulk Python)
- [x] improvement_rate: fenetre glissante 5 sessions recentes vs 5 precedentes
- [x] 6 event_types: violation, brief_score, drift, hallucination, config_issue, injection

### Learning Engine Wiring
- [x] Creer core/learning_bridge.py (get_engine singleton + record_safe fire-and-forget)
- [x] Wirer scan_code → violation events (per finding, guard_name + severity)
- [x] Wirer scan_senior → violation events (per finding, guard_name + severity)
- [x] Wirer scan_semgrep → violation events (per finding, rule_id as guard_name)
- [x] Wirer check_config → config_issue events (per finding, check_type + severity)
- [x] Wirer deep_hallucination → hallucination events (per hallucinated module)
- [x] Wirer check_drift → drift events (velocity + highest_metric, session_id passthrough)
- [x] Wirer enforce_brief → brief_score events (score, session_id passthrough)
- [x] Wirer shield_prompt → injection events (per finding, category)
- [x] Tests learning_bridge: 9 tests (3 get_engine, 5 record_safe, 1 reset)
- [x] Tests learning_wiring: 12 tests (mock record_safe dans chaque tool, verifie event_type/data)
- [x] Tests full_workflow: 4 tests (e2e sans mock: tool → bridge → engine → profile)
- [x] Tous les tests passent: 1581 (1556 + 9 bridge + 12 wiring + 4 workflow)
- [x] ruff clean
- [x] check_session et monitor_entropy: non wires (pas d'event_type correspondant)

### E2E Tests + Packaging
- [x] Tests E2E realistes: 4 scenarios (disciplined, chaotic, improvement, config_attack)
- [x] Scenario 1: workflow developeur discipline — brief fort, code clean, 0 violations
- [x] Scenario 2: workflow developeur chaotique — brief vague, violations, hallucinations, injections
- [x] Scenario 3: amelioration progressive — 10 sessions, improvement_rate positif
- [x] Scenario 4: config file attack — Unicode invisible + injection dans .cursorrules
- [x] Packaging MCP: pyproject.toml mis a jour, entry point vibesrails-mcp
- [x] main() ajoutee dans mcp_server.py
- [x] README_MCP.md (installation, config Claude Code, 12 tools documentes)
- [x] install_test.sh (pip install -e + verification entry point)
- [x] pip install -e ".[mcp]" OK, vibesrails-mcp entry point fonctionnel
- [x] Tous les tests passent: 1585 (1581 + 4 E2E)
- [x] ruff clean

## Semaine 2-4 (suite)
Voir docs/VIBESRAILS_MCP_MIGRATION_SPEC.md sections 6.

## Notes
- MCP SDK v1.23.3 installe
- FastMCP lifespan pattern confirme pour migrate() au startup
- Seul fichier existant modifie: guards_v2/pre_deploy.py (fix B4 — 3 lignes ajoutees)
- Les 1124 tests existants passent toujours
- Piege pytest tmp_path: dossier nomme test_<nom>0/, matche **/test_* dans fnmatch des guards
- scan_code accepte file_path (filtre par nom) ou project_path (scan tout)
- 16 guards, chacun avec pedagogy {why, how_to_fix, prevention}
- scan_senior: 5 file-based guards (error_handling, hallucination, lazy_code, bypass, resilience)
- core/guardian.py: copie exacte de ai_guardian.py, seul changement: from .scanner -> from vibesrails.scanner
- check_session: detection via env vars (AI_ENV_MARKERS), pedagogy conditionnelle (ai_detected/no_ai_detected)
- MCP server: 5 tools enregistres (ping, scan_code, scan_senior, check_session, scan_semgrep)
- scan_semgrep: pedagogy classifiee par categorie (security/secrets/correctness/performance)
- Semgrep 1.149.0 installe, tests live + mocked pour "not installed"
- adapters/semgrep_adapter.py: copie exacte de vibesrails/semgrep_adapter.py (backward compat preservee)
- Integration tests: verifient 7 tools, format coherent, scan combine sans crash
- Session Entropy Monitor: formule 4 facteurs (duration*0.3 + files*0.2 + violations*0.3 + loc*0.2)
- Seuils: safe [0-0.3], warning [0.3-0.6], elevated [0.6-0.8], critical [0.8-1.0]
- Pedagogy contextuelle: warning cite "88% hallucination" stat, critical dit "STOP"
- SessionTracker persiste dans SQLite (table sessions deja creee en S1-J1)
- Tests time-mocked: datetime.now patche pour verifier calculs entropy exacts
- MCP server: 8 tools (ping, scan_code, scan_senior, check_session, scan_semgrep, monitor_entropy, check_config, deep_hallucination)
- Config Shield: 4 checks (invisible_unicode, contradictory, exfiltration, security_override)
- 10 AI config patterns scanned (Cursor, Claude, Copilot, MCP, Continue, Windsurf, Cline)
- ConfigFinding dataclass: check_type, severity, message, file, line, matched_text
- Pedagogy par check_type: why, how_to_fix, prevention
- MCP server: 9 tools (+ check_drift)
- Deep Hallucination: 4 niveaux (import local, registre PyPI, symbol API, version compat)
- Slopsquatting detection: difflib.get_close_matches(cutoff=0.75) sur packages connus
- Cache SQLite: table package_cache (TTL 24h existence, 7j api_surface)
- Bloom filter offline: ~/.vibesrails/packages/{ecosystem}.bloom (fallback si absent)
- PyPI API: urllib.request.urlopen, timeout 3s, pas de retry
- Level 4 gere stdlib (pas de metadata) via importlib.import_module fallback
- Pedagogy en francais par defaut (L1-L4), slopsquatting = warning specifique
- Drift Velocity: mesure la VITESSE de derive, pas juste la derive
- AST metrics: import_count, class_count, function_count, dependency_count, complexity_avg, public_api_surface
- Cyclomatic complexity via AST visitor simple (if/for/while/except/with/BoolOp), pas de radon
- Velocity = moyenne ponderee des % de changement par metrique
- Consecutive high counter: 3+ sessions >10% → review_required
- Trend via comparaison velocity[n] vs velocity[n-1] (±2% = stable)
- MCP server: 10 tools (+ enforce_brief)
- Migration V2: table brief_history + index idx_brief_history_session (additive, V1 intacte)
- SCHEMA_VERSION passe de 1 a 2 — tests mis a jour (EXPECTED_TABLES, version dynamique)
- BriefEnforcer: score deterministe, required * 20 + optional * 13.33
- Vague detection: regex patterns (fix it, make it work, idk, whatever, etc.)
- Bonus scoring: action verbs, file references, technical terms
- History: brief_json stocke dans SQLite, filtrable par session_id
- Strict mode: block < 60 vs normal mode: block < 20, warn < 60
