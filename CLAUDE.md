# VibesRails - Development Guidelines

> From KIONOS™ (free tools) - Developed by SM

## Project Overview

VibesRails is a YAML-driven security scanner for Python projects. It catches secrets, security issues, and code quality problems before production.

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

## Development Rules

### 1. Testing (MANDATORY)

Coverage minimum: 80%. Always use `--timeout=60`.

```bash
pytest tests/ --cov=vibesrails --cov-report=term --timeout=60
pytest tests/ --cov=vibesrails --cov-fail-under=80 --timeout=60
```

Use `--cov-report=term` (NOT `term-missing` — too slow). Config in pyproject.toml applies timeout=30 by default.

Naming: `tests/test_<module>.py`, functions: `test_<function>_<scenario>`

### 2. Code Quality

Run before every commit:
```bash
ruff check vibesrails/ --fix
bandit -r vibesrails/ -ll
vibesrails --all
```

### 3. Architecture

Module dependencies (enforced by import-linter):
```
scanner.py    → (no deps on cli, smart_setup)
config.py     → (no deps on cli)
guardian.py   → scanner only
cli.py        → can import all
smart_setup.py → can import all
```

### 4. Commit Standards

Pre-commit checklist:
1. Tests + coverage pass at 80%
2. Lint clean
3. `vibesrails --all` clean
4. No secrets in code

Format: `type(scope): description` — types: feat, fix, refactor, test, docs, chore, style

### 5. Key Commands

```bash
vibesrails --all        # Scan entire project
vibesrails --show       # Show active patterns
vibesrails --setup      # Setup new project
vibesrails --version    # Show version
```

## Security Hooks (4-layer protection)

1. **PreToolUse** — blocks secrets, SQL injection, eval/exec in Write/Edit/Bash BEFORE execution
2. **PostToolUse** — warns after write (full vibesrails scan, non-blocking)
3. **Pre-commit** — blocks commits with issues
4. **ptuh.py** — self-protection (prevents hook deletion, config weakening)

If a hook blocks you: fix the code. Never bypass.

## Session Continuity (persistent plans)

Les todos en mémoire ne survivent pas aux crashes. Toujours persister la marche en avant dans des fichiers.

**Workflow obligatoire :**
1. **Début de session** → écrire/relire le plan dans `docs/plans/YYYY-MM-DD-<sujet>.md`
2. **Pendant le travail** → cocher les étapes terminées dans le fichier plan
3. **Nouvelle session / crash** → relire `docs/plans/` pour reprendre où on en était

Format du fichier plan :
```markdown
# Plan: <sujet>
Date: YYYY-MM-DD

## Étapes
- [x] Étape terminée
- [ ] Étape en cours
- [ ] Étape à faire

## Notes
(décisions prises, blocages, contexte important)
```

Ne jamais se fier uniquement aux todos en mémoire. Le fichier dans `docs/plans/` est la source de vérité.

## Project Tree (persistent snapshot)

Maintenir un fichier `docs/PROJECT_TREE.md` avec l'arbre complet du projet.

**Mise à jour obligatoire :**
- Avant chaque commit/push
- En fin de session

**Commande pour générer :**
```bash
tree -I '__pycache__|*.pyc|.git|*.egg-info|node_modules|.ruff_cache|dist|build|.pytest_cache' --dirsfirst > docs/PROJECT_TREE.md
```

**En début de session** → lire `docs/PROJECT_TREE.md` pour comprendre la structure actuelle du projet.

Ce fichier est commité dans git et fait partie du repo.
