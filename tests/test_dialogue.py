"""Tests for interactive dialogue."""
import pytest
from unittest.mock import patch, MagicMock
from vibesrails.guardian.dialogue import InteractiveDialogue
from vibesrails.guardian.placement_guard import Divergence
from vibesrails.guardian.types import Signature


def test_dialogue_presents_placement_options():
    """Should present options when placement divergence detected."""
    divergence = Divergence(
        category="test",
        expected_location="tests/",
        actual_location="src/",
        confidence=0.95,
        message="Tests should be in tests/"
    )

    dialogue = InteractiveDialogue()
    prompt = dialogue.format_placement_prompt("src/test_foo.py", divergence)

    assert "tests/" in prompt
    assert "src/" in prompt
    assert "0.95" in prompt or "95%" in prompt
    assert "1)" in prompt  # Option 1
    assert "2)" in prompt  # Option 2


def test_dialogue_presents_duplication_options():
    """Should present options when similar code detected."""
    similar = [
        Signature(
            name="validate_email",
            signature_type="function",
            file_path="utils/validators.py",
            line_number=10,
            parameters=["email"],
            return_type="bool"
        ),
        Signature(
            name="email_validator",
            signature_type="function",
            file_path="domain/validation/email.py",
            line_number=25,
            parameters=["email_str"],
            return_type="bool"
        )
    ]

    dialogue = InteractiveDialogue()
    prompt = dialogue.format_duplication_prompt("check_email_format", similar)

    assert "validate_email" in prompt
    assert "email_validator" in prompt
    assert "utils/validators.py:10" in prompt
    assert "domain/validation/email.py:25" in prompt


def test_dialogue_records_decision():
    """Should record user decisions to observations log."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".vibesrails"
        cache_dir.mkdir()

        dialogue = InteractiveDialogue(cache_dir)
        dialogue.record_decision(
            file_path="src/test_foo.py",
            decision_type="placement_divergence",
            user_choice="create_here",
            metadata={"expected": "tests/", "actual": "src/"}
        )

        # Should create observations log
        log_file = cache_dir / "observations.jsonl"
        assert log_file.exists()

        # Should contain decision
        content = log_file.read_text()
        assert "placement_divergence" in content
        assert "create_here" in content
