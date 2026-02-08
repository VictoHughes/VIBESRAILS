"""Tests for tools/deep_hallucination.py — MCP deep_hallucination tool."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.deep_hallucination import deep_hallucination  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────

def _write_file(tmp_path: Path, content: str, name: str = "sample.py") -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


def _mock_urlopen_200(*args, **kwargs):
    """Mock that returns 200 for any PyPI request."""
    resp = type("Resp", (), {"status": 200})()
    return type("Ctx", (), {
        "__enter__": lambda self: resp,
        "__exit__": lambda *a: None,
    })()


def _mock_urlopen_error(*args, **kwargs):
    """Mock that simulates network failure."""
    raise Exception("Network unavailable")


# ── Valid imports ────────────────────────────────────────────────────


class TestValidImports:
    """Tests for files with valid, importable modules."""

    def test_stdlib_imports_pass(self, tmp_path):
        f = _write_file(tmp_path, "import os\nimport sys\nimport json\n")
        db = tmp_path / "test.db"
        result = deep_hallucination(file_path=str(f), max_level=1, db_path=str(db))
        assert result["status"] == "pass"
        assert result["imports_checked"] == 3
        assert len(result["hallucinations"]) == 0
        assert len(result["verified"]) == 3

    def test_no_imports_pass(self, tmp_path):
        f = _write_file(tmp_path, "x = 1\ny = 2\n")
        db = tmp_path / "test.db"
        result = deep_hallucination(file_path=str(f), max_level=1, db_path=str(db))
        assert result["status"] == "pass"
        assert result["imports_checked"] == 0

    def test_from_import_pass(self, tmp_path):
        f = _write_file(tmp_path, "from os.path import join\n")
        db = tmp_path / "test.db"
        result = deep_hallucination(file_path=str(f), max_level=1, db_path=str(db))
        assert result["status"] == "pass"
        assert result["imports_checked"] == 1


# ── Hallucinated imports ─────────────────────────────────────────────


class TestHallucinatedImports:
    """Tests for files with hallucinated imports."""

    def test_fake_module_detected_level1(self, tmp_path):
        f = _write_file(tmp_path, "import fake_nonexistent_pkg_xyz\n")
        db = tmp_path / "test.db"
        result = deep_hallucination(file_path=str(f), max_level=1, db_path=str(db))
        assert result["status"] == "block"
        assert len(result["hallucinations"]) == 1
        h = result["hallucinations"][0]
        assert h["failed_level"] == 1
        assert "fake_nonexistent_pkg_xyz" in h["module"]

    def test_fake_module_detected_level2_via_api(self, tmp_path):
        f = _write_file(tmp_path, "import asdkjhqwelkjh\n")
        db = tmp_path / "test.db"
        with patch("core.hallucination_deep.urllib.request.urlopen", side_effect=_mock_urlopen_error):
            result = deep_hallucination(
                file_path=str(f), max_level=2, db_path=str(db),
            )
        # Network error → unverifiable (not hallucination)
        assert len(result["unverifiable"]) >= 1

    def test_hallucination_has_pedagogy(self, tmp_path):
        f = _write_file(tmp_path, "import fake_nonexistent_pkg_xyz\n")
        db = tmp_path / "test.db"
        result = deep_hallucination(file_path=str(f), max_level=1, db_path=str(db))
        for h in result["hallucinations"]:
            assert "pedagogy" in h
            p = h["pedagogy"]
            assert "why" in p
            assert "how_to_fix" in p
            assert "prevention" in p


# ── max_level control ────────────────────────────────────────────────


class TestMaxLevelControl:
    """Tests for max_level parameter behavior."""

    def test_max_level_1_no_api_call(self, tmp_path):
        f = _write_file(tmp_path, "import fake_nonexistent_pkg_xyz\n")
        db = tmp_path / "test.db"
        with patch("core.hallucination_deep.urllib.request.urlopen") as mock_open:
            result = deep_hallucination(file_path=str(f), max_level=1, db_path=str(db))
        mock_open.assert_not_called()
        assert result["status"] == "block"

    def test_max_level_3_checks_symbols(self, tmp_path):
        f = _write_file(tmp_path, "from os import fake_symbol_xyz\n")
        db = tmp_path / "test.db"
        result = deep_hallucination(file_path=str(f), max_level=3, db_path=str(db))
        assert result["status"] == "block"
        assert result["hallucinations"][0]["failed_level"] == 3

    def test_max_level_4_checks_version(self, tmp_path):
        f = _write_file(tmp_path, "from os import path\n")
        db = tmp_path / "test.db"
        result = deep_hallucination(file_path=str(f), max_level=4, db_path=str(db))
        assert result["status"] == "pass"

    def test_max_level_clamped_to_valid_range(self, tmp_path):
        """max_level outside 1-4 should return error (input validation)."""
        f = _write_file(tmp_path, "import os\n")
        db = tmp_path / "test.db"
        r1 = deep_hallucination(file_path=str(f), max_level=0, db_path=str(db))
        r2 = deep_hallucination(file_path=str(f), max_level=99, db_path=str(db))
        assert r1["status"] == "error"
        assert r2["status"] == "error"


# ── Error handling ───────────────────────────────────────────────────


class TestErrorHandling:
    """Tests for error cases."""

    def test_nonexistent_file(self, tmp_path):
        db = tmp_path / "test.db"
        result = deep_hallucination(
            file_path=str(tmp_path / "nope.py"), db_path=str(db),
        )
        assert result["status"] == "error"
        assert "does not exist" in result.get("error", "").lower()

    def test_syntax_error_file(self, tmp_path):
        f = _write_file(tmp_path, "def broken(\n")
        db = tmp_path / "test.db"
        result = deep_hallucination(file_path=str(f), db_path=str(db))
        assert result["status"] == "pass"
        assert result["imports_checked"] == 0


# ── Result structure ─────────────────────────────────────────────────


class TestResultStructure:
    """Tests for consistent result structure."""

    def test_result_has_required_keys(self, tmp_path):
        f = _write_file(tmp_path, "import os\n")
        db = tmp_path / "test.db"
        result = deep_hallucination(file_path=str(f), max_level=1, db_path=str(db))
        assert "status" in result
        assert "imports_checked" in result
        assert "hallucinations" in result
        assert "verified" in result
        assert "unverifiable" in result
        assert "pedagogy" in result

    def test_relative_imports_skipped(self, tmp_path):
        f = _write_file(tmp_path, "from . import sibling\nfrom .utils import helper\n")
        db = tmp_path / "test.db"
        result = deep_hallucination(file_path=str(f), max_level=1, db_path=str(db))
        assert result["imports_checked"] == 0
