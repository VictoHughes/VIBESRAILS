"""
vibesrails Smart Setup - Claude Code Integration.

Functions for CLAUDE.md generation and hooks installation.
"""

import json
from pathlib import Path


def get_package_data_path(relative_path: str) -> Path | None:
    """Get path to a file in the package data."""
    try:
        import importlib.resources as resources
        # Python 3.9+
        with resources.files("vibesrails").joinpath(relative_path) as p:
            if p.exists():
                return Path(p)
    except Exception:
        pass

    # Fallback: relative to this file
    pkg_path = Path(__file__).parent.parent / relative_path
    if pkg_path.exists():
        return pkg_path
    return None


def generate_claude_md() -> str:
    """Generate CLAUDE.md content for Claude Code integration."""
    # Try to load from template
    template_path = get_package_data_path("claude_integration/CLAUDE.md.template")
    if template_path and template_path.exists():
        return template_path.read_text()

    # Fallback to hardcoded content
    return '''# vibesrails - Instructions Claude Code

## Ce projet utilise vibesrails

vibesrails scanne automatiquement chaque commit pour detecter:
- Secrets hardcodes (API keys, passwords, tokens)
- Injections SQL
- Patterns dangereux

## Regles a suivre

1. **Ne jamais hardcoder de secrets**
   ```python
   # MAUVAIS - vibesrails va bloquer
   api_key = "sk-1234567890"  # vibesrails: ignore (example)

   # BON
   import os
   api_key = os.environ.get("API_KEY")
   ```

2. **Si vibesrails bloque un faux positif**
   ```python
   code = "example"  # vibesrails: ignore
   ```

3. **Commandes utiles**
   ```bash
   vibesrails --all    # Scanner tout le projet
   vibesrails --fix    # Auto-corriger les patterns simples
   vibesrails --show   # Voir les patterns actifs
   ```

## Guardian Mode

vibesrails detecte automatiquement Claude Code et active le mode Guardian:
- Verifications plus strictes pour le code genere par AI
- Les warnings peuvent devenir des blocks

## Configuration

Fichier: `vibesrails.yaml`
'''


def install_claude_hooks(project_root: Path) -> bool:
    """Install Claude Code hooks for vibesrails integration."""
    hooks_source = get_package_data_path("claude_integration/hooks.json")
    if not hooks_source or not hooks_source.exists():
        return False

    # Claude Code hooks go in .claude/settings.local.json or project root
    claude_dir = project_root / ".claude"
    claude_dir.mkdir(exist_ok=True)

    hooks_dest = claude_dir / "hooks.json"

    # Load source hooks
    source_hooks = json.loads(hooks_source.read_text())

    # If hooks file exists, merge; otherwise create
    if hooks_dest.exists():
        existing = json.loads(hooks_dest.read_text())
        # Merge hooks
        for event, handlers in source_hooks.get("hooks", {}).items():
            if event not in existing.get("hooks", {}):
                existing.setdefault("hooks", {})[event] = handlers
            else:
                # Check if vibesrails hook already exists
                existing_commands = [h.get("command", "") for h in existing["hooks"][event]]
                for handler in handlers:
                    if "vibesrails" in handler.get("command", "") and \
                       not any("vibesrails" in cmd for cmd in existing_commands):
                        existing["hooks"][event].append(handler)
        hooks_dest.write_text(json.dumps(existing, indent=2))
    else:
        hooks_dest.write_text(json.dumps(source_hooks, indent=2))

    return True
