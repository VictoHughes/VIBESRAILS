# Installation depuis les sources

Pour les contributeurs ou pour tester la dernière version.

## Prérequis

- Python 3.10+
- Git

## Installation

```bash
# Cloner le repo
git clone https://github.com/VictoHughes/VIBESRAILS.git
cd VIBESRAILS

# Installer en mode editable
pip install -e .
```

## Vérification

```bash
vibesrails --version
```

## Développement

```bash
# Installer les dépendances de dev
pip install -e ".[dev]"

# Lancer les tests
pytest tests/ -v

# Scanner vibesrails lui-même
vibesrails --all
```

## Structure du projet

```
vibesrails/
├── vibesrails/
│   ├── __init__.py
│   ├── cli.py           # Point d'entrée CLI
│   ├── scanner.py       # Moteur de scan
│   ├── config.py        # Gestion config + extends
│   ├── autofix.py       # Auto-correction
│   ├── guardian.py      # Mode AI Guardian
│   ├── smart_setup.py   # Setup interactif
│   ├── packs/           # Pattern packs
│   │   ├── security.yaml
│   │   ├── web.yaml
│   │   ├── fastapi.yaml
│   │   └── django.yaml
│   └── config/
│       └── default.yaml
├── tests/
├── docs/
└── install_guide/
```

## Contribuer

1. Fork le repo
2. Créer une branche: `git checkout -b feature/ma-feature`
3. Commiter (vibesrails scannera automatiquement)
4. Push et créer une PR
