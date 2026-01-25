# Instructions pour Claude Code

## Quand l'utilisateur demande d'installer vibesrails

Si l'utilisateur dit:
- "installe vibesrails"
- "configure vibesrails"
- "ajoute vibesrails"
- "setup vibesrails"
- "met en place la sécurité"

### Étapes à suivre:

```bash
# 1. Vérifier si vibesrails est installé
pip show vibesrails || pip install vibesrails

# 2. Lancer le setup interactif
vibesrails --setup
```

### Le setup va:
1. Analyser le projet (FastAPI, Django, Flask, etc.)
2. Détecter les fichiers .env
3. Proposer une configuration optimisée
4. Demander confirmation à l'utilisateur
5. Créer `vibesrails.yaml`
6. Installer le hook pre-commit

### Après le setup:
- Chaque `git commit` sera scanné automatiquement
- Les secrets hardcodés seront bloqués
- Les patterns dangereux seront détectés

---

## Quand l'utilisateur a un problème avec vibesrails

### "vibesrails bloque mon commit"

```bash
# Voir ce qui bloque
vibesrails --all

# Si c'est un faux positif, ajouter sur la ligne:
# vibesrails: ignore
```

### "Je veux voir les patterns"

```bash
vibesrails --show
```

### "Je veux corriger automatiquement"

```bash
vibesrails --fix --dry-run  # Prévisualiser
vibesrails --fix            # Appliquer
```

### "Je veux désinstaller"

```bash
vibesrails --uninstall
```

---

## Commandes vibesrails

| Commande | Description |
|----------|-------------|
| `vibesrails` | Scanner fichiers staged |
| `vibesrails --all` | Scanner tout le projet |
| `vibesrails --setup` | Configuration interactive |
| `vibesrails --show` | Afficher patterns actifs |
| `vibesrails --fix` | Auto-corriger |
| `vibesrails --fix --dry-run` | Prévisualiser corrections |
| `vibesrails --guardian-stats` | Stats des blocks AI |
| `vibesrails --uninstall` | Retirer du projet |

---

## Exemple de réponse Claude Code

Quand l'utilisateur demande "installe vibesrails":

```
Je vais installer vibesrails pour sécuriser ce projet.

1. Installation du package:
   pip install vibesrails

2. Configuration du projet:
   vibesrails --setup

Le setup va analyser ton projet et proposer une configuration.
Tu pourras valider avant qu'il crée les fichiers.

Après ça, chaque commit sera automatiquement scanné pour:
- Secrets hardcodés (API keys, passwords)
- Injections SQL
- Patterns dangereux

Tu veux que je lance le setup?
```
