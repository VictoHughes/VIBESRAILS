"""Tests for vibesrails.hooks.inbox."""

from __future__ import annotations

from vibesrails.hooks.inbox import (
    _TEMPLATE_HEADER,
    check_inbox,
    clear_inbox,
    create_inbox,
)


def test_inbox_with_content(tmp_path):
    f = tmp_path / "inbox.md"
    f.write_text(_TEMPLATE_HEADER + "Fix the login bug\n")
    assert check_inbox(f) == "Fix the login bug"


def test_inbox_empty(tmp_path):
    f = tmp_path / "inbox.md"
    f.write_text("")
    assert check_inbox(f) == ""


def test_inbox_missing(tmp_path):
    assert check_inbox(tmp_path / "nope.md") == ""


def test_clear_inbox(tmp_path):
    f = tmp_path / "inbox.md"
    f.write_text("some content\n")
    clear_inbox(f)
    assert f.exists()
    assert f.read_text() == _TEMPLATE_HEADER


def test_inbox_ignores_template_only(tmp_path):
    f = tmp_path / "inbox.md"
    f.write_text(_TEMPLATE_HEADER)
    assert check_inbox(f) == ""


def test_create_inbox(tmp_path):
    f = tmp_path / "sub" / "inbox.md"
    create_inbox(f)
    assert f.exists()
    assert f.read_text() == _TEMPLATE_HEADER
    # Calling again should not overwrite
    f.write_text("modified")
    create_inbox(f)
    assert f.read_text() == "modified"
