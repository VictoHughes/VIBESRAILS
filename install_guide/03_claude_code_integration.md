# Intégration avec Claude Code

Configuration automatique pour les sessions Claude Code.

## Installation

```bash
pip install vibesrails
```

## Setup automatique

Quand vous ouvrez un projet avec Claude Code:

```bash
vibesrails --setup
```

Le setup va:
1. **Détecter** le type de projet (FastAPI, Django, Flask, CLI)
2. **Analyser** les patterns de secrets existants
3. **Proposer** une configuration optimisée
4. **Demander confirmation** avant de créer
5. **Installer** le hook pre-commit

## Guardian Mode

vibesrails détecte automatiquement Claude Code et active le **Guardian Mode**:

- Variables détectées: `CLAUDE_CODE`, `CURSOR_SESSION`, `COPILOT_AGENT`
- Warnings peuvent devenir BLOCK (configurable)
- Logging des blocks pour analyse

### Configuration Guardian

```yaml
# vibesrails.yaml
guardian:
  enabled: true
  auto_detect: true              # Détecte Claude Code automatiquement
  warnings_as_blocking: false    # true = plus strict
```

## Hooks Claude Code (optionnel)

Ajouter dans `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "test -f vibesrails.yaml || echo '💡 Run: vibesrails --setup'"
      }
    ]
  }
}
```

## Flow de travail

```
┌─────────────────────────────────────────────────────────┐
│  1. Claude Code démarre                                 │
│  2. Hook suggère: "vibesrails --setup"                  │
│  3. Setup interactif crée la config                     │
│  4. Vous codez normalement                              │
│  5. git commit → vibesrails scanne                      │
│  6. BLOCK si problème → vous corrigez                   │
│  7. PASS → commit accepté                               │
└─────────────────────────────────────────────────────────┘
```

## Commandes utiles

| Commande | Description |
|----------|-------------|
| `vibesrails --setup` | Setup interactif |
| `vibesrails --all` | Scanner tout |
| `vibesrails --fix` | Auto-corriger |
| `vibesrails --guardian-stats` | Stats des blocks AI |

## Suppression inline

Si vibesrails bloque un faux positif:

```python
# Ignorer cette ligne
code_ok = True  # vibesrails: ignore

# Ignorer un pattern spécifique
value == None  # vibesrails: ignore [none_comparison]
```
