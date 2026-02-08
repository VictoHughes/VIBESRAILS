"""Detects code duplication by searching signature index."""
import json
from dataclasses import dataclass
from pathlib import Path

from .types import Signature


@dataclass
class DuplicationResult:
    """Result of duplication check."""
    has_duplicates: bool
    similar_signatures: list[Signature]


class DuplicationGuard:
    """Detects potential code duplication."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.index_file = cache_dir / "signature_index.json"
        self._index: list[Signature] | None = None

    def check_duplication(self, function_name: str, signature: str) -> DuplicationResult:
        """Check if function/class already exists or similar code present."""
        index = self._load_index()

        if not index:
            return DuplicationResult(has_duplicates=False, similar_signatures=[])

        similar = []
        name_lower = function_name.lower()

        for sig in index:
            # Exact match
            if sig.name.lower() == name_lower:
                similar.append(sig)
                continue

            # Similar names (share words)
            sig_words = set(sig.name.lower().replace("_", " ").split())
            name_words = set(name_lower.replace("_", " ").split())

            if sig_words & name_words:  # Intersection
                similar.append(sig)

        return DuplicationResult(
            has_duplicates=len(similar) > 0,
            similar_signatures=similar
        )

    def _load_index(self) -> list[Signature] | None:
        """Load signature index from cache."""
        if self._index is not None:
            return self._index

        if not self.index_file.exists():
            return None

        with open(self.index_file) as f:
            data = json.load(f)

        # Convert dicts back to Signature objects
        self._index = [
            Signature(
                name=sig["name"],
                signature_type=sig["signature_type"],
                file_path=sig["file_path"],
                line_number=sig["line_number"],
                parameters=sig["parameters"],
                return_type=sig.get("return_type"),
                parent_class=sig.get("parent_class")
            )
            for sig in data
        ]

        return self._index
