"""
vibesrails Smart Setup - Core Setup Logic.

Main smart_setup function and CLI entry point.
"""

import logging
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

logger = logging.getLogger(__name__)


def _detect_and_report(project_root: Path) -> dict:
    """Run detection and print findings report. Returns detection results."""
    project_types = detect_project_type(project_root)
    existing_configs = detect_existing_configs(project_root)
    has_secrets = detect_secrets_risk(project_root)
    env_files = detect_env_files(project_root)
    arch_info = detect_architecture_complexity(project_root)

    logger.info(f"{YELLOW}{msg('project_analysis')}{NC}")

    if project_types:
        logger.info(f"  {msg('detected_types')}: {', '.join(project_types)}")
    else:
        logger.info(f"  Type: {msg('generic_python')}")

    packs_to_use = ["@vibesrails/security-pack"]
    for proj_type in project_types:
        pack = PROJECT_SIGNATURES.get(proj_type, {}).get("pack")
        if pack and pack not in packs_to_use:
            packs_to_use.append(pack)

    logger.info(f"  {msg('packs_to_include')}: {', '.join(packs_to_use)}")

    if existing_configs:
        logger.info(f"  {msg('existing_configs')}: {', '.join(existing_configs.keys())}")
    if has_secrets:
        logger.error(f"  {RED}{msg('secret_patterns_detected')}{NC}")
    if env_files:
        logger.info(f"  {msg('env_files')}: {', '.join(f.name for f in env_files)}")

    if arch_info["needs_arch"]:
        logger.info(f"  {BLUE}{msg('arch_detected')}: {len(arch_info['layers'])} {msg('arch_layers')}{NC}")
        for layer in arch_info["layers"][:5]:
            logger.info(f"    • {layer}")
    else:
        logger.info(f"  {msg('arch_simple_project')}")

    return {
        "project_types": project_types,
        "existing_configs": existing_configs,
        "has_secrets": has_secrets,
        "env_files": env_files,
        "arch_info": arch_info,
    }


def _prompt_user_config(project_root: Path, dry_run: bool, interactive: bool, arch_info: dict) -> tuple[list, dict | None]:
    """Prompt for extra patterns and architecture config. Returns (extra_patterns, architecture_config)."""
    extra_patterns = []
    if interactive and not dry_run:
        logger.info(f"\n{YELLOW}{msg('config_mode')}{NC}")
        logger.info(f"  1. {msg('mode_simple')}")
        logger.info(f"  2. {msg('mode_advanced')}")
        logger.info(f"  3. {msg('mode_skip')}")

        mode = input(f"\n  {msg('choice')} [1/2/3]: ").strip()

        if mode == "1":
            extra_patterns = prompt_vibe_protections(project_root)
        elif mode == "2":
            extra_patterns = prompt_extra_patterns(project_root)

    architecture_config = None
    if arch_info["needs_arch"] and interactive and not dry_run:
        logger.info("")
        if prompt_user(f"{BLUE}{msg('arch_suggest')}{NC}", default="y"):
            architecture_config = {
                "enabled": True,
                "language": arch_info["language"],
                "layers": arch_info["layers"],
            }
            tool_info = ARCHITECTURE_TOOLS.get(arch_info["language"], {})
            logger.info(f"  {GREEN}✓ {msg('arch_will_check')}{NC}")
            logger.info(f"  {msg('arch_install_cmd')}: {tool_info.get('install', 'pip install import-linter')}")

    return extra_patterns, architecture_config


def _create_config_files(project_root: Path, config_content: str, architecture_config: dict | None, interactive: bool) -> dict:
    """Create config files on disk. Returns partial result dict."""
    result = {}

    config_path = project_root / "vibesrails.yaml"
    config_path.write_text(config_content)
    logger.info(f"\n{GREEN}{msg('created')}: vibesrails.yaml{NC}")
    result["created"] = True

    # Architecture config
    if architecture_config and architecture_config.get("enabled"):
        lang = architecture_config.get("language", "python")
        if lang == "python":
            importlinter_path = project_root / ".importlinter"
            if not importlinter_path.exists():
                importlinter_content = generate_importlinter_config(
                    project_root, architecture_config.get("layers", [])
                )
                importlinter_path.write_text(importlinter_content)
                logger.info(f"{GREEN}{msg('created')}: .importlinter ({msg('arch_config_created')}){NC}")
        result["architecture_config_created"] = True

    # Install hook
    from ..cli import install_hook
    install_hook(architecture_enabled=architecture_config is not None)

    # CLAUDE.md
    claude_md_path = project_root / "CLAUDE.md"
    claude_md_content = generate_claude_md()

    if claude_md_path.exists():
        existing_content = claude_md_path.read_text()
        if "vibesrails" not in existing_content.lower():
            claude_md_path.write_text(existing_content + "\n\n" + claude_md_content)
            logger.info(f"{GREEN}{msg('updated')}: CLAUDE.md ({msg('claude_instructions')}){NC}")
        else:
            existing_msg = "CLAUDE.md already has vibesrails instructions" if LANG == "en" else "CLAUDE.md existe deja avec instructions vibesrails"
            logger.info(f"{YELLOW}{existing_msg}{NC}")
    else:
        claude_md_path.write_text(claude_md_content)
        logger.info(f"{GREEN}{msg('created')}: CLAUDE.md ({msg('claude_instructions')}){NC}")

    result["claude_md_created"] = True

    # Claude Code hooks
    result["hooks_installed"] = False
    if interactive:
        logger.info("")
        if prompt_user(f"{BLUE}{msg('install_hooks')}{NC}", default="y"):
            if install_claude_hooks(project_root):
                logger.info(f"{GREEN}{msg('created')}: .claude/hooks.json ({msg('claude_hooks')}){NC}")
                result["hooks_installed"] = True
            else:
                logger.info(f"{YELLOW}{msg('hooks_not_available')}{NC}")
    else:
        if install_claude_hooks(project_root):
            logger.info(f"{GREEN}{msg('created')}: .claude/hooks.json ({msg('claude_hooks')}){NC}")
            result["hooks_installed"] = True

    return result


def smart_setup(
    project_root: Path | None = None,
    dry_run: bool = False,
    interactive: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Run smart setup analysis with user confirmation."""
    if project_root is None:
        project_root = Path.cwd()

    project_root = Path(project_root).resolve()

    logger.info(f"{BLUE}{msg('smart_setup')}{NC}")
    logger.info("=" * 40)
    logger.info(f"{msg('analyzing')}: {project_root.name}/")
    logger.info("")

    findings = _detect_and_report(project_root)

    # Check if config already exists
    config_path = project_root / "vibesrails.yaml"
    if config_path.exists() and not force:
        logger.info(f"\n{YELLOW}{msg('config_exists')}{NC}")
        if interactive:
            if not prompt_user(msg('overwrite_config'), default="n"):
                logger.info(f"{YELLOW}{msg('setup_cancelled')}{NC}")
                return {"created": False, "reason": "exists"}
        else:
            logger.info(msg('use_force'))
            return {"created": False, "reason": "exists"}

    extra_patterns, architecture_config = _prompt_user_config(
        project_root, dry_run, interactive, findings["arch_info"]
    )

    # Generate config
    config_content = generate_config_with_extras(
        findings["project_types"], findings["has_secrets"], findings["env_files"],
        findings["existing_configs"], extra_patterns,
        architecture=architecture_config
    )

    # Show preview
    logger.info(f"\n{YELLOW}{msg('proposed_config')}{NC}")
    logger.info("-" * 40)
    logger.info(config_content)
    logger.info("-" * 40)

    result = {
        "project_root": str(project_root),
        "project_types": findings["project_types"],
        "existing_configs": list(findings["existing_configs"].keys()),
        "has_secrets": findings["has_secrets"],
        "env_files": [str(f) for f in findings["env_files"]],
        "extra_patterns": extra_patterns,
        "config_content": config_content,
        "architecture": architecture_config,
    }

    if dry_run:
        dry_run_msg = "(Dry-run mode - no files created)" if LANG == "en" else "(Mode dry-run - aucun fichier cree)"
        logger.info(f"\n{YELLOW}{dry_run_msg}{NC}")
        result["created"] = False
        return result

    if interactive:
        logger.info("")
        if not prompt_user(f"{GREEN}{msg('create_config')}{NC}"):
            logger.info(f"{YELLOW}{msg('setup_cancelled')}{NC}")
            result["created"] = False
            return result

    file_result = _create_config_files(project_root, config_content, architecture_config, interactive)
    result.update(file_result)

    logger.info("")
    logger.info(f"{GREEN}{msg('setup_complete')}{NC}")
    logger.info(f"\n{msg('files_created')}:")
    logger.info(f"  - vibesrails.yaml ({msg('config_file')})")
    logger.info(f"  - .git/hooks/pre-commit ({msg('auto_scan')})")
    logger.info(f"  - CLAUDE.md ({msg('claude_instructions')})")
    if result.get("hooks_installed"):
        logger.info(f"  - .claude/hooks.json ({msg('claude_hooks')})")
    logger.info(f"\n{msg('next_steps')}:")
    logger.info(f"  1. {msg('commit_normally')}")
    logger.info(f"  2. {msg('scan_all')}: vibesrails --all")
    logger.info(f"\n{BLUE}A.B.H.A.M.H{NC}")

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
        logger.error("Smart setup failed: %s", e)
        logger.error(f"{RED}Error: {e}{NC}")
        return False
