# Installation via pip (Recommandée)

La méthode la plus simple pour la plupart des utilisateurs.

## Installation

```bash
pip install vibesrails
```

## Vérification

```bash
vibesrails --version
```

## Setup dans un projet

```bash
cd mon-projet/
vibesrails --setup
```

Le setup interactif va:
1. Analyser votre projet (FastAPI, Django, etc.)
2. Proposer une configuration optimisée
3. Demander confirmation avant de créer les fichiers
4. Installer le hook pre-commit automatiquement

## Utilisation

```bash
# Scanner les fichiers staged (défaut)
vibesrails

# Scanner tout le projet
vibesrails --all

# Voir les patterns actifs
vibesrails --show

# Auto-corriger les patterns simples
vibesrails --fix
```

## Mise à jour

```bash
pip install --upgrade vibesrails
```

## Désinstallation

```bash
# Retirer du projet
vibesrails --uninstall

# Désinstaller le package
pip uninstall vibesrails
```
