"""[EXPERIMENTAL] Function and class signature indexing."""
import ast
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class Signature:
    """[EXPERIMENTAL] A function or class signature."""
    name: str
    signature_type: Literal["function", "method", "class"]
    file_path: str  # Relative to project root
    line_number: int
    parameters: list[str]
    return_type: str | None = None
    parent_class: str | None = None  # For methods


class SignatureIndexer:
    """[EXPERIMENTAL] Builds index of all function/class signatures in project."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def build_index(self) -> list[Signature]:
        """Scan all Python files and extract signatures."""
        signatures = []

        for py_file in self.project_root.rglob("*.py"):
            try:
                signatures.extend(self._extract_signatures(py_file))
            except (OSError, UnicodeDecodeError, SyntaxError):
                logger.debug("Skipping file with parse/read errors: %s", py_file)
                continue

        return signatures

    def _extract_signatures(self, file_path: Path) -> list[Signature]:
        """Extract signatures from a single file."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
        except (OSError, UnicodeDecodeError, SyntaxError):
            logger.debug("Failed to parse %s for signatures", file_path)
            return []

        signatures = []
        relative_path = str(file_path.relative_to(self.project_root))
        parent_map = self._build_parent_map(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Function or method
                params = [arg.arg for arg in node.args.args]
                return_type = None
                if node.returns:
                    return_type = ast.unparse(node.returns)

                # Determine if method (inside class) via O(1) lookup
                parent = parent_map.get(id(node))
                parent_class = parent.name if isinstance(parent, ast.ClassDef) else None
                sig_type = "method" if parent_class else "function"

                signatures.append(Signature(
                    name=node.name,
                    signature_type=sig_type,
                    file_path=relative_path,
                    line_number=node.lineno,
                    parameters=params,
                    return_type=return_type,
                    parent_class=parent_class
                ))

            elif isinstance(node, ast.ClassDef):
                signatures.append(Signature(
                    name=node.name,
                    signature_type="class",
                    file_path=relative_path,
                    line_number=node.lineno,
                    parameters=[]
                ))

        return signatures

    @staticmethod
    def _build_parent_map(tree: ast.AST) -> dict[int, ast.AST]:
        """Build child-id → parent map for O(1) parent lookup."""
        parent_map: dict[int, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent_map[id(child)] = node
        return parent_map

    def find_similar(
        self, query: str, index: list[Signature], *, include_exact: bool = False,
    ) -> list[Signature]:
        """Find signatures with similar names.

        Args:
            include_exact: If True, include exact name matches in results.
                Default False to exclude self-matches.
        """
        query_lower = query.lower()
        similar = []
        query_words = set(query_lower.replace("_", " ").split())

        for sig in index:
            sig_lower = sig.name.lower()

            if sig_lower == query_lower:
                if include_exact:
                    similar.append(sig)
                continue

            # If they share words, it's similar
            sig_words = set(sig_lower.replace("_", " ").split())
            if query_words & sig_words:
                similar.append(sig)

        return similar
