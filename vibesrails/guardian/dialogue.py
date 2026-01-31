"""Interactive dialogue for validation decisions."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .types import Signature

from .placement_guard import Divergence


class InteractiveDialogue:
    """Handles interactive validation prompts."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path(".vibesrails")
        self.observations_file = self.cache_dir / "observations.jsonl"

    def format_placement_prompt(self, file_path: str, divergence: Divergence) -> str:
        """Format prompt for placement divergence."""
        prompt = f"""
🤔 Pattern Divergence Detected

File: {file_path}
Expected: {divergence.expected_location}
Actual: {divergence.actual_location}
Confidence: {divergence.confidence:.0%} ({divergence.message})

Options:
  1) Use expected location (create in {divergence.expected_location})
  2) Create here (new pattern - will learn this)
  3) Ignore this time (don't learn)

Choice:"""
        return prompt.strip()

    def format_duplication_prompt(self, function_name: str, similar: list[Signature]) -> str:
        """Format prompt for duplication detection."""
        similar_list = "\n".join([
            f"  • {sig.name} ({sig.signature_type}) in {sig.file_path}:{sig.line_number}"
            for sig in similar
        ])

        prompt = f"""
💡 Similar Code Detected

Creating: {function_name}
Found similar:
{similar_list}

Options:
  1) Use existing (recommended)
  2) Create anyway (different purpose)
  3) Refactor to centralize

Choice:"""
        return prompt.strip()

    def record_decision(
        self,
        file_path: str,
        decision_type: str,
        user_choice: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Record user decision to observations log."""
        observation = {
            "timestamp": datetime.now().isoformat(),
            "file_path": file_path,
            "decision_type": decision_type,
            "user_choice": user_choice,
            "metadata": metadata or {}
        }

        # Append to JSONL file
        self.cache_dir.mkdir(exist_ok=True)
        with open(self.observations_file, "a") as f:
            f.write(json.dumps(observation) + "\n")
