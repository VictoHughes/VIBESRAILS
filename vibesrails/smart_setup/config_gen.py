"""
vibesrails Smart Setup - Config Generation.

Functions to generate vibesrails.yaml and .importlinter configs.
"""

from pathlib import Path

from .detection import ARCHITECTURE_TOOLS, PROJECT_SIGNATURES
from .i18n import LANG


def generate_importlinter_config(project_root: Path, layers: list[str]) -> str:
    """Generate .importlinter config based on detected layers."""
    # Find the root package name
    root_package = None
    for item in project_root.iterdir():
        if item.is_dir() and (item / "__init__.py").exists():
            root_package = item.name
            break

    if not root_package:
        root_package = project_root.name.replace("-", "_")

    lines = [
        "[importlinter]",
        f"root_package = {root_package}",
        "",
    ]

    # Generate contracts based on detected layers
    contract_num = 1

    # Domain independence (if domain layer exists)
    domain_layers = [layer for layer in layers if "domain" in layer.lower() or "core" in layer.lower()]
    if domain_layers:
        for layer in domain_layers:
            layer_module = layer.replace("/", ".")
            lines.extend([
                f"[importlinter:contract:{contract_num}]",
                f"name = {layer} has no external dependencies",
                "type = independence",
                f"modules = {root_package}.{layer_module}",
                "",
            ])
            contract_num += 1

    # Layer contract (if multiple layers)
    if len(layers) >= 2:
        # Sort layers by typical dependency order
        layer_order = ["api", "handler", "controller", "service", "infra", "infrastructure", "adapter", "domain", "core", "model"]
        sorted_layers = sorted(layers, key=lambda layer: next((idx for idx, kw in enumerate(layer_order) if kw in layer.lower()), 99))

        lines.extend([
            f"[importlinter:contract:{contract_num}]",
            "name = Architectural layers",
            "type = layers",
            "layers =",
        ])
        for layer in sorted_layers:
            layer_module = layer.replace("/", ".")
            lines.append(f"    {root_package}.{layer_module}")
        lines.append("")

    return "\n".join(lines)


def generate_config(
    project_types: list[str],
    has_secrets: bool,
    env_files: list[Path],
    existing_configs: dict[str, Path],
) -> str:
    """Generate optimized vibesrails.yaml content."""

    lines = [
        "# vibesrails.yaml - Auto-generated configuration",
        "# Detected project structure and optimized patterns",
        "",
        'version: "1.0"',
        "",
    ]

    # Extends section
    extends = ["@vibesrails/security-pack"]  # Always include security

    for proj_type in project_types:
        pack = PROJECT_SIGNATURES.get(proj_type, {}).get("pack")
        if pack and pack not in extends:
            extends.append(pack)

    if len(extends) == 1:
        lines.append(f'extends: "{extends[0]}"')
    else:
        lines.append("extends:")
        for pack in extends:
            lines.append(f'  - "{pack}"')

    lines.append("")

    # Guardian section (enabled for Claude Code)
    lines.extend([
        "# AI Coding Safety (auto-enabled in Claude Code)",
        "guardian:",
        "  enabled: true",
        "  auto_detect: true",
        "  warnings_as_blocking: false",
        "",
    ])

    # Semgrep integration (enhanced scanning)
    semgrep_preset = "auto"  # Default
    semgrep_additional = []

    # Customize preset based on project type
    for proj_type in project_types:
        if proj_type in ["fastapi", "django", "flask"]:
            semgrep_additional.append(f"p/{proj_type}")

    lines.extend([
        "# Semgrep Integration (AST-based analysis)",
        "# Auto-installs on first run",
        "semgrep:",
        "  enabled: true",
        f'  preset: "{semgrep_preset}"  # auto | strict | minimal',
    ])

    if semgrep_additional:
        lines.append("  additional_rules:")
        for rule in semgrep_additional:
            lines.append(f'    - "{rule}"')

    lines.extend([
        "  exclude_rules: []  # Optional: rules to exclude",
        "",
    ])

    # Project-specific patterns
    if has_secrets or env_files:
        lines.extend([
            "# Project-specific patterns",
            "blocking:",
        ])

        if env_files:
            lines.extend([
                "  - id: env_file_content",
                "    name: \"Env File Content\"",
                '    regex: "^[A-Z_]+=.{10,}"',
                '    scope: [".env*"]',
                '    message: "Ne pas commiter les fichiers .env"',
                "",
            ])

    # Complexity settings
    lines.extend([
        "# Quality settings",
        "complexity:",
        "  max_file_lines: 300",
        "  max_function_lines: 50",
    ])

    return "\n".join(lines)


def generate_config_with_extras(
    project_types: list[str],
    has_secrets: bool,
    env_files: list[Path],
    existing_configs: dict[str, Path],
    extra_patterns: list[dict],
    architecture: dict | None = None,
) -> str:
    """Generate optimized vibesrails.yaml content with extra patterns."""

    lines = [
        "# vibesrails.yaml - Configuration generee par Smart Setup",
        "# Modifiez selon vos besoins",
        "",
        'version: "1.0"',
        "",
    ]

    # Extends section
    extends = ["@vibesrails/security-pack"]  # Always include security

    for proj_type in project_types:
        pack = PROJECT_SIGNATURES.get(proj_type, {}).get("pack")
        if pack and pack not in extends:
            extends.append(pack)

    if len(extends) == 1:
        lines.append(f'extends: "{extends[0]}"')
    else:
        lines.append("extends:")
        for pack in extends:
            lines.append(f'  - "{pack}"')

    lines.append("")

    # Guardian section (enabled for Claude Code)
    lines.extend([
        "# AI Coding Safety (auto-enabled in Claude Code)",
        "guardian:",
        "  enabled: true",
        "  auto_detect: true",
        "  warnings_as_blocking: false",
        "",
    ])

    # Semgrep integration (enhanced scanning)
    semgrep_preset = "auto"  # Default
    semgrep_additional = []

    # Customize preset based on project type
    for proj_type in project_types:
        if proj_type in ["fastapi", "django", "flask"]:
            semgrep_additional.append(f"p/{proj_type}")

    lines.extend([
        "# Semgrep Integration (AST-based analysis)",
        "# Auto-installs on first run",
        "semgrep:",
        "  enabled: true",
        f'  preset: "{semgrep_preset}"  # auto | strict | minimal',
    ])

    if semgrep_additional:
        lines.append("  additional_rules:")
        for rule in semgrep_additional:
            lines.append(f'    - "{rule}"')

    lines.extend([
        "  exclude_rules: []  # Optional: rules to exclude",
        "",
    ])

    # Project-specific patterns (only add if there are actual patterns)
    has_actual_patterns = env_files or extra_patterns
    if has_actual_patterns:
        lines.extend([
            "# Project-specific patterns",
            "blocking:",
        ])

        if env_files:
            env_msg = "Do not commit .env files" if LANG == "en" else "Ne pas commiter les fichiers .env"
            lines.extend([
                "  - id: env_file_content",
                "    name: \"Env File Content\"",
                '    regex: "^[A-Z_]+=.{10,}"',
                '    scope: [".env*"]',
                f'    message: "{env_msg}"',
                "",
            ])

        # Add extra patterns from user
        for pattern in extra_patterns:
            lines.extend([
                f"  - id: {pattern['id']}",
                "    name: \"Custom Pattern\"",
                f'    regex: "{pattern["regex"]}"',
                f'    message: "{pattern["message"]}"',
                "",
            ])

    # Architecture settings (if enabled)
    if architecture and architecture.get("enabled"):
        tool_info = ARCHITECTURE_TOOLS.get(architecture.get("language", "python"), {})
        lines.extend([
            "# Architecture checking (pre-commit)",
            "architecture:",
            "  enabled: true",
            f"  tool: {tool_info.get('tool', 'import-linter')}",
            f"  config: {tool_info.get('config_file', '.importlinter')}",
            "  # Fails silently if tool not installed",
            f"  # Install: {tool_info.get('install', 'pip install import-linter')}",
            "",
        ])

    # Complexity settings
    lines.extend([
        "# Quality settings",
        "complexity:",
        "  max_file_lines: 300",
        "  max_function_lines: 50",
    ])

    return "\n".join(lines)
