"""Tests for tools/scan_code.py — MCP scan_code tool."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.scan_code import (  # noqa: E402
    GUARD_PEDAGOGY,
    GUARD_REGISTRY,
    _determine_status,
    _resolve_guards,
    scan_code,
)

# ── Fixtures ───────────────────────────────────────────────────────────

BAD_CODE = """\
import os
import sys
import json

password = "super_secret_123"

def my_function(x):
    print("debug output")  # vibesrails: ignore
    if x > 0:
        if x > 10:
            if x > 100:
                return True
    return False
"""

CLEAN_CODE = """\
\"\"\"A clean module.\"\"\"

import logging

logger = logging.getLogger(__name__)


def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b
"""


def _write_file(tmp_path: Path, content: str, name: str = "example.py") -> Path:
    """Write a Python file to tmp_path and return its path."""
    f = tmp_path / name
    f.write_text(content)
    return f


# ── Guard registry ─────────────────────────────────────────────────────


class TestGuardRegistry:
    """Tests for the guard registry mapping."""

    def test_all_16_guards_registered(self):
        populated = {k: v for k, v in GUARD_REGISTRY.items() if v is not None}
        assert len(populated) == 16

    def test_all_guards_have_pedagogy(self):
        for slug in GUARD_REGISTRY:
            assert slug in GUARD_PEDAGOGY, f"Missing pedagogy for {slug}"

    def test_pedagogy_has_required_keys(self):
        for slug, pedagogy in GUARD_PEDAGOGY.items():
            assert "why" in pedagogy, f"{slug} missing 'why'"
            assert "how_to_fix" in pedagogy, f"{slug} missing 'how_to_fix'"
            assert "prevention" in pedagogy, f"{slug} missing 'prevention'"


# ── _resolve_guards ────────────────────────────────────────────────────


class TestResolveGuards:
    """Tests for guard name resolution."""

    def test_all_returns_all_guards(self):
        result = _resolve_guards("all")
        assert len(result) == 16

    def test_specific_guard(self):
        result = _resolve_guards(["dead_code"])
        assert len(result) == 1
        assert result[0][0] == "dead_code"

    def test_multiple_guards(self):
        result = _resolve_guards(["dead_code", "complexity"])
        slugs = [slug for slug, _ in result]
        assert slugs == ["dead_code", "complexity"]

    def test_unknown_guard_raises(self):
        try:
            _resolve_guards(["nonexistent_guard"])
            raise AssertionError("Should have raised ValueError")
        except ValueError as exc:
            assert "nonexistent_guard" in str(exc)
            assert "Available:" in str(exc)


# ── _determine_status ──────────────────────────────────────────────────


class TestDetermineStatus:
    """Tests for status determination from findings."""

    def test_empty_findings_pass(self):
        assert _determine_status([]) == "pass"

    def test_block_severity(self):
        assert _determine_status([{"severity": "block"}]) == "block"

    def test_warn_severity(self):
        assert _determine_status([{"severity": "warn"}]) == "warn"

    def test_info_severity(self):
        assert _determine_status([{"severity": "info"}]) == "info"

    def test_mixed_returns_worst(self):
        findings = [{"severity": "info"}, {"severity": "warn"}, {"severity": "block"}]
        assert _determine_status(findings) == "block"

    def test_warn_beats_info(self):
        findings = [{"severity": "info"}, {"severity": "warn"}]
        assert _determine_status(findings) == "warn"


# ── scan_code integration ──────────────────────────────────────────────


class TestScanCodeIntegration:
    """Integration tests for the scan_code function."""

    def test_bad_code_produces_findings(self, tmp_path):
        f = _write_file(tmp_path, BAD_CODE)
        result = scan_code(
            file_path=str(f), guards=["dead_code", "observability"]
        )
        assert result["status"] != "pass"
        assert result["summary"]["total"] > 0

    def test_findings_have_pedagogy(self, tmp_path):
        f = _write_file(tmp_path, BAD_CODE)
        result = scan_code(
            file_path=str(f), guards=["dead_code", "observability"]
        )
        for finding in result["findings"]:
            assert "pedagogy" in finding, f"Missing pedagogy in {finding}"
            p = finding["pedagogy"]
            assert "why" in p
            assert "how_to_fix" in p
            assert "prevention" in p

    def test_guards_all(self, tmp_path):
        f = _write_file(tmp_path, BAD_CODE)
        result = scan_code(file_path=str(f), guards="all")
        assert len(result["guards_run"]) == 16

    def test_guards_specific_subset(self, tmp_path):
        f = _write_file(tmp_path, BAD_CODE)
        result = scan_code(
            file_path=str(f), guards=["dead_code", "complexity"]
        )
        assert result["guards_run"] == ["dead_code", "complexity"]

    def test_clean_code_fewer_findings(self, tmp_path):
        f = _write_file(tmp_path, CLEAN_CODE)
        result = scan_code(
            file_path=str(f), guards=["dead_code", "observability"]
        )
        # Clean code should have no dead_code or observability findings for the file
        file_findings = [
            fi for fi in result["findings"]
            if fi.get("file", "").endswith("example.py")
        ]
        assert len(file_findings) == 0

    def test_nonexistent_path_returns_error(self):
        result = scan_code(file_path="/nonexistent/path/file.py", guards=["dead_code"])
        assert result["status"] == "error"
        assert "does not exist" in result.get("error", "")

    def test_invalid_guard_returns_error(self, tmp_path):
        f = _write_file(tmp_path, CLEAN_CODE)
        result = scan_code(file_path=str(f), guards=["fake_guard"])
        assert result["status"] == "error"
        assert "Unknown guard" in result.get("error", "")

    def test_project_path_overrides_file_path(self, tmp_path):
        f = _write_file(tmp_path, BAD_CODE)
        result = scan_code(
            file_path=str(f),
            project_path=str(tmp_path),
            guards=["dead_code"],
        )
        assert result["guards_run"] == ["dead_code"]
        # project_path used means scanning whole directory
        assert result["status"] in ("pass", "info", "warn", "block")

    def test_summary_counts_correct(self, tmp_path):
        f = _write_file(tmp_path, BAD_CODE)
        result = scan_code(
            file_path=str(f), guards=["dead_code", "observability"]
        )
        total = sum(result["summary"]["by_severity"].values())
        assert total == result["summary"]["total"]
        assert total == len(result["findings"])

    def test_result_structure(self, tmp_path):
        f = _write_file(tmp_path, CLEAN_CODE)
        result = scan_code(file_path=str(f), guards=["dead_code"])
        assert "status" in result
        assert "findings" in result
        assert "guards_run" in result
        assert "summary" in result
        assert "total" in result["summary"]
        assert "by_severity" in result["summary"]


class TestScanCodeSingleGuards:
    """Test individual guards produce expected findings."""

    def test_dead_code_detects_unused_import(self, tmp_path):
        code = "import os\nimport json\n\ndef foo():\n    return os.getcwd()\n"
        f = _write_file(tmp_path, code)
        result = scan_code(file_path=str(f), guards=["dead_code"])
        messages = [fi["message"] for fi in result["findings"]]
        assert any("json" in m for m in messages), f"Expected unused json import, got: {messages}"

    def test_observability_detects_print(self):
        # Use tempfile.mkdtemp() directly instead of pytest tmp_path because
        # the observability guard skips **/test_* paths via fnmatch, and
        # pytest's tmp_path includes "test_<testname>0/" in the full path.
        import shutil
        import tempfile

        tmpdir = Path(tempfile.mkdtemp(prefix="obs_scan_"))
        try:
            code = (
                "import logging\n\n"
                "logger = logging.getLogger(__name__)\n\n\n"
                "def process_data(items):\n"
                "    for item in items:\n"
                '        print(f"Processing {item}")\n'
                "    return items\n\n\n"
                "def validate(x):\n"
                '    print("validating...")\n'
                "    return x > 0\n"
            )
            _write_file(tmpdir, code)
            result = scan_code(project_path=str(tmpdir), guards=["observability"])
            messages = [fi["message"] for fi in result["findings"]]
            assert any("print" in m.lower() for m in messages), (
                f"Expected print detection, got: {messages}"
            )
        finally:
            shutil.rmtree(tmpdir)

    def test_database_safety_detects_fstring_sql(self, tmp_path):
        code = (
            "import sqlite3\n"
            "def query(user_id):\n"
            "    conn = sqlite3.connect('db.sqlite')\n"
            '    conn.execute(f"SELECT * FROM users WHERE id={user_id}")\n'
        )
        f = _write_file(tmp_path, code)
        result = scan_code(file_path=str(f), guards=["database_safety"])
        # Should detect SQL injection via f-string
        sql_findings = [
            fi for fi in result["findings"]
            if "sql" in fi["message"].lower() or "inject" in fi["message"].lower()
        ]
        assert len(sql_findings) > 0, f"Expected SQL injection finding, got: {result['findings']}"
