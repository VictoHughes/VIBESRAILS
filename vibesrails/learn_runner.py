"""Learn command execution for VibesRails.

Handles project structure learning and pattern detection.
"""

import json
from pathlib import Path

from .learner import PatternDetector, SignatureIndexer, StructureRulesGenerator
from .scanner import BLUE, GREEN, NC, YELLOW


def handle_learn_command() -> int:
    """Learn project structure and create pattern rules."""
    print(f"{BLUE}🧠 Learning project structure...{NC}")

    project_root = Path.cwd()
    cache_dir = project_root / ".vibesrails"
    cache_dir.mkdir(exist_ok=True)

    # Detect patterns
    print("  Detecting patterns...")
    detector = PatternDetector(project_root)
    patterns = detector.detect()

    if not patterns:
        print(f"{YELLOW}  No clear patterns detected yet.{NC}")
        return 0

    print(f"{GREEN}  Detected patterns:{NC}")
    for pattern in patterns:
        print(f"    - {pattern.category:12} → {pattern.location:30} "
              f"({pattern.confidence:.0%} confidence, {pattern.examples} examples)")

    # Generate rules
    print("\n  Generating structure rules...")
    generator = StructureRulesGenerator()
    patterns_file = cache_dir / "learned_patterns.yaml"
    generator.save_rules(patterns, patterns_file)
    print(f"{GREEN}  ✓ Rules saved to .vibesrails/learned_patterns.yaml{NC}")

    # Build signature index
    print("\n  Building signature index...")
    indexer = SignatureIndexer(project_root)
    signatures = indexer.build_index()

    index_file = cache_dir / "signature_index.json"
    index_data = [
        {
            "name": sig.name,
            "signature_type": sig.signature_type,
            "file_path": sig.file_path,
            "line_number": sig.line_number,
            "parameters": sig.parameters,
            "return_type": sig.return_type,
            "parent_class": sig.parent_class,
        }
        for sig in signatures
    ]
    with open(index_file, "w") as f:
        json.dump(index_data, f, indent=2)

    print(f"{GREEN}  ✓ Indexed {len(signatures)} signatures{NC}")
    print(f"\n{GREEN}✓ Learning complete!{NC}")
    print("  Patterns and signatures cached in .vibesrails/")

    return 0
