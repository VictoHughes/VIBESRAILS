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
import sqlite3
import urllib.request
from datetime import datetime, timedelta, timezone
from difflib import get_close_matches
from pathlib import Path

from storage.migrations import get_db_path, migrate

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
        pkg_lower = package_name.lower().replace("-", "_")

        # requirements.txt
        req_file = self._project_path / "requirements.txt"
        if req_file.is_file():
            for line in req_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                dep = line.split("==")[0].split(">=")[0].split("<=")[0]
                dep = dep.split("[")[0].split(">")[0].split("<")[0].split("~=")[0]
                dep = dep.split("!=")[0].strip()
                if dep.lower().replace("-", "_") == pkg_lower:
                    return True

        # pyproject.toml (simple parse — look for dependencies list)
        pyproject = self._project_path / "pyproject.toml"
        if pyproject.is_file():
            content = pyproject.read_text()
            for line in content.splitlines():
                stripped = line.strip().strip('"').strip("'").strip(",")
                dep = stripped.split("==")[0].split(">=")[0].split("<=")[0]
                dep = dep.split("[")[0].split(">")[0].split("<")[0].split("~=")[0]
                dep = dep.split("!=")[0].strip().strip('"').strip("'")
                if dep.lower().replace("-", "_") == pkg_lower:
                    return True

        return False

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
        bloom_dir = Path.home() / ".vibesrails" / "packages"
        bloom_file = bloom_dir / f"{ecosystem}.bloom"
        if not bloom_file.is_file():
            return None
        try:
            data = bloom_file.read_text()
            packages = {p.strip().lower() for p in data.splitlines() if p.strip()}
            return package_name.lower() in packages
        except OSError:
            return None

    def _check_pypi_api(self, package_name: str) -> bool | None:
        """Query PyPI JSON API. Returns None on network error."""
        url = f"https://pypi.org/pypi/{package_name}/json"
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            logger.debug("PyPI API unreachable for %s", package_name)
            return None

    def _find_similar(self, package_name: str, ecosystem: str) -> list[str]:
        """Find similar package names for slopsquatting detection."""
        known = self._get_known_packages(ecosystem)
        if not known:
            return []
        matches = get_close_matches(
            package_name.lower(), known, n=3, cutoff=0.75
        )
        return [m for m in matches if m != package_name.lower()]

    def _get_known_packages(self, ecosystem: str) -> list[str]:
        """Get known packages from bloom filter or cache."""
        # Try bloom file
        bloom_dir = Path.home() / ".vibesrails" / "packages"
        bloom_file = bloom_dir / f"{ecosystem}.bloom"
        if bloom_file.is_file():
            try:
                data = bloom_file.read_text()
                return [p.strip().lower() for p in data.splitlines() if p.strip()]
            except OSError:
                pass

        # Fallback: packages from cache
        conn = sqlite3.connect(str(self._db_path))
        try:
            cursor = conn.execute(
                "SELECT package_name FROM package_cache "
                "WHERE ecosystem = ? AND exists_flag = 1 LIMIT 10000",
                (ecosystem,),
            )
            return [row[0].lower() for row in cursor.fetchall()]
        finally:
            conn.close()

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
            mod = importlib.import_module(package_name)
        except ImportError:
            return {
                "exists": False,
                "status": "unverifiable",
                "reason": "not_installed",
                "available_symbols": [],
            }

        exists = hasattr(mod, symbol_name)

        # Get public API surface (up to 10 items)
        all_symbols = getattr(mod, "__all__", None)
        if all_symbols is None:
            all_symbols = [s for s in dir(mod) if not s.startswith("_")]
        available = list(all_symbols[:10])

        return {
            "exists": exists,
            "status": "verified" if exists else "not_found",
            "reason": None if exists else f"'{symbol_name}' not in {package_name}",
            "available_symbols": available,
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
            # Stdlib modules don't have package metadata — check if importable
            try:
                importlib.import_module(package_name)
            except ImportError:
                return {
                    "compatible": False,
                    "installed_version": None,
                    "reason": "not_installed",
                }
            # Importable but no metadata (stdlib or namespace package)
            installed_version = "stdlib"

        # If no symbol to check, just confirm installation
        if symbol_name is None:
            return {
                "compatible": True,
                "installed_version": installed_version,
                "reason": None,
            }

        # Check if symbol exists in current version
        try:
            mod = importlib.import_module(package_name)
        except ImportError:
            return {
                "compatible": False,
                "installed_version": installed_version,
                "reason": "import_failed",
            }

        exists = hasattr(mod, symbol_name)
        return {
            "compatible": exists,
            "installed_version": installed_version,
            "reason": (
                None if exists
                else f"'{symbol_name}' not found in {package_name} v{installed_version}"
            ),
        }

    # ── Cache helpers ────────────────────────────────────────────────

    def _get_cache(
        self, package_name: str, ecosystem: str, check_type: str
    ) -> bool | None:
        """Get cached existence result. Returns None if expired or missing."""
        conn = sqlite3.connect(str(self._db_path))
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
        conn = sqlite3.connect(str(self._db_path))
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
