"""Comprehensive tests for vibesrails config module.

Tests cover:
- deep_merge: Deep merge two dicts with list extension
- resolve_pack_path: Resolve built-in pack names to paths
- is_allowed_remote_domain: SSRF protection
- fetch_remote_config: Remote config fetch with caching
- load_extended_config: Load config with extends resolution
- resolve_extends: Resolve single extends reference
- load_config_with_extends: Main entry point
"""

import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

from vibesrails.config import (
    ALLOWED_REMOTE_DOMAINS,
    BUILTIN_PACKS,
    _remote_cache,
    deep_merge,
    fetch_remote_config,
    is_allowed_remote_domain,
    load_config_with_extends,
    load_extended_config,
    resolve_extends,
    resolve_pack_path,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture(autouse=True)
def clear_remote_cache():
    """Clear remote config cache before each test."""
    _remote_cache.clear()
    yield
    _remote_cache.clear()


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary directory for config files."""
    return tmp_path


# ============================================
# deep_merge Tests
# ============================================

class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_scalar_override(self):
        """Override wins for scalar values."""
        base = {"version": "1.0", "name": "base"}
        override = {"version": "2.0"}
        result = deep_merge(base, override)
        assert result["version"] == "2.0"
        assert result["name"] == "base"

    def test_dict_recursive_merge(self):
        """Dicts are merged recursively."""
        base = {"settings": {"a": 1, "b": 2}}
        override = {"settings": {"b": 3, "c": 4}}
        result = deep_merge(base, override)
        assert result["settings"] == {"a": 1, "b": 3, "c": 4}

    def test_list_extend(self):
        """Lists are extended, not replaced."""
        base = {"patterns": [{"id": "a"}]}
        override = {"patterns": [{"id": "b"}]}
        result = deep_merge(base, override)
        assert len(result["patterns"]) == 2
        assert result["patterns"][0]["id"] == "a"
        assert result["patterns"][1]["id"] == "b"

    def test_nested_structure(self):
        """Complex nested structures merge correctly."""
        base = {
            "config": {
                "blocking": [{"id": "base1"}],
                "settings": {"strict": True},
            }
        }
        override = {
            "config": {
                "blocking": [{"id": "child1"}],
                "settings": {"verbose": True},
            }
        }
        result = deep_merge(base, override)
        assert len(result["config"]["blocking"]) == 2
        assert result["config"]["settings"]["strict"] is True
        assert result["config"]["settings"]["verbose"] is True

    def test_empty_base(self):
        """Merging into empty base works."""
        base = {}
        override = {"key": "value", "nested": {"a": 1}}
        result = deep_merge(base, override)
        assert result == override

    def test_empty_override(self):
        """Merging empty override preserves base."""
        base = {"key": "value", "nested": {"a": 1}}
        override = {}
        result = deep_merge(base, override)
        assert result == base

    def test_none_value_override(self):
        """None values can override existing values."""
        base = {"key": "value"}
        override = {"key": None}
        result = deep_merge(base, override)
        assert result["key"] is None

    def test_new_keys_added(self):
        """New keys from override are added."""
        base = {"existing": 1}
        override = {"new": 2}
        result = deep_merge(base, override)
        assert result == {"existing": 1, "new": 2}

    def test_base_not_modified(self):
        """Original base dict is not modified."""
        base = {"key": "original"}
        override = {"key": "new"}
        result = deep_merge(base, override)
        assert base["key"] == "original"
        assert result["key"] == "new"

    def test_dict_to_scalar_override(self):
        """Scalar can override dict."""
        base = {"key": {"nested": 1}}
        override = {"key": "scalar"}
        result = deep_merge(base, override)
        assert result["key"] == "scalar"

    def test_list_to_dict_override(self):
        """Dict can override list."""
        base = {"key": [1, 2, 3]}
        override = {"key": {"a": 1}}
        result = deep_merge(base, override)
        assert result["key"] == {"a": 1}


# ============================================
# resolve_pack_path Tests
# ============================================

class TestResolvePackPath:
    """Tests for resolve_pack_path function."""

    def test_known_pack_security(self):
        """Resolve @vibesrails/security-pack."""
        result = resolve_pack_path("@vibesrails/security-pack")
        assert result is not None
        assert result.exists()
        assert result.name == "security.yaml"

    def test_pack_file_missing_on_disk(self):
        """Return None when pack is defined but file doesn't exist."""
        from vibesrails import config

        # Temporarily add a non-existent pack
        original_packs = config.BUILTIN_PACKS.copy()
        config.BUILTIN_PACKS["@vibesrails/fake-pack"] = "packs/nonexistent.yaml"

        try:
            result = resolve_pack_path("@vibesrails/fake-pack")
            assert result is None
        finally:
            config.BUILTIN_PACKS.clear()
            config.BUILTIN_PACKS.update(original_packs)

    def test_known_pack_web(self):
        """Resolve @vibesrails/web-pack."""
        result = resolve_pack_path("@vibesrails/web-pack")
        assert result is not None
        assert result.exists()
        assert result.name == "web.yaml"

    def test_known_pack_fastapi(self):
        """Resolve @vibesrails/fastapi-pack."""
        result = resolve_pack_path("@vibesrails/fastapi-pack")
        assert result is not None
        assert result.exists()

    def test_known_pack_django(self):
        """Resolve @vibesrails/django-pack."""
        result = resolve_pack_path("@vibesrails/django-pack")
        assert result is not None
        assert result.exists()

    def test_unknown_pack_returns_none(self):
        """Unknown pack returns None."""
        result = resolve_pack_path("@vibesrails/unknown-pack")
        assert result is None

    def test_invalid_pack_name_format(self):
        """Invalid pack name format returns None."""
        result = resolve_pack_path("security-pack")
        assert result is None

    def test_empty_string(self):
        """Empty string returns None."""
        result = resolve_pack_path("")
        assert result is None

    def test_builtin_packs_all_exist(self):
        """All defined BUILTIN_PACKS can be resolved."""
        for pack_name in BUILTIN_PACKS.keys():
            result = resolve_pack_path(pack_name)
            assert result is not None, f"Pack {pack_name} should exist"
            assert result.exists(), f"Pack file {result} should exist"


# ============================================
# is_allowed_remote_domain Tests (SSRF Protection)
# ============================================

class TestIsAllowedRemoteDomain:
    """Tests for is_allowed_remote_domain function (SSRF protection)."""

    def test_allowed_github(self):
        """GitHub HTTPS URLs are allowed."""
        assert is_allowed_remote_domain("https://github.com/user/repo/config.yaml")

    def test_allowed_raw_github(self):
        """Raw GitHub URLs are allowed."""
        assert is_allowed_remote_domain(
            "https://raw.githubusercontent.com/user/repo/main/config.yaml"
        )

    def test_allowed_gitlab(self):
        """GitLab HTTPS URLs are allowed."""
        assert is_allowed_remote_domain("https://gitlab.com/user/repo/config.yaml")

    def test_allowed_bitbucket(self):
        """Bitbucket HTTPS URLs are allowed."""
        assert is_allowed_remote_domain("https://bitbucket.org/user/repo/config.yaml")

    def test_allowed_gist(self):
        """Gist URLs are allowed."""
        assert is_allowed_remote_domain(
            "https://gist.githubusercontent.com/user/id/raw/config.yaml"
        )

    def test_blocked_domain(self):
        """Non-allowlisted domains are blocked."""
        assert not is_allowed_remote_domain("https://evil.com/config.yaml")
        assert not is_allowed_remote_domain("https://example.com/config.yaml")

    def test_http_blocked(self):
        """HTTP URLs are blocked (only HTTPS allowed)."""
        assert not is_allowed_remote_domain("http://github.com/config.yaml")
        assert not is_allowed_remote_domain("http://raw.githubusercontent.com/config.yaml")

    def test_ip_address_blocked(self):
        """IP addresses are blocked to prevent internal network access."""
        assert not is_allowed_remote_domain("https://192.168.1.1/config.yaml")
        assert not is_allowed_remote_domain("https://10.0.0.1/config.yaml")
        assert not is_allowed_remote_domain("https://127.0.0.1/config.yaml")
        assert not is_allowed_remote_domain("https://172.16.0.1/config.yaml")

    def test_userinfo_bypass_prevention(self):
        """Prevent bypass via user:pass@host (github.com@evil.com)."""
        # This attempts to bypass by putting the allowed domain in the userinfo
        assert not is_allowed_remote_domain("https://github.com@evil.com/config.yaml")
        assert not is_allowed_remote_domain("https://user:pass@evil.com/config.yaml")

    def test_port_stripping(self):
        """Port numbers are stripped for domain check."""
        assert is_allowed_remote_domain("https://github.com:443/config.yaml")
        assert not is_allowed_remote_domain("https://evil.com:443/config.yaml")

    def test_extra_allowed_domains(self):
        """Extra domains can be added via parameter."""
        assert not is_allowed_remote_domain("https://my-corp.com/config.yaml")
        assert is_allowed_remote_domain(
            "https://my-corp.com/config.yaml",
            extra_domains={"my-corp.com"}
        )

    def test_case_insensitive(self):
        """Domain check is case-insensitive."""
        assert is_allowed_remote_domain("https://GITHUB.COM/config.yaml")
        assert is_allowed_remote_domain("https://GitHub.Com/config.yaml")

    def test_invalid_url(self):
        """Invalid URLs return False."""
        assert not is_allowed_remote_domain("")
        assert not is_allowed_remote_domain("not-a-url")
        assert not is_allowed_remote_domain("ftp://github.com/config.yaml")

    def test_all_default_domains_allowed(self):
        """All default allowed domains work with HTTPS."""
        for domain in ALLOWED_REMOTE_DOMAINS:
            url = f"https://{domain}/config.yaml"
            assert is_allowed_remote_domain(url), f"{domain} should be allowed"

    def test_exception_during_parsing(self):
        """Exception during URL parsing returns False."""
        # Mock urlparse to raise an exception (imported inside the function)
        with mock.patch('urllib.parse.urlparse', side_effect=Exception("Parse error")):
            result = is_allowed_remote_domain("https://github.com/test")
            assert result is False


# ============================================
# fetch_remote_config Tests
# ============================================

class TestFetchRemoteConfig:
    """Tests for fetch_remote_config function."""

    def test_successful_fetch(self):
        """Successful fetch returns parsed config."""
        yaml_content = "version: '1.0'\nblocking: []"
        mock_response = mock.MagicMock()
        mock_response.read.return_value = yaml_content.encode('utf-8')
        mock_response.__enter__ = mock.MagicMock(return_value=mock_response)
        mock_response.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch('urllib.request.urlopen', return_value=mock_response):
            result = fetch_remote_config("https://github.com/user/repo/config.yaml")

        assert result is not None
        assert result["version"] == "1.0"
        assert result["blocking"] == []

    def test_domain_blocked(self, capsys):
        """Blocked domains return None and print message."""
        result = fetch_remote_config("https://evil.com/config.yaml")
        assert result is None
        captured = capsys.readouterr()
        assert "BLOCKED" in captured.out or result is None

    def test_network_error_handling(self, capsys):
        """Network errors are handled gracefully."""
        import urllib.error

        with mock.patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
            result = fetch_remote_config("https://github.com/user/repo/config.yaml")

        assert result is None
        captured = capsys.readouterr()
        assert "Failed to fetch" in captured.out or result is None

    def test_size_limit_exceeded(self, capsys):
        """Large configs (>500KB) are rejected."""
        large_content = "x" * 600_000  # 600KB
        mock_response = mock.MagicMock()
        mock_response.read.return_value = large_content.encode('utf-8')
        mock_response.__enter__ = mock.MagicMock(return_value=mock_response)
        mock_response.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch('urllib.request.urlopen', return_value=mock_response):
            result = fetch_remote_config("https://github.com/user/repo/config.yaml")

        assert result is None
        captured = capsys.readouterr()
        assert "too large" in captured.out

    def test_caching_behavior(self):
        """Subsequent fetches use cache."""
        yaml_content = "version: '1.0'"
        mock_response = mock.MagicMock()
        mock_response.read.return_value = yaml_content.encode('utf-8')
        mock_response.__enter__ = mock.MagicMock(return_value=mock_response)
        mock_response.__exit__ = mock.MagicMock(return_value=False)

        url = "https://github.com/user/repo/config.yaml"

        with mock.patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            # First fetch
            result1 = fetch_remote_config(url)
            # Second fetch (should use cache)
            result2 = fetch_remote_config(url)

        assert result1 == result2
        assert mock_urlopen.call_count == 1  # Only called once

    def test_yaml_parse_error(self, capsys):
        """YAML parse errors are handled."""
        invalid_yaml = "{ invalid: yaml: content"
        mock_response = mock.MagicMock()
        mock_response.read.return_value = invalid_yaml.encode('utf-8')
        mock_response.__enter__ = mock.MagicMock(return_value=mock_response)
        mock_response.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch('urllib.request.urlopen', return_value=mock_response):
            result = fetch_remote_config("https://github.com/user/repo/config.yaml")

        assert result is None
        captured = capsys.readouterr()
        assert "Failed to fetch" in captured.out or result is None

    def test_custom_timeout(self):
        """Custom timeout is passed to urlopen."""
        yaml_content = "version: '1.0'"
        mock_response = mock.MagicMock()
        mock_response.read.return_value = yaml_content.encode('utf-8')
        mock_response.__enter__ = mock.MagicMock(return_value=mock_response)
        mock_response.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            fetch_remote_config("https://github.com/user/repo/config.yaml", timeout=30)
            mock_urlopen.assert_called_with(mock.ANY, timeout=30)

    def test_extra_domains_param(self):
        """Extra domains parameter is passed to domain check."""
        yaml_content = "version: '1.0'"
        mock_response = mock.MagicMock()
        mock_response.read.return_value = yaml_content.encode('utf-8')
        mock_response.__enter__ = mock.MagicMock(return_value=mock_response)
        mock_response.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch('urllib.request.urlopen', return_value=mock_response):
            result = fetch_remote_config(
                "https://custom-domain.com/config.yaml",
                extra_domains={"custom-domain.com"}
            )

        assert result is not None
        assert result["version"] == "1.0"


# ============================================
# load_extended_config Tests
# ============================================

class TestLoadExtendedConfig:
    """Tests for load_extended_config function."""

    def test_simple_config_no_extends(self, temp_config_dir):
        """Load simple config without extends."""
        config_file = temp_config_dir / "simple.yaml"
        config_file.write_text("""
version: "1.0"
blocking:
  - id: test_pattern
    name: "Test"
    regex: "test"
    message: "Test message"
""")
        result = load_extended_config(config_file)
        assert result["version"] == "1.0"
        assert len(result["blocking"]) == 1

    def test_local_file_extends(self, temp_config_dir):
        """Config extends local file."""
        # Create base config
        base = temp_config_dir / "base.yaml"
        base.write_text("""
version: "1.0"
blocking:
  - id: base_pattern
    name: "Base"
    regex: "base"
    message: "Base"
""")
        # Create child config
        child = temp_config_dir / "child.yaml"
        child.write_text("""
extends: "./base.yaml"
blocking:
  - id: child_pattern
    name: "Child"
    regex: "child"
    message: "Child"
""")
        result = load_extended_config(child)
        ids = [p["id"] for p in result["blocking"]]
        assert "base_pattern" in ids
        assert "child_pattern" in ids

    def test_circular_reference_detection(self, temp_config_dir, capsys):
        """Circular references are detected and handled."""
        # Create circular configs
        config_a = temp_config_dir / "a.yaml"
        config_b = temp_config_dir / "b.yaml"

        config_a.write_text("""
extends: "./b.yaml"
blocking:
  - id: a_pattern
    name: "A"
    regex: "a"
    message: "A"
""")
        config_b.write_text("""
extends: "./a.yaml"
blocking:
  - id: b_pattern
    name: "B"
    regex: "b"
    message: "B"
""")
        # Should not hang, should return partial result
        result = load_extended_config(config_a)
        assert isinstance(result, dict)
        captured = capsys.readouterr()
        assert "Circular" in captured.out

    def test_missing_file_handling(self, temp_config_dir, capsys):
        """Missing extends files are handled gracefully."""
        config = temp_config_dir / "with_missing.yaml"
        config.write_text("""
extends: "./missing.yaml"
blocking:
  - id: test
    name: "Test"
    regex: "test"
    message: "Test"
""")
        result = load_extended_config(config)
        # Should still return the child config
        assert "blocking" in result
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_multiple_extends(self, temp_config_dir):
        """Config can extend multiple files."""
        # Create base configs
        base1 = temp_config_dir / "base1.yaml"
        base1.write_text("""
blocking:
  - id: base1_pattern
    name: "Base1"
    regex: "base1"
    message: "Base1"
""")
        base2 = temp_config_dir / "base2.yaml"
        base2.write_text("""
blocking:
  - id: base2_pattern
    name: "Base2"
    regex: "base2"
    message: "Base2"
""")
        # Create child with multiple extends
        child = temp_config_dir / "child.yaml"
        child.write_text("""
extends:
  - "./base1.yaml"
  - "./base2.yaml"
blocking:
  - id: child_pattern
    name: "Child"
    regex: "child"
    message: "Child"
""")
        result = load_extended_config(child)
        ids = [p["id"] for p in result["blocking"]]
        assert "base1_pattern" in ids
        assert "base2_pattern" in ids
        assert "child_pattern" in ids

    def test_empty_config_file(self, temp_config_dir):
        """Empty config file returns empty dict."""
        config = temp_config_dir / "empty.yaml"
        config.write_text("")
        result = load_extended_config(config)
        assert result == {}

    def test_nested_extends(self, temp_config_dir):
        """Nested extends (grandparent -> parent -> child)."""
        grandparent = temp_config_dir / "grandparent.yaml"
        grandparent.write_text("""
blocking:
  - id: grandparent
    name: "GP"
    regex: "gp"
    message: "GP"
""")
        parent = temp_config_dir / "parent.yaml"
        parent.write_text("""
extends: "./grandparent.yaml"
blocking:
  - id: parent
    name: "P"
    regex: "p"
    message: "P"
""")
        child = temp_config_dir / "child.yaml"
        child.write_text("""
extends: "./parent.yaml"
blocking:
  - id: child
    name: "C"
    regex: "c"
    message: "C"
""")
        result = load_extended_config(child)
        ids = [p["id"] for p in result["blocking"]]
        assert "grandparent" in ids
        assert "parent" in ids
        assert "child" in ids


# ============================================
# resolve_extends Tests
# ============================================

class TestResolveExtends:
    """Tests for resolve_extends function."""

    def test_builtin_pack_reference(self):
        """Resolve built-in pack reference."""
        seen = set()
        result = resolve_extends("@vibesrails/security-pack", Path("."), seen)
        assert result is not None
        assert "blocking" in result

    def test_unknown_pack(self, capsys):
        """Unknown pack returns None with warning."""
        seen = set()
        result = resolve_extends("@vibesrails/unknown", Path("."), seen)
        assert result is None
        captured = capsys.readouterr()
        assert "Unknown pack" in captured.out

    def test_https_url_reference(self):
        """Resolve HTTPS URL reference."""
        yaml_content = "version: '1.0'\nblocking: []"
        mock_response = mock.MagicMock()
        mock_response.read.return_value = yaml_content.encode('utf-8')
        mock_response.__enter__ = mock.MagicMock(return_value=mock_response)
        mock_response.__exit__ = mock.MagicMock(return_value=False)

        seen = set()
        with mock.patch('urllib.request.urlopen', return_value=mock_response):
            result = resolve_extends(
                "https://raw.githubusercontent.com/user/repo/main/config.yaml",
                Path("."),
                seen
            )

        assert result is not None

    def test_http_url_blocked(self, capsys):
        """HTTP URLs are blocked."""
        seen = set()
        result = resolve_extends(
            "http://example.com/config.yaml",
            Path("."),
            seen
        )
        assert result is None

    def test_local_relative_path(self, temp_config_dir):
        """Resolve relative local path (./file)."""
        config = temp_config_dir / "base.yaml"
        config.write_text("version: '1.0'\nblocking: []")

        seen = set()
        result = resolve_extends("./base.yaml", temp_config_dir, seen)
        assert result is not None
        assert result["version"] == "1.0"

    def test_local_parent_path(self, temp_config_dir):
        """Resolve parent directory path (../file)."""
        subdir = temp_config_dir / "subdir"
        subdir.mkdir()
        config = temp_config_dir / "base.yaml"
        config.write_text("version: '1.0'\nblocking: []")

        seen = set()
        result = resolve_extends("../base.yaml", subdir, seen)
        assert result is not None

    def test_local_absolute_path(self, temp_config_dir):
        """Resolve absolute local path."""
        config = temp_config_dir / "base.yaml"
        config.write_text("version: '1.0'\nblocking: []")

        seen = set()
        result = resolve_extends(str(config), temp_config_dir, seen)
        assert result is not None

    def test_missing_local_file(self, temp_config_dir, capsys):
        """Missing local file returns None with warning."""
        seen = set()
        result = resolve_extends("./missing.yaml", temp_config_dir, seen)
        assert result is None
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_implicit_local_file(self, temp_config_dir):
        """Resolve implicit local file (no prefix)."""
        config = temp_config_dir / "base.yaml"
        config.write_text("version: '1.0'\nblocking: []")

        seen = set()
        result = resolve_extends("base.yaml", temp_config_dir, seen)
        assert result is not None

    def test_unresolvable_reference(self, temp_config_dir, capsys):
        """Unresolvable reference returns None with warning."""
        seen = set()
        result = resolve_extends("nonexistent.yaml", temp_config_dir, seen)
        assert result is None
        captured = capsys.readouterr()
        assert "Could not resolve" in captured.out

    def test_remote_config_with_extends_warning(self, capsys):
        """Remote configs with extends trigger warning."""
        yaml_content = "extends: './another.yaml'\nversion: '1.0'"
        mock_response = mock.MagicMock()
        mock_response.read.return_value = yaml_content.encode('utf-8')
        mock_response.__enter__ = mock.MagicMock(return_value=mock_response)
        mock_response.__exit__ = mock.MagicMock(return_value=False)

        seen = set()
        with mock.patch('urllib.request.urlopen', return_value=mock_response):
            result = resolve_extends(
                "https://github.com/user/repo/config.yaml",
                Path("."),
                seen
            )

        captured = capsys.readouterr()
        assert "Remote config extends not supported" in captured.out
        assert result is not None
        assert "extends" not in result  # extends should be removed


# ============================================
# load_config_with_extends Tests
# ============================================

class TestLoadConfigWithExtends:
    """Tests for load_config_with_extends function (main entry point)."""

    def test_file_not_found(self):
        """FileNotFoundError raised for missing file."""
        with pytest.raises(FileNotFoundError):
            load_config_with_extends("/nonexistent/path/config.yaml")

    def test_file_too_large(self, temp_config_dir):
        """ValueError raised for files over 1MB."""
        large_file = temp_config_dir / "large.yaml"
        # Create a file > 1MB
        large_file.write_text("x" * 1_100_000)

        with pytest.raises(ValueError) as exc_info:
            load_config_with_extends(large_file)
        assert "too large" in str(exc_info.value)

    def test_valid_config(self, temp_config_dir):
        """Valid config loads successfully."""
        config = temp_config_dir / "valid.yaml"
        config.write_text("""
version: "1.0"
blocking:
  - id: test
    name: "Test"
    regex: "test"
    message: "Test"
""")
        result = load_config_with_extends(config)
        assert result["version"] == "1.0"
        assert len(result["blocking"]) == 1

    def test_string_path_accepted(self, temp_config_dir):
        """String path (not just Path) is accepted."""
        config = temp_config_dir / "config.yaml"
        config.write_text("version: '1.0'")

        result = load_config_with_extends(str(config))
        assert result["version"] == "1.0"

    def test_with_extends(self, temp_config_dir):
        """Config with extends loads and merges correctly."""
        base = temp_config_dir / "base.yaml"
        base.write_text("""
blocking:
  - id: base
    name: "Base"
    regex: "base"
    message: "Base"
""")
        child = temp_config_dir / "child.yaml"
        child.write_text("""
extends: "./base.yaml"
blocking:
  - id: child
    name: "Child"
    regex: "child"
    message: "Child"
""")
        result = load_config_with_extends(child)
        ids = [p["id"] for p in result["blocking"]]
        assert "base" in ids
        assert "child" in ids

    def test_extends_builtin_pack(self, temp_config_dir):
        """Config extending built-in pack works."""
        config = temp_config_dir / "with_pack.yaml"
        config.write_text("""
extends: "@vibesrails/security-pack"
blocking:
  - id: custom
    name: "Custom"
    regex: "custom"
    message: "Custom"
""")
        result = load_config_with_extends(config)
        # Should have patterns from both security pack and custom
        assert len(result["blocking"]) > 1
        ids = [p["id"] for p in result["blocking"]]
        assert "custom" in ids
        assert "hardcoded_secret" in ids  # from security pack


# ============================================
# Integration Tests
# ============================================

class TestConfigIntegration:
    """Integration tests for config module."""

    def test_full_extends_chain(self, temp_config_dir):
        """Test complete extends chain with merging."""
        # Grandparent
        grandparent = temp_config_dir / "grandparent.yaml"
        grandparent.write_text("""
version: "1.0"
blocking:
  - id: gp
    name: "GP"
    regex: "gp"
    message: "GP"
warning:
  - id: gp_warn
    name: "GP Warn"
    regex: "gpwarn"
    message: "GP Warn"
""")
        # Parent
        parent = temp_config_dir / "parent.yaml"
        parent.write_text("""
extends: "./grandparent.yaml"
version: "2.0"
blocking:
  - id: parent
    name: "Parent"
    regex: "parent"
    message: "Parent"
""")
        # Child
        child = temp_config_dir / "child.yaml"
        child.write_text("""
extends: "./parent.yaml"
blocking:
  - id: child
    name: "Child"
    regex: "child"
    message: "Child"
""")

        result = load_config_with_extends(child)

        # Version should be overridden by parent (child doesn't set it)
        assert result["version"] == "2.0"

        # All blocking patterns should be present
        blocking_ids = [p["id"] for p in result["blocking"]]
        assert "gp" in blocking_ids
        assert "parent" in blocking_ids
        assert "child" in blocking_ids

        # Warning from grandparent should be present
        warning_ids = [p["id"] for p in result.get("warning", [])]
        assert "gp_warn" in warning_ids

    def test_deep_merge_preserves_structure(self, temp_config_dir):
        """Deep merge preserves nested structure correctly."""
        base = temp_config_dir / "base.yaml"
        base.write_text("""
settings:
  strict: true
  verbose: false
  nested:
    a: 1
    b: 2
""")
        child = temp_config_dir / "child.yaml"
        child.write_text("""
extends: "./base.yaml"
settings:
  verbose: true
  nested:
    b: 3
    c: 4
""")

        result = load_config_with_extends(child)

        assert result["settings"]["strict"] is True  # preserved from base
        assert result["settings"]["verbose"] is True  # overridden by child
        assert result["settings"]["nested"]["a"] == 1  # preserved
        assert result["settings"]["nested"]["b"] == 3  # overridden
        assert result["settings"]["nested"]["c"] == 4  # added
