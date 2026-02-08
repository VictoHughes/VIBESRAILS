# VIBESRAILS MCP SERVER — SPÉCIFICATION OPÉRATOIRE COMPLÈTE

**Date**: 2026-02-07
**Auteur**: CTO Assistant (Claude Opus 4.6)
**Usage**: Document de référence pour Claude Code — chaque étape exécutable
**Version cible**: vibesrails-mcp v0.1.0

---

## TABLE DES MATIÈRES

1. [Inventaire complet de l'existant](#1-inventaire)
2. [Décision par composant: GARDER / JETER / TRANSFORMER](#2-decisions)
3. [Architecture cible MCP Server](#3-architecture)
4. [Mapping migration: ancien → nouveau](#4-mapping)
5. [6 concepts uniques — spécifications techniques](#5-concepts)
6. [Plan d'exécution semaine par semaine](#6-plan)
7. [Prompts Claude Code par étape](#7-prompts)

---

## 1. INVENTAIRE COMPLET DE L'EXISTANT {#1-inventaire}

### 1.1 Fichiers source (13,156 LOC)

| Fichier | LOC | Rôle | Coverage |
|---------|-----|------|----------|
| `cli.py` | ~350 | Entry-point CLI principal (argparse) | 13% |
| `cli_v2.py` | ~280 | Dispatcher guards V2 | 10% |
| `cli_setup.py` | ~150 | Setup hooks, init config | ~60% |
| `scanner.py` | 506 | Scanner V1 regex + orchestration | ~70% |
| `scan_runner.py` | ~120 | Orchestration scan | ~75% |
| `ai_guardian.py` | 262 | Détection sessions AI (env vars) | ~65% |
| `metrics.py` | 208 | MetricsCollector (SQLite) | 53% |
| `learn_runner.py` | 61 | Structure learning CLI | 23% |
| `semgrep_adapter.py` | 192 | Installation + exécution Semgrep | 54% |
| `config/default.yaml` | 139 | Config par défaut (OBSOLÈTE) | N/A |
| `vibesrails.yaml` | 177 | Config de référence | N/A |

### 1.2 Guards V2 — AST (24 modules, ~5,400 LOC)

| Module | LOC | Fonction | Unique? |
|--------|-----|----------|---------|
| `dead_code.py` | ~200 | Détection code mort | Non (vulture) |
| `complexity.py` | ~180 | Complexité cyclomatique | Non (radon) |
| `architecture_drift.py` | ~250 | Dérive architecture | **OUI** |
| `mutation_engine.py` | ~300 | Mutation testing | **OUI** |
| `test_integrity.py` | ~220 | Intégrité des tests | **OUI** |
| `env_repr_leak.py` | ~150 | Fuite __repr__ env | **OUI** |
| `pre_deploy.py` | ~180 | Check pré-déploiement | Partiel |
| `dependency_audit.py` | ~200 | Audit dépendances | Non (pip-audit) |
| `import_guard.py` | ~170 | Imports circulaires | Partiel |
| `type_safety.py` | ~160 | Vérification types | Non (mypy) |
| Autres (14 modules) | ~2,890 | Divers guards | Mixte |

### 1.3 Senior Guards (8 modules, ~765 LOC)

| Module | LOC | Fonction | Unique? |
|--------|-----|----------|---------|
| `hallucination_guard.py` | ~120 | Imports fantômes | **OUI** |
| `session_discipline.py` | ~100 | Discipline session | **OUI** |
| `brief_enforcement.py` | ~95 | Enforce brief avant code | **OUI** |
| `architecture_guard.py` | ~90 | Respect archi | **OUI** |
| `scope_guard.py` | ~85 | Limitation scope | **OUI** |
| `review_guard.py` | ~80 | Auto-review | **OUI** |
| `pattern_guard.py` | ~100 | Patterns interdits | Partiel |
| `quality_gate.py` | ~95 | Gate qualité | Partiel |

### 1.4 Hooks Claude Code (4 hooks, ~768 LOC)

| Hook | LOC | Trigger | Fonction |
|------|-----|---------|----------|
| `pre_tool_use.py` | ~200 | PreToolUse | Bloque fichiers dangereux avant écriture |
| `post_tool_use.py` | ~180 | PostToolUse | Scan après écriture |
| `session_scan.py` | 87 | SessionStart | Full scan au démarrage |
| `session_lock.py` | ~120 | SessionStart | Lock multi-session |

### 1.5 Autres composants

| Composant | LOC | Rôle |
|-----------|-----|------|
| `community/pack_manager.py` | ~200 | Téléchargement packs YAML |
| `community/packs/` | ~300 | 3 packs (sur 5 déclarés) |
| `semgrep_integration.py` | 7 | Re-export (dead) |
| `e2e_semgrep.py` | 7 | Re-export (dead) |

### 1.6 Tests (16,252 LOC)

- **1,124 tests, 0 failures, 81% coverage**
- 52 fichiers de tests
- Points faibles: cli.py (13%), cli_v2.py (10%), hooks (0% mesuré), learn_runner (23%), metrics (53%)

---

## 2. DÉCISION PAR COMPOSANT {#2-decisions}

### ✅ GARDER — Migrer vers MCP Server

| Composant | Raison | Effort migration |
|-----------|--------|-----------------|
| `guards_v2/` (24 modules) | Cœur de l'analyse AST, 5,400 LOC testées | Faible — copie + wrapper MCP |
| `senior_guards/` (8 modules) | 100% unique, zéro concurrent | Faible — copie + wrapper MCP |
| `ai_guardian.py` | Détection AI session unique | Faible — copie directe |
| `scan_runner.py` | Orchestration scan | Moyen — adapter pour MCP |
| `semgrep_adapter.py` | Intégration Semgrep comme backend | Faible — copie + wrapper MCP |
| `metrics.py` | Collecte métriques, base SQLite | Moyen — étendre pour sessions |
| `hooks/` logique (scan + lock) | Logique de protection réutilisable | Moyen — transformer en MCP tools |

**Total gardé: ~8,500 LOC (65% du code)**

### ❌ JETER — Ne pas migrer

| Composant | Raison | Ce qui le remplace |
|-----------|--------|-------------------|
| `cli.py` (350 LOC) | 13% coverage, 3 bugs bloquants, architecture confuse | MCP Server = nouvelle interface |
| `cli_v2.py` (280 LOC) | 10% coverage, dispatch cassé | MCP tools remplacent le dispatch |
| `cli_setup.py` (150 LOC) | Code dupliqué (_get_cached_diff) | Setup MCP intégré |
| `scanner.py` V1 regex (300 LOC) | Redondant avec Semgrep (5000+ rules) | Semgrep via adapter |
| `learn_runner.py` (61 LOC) | 23% coverage, feature dormante | Supprimé (pas de valeur) |
| `community/pack_manager.py` (200 LOC) | Sans signature, 2 packs manquants | Remplacé par config MCP |
| `community/packs/` (300 LOC) | YAML sans vérification | Supprimé |
| `semgrep_integration.py` (7 LOC) | Dead code re-export | Supprimé |
| `e2e_semgrep.py` (7 LOC) | Dead code re-export | Supprimé |
| `config/default.yaml` (139 LOC) | Obsolète vs vibesrails.yaml | Nouvelle config MCP |

**Total jeté: ~1,794 LOC (14% du code)**

### 🔄 TRANSFORMER — Modifier significativement

| Composant | Transformation | Effort |
|-----------|---------------|--------|
| `scanner.py` (partie orchestration, ~200 LOC) | Extraire logique utile, jeter regex V1 | Moyen |
| `metrics.py` | Étendre pour tracking sessions (durée, entropy) | Moyen |
| `hooks/` (interface) | Transformer de hooks Claude Code en MCP tools | Fort |
| `vibesrails.yaml` | Nouvelle structure config pour MCP | Fort |

---

## 3. ARCHITECTURE CIBLE MCP SERVER {#3-architecture}

### 3.1 Structure des fichiers

```
vibesrails/                          # Même repo, nouveau point d'entrée
├── mcp_server.py                    # 🆕 Point d'entrée MCP (stdio + SSE)
├── tools/                           # 🆕 Outils MCP exposés
│   ├── __init__.py
│   ├── scan_code.py                 # Guards V2 AST via MCP
│   ├── scan_senior.py               # Senior Guards via MCP
│   ├── scan_semgrep.py              # Semgrep adapter via MCP
│   ├── check_session.py             # Guardian Mode via MCP
│   ├── monitor_entropy.py           # 🆕 Session Entropy Monitor
│   ├── check_drift.py               # 🆕 Drift Velocity Index
│   ├── check_config.py              # 🆕 AI Config Shield
│   ├── deep_hallucination.py        # 🆕 Deep Hallucination Analysis
│   └── prompt_shield.py             # 🆕 Prompt Injection Detection
├── guards_v2/                       # ♻️ INCHANGÉ — copie directe
│   ├── __init__.py                  # Fix B4: ajouter PreDeployGuard.scan()
│   ├── architecture_drift.py
│   ├── mutation_engine.py
│   ├── test_integrity.py
│   ├── env_repr_leak.py
│   └── ... (24 modules)
├── senior_guards/                   # ♻️ INCHANGÉ — copie directe
│   ├── hallucination_guard.py
│   ├── session_discipline.py
│   ├── brief_enforcement.py
│   └── ... (8 modules)
├── core/                            # 🆕 Nouveau noyau
│   ├── __init__.py
│   ├── guardian.py                   # ♻️ Copie de ai_guardian.py
│   ├── session_tracker.py           # 🆕 Tracking sessions (durée, fichiers, complexité)
│   ├── drift_tracker.py             # 🆕 Mesure drift architectural
│   ├── config_shield.py             # 🆕 Scan fichiers config AI
│   ├── hallucination_deep.py        # 🆕 Vérification sémantique imports
│   ├── prompt_shield.py             # 🆕 Détection prompt injection dans code
│   └── profiler.py                  # 🆕 Agrégation cross-session
├── adapters/                        # 🆕 Intégrations backends
│   ├── __init__.py
│   ├── semgrep_adapter.py           # ♻️ Copie de semgrep_adapter.py
│   └── medusa_adapter.py            # 🆕 Futur — intégration MEDUSA
├── storage/
│   ├── __init__.py
│   ├── session_db.py                # 🆕 SQLite pour sessions + métriques
│   └── migrations.py               # 🆕 Schema versioning (upgrade safe)
├── pedagogy/                        # 🆕 Messages pédagogiques
│   ├── __init__.py
│   ├── explanations.py              # Messages "pourquoi" par type de violation
│   ├── recommendations.py           # Messages "comment éviter" par type
│   └── session_tips.py              # Conseils basés sur l'état de la session
├── config/
│   ├── default_mcp.yaml             # 🆕 Config MCP par défaut
│   └── schema.py                    # 🆕 Validation config
├── cli.py                           # 🆕 CLI minimal (backward compat)
├── tests/                           # Tests existants + nouveaux
│   ├── test_guards_v2/              # ♻️ INCHANGÉ
│   ├── test_senior_guards/          # ♻️ INCHANGÉ
│   ├── test_tools/                  # 🆕 Tests outils MCP
│   ├── test_core/                   # 🆕 Tests nouveau noyau
│   └── test_pedagogy/               # 🆕 Tests messages pédagogiques
└── pyproject.toml                   # Mis à jour
```

### 3.2 Dépendances

```toml
[project]
dependencies = [
    "mcp>=1.0",              # 🆕 MCP SDK Python
    "pyyaml>=6.0",           # Existant
    "rich>=13.0",            # Existant (output formaté)
]

[project.optional-dependencies]
semgrep = ["semgrep>=1.50"]  # Optionnel — backend Semgrep
deep = [                      # Optionnel — hallucination profonde
    "requests>=2.31",        # Vérification PyPI/npm
]
all = ["vibesrails[semgrep,deep]"]
```

### 3.3 Protocole MCP — Outils exposés

Chaque outil MCP suit ce contrat:

```python
@mcp_server.tool()
async def tool_name(arguments: dict) -> dict:
    """
    Returns:
        {
            "status": "pass" | "warn" | "fail" | "block",
            "findings": [...],
            "pedagogy": {          # 🆕 LE DIFFÉRENCIATEUR
                "why": "...",      # Pourquoi ce problème existe
                "how_to_fix": "...",  # Comment le corriger
                "prevention": "..."   # Comment l'éviter à l'avenir
            },
            "session_context": {   # 🆕 Contexte session
                "duration_minutes": 45,
                "entropy_score": 0.72,
                "files_modified": 12
            }
        }
    """
```

---

## 4. MAPPING MIGRATION: ANCIEN → NOUVEAU {#4-mapping}

### 4.1 Fichiers — Correspondance exacte

| Ancien fichier | Action | Nouveau fichier | Modifications |
|----------------|--------|-----------------|---------------|
| `guards_v2/*.py` (24) | COPIE | `guards_v2/*.py` | Fix B4 (PreDeployGuard.scan) uniquement |
| `senior_guards/*.py` (8) | COPIE | `senior_guards/*.py` | Aucune |
| `ai_guardian.py` | COPIE+RENAME | `core/guardian.py` | Rename + nettoyage imports |
| `semgrep_adapter.py` | COPIE | `adapters/semgrep_adapter.py` | Nettoyage imports |
| `metrics.py` | TRANSFORM | `storage/session_db.py` | Étendre avec session tracking |
| `scan_runner.py` | TRANSFORM | `tools/scan_code.py` | Wrapper MCP autour de la logique |
| `hooks/pre_tool_use.py` | TRANSFORM | (logique dans scan_code.py) | Extraire logique, jeter interface hook |
| `hooks/post_tool_use.py` | TRANSFORM | (logique dans scan_code.py) | Extraire logique, jeter interface hook |
| `hooks/session_scan.py` | TRANSFORM | `tools/check_session.py` | Wrapper MCP |
| `hooks/session_lock.py` | TRANSFORM | `core/session_tracker.py` | Intégrer dans session tracking |
| `cli.py` | JETER | `cli.py` (nouveau, minimal) | Nouveau CLI minimal |
| `cli_v2.py` | JETER | — | Remplacé par MCP tools |
| `cli_setup.py` | JETER | — | Remplacé par config MCP |
| `scanner.py` | PARTIEL | `tools/scan_code.py` | Garder orchestration, jeter regex V1 |
| `learn_runner.py` | JETER | — | Feature supprimée |
| `community/*` | JETER | — | Remplacé par config MCP |
| `config/default.yaml` | JETER | `config/default_mcp.yaml` | Nouvelle config from scratch |

### 4.2 Tests — Correspondance

| Ancien test | Action | Nouveau test |
|-------------|--------|-------------|
| `tests/test_guards_v2/` | COPIE | `tests/test_guards_v2/` — inchangé |
| `tests/test_senior_guards/` | COPIE | `tests/test_senior_guards/` — inchangé |
| `tests/test_cli.py` | JETER | `tests/test_tools/` — nouveaux tests MCP |
| `tests/test_hooks/` | TRANSFORM | `tests/test_tools/` — adapter pour MCP |
| `tests/test_scanner.py` | PARTIEL | `tests/test_tools/test_scan_code.py` |

### 4.3 Bugs de l'audit — Résolution

| Bug | Résolution dans MCP |
|-----|-------------------|
| **B1** CLI 13% coverage | RÉSOLU — CLI jeté, MCP tools testés from scratch |
| **B2** Exécution continue après erreur | RÉSOLU — MCP = request/response, pas de flow continu |
| **B3** Double learn command | RÉSOLU — Feature supprimée |
| **B4** PreDeployGuard.scan() | **À FIXER** — 3 lignes, 5 minutes |
| **B5** session_scan 0 tests | **À TESTER** — Nouveaux tests dans test_tools/ |
| **B6** learn_runner 23% | RÉSOLU — Feature supprimée |
| **B7** metrics 53% | **À TESTER** — Nouveaux tests pour session_db.py |
| **B8** default.yaml obsolète | RÉSOLU — Nouvelle config MCP from scratch |
| **I1** scanner.py 506 lignes | RÉSOLU — Éclaté en tools/ |
| **I2** Config crash None | **À FIXER** — Validation dans schema.py |
| **I3** Code dupliqué diff | RÉSOLU — Fichiers jetés |
| **I4** Hooks 0% coverage | RÉSOLU — Hooks remplacés par MCP tools testés |
| **I5** Race condition lock | **À FIXER** — Atomique dans session_tracker.py |
| **I6** Semgrep 54% coverage | **À TESTER** — Nouveaux tests adapter |
| **I7** Pack manager sans signature | RÉSOLU — Pack manager supprimé |
| **I8** Packs incomplets | RÉSOLU — Packs supprimés |
| **I9** Regex secrets manquants | RÉSOLU — Semgrep les détecte mieux |
| **I10** Crash modules optionnels | **À FIXER** — try/except dans adapters/ |

**Résumé: 8 bloquants → 1 fix 5min (B4) + 3 à tester + 4 résolus automatiquement par la migration**

---

## 5. 6 CONCEPTS UNIQUES — SPÉCIFICATIONS TECHNIQUES {#5-concepts}

### 5.1 SESSION ENTROPY MONITOR™

**Fichier**: `core/session_tracker.py` + `tools/monitor_entropy.py`

**Données trackées** (SQLite):
```python
class SessionRecord:
    session_id: str           # ID session Claude Code
    start_time: datetime
    files_modified: list[str]
    total_changes_loc: int    # Lignes ajoutées + supprimées
    violations_count: int     # Violations détectées
    ai_tool: str              # "claude_code" | "cursor" | "copilot"
    entropy_score: float      # 0.0 (safe) → 1.0 (danger)
```

**Calcul entropy_score**:
```python
def calculate_entropy(session: SessionRecord) -> float:
    duration_factor = min(session.duration_minutes / 60, 1.0)  # Max à 60min
    files_factor = min(len(session.files_modified) / 20, 1.0)  # Max à 20 fichiers
    violations_factor = min(session.violations_count / 10, 1.0) # Max à 10 violations
    change_factor = min(session.total_changes_loc / 500, 1.0)  # Max à 500 LOC
    
    return (duration_factor * 0.3 + 
            files_factor * 0.2 + 
            violations_factor * 0.3 + 
            change_factor * 0.2)
```

**Seuils**:
- 0.0–0.3: ✅ Safe — scan normal
- 0.3–0.6: ⚠️ Warning — "Session longue, considère un break"
- 0.6–0.8: 🔶 Elevated — scan strict, tous les guards activés
- 0.8–1.0: 🔴 Critical — "STOP. Reset ta session. 88% d'hallucination après 20min"

**Pédagogie intégrée**:
```python
ENTROPY_PEDAGOGY = {
    "warn": {
        "why": "Les sessions AI longues produisent 88% plus d'hallucinations (source: Rev 2025, 1038 répondants). "
               "Ton score d'entropie est à {score:.0%}.",
        "how_to_fix": "Commit ton travail actuel, prends 5 minutes, puis recommence une session propre.",
        "prevention": "Règle d'or: 1 session = 1 feature = max 20 minutes."
    },
    "critical": {
        "why": "Session active depuis {minutes} minutes avec {files} fichiers modifiés. "
               "La probabilité d'hallucination est maximale.",
        "how_to_fix": "STOP IMMÉDIAT. Commit, review ce qui a été généré, puis nouvelle session.",
        "prevention": "Utilise le Senior Mode: brief → code → review → commit. Jamais de marathon."
    }
}
```

### 5.2 PRE-GENERATION DISCIPLINE (Senior Mode v2)

**Fichier**: `tools/scan_senior.py` (wraps `senior_guards/brief_enforcement.py`)

**Brief requis avant génération**:
```yaml
# Exemple de brief structuré
vibesrails_brief:
  feature: "Ajouter authentification JWT"
  constraints:
    - "Ne PAS modifier models/user.py"
    - "Utiliser PyJWT, pas jose"
    - "Max 3 fichiers modifiés"
  architecture:
    pattern: "middleware dans auth/"
    forbidden_dirs: ["core/", "models/"]
  scope: "auth/jwt_middleware.py + auth/decorators.py + tests/"
  acceptance_criteria:
    - "Tests passent"
    - "Aucun secret hardcodé"
```

**MCP Tool**: `enforce_brief`
```python
@mcp_server.tool()
async def enforce_brief(arguments: dict) -> dict:
    """Vérifie qu'un brief structuré existe avant de coder.
    
    Arguments:
        file_path: Fichier sur le point d'être modifié
        session_id: ID de la session active
    
    Returns:
        status: "pass" si brief existe et couvre ce fichier
                "block" si aucun brief ou fichier hors scope
    """
```

**Pédagogie**:
```python
BRIEF_PEDAGOGY = {
    "no_brief": {
        "why": "Coder sans brief = naviguer sans carte. L'AI va halluciner des solutions "
               "qui semblent correctes mais violent ton architecture.",
        "how_to_fix": "Crée un fichier .vibesrails-brief.yaml avec: feature, constraints, scope.",
        "prevention": "Avant chaque feature: 2 minutes de brief > 2 heures de debug."
    }
}
```

### 5.3 DRIFT VELOCITY INDEX™

**Fichier**: `core/drift_tracker.py` + `tools/check_drift.py`

**Concept**: Mesurer la VITESSE de dérive, pas juste la détecter.

**Données**:
```python
class DriftSnapshot:
    timestamp: datetime
    file_path: str
    metrics: {
        "import_count": int,
        "class_count": int,
        "function_count": int,
        "dependency_count": int,
        "complexity_avg": float,
        "public_api_surface": list[str],  # Fonctions/classes publiques
    }

class DriftVelocity:
    period: str  # "session" | "day" | "week"
    files_drifted: int
    drift_percentage: float  # % de changement moyen
    hotspots: list[str]      # Fichiers qui dérivent le plus
    trend: str               # "accelerating" | "stable" | "decelerating"
```

**Calcul**:
```python
def measure_drift(before: DriftSnapshot, after: DriftSnapshot) -> float:
    deltas = []
    for metric in before.metrics:
        if before.metrics[metric] != 0:
            delta = abs(after.metrics[metric] - before.metrics[metric]) / before.metrics[metric]
            deltas.append(delta)
    return sum(deltas) / len(deltas) if deltas else 0.0
```

**Seuils**:
- 0–5% drift par session: ✅ Normal
- 5–15% drift: ⚠️ "Architecture qui bouge vite"
- 15%+ drift: 🔴 "STOP — dérive architecturale détectée"
- 3 sessions consécutives à >10%: 🔴 "Tendance de dérive — review architecturale requise"

### 5.4 AI CONFIG SHIELD

**Fichier**: `core/config_shield.py` + `tools/check_config.py`

**Fichiers scannés**:
```python
AI_CONFIG_FILES = [
    ".cursorrules",
    ".cursor/rules/*.mdc",
    "CLAUDE.md",
    ".claude/settings.json",
    ".github/copilot-instructions.md",
    ".windsurfrules",
    ".clinerules",
    "mcp.json",
    ".mcp.json",
]
```

**Vérifications**:
```python
class ConfigShieldChecks:
    # 1. Unicode caché (attaque Rules File Backdoor)
    def check_hidden_unicode(self, content: str) -> list[Finding]:
        """Détecte caractères Unicode invisibles (U+E0000-U+E007F, 
        zero-width, RTL override, etc.)"""
    
    # 2. Instructions contradictoires
    def check_contradictions(self, content: str) -> list[Finding]:
        """Détecte: 'ignore security', 'skip validation', 
        'disable checks', 'no need to test'"""
    
    # 3. Exfiltration tentatives
    def check_exfiltration(self, content: str) -> list[Finding]:
        """Détecte: URLs externes suspectes, fetch/curl instructions,
        'send to', 'post to', webhook URLs"""
    
    # 4. Override de sécurité
    def check_security_override(self, content: str) -> list[Finding]:
        """Détecte: 'bypass auth', 'hardcode', 'skip ssl',
        'eval(', 'exec(' dans les instructions"""
```

**Pédagogie**:
```python
CONFIG_SHIELD_PEDAGOGY = {
    "hidden_unicode": {
        "why": "Des caractères Unicode invisibles ont été trouvés dans {file}. "
               "C'est l'attaque 'Rules File Backdoor' documentée par Pillar Security (mars 2025). "
               "Ces caractères injectent des instructions malicieuses que tu ne peux pas voir.",
        "how_to_fix": "Ouvre le fichier en mode hex. Supprime tous les caractères non-ASCII non intentionnels.",
        "prevention": "Toujours vérifier les fichiers de config AI après un git pull de sources externes."
    }
}
```

### 5.5 DEEP HALLUCINATION ANALYSIS

**Fichier**: `core/hallucination_deep.py` + `tools/deep_hallucination.py`

**Au-delà du HallucinationGuard existant** (qui vérifie juste si un import existe):

```python
class DeepHallucinationChecker:
    # Niveau 1: Import existe? (existant dans senior_guards)
    def check_import_exists(self, module_name: str) -> bool
    
    # Niveau 2: 🆕 Package existe sur PyPI/npm?
    async def check_package_registry(self, package: str, ecosystem: str) -> dict:
        """Vérifie via API PyPI/npm si le package existe réellement.
        Détecte slopsquatting (noms similaires à des packages réels)."""
    
    # Niveau 3: 🆕 La fonction/classe utilisée existe dans le package?
    def check_api_surface(self, package: str, symbol: str) -> dict:
        """Vérifie que 'from package import symbol' est valide.
        L'AI invente souvent des fonctions qui n'existent pas."""
    
    # Niveau 4: 🆕 La version est compatible?
    def check_version_compat(self, package: str, version: str, symbol: str) -> dict:
        """Vérifie que le symbol existe dans la version spécifiée.
        Ex: pandas.DataFrame.to_markdown() n'existe pas avant 1.0"""
```

**Cache** (SQLite, pour ne pas spammer les registries):
```python
# Table: package_cache
# package_name | ecosystem | exists | api_surface | version | cached_at
# TTL: 24h pour existence, 7j pour api_surface
```

### 5.6 CROSS-SESSION PROFILER

**Fichier**: `core/profiler.py` + `storage/session_db.py`

**Données agrégées**:
```python
class ProjectProfile:
    project_path: str
    sessions_total: int
    avg_session_duration: float
    avg_entropy_score: float
    recurring_violations: dict[str, int]  # type → count
    model_breakdown: dict[str, dict]      # "claude" → {sessions, avg_entropy, top_violations}
    hotspot_files: list[str]              # Fichiers les plus souvent violés
    drift_trend: str                      # "improving" | "stable" | "degrading"
    recommendations: list[str]            # Conseils personnalisés basés sur l'historique
```

**MCP Tool**: `get_profile`
```python
@mcp_server.tool()
async def get_profile(arguments: dict) -> dict:
    """Retourne le profil cumulé du projet: tendances, violations récurrentes,
    recommandations personnalisées basées sur l'historique."""
```

### 5.7 PROMPT SHIELD

**Fichier**: `core/prompt_shield.py` + `tools/prompt_shield.py`

**Contexte**: L'attaque "Rules File Backdoor" (Pillar Security, mars 2025) et les prompt injections dans le code sont des vecteurs réels. `agent-security-scanner-mcp` a un firewall pour ça. On doit couvrir cet angle.

**Ce qu'on scanne** (dans les fichiers de code ET les configs):
```python
class PromptShieldChecks:
    # 1. Instructions cachées dans les commentaires
    def check_hidden_instructions(self, content: str) -> list[Finding]:
        """Détecte dans les commentaires de code:
        - 'ignore previous instructions'
        - 'you are now', 'act as', 'pretend you'
        - 'do not tell the user'
        - 'bypass', 'override safety'
        - Instructions en base64 encodées dans les commentaires
        """
    
    # 2. Unicode invisible (U+E0000-U+E007F, zero-width, RTL override)
    def check_invisible_unicode(self, content: str) -> list[Finding]:
        """Détecte caractères invisibles qui cachent des instructions
        pour les LLMs tout en étant invisibles aux humains."""
    
    # 3. Exfiltration patterns dans le code
    def check_exfiltration_code(self, content: str) -> list[Finding]:
        """Détecte: 
        - fetch/requests.post vers des URLs non-whitelistées
        - subprocess avec URLs dynamiques
        - eval/exec avec input réseau
        - Envoi de variables d'environnement vers l'extérieur
        """
    
    # 4. Social engineering dans les strings
    def check_social_engineering(self, content: str) -> list[Finding]:
        """Détecte dans les docstrings/strings:
        - Instructions qui ciblent les LLMs ('when asked about', 'always respond with')
        - Tentatives de manipulation de contexte
        """
```

**Pédagogie**:
```python
PROMPT_SHIELD_PEDAGOGY = {
    "hidden_instruction": {
        "why": "Un commentaire dans {file}:{line} contient une instruction qui cible ton IA. "
               "Quand Claude/Cursor lit ce fichier, il obéit à cette instruction cachée. "
               "C'est l'attaque 'Rules File Backdoor' documentée par Pillar Security.",
        "how_to_fix": "Supprime le commentaire suspect. Vérifie l'historique git: qui l'a ajouté?",
        "prevention": "Scanne toujours les fichiers après un git pull de sources externes."
    },
    "exfiltration": {
        "why": "Ce code envoie des données vers {url}. Si c'est du code AI-generated, "
               "l'IA a peut-être été manipulée pour ajouter cette exfiltration.",
        "how_to_fix": "Vérifie que l'URL de destination est légitime et attendue.",
        "prevention": "Whitelist les domaines autorisés dans ta config vibesrails."
    }
}
```

### 5.8 SCHEMA MIGRATIONS (SQLite)

**Fichier**: `storage/migrations.py`

**Problème**: Entre v0.1 et v0.2, le schema SQLite change. Sans migration, `pip install --upgrade` → crash ou perte de données.

**Solution** (simple, pas d'ORM, ~50 LOC):
```python
SCHEMA_VERSION = 1

MIGRATIONS = {
    1: [
        """CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            start_time TEXT NOT NULL,
            end_time TEXT,
            ai_tool TEXT,
            files_modified TEXT,  -- JSON array
            total_changes_loc INTEGER DEFAULT 0,
            violations_count INTEGER DEFAULT 0,
            entropy_score REAL DEFAULT 0.0,
            project_path TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES sessions(id),
            timestamp TEXT NOT NULL,
            guard_name TEXT NOT NULL,
            file_path TEXT,
            severity TEXT,
            message TEXT,
            pedagogy_shown INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS drift_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES sessions(id),
            file_path TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metrics TEXT  -- JSON object
        )""",
        """CREATE TABLE IF NOT EXISTS package_cache (
            package_name TEXT NOT NULL,
            ecosystem TEXT NOT NULL,
            exists_flag INTEGER,
            api_surface TEXT,  -- JSON
            version TEXT,
            cached_at TEXT NOT NULL,
            PRIMARY KEY (package_name, ecosystem)
        )""",
        "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1')",
    ],
    # Future migrations:
    # 2: ["ALTER TABLE sessions ADD COLUMN ai_model_version TEXT DEFAULT 'unknown'"],
}

def get_current_version(conn) -> int:
    try:
        cursor = conn.execute("SELECT value FROM meta WHERE key='schema_version'")
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0

def migrate(db_path: str) -> None:
    """Exécuté au démarrage du MCP Server. Idempotent."""
    conn = sqlite3.connect(db_path)
    current = get_current_version(conn)
    for version in sorted(MIGRATIONS.keys()):
        if version > current:
            for sql in MIGRATIONS[version]:
                conn.execute(sql)
            conn.execute("UPDATE meta SET value=? WHERE key='schema_version'", (str(version),))
    conn.commit()
    conn.close()
```

**Règles**:
- Chaque migration est un numéro incrémental
- Jamais de DROP/DELETE dans les migrations (données utilisateur)
- ALTER TABLE ADD COLUMN uniquement (SQLite ne supporte pas RENAME COLUMN < 3.25)
- Exécuté automatiquement au démarrage, idempotent

---

## 6. PLAN D'EXÉCUTION {#6-plan}

### Semaine 1: Fondation

| Jour | Tâche | Livrable | Test |
|------|-------|----------|------|
| J1 | Archive v2.0.0 (git tag, tar.gz) | `v2.0.0-archive` tag | Vérifier intégrité archive |
| J1 | Scaffold MCP Server (mcp_server.py) + migrations.py | Server qui démarre + DB init | `pytest test_mcp_server.py` |
| J2 | Copier guards_v2/ (24 modules) inchangés | Guards dans nouveau projet | Tests existants passent |
| J2 | Fix B4: PreDeployGuard.scan() | Bug bloquant corrigé | `run_all_guards()` ne crash plus |
| J3 | Copier senior_guards/ (8 modules) | Senior guards dans projet | Tests existants passent |
| J3 | Copier ai_guardian.py → core/guardian.py | Guardian mode migré | Tests existants passent |
| J4 | Copier semgrep_adapter.py → adapters/ | Semgrep adapter migré | Tests existants passent |
| J4 | Premier MCP tool: `scan_code` | scan_code opérationnel | Test MCP tool call |
| J5 | MCP tools: `scan_senior` + `scan_semgrep` | 3 outils MCP live | Tests tools |
| J5 | MCP tool: `check_session` (Guardian) | 4 outils MCP live | Tests tools |

**Critère fin S1**: `vibesrails-mcp` démarre, 4 tools fonctionnels, tous tests passent.

### Semaine 2: Concepts uniques (1-2)

| Jour | Tâche | Livrable | Test |
|------|-------|----------|------|
| J1 | `storage/session_db.py` — SQLite schema | DB sessions opérationnelle | Tests CRUD |
| J1 | `core/session_tracker.py` — tracking | Tracking sessions | Tests calcul entropy |
| J2 | `tools/monitor_entropy.py` — MCP tool | Session Entropy Monitor live | Tests seuils + pedagogy |
| J3 | `core/config_shield.py` — détection | Scan configs AI | Tests Unicode + exfiltration |
| J4 | `tools/check_config.py` — MCP tool | AI Config Shield live | Tests MCP tool |
| J5 | `pedagogy/` — messages pour concepts 1-2 | Messages pédagogiques | Tests contenu |

**Critère fin S2**: 6 tools MCP, Session Entropy + Config Shield fonctionnels.

### Semaine 3: Concepts uniques (3-4-5)

| Jour | Tâche | Livrable | Test |
|------|-------|----------|------|
| J1 | `core/hallucination_deep.py` — Niveaux 2-4 | Deep hallucination | Tests avec packages réels |
| J2 | `tools/deep_hallucination.py` — MCP tool | Deep Hallucination live | Tests MCP tool |
| J3 | `core/drift_tracker.py` — snapshots + velocity | Drift tracking | Tests calcul drift |
| J3 | `tools/check_drift.py` — MCP tool | Drift Velocity live | Tests MCP tool |
| J4 | `core/prompt_shield.py` — détection injections | Prompt Shield | Tests patterns injection |
| J4 | `tools/prompt_shield.py` — MCP tool | Prompt Shield live | Tests MCP tool |
| J5 | `pedagogy/` — messages concepts 3-4-5 | Messages pédagogiques | Tests contenu |

**Critère fin S3**: 9 tools MCP, tous concepts implémentés.

### Semaine 4: Polish + Profiler

| Jour | Tâche | Livrable | Test |
|------|-------|----------|------|
| J1 | `core/profiler.py` — agrégation cross-session | Profiler opérationnel | Tests agrégation |
| J2 | `tools/get_profile.py` — MCP tool | Cross-Session Profiler live | Tests MCP tool |
| J3 | CLI minimal backward-compatible | `vibesrails scan` fonctionne encore | Tests CLI |
| J4 | Config MCP (`default_mcp.yaml` + `schema.py`) | Config validée | Tests validation |
| J5 | Coverage global ≥ 80%, ruff clean | Qualité production | Tous tests passent |

**Critère fin S4**: MVP complet, 9+ tools MCP, ≥80% coverage.

### Semaine 5: Launch

| Jour | Tâche | Livrable |
|------|-------|----------|
| J1 | README killer + CHANGELOG + LICENSE | Documentation complète |
| J2 | Article "I can't code and I built this" | Blog post |
| J3 | Config Claude Code + Cursor + Windsurf | Instructions installation |
| J4 | Push PyPI + GitHub release | v0.1.0 publié |
| J5 | Posts Twitter/LinkedIn/Reddit | Lancement public |

---

## 7. PROMPTS CLAUDE CODE — PAR ÉTAPE {#7-prompts}

### Prompt S1-J1: Scaffold MCP Server + Migrations

```
CONTEXTE: Tu travailles sur vibesrails, un outil de sécurité Python pour AI-assisted coding.
On pivote vers un MCP Server. Le projet existant a 1124 tests qui passent, 81% coverage.
L'archive v2.0.0 est déjà faite.

IMPORTANT: Lis d'abord docs/VIBESRAILS_MCP_MIGRATION_SPEC.md pour comprendre l'architecture
cible complète. Ce fichier est ta référence pour TOUT le projet.

ÉTAPE 1 — SCAFFOLD MCP SERVER
1. Installe la dépendance: pip install mcp
2. Crée mcp_server.py à la racine avec:
   - Un MCP Server basique (stdio transport)
   - Un tool de test "ping" qui retourne {"status": "ok", "version": "0.1.0"}
   - Logging vers stderr
   - Appel à migrate() au démarrage (voir étape 3)
3. Crée la structure de dossiers (chacun avec __init__.py vide):
   - tools/
   - core/
   - adapters/
   - storage/
   - pedagogy/
   - config/
4. Vérifie que le server démarre: python mcp_server.py

ÉTAPE 2 — SCHEMA MIGRATIONS
1. Crée storage/migrations.py avec:
   - SCHEMA_VERSION = 1
   - MIGRATIONS dict avec version 1 contenant les CREATE TABLE:
     * meta (key TEXT PK, value TEXT)
     * sessions (id TEXT PK, start_time TEXT, end_time TEXT, ai_tool TEXT,
       files_modified TEXT, total_changes_loc INT, violations_count INT,
       entropy_score REAL, project_path TEXT)
     * violations (id INTEGER PK AUTOINCREMENT, session_id TEXT FK,
       timestamp TEXT, guard_name TEXT, file_path TEXT, severity TEXT,
       message TEXT, pedagogy_shown INT DEFAULT 0)
     * drift_snapshots (id INTEGER PK AUTOINCREMENT, session_id TEXT FK,
       file_path TEXT, timestamp TEXT, metrics TEXT)
     * package_cache (package_name TEXT, ecosystem TEXT, exists_flag INT,
       api_surface TEXT, version TEXT, cached_at TEXT, PK(package_name, ecosystem))
   - get_current_version(conn) -> int
   - migrate(db_path) -> None (idempotent, exécuté au démarrage)
   - DB path: ~/.vibesrails/sessions.db (créer le dossier si nécessaire)

ÉTAPE 3 — TESTS
1. Crée tests/test_mcp_server.py:
   - Test: server s'initialise sans erreur
   - Test: tool "ping" retourne le format attendu
   - Test: version est "0.1.0"
2. Crée tests/test_storage/test_migrations.py:
   - Test: migrate() crée toutes les tables
   - Test: migrate() est idempotent (2ème appel ne crash pas)
   - Test: get_current_version retourne 1 après migration
   - Test: dossier ~/.vibesrails/ est créé automatiquement
   - Test: DB vide → migration complète
   - Utiliser un tmp_path fixture pour ne pas toucher la vraie DB

ÉTAPE 4 — VÉRIFICATION
1. Tous les tests EXISTANTS (1124) passent toujours
2. Les nouveaux tests passent
3. ruff check — 0 erreurs
4. Le MCP server démarre et répond au ping

CONTRAINTES:
- NE modifie AUCUN fichier existant
- NE supprime RIEN
- Le code existant (cli.py, scanner.py, etc.) doit continuer à fonctionner
- Python 3.10+ minimum
- SQLite3 standard library uniquement (pas de dépendance ORM)
- Toutes les requêtes SQL paramétrées (pas de f-strings)
```

### Prompt S1-J2: Migration Guards V2

```
CONTEXTE: vibesrails pivote vers MCP Server. Le scaffold est prêt (mcp_server.py + dossiers).
On migre maintenant les guards V2 (24 modules AST) qui sont le cœur du produit.

TÂCHE:
1. Les guards_v2/ existent déjà dans le projet. Ils restent EN PLACE (pas de copie).
   Le MCP Server va les importer directement.

2. FIX CRITIQUE B4: Dans guards_v2/pre_deploy.py, ajouter:
   def scan(self, project_root):
       return self.run_all(project_root)
   Ceci corrige le crash de run_all_guards() documenté dans l'audit.

3. Crée tools/scan_code.py:
   - Import des guards depuis guards_v2/
   - Fonction MCP tool "scan_code" qui:
     a) Accepte: {"file_path": str, "guards": list[str] | "all"}
     b) Exécute les guards demandés sur le fichier
     c) Retourne: {"status", "findings", "pedagogy"}
   - Le champ "pedagogy" pour chaque finding doit contenir:
     {"why": "...", "how_to_fix": "...", "prevention": "..."}

4. Enregistre le tool dans mcp_server.py

5. Crée tests/test_tools/test_scan_code.py:
   - Test que scan_code retourne des findings sur du code avec des problèmes connus
   - Test que "pedagogy" est toujours présent dans chaque finding
   - Test avec guards="all" et guards=["dead_code", "complexity"]
   - Minimum 10 tests, target 80% coverage sur scan_code.py

CONTRAINTES:
- Les tests existants des guards_v2 (dans tests/test_guards_v2/) doivent TOUJOURS passer
- Ne modifie PAS les guards eux-mêmes (sauf B4)
- Le scan_code tool est un WRAPPER autour des guards, pas une réécriture
```

### Prompt S1-J3: Migration Senior Guards + Guardian

```
CONTEXTE: MCP Server avec scan_code tool opérationnel. 
On ajoute les senior guards (8 modules) et le guardian mode.

TÂCHE 1 — Senior Guards MCP Tool:
1. Les senior_guards/ existent déjà. Pas de copie, import direct.
2. Crée tools/scan_senior.py:
   - MCP tool "scan_senior" qui:
     a) Accepte: {"file_path": str, "guards": list[str] | "all"}
     b) Exécute les senior guards (hallucination, discipline, brief, etc.)
     c) Retourne: {"status", "findings", "pedagogy"}
   - Pédagogie spécifique AI:
     - hallucination_guard → "L'AI a inventé cet import. Le package {pkg} n'existe pas sur PyPI."
     - session_discipline → "Tu codes depuis {minutes}min. Après 20min, 88% de révisions nécessaires."
     - brief_enforcement → "Pas de brief trouvé. Sans brief, l'AI navigue sans carte."

3. Crée tests/test_tools/test_scan_senior.py (minimum 10 tests)

TÂCHE 2 — Guardian Mode MCP Tool:
1. Copie ai_guardian.py → core/guardian.py (rename + update imports)
2. Crée tools/check_session.py:
   - MCP tool "check_session" qui:
     a) Détecte l'outil AI actif (Claude Code, Cursor, Copilot) via env vars
     b) Retourne: {"ai_tool": str, "session_active": bool, "recommendations": list}
   - Pédagogie: recommandations spécifiques par outil AI

3. Crée tests/test_tools/test_check_session.py (minimum 8 tests)

TÂCHE 3 — Enregistrer les tools dans mcp_server.py

CONTRAINTES:
- Tests existants des senior_guards et ai_guardian doivent TOUJOURS passer
- Ne modifie PAS les guards existants
```

### Prompt S1-J4-J5: Semgrep adapter + finalisation S1

```
CONTEXTE: MCP Server avec 3 tools (scan_code, scan_senior, check_session).
On ajoute Semgrep comme backend et on finalise la semaine 1.

TÂCHE 1 — Semgrep MCP Tool:
1. Copie semgrep_adapter.py → adapters/semgrep_adapter.py
2. Crée tools/scan_semgrep.py:
   - MCP tool "scan_semgrep" qui:
     a) Vérifie si Semgrep est installé (sinon message clair)
     b) Accepte: {"file_path": str, "rules": str | "auto"}
     c) Exécute Semgrep via l'adapter
     d) Retourne: {"status", "findings", "pedagogy"}
   - Pédagogie: pour chaque finding Semgrep, ajouter contexte AI:
     "Cette vulnérabilité est fréquente dans le code AI-generated car..."
3. Crée tests/test_tools/test_scan_semgrep.py (8 tests, mock Semgrep)

TÂCHE 2 — Tests d'intégration S1:
1. Crée tests/test_integration/test_mcp_full.py:
   - Test: server démarre avec tous les tools enregistrés
   - Test: chaque tool est appelable et retourne le format attendu
   - Test: scan_code + scan_senior + scan_semgrep sur le même fichier
   - Test: tous les résultats contiennent "pedagogy"

TÂCHE 3 — Vérification finale:
1. Lancer pytest — TOUS les tests (anciens + nouveaux) passent
2. Lancer ruff — 0 erreurs
3. Vérifier coverage ≥ 80% sur les nouveaux fichiers tools/

LIVRABLE FIN S1:
- mcp_server.py fonctionnel avec 4 tools: scan_code, scan_senior, scan_semgrep, check_session
- Tous les tests passent (anciens + ~40 nouveaux)
- Guards existants inchangés
```

### Prompt S2: Session Entropy + Config Shield

```
CONTEXTE: vibesrails MCP Server v0.1 avec 4 tools fonctionnels.
Semaine 2: on implémente les 2 premiers concepts uniques.

RÉFÉRENCE: Lis le fichier VIBESRAILS_MCP_MIGRATION_SPEC.md sections 5.1 et 5.4 
pour les spécifications détaillées.

TÂCHE 1 — Storage (J1):
1. Crée storage/session_db.py:
   - SQLite database (~/.vibesrails/sessions.db)
   - Tables: sessions, violations, snapshots
   - CRUD: create_session, update_session, get_session, list_sessions
   - Pas d'ORM, sqlite3 direct, requêtes paramétrées
2. Tests: tests/test_storage/test_session_db.py (15 tests minimum)

TÂCHE 2 — Session Entropy Monitor (J1-J2):
1. Crée core/session_tracker.py:
   - SessionTracker class
   - Méthodes: start_session, track_file_change, track_violation, calculate_entropy
   - Formule entropy: voir spec section 5.1
   - Seuils: 0-0.3 safe, 0.3-0.6 warn, 0.6-0.8 elevated, 0.8-1.0 critical
2. Crée tools/monitor_entropy.py:
   - MCP tool "monitor_entropy"
   - Accepte: {"session_id": str} ou {} pour session courante
   - Retourne: status + entropy_score + pedagogy avec messages de la spec
3. Crée pedagogy/session_tips.py:
   - Messages pédagogiques indexés par seuil d'entropy
   - Sources citées (Rev 2025, 88% revision rate)
4. Tests: 15+ tests couvrant calcul, seuils, messages

TÂCHE 3 — AI Config Shield (J3-J4):
1. Crée core/config_shield.py:
   - ConfigShield class
   - 4 checks: hidden_unicode, contradictions, exfiltration, security_override
   - Liste des fichiers config AI: voir spec section 5.4
2. Crée tools/check_config.py:
   - MCP tool "check_config"
   - Scanne automatiquement tous les fichiers config AI du projet
   - Retourne: status + findings + pedagogy
3. Crée pedagogy/explanations.py:
   - Messages pour chaque type de violation config
   - Référence: attaque Rules File Backdoor (Pillar Security, mars 2025)
4. Tests: 12+ tests (fichiers config avec et sans problèmes)

TÂCHE 4 — Enregistrer les 2 nouveaux tools dans mcp_server.py

CONTRAINTES:
- SQLite uniquement, pas de Redis/Postgres
- Pas de dépendances réseau pour Config Shield (analyse locale)
- Chaque tool < 100ms de latence
- Coverage ≥ 80% sur tous les nouveaux fichiers
```

### Prompt S3: Deep Hallucination + Drift Velocity

```
CONTEXTE: vibesrails MCP Server avec 6 tools. 
Semaine 3: Deep Hallucination Analysis + Drift Velocity Index.

RÉFÉRENCE: VIBESRAILS_MCP_MIGRATION_SPEC.md sections 5.3 et 5.5.

TÂCHE 1 — Deep Hallucination (J1-J2):
1. Crée core/hallucination_deep.py:
   - DeepHallucinationChecker class
   - Niveau 1: check_import_exists (réutilise senior_guards/hallucination_guard.py)
   - Niveau 2: check_package_registry — vérifie PyPI API (https://pypi.org/pypi/{pkg}/json)
   - Niveau 3: check_api_surface — vérifie que les symbols importés existent
   - Niveau 4: check_version_compat — vérifie compatibilité version
   - Cache SQLite: table package_cache (TTL 24h existence, 7j api_surface)
2. Crée tools/deep_hallucination.py:
   - MCP tool "deep_hallucination"
   - Accepte: {"file_path": str} ou {"import_statement": str}
   - Retourne: findings par niveau + pedagogy
3. Tests: 15+ tests (packages réels vs inventés, cache, fallback offline)

TÂCHE 2 — Drift Velocity Index (J3-J4):
1. Crée core/drift_tracker.py:
   - DriftTracker class
   - take_snapshot(file_path) → DriftSnapshot (métriques AST)
   - measure_drift(before, after) → float (% changement)
   - track_velocity(project_path) → DriftVelocity (trend sur N sessions)
   - Stockage: table drift_snapshots dans SQLite
2. Crée tools/check_drift.py:
   - MCP tool "check_drift"
   - Accepte: {"file_path": str} ou {"project_path": str}
   - Retourne: drift_percentage + velocity + trend + pedagogy
3. Tests: 12+ tests (fichier stable, fichier qui dérive, tendances)

TÂCHE 3 — Pédagogie concepts 3-4:
1. Ajouter dans pedagogy/explanations.py les messages pour:
   - Hallucination deep (slopsquatting, API fantôme, version mismatch)
   - Drift velocity (accélération, hotspots, recommandations review)

CONTRAINTES:
- Deep Hallucination: mode offline obligatoire (fallback si pas de réseau)
- Drift: calcul basé sur AST (ast.parse), pas sur diff textuel
- Cache: SQLite dans ~/.vibesrails/cache.db
```

### Prompt S4: Profiler + Polish

```
CONTEXTE: vibesrails MCP Server avec 8 tools, tous les concepts implémentés.
Semaine 4: Cross-Session Profiler + polish + qualité production.

TÂCHE 1 — Cross-Session Profiler (J1-J2):
1. Crée core/profiler.py:
   - ProjectProfiler class
   - get_profile(project_path) → ProjectProfile
   - Agrège: sessions, entropy moyenne, violations récurrentes, model breakdown
   - Génère recommendations personnalisées basées sur l'historique
2. Crée tools/get_profile.py:
   - MCP tool "get_profile"
3. Tests: 10+ tests

TÂCHE 2 — CLI backward-compatible (J3):
1. Crée un nouveau cli.py minimal:
   - `vibesrails scan <path>` → appelle scan_code
   - `vibesrails check` → appelle check_session + check_config
   - `vibesrails profile` → appelle get_profile
   - `vibesrails mcp` → lance le MCP server
   - Pas d'argparse complexe, juste click ou typer
2. Tests: 10 tests CLI

TÂCHE 3 — Config MCP (J4):
1. Crée config/default_mcp.yaml avec tous les seuils configurables
2. Crée config/schema.py pour validation
3. Gère: config=None, YAML invalide, seuils hors range

TÂCHE 4 — Qualité (J5):
1. ruff check — 0 erreurs
2. ruff format — tout formaté
3. pytest avec coverage — ≥ 80% global
4. Vérifier que CHAQUE MCP tool a des tests + pedagogy
5. Supprimer les fichiers jetés (cli.py ancien, cli_v2.py, etc.) ou les déplacer dans archive/

LIVRABLE FIN S4:
- 9+ MCP tools fonctionnels
- CLI backward-compatible
- ≥ 80% coverage
- 0 erreurs ruff
- Prêt pour release
```

---

## RÉSUMÉ EXÉCUTIF

### KPIs DE LANCEMENT

| KPI | Cible S+4 (1 mois post-launch) | Mesure |
|-----|-------------------------------|--------|
| Installs PyPI | 200+ | PyPI stats API (public) |
| GitHub stars | 50+ | Compteur GitHub |
| Retention S2 | 30%+ utilisent encore semaine 2 | Telemetry opt-in |

### TELEMETRY OPT-IN

```yaml
# default_mcp.yaml
telemetry:
  enabled: false  # JAMAIS opt-out. Toujours opt-in explicite.
  # Si activé: envoie UNIQUEMENT au démarrage:
  # - "server_started"
  # - vibesrails version
  # - os (linux/macos/windows)
  # - ai_tool détecté (claude_code/cursor/etc)
  # ZÉRO données projet, ZÉRO code, ZÉRO fichiers, ZÉRO IP
  endpoint: "https://telemetry.vibesrails.dev/ping"  # À créer post-MVP
```

### CONCURRENTS — MATRICE DE POSITIONNEMENT

```
                        agent-security  mcp-scan  mcp-fortress  vibesrails
                        scanner-mcp     (Invariant) (fortress)   MCP
Session Entropy              ❌            ❌          ❌          ✅
Brief Enforcement            ❌            ❌          ❌          ✅
Drift Velocity               ❌            ❌          ❌          ✅
AI Config Shield             ❌            ❌          ❌          ✅
Prompt Shield                ✅            ✅          ❌          ✅
Pédagogie intégrée           ❌            ❌          ❌          ✅
Cross-Session Profiling      ❌            ❌          ❌          ✅
Package hallucination     ✅ (bloom)       ❌          ❌       ✅ (PyPI API)
Vuln scanning             ✅ (359 rules)   ❌          ✅       ✅ (via Semgrep)
Prompt injection firewall    ✅            ✅          ❌          ✅
MCP Server scanning          ❌            ✅          ✅          ❌
```

**Positionnement vibesrails**: On ne scanne pas les MCP servers (mcp-scan fait ça). On scanne le CODE GÉNÉRÉ PAR L'IA et on ÉDUQUE le développeur. Complémentaire, pas concurrent.

---

```
ÉTAT ACTUEL                          ÉTAT CIBLE (S4)
─────────────────────────           ─────────────────────────
CLI argparse cassé (13%)     →      MCP Server 9+ tools
Guards V2 (24, testés)       →      Guards V2 (inchangés, via MCP)
Senior Guards (8, testés)    →      Senior Guards (inchangés, via MCP)  
Guardian Mode                →      check_session MCP tool
Semgrep adapter              →      scan_semgrep MCP tool
Scanner V1 regex             →      SUPPRIMÉ (Semgrep le remplace)
Pack manager (sans sig)      →      SUPPRIMÉ
Learn system (dormant)       →      SUPPRIMÉ
Hooks Claude Code            →      MCP tools (standard industrie)
0 pédagogie                  →      pedagogy/ (chaque finding expliqué)
0 tracking session           →      Session Entropy Monitor
0 détection config           →      AI Config Shield
Hallucination basique        →      Deep Hallucination (4 niveaux)
0 mesure drift               →      Drift Velocity Index
0 profiling                  →      Cross-Session Profiler

Code gardé: ~8,500 LOC (65%)
Code jeté: ~1,800 LOC (14%)
Code nouveau: ~3,000 LOC estimé
Tests nouveaux: ~150-200
```

**Le produit final**: Un MCP Server qui dit non seulement "ton code a un problème" mais "voici POURQUOI l'AI l'a généré, COMMENT le fixer, et COMMENT l'éviter la prochaine fois."

---

*Spec générée le 2026-02-07 — Prête pour exécution Claude Code*
