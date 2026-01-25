---
name: vibesrails
description: Validation obligatoire avant toute action de coding. Lit config/vibesrails.yaml pour patterns et exceptions.
---

# vibesrails - Garde-fou contre le vibe coding

## RÈGLE ABSOLUE

**AVANT de modifier du code, tu DOIS :**
1. Lire `config/vibesrails.yaml`
2. Vérifier que tes changements respectent les patterns
3. Annoncer : "✓ vibesrails validé"

## Workflow

```
[Demande utilisateur]
         │
         ▼
[Lire config/vibesrails.yaml] ──→ Comprendre patterns + exceptions
         │
         ▼
[Vérifier le contexte]
  - Est-ce un fichier test ?
  - Est-ce dans une zone d'exception ?
  - Y a-t-il des patterns bloquants ?
         │
         ▼
[Annoncer validation]
  "✓ vibesrails: [fichier] OK - pas de pattern bloquant"
  ou
  "⚠️ vibesrails: [pattern] détecté - correction requise"
         │
         ▼
[Coder seulement après validation]
```

## Source de vérité

**NE PAS mémoriser les patterns** - toujours relire `config/vibesrails.yaml`

Le fichier contient :
- `blocking` : Patterns qui bloquent le commit
- `warning` : Patterns qui génèrent un avertissement
- `exceptions` : Fichiers/dossiers avec permissions spéciales
- `kionos` : Configuration de la formule de sécurité

## Vérification rapide

Avant chaque modification de fichier .py :

```
1. Le fichier est-il dans exceptions? → Vérifier quels patterns sont autorisés
2. Mon code contient-il un pattern bloquant? → Ne pas écrire
3. Mon code contient-il un pattern warning? → Avertir l'utilisateur
```

## Si un pattern est nécessaire

Si le code DOIT utiliser un pattern bloquant :
1. Expliquer POURQUOI c'est nécessaire
2. Proposer une alternative sécurisée si possible
3. Si vraiment nécessaire : ajouter une exception dans vibesrails.yaml

## Test local

L'utilisateur peut tester avec :
```bash
python3 scripts/vibesrails.py --show      # Voir tous les patterns
python3 scripts/vibesrails.py --validate  # Valider le YAML
python3 scripts/vibesrails.py             # Scanner les fichiers stagés
```
