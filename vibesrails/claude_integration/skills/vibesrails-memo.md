---
name: vibesrails-memo
description: Persist current task state to survive compaction
---

# vibesrails Memo Skill

## Quand utiliser

Utilise ce skill quand:
- Tu commences une tâche complexe (brainstorming, plan)
- Avant une compaction probable (conversation longue)
- L'utilisateur demande de "noter où on en est"

## Écrire le mémo

```bash
mkdir -p .claude
cat > .claude/current-task.md << 'EOF'
# Tâche en cours

**Plan:** docs/plans/YYYY-MM-DD-feature.md
**Étape:** 3/7 - Implémenter le composant X
**Contexte:** On a fini Y, maintenant on fait Z

## Prochaines actions
1. [ ] Faire ceci
2. [ ] Faire cela
EOF
```

## Lire le mémo

```bash
cat .claude/current-task.md
```

## Effacer le mémo (tâche terminée)

```bash
rm .claude/current-task.md
```

## Format recommandé

```markdown
# Tâche en cours

**Plan:** [lien vers le plan]
**Étape:** [X/Y] - [description]
**Contexte:** [résumé de ce qui a été fait]

## Prochaines actions
1. [ ] Action immédiate
2. [ ] Action suivante
```

## Automatisation

Le hook SessionStart lit ce fichier et l'affiche automatiquement au démarrage.
