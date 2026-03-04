"""Community pack manager — install, list, validate, remove packs."""

from __future__ import annotations

import hashlib
import json
import logging
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

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


def _parse_pack_id(pack_id: str) -> tuple[str, str, str]:
    """Parse ``@user/repo`` or ``@user/repo@ref`` into (user, repo, ref).

    *ref* defaults to ``"main"`` when omitted.
    Raises ``ValueError`` if the format is invalid.
    """
    if not pack_id.startswith("@") or "/" not in pack_id:
        raise ValueError(
            f"Invalid pack id '{pack_id}'. "
            "Expected format: @user/repo[@ref]"
        )
    cleaned = pack_id.lstrip("@")
    # Split ref: user/repo@v1.0.0 → ("user/repo", "v1.0.0")
    if "@" in cleaned:
        repo_part, ref = cleaned.split("@", 1)
        if not ref:
            raise ValueError(
                f"Invalid pack id '{pack_id}'. "
                "Empty ref after @"
            )
    else:
        repo_part = cleaned
        ref = "main"
    parts = repo_part.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"Invalid pack id '{pack_id}'. "
            "Expected format: @user/repo[@ref]"
        )
    return parts[0], parts[1], ref


def _pack_filename(user: str, repo: str) -> str:
    return f"{user}-{repo}.yaml"


def _github_raw_url(user: str, repo: str, ref: str = "main") -> str:
    return (
        f"https://raw.githubusercontent.com/"
        f"{user}/{repo}/{ref}/vibesrails.yaml"
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
        user, repo, ref = _parse_pack_id(pack_id)
        url = _github_raw_url(user, repo, ref)

        try:
            content = self._fetch(url)
        except (urllib.error.URLError, OSError) as e:
            logger.error("Failed to fetch pack from %s: %s", url, e)
            return False

        if not self.validate_pack(content):
            return False

        # Check for pattern conflicts with existing packs
        conflicts = self._detect_conflicts(content, user, repo, project_root)
        if conflicts:
            for conflict in conflicts:
                logger.warning("Pattern conflict: %s", conflict)

        packs_dir = project_root / PACKS_DIR
        packs_dir.mkdir(parents=True, exist_ok=True)

        dest = packs_dir / _pack_filename(user, repo)
        dest.write_text(content, encoding="utf-8")

        # Compute SHA256 checksum
        content_hash = hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

        # Save metadata alongside the YAML file.
        meta = {
            "id": pack_id,
            "user": user,
            "repo": repo,
            "ref": ref,
            "sha256": content_hash,
        }
        meta_path = dest.with_suffix(".meta.json")
        meta_path.write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

        # Update lockfile
        self._update_lockfile(
            project_root, user, repo, ref, content_hash,
        )
        return True

    def uninstall(
        self, pack_id: str, project_root: Path
    ) -> bool:
        """Remove an installed pack.

        Returns ``True`` if removed, ``False`` if not found.
        """
        user, repo, _ref = _parse_pack_id(pack_id)
        packs_dir = project_root / PACKS_DIR
        yaml_path = packs_dir / _pack_filename(user, repo)
        meta_path = yaml_path.with_suffix(".meta.json")

        if not yaml_path.exists():
            return False

        yaml_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

        # Remove from lockfile
        self._remove_from_lockfile(project_root, user, repo)
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
    def _default_fetch(url: str) -> str:  # pragma: no cover — network I/O, tested via mock injection
        with urllib.request.urlopen(url, timeout=15) as resp:  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
            return resp.read().decode("utf-8")

    @staticmethod
    def _extract_pattern_names(content: str) -> set[str]:
        """Extract pattern names from a pack's YAML content."""
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            return set()
        if not isinstance(data, dict):
            return set()
        names: set[str] = set()
        for section in ("blocking", "warning"):
            for rule in data.get(section, []) or []:
                if isinstance(rule, dict) and "pattern" in rule:
                    names.add(rule["pattern"])
        return names

    def _detect_conflicts(
        self,
        new_content: str,
        new_user: str,
        new_repo: str,
        project_root: Path,
    ) -> list[str]:
        """Return list of conflict descriptions if patterns overlap."""
        new_patterns = self._extract_pattern_names(new_content)
        if not new_patterns:
            return []

        conflicts: list[str] = []
        packs_dir = project_root / PACKS_DIR
        if not packs_dir.is_dir():
            return []

        new_filename = _pack_filename(new_user, new_repo)
        for pack_file in packs_dir.glob("*.yaml"):
            if pack_file.name == new_filename:
                continue  # skip self on re-install
            try:
                existing = pack_file.read_text(encoding="utf-8")
            except OSError:
                continue
            existing_patterns = self._extract_pattern_names(existing)
            overlap = new_patterns & existing_patterns
            for pattern in sorted(overlap):
                conflicts.append(
                    f"'{pattern}' already defined in {pack_file.name}"
                )
        return conflicts

    @staticmethod
    def _lockfile_path(project_root: Path) -> Path:
        return project_root / PACKS_DIR / "packs.lock"

    @staticmethod
    def _load_lockfile(lockfile: Path) -> dict:
        if not lockfile.exists():
            return {}
        try:
            return json.loads(lockfile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _update_lockfile(
        self,
        project_root: Path,
        user: str,
        repo: str,
        ref: str,
        content_hash: str,
    ) -> None:
        """Add or update a pack entry in the lockfile."""
        lockfile = self._lockfile_path(project_root)
        data = self._load_lockfile(lockfile)
        key = f"{user}/{repo}"
        data[key] = {"ref": ref, "sha256": content_hash}
        lockfile.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )

    def _remove_from_lockfile(
        self, project_root: Path, user: str, repo: str,
    ) -> None:
        """Remove a pack entry from the lockfile."""
        lockfile = self._lockfile_path(project_root)
        data = self._load_lockfile(lockfile)
        key = f"{user}/{repo}"
        if key in data:
            del data[key]
            lockfile.write_text(
                json.dumps(data, indent=2) + "\n", encoding="utf-8"
            )

    def verify_integrity(
        self, project_root: Path,
    ) -> list[str]:
        """Verify installed packs against lockfile checksums.

        Returns list of mismatched pack descriptions.
        """
        lockfile = self._lockfile_path(project_root)
        lock_data = self._load_lockfile(lockfile)
        if not lock_data:
            return []

        mismatches: list[str] = []
        packs_dir = project_root / PACKS_DIR
        for key, entry in lock_data.items():
            user, repo = key.split("/", 1)
            pack_file = packs_dir / _pack_filename(user, repo)
            if not pack_file.exists():
                mismatches.append(f"{key}: file missing")
                continue
            try:
                content = pack_file.read_text(encoding="utf-8")
            except OSError:
                mismatches.append(f"{key}: unreadable")
                continue
            actual_hash = hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest()
            if actual_hash != entry.get("sha256"):
                mismatches.append(
                    f"{key}: checksum mismatch "
                    f"(expected {entry['sha256'][:12]}..., "
                    f"got {actual_hash[:12]}...)"
                )
        return mismatches
