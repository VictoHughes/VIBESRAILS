"""Path validation for MCP tool inputs.

Prevents path traversal, symlink attacks, and oversized file processing.
All path arguments from MCP clients must pass through validate_path()
before being used.

Filesystem sandbox:
  - DENIED_ROOTS: always blocked (/etc, /var, /proc, /sys, /dev)
  - VIBESRAILS_ALLOWED_ROOTS env var: if set, only those roots are allowed
"""

from __future__ import annotations

import os
from pathlib import Path


class PathValidationError(ValueError):
    """Raised when a path argument fails validation.

    Messages are safe to return to MCP clients (no internal paths leaked).
    """


_MAX_SIZE_MB_DEFAULT = 10

# System directories that should never be accessed by MCP tools.
# /var/folders excluded: macOS tmp space used by pytest/tmp_path.
DENIED_ROOTS: tuple[str, ...] = (
    "/etc",
    "/var/log",
    "/var/run",
    "/var/spool",
    "/proc",
    "/sys",
    "/dev",
)


def _get_allowed_roots() -> list[Path] | None:
    """Parse VIBESRAILS_ALLOWED_ROOTS env var.

    Returns None if not set (no allowlist restriction).
    Returns list of resolved Path objects if set.
    """
    raw = os.environ.get("VIBESRAILS_ALLOWED_ROOTS")
    if not raw:
        return None
    roots = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            roots.append(Path(os.path.realpath(part)))
    return roots if roots else None


def _check_sandbox(resolved: Path) -> None:
    """Check resolved path against denied and allowed roots.

    Raises PathValidationError if path is in a denied root or
    outside allowed roots (when configured).
    """
    resolved_str = str(resolved)

    # Always block denied roots (check both raw and realpath-resolved forms
    # to handle macOS symlinks like /etc -> /private/etc)
    for denied in DENIED_ROOTS:
        denied_resolved = os.path.realpath(denied)
        if (
            resolved_str == denied
            or resolved_str.startswith(denied + "/")
            or resolved_str == denied_resolved
            or resolved_str.startswith(denied_resolved + "/")
        ):
            raise PathValidationError("Path outside allowed roots.")

    # Check allowed roots (if configured)
    allowed = _get_allowed_roots()
    if allowed is not None:
        for root in allowed:
            root_str = str(root)
            if resolved_str == root_str or resolved_str.startswith(root_str + "/"):
                return  # Inside an allowed root
        raise PathValidationError("Path outside allowed roots.")


def validate_path(
    path: str,
    *,
    must_exist: bool = True,
    must_be_file: bool = False,
    must_be_dir: bool = False,
    max_size_mb: int = _MAX_SIZE_MB_DEFAULT,
    follow_symlinks: bool = False,
    allowed_extensions: set[str] | None = None,
) -> Path:
    """Validate and resolve a filesystem path.

    Args:
        path: Raw path string from MCP client.
        must_exist: Reject if path doesn't exist.
        must_be_file: Reject if path is not a regular file.
        must_be_dir: Reject if path is not a directory.
        max_size_mb: Max file size in MB (only checked for files).
        follow_symlinks: If False, reject symlinks.
        allowed_extensions: If set, reject files with other extensions.

    Returns:
        Resolved Path object.

    Raises:
        PathValidationError: If validation fails.
    """
    if not path or not isinstance(path, str):
        raise PathValidationError("Path must be a non-empty string.")

    if not path.strip():
        raise PathValidationError("Path must be a non-empty string.")

    # Resolve to absolute, collapsing .. and symlinks
    resolved = Path(os.path.realpath(path))

    # Filesystem sandbox check
    _check_sandbox(resolved)

    # Reject symlinks (before existence check — the original path may be a symlink)
    if not follow_symlinks:
        original = Path(path)
        if original.is_symlink():
            raise PathValidationError("Symlinks are not allowed.")

    if must_exist and not resolved.exists():
        raise PathValidationError("Path does not exist.")

    if must_be_file:
        if resolved.exists() and not resolved.is_file():
            raise PathValidationError("Path is not a file.")

    if must_be_dir:
        if resolved.exists() and not resolved.is_dir():
            raise PathValidationError("Path is not a directory.")

    # Extension check (only for files)
    if allowed_extensions and resolved.is_file():
        if resolved.suffix.lower() not in allowed_extensions:
            allowed = ", ".join(sorted(allowed_extensions))
            raise PathValidationError(
                f"File extension not allowed. Accepted: {allowed}"
            )

    # Size check (only for existing files)
    if resolved.is_file() and max_size_mb > 0:
        size_bytes = resolved.stat().st_size
        max_bytes = max_size_mb * 1024 * 1024
        if size_bytes > max_bytes:
            raise PathValidationError(
                f"File too large ({size_bytes // (1024*1024)}MB). "
                f"Maximum: {max_size_mb}MB."
            )

    return resolved
