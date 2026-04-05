"""Tests for OpenCode plugin adapter."""

from __future__ import annotations

from vibesrails.opencode_adapter import generate_opencode_plugin


def test_generates_js_file(tmp_path):
    path = generate_opencode_plugin(tmp_path)
    assert path.exists()
    assert path.name == "vibesrails.js"


def test_plugin_contains_hooks(tmp_path):
    path = generate_opencode_plugin(tmp_path)
    content = path.read_text()
    assert "tool.execute.before" in content
    assert "tool.execute.after" in content


def test_plugin_references_vibesrails(tmp_path):
    path = generate_opencode_plugin(tmp_path)
    content = path.read_text()
    assert "vibesrails" in content


def test_creates_directory(tmp_path):
    generate_opencode_plugin(tmp_path)
    assert (tmp_path / ".opencode" / "plugins").is_dir()


def test_idempotent(tmp_path):
    generate_opencode_plugin(tmp_path)
    generate_opencode_plugin(tmp_path)
    path = tmp_path / ".opencode" / "plugins" / "vibesrails.js"
    assert path.exists()
