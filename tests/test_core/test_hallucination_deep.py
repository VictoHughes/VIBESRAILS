"""Tests for core/hallucination_deep.py — Deep Hallucination Checker."""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.hallucination_deep import DeepHallucinationChecker  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────

def _checker(tmp_path: Path, project_path: str | None = None) -> DeepHallucinationChecker:
    db = tmp_path / "test_halluc.db"
    return DeepHallucinationChecker(db_path=str(db), project_path=project_path)


# ── Level 1: check_import_exists ─────────────────────────────────────


class TestLevel1ImportExists:
    """Tests for Level 1 — local import existence."""

    def test_stdlib_module_exists(self, tmp_path):
        c = _checker(tmp_path)
        assert c.check_import_exists("os") is True

    def test_installed_package_exists(self, tmp_path):
        c = _checker(tmp_path)
        assert c.check_import_exists("pytest") is True

    def test_nonexistent_module_not_found(self, tmp_path):
        c = _checker(tmp_path)
        assert c.check_import_exists("fake_nonexistent_pkg_xyz") is False

    def test_dotted_module_checks_top_level(self, tmp_path):
        c = _checker(tmp_path)
        assert c.check_import_exists("os.path") is True

    def test_checks_requirements_txt(self, tmp_path):
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "requirements.txt").write_text("some-weird-pkg-abc>=1.0\n")
        c = _checker(tmp_path, project_path=str(proj))
        assert c.check_import_exists("some_weird_pkg_abc") is True

    def test_checks_pyproject_toml(self, tmp_path):
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\ndependencies = [\n  "my-special-lib>=2.0",\n]\n'
        )
        c = _checker(tmp_path, project_path=str(proj))
        assert c.check_import_exists("my_special_lib") is True


# ── Level 2: check_package_registry ──────────────────────────────────


class TestLevel2PackageRegistry:
    """Tests for Level 2 — PyPI registry verification."""

    def test_existing_package_via_api(self, tmp_path):
        c = _checker(tmp_path)
        with patch("core.hallucination_deep.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: type(
                "Resp", (), {"status": 200}
            )()
            mock_open.return_value.__exit__ = lambda *a: None
            result = c.check_package_registry("requests")
        assert result["exists"] is True
        assert result["source"] == "api"

    def test_nonexistent_package_via_api(self, tmp_path):
        c = _checker(tmp_path)
        with patch("core.hallucination_deep.urllib.request.urlopen") as mock_open:
            mock_open.side_effect = Exception("404")
            result = c.check_package_registry("asdkjhqwelkjh")
        # API error → unknown (None)
        assert result["exists"] is None
        assert result["source"] == "unknown"

    def test_pypi_404_returns_false(self, tmp_path):
        """When PyPI returns non-200, package doesn't exist."""
        c = _checker(tmp_path)
        with patch("core.hallucination_deep.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: type(
                "Resp", (), {"status": 404}
            )()
            mock_open.return_value.__exit__ = lambda *a: None
            result = c.check_package_registry("nonexistent_pkg_zzz")
        assert result["exists"] is False
        assert result["source"] == "api"

    def test_bloom_filter_found(self, tmp_path):
        bloom_dir = Path.home() / ".vibesrails" / "packages"
        bloom_dir.mkdir(parents=True, exist_ok=True)
        bloom_file = bloom_dir / "pypi.bloom"
        original_exists = bloom_file.exists()
        original_content = bloom_file.read_text() if original_exists else None

        try:
            bloom_file.write_text("requests\nnumpy\npandas\n")
            c = _checker(tmp_path)
            result = c.check_package_registry("requests")
            assert result["exists"] is True
            assert result["source"] == "bloom"
        finally:
            if original_content is not None:
                bloom_file.write_text(original_content)
            elif bloom_file.exists():
                bloom_file.unlink()

    def test_slopsquatting_detection(self, tmp_path):
        """Detects similar package names (typosquatting risk)."""
        bloom_dir = Path.home() / ".vibesrails" / "packages"
        bloom_dir.mkdir(parents=True, exist_ok=True)
        bloom_file = bloom_dir / "pypi.bloom"
        original_exists = bloom_file.exists()
        original_content = bloom_file.read_text() if original_exists else None

        try:
            bloom_file.write_text("requests\nnumpy\npandas\n")
            c = _checker(tmp_path)
            # "reqeusts" is not in bloom but "requests" is close
            result = c.check_package_registry("reqeusts")
            assert result["exists"] is False
            assert result["source"] == "bloom"
            assert "requests" in result["similar_packages"]
        finally:
            if original_content is not None:
                bloom_file.write_text(original_content)
            elif bloom_file.exists():
                bloom_file.unlink()

    def test_network_unavailable_returns_unknown(self, tmp_path):
        """When no bloom file and API fails → source is 'unknown'."""
        c = _checker(tmp_path)
        # Ensure no bloom file
        bloom_file = Path.home() / ".vibesrails" / "packages" / "pypi.bloom"
        bloom_existed = bloom_file.exists()

        try:
            if bloom_existed:
                bloom_file.rename(bloom_file.with_suffix(".bloom.bak"))

            with patch("core.hallucination_deep.urllib.request.urlopen") as mock_open:
                mock_open.side_effect = Exception("Network error")
                result = c.check_package_registry("somepackage")
            assert result["source"] == "unknown"
            assert result["exists"] is None
        finally:
            bak = bloom_file.with_suffix(".bloom.bak")
            if bak.exists():
                bak.rename(bloom_file)


# ── Level 3: check_symbol_exists ─────────────────────────────────────


class TestLevel3SymbolExists:
    """Tests for Level 3 — symbol verification."""

    def test_existing_symbol_found(self, tmp_path):
        c = _checker(tmp_path)
        result = c.check_symbol_exists("os", "path")
        assert result["exists"] is True
        assert result["status"] == "verified"

    def test_nonexistent_symbol_not_found(self, tmp_path):
        c = _checker(tmp_path)
        result = c.check_symbol_exists("os", "fake_function_xyz")
        assert result["exists"] is False
        assert result["status"] == "not_found"
        assert len(result["available_symbols"]) > 0

    def test_uninstalled_package_unverifiable(self, tmp_path):
        c = _checker(tmp_path)
        result = c.check_symbol_exists("fake_nonexistent_pkg_xyz", "anything")
        assert result["status"] == "unverifiable"
        assert result["reason"] == "not_installed"


# ── Level 4: check_version_compat ────────────────────────────────────


class TestLevel4VersionCompat:
    """Tests for Level 4 — version compatibility."""

    def test_installed_package_compatible(self, tmp_path):
        c = _checker(tmp_path)
        result = c.check_version_compat("pytest")
        assert result["compatible"] is True
        assert result["installed_version"] is not None

    def test_installed_with_existing_symbol(self, tmp_path):
        c = _checker(tmp_path)
        result = c.check_version_compat("os", symbol_name="path")
        assert result["compatible"] is True

    def test_installed_with_missing_symbol(self, tmp_path):
        c = _checker(tmp_path)
        result = c.check_version_compat("os", symbol_name="fake_func_xyz")
        assert result["compatible"] is False
        assert "fake_func_xyz" in result["reason"]

    def test_uninstalled_package(self, tmp_path):
        c = _checker(tmp_path)
        result = c.check_version_compat("fake_nonexistent_pkg_xyz")
        assert result["compatible"] is False
        assert result["reason"] == "not_installed"


# ── Cache ────────────────────────────────────────────────────────────


class TestCache:
    """Tests for SQLite caching."""

    def test_second_call_uses_cache(self, tmp_path):
        """Second check_package_registry call should use cache, not API."""
        c = _checker(tmp_path)

        call_count = 0

        def mock_urlopen(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = type("Resp", (), {"status": 200})()
            ctx = type("Ctx", (), {
                "__enter__": lambda self: resp,
                "__exit__": lambda *a: None,
            })()
            return ctx

        with patch("core.hallucination_deep.urllib.request.urlopen", side_effect=mock_urlopen):
            # Ensure no bloom file interferes
            bloom_file = Path.home() / ".vibesrails" / "packages" / "pypi.bloom"
            bloom_existed = bloom_file.exists()

            try:
                if bloom_existed:
                    bloom_file.rename(bloom_file.with_suffix(".bloom.bak"))

                r1 = c.check_package_registry("cached_test_pkg")
                r2 = c.check_package_registry("cached_test_pkg")

            finally:
                bak = bloom_file.with_suffix(".bloom.bak")
                if bak.exists():
                    bak.rename(bloom_file)

        assert r1["source"] == "api"
        assert r2["source"] == "cache"
        assert call_count == 1  # Only one API call

    def test_expired_cache_refetches(self, tmp_path):
        """Expired cache entry should trigger a new API call."""
        db = tmp_path / "cache_test.db"
        c = DeepHallucinationChecker(db_path=str(db))

        # Insert an expired cache entry (25 hours ago)
        expired = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT OR REPLACE INTO package_cache "
            "(package_name, ecosystem, exists_flag, api_surface, version, cached_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("expired_pkg", "pypi", 1, None, None, expired),
        )
        conn.commit()
        conn.close()

        def mock_urlopen(*args, **kwargs):
            resp = type("Resp", (), {"status": 200})()
            return type("Ctx", (), {
                "__enter__": lambda self: resp,
                "__exit__": lambda *a: None,
            })()

        bloom_file = Path.home() / ".vibesrails" / "packages" / "pypi.bloom"
        bloom_existed = bloom_file.exists()
        try:
            if bloom_existed:
                bloom_file.rename(bloom_file.with_suffix(".bloom.bak"))

            with patch("core.hallucination_deep.urllib.request.urlopen", side_effect=mock_urlopen):
                result = c.check_package_registry("expired_pkg")

        finally:
            bak = bloom_file.with_suffix(".bloom.bak")
            if bak.exists():
                bak.rename(bloom_file)

        assert result["source"] == "api"  # Re-fetched, not cache
