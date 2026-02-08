"""Learn command execution for VibesRails.

Handles project structure learning and pattern detection.
"""

import json
import logging
from pathlib import Path

from .learner import PatternDetector, SignatureIndexer, StructureRulesGenerator
from .scanner import BLUE, GREEN, NC, YELLOW

logger = logging.getLogger(__name__)


def _build_signature_index(project_root: Path, cache_dir: Path) -> int:
    """Build and save signature index. Returns count."""
    logger.info("\n  Building signature index...")
    indexer = SignatureIndexer(project_root)
    signatures = indexer.build_index()
    index_data = [
        {"name": sig.name, "signature_type": sig.signature_type,
         "file_path": sig.file_path, "line_number": sig.line_number,
         "parameters": sig.parameters, "return_type": sig.return_type,
         "parent_class": sig.parent_class}
        for sig in signatures
    ]
    with open(cache_dir / "signature_index.json", "w") as f:
        json.dump(index_data, f, indent=2)
    return len(signatures)


def handle_learn_command() -> int:
    """Learn project structure and create pattern rules."""
    logger.info(f"{BLUE}🧠 Learning project structure...{NC}")

    project_root = Path.cwd()
    cache_dir = project_root / ".vibesrails"
    cache_dir.mkdir(exist_ok=True)

    logger.info("  Detecting patterns...")
    patterns = PatternDetector(project_root).detect()

    if not patterns:
        logger.info(f"{YELLOW}  No clear patterns detected yet.{NC}")
        return 0

    logger.info(f"{GREEN}  Detected patterns:{NC}")
    for p in patterns:
        logger.info(f"    - {p.category} → {p.location} ({p.confidence * 100:.0f}% confidence, {p.examples} examples)")

    logger.info("\n  Generating structure rules...")
    StructureRulesGenerator().save_rules(patterns, cache_dir / "learned_patterns.yaml")
    logger.info(f"{GREEN}  ✓ Rules saved to .vibesrails/learned_patterns.yaml{NC}")

    sig_count = _build_signature_index(project_root, cache_dir)
    logger.info(f"{GREEN}  ✓ Indexed {sig_count} signatures{NC}")
    logger.info(f"\n{GREEN}✓ Learning complete!{NC}")
    logger.info("  Patterns and signatures cached in .vibesrails/")
    return 0
