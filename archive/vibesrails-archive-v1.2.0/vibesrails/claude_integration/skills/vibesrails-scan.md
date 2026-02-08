---
name: vibesrails-scan
description: Scan code for security issues with vibesrails
---

# vibesrails Scan Skill

## Quand utiliser

Utilise ce skill quand l'utilisateur demande:
- "scanne le code"
- "vérifie la sécurité"
- "lance vibesrails"
- "check les patterns"

## Commandes

### Scanner tout le projet

```bash
vibesrails --all
```

### Scanner fichiers staged uniquement

```bash
vibesrails
```

### Voir les patterns actifs

```bash
vibesrails --show
```

## Interpréter les résultats

### BLOCK (Commit bloqué)

```
BLOCK main.py:10
  [hardcoded_secret] Secret hardcodé - utiliser variables d'environnement
```

**Action:** Corriger le code avant de commiter

### WARN (Commit accepté, signalé)

```
WARN utils.py:25
  [none_comparison] Utiliser 'is None'
```

**Action:** Amélioration suggérée, pas bloquant

### PASS

```
vibesrails: PASSED
```

**Action:** Tout va bien, commit autorisé

## Résoudre les problèmes

### Secret hardcodé

```python
# AVANT (bloqué)
api_key = "sk-123456"

# APRÈS (OK)
import os
api_key = os.environ.get("API_KEY")
```

### Faux positif

```python
# Ajouter sur la ligne:
code = "example"  # vibesrails: ignore
```

### Auto-fix disponible

```bash
vibesrails --fix --dry-run  # Prévisualiser
vibesrails --fix            # Appliquer
```
