"""
vibesrails Smart Setup - Config Generation.

Functions to generate vibesrails.yaml and .importlinter configs.
"""

import logging
from pathlib import Path

from .detection import ARCHITECTURE_TOOLS, PROJECT_SIGNATURES
from .i18n import LANG

logger = logging.getLogger(__name__)


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


def _generate_extends_section(project_types: list[str]) -> list[str]:
    """Generate the extends section lines."""
    lines = []
    extends = ["@vibesrails/security-pack"]

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
    return lines


def _generate_semgrep_section(project_types: list[str]) -> list[str]:
    """Generate the semgrep integration section lines."""
    lines = []
    semgrep_preset = "auto"
    semgrep_additional = []

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
    return lines


def _generate_patterns_section(env_files: list[Path], extra_patterns: list[dict]) -> list[str]:
    """Generate the project-specific patterns section lines."""
    lines = []
    if not env_files and not extra_patterns:
        return lines

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

    for pattern in extra_patterns:
        lines.extend([
            f"  - id: {pattern['id']}",
            "    name: \"Custom Pattern\"",
            f'    regex: "{pattern["regex"]}"',
            f'    message: "{pattern["message"]}"',
            "",
        ])

    return lines


def _generate_architecture_section(architecture: dict | None) -> list[str]:
    """Generate the architecture DIP rules section lines."""
    lines = []
    if not architecture or not architecture.get("enabled"):
        return lines

    layers = [layer.lower() for layer in architecture.get("layers", [])]
    has_domain = any("domain" in layer or "core" in layer for layer in layers)
    has_infra = any("infra" in layer for layer in layers)
    has_app = any("application" in layer or "service" in layer for layer in layers)

    if has_domain and (has_infra or has_app):
        domain_layer = next((layer for layer in architecture.get("layers", []) if "domain" in layer.lower() or "core" in layer.lower()), None)
        root_prefix = domain_layer.split("/")[0] if domain_layer and "/" in domain_layer else ""

        lines.extend([
            "# Architecture - DIP (Dependency Inversion Principle)",
            "architecture:",
        ])

        if has_infra and root_prefix:
            infra_layer = next((layer for layer in architecture.get("layers", []) if "infra" in layer.lower()), "")
            infra_module = infra_layer.replace("/", ".")
            infra_regex = infra_module.replace(".", "\\\\.")
            domain_scope = domain_layer.replace("/", "/") + "/**/*.py"
            lines.extend([
                "  - id: dip_domain_infra",
                '    name: "DIP Violation (Domain → Infrastructure)"',
                f'    regex: "from {infra_regex}"',
                f'    scope: ["{domain_scope}"]',
                '    message: "Domain must not import Infrastructure (Dependency Inversion Principle)"',
                '    level: "BLOCK"',
                "",
            ])

        if has_app and root_prefix:
            app_layer = next((layer for layer in architecture.get("layers", []) if "application" in layer.lower() or "service" in layer.lower()), "")
            app_module = app_layer.replace("/", ".")
            app_regex = app_module.replace(".", "\\\\.")
            domain_scope = domain_layer.replace("/", "/") + "/**/*.py"
            lines.extend([
                "  - id: dip_domain_application",
                '    name: "DIP Violation (Domain → Application)"',
                f'    regex: "from {app_regex}"',
                f'    scope: ["{domain_scope}"]',
                '    message: "Domain must not import Application (Dependency Inversion Principle)"',
                '    level: "BLOCK"',
                "",
            ])

        if not (has_infra or has_app) or not root_prefix:
            lines.append("")

    tool_info = ARCHITECTURE_TOOLS.get(architecture.get("language", "python"), {})
    lines.extend([
        "# Architecture tool (optional, for deeper checks)",
        "# architecture_tool:",
        f"#   tool: {tool_info.get('tool', 'import-linter')}",
        f"#   config: {tool_info.get('config_file', '.importlinter')}",
        f"#   Install: {tool_info.get('install', 'pip install import-linter')}",
        "",
    ])

    return lines


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

    lines.extend(_generate_extends_section(project_types))

    # Guardian section (enabled for Claude Code)
    lines.extend([
        "# AI Coding Safety (auto-enabled in Claude Code)",
        "guardian:",
        "  enabled: true",
        "  auto_detect: true",
        "  warnings_as_blocking: false",
        "",
    ])

    lines.extend(_generate_semgrep_section(project_types))
    lines.extend(_generate_patterns_section(env_files, extra_patterns))
    lines.extend(_generate_architecture_section(architecture))

    # Complexity settings
    lines.extend([
        "# Quality settings",
        "complexity:",
        "  max_file_lines: 300",
        "  max_function_lines: 50",
    ])

    return "\n".join(lines)
