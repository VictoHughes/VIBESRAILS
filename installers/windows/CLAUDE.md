# vibesrails Integration

## Auto-Setup

Ce projet utilise vibesrails pour la sécurité du code.

### Configuration automatique

Quand tu travailles sur ce projet:

1. **Avant de modifier du code**, vérifie que `vibesrails.yaml` existe
2. Si non, exécute `vibesrails --setup` pour auto-configurer
3. Le pre-commit hook scannera automatiquement chaque commit

### Commandes utiles

```bash
vibesrails --setup     # Auto-configuration intelligente
vibesrails --show      # Voir patterns actifs
vibesrails --fix       # Auto-corriger patterns simples
vibesrails --all       # Scanner tout le projet
vibesrails --watch     # Mode surveillance continue
```

### Règles à suivre

- Ne jamais commiter de secrets (passwords, API keys, tokens)
- Utiliser `os.environ.get()` pour les credentials
- Si vibesrails bloque, corriger avant de commiter
- Pour les faux positifs: `# vibesrails: ignore`

### Guardian Mode

vibesrails détecte automatiquement Claude Code et active le mode Guardian:
- Vérifications plus strictes
- Warnings traités comme bloquants
- Logging pour analyse

#### Statistiques Guardian

```bash
vibesrails --guardian-stats   # Voir les stats de blocks
```

Les logs sont stockés dans `.vibesrails/guardian.log` (format JSONL):
```json
{"timestamp": "...", "agent": "claude", "file": "...", "pattern_id": "...", "level": "BLOCK"}
```

## Skills disponibles

Si l'utilisateur demande de scanner le code ou configurer la sécurité:

- `/vibesrails-setup` - Configurer vibesrails pour ce projet
- `/vibesrails-scan` - Scanner le code pour les problèmes de sécurité

### Workflow recommandé

1. Au début d'un projet: `vibesrails --setup`
2. Pendant le dev: les commits sont auto-scannés
3. Si BLOCK: corriger le code, pas bypass
4. Si faux positif: `# vibesrails: ignore` avec justification

## Intégration Plans & Tâches

### Plans actifs

Les plans de travail sont dans `docs/plans/`. Au démarrage de session:
1. Vérifie s'il y a un plan actif (le plus récent)
2. Si oui, continue depuis là où tu en étais
3. Utilise TodoWrite pour tracker les étapes du plan

### Synchronisation

```
docs/plans/*.md     → Plan global (brainstorming, design)
TodoWrite           → Tâches granulaires du plan
vibesrails          → Sécurité à chaque commit
```

### Si tu perds le contexte

1. Lis le plan actif: `docs/plans/YYYY-MM-DD-*.md`
2. Vérifie les tâches: `TaskList`
3. Lis le mémo: `.claude/current-task.md`
4. Reprends où tu en étais

### Persister l'état (anti-compaction)

TodoWrite est en mémoire. Pour persister entre sessions/compactions:

```bash
# Écrire le mémo de tâche courante
echo "Task 3/7: Implémenter login OAuth" > .claude/current-task.md
```

Ce fichier est lu au SessionStart et rappelé automatiquement.
