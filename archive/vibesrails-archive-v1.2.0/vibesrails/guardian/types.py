"""Guardian-local type definitions.

Duplicated from learner.signature_index to avoid cross-module dependency.
Guardian should only depend on scanner, not learner.
"""

from dataclasses import dataclass
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
