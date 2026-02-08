"""Tests for community pack manager — real filesystem, mock only network."""

from __future__ import annotations

import json

import pytest

from vibesrails.community.pack_manager import (
    OFFICIAL_REGISTRY,
    PACKS_DIR,
    PackManager,
    _github_raw_url,
    _pack_filename,
    _parse_pack_id,
)

VALID_YAML = "blocking:\n  - pattern: secret\nwarning:\n  - pattern: todo\n"
VALID_YAML_BLOCKING_ONLY = "blocking:\n  - pattern: key\n"
VALID_YAML_WARNING_ONLY = "warning:\n  - pattern: fixme\n"
INVALID_YAML_NO_SECTIONS = "metadata:\n  name: test\n"
INVALID_YAML_SYNTAX = ":::\nbad yaml{{{\n"


# ── Parsing helpers (no mock) ────────────────────────────


def test_parse_pack_id_valid():
    assert _parse_pack_id("@alice/rules") == ("alice", "rules")


def test_parse_pack_id_complex_repo():
    assert _parse_pack_id("@org/my-pack-name") == ("org", "my-pack-name")


def test_parse_pack_id_missing_at():
    with pytest.raises(ValueError):
        _parse_pack_id("alice/rules")


def test_parse_pack_id_missing_slash():
    with pytest.raises(ValueError):
        _parse_pack_id("@alicerules")


def test_parse_pack_id_empty_user():
    with pytest.raises(ValueError):
        _parse_pack_id("@/rules")


def test_parse_pack_id_empty_repo():
    with pytest.raises(ValueError):
        _parse_pack_id("@alice/")


def test_pack_filename():
    assert _pack_filename("alice", "rules") == "alice-rules.yaml"


def test_github_raw_url():
    url = _github_raw_url("alice", "rules")
    assert "raw.githubusercontent.com" in url
    assert "alice/rules" in url


# ── validate_pack (no mock) ─────────────────────────────


def test_validate_full_yaml():
    assert PackManager.validate_pack(VALID_YAML) is True


def test_validate_blocking_only():
    assert PackManager.validate_pack(VALID_YAML_BLOCKING_ONLY) is True


def test_validate_warning_only():
    assert PackManager.validate_pack(VALID_YAML_WARNING_ONLY) is True


def test_validate_no_sections():
    assert PackManager.validate_pack(INVALID_YAML_NO_SECTIONS) is False


def test_validate_bad_syntax():
    assert PackManager.validate_pack(INVALID_YAML_SYNTAX) is False


def test_validate_not_a_dict():
    assert PackManager.validate_pack("- item1\n- item2\n") is False


def test_validate_empty_string():
    assert PackManager.validate_pack("") is False


def test_validate_scalar():
    assert PackManager.validate_pack("just a string") is False


# ── install (real filesystem, mock network) ──────────────


def test_install_success(tmp_path):
    mgr = PackManager(fetch_fn=lambda _url: VALID_YAML)
    assert mgr.install("@alice/rules", tmp_path) is True

    pack_file = tmp_path / PACKS_DIR / "alice-rules.yaml"
    assert pack_file.exists()
    assert pack_file.read_text() == VALID_YAML

    meta_file = pack_file.with_suffix(".meta.json")
    assert meta_file.exists()
    meta = json.loads(meta_file.read_text())
    assert meta["id"] == "@alice/rules"
    assert meta["user"] == "alice"
    assert meta["repo"] == "rules"


def test_install_creates_packs_dir(tmp_path):
    mgr = PackManager(fetch_fn=lambda _url: VALID_YAML)
    mgr.install("@alice/rules", tmp_path)
    assert (tmp_path / PACKS_DIR).is_dir()


def test_install_fetch_failure(tmp_path):
    def _fail(_url):
        raise ConnectionError("offline")

    mgr = PackManager(fetch_fn=_fail)
    assert mgr.install("@alice/rules", tmp_path) is False


def test_install_invalid_content(tmp_path):
    mgr = PackManager(fetch_fn=lambda _url: INVALID_YAML_NO_SECTIONS)
    assert mgr.install("@alice/rules", tmp_path) is False


def test_install_invalid_yaml_syntax(tmp_path):
    mgr = PackManager(fetch_fn=lambda _url: INVALID_YAML_SYNTAX)
    assert mgr.install("@alice/rules", tmp_path) is False


def test_install_overwrites_existing(tmp_path):
    mgr = PackManager(fetch_fn=lambda _url: VALID_YAML)
    mgr.install("@alice/rules", tmp_path)
    new_yaml = "blocking:\n  - pattern: updated\n"
    mgr2 = PackManager(fetch_fn=lambda _url: new_yaml)
    mgr2.install("@alice/rules", tmp_path)
    pack_file = tmp_path / PACKS_DIR / "alice-rules.yaml"
    assert pack_file.read_text() == new_yaml


# ── uninstall (real filesystem) ──────────────────────────


def test_uninstall_success(tmp_path):
    mgr = PackManager(fetch_fn=lambda _url: VALID_YAML)
    mgr.install("@alice/rules", tmp_path)
    assert mgr.uninstall("@alice/rules", tmp_path) is True
    assert not (tmp_path / PACKS_DIR / "alice-rules.yaml").exists()
    assert not (tmp_path / PACKS_DIR / "alice-rules.meta.json").exists()


def test_uninstall_not_found(tmp_path):
    mgr = PackManager()
    assert mgr.uninstall("@alice/rules", tmp_path) is False


def test_uninstall_only_removes_target(tmp_path):
    mgr = PackManager(fetch_fn=lambda _url: VALID_YAML)
    mgr.install("@alice/rules", tmp_path)
    mgr.install("@bob/checks", tmp_path)
    mgr.uninstall("@alice/rules", tmp_path)
    assert (tmp_path / PACKS_DIR / "bob-checks.yaml").exists()


# ── list_installed (real filesystem) ─────────────────────


def test_list_installed_empty(tmp_path):
    assert PackManager().list_installed(tmp_path) == []


def test_list_installed_after_install(tmp_path):
    mgr = PackManager(fetch_fn=lambda _url: VALID_YAML)
    mgr.install("@alice/rules", tmp_path)
    mgr.install("@bob/checks", tmp_path)
    installed = mgr.list_installed(tmp_path)
    ids = [p["id"] for p in installed]
    assert "@alice/rules" in ids
    assert "@bob/checks" in ids


def test_list_installed_after_uninstall(tmp_path):
    mgr = PackManager(fetch_fn=lambda _url: VALID_YAML)
    mgr.install("@alice/rules", tmp_path)
    mgr.install("@bob/checks", tmp_path)
    mgr.uninstall("@alice/rules", tmp_path)
    installed = mgr.list_installed(tmp_path)
    ids = [p["id"] for p in installed]
    assert "@alice/rules" not in ids
    assert "@bob/checks" in ids


def test_list_installed_ignores_corrupt_meta(tmp_path):
    mgr = PackManager(fetch_fn=lambda _url: VALID_YAML)
    mgr.install("@alice/rules", tmp_path)
    # Corrupt the meta file
    meta = tmp_path / PACKS_DIR / "alice-rules.meta.json"
    meta.write_text("{{{bad json")
    installed = mgr.list_installed(tmp_path)
    assert len(installed) == 0


# ── list_available ───────────────────────────────────────


def test_list_available():
    mgr = PackManager()
    available = mgr.list_available()
    assert len(available) == len(OFFICIAL_REGISTRY)
    assert available is not OFFICIAL_REGISTRY


def test_list_available_contains_expected_packs():
    available = PackManager().list_available()
    ids = [p["id"] for p in available]
    assert "@vibesrails/security" in ids
    assert "@vibesrails/django" in ids


# ── Real YAML validation of written files ────────────────


def test_installed_file_is_valid_yaml(tmp_path):
    import yaml
    mgr = PackManager(fetch_fn=lambda _url: VALID_YAML)
    mgr.install("@alice/rules", tmp_path)
    pack_file = tmp_path / PACKS_DIR / "alice-rules.yaml"
    data = yaml.safe_load(pack_file.read_text())
    assert "blocking" in data
    assert "warning" in data
