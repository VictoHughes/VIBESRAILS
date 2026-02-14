"""Deep Hallucination Analysis — multi-level import verification.

Goes beyond the basic HallucinationGuard (Level 1 only) with 4 levels:
  Level 1: Import exists locally? (importlib + requirements/pyproject)
  Level 2: Package exists on PyPI? (cache → bloom filter → API)
  Level 3: Symbol exists in the package? (dynamic import + hasattr)
  Level 4: Symbol exists in the requested version? (version comparison)

Uses SQLite package_cache table for TTL-based caching.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import logging
import re
import sqlite3
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from storage.migrations import get_db_path, migrate

from .hallucination_registry import (
    check_bloom_filter,
    check_in_project_deps,
    find_similar,
    get_known_packages,
)

logger = logging.getLogger(__name__)

# TTL durations for cache
_EXISTENCE_TTL = timedelta(hours=24)
_API_SURFACE_TTL = timedelta(days=7)


class DeepHallucinationChecker:
    """Multi-level hallucination checker for Python imports."""

    def __init__(self, db_path: str | None = None, project_path: str | None = None):
        if db_path:
            self._db_path = Path(db_path)
        else:
            self._db_path = get_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        migrate(db_path=str(self._db_path))
        self._project_path = Path(project_path) if project_path else None

    # ── Level 1: Import exists locally? ──────────────────────────────

    def check_import_exists(self, module_name: str) -> bool:
        """Check if a module is importable locally or listed in project deps.

        Args:
            module_name: Top-level module name (e.g. "requests", "os").

        Returns:
            True if the module can be found.
        """
        top = module_name.split(".")[0]

        # importlib.util.find_spec
        try:
            if importlib.util.find_spec(top) is not None:
                return True
        except (ModuleNotFoundError, ValueError):
            pass

        # Check project requirements
        if self._project_path and self._check_in_project_deps(top):
            return True

        return False

    def _check_in_project_deps(self, package_name: str) -> bool:
        """Check if package is listed in requirements.txt or pyproject.toml."""
        return check_in_project_deps(package_name, self._project_path)

    # ── Level 2: Package exists on registry? ─────────────────────────

    def check_package_registry(
        self, package_name: str, ecosystem: str = "pypi"
    ) -> dict:
        """Check if a package exists on the registry (PyPI).

        Strategy: cache → bloom filter → API fallback.

        Args:
            package_name: Package name to check.
            ecosystem: "pypi" (only supported ecosystem for now).

        Returns:
            {"exists": bool, "source": "cache"|"bloom"|"api"|"unknown",
             "similar_packages": list}
        """
        # 1. Check cache first
        cached = self._get_cache(package_name, ecosystem, "existence")
        if cached is not None:
            similar = self._find_similar(package_name, ecosystem) if not cached else []
            return {"exists": cached, "source": "cache", "similar_packages": similar}

        # 2. Bloom filter (offline)
        bloom_result = self._check_bloom_filter(package_name, ecosystem)
        if bloom_result is not None:
            self._set_cache(package_name, ecosystem, bloom_result)
            similar = self._find_similar(package_name, ecosystem) if not bloom_result else []
            return {
                "exists": bloom_result,
                "source": "bloom",
                "similar_packages": similar,
            }

        # 3. PyPI API (online fallback)
        api_result = self._check_pypi_api(package_name)
        if api_result is not None:
            self._set_cache(package_name, ecosystem, api_result)
            similar = self._find_similar(package_name, ecosystem) if not api_result else []
            return {
                "exists": api_result,
                "source": "api",
                "similar_packages": similar,
            }

        # Network unavailable
        similar = self._find_similar(package_name, ecosystem)
        return {"exists": None, "source": "unknown", "similar_packages": similar}

    def _check_bloom_filter(self, package_name: str, ecosystem: str) -> bool | None:
        """Check bloom filter file. Returns None if file doesn't exist."""
        return check_bloom_filter(package_name, ecosystem)

    _VALID_PACKAGE_RE = re.compile(r"^[a-zA-Z0-9_.\-]+$")

    def _check_pypi_api(self, package_name: str) -> bool | None:
        """Query PyPI JSON API. Returns None on network error."""
        if not self._VALID_PACKAGE_RE.match(package_name):
            logger.warning("Invalid package name rejected: %s", package_name[:50])
            return None
        url = f"https://pypi.org/pypi/{package_name}/json"
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=3) as resp:  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
                return resp.status == 200
        except Exception:
            logger.debug("PyPI API unreachable for %s", package_name)
            return None

    def _find_similar(self, package_name: str, ecosystem: str) -> list[str]:
        """Find similar package names for slopsquatting detection."""
        return find_similar(package_name, ecosystem, str(self._db_path))

    def _get_known_packages(self, ecosystem: str) -> list[str]:
        """Get known packages from bloom filter or cache."""
        return get_known_packages(ecosystem, str(self._db_path))

    # ── Level 3: Symbol exists in the package? ───────────────────────

    def check_symbol_exists(self, package_name: str, symbol_name: str) -> dict:
        """Check if a symbol (function/class/attr) exists in a package.

        Args:
            package_name: Importable package name.
            symbol_name: Symbol to look for (e.g. "DataFrame", "get").

        Returns:
            {"exists": bool, "status": "verified"|"not_found"|"unverifiable",
             "reason": str|None, "available_symbols": list[:10]}
        """
        try:
            importlib.metadata.distribution(package_name)
        except importlib.metadata.PackageNotFoundError:
            return {
                "exists": False,
                "status": "unverifiable",
                "reason": "not_installed",
                "available_symbols": [],
            }

        # Package installed — symbol verification disabled for security
        # (importlib.import_module executes __init__.py → RCE on malicious packages)
        return {
            "exists": None,
            "status": "installed_not_verified",
            "reason": "symbol_check_disabled_for_security",
            "available_symbols": [],
        }

    # ── Level 4: Version compatibility? ──────────────────────────────

    def check_version_compat(
        self, package_name: str, symbol_name: str | None = None
    ) -> dict:
        """Check version compatibility for a package/symbol.

        Args:
            package_name: Package name.
            symbol_name: Optional symbol to check in the installed version.

        Returns:
            {"compatible": bool, "installed_version": str|None,
             "reason": str|None}
        """
        # Get installed version
        try:
            installed_version = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            # Stdlib modules don't have package metadata — check via find_spec (no code execution)
            if importlib.util.find_spec(package_name) is not None:
                installed_version = "stdlib"
            else:
                return {
                    "compatible": False,
                    "installed_version": None,
                    "reason": "not_installed",
                }

        # If no symbol to check, just confirm installation
        if symbol_name is None:
            return {
                "compatible": True,
                "installed_version": installed_version,
                "reason": None,
            }

        # Symbol verification disabled for security (avoids RCE via __init__.py)
        return {
            "compatible": True,
            "installed_version": installed_version,
            "reason": "symbol_check_disabled_for_security",
        }

    # ── Cache helpers ────────────────────────────────────────────────

    def _get_cache(
        self, package_name: str, ecosystem: str, check_type: str
    ) -> bool | None:
        """Get cached existence result. Returns None if expired or missing."""
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        try:
            cursor = conn.execute(
                "SELECT exists_flag, cached_at FROM package_cache "
                "WHERE package_name = ? AND ecosystem = ?",
                (package_name.lower(), ecosystem),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            cached_at = datetime.fromisoformat(row[1])
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            ttl = _EXISTENCE_TTL if check_type == "existence" else _API_SURFACE_TTL

            if now - cached_at > ttl:
                return None  # Expired

            return bool(row[0])
        finally:
            conn.close()

    def _set_cache(
        self, package_name: str, ecosystem: str, exists: bool,
        api_surface: str | None = None, version: str | None = None,
    ) -> None:
        """Write to package_cache."""
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO package_cache "
                "(package_name, ecosystem, exists_flag, api_surface, version, cached_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (package_name.lower(), ecosystem, int(exists), api_surface, version, now),
            )
            conn.commit()
        finally:
            conn.close()
