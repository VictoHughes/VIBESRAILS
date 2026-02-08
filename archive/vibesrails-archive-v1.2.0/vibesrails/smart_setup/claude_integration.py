"""
vibesrails Smart Setup - Claude Code Integration.

Functions for CLAUDE.md generation and hooks installation.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_package_data_path(relative_path: str) -> Path | None:
    """Get path to a file in the package data."""
    try:
        # Project requires Python 3.10+ (see pyproject.toml)
        import importlib.resources as resources  # nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
        # Use Traversable API directly (no context manager - deprecated in 3.13)
        traversable = resources.files("vibesrails").joinpath(relative_path)
        # Convert to Path - works for file system resources
        resource_path = Path(str(traversable))
        if resource_path.exists():
            return resource_path
    except Exception:
        logger.debug("Could not load package data via importlib.resources")

    # Fallback: relative to this file
    pkg_path = Path(__file__).parent.parent / relative_path
    if pkg_path.exists():
        return pkg_path
    return None


_FALLBACK_CLAUDE_MD = """\
# vibesrails - Instructions Claude Code

## Ce projet utilise vibesrails

vibesrails scanne automatiquement chaque commit pour detecter:
- Secrets hardcodes (API keys, passwords, tokens)
- Injections SQL
- Patterns dangereux
- Violations architecturales

**Powered by Semgrep + VibesRails:**
- Semgrep: Analyse AST (precision)
- VibesRails: Architecture + Guardian Mode (AI safety)

## Regles a suivre

1. **Ne jamais hardcoder de secrets**
   ```python
   # MAUVAIS - vibesrails va bloquer
   api_key = "your-key-here"

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

## Semgrep Integration

vibesrails orchestre Semgrep pour une analyse avancee:
- Auto-installation au premier scan
- Configuration via `vibesrails.yaml` (section `semgrep:`)
- Deduplication intelligente des resultats

## Configuration

Fichier: `vibesrails.yaml`
"""


def generate_claude_md() -> str:
    """Generate CLAUDE.md content for Claude Code integration."""
    template_path = get_package_data_path("claude_integration/CLAUDE.md.template")
    if template_path and template_path.exists():
        return template_path.read_text()
    return _FALLBACK_CLAUDE_MD


def _has_vibesrails_hook(handlers: list[dict]) -> bool:
    """Check if any handler in a list is a vibesrails command."""
    return any("vibesrails" in h.get("command", "") for h in handlers)


def _merge_hooks(existing: dict, source_hooks: dict) -> None:
    """Merge source hooks into existing hooks dict (in-place), skipping vibesrails dupes."""
    for event, handlers in source_hooks.get("hooks", {}).items():
        if event not in existing.get("hooks", {}):
            existing.setdefault("hooks", {})[event] = handlers
        else:
            existing_handlers = existing["hooks"][event]
            has_vr = _has_vibesrails_hook(existing_handlers)
            for handler in handlers:
                is_vr = "vibesrails" in handler.get("command", "")
                if not (is_vr and has_vr):
                    existing_handlers.append(handler)


def install_claude_hooks(project_root: Path) -> bool:
    """Install Claude Code hooks for vibesrails integration."""
    hooks_source = get_package_data_path("claude_integration/hooks.json")
    if not hooks_source or not hooks_source.exists():
        return False

    claude_dir = project_root / ".claude"
    claude_dir.mkdir(exist_ok=True)
    hooks_dest = claude_dir / "hooks.json"
    source_hooks = json.loads(hooks_source.read_text())

    if not hooks_dest.exists():
        hooks_dest.write_text(json.dumps(source_hooks, indent=2))
    else:
        existing = json.loads(hooks_dest.read_text())
        _merge_hooks(existing, source_hooks)
        hooks_dest.write_text(json.dumps(existing, indent=2))

    return True
