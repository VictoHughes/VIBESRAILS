"""Tests for coverage_reader — reads pre-generated coverage.json."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest import mock

from vibesrails.adapters.coverage_reader import (
    is_coverage_stale,
    read_coverage,
)

# ── helpers ────────────────────────────────────────────────────


def _write_coverage_json(root: Path, data: dict) -> Path:
    """Write a coverage.json to root and return its path."""
    path = root / "coverage.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


_MOCK_COVERAGE = {
    "meta": {"version": "7.6"},
    "totals": {
        "percent_covered": 85.0,
        "num_statements": 80,
        "covered_lines": 68,
    },
    "files": {
        "app.py": {"summary": {"percent_covered": 90.0}},
        "utils.py": {"summary": {"percent_covered": 70.0}},
    },
}


# ── tests ──────────────────────────────────────────────────────


def test_read_coverage_basic(tmp_path):
    """Basic read: total_percent and file count are correct."""
    _write_coverage_json(tmp_path, _MOCK_COVERAGE)
    report = read_coverage(tmp_path)

    assert report is not None
    assert report.total_percent == 85.0
    assert report.total_statements == 80
    assert report.total_covered == 68
    assert len(report.files) == 2


def test_read_coverage_per_file(tmp_path):
    """Per-file percentages are extracted correctly."""
    _write_coverage_json(tmp_path, _MOCK_COVERAGE)
    report = read_coverage(tmp_path)

    assert report is not None
    assert report.files["app.py"] == 90.0
    assert report.files["utils.py"] == 70.0


def test_read_coverage_missing_file(tmp_path):
    """No coverage.json → returns None."""
    result = read_coverage(tmp_path)
    assert result is None


def test_read_coverage_invalid_json(tmp_path):
    """Corrupt JSON → returns None."""
    (tmp_path / "coverage.json").write_text("not valid json {{", encoding="utf-8")
    result = read_coverage(tmp_path)
    assert result is None


def test_files_below_threshold(tmp_path):
    """files_below(80) should return utils.py (70%) but not app.py (90%)."""
    _write_coverage_json(tmp_path, _MOCK_COVERAGE)
    report = read_coverage(tmp_path)

    assert report is not None
    below = report.files_below(80.0)
    assert "utils.py" in below
    assert "app.py" not in below
    assert below["utils.py"] == 70.0


def test_staleness_no_file(tmp_path):
    """Missing coverage.json → is_coverage_stale returns True."""
    assert is_coverage_stale(tmp_path) is True


def test_staleness_fresh(tmp_path):
    """coverage.json written after last git commit → not stale (False)."""
    _write_coverage_json(tmp_path, _MOCK_COVERAGE)

    # Simulate: last commit was 1 second in the past, file is newer
    past_ts = time.time() - 1.0

    with mock.patch(
        "vibesrails.adapters.coverage_reader.subprocess.run"
    ) as mock_run:
        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout=str(int(past_ts)),
        )
        # File was just created so its mtime > past_ts
        result = is_coverage_stale(tmp_path)

    assert result is False
