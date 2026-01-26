"""
vibesrails Smart Setup - Core Setup Logic.

Main smart_setup function and CLI entry point.
"""

import os
from pathlib import Path
from typing import Any

from ..scanner import BLUE, GREEN, NC, RED, YELLOW
from .advanced_patterns import prompt_extra_patterns
from .claude_integration import generate_claude_md, install_claude_hooks
from .config_gen import generate_config_with_extras, generate_importlinter_config
from .detection import (
    ARCHITECTURE_TOOLS,
    PROJECT_SIGNATURES,
    detect_architecture_complexity,
    detect_env_files,
    detect_existing_configs,
    detect_project_type,
    detect_secrets_risk,
)
from .i18n import LANG, msg
from .vibe_mode import prompt_user, prompt_vibe_protections


def smart_setup(
    project_root: Path | None = None,
    dry_run: bool = False,
    interactive: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Run smart setup analysis with user confirmation.

    Args:
        project_root: Project directory (defaults to cwd)
        dry_run: If True, only analyze without creating files
        interactive: If True, ask for user confirmation
        force: If True, overwrite existing config

    Returns:
        Analysis results dict
    """
    if project_root is None:
        project_root = Path.cwd()

    project_root = Path(project_root).resolve()

    print(f"{BLUE}{msg('smart_setup')}{NC}")
    print("=" * 40)
    print(f"{msg('analyzing')}: {project_root.name}/")
    print()

    # Detect project characteristics
    project_types = detect_project_type(project_root)
    existing_configs = detect_existing_configs(project_root)
    has_secrets = detect_secrets_risk(project_root)
    env_files = detect_env_files(project_root)
    arch_info = detect_architecture_complexity(project_root)

    # Report findings
    print(f"{YELLOW}{msg('project_analysis')}{NC}")

    if project_types:
        print(f"  {msg('detected_types')}: {', '.join(project_types)}")
    else:
        print(f"  Type: {msg('generic_python')}")

    packs_to_use = ["@vibesrails/security-pack"]
    for proj_type in project_types:
        pack = PROJECT_SIGNATURES.get(proj_type, {}).get("pack")
        if pack and pack not in packs_to_use:
            packs_to_use.append(pack)

    print(f"  {msg('packs_to_include')}: {', '.join(packs_to_use)}")

    if existing_configs:
        print(f"  {msg('existing_configs')}: {', '.join(existing_configs.keys())}")

    if has_secrets:
        print(f"  {RED}{msg('secret_patterns_detected')}{NC}")

    if env_files:
        print(f"  {msg('env_files')}: {', '.join(f.name for f in env_files)}")

    # Show architecture info
    if arch_info["needs_arch"]:
        print(f"  {BLUE}{msg('arch_detected')}: {len(arch_info['layers'])} {msg('arch_layers')}{NC}")
        for layer in arch_info["layers"][:5]:
            print(f"    • {layer}")
    else:
        print(f"  {msg('arch_simple_project')}")

    # Check if config already exists
    config_path = project_root / "vibesrails.yaml"
    if config_path.exists() and not force:
        print(f"\n{YELLOW}{msg('config_exists')}{NC}")
        if interactive:
            if not prompt_user(msg('overwrite_config'), default="n"):
                print(f"{YELLOW}{msg('setup_cancelled')}{NC}")
                return {"created": False, "reason": "exists"}
        else:
            print(msg('use_force'))
            return {"created": False, "reason": "exists"}

    # Interactive: ask for protections (vibe coder mode by default)
    extra_patterns = []
    if interactive and not dry_run:
        print(f"\n{YELLOW}{msg('config_mode')}{NC}")
        print(f"  1. {msg('mode_simple')}")
        print(f"  2. {msg('mode_advanced')}")
        print(f"  3. {msg('mode_skip')}")

        mode = input(f"\n  {msg('choice')} [1/2/3]: ").strip()

        if mode == "1":
            extra_patterns = prompt_vibe_protections(project_root)
        elif mode == "2":
            extra_patterns = prompt_extra_patterns(project_root)
        # mode 3 or other = skip

    # Architecture checking (offer if complex project)
    architecture_config = None
    if arch_info["needs_arch"] and interactive and not dry_run:
        print()
        if prompt_user(f"{BLUE}{msg('arch_suggest')}{NC}", default="y"):
            architecture_config = {
                "enabled": True,
                "language": arch_info["language"],
                "layers": arch_info["layers"],
            }
            tool_info = ARCHITECTURE_TOOLS.get(arch_info["language"], {})
            print(f"  {GREEN}✓ {msg('arch_will_check')}{NC}")
            print(f"  {msg('arch_install_cmd')}: {tool_info.get('install', 'pip install import-linter')}")

    # Generate config
    config_content = generate_config_with_extras(
        project_types, has_secrets, env_files, existing_configs, extra_patterns,
        architecture=architecture_config
    )

    # Show preview
    print(f"\n{YELLOW}{msg('proposed_config')}{NC}")
    print("-" * 40)
    print(config_content)
    print("-" * 40)

    result = {
        "project_root": str(project_root),
        "project_types": project_types,
        "existing_configs": list(existing_configs.keys()),
        "has_secrets": has_secrets,
        "env_files": [str(f) for f in env_files],
        "extra_patterns": extra_patterns,
        "config_content": config_content,
        "architecture": architecture_config,
    }

    if dry_run:
        dry_run_msg = "(Dry-run mode - no files created)" if LANG == "en" else "(Mode dry-run - aucun fichier cree)"
        print(f"\n{YELLOW}{dry_run_msg}{NC}")
        result["created"] = False
        return result

    # Final confirmation
    if interactive:
        print()
        if not prompt_user(f"{GREEN}{msg('create_config')}{NC}"):
            print(f"{YELLOW}{msg('setup_cancelled')}{NC}")
            result["created"] = False
            return result

    # Create config file
    config_path.write_text(config_content)
    print(f"\n{GREEN}{msg('created')}: vibesrails.yaml{NC}")
    result["created"] = True

    # Create architecture config if enabled
    if architecture_config and architecture_config.get("enabled"):
        lang = architecture_config.get("language", "python")
        if lang == "python":
            importlinter_path = project_root / ".importlinter"
            if not importlinter_path.exists():
                importlinter_content = generate_importlinter_config(
                    project_root, architecture_config.get("layers", [])
                )
                importlinter_path.write_text(importlinter_content)
                print(f"{GREEN}{msg('created')}: .importlinter ({msg('arch_config_created')}){NC}")
        result["architecture_config_created"] = True

    # Install hook (with architecture support)
    from ..cli import install_hook
    install_hook(architecture_enabled=architecture_config is not None)

    # Create or update CLAUDE.md for Claude Code integration
    claude_md_path = project_root / "CLAUDE.md"
    claude_md_content = generate_claude_md()

    if claude_md_path.exists():
        # Append vibesrails section if not already present
        existing_content = claude_md_path.read_text()
        if "vibesrails" not in existing_content.lower():
            claude_md_path.write_text(existing_content + "\n\n" + claude_md_content)
            print(f"{GREEN}{msg('updated')}: CLAUDE.md ({msg('claude_instructions')}){NC}")
        else:
            existing_msg = "CLAUDE.md already has vibesrails instructions" if LANG == "en" else "CLAUDE.md existe deja avec instructions vibesrails"
            print(f"{YELLOW}{existing_msg}{NC}")
    else:
        claude_md_path.write_text(claude_md_content)
        print(f"{GREEN}{msg('created')}: CLAUDE.md ({msg('claude_instructions')}){NC}")

    result["claude_md_created"] = True

    # Offer Claude Code hooks installation
    result["hooks_installed"] = False
    if interactive:
        print()
        if prompt_user(f"{BLUE}{msg('install_hooks')}{NC}", default="y"):
            if install_claude_hooks(project_root):
                print(f"{GREEN}{msg('created')}: .claude/hooks.json ({msg('claude_hooks')}){NC}")
                result["hooks_installed"] = True
            else:
                print(f"{YELLOW}{msg('hooks_not_available')}{NC}")
    else:
        # Non-interactive: install hooks by default
        if install_claude_hooks(project_root):
            print(f"{GREEN}{msg('created')}: .claude/hooks.json ({msg('claude_hooks')}){NC}")
            result["hooks_installed"] = True

    print()
    print(f"{GREEN}{msg('setup_complete')}{NC}")
    print(f"\n{msg('files_created')}:")
    print(f"  - vibesrails.yaml ({msg('config_file')})")
    print(f"  - .git/hooks/pre-commit ({msg('auto_scan')})")
    print(f"  - CLAUDE.md ({msg('claude_instructions')})")
    if result["hooks_installed"]:
        print(f"  - .claude/hooks.json ({msg('claude_hooks')})")
    print(f"\n{msg('next_steps')}:")
    print(f"  1. {msg('commit_normally')}")
    print(f"  2. {msg('scan_all')}: vibesrails --all")
    print(f"\n{BLUE}A.B.H.A.M.H{NC}")

    return result


def run_smart_setup_cli(force: bool = False, dry_run: bool = False) -> bool:
    """CLI entry point for smart setup."""
    try:
        # Check if running in interactive terminal
        interactive = os.isatty(0)  # stdin is a terminal

        result = smart_setup(
            dry_run=dry_run,
            interactive=interactive,
            force=force,
        )
        return result.get("created", False) or dry_run
    except Exception as e:
        print(f"{RED}Error: {e}{NC}")
        return False
