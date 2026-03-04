"""Tests for vibesrails sync-claude — CLAUDE.md auto-generation."""

import subprocess
from unittest import mock

from vibesrails.sync_claude import (
    check_version_stale,
    generate_cli_commands,
    generate_entry_points,
    generate_mcp_tools,
    generate_overview,
    introspect_cli_commands,
    introspect_entry_points,
    introspect_guards,
    introspect_hooks,
    introspect_mcp_tools,
    introspect_test_count,
    introspect_version,
    merge_sections,
    sync_claude,
)

# ============================================
# introspect_version
# ============================================


def test_introspect_version():
    """Returns current package version."""
    version = introspect_version()
    assert version
    assert "." in version


# ============================================
# introspect_cli_commands
# ============================================


def test_introspect_cli_commands(tmp_path):
    """Parses argparse groups and flags from cli.py."""
    cli_py = tmp_path / "vibesrails" / "cli.py"
    cli_py.parent.mkdir()
    cli_py.write_text(
        'g = parser.add_argument_group("Scanning")\n'
        'g.add_argument("--all", action="store_true", help="Scan all files")\n'
        'g.add_argument("--file", help="Scan specific file")\n'
    )
    groups = introspect_cli_commands(tmp_path)
    assert "Scanning" in groups
    assert len(groups["Scanning"]) == 2
    assert groups["Scanning"][0]["flag"] == "--all"
    assert groups["Scanning"][0]["help"] == "Scan all files"


def test_introspect_cli_commands_no_file(tmp_path):
    """Returns empty dict when cli.py missing."""
    groups = introspect_cli_commands(tmp_path)
    assert groups == {}


# ============================================
# introspect_mcp_tools
# ============================================


def test_introspect_mcp_tools(tmp_path):
    """Parses MCP tool decorators and docstrings."""
    mcp_file = tmp_path / "mcp_tools.py"
    mcp_file.write_text(
        '@mcp.tool()\n'
        'def scan_code(path: str) -> dict:\n'
        '    """Run AST security guards on code."""\n'
        '    pass\n'
    )
    tools = introspect_mcp_tools(tmp_path)
    assert len(tools) == 1
    assert tools[0]["name"] == "scan_code"
    assert "AST" in tools[0]["description"]


def test_introspect_mcp_tools_both_files(tmp_path):
    """Reads from both mcp_tools.py and mcp_tools_ext.py."""
    (tmp_path / "mcp_tools.py").write_text(
        '@mcp.tool()\ndef tool_a() -> dict:\n    """Tool A desc."""\n    pass\n'
    )
    (tmp_path / "mcp_tools_ext.py").write_text(
        '@mcp.tool()\ndef tool_b() -> dict:\n    """Tool B desc."""\n    pass\n'
    )
    tools = introspect_mcp_tools(tmp_path)
    assert len(tools) == 2
    names = {t["name"] for t in tools}
    assert "tool_a" in names
    assert "tool_b" in names


def test_introspect_mcp_tools_no_files(tmp_path):
    """Returns empty list when no MCP files."""
    tools = introspect_mcp_tools(tmp_path)
    assert tools == []


# ============================================
# introspect_guards
# ============================================


def test_introspect_guards(tmp_path):
    """Lists guard modules excluding private helpers."""
    guards_dir = tmp_path / "vibesrails" / "guards_v2"
    guards_dir.mkdir(parents=True)
    (guards_dir / "__init__.py").write_text("")
    (guards_dir / "complexity.py").write_text("")
    (guards_dir / "dead_code.py").write_text("")
    (guards_dir / "_git_helpers.py").write_text("")
    (guards_dir / "pre_deploy_checks.py").write_text("")

    guards = introspect_guards(tmp_path)
    assert "complexity" in guards
    assert "dead_code" in guards
    assert "_git_helpers" not in guards
    assert "pre_deploy_checks" not in guards


def test_introspect_guards_no_dir(tmp_path):
    """Returns empty list when dir missing."""
    assert introspect_guards(tmp_path) == []


# ============================================
# introspect_hooks
# ============================================


def test_introspect_hooks(tmp_path):
    """Lists hook modules."""
    hooks_dir = tmp_path / "vibesrails" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "__init__.py").write_text("")
    (hooks_dir / "pre_tool_use.py").write_text("")
    (hooks_dir / "throttle.py").write_text("")

    hooks = introspect_hooks(tmp_path)
    assert "pre_tool_use" in hooks
    assert "throttle" in hooks
    assert "__init__" not in hooks


# ============================================
# introspect_entry_points
# ============================================


def test_introspect_entry_points(tmp_path):
    """Reads entry points from pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project.scripts]\n'
        'vibesrails = "vibesrails.cli:main"\n'
        'vibesrails-mcp = "mcp_server:main"\n'
        '\n[tool.ruff]\n'
    )
    entries = introspect_entry_points(tmp_path)
    assert len(entries) == 2
    assert entries[0]["command"] == "vibesrails"
    assert entries[0]["module"] == "vibesrails.cli:main"


def test_introspect_entry_points_no_file(tmp_path):
    """Returns empty list when no pyproject.toml."""
    assert introspect_entry_points(tmp_path) == []


# ============================================
# introspect_test_count
# ============================================


def test_introspect_test_count_ok(tmp_path):
    """Parses test count from pytest output."""
    mock_result = mock.Mock(
        returncode=0,
        stdout="2000 tests collected in 1.0s\n",
        stderr="",
    )
    with mock.patch("vibesrails.sync_claude.subprocess.run", return_value=mock_result):
        count = introspect_test_count(tmp_path)
    assert count == 2000


def test_introspect_test_count_fail(tmp_path):
    """Returns None on timeout."""
    with mock.patch(
        "vibesrails.sync_claude.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=60),
    ):
        count = introspect_test_count(tmp_path)
    assert count is None


# ============================================
# generate_overview
# ============================================


def test_generate_overview(tmp_path):
    """Overview includes version and key numbers."""
    # Set up minimal structure
    (tmp_path / "vibesrails" / "guards_v2").mkdir(parents=True)
    (tmp_path / "vibesrails" / "hooks").mkdir(parents=True)

    mock_result = mock.Mock(returncode=0, stdout="500 tests collected\n", stderr="")
    with mock.patch("vibesrails.sync_claude.subprocess.run", return_value=mock_result):
        overview = generate_overview(tmp_path)

    assert "VibesRails" in overview
    assert "500 tests" in overview


# ============================================
# generate_entry_points
# ============================================


def test_generate_entry_points_table(tmp_path):
    """Generates markdown table."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project.scripts]\nvibesrails = "vibesrails.cli:main"\n'
    )
    table = generate_entry_points(tmp_path)
    assert "| Command |" in table
    assert "`vibesrails`" in table
    assert "CLI scanner" in table


# ============================================
# generate_cli_commands
# ============================================


def test_generate_cli_commands(tmp_path):
    """Generates CLI section with groups."""
    cli_py = tmp_path / "vibesrails" / "cli.py"
    cli_py.parent.mkdir(exist_ok=True)
    cli_py.write_text(
        'g = parser.add_argument_group("Scanning")\n'
        'g.add_argument("--all", action="store_true", help="Scan files")\n'
    )
    section = generate_cli_commands(tmp_path)
    assert "## CLI Commands" in section
    assert "### Scanning" in section
    assert "--all" in section


# ============================================
# generate_mcp_tools
# ============================================


def test_generate_mcp_tools_table(tmp_path):
    """Generates MCP tools table."""
    (tmp_path / "mcp_tools.py").write_text(
        '@mcp.tool()\ndef ping() -> dict:\n    """Health check."""\n    pass\n'
    )
    section = generate_mcp_tools(tmp_path)
    assert "## MCP Server" in section
    assert "`ping`" in section


# ============================================
# merge_sections
# ============================================


def test_merge_replaces_auto_sections(tmp_path):
    """Auto sections are replaced, manual content preserved."""
    existing = (
        "# Title\n\n"
        "<!-- AUTO:overview -->\nold overview\n<!-- /AUTO:overview -->\n\n"
        "## Manual Section\nThis stays.\n"
    )
    (tmp_path / "vibesrails" / "guards_v2").mkdir(parents=True)
    (tmp_path / "vibesrails" / "hooks").mkdir(parents=True)

    mock_result = mock.Mock(returncode=0, stdout="100 tests collected\n", stderr="")
    with mock.patch("vibesrails.sync_claude.subprocess.run", return_value=mock_result):
        result = merge_sections(existing, tmp_path)

    assert "VibesRails" in result  # New overview content
    assert "old overview" not in result  # Old content replaced
    assert "This stays." in result  # Manual content preserved


def test_merge_ignores_missing_markers(tmp_path):
    """Content without markers is returned unchanged."""
    existing = "# No markers here\nJust text.\n"
    result = merge_sections(existing, tmp_path)
    assert result == existing


def test_merge_preserves_multiple_manual_sections(tmp_path):
    """Multiple manual sections between auto sections are preserved."""
    existing = (
        "<!-- AUTO:overview -->\nold\n<!-- /AUTO:overview -->\n\n"
        "## Gotchas\nDon't do X.\n\n"
        "<!-- AUTO:cli_commands -->\nold cli\n<!-- /AUTO:cli_commands -->\n\n"
        "## Conventions\nUse Y.\n"
    )
    cli_py = tmp_path / "vibesrails" / "cli.py"
    cli_py.parent.mkdir(parents=True)
    cli_py.write_text("")
    (tmp_path / "vibesrails" / "guards_v2").mkdir(parents=True)
    (tmp_path / "vibesrails" / "hooks").mkdir(parents=True)

    mock_result = mock.Mock(returncode=0, stdout="50 tests collected\n", stderr="")
    with mock.patch("vibesrails.sync_claude.subprocess.run", return_value=mock_result):
        result = merge_sections(existing, tmp_path)

    assert "Don't do X." in result
    assert "Use Y." in result


# ============================================
# check_version_stale
# ============================================


def test_check_version_stale_current(tmp_path):
    """Not stale when version matches."""
    from vibesrails import __version__
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(f"> VibesRails {__version__} — by SM\n")
    assert check_version_stale(claude_md) is False


def test_check_version_stale_old(tmp_path):
    """Stale when version differs."""
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("> VibesRails 0.0.1 — by SM\n")
    assert check_version_stale(claude_md) is True


def test_check_version_stale_no_file(tmp_path):
    """Not stale when file missing."""
    claude_md = tmp_path / "CLAUDE.md"
    assert check_version_stale(claude_md) is False


# ============================================
# sync_claude
# ============================================


def test_sync_claude_dry_run(tmp_path):
    """Dry run returns content without writing."""
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(
        "# Title\n<!-- AUTO:overview -->\nold\n<!-- /AUTO:overview -->\n"
    )
    (tmp_path / "vibesrails" / "guards_v2").mkdir(parents=True)
    (tmp_path / "vibesrails" / "hooks").mkdir(parents=True)

    mock_result = mock.Mock(returncode=0, stdout="100 tests collected\n", stderr="")
    with mock.patch("vibesrails.sync_claude.subprocess.run", return_value=mock_result):
        result = sync_claude(tmp_path, dry_run=True)

    assert "VibesRails" in result
    # File should still have old content
    assert "old" in claude_md.read_text()


def test_sync_claude_writes_file(tmp_path):
    """Non-dry-run writes updated content."""
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(
        "# Title\n<!-- AUTO:overview -->\nold\n<!-- /AUTO:overview -->\n"
    )
    (tmp_path / "vibesrails" / "guards_v2").mkdir(parents=True)
    (tmp_path / "vibesrails" / "hooks").mkdir(parents=True)

    mock_result = mock.Mock(returncode=0, stdout="100 tests collected\n", stderr="")
    with mock.patch("vibesrails.sync_claude.subprocess.run", return_value=mock_result):
        sync_claude(tmp_path, dry_run=False)

    content = claude_md.read_text()
    assert "VibesRails" in content
    assert "old" not in content


def test_sync_claude_no_file(tmp_path):
    """Returns empty string when CLAUDE.md missing."""
    result = sync_claude(tmp_path)
    assert result == ""
