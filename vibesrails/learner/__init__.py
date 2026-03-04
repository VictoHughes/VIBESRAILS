"""Pattern learning and structure detection.

.. warning::
    This module is **experimental**. APIs may change without notice.
    Not recommended for production use.
"""

import warnings

warnings.warn(
    "vibesrails.learner is experimental and not production-ready. "
    "APIs may change without notice.",
    stacklevel=2,
    category=FutureWarning,
)

from .pattern_detector import DetectedPattern, PatternDetector  # noqa: E402
from .signature_index import Signature, SignatureIndexer  # noqa: E402
from .structure_rules import StructureRulesGenerator  # noqa: E402

__all__ = [
    "PatternDetector",
    "DetectedPattern",
    "SignatureIndexer",
    "Signature",
    "StructureRulesGenerator",
]
