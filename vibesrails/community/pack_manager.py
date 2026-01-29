"""Community pack manager — install, list, validate, remove packs."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

PACKS_DIR = ".vibesrails/packs"

OFFICIAL_REGISTRY: list[dict[str, str]] = [
    {
        "id": "@vibesrails/security",
        "description": "Core security patterns (secrets, SQL injection).",
    },
    {
        "id": "@vibesrails/python-quality",
        "description": "Python code-quality checks (typing, imports).",
    },
    {
        "id": "@vibesrails/django",
        "description": "Django-specific security and best-practice rules.",
    },
    {
        "id": "@vibesrails/fastapi",
        "description": "FastAPI patterns (auth, validation, CORS).",
    },
    {
        "id": "@vibesrails/docker",
        "description": "Dockerfile and docker-compose best practices.",
    },
]


def _parse_pack_id(pack_id: str) -> tuple[str, str]:
    """Parse ``@user/repo`` into (user, repo).

    Raises ``ValueError`` if the format is invalid.
    """
    if not pack_id.startswith("@") or "/" not in pack_id:
        raise ValueError(
            f"Invalid pack id '{pack_id}'. "
            "Expected format: @user/repo"
        )
    cleaned = pack_id.lstrip("@")
    parts = cleaned.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"Invalid pack id '{pack_id}'. "
            "Expected format: @user/repo"
        )
    return parts[0], parts[1]


def _pack_filename(user: str, repo: str) -> str:
    return f"{user}-{repo}.yaml"


def _github_raw_url(user: str, repo: str) -> str:
    return (
        f"https://raw.githubusercontent.com/"
        f"{user}/{repo}/main/vibesrails.yaml"
    )


class PackManager:
    """Manage community vibesrails packs."""

    # Allow dependency-injection of the fetch function for testing.
    def __init__(
        self,
        fetch_fn: Any | None = None,
    ) -> None:
        self._fetch = fetch_fn or self._default_fetch

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def install(
        self, pack_id: str, project_root: Path
    ) -> bool:
        """Install a pack from GitHub.

        Returns ``True`` on success, ``False`` on failure.
        """
        user, repo = _parse_pack_id(pack_id)
        url = _github_raw_url(user, repo)

        try:
            content = self._fetch(url)
        except Exception:
            return False

        if not self.validate_pack(content):
            return False

        packs_dir = project_root / PACKS_DIR
        packs_dir.mkdir(parents=True, exist_ok=True)

        dest = packs_dir / _pack_filename(user, repo)
        dest.write_text(content, encoding="utf-8")

        # Save metadata alongside the YAML file.
        meta = {
            "id": pack_id,
            "user": user,
            "repo": repo,
        }
        meta_path = dest.with_suffix(".meta.json")
        meta_path.write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        return True

    def uninstall(
        self, pack_id: str, project_root: Path
    ) -> bool:
        """Remove an installed pack.

        Returns ``True`` if removed, ``False`` if not found.
        """
        user, repo = _parse_pack_id(pack_id)
        packs_dir = project_root / PACKS_DIR
        yaml_path = packs_dir / _pack_filename(user, repo)
        meta_path = yaml_path.with_suffix(".meta.json")

        if not yaml_path.exists():
            return False

        yaml_path.unlink()
        if meta_path.exists():
            meta_path.unlink()
        return True

    def list_installed(
        self, project_root: Path
    ) -> list[dict[str, str]]:
        """Return metadata for every installed pack."""
        packs_dir = project_root / PACKS_DIR
        if not packs_dir.is_dir():
            return []

        results: list[dict[str, str]] = []
        for meta_file in sorted(packs_dir.glob("*.meta.json")):
            try:
                data = json.loads(
                    meta_file.read_text(encoding="utf-8")
                )
                results.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def list_available(self) -> list[dict[str, str]]:
        """Return the built-in official pack registry."""
        return list(OFFICIAL_REGISTRY)

    @staticmethod
    def validate_pack(content: str) -> bool:
        """Check that *content* is valid YAML with the right sections.

        A valid pack must parse as a mapping and contain at least one
        of ``blocking`` or ``warning``.
        """
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            return False

        if not isinstance(data, dict):
            return False

        return "blocking" in data or "warning" in data

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _default_fetch(url: str) -> str:  # pragma: no cover
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode("utf-8")
