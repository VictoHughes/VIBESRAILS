"""Contract tracker — snapshot and compare public API signatures between phases.

Uses Python AST to extract public function/class/method signatures.
Stores snapshots in .vibesrails/contracts/phase_N.json.
Compares snapshots to detect breaking changes (removed/modified signatures).
"""

from __future__ import annotations

import ast
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

CONTRACTS_DIR = ".vibesrails/contracts"

# Directories to skip during signature extraction
_SKIP_DIRS = {
    "__pycache__", ".venv", "venv", ".git", ".eggs",
    "node_modules", "dist", "build", ".pytest_cache",
    ".ruff_cache", ".mypy_cache",
}


@dataclass
class Signature:
    """A single public API signature."""

    module: str
    name: str
    kind: str  # "function", "class", "method"
    params: list[str] = field(default_factory=list)
    return_type: str | None = None

    @property
    def qualified_name(self) -> str:
        return f"{self.module}.{self.name}"

    def signature_str(self) -> str:
        """Human-readable signature string."""
        params = ", ".join(self.params)
        ret = f" -> {self.return_type}" if self.return_type else ""
        return f"{self.name}({params}){ret}"


@dataclass
class ContractDiff:
    """Diff between two snapshots."""

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def has_breaking(self) -> bool:
        return bool(self.removed or self.modified)

    @property
    def total_changes(self) -> int:
        return len(self.added) + len(self.removed) + len(self.modified)


# ── AST extraction ─────────────────────────────────────────────


def _format_annotation(node: ast.expr | None) -> str | None:
    """Convert an AST annotation node to a readable string."""
    if node is None:
        return None
    return ast.unparse(node)


def _format_param(arg: ast.arg) -> str:
    """Format a function parameter as 'name: type' or just 'name'."""
    if arg.annotation:
        return f"{arg.arg}: {_format_annotation(arg.annotation)}"
    return arg.arg


def extract_signatures(filepath: Path, module_name: str = "") -> list[Signature]:
    """Extract public signatures from a Python file using AST.

    Only extracts top-level functions and classes (+ their public methods).
    Skips private names (starting with _).
    """
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    sigs: list[Signature] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name.startswith("_"):
                continue
            params = [_format_param(a) for a in node.args.args if a.arg != "self"]
            sigs.append(Signature(
                module=module_name,
                name=node.name,
                kind="function",
                params=params,
                return_type=_format_annotation(node.returns),
            ))

        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            # Extract public methods
            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    if item.name.startswith("_") and item.name != "__init__":
                        continue
                    params = [_format_param(a) for a in item.args.args if a.arg != "self"]
                    method_name = f"{node.name}.{item.name}"
                    sigs.append(Signature(
                        module=module_name,
                        name=method_name,
                        kind="method" if item.name != "__init__" else "method",
                        params=params,
                        return_type=_format_annotation(item.returns),
                    ))

    return sigs


def _iter_py_files(root: Path, limit: int = 500) -> list[Path]:
    """Iterate Python files, skipping tests and hidden dirs."""
    files = []
    for path in root.rglob("*.py"):
        # Skip excluded dirs
        parts = set(path.relative_to(root).parts)
        if parts & _SKIP_DIRS:
            continue
        # Skip test files
        name = path.name
        if name.startswith("test_") or name.endswith("_test.py"):
            continue
        if "tests" in path.relative_to(root).parts:
            continue
        files.append(path)
        if len(files) >= limit:
            break
    return sorted(files)


# ── Snapshot operations ────────────────────────────────────────


def snapshot(root: Path) -> dict[str, dict]:
    """Take a snapshot of all public signatures in the project.

    Returns: { "module.name": { "kind", "params", "return_type", "sig" } }
    """
    result: dict[str, dict] = {}
    for filepath in _iter_py_files(root):
        try:
            rel = filepath.relative_to(root)
            module_name = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
        except ValueError:
            module_name = filepath.stem

        sigs = extract_signatures(filepath, module_name)
        for sig in sigs:
            key = sig.qualified_name
            result[key] = {
                "kind": sig.kind,
                "params": sig.params,
                "return_type": sig.return_type,
                "sig": sig.signature_str(),
            }
    return result


def save_snapshot(root: Path, phase: int, data: dict[str, dict]) -> Path:
    """Save a contract snapshot for the given phase."""
    contracts_dir = root / CONTRACTS_DIR
    contracts_dir.mkdir(parents=True, exist_ok=True)
    path = contracts_dir / f"phase_{phase}.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return path


def load_snapshot(root: Path, phase: int) -> dict[str, dict] | None:
    """Load a contract snapshot. Returns None if not found."""
    path = root / CONTRACTS_DIR / f"phase_{phase}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def latest_snapshot(root: Path) -> tuple[int, dict[str, dict]] | None:
    """Find the most recent snapshot. Returns (phase_num, data) or None."""
    contracts_dir = root / CONTRACTS_DIR
    if not contracts_dir.is_dir():
        return None
    snapshots = sorted(contracts_dir.glob("phase_*.json"), reverse=True)
    for path in snapshots:
        try:
            phase_num = int(path.stem.split("_")[1])
            data = json.loads(path.read_text())
            return (phase_num, data)
        except (ValueError, json.JSONDecodeError, OSError, IndexError):
            continue
    return None


# ── Comparison ─────────────────────────────────────────────────


def compare(old: dict[str, dict], new: dict[str, dict]) -> ContractDiff:
    """Compare two snapshots and return the diff."""
    old_keys = set(old.keys())
    new_keys = set(new.keys())

    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)

    modified = []
    for key in sorted(old_keys & new_keys):
        old_sig = old[key].get("sig", "")
        new_sig = new[key].get("sig", "")
        if old_sig != new_sig:
            modified.append((key, old_sig, new_sig))

    return ContractDiff(added=added, removed=removed, modified=modified)


# ── Formatting ─────────────────────────────────────────────────


def format_diff(diff: ContractDiff, phase_num: int | None = None) -> str:
    """Format a ContractDiff as a human-readable report."""
    lines = []
    phase_label = f" since Phase {phase_num} snapshot" if phase_num is not None else ""
    lines.append(f"Contract changes{phase_label}:")

    if not diff.total_changes:
        lines.append("  No changes detected.")
        return "\n".join(lines)

    if diff.added:
        lines.append(f"  +{len(diff.added)} added (new public signatures)")
        for name in diff.added[:10]:
            lines.append(f"    + {name}")
        if len(diff.added) > 10:
            lines.append(f"    ... and {len(diff.added) - 10} more")

    if diff.modified:
        lines.append(f"  ~{len(diff.modified)} modified (signature changed)")
        for name, old_sig, new_sig in diff.modified[:10]:
            lines.append(f"    ~ {name}: {old_sig} -> {new_sig}")

    if diff.removed:
        lines.append(f"  -{len(diff.removed)} removed (breaking change)")
        for name in diff.removed[:10]:
            lines.append(f"    - {name}")

    return "\n".join(lines)
