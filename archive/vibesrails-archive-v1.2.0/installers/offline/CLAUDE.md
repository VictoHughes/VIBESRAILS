# vibesrails Integration

Ce projet est protege par vibesrails — scanner de securite automatique.

## Senior Developer Standards

<investigate_before_answering>
ALWAYS read and understand relevant files before proposing edits. Never speculate about code you have not opened. If a file is referenced, you MUST read it first. Never claim something works without running the test. Give grounded, hallucination-free answers only.
</investigate_before_answering>

<no_lazy_work>
Never take shortcuts. Never skip tests. Never produce incomplete implementations. Never say "I'll leave that as an exercise" or "you can add more later." Every piece of code you write must be complete, tested, and production-ready. If you are unsure about something, say "I don't know" rather than guessing. Uncertainty is acceptable; hallucination is not.
</no_lazy_work>

<default_to_action>
Implement changes rather than suggesting them. If intent is unclear, infer the most useful action and proceed. Use tools to discover missing details instead of guessing. Read files before editing. Run tests after writing code.
</default_to_action>

<anti_bypass>
Never disable, remove, skip, or work around vibesrails hooks, pre-commit hooks, or security checks. If vibesrails blocks your code, fix the code — do not bypass the guard. Never use --no-verify, never delete hook files, never modify .claude/hooks.json or vibesrails.yaml to weaken protections.
</anti_bypass>

## Configuration

```bash
vibesrails --setup     # Auto-configuration intelligente
vibesrails --show      # Voir patterns actifs
vibesrails --fix       # Auto-corriger patterns simples
vibesrails --all       # Scanner tout le projet
vibesrails --watch     # Mode surveillance continue
```

## Testing (MANDATORY)

<testing_discipline>
Before ANY commit, verify tests exist and pass. Follow this workflow:

1. CHECK: Does this project have tests? Look for tests/, test_*, *_test.py, pytest.ini, or test commands in package.json/Makefile/pyproject.toml.
2. CREATE: If no tests exist for the code you changed, write them FIRST. Minimum: happy path + edge case + error case per function.
3. RUN: Run tests after every change. Never commit untested code. Never claim "it works" without running the tests.
4. COVERAGE: If a coverage tool is configured, verify coverage does not decrease.

If you write code without tests, you are not done. Tests are not optional.
Test commands to try (in order): pytest, npm test, make test, cargo test, go test ./...
</testing_discipline>

## Rules

- Ne jamais commiter de secrets (passwords, API keys, tokens)
- Utiliser `os.environ.get()` pour les credentials
- Si vibesrails bloque, corriger avant de commiter
- Pour les faux positifs: `# vibesrails: ignore`

## Security Hooks (4-layer protection)

1. **PreToolUse** — blocks secrets, SQL injection, eval/exec in Write/Edit/Bash BEFORE execution
2. **PostToolUse** — warns after write: V1 scanner (regex) + V2 guards AST (DeadCode, Observability, Complexity, Performance, TypeSafety, APIDesign)
3. **Pre-commit** — blocks commits with issues
4. **ptuh.py** — self-protection (prevents hook deletion, config weakening)

If a hook blocks you: fix the code. Never bypass.

## Guardian Mode

vibesrails detecte automatiquement Claude Code et active le mode Guardian:
- Verifications plus strictes
- Warnings traites comme bloquants
- Logging dans `.vibesrails/guardian.log`

## Plans & Taches

Les plans sont dans `docs/plans/`. Au demarrage de session:
1. Verifie s'il y a un plan actif (le plus recent)
2. Continue depuis la ou tu en etais
3. Utilise TodoWrite pour tracker les etapes

Si tu perds le contexte:
1. Lis le plan actif: `docs/plans/YYYY-MM-DD-*.md`
2. Verifie les taches: `TaskList`
3. Lis le memo: `.claude/current-task.md`

## Session Continuity (persistent plans)

Les todos en memoire ne survivent pas aux crashes. Toujours persister la marche en avant dans des fichiers.

**Workflow obligatoire :**
1. **Debut de session** → ecrire/relire le plan dans `docs/plans/YYYY-MM-DD-<sujet>.md`
2. **Pendant le travail** → cocher les etapes terminees dans le fichier plan
3. **Nouvelle session / crash** → relire `docs/plans/` pour reprendre ou on en etait

Format du fichier plan :
```markdown
# Plan: <sujet>
Date: YYYY-MM-DD

## Etapes
- [x] Etape terminee
- [ ] Etape en cours
- [ ] Etape a faire

## Notes
(decisions prises, blocages, contexte important)
```

Ne jamais se fier uniquement aux todos en memoire. Le fichier dans `docs/plans/` est la source de verite.

## Project Tree (persistent snapshot)

Maintenir un fichier `docs/PROJECT_TREE.md` avec l'arbre complet du projet.

**Mise a jour obligatoire :**
- Avant chaque commit/push
- En fin de session

**Commande pour generer :**
```bash
tree -I '__pycache__|*.pyc|.git|*.egg-info|node_modules|.ruff_cache|dist|build|.pytest_cache' --dirsfirst > docs/PROJECT_TREE.md
```

**En debut de session** → lire `docs/PROJECT_TREE.md` pour comprendre la structure actuelle du projet.

Ce fichier est commite dans git et fait partie du repo.
