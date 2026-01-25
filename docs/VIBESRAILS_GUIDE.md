# vibesrails - Guide Complet

## Le Filet de Sécurité pour le Vibe Coding

---

## Qu'est-ce que vibesrails?

**vibesrails** est un scanner de sécurité automatique qui protège ton code sans ralentir ton flow.

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   Tu codes vite    →    vibesrails vérifie    →   Safe │
│   (vibe coding)         (automatique)              OK  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Problème résolu

| Sans vibesrails | Avec vibesrails |
|-----------------|-----------------|
| Secret pushé sur GitHub | Bloqué avant commit |
| SQL injection découverte en prod | Détectée immédiatement |
| AI génère du code dangereux | Guardian mode le bloque |
| Code review trouve les bugs tard | Détection instantanée |

---

## Installation (30 secondes)

```bash
pip install vibesrails
```

C'est tout. vibesrails s'auto-configure.

---

## Comment ça marche?

### Avec Claude Code (Automatique)

Quand tu utilises Claude Code dans un projet:

```
┌─────────────────────────────────────────────────────────┐
│  1. Claude Code détecte le projet                       │
│                    |                                    │
│  2. vibesrails analyse la structure                     │
│     - FastAPI? -> charge fastapi-pack                   │
│     - Django? -> charge django-pack                     │
│     - Secrets? -> active security-pack                  │
│                    |                                    │
│  3. Crée vibesrails.yaml optimisé                       │
│                    |                                    │
│  4. Installe le hook pre-commit                         │
│                    |                                    │
│  5. Chaque commit est scanné automatiquement            │
└─────────────────────────────────────────────────────────┘
```

**Tu n'as rien à faire.** Claude Code gère tout.

### Flow de développement

```
   Toi                    Claude Code                 vibesrails
    |                         |                           |
    | "Ajoute un login"       |                           |
    |------------------------>|                           |
    |                         |                           |
    |                         | Génère le code            |
    |                         |-------------------------->|
    |                         |                           | Scan
    |                         |                           |
    |                         |<--------------------------|
    |                         | BLOCK: hardcoded secret   |
    |                         |                           |
    |                         | Corrige automatiquement   |
    |                         |-------------------------->|
    |                         |                           | Scan
    |                         |<--------------------------|
    |                         | PASS                      |
    |                         |                           |
    |<------------------------|                           |
    | "Login ajouté avec      |                           |
    |  variables d'env"       |                           |
```

---

## Qu'est-ce qui est détecté?

### BLOCK (Commit refusé)

| Pattern | Exemple | Risque |
|---------|---------|--------|
| Secret hardcodé | `password = "admin123"` | Fuite de credentials |
| SQL Injection | `f"SELECT * FROM {user}"` | Base de données compromise |
| Shell Injection | `shell=True` | Exécution de code arbitraire |
| YAML dangereux | `yaml.load()` | Exécution de code |
| NumPy dangereux | `allow_pickle=True` | Exécution de code |

### WARN (Commit accepté, signalé)

| Pattern | Exemple | Amélioration |
|---------|---------|--------------|
| Star import | `from x import *` | Importer explicitement |
| None comparison | `x == None` | Utiliser `x is None` |
| Bare except | `except:` | Attraper exceptions spécifiques |

---

## Configuration Auto-Détectée

vibesrails analyse ton projet et charge les bons patterns:

```yaml
# vibesrails.yaml (généré automatiquement)

# Détecté: FastAPI + SQLAlchemy
extends:
  - "@vibesrails/security-pack"
  - "@vibesrails/fastapi-pack"

# Patterns spécifiques au projet
blocking:
  - id: project_secret
    regex: "ACME_API_KEY"
    message: "Clé API projet détectée"
```

### Packs disponibles

| Pack | Contenu |
|------|---------|
| `@vibesrails/security-pack` | OWASP Top 10, secrets, injections |
| `@vibesrails/web-pack` | XSS, CSRF, CORS |
| `@vibesrails/fastapi-pack` | Patterns FastAPI spécifiques |
| `@vibesrails/django-pack` | Patterns Django spécifiques |

---

## Guardian Mode (Protection AI)

Quand Claude Code génère du code, vibesrails active le **Guardian Mode**:

```
┌─────────────────────────────────────────────────────────┐
│  GUARDIAN MODE ACTIVE (Claude Code)                     │
│                                                         │
│  - Warnings deviennent BLOCK (plus strict)              │
│  - Patterns additionnels activés                        │
│  - Logging des blocks pour analyse                      │
│                                                         │
│  "L'AI code vite, vibesrails vérifie tout"             │
└─────────────────────────────────────────────────────────┘
```

---

## Suppression inline

Si un pattern est un faux positif:

```python
# Ignorer cette ligne
password = get_password()  # vibesrails: ignore

# Ignorer un pattern spécifique
value == None  # vibesrails: ignore [none_comparison]

# Ignorer la ligne suivante
# vibesrails: ignore-next-line
api_key = "test_key_for_unit_tests"
```

---

## Auto-Fix

vibesrails peut corriger automatiquement certains patterns:

```bash
vibesrails --fix      # Corrige
vibesrails --dry-run  # Prévisualise
```

**Patterns auto-fixables:**

| Avant | Après |
|-------|-------|
| `x == None` | `x is None` |
| `x != None` | `x is not None` |
| `yaml.load(f)` | `yaml.safe_load(f)` |
| `x == True` | `x` |
| `x == False` | `not x` |

---

## Résumé

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   vibesrails = pip install + forget                     │
│                                                         │
│   - Auto-configuration selon le projet                  │
│   - Scan automatique à chaque commit                    │
│   - Guardian mode pour Claude Code                      │
│   - Zero friction, zero commande manuelle               │
│                                                         │
│   Tu codes. vibesrails protège.                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Commandes (rarement nécessaires)

| Commande | Usage |
|----------|-------|
| `vibesrails --show` | Voir patterns actifs |
| `vibesrails --fix` | Auto-corriger |
| `vibesrails --guardian-stats` | Stats AI |
| `vibesrails --uninstall` | Désinstaller |

---

*vibesrails v1.2 - Scale up your vibe coding safely*
