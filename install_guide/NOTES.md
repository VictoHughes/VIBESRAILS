# vibesrails - Notes d'installation

## Comment ça marche?

### 1. Les Packs sont INCLUS dans le package

```
pip install vibesrails
     │
     └── Installe TOUT:
         ├── vibesrails (commande CLI)
         ├── vibesrails/packs/security.yaml   ← INCLUS
         ├── vibesrails/packs/web.yaml        ← INCLUS
         ├── vibesrails/packs/fastapi.yaml    ← INCLUS
         └── vibesrails/packs/django.yaml     ← INCLUS
```

**Tu n'as RIEN à télécharger séparément.** Les packs sont bundlés.

### 2. Où sont les fichiers?

| Fichier | Où? | Quand? |
|---------|-----|--------|
| `vibesrails` (CLI) | Système (pip) | `pip install` |
| `packs/*.yaml` | Dans le package pip | `pip install` |
| `vibesrails.yaml` | **TON PROJET** | `vibesrails --setup` |
| `.git/hooks/pre-commit` | **TON PROJET** | `vibesrails --setup` |

### 3. Flow d'installation

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ÉTAPE 1: pip install vibesrails                                │
│           └── Installe CLI + packs (une seule fois)             │
│                                                                 │
│  ÉTAPE 2: cd mon-projet/                                        │
│           vibesrails --setup                                    │
│           └── Crée vibesrails.yaml DANS ton projet              │
│           └── Installe hook DANS ton projet                     │
│                                                                 │
│  ÉTAPE 3: Tu codes, tu commit                                   │
│           └── Hook appelle vibesrails                           │
│           └── vibesrails lit vibesrails.yaml                    │
│           └── vibesrails charge les packs référencés            │
│           └── Scan → BLOCK ou PASS                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## C'est quoi les Packs?

Les packs sont des **fichiers YAML avec des règles prédéfinies**.

### Packs disponibles (inclus avec pip install):

| Pack | Alias | Contenu |
|------|-------|---------|
| `packs/security.yaml` | `@vibesrails/security-pack` | OWASP Top 10, secrets, injections |
| `packs/web.yaml` | `@vibesrails/web-pack` | XSS, CSRF, CORS |
| `packs/fastapi.yaml` | `@vibesrails/fastapi-pack` | Patterns FastAPI |
| `packs/django.yaml` | `@vibesrails/django-pack` | Patterns Django |

### Comment les utiliser?

Dans `vibesrails.yaml` de TON projet:

```yaml
# Utiliser UN pack
extends: "@vibesrails/security-pack"

# Utiliser PLUSIEURS packs
extends:
  - "@vibesrails/security-pack"
  - "@vibesrails/fastapi-pack"
```

vibesrails résout `@vibesrails/security-pack` → fichier dans le package pip.

## GitHub vs Local

| Élément | Sur GitHub? | Local? |
|---------|-------------|--------|
| Code source vibesrails | Oui (pour contribuer) | Non nécessaire |
| Package pip | PyPI | `~/.local/lib/python/...` |
| `vibesrails.yaml` | **Oui, dans ton repo** | Dans ton projet |
| `.git/hooks/pre-commit` | Non (gitignore) | Dans ton projet |

## Avec Claude Code

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Claude Code démarre dans ton-projet/                           │
│       │                                                         │
│       ▼                                                         │
│  "vibesrails --setup" (tu exécutes ou Claude suggère)           │
│       │                                                         │
│       ├── Analyse: FastAPI détecté                              │
│       ├── Propose config avec fastapi-pack                      │
│       ├── "Créer?" → Oui                                        │
│       │                                                         │
│       ▼                                                         │
│  CRÉÉ dans ton-projet/:                                         │
│       ├── vibesrails.yaml  (ta config)                          │
│       └── .git/hooks/pre-commit  (le hook)                      │
│                                                                 │
│  Les packs? Déjà installés avec pip. Rien à faire.              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Résumé en une image

```
PyPI (internet)              Ton ordi                    Ton projet
     │                           │                           │
     │  pip install              │                           │
     │─────────────────────────► │                           │
     │                           │                           │
     │                    ~/.local/lib/                      │
     │                    python3.x/                         │
     │                    site-packages/                     │
     │                    vibesrails/                        │
     │                       ├── cli.py                      │
     │                       ├── scanner.py                  │
     │                       └── packs/  ← PACKS ICI         │
     │                           │                           │
     │                           │  vibesrails --setup       │
     │                           │─────────────────────────► │
     │                           │                           │
     │                           │                    mon-projet/
     │                           │                       ├── vibesrails.yaml
     │                           │                       ├── .git/hooks/pre-commit
     │                           │                       └── main.py
```
