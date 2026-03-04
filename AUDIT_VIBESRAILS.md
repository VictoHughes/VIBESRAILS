# AUDIT VIBESRAILS — Rapport Complet

> Audit technique — 4 mars 2026
> Version: 2.1.5 | Tests: 1875/1875 PASS | Python 3.12.8

---

## 1. Structure du Projet (Tree Commenté)

```
vibesrails/                          # 258 fichiers, 29 répertoires
├── adapters/                        # Adapteurs externes
│   └── semgrep_adapter.py           # ⚠ DUPLIQUÉ (voir vibesrails/semgrep_adapter.py)
├── core/                            # Moteur MCP — logique métier serveur
│   ├── brief_enforcer.py            # Validation briefs pré-génération (scoring 0-100)
│   ├── brief_enforcer_patterns.py   # Patterns de validation des briefs
│   ├── config_shield.py             # Scan configs AI (.cursorrules, CLAUDE.md) pour injections
│   ├── drift_metrics.py             # Métriques de dérive architecturale
│   ├── drift_tracker.py             # Suivi vélocité de dérive entre snapshots
│   ├── guardian.py                  # Détection session AI (7 agents supportés)
│   ├── hallucination_deep.py        # Vérification imports hallucinated (4 niveaux + slopsquatting)
│   ├── hallucination_registry.py    # Registre des hallucinations connues
│   ├── input_validator.py           # Validation inputs MCP (anti-injection)
│   ├── learning_bridge.py           # Pont fire-and-forget vers learning engine
│   ├── learning_engine.py           # Moteur d'apprentissage cross-session
│   ├── learning_profile.py          # Profiling développeur
│   ├── logger.py                    # Logging MCP (stderr, pas stdout)
│   ├── path_validator.py            # Validation chemins (anti-traversal)
│   ├── prompt_shield.py             # Détection prompt injection (5 catégories)
│   ├── prompt_shield_patterns.py    # Patterns de détection injection
│   ├── rate_limiter.py              # Rate limiting 60 calls/min par tool
│   ├── secret_patterns.py           # Patterns de détection secrets
│   └── session_tracker.py           # Suivi entropie session (scoring 0-1)
├── docs/                            # Documentation
│   ├── METRICS.md                   # Guide métriques
│   ├── PROJECT_TREE.md              # Arbre projet (auto-généré)
│   ├── RATE_LIMITING.md             # Doc rate limiting
│   ├── SEMGREP_INTEGRATION.md       # Doc intégration Semgrep
│   ├── SENIOR_MODE.md               # Doc Senior Mode
│   └── VIBESRAILS_GUIDE.md          # Guide utilisateur
├── storage/                         # Persistence SQLite
│   └── migrations.py                # Migrations DB (V1→V2→V3)
├── tests/                           # Suite de tests (1875 tests)
│   ├── test_advisors/               # Tests upgrade advisor
│   ├── test_community/              # Tests pack manager
│   ├── test_core/                   # Tests moteur MCP (12 fichiers)
│   ├── test_guards_v2/              # Tests 16 guards V2 (16 fichiers)
│   ├── test_hooks/                  # Tests hooks (7 fichiers)
│   ├── test_integration/            # Tests E2E + MCP (4 fichiers)
│   ├── test_security/               # Tests sécurité (10 fichiers)
│   ├── test_storage/                # Tests migrations (3 fichiers)
│   ├── test_tools/                  # Tests 12 outils MCP (12 fichiers)
│   └── *.py                         # Tests CLI, scanner, guardian, etc. (27 fichiers)
├── tools/                           # Implémentations outils MCP
│   ├── scan_code.py                 # Scan AST (16 guards V2)
│   ├── scan_senior.py               # Scan Senior Mode (5 guards)
│   ├── scan_semgrep.py              # Scan Semgrep (sécurité, secrets)
│   ├── deep_hallucination.py        # Vérification imports (4 niveaux)
│   ├── monitor_entropy.py           # Entropie session (start/update/status/end)
│   ├── check_drift.py               # Vélocité dérive architecturale
│   ├── enforce_brief.py             # Validation briefs pré-génération
│   ├── shield_prompt.py             # Détection prompt injection
│   ├── check_config.py              # Scan configs AI malveillantes
│   ├── check_session.py             # Détection session AI
│   ├── get_learning.py              # Profiling & insights développeur
│   ├── scan_code_pedagogy.py        # Pédagogie scan_code
│   └── deep_hallucination_pedagogy.py # Pédagogie deep_hallucination
├── vibesrails/                      # Package CLI principal
│   ├── advisors/                    # Conseiller de mise à jour
│   │   └── upgrade_advisor.py       # Check outdated deps via PyPI
│   ├── claude_integration/          # Intégration Claude Code
│   │   ├── skills/                  # Skills Claude Code (3 fichiers .md)
│   │   ├── hooks.json               # Config hooks Claude
│   │   └── CLAUDE.md.template       # Template CLAUDE.md
│   ├── community/                   # Packs communautaires
│   │   └── pack_manager.py          # Install/remove packs GitHub
│   ├── config/
│   │   └── default.yaml             # Config par défaut (17 patterns)
│   ├── guardian/                     # Guardian Mode (dialogue, duplication, placement)
│   │   ├── dialogue.py              # Dialogue interactif avec l'utilisateur
│   │   ├── duplication_guard.py     # Détection code dupliqué
│   │   ├── placement_guard.py       # Vérification placement code
│   │   └── types.py                 # Types Guardian
│   ├── guards_v2/                   # 16 guards AST avancés
│   │   ├── api_design.py            # Cohérence API
│   │   ├── architecture_bypass.py   # Détection contournements archi
│   │   ├── architecture_drift.py    # Dérive architecturale
│   │   ├── complexity.py            # Complexité cyclomatique
│   │   ├── database_safety.py       # Sécurité SQL/ORM
│   │   ├── dead_code.py             # Code mort
│   │   ├── dependency_audit.py      # Audit dépendances CVE
│   │   ├── docstring.py             # Standards documentation
│   │   ├── env_safety.py            # Sécurité variables env
│   │   ├── git_workflow.py          # Conventions git
│   │   ├── mutation.py              # Tests mutation
│   │   ├── observability.py         # Logging/tracing
│   │   ├── performance.py           # N+1, fuites mémoire
│   │   ├── pr_checklist.py          # Checklist PR
│   │   ├── pre_deploy.py            # Vérification pré-déploiement
│   │   ├── test_integrity.py        # Détection faux tests
│   │   └── type_safety.py           # Annotations types
│   ├── hooks/                       # Système hooks 4 couches
│   │   ├── pre_tool_use.py          # BLOC avant écriture (secrets, SQL, eval)
│   │   ├── post_tool_use.py         # WARN après écriture (scan complet)
│   │   ├── session_lock.py          # Verrou session
│   │   ├── session_scan.py          # Scan session
│   │   ├── queue_processor.py       # Queue inter-sessions
│   │   ├── inbox.py                 # Inbox mobile
│   │   └── throttle.py              # Anti-emballement (5 writes max)
│   ├── learner/                     # Apprentissage automatique
│   │   ├── pattern_detector.py      # Détection patterns projet
│   │   ├── signature_index.py       # Index signatures AST
│   │   └── structure_rules.py       # Règles structure projet
│   ├── packs/                       # Packs intégrés (django, fastapi, security, web)
│   ├── senior_mode/                 # Mode Senior (8 guards)
│   │   ├── guards.py                # 8 guards (diff, errors, tests, resilience, etc.)
│   │   ├── guards_analysis.py       # Patterns d'analyse
│   │   ├── architecture_mapper.py   # Cartographie architecture
│   │   ├── claude_reviewer.py       # Review via Claude API
│   │   └── report.py                # Rapport Senior Mode
│   ├── smart_setup/                 # Setup automatique projet
│   ├── cli.py                       # CLI principal (40+ commandes)
│   ├── cli_v2.py                    # CLI étendu (guards V2)
│   ├── scanner.py                   # Scanner regex (17 patterns)
│   ├── ai_guardian.py               # Détection AI + Guardian Mode
│   ├── autofix.py                   # Auto-correction patterns simples
│   ├── watch.py                     # Mode watch (live scan)
│   └── ...                          # 15 autres modules support
├── mcp_server.py                    # Point d'entrée MCP (FastMCP, stdio)
├── mcp_tools.py                     # 6 outils MCP (scan, entropy, hallucination, drift)
├── mcp_tools_ext.py                 # 6 outils MCP (brief, prompt, config, session, learning, ping)
├── pyproject.toml                   # Config build/deps/tools
├── vibesrails.yaml                  # Config projet locale
└── Makefile                         # Raccourcis make
```

---

## 2. Inventaire Features

### 2.1 Outils MCP (12 tools)

| # | Tool | Description | Learning | Pédagogie | Statut |
|---|------|------------|----------|-----------|--------|
| 1 | `ping` | Health check serveur | — | Simple | OK |
| 2 | `scan_code` | Scan AST (16 guards V2) | Wired | Riche | OK |
| 3 | `scan_senior` | Scan Senior Mode (5 guards AI) | Wired | Riche | OK |
| 4 | `scan_semgrep` | Semgrep (sécurité, secrets, qualité) | Wired | Riche | OK |
| 5 | `deep_hallucination` | Vérif imports (4 niveaux + slopsquatting) | Wired | Riche | OK |
| 6 | `monitor_entropy` | Entropie session (0.0-1.0) | Non wired | Riche | OK |
| 7 | `check_drift` | Vélocité dérive architecturale | Wired | Riche | OK |
| 8 | `enforce_brief` | Validation briefs pré-génération | Wired | Riche | OK |
| 9 | `shield_prompt` | Détection prompt injection (5 cat.) | Wired | Riche | OK |
| 10 | `check_config` | Scan configs AI malveillantes | Wired | Riche | OK |
| 11 | `check_session` | Détection session AI (7 agents) | Non wired | Simple | OK |
| 12 | `get_learning` | Profiling & insights cross-session | Manuel | Riche | OK |

**Wiring Learning Bridge:** 8/10 auto-wired + 1 manuel + 2 non wired (by design)

### 2.2 Commandes CLI (40+)

| Catégorie | Commande | Description |
|-----------|----------|-------------|
| **Scan** | `--all` | Scan tous les fichiers Python |
| | `--file, -f` | Scan fichier spécifique |
| | `--senior` | Senior Mode (archi + guards + review) |
| | `--senior-v2` | Tous les guards V2 |
| | `--show` | Affiche patterns actifs |
| | `--stats` | Statistiques de scan |
| | `--fixable` | Patterns auto-fixables |
| **Setup** | `--init` | Initialise vibesrails.yaml |
| | `--setup` | Smart auto-setup (analyse projet) |
| | `--hook` | Installe pre-commit hook |
| | `--uninstall` | Supprime vibesrails du projet |
| | `--validate` | Valide config YAML |
| **Fix** | `--fix` | Auto-fix patterns simples |
| | `--dry-run` | Preview des corrections |
| **Guards V2** | `--audit-deps` | Audit CVE dépendances |
| | `--complexity` | Complexité cyclomatique |
| | `--dead-code` | Code mort |
| | `--env-check` | Sécurité env vars |
| | `--test-integrity` | Détection faux tests |
| | `--mutation` | Tests mutation |
| | `--pr-check` | Checklist PR |
| | `--pre-deploy` | Vérif pré-déploiement |
| **Community** | `--install-pack` | Installer pack GitHub |
| | `--remove-pack` | Supprimer pack |
| | `--list-packs` | Lister packs |
| **Session** | `--watch` | Live scan (watchdog) |
| | `--queue` | Queue inter-sessions |
| | `--inbox` | Inbox mobile |
| | `--throttle-status` | Compteur throttle |
| | `--guardian-stats` | Stats Guardian Mode |
| **Info** | `--version` | Version |
| | `--about` | À propos (hidden) |

### 2.3 Guardian Mode — Agents Détectés

| Variable Env | Agent | Statut |
|-------------|-------|--------|
| `CLAUDE_CODE` | Claude Code CLI | Détecté |
| `CURSOR_SESSION` | Cursor IDE | Détecté |
| `COPILOT_AGENT` | GitHub Copilot | Détecté |
| `AIDER_SESSION` | Aider | Détecté |
| `CONTINUE_SESSION` | Continue.dev | Détecté |
| `CODY_SESSION` | Sourcegraph Cody | Détecté |
| `VIBESRAILS_AGENT_MODE` | Override manuel | Détecté |
| `TERM_PROGRAM=claude-code` | Claude Code (alt) | Détecté |

**Config Guardian (vibesrails.yaml):**
- `guardian.enabled`: true
- `guardian.auto_detect`: true
- `guardian.senior_mode`: "off" / "auto" / "always"
- `guardian.warnings_as_blocking`: false
- `guardian.max_file_lines`: 300

### 2.4 Senior Mode (8 Guards)

| Guard | Type | Sévérité |
|-------|------|----------|
| DiffSizeGuard | Taille commits | WARN/BLOCK (>100/200 lignes) |
| ErrorHandlingGuard | except bare/pass | WARN |
| TestCoverageGuard | Ratio tests/code | WARN (<0.3) |
| ResilienceGuard | Timeouts manquants | WARN |
| HallucinationGuard | Imports inexistants | BLOCK |
| LazyCodeGuard | Placeholders (pass, ...) | WARN/BLOCK |
| BypassGuard | noqa, type: ignore | BLOCK |
| DependencyGuard | Nouvelles deps | WARN |

### 2.5 Guards V2 (16 Guards AST)

| Guard | Fichier | Scope |
|-------|---------|-------|
| DependencyAuditGuard | dependency_audit.py | Projet |
| PerformanceGuard | performance.py | Fichier |
| ComplexityGuard | complexity.py | Fichier |
| EnvSafetyGuard | env_safety.py | Projet |
| GitWorkflowGuard | git_workflow.py | Projet |
| DeadCodeGuard | dead_code.py | Projet |
| ObservabilityGuard | observability.py | Fichier |
| TypeSafetyGuard | type_safety.py | Fichier |
| DocstringGuard | docstring.py | Fichier |
| PRChecklistGuard | pr_checklist.py | Projet |
| DatabaseSafetyGuard | database_safety.py | Fichier |
| APIDesignGuard | api_design.py | Fichier |
| PreDeployGuard | pre_deploy.py | Projet |
| TestIntegrityGuard | test_integrity.py | Projet |
| MutationGuard | mutation.py | Projet |
| ArchitectureDriftGuard | architecture_drift.py | Projet |

### 2.6 Scanner Patterns (17 patterns par défaut)

| Catégorie | Pattern | Sévérité |
|-----------|---------|----------|
| **Blocking** | hardcoded_secret | BLOCK |
| | sql_injection | BLOCK |
| | shell_injection | BLOCK |
| | unsafe_yaml | BLOCK |
| | unsafe_numpy | BLOCK |
| **Warning** | star_import | WARN |
| | none_comparison | WARN |
| | bare_except | WARN |
| **Bugs** | mutable_default | BLOCK |
| | assert_in_prod | WARN |
| **Architecture** | dip_domain_infra | BLOCK |
| | dip_domain_application | BLOCK |
| **Maintainability** | print_debug | WARN |
| | file_too_long | WARN (>300 lignes) |

### 2.7 Système Hooks (4 couches)

| Couche | Hook | Comportement |
|--------|------|-------------|
| 1 | **PreToolUse** | BLOQUE avant Write/Edit/Bash (secrets, SQL, eval, size) |
| 2 | **PostToolUse** | WARN après écriture (scan complet V1+V2+Senior) |
| 3 | **Pre-commit** | BLOQUE commits avec issues (installable via `--hook`) |
| 4 | **Throttle** | Anti-emballement (max 5 writes avant vérification) |

### 2.8 Intégration Semgrep

- **Méthode:** Subprocess → semgrep CLI → JSON parse
- **Presets:** auto, strict (`p/security-audit`), minimal (`p/secrets`)
- **Dégradation:** Gracieuse si non installé (message pédagogique)
- **Config:** `semgrep.enabled`, `semgrep.preset`, `semgrep.additional_rules`

### 2.9 Autres Features

| Feature | Fichier | Statut |
|---------|---------|--------|
| Watch Mode (live scan) | watch.py | OK (watchdog) |
| Auto-fix | autofix.py | OK |
| Rate Limiting | rate_limiting.py | OK (60/min) |
| Logging MCP | core/logger.py | OK (stderr) |
| Config YAML | config.py | OK |
| Learning Engine | core/learning_engine.py | OK (SQLite) |
| Pack Manager | community/pack_manager.py | Partiel |
| Upgrade Advisor | advisors/upgrade_advisor.py | Partiel |
| Learner | learner/*.py | Partiel |

---

## 3. Résultats Tests

```
Platform: darwin — Python 3.12.8, pytest 9.0.2
Timeout: 60s (thread method)
Durée: 58.03s

═══════════════════════════════════
  1875 passed — 0 failed — 0 skipped
═══════════════════════════════════
```

### Répartition par module

| Répertoire | Fichiers | Tests (approx) |
|-----------|----------|-----------------|
| test_guards_v2/ | 16 | ~380 |
| test_core/ | 12 | ~290 |
| test_tools/ | 12 | ~200 |
| test_security/ | 10 | ~140 |
| test_hooks/ | 7 | ~75 |
| test_integration/ | 4 | ~35 |
| test_storage/ | 3 | ~27 |
| Racine tests/ | 27 | ~728 |
| **Total** | **91** | **1875** |

---

## 4. Dépendances

### Core (obligatoire)

| Package | Version | Rôle |
|---------|---------|------|
| pyyaml | >=6.0 | Parsing config YAML |

### Optionnelles

| Groupe | Package | Version | Rôle |
|--------|---------|---------|------|
| `[watch]` | watchdog | >=3.0 | Live file monitoring |
| `[claude]` | anthropic | >=0.18 | Claude API (reviewer) |
| `[audit]` | pip-audit | >=2.6 | Audit CVE dépendances |
| `[typing]` | mypy | >=1.0 | Type checking |
| `[deadcode]` | vulture | >=2.7 | Détection code mort |
| `[mcp]` | mcp[cli] | >=1.0.0 | Serveur MCP |
| `[semgrep]` | semgrep | >=1.45.0 | Static analysis |

### Dev

| Package | Version | Rôle |
|---------|---------|------|
| pytest | >=7.0 | Tests |
| pytest-timeout | >=2.0 | Timeout tests |
| pytest-cov | >=4.0 | Coverage |
| ruff | >=0.1 | Linter |
| import-linter | >=2.0 | Architecture enforcement |

### Build

| Package | Version |
|---------|---------|
| setuptools | >=61.0 |
| wheel | (latest) |

---

## 5. Gaps Identifiés

### Tableau des Gaps

| # | Gap | Sévérité | Effort | Fichier(s) |
|---|-----|----------|--------|-----------|
| 1 | **Semgrep adapter dupliqué** — `adapters/semgrep_adapter.py` identique à `vibesrails/semgrep_adapter.py` | CRITIQUE | 1h | 2 fichiers |
| 2 | **Module learner incomplet** — pattern_detector limité (2 patterns), signature_index sans async, structure_rules stub-like, pas d'intégration CLI | HAUTE | 2-3j | learner/*.py |
| 3 | **Pack manager sans sécurité** — pas de versionning, pas de signature/checksum, pas de résolution conflits | HAUTE | 2j | community/pack_manager.py |
| 4 | **Upgrade advisor isolé** — pas intégré dans PreDeployGuard, pas dans cli.py principal, pas de scan transitif | HAUTE | 1j | advisors/upgrade_advisor.py |
| 5 | **Tests manquants pour modules helper** — architecture_bypass.py, mutation_engine.py, mutation_visitors.py, pre_deploy_checks.py, dependency_audit_checks.py, 4 fichiers _helper sans tests unitaires dédiés | MOYENNE | 2j | guards_v2/ (8 fichiers) |
| 6 | **Imports typing dépréciés** — `from typing import List, Optional, Dict, Tuple` dans 4 fichiers (cassera en Python 3.13) | MOYENNE | 30min | 4 fichiers |
| 7 | **Fichiers tests géants** — test_smart_setup (2123 lig.), test_scanner (1775), test_cli (1046), test_config (961) | MOYENNE | 1j | 4 fichiers tests |
| 8 | **Exception catches trop larges** — `except Exception: pass` dans hooks/post_tool_use.py (5x), pre_tool_use.py (2x), dependency_audit_checks.py, signature_index.py | MOYENNE | 2h | 4 fichiers |
| 9 | **monitor_entropy et check_session non wired** au learning engine (pas de event_type correspondant) | BASSE | 1h | 2 tools |
| 10 | **SignatureIndexer.find_similar()** skip exact matches (comportement contre-intuitif) | BASSE | 15min | signature_index.py |
| 11 | **_find_parent_class() O(n²)** — ast.walk() imbriqué inefficace | BASSE | 30min | signature_index.py |
| 12 | **ObservabilityGuard skip patterns trop larges** — `test_*` matche aussi les répertoires | BASSE | 15min | observability.py |
| 13 | **Nommage modules incohérent** — mutation.py/mutation_engine.py/mutation_mutmut.py/mutation_visitors.py (4 fichiers pour 1 feature) | BASSE | 2h | guards_v2/ |
| 14 | **Seuils magiques non documentés** — 0.8/0.6 mock thresholds, 0.9/0.7 enforcement/observation | BASSE | 30min | 3 fichiers |
| 15 | **tools_count hardcodé** dans mcp_server.py (doit être mis à jour manuellement) | BASSE | 15min | mcp_server.py |

### Aucun TODO/FIXME réel dans le code source

Tous les TODO/FIXME trouvés sont dans les tests (fixtures) ou dans les patterns de détection — le code source est propre.

---

## 6. Recommandations Prioritaires (Top 5)

### 1. Consolider le semgrep adapter dupliqué
**Impact:** CRITIQUE | **Effort:** 1h

Garder `adapters/semgrep_adapter.py` comme source unique, faire pointer `vibesrails/semgrep_adapter.py` vers un re-export. Mettre à jour les imports `List, Optional` → `list, T | None`.

### 2. Décider du sort du module learner
**Impact:** HAUTE | **Effort:** 2-3 jours

Trois options :
- **A)** Compléter et intégrer dans CLI (ajouter `vibesrails learn`, enrichir pattern_detector, connecter à structure_rules)
- **B)** Marquer comme expérimental et documenter les limitations
- **C)** Supprimer si non maintenu — réduit la surface de maintenance

### 3. Sécuriser le pack manager
**Impact:** HAUTE | **Effort:** 2 jours

- Ajouter versionning (tags Git au lieu de `main` hardcodé)
- Ajouter checksums pour vérification d'intégrité
- Ajouter détection de conflits entre packs
- Intégrer dans cli.py principal (actuellement cli_v2.py uniquement)

### 4. Ajouter tests unitaires pour les modules helper guards_v2
**Impact:** MOYENNE | **Effort:** 2 jours

8 modules sans tests dédiés : architecture_bypass, mutation_engine, mutation_visitors, pre_deploy_checks, dependency_audit_checks, _arch_layers, _env_patterns, _perf_patterns, _git_helpers. Couverts par tests d'intégration mais pas de régression unitaire.

### 5. Moderniser les imports typing + resserrer les exception handlers
**Impact:** MOYENNE | **Effort:** 1h

- Remplacer `from typing import List, Dict, Optional, Tuple` par types natifs dans les 4 fichiers identifiés
- Spécifier les exceptions dans les `except Exception` des hooks (FileNotFoundError, json.JSONDecodeError, etc.)

---

## Annexe: Métriques Clés

| Métrique | Valeur |
|----------|--------|
| Fichiers source (.py) | ~130 |
| Fichiers tests (.py) | ~91 |
| Total lignes source | ~17 270 |
| Total lignes tests | ~37 194 |
| Ratio tests/source | 2.15x |
| Tests | 1875 (100% pass) |
| Outils MCP | 12 (100% opérationnels) |
| Guards V2 | 16 |
| Senior Guards | 8 |
| Scanner Patterns | 17 |
| Agents AI détectés | 7 (+1 override) |
| Dépendance core | 1 (pyyaml) |
| Dépendances optionnelles | 7 groupes |
| Packs intégrés | 4 (django, fastapi, security, web) |
| Schema DB | V3 |
