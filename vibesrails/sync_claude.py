"""sync-claude — Auto-generate factual CLAUDE.md sections from code introspection.

Regenerates sections wrapped in <!-- AUTO:name --> / <!-- /AUTO:name --> markers.
Preserves everything outside these markers (manual sections).
"""

import logging
import re
import subprocess
import sys
from pathlib import Path

from . import __version__

logger = logging.getLogger(__name__)

_SKIP_DIRS = ("__pycache__", ".venv", "venv", ".git", "build", "dist", ".egg")


# ── Introspection ───────────────────────────────────────────────


def introspect_version() -> str:
    """Get current version from package."""
    return __version__


def introspect_cli_commands(root: Path) -> dict[str, list[dict[str, str]]]:
    """Introspect CLI argparse groups and their arguments.

    Returns dict of group_name -> list of {flag, help}.
    """
    cli_path = root / "vibesrails" / "cli.py"
    if not cli_path.exists():
        return {}

    content = cli_path.read_text()
    groups: dict[str, list[dict[str, str]]] = {}
    current_group = None

    # Join continuation lines: if a line has add_argument( but no closing ),
    # accumulate until we find the closing paren.
    raw_lines = content.splitlines()
    logical_lines: list[str] = []
    buf = ""
    for line in raw_lines:
        stripped = line.strip()
        if buf:
            buf += " " + stripped
            if ")" in stripped:
                logical_lines.append(buf)
                buf = ""
        elif "add_argument" in stripped or "add_argument_group" in stripped:
            if stripped.count("(") > stripped.count(")"):
                buf = stripped
            else:
                logical_lines.append(stripped)
        else:
            logical_lines.append(stripped)
    if buf:
        logical_lines.append(buf)

    for line in logical_lines:
        # Detect group: parser.add_argument_group("Name")
        group_match = re.search(r'add_argument_group\(["\'](.+?)["\']', line)
        if group_match:
            current_group = group_match.group(1)
            groups[current_group] = []
            continue

        # Detect argument: add_argument("--flag", ... help="desc")
        # Use backreference to match same quote type for help text
        if current_group and "add_argument" in line:
            flag_match = re.search(r'add_argument\(["\'](-[\w-]+)["\']', line)
            help_match = re.search(r'help=(["\'])(.+?)\1', line)
            if flag_match and help_match:
                groups[current_group].append({
                    "flag": flag_match.group(1),
                    "help": help_match.group(2),
                })

    return groups


def introspect_mcp_tools(root: Path) -> list[dict[str, str]]:
    """Introspect MCP tool names and their docstrings."""
    tools = []
    for filename in ["mcp_tools.py", "mcp_tools_ext.py"]:
        filepath = root / filename
        if not filepath.exists():
            continue

        content = filepath.read_text()
        lines = content.splitlines()

        for i, line in enumerate(lines):
            # Pattern: @mcp.tool() followed by def name(
            if "@mcp.tool()" in line:
                for j in range(i + 1, min(i + 5, len(lines))):
                    def_match = re.search(r"def (\w+)\(", lines[j])
                    if def_match:
                        name = def_match.group(1)
                        # Get first line of docstring
                        doc = ""
                        for k in range(j + 1, min(j + 10, len(lines))):
                            doc_match = re.search(r'"""(.+?)(?:"""|\.)', lines[k])
                            if doc_match:
                                doc = doc_match.group(1).strip()
                                break
                        tools.append({"name": name, "description": doc})
                        break

    return tools


def introspect_guards(root: Path) -> list[str]:
    """List V2 guard module names (excluding private helpers)."""
    guards_dir = root / "vibesrails" / "guards_v2"
    if not guards_dir.exists():
        return []
    guards = []
    for py_file in sorted(guards_dir.glob("*.py")):
        name = py_file.stem
        if name.startswith("_") or name == "__init__":
            continue
        # Skip helper/checks modules
        if name.endswith("_checks") or name.endswith("_detectors") or name.endswith("_patterns"):
            continue
        guards.append(name)
    return guards


def introspect_hooks(root: Path) -> list[str]:
    """List hook module names."""
    hooks_dir = root / "vibesrails" / "hooks"
    if not hooks_dir.exists():
        return []
    hooks = []
    for py_file in sorted(hooks_dir.glob("*.py")):
        name = py_file.stem
        if name.startswith("_") or name == "__init__":
            continue
        hooks.append(name)
    return hooks


def introspect_entry_points(root: Path) -> list[dict[str, str]]:
    """Read entry points from pyproject.toml."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return []

    entries = []
    content = pyproject.read_text()
    in_scripts = False
    for line in content.splitlines():
        if "[project.scripts]" in line:
            in_scripts = True
            continue
        if in_scripts:
            if line.startswith("["):
                break
            match = re.match(r'(\S+)\s*=\s*"(.+)"', line.strip())
            if match:
                entries.append({"command": match.group(1), "module": match.group(2)})

    return entries


def introspect_test_count(root: Path) -> int | None:
    """Get test count via pytest --collect-only."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "--timeout=30"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        combined = result.stdout + "\n" + result.stderr
        for line in reversed(combined.splitlines()):
            match = re.search(r"(\d+)\s+tests?\s", line)
            if match:
                return int(match.group(1))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


# ── Section generators ──────────────────────────────────────────


def generate_overview(root: Path) -> str:
    """Generate the Project Overview section."""
    version = introspect_version()
    mcp_tools = introspect_mcp_tools(root)
    guards = introspect_guards(root)
    hooks = introspect_hooks(root)
    test_count = introspect_test_count(root)

    test_str = str(test_count) if test_count else "?"
    lines = [
        f"> VibesRails {version} — by SM",
        "",
        "## Project Overview",
        "",
        "VibesRails is an engineering methodology enforcer for AI-assisted Python development."
        " It combines phase detection, context adaptation, gate-based progression,"
        " a YAML-driven CLI scanner, an MCP server, and a hook system"
        " that enforces engineering discipline in real-time.",
        "",
        f"**Key numbers:** {test_str} tests | {len(mcp_tools)} MCP tools"
        f" | {len(guards)} V2 guards | {len(hooks)} hook modules",
    ]
    return "\n".join(lines)


def generate_entry_points(root: Path) -> str:
    """Generate the Entry Points table."""
    entries = introspect_entry_points(root)
    lines = [
        "### Entry Points",
        "",
        "| Command | Module | Purpose |",
        "|---------|--------|---------|",
    ]
    purposes = {
        "vibesrails": "CLI scanner",
        "vibesrails-mcp": "MCP server (stdio)",
    }
    for entry in entries:
        purpose = purposes.get(entry["command"], "")
        lines.append(f"| `{entry['command']}` | `{entry['module']}` | {purpose} |")
    return "\n".join(lines)


def generate_cli_commands(root: Path) -> str:
    """Generate the CLI Commands section."""
    groups = introspect_cli_commands(root)
    lines = ["## CLI Commands", ""]

    for group_name, args in groups.items():
        if not args:
            continue
        lines.append(f"### {group_name}")
        lines.append("```bash")
        for arg in args:
            # Pad flag for alignment
            flag = arg["flag"]
            padding = " " * max(1, 22 - len(flag))
            lines.append(f"vibesrails {flag}{padding}# {arg['help']}")
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def generate_mcp_tools(root: Path) -> str:
    """Generate the MCP Server tools table."""
    tools = introspect_mcp_tools(root)
    lines = [
        f"## MCP Server ({len(tools)} Tools)",
        "",
        "| Tool | Description |",
        "|------|-------------|",
    ]
    for tool in tools:
        lines.append(f"| `{tool['name']}` | {tool['description']} |")
    return "\n".join(lines)


# ── Section map ─────────────────────────────────────────────────


_SECTION_GENERATORS = {
    "overview": generate_overview,
    "entry_points": generate_entry_points,
    "cli_commands": generate_cli_commands,
    "mcp_tools": generate_mcp_tools,
}


# ── Merge engine ───────────────────────────────────────────────


def merge_sections(existing: str, root: Path) -> str:
    """Replace AUTO sections in existing CLAUDE.md, preserve everything else."""
    result = existing

    for section_name, generator in _SECTION_GENERATORS.items():
        open_tag = f"<!-- AUTO:{section_name} -->"
        close_tag = f"<!-- /AUTO:{section_name} -->"

        if open_tag in result and close_tag in result:
            new_content = generator(root)
            pattern = re.compile(
                re.escape(open_tag) + r".*?" + re.escape(close_tag),
                re.DOTALL,
            )
            replacement = f"{open_tag}\n{new_content}\n{close_tag}"
            result = pattern.sub(replacement, result)

    return result


def check_version_stale(claude_md_path: Path) -> bool:
    """Check if CLAUDE.md version differs from package version."""
    if not claude_md_path.exists():
        return False
    content = claude_md_path.read_text()
    version_match = re.search(r"VibesRails (\d+\.\d+\.\d+)", content)
    if not version_match:
        return False
    return version_match.group(1) != __version__


def sync_claude(root: Path, dry_run: bool = False) -> str:
    """Sync CLAUDE.md with auto-generated content.

    Returns the new content. Writes to disk unless dry_run=True.
    """
    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        logger.error("CLAUDE.md not found at %s", claude_md)
        return ""

    existing = claude_md.read_text()
    new_content = merge_sections(existing, root)

    if dry_run:
        return new_content

    if new_content != existing:
        claude_md.write_text(new_content)
        logger.info("CLAUDE.md updated with fresh data")
    else:
        logger.info("CLAUDE.md already up to date")

    return new_content
