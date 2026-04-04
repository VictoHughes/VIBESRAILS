"""OpenSpec interop — detect and read OpenSpec project structure.

Reads the filesystem directly. No dependency on the OpenSpec CLI (npm).

OpenSpec directory structure:
    openspec/
    ├── project.md          # project metadata
    ├── specs/              # current system behavior (per feature)
    │   ├── auth-login/
    │   └── checkout-cart/
    └── changes/            # pending modifications
        ├── add-dark-mode/
        │   ├── proposal.md
        │   ├── specs/
        │   ├── design.md
        │   └── tasks.md
        └── archive/         # completed changes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OpenSpecInfo:
    """Parsed OpenSpec project state."""

    detected: bool = False
    has_project_md: bool = False
    spec_count: int = 0
    spec_names: list[str] = field(default_factory=list)
    pending_count: int = 0
    pending_names: list[str] = field(default_factory=list)
    archived_count: int = 0


def detect(root: Path) -> OpenSpecInfo:
    """Detect and parse OpenSpec structure in a project.

    Returns OpenSpecInfo with detected=False if no openspec/ directory.
    Never raises — graceful degradation on any filesystem error.
    """
    info = OpenSpecInfo()
    openspec_dir = root / "openspec"

    if not openspec_dir.is_dir():
        return info

    info.detected = True
    info.has_project_md = (openspec_dir / "project.md").is_file()

    # Count specs
    specs_dir = openspec_dir / "specs"
    if specs_dir.is_dir():
        try:
            spec_dirs = [
                d for d in sorted(specs_dir.iterdir())
                if d.is_dir() and not d.name.startswith(".")
            ]
            info.spec_count = len(spec_dirs)
            info.spec_names = [d.name for d in spec_dirs]
        except OSError:
            pass

    # Count pending changes (exclude archive/)
    changes_dir = openspec_dir / "changes"
    if changes_dir.is_dir():
        try:
            pending = [
                d for d in sorted(changes_dir.iterdir())
                if d.is_dir()
                and d.name != "archive"
                and not d.name.startswith(".")
            ]
            info.pending_count = len(pending)
            info.pending_names = [d.name for d in pending]
        except OSError:
            pass

    # Count archived changes
    archive_dir = changes_dir / "archive" if changes_dir.is_dir() else None
    if archive_dir and archive_dir.is_dir():
        try:
            archived = [
                d for d in archive_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
            info.archived_count = len(archived)
        except OSError:
            pass

    return info
