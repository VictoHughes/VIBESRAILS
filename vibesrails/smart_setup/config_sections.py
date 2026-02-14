"""Config section generators — extracted from config_gen.py."""

from pathlib import Path

from .detection import ARCHITECTURE_TOOLS, PROJECT_SIGNATURES
from .i18n import LANG


def generate_extends_section(project_types: list[str]) -> list[str]:
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


def generate_semgrep_section(project_types: list[str]) -> list[str]:
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


def generate_patterns_section(env_files: list[Path], extra_patterns: list[dict]) -> list[str]:
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


def generate_architecture_section(architecture: dict | None) -> list[str]:
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
