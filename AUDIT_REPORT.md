# AUDIT REPORT - VibesRails 2.0.0

**Date**: 2026-02-07
**Auditeur**: Claude Opus 4.6
**Scope**: Audit complet de toutes les features du projet
**Methode**: Lecture exhaustive du code, execution des tests, analyse statique (ruff, bandit, vibesrails --all)

---

## SCORE GLOBAL DE SANTE: 6.5 / 10

| Dimension | Score | Commentaire |
|-----------|-------|-------------|
| Tests (1124 pass, 81% cov) | 7/10 | Bon globalement, mais 5 modules critiques sous 55% |
| Architecture | 8/10 | Propre, modulaire, guards V2 bien concu |
| CLI | 4/10 | 13% coverage, bugs de controle, double entry-points |
| Hooks | 5/10 | Fonctionnent en production, mais 0% coverage mesure |
| Securite code | 7/10 | Bandit propre (0 high), Semgrep warnings urllib |
| Documentation | 6/10 | CLAUDE.md excellent, config YAML divergente |
| Lint | 9/10 | 1 seule erreur ruff (import sort) |
| Features completude | 6/10 | Tout fonctionne, mais 2 features dormantes |

---

## RESULTATS DES OUTILS

```
pytest:         1124 passed, 0 failed, 81% coverage (seuil: 80%)
ruff:           1 erreur (import sort dans post_tool_use.py)
bandit:         0 high, 3 medium (urllib.urlopen - acceptable)
vibesrails:     0 BLOCKING, 30 WARNINGS (fichiers >300 lignes, TODOs)
```

---

## BUGS BLOQUANTS (8) — Empechent l'utilisation fiable

### B1. CLI quasi non teste (13% / 10% coverage)

**Fichiers**: `cli.py` (13%), `cli_v2.py` (10%)
**Probleme**: `test_cli.py` teste en realite `cli_setup.py`. Les vrais entry-points CLI (argparse, dispatch, orchestration) ne sont JAMAIS testes.
**Fonctions non testees**: `_parse_args()`, `_handle_info_commands()`, `_handle_setup_commands()`, `_handle_hook_commands()`, `main()`, `dispatch_v2_commands()`
**Impact**: Toute regression dans le CLI passe inapercue.
**Fix**: Ecrire 30-40 tests pour cli.py et cli_v2.py (target 80%).

---

### B2. Bug de controle CLI — execution continue apres erreur

**Fichier**: `cli.py:172-178`, `cli_v2.py:250-255`
**Probleme**: `dispatch_v2_commands()` retourne TOUJOURS `False` (jamais `True` malgre la docstring). Les sous-fonctions font `sys.exit()` directement. Si une guard plante SANS exit, l'execution continue et tente un scan sans config → crash.
**Impact**: Crash silencieux possible en production.
**Fix**: Unifier le pattern de controle (soit return bool partout, soit sys.exit partout).

---

### B3. Double handling de la commande `learn`

**Fichier**: `cli.py:206-207` et `cli.py:137-139`
**Probleme**: `vibesrails learn` (positional) appelle `handle_learn_command()` (structure learning). `vibesrails --learn` (flag) appelle `run_learn_mode()` (Claude AI). Deux fonctions DIFFERENTES pour ce qui semble etre la meme feature.
**Impact**: Confusion utilisateur, comportement imprevisible.
**Fix**: Unifier en un seul entry-point ou documenter clairement la difference.

---

### B4. PreDeployGuard.scan() manquant — casse run_all_guards()

**Fichier**: `guards_v2/pre_deploy.py`
**Probleme**: PreDeployGuard a `run_all()` mais PAS `scan()`. Or `run_all_guards()` dans `__init__.py` appelle `guard.scan(project_root)` pour TOUS les guards → `AttributeError` sur PreDeployGuard.
**Impact**: `run_all_guards()` crash. Toute feature qui l'appelle est cassee.
**Fix**: Ajouter `def scan(self, project_root): return self.run_all(project_root)` (3 lignes).

---

### B5. session_scan.py — hook critique avec ZERO tests

**Fichier**: `hooks/session_scan.py` (87 lignes, 0% coverage)
**Probleme**: Le hook SessionStart (full project scan au demarrage) n'a AUCUN test automatique. Il fonctionne en production (verifie live), mais si on le casse, on ne le saura que manuellement.
**Impact**: Regression silencieuse possible sur le hook le plus visible.
**Fix**: Creer `tests/test_hooks/test_session_scan.py` avec 8-10 tests.

---

### B6. learn_runner.py — 23% coverage

**Fichier**: `learn_runner.py` (61 lignes, 23% coverage)
**Probleme**: Feature exposee via CLI (`vibesrails learn`) mais quasi non testee. `handle_learn_command()` et `_build_signature_index()` n'ont aucun test.
**Impact**: Structure learning probablement dormant et fragile.
**Fix**: Ajouter 15-20 tests (target 80%).

---

### B7. metrics.py — 53% coverage, zero tests dedies

**Fichier**: `metrics.py` (208 lignes, 53% coverage)
**Probleme**: `MetricsCollector` est UTILISE en production (`track_scan()` appele par scan_runner), expose via CLI (`--stats`), mais n'a AUCUN test dedie. Coverage 53% vient de tests indirects.
**Impact**: Silent failures possibles (ecriture echouee, stats incorrects).
**Fix**: Ajouter 10-15 tests pour MetricsCollector.

---

### B8. default.yaml diverge de vibesrails.yaml

**Fichiers**: `config/default.yaml` (139 lignes) vs `vibesrails.yaml` (177 lignes)
**Probleme**: `vibesrails --init` genere une config basee sur `default.yaml` qui est OBSOLETE. Il manque des patterns recents (command_injection), guardian senior_mode est "off" au lieu de "auto".
**Impact**: Nouveaux utilisateurs n'ont pas les dernieres protections.
**Fix**: Synchroniser default.yaml avec vibesrails.yaml.

---

## BUGS IMPORTANTS (10) — Degradent l'experience

### I1. scanner.py depasse la limite de taille (506 lignes, max 300)

**Impact**: Difficile a maintenir, vibesrails --all le signale comme warning.
**Fix**: Extraire scanner_utils.py, pattern_utils.py, display.py (~200 lignes a sortir).

---

### I2. Validation config fragile — crash sur config=None

**Fichier**: `scanner.py:391`
**Probleme**: `validate_config(config)` crash avec `AttributeError` si `config` est `None` (YAML vide). Regex invalide detectee mais execution continue quand meme.
**Fix**: Ajouter `if config is None: return False` + `sys.exit(1)` sur regex invalide.

---

### I3. Code duplique — _get_cached_diff vs _get_staged_diff

**Fichiers**: `cli_setup.py:92` et `cli_v2.py:40`
**Probleme**: Meme fonction (git diff --cached), implementations divergentes. cli_v2 a timeout + error handling, cli_setup non.
**Fix**: Unifier dans un seul module.

---

### I4. Hooks 0% coverage — faux negatif trompeur

**Fichiers**: `pre_tool_use.py` (0%), `post_tool_use.py` (0%)
**Probleme**: 20 tests passent (16 + 4) mais coverage.py ne les voit pas car tests via subprocess. Le coverage report ment.
**Fix**: Documenter dans pyproject.toml ou reecrire tests avec imports directs.

---

### I5. session_lock.py — race conditions potentielles

**Fichier**: `hooks/session_lock.py`
**Probleme**: `check_other_session()` + `acquire_lock()` ne sont pas atomiques. Entre check et acquire, un autre process peut prendre le lock.
**Fix**: Ajouter test multiprocessing concurrent.

---

### I6. semgrep_adapter.py — 54% coverage

**Fichier**: `semgrep_adapter.py` (192 lignes)
**Probleme**: `install()` success path, timeout handling, retry logic non testes.
**Fix**: Ajouter tests subprocess avec mocks (target 80%).

---

### I7. Pack manager sans verification de signature

**Fichier**: `community/pack_manager.py`
**Probleme**: Telecharge des YAML depuis GitHub sans checksum ni GPG signature. Un compromis GitHub → YAML malicieux (patterns ReDoS).
**Fix**: Ajouter verification checksum ou pack signing.

---

### I8. Packs officiels incomplets — 2 sur 5 manquent

**Fichier**: `community/pack_manager.py` OFFICIAL_REGISTRY
**Probleme**: `@vibesrails/python-quality` et `@vibesrails/docker` declares dans le registry mais absents de `vibesrails/packs/`. Installation → 404.
**Fix**: Creer les packs ou les retirer du registry.

---

### I9. Regex patterns incomplets — secrets non detectes

**Fichier**: `vibesrails.yaml`
**Probleme**: Pas de detection pour AWS_SECRET_ACCESS_KEY, STRIPE_SECRET_KEY (sk_live_), GITHUB_TOKEN (ghp_), OpenAI (sk-). SQL concat (`execute(...+...`) non detecte.
**Fix**: Ajouter 3-5 patterns supplementaires.

---

### I10. Crash paths non geres — modules optionnels

**Fichier**: `cli.py`
**Probleme**: `--learn` sans `anthropic`, `--watch` sans `watchdog`, `--audit-deps` sans `pip-audit` → `ImportError` brute au lieu d'un message clair.
**Fix**: try/except ImportError avec message user-friendly.

---

## BUGS MINEURS (7) — Cosmetiques

### M1. Naming confusion: cli_v2.py devrait s'appeler guards_dispatcher.py

### M2. Docstrings mensongeres: dispatch_v2_commands() dit "Returns True" mais retourne toujours False

### M3. Helper modules non prefixes par underscore (architecture_bypass.py, mutation_engine.py, etc.)

### M4. Dead code: wrappers _levenshtein() et _normalize_pkg_name() dans dependency_audit.py jamais appeles

### M5. Re-exports inutiles: semgrep_integration.py et e2e_semgrep.py (7 lignes chacun, juste des imports)

### M6. ruff: 1 erreur import sort dans post_tool_use.py

### M7. GUARD_COUNT variable morte dans guards_v2/__init__.py (jamais utilisee)

---

## VERDICT

### Ce projet EST PRET pour:

- **Usage personnel / equipe interne** — Le scanner fonctionne, les hooks protegent, les guards V2 detectent de vrais problemes. L'experience utilisateur est correcte.
- **Demo / showcase** — Les features annoncees (Semgrep, mutation testing, AI learning, community packs) existent REELLEMENT. Ce n'est pas du vaporware.
- **Integration Claude Code** — Les hooks PreToolUse/PostToolUse/SessionStart fonctionnent en production (verifie live).

### Ce projet N'EST PAS PRET pour:

- **Release publique / open-source** — 5 modules critiques sous 55% coverage. Le CLI principal a 13% de tests. `run_all_guards()` crash sur PreDeployGuard. Config par defaut obsolete.
- **Enterprise / production critique** — Pack manager sans signature, session_lock avec race conditions, crash paths non geres.
- **Maintenance par un tiers** — Architecture CLI confuse (3 fichiers, patterns mixtes), learn system en double, scanner.py surdimensionne.

---

## PRE-REQUIS AVANT TOUT PIVOT MCP

Avant de transformer VibesRails en MCP server, ces 5 items sont NON NEGOCIABLES:

| # | Item | Effort | Priorite |
|---|------|--------|----------|
| 1 | Fixer PreDeployGuard.scan() | 5 min | P0 |
| 2 | Tests CLI (cli.py + cli_v2.py → 80%) | 4h | P0 |
| 3 | Tests hooks (session_scan.py) | 2h | P0 |
| 4 | Tests metrics.py + learn_runner.py | 3h | P0 |
| 5 | Sync default.yaml | 30 min | P1 |

**Total estime: ~10h de travail de tests/fixes avant d'etre production-ready.**

Les features sont LA. Le code est REEL. Ce qui manque, c'est la couverture de tests pour garantir que ca ne casse pas quand on refactore pour MCP.

---

*Rapport genere par Claude Opus 4.6 — Aucun menagement, chiffres concrets, zero encouragement gratuit.*
