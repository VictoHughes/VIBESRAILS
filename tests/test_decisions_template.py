"""Tests for decisions.md template generation and preflight detection."""

import os

from vibesrails.cli_setup import create_decisions_md, get_decisions_template_path, init_config
from vibesrails.preflight import check_decisions_md

# ============================================
# Template file exists
# ============================================


def test_decisions_template_exists():
    """Template file is bundled with the package."""
    template = get_decisions_template_path()
    assert template.exists()
    content = template.read_text()
    assert "Project Decisions" in content
    assert "Stack" in content
    assert "Architecture" in content


# ============================================
# create_decisions_md
# ============================================


def test_create_decisions_md_creates_file(tmp_path):
    """Creates docs/decisions.md from template."""
    result = create_decisions_md(tmp_path)
    assert result is True
    target = tmp_path / "docs" / "decisions.md"
    assert target.exists()
    content = target.read_text()
    assert "Project Decisions" in content


def test_create_decisions_md_creates_docs_dir(tmp_path):
    """Creates docs/ directory if it doesn't exist."""
    assert not (tmp_path / "docs").exists()
    create_decisions_md(tmp_path)
    assert (tmp_path / "docs").is_dir()


def test_create_decisions_md_skips_if_docs_exists(tmp_path):
    """Skips if docs/decisions.md already exists."""
    docs = tmp_path / "docs"
    docs.mkdir()
    existing = docs / "decisions.md"
    existing.write_text("# My existing decisions\n")

    result = create_decisions_md(tmp_path)
    assert result is False
    # Content unchanged
    assert existing.read_text() == "# My existing decisions\n"


def test_create_decisions_md_skips_if_root_exists(tmp_path):
    """Skips if decisions.md exists at project root."""
    (tmp_path / "decisions.md").write_text("# Root decisions\n")

    result = create_decisions_md(tmp_path)
    assert result is False
    assert not (tmp_path / "docs" / "decisions.md").exists()


def test_create_decisions_md_skips_if_vibesrails_dir_exists(tmp_path):
    """Skips if .vibesrails/decisions.md exists."""
    vr_dir = tmp_path / ".vibesrails"
    vr_dir.mkdir()
    (vr_dir / "decisions.md").write_text("# Vibesrails decisions\n")

    result = create_decisions_md(tmp_path)
    assert result is False


# ============================================
# init_config generates decisions.md
# ============================================


def test_init_config_creates_decisions_md(tmp_path):
    """--init also creates docs/decisions.md."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        target = tmp_path / "vibesrails.yaml"
        result = init_config(target)

        assert result is True
        assert target.exists()

        decisions = tmp_path / "docs" / "decisions.md"
        assert decisions.exists()
        assert "Project Decisions" in decisions.read_text()
    finally:
        os.chdir(original_cwd)


def test_init_config_skips_decisions_if_exists(tmp_path):
    """--init doesn't overwrite existing decisions.md."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "decisions.md").write_text("# Custom\n")

        target = tmp_path / "vibesrails.yaml"
        init_config(target)

        assert (docs / "decisions.md").read_text() == "# Custom\n"
    finally:
        os.chdir(original_cwd)


# ============================================
# Preflight — check_decisions_md
# ============================================


def test_preflight_finds_docs_decisions(tmp_path):
    """Preflight finds docs/decisions.md."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "decisions.md").write_text("# D\n")

    result = check_decisions_md(tmp_path)
    assert result.status == "ok"
    assert "docs/decisions.md" in result.message


def test_preflight_finds_root_decisions(tmp_path):
    """Preflight finds decisions.md at root."""
    (tmp_path / "decisions.md").write_text("# D\n")

    result = check_decisions_md(tmp_path)
    assert result.status == "ok"


def test_preflight_finds_vibesrails_decisions(tmp_path):
    """Preflight finds .vibesrails/decisions.md."""
    vr_dir = tmp_path / ".vibesrails"
    vr_dir.mkdir()
    (vr_dir / "decisions.md").write_text("# D\n")

    result = check_decisions_md(tmp_path)
    assert result.status == "ok"
    assert ".vibesrails/decisions.md" in result.message


def test_preflight_warns_if_missing(tmp_path):
    """Preflight warns when no decisions.md found."""
    result = check_decisions_md(tmp_path)
    assert result.status == "warn"
    assert "No decisions.md" in result.message
