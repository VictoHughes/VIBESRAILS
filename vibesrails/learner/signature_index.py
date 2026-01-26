"""Function and class signature indexing."""
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class Signature:
    """A function or class signature."""
    name: str
    signature_type: Literal["function", "method", "class"]
    file_path: str  # Relative to project root
    line_number: int
    parameters: list[str]
    return_type: str | None = None
    parent_class: str | None = None  # For methods


class SignatureIndexer:
    """Builds index of all function/class signatures in project."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def build_index(self) -> list[Signature]:
        """Scan all Python files and extract signatures."""
        signatures = []

        for py_file in self.project_root.rglob("*.py"):
            try:
                signatures.extend(self._extract_signatures(py_file))
            except Exception:
                # Skip files with syntax errors
                continue

        return signatures

    def _extract_signatures(self, file_path: Path) -> list[Signature]:
        """Extract signatures from a single file."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
        except Exception:
            return []

        signatures = []
        relative_path = str(file_path.relative_to(self.project_root))

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Function or method
                params = [arg.arg for arg in node.args.args]
                return_type = None
                if node.returns:
                    return_type = ast.unparse(node.returns)

                # Determine if method (inside class)
                parent_class = self._find_parent_class(tree, node)
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

    def _find_parent_class(self, tree: ast.AST, func_node: ast.FunctionDef) -> str | None:
        """Find parent class of a function node."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if func_node in ast.walk(node):
                    return node.name
        return None

    def find_similar(self, query: str, index: list[Signature]) -> list[Signature]:
        """Find signatures with similar names."""
        query_lower = query.lower()
        similar = []

        for sig in index:
            sig_lower = sig.name.lower()

            # Exact match
            if sig_lower == query_lower:
                continue  # Skip exact matches

            # Contains similar words
            query_words = set(query_lower.replace("_", " ").split())
            sig_words = set(sig_lower.replace("_", " ").split())

            # If they share words, it's similar
            if query_words & sig_words:
                similar.append(sig)

        return similar
