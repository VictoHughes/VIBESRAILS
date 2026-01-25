---
name: vibesrails-setup
description: Configure vibesrails security scanner for this project
---

# vibesrails Setup Skill

## Quand utiliser

Utilise ce skill quand l'utilisateur demande:
- "installe vibesrails"
- "configure la sécurité"
- "setup vibesrails"
- "ajoute un scanner de sécurité"

## Étapes

### 1. Vérifier l'installation

```bash
pip show vibesrails || pip install vibesrails
```

### 2. Lancer le setup interactif

```bash
vibesrails --setup
```

Le setup va:
1. Analyser le projet (FastAPI, Django, Flask...)
2. Détecter les secrets existants
3. Proposer une configuration optimisée
4. Demander confirmation à l'utilisateur
5. Créer `vibesrails.yaml`
6. Installer le hook pre-commit
7. Créer `CLAUDE.md` avec les instructions

### 3. Confirmer le succès

```bash
vibesrails --all
```

## Fichiers créés

| Fichier | Description |
|---------|-------------|
| `vibesrails.yaml` | Configuration du scanner |
| `.git/hooks/pre-commit` | Hook de scan automatique |
| `CLAUDE.md` | Instructions pour Claude Code |

## Après le setup

Informer l'utilisateur:
- Chaque commit sera scanné automatiquement
- Les secrets hardcodés seront bloqués
- Utiliser `os.environ.get()` pour les credentials
- `# vibesrails: ignore` pour les faux positifs
