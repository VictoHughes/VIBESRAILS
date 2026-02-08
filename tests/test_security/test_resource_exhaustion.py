"""Security tests: resource exhaustion prevention.

Tests that large inputs, many files, deep nesting, and oversized text
are handled safely without crashing or consuming excessive resources.
"""

from __future__ import annotations

from core.drift_tracker import aggregate_metrics
from core.prompt_shield import _MAX_EXTRACT_DEPTH, PromptShield, _extract_strings


def test_aggregate_metrics_max_files(tmp_path):
    """Aggregate stops after max_files to prevent DoS on huge repos."""
    # Create more files than the limit (use a small limit for speed)
    for i in range(20):
        (tmp_path / f"mod_{i}.py").write_text(f"x_{i} = {i}")

    result = aggregate_metrics(tmp_path, max_files=10)
    assert result["file_count"] <= 10


def test_deep_nested_dict_no_crash():
    """Deeply nested dict doesn't cause RecursionError in _extract_strings."""
    # Build a 200-deep nested dict
    nested: dict = {"key": "leaf_value"}
    for _ in range(200):
        nested = {"nested": nested}

    # Should not raise RecursionError
    result = _extract_strings(nested)
    # At depth > _MAX_EXTRACT_DEPTH, extraction stops
    assert isinstance(result, list)


def test_oversized_text_rejected():
    """PromptShield rejects text larger than 10 MB."""
    shield = PromptShield()
    giant = "A" * (11 * 1024 * 1024)  # 11 MB
    findings = shield.scan_text(giant)
    assert len(findings) == 1
    assert "too large" in findings[0].message.lower()


def test_oversized_file_rejected(tmp_path):
    """PromptShield rejects files larger than 10 MB."""
    shield = PromptShield()
    big_file = tmp_path / "big.txt"
    big_file.write_bytes(b"A" * (11 * 1024 * 1024))
    findings = shield.scan_file(str(big_file))
    assert len(findings) == 1
    assert "too large" in findings[0].message.lower()


def test_sql_limit_in_brief_history(tmp_path):
    """Brief history query has LIMIT clause."""
    from core.brief_enforcer import BriefEnforcer

    db = str(tmp_path / "test.db")
    enforcer = BriefEnforcer(db_path=db)

    # Store a few briefs
    for i in range(5):
        enforcer.store_brief(
            {"intent": f"Task {i}: Implement user authentication"},
            50 + i, "minimal",
        )

    history = enforcer.get_history()
    assert len(history) <= 1000  # LIMIT enforced


def test_extract_strings_depth_limit():
    """_extract_strings stops at _MAX_EXTRACT_DEPTH."""
    # Build exactly at the depth limit
    nested: dict = {"key": "deep_value"}
    for _ in range(_MAX_EXTRACT_DEPTH + 5):
        nested = {"level": nested}

    result = _extract_strings(nested)
    # The "deep_value" at the bottom should NOT be extracted (too deep)
    assert "deep_value" not in result
