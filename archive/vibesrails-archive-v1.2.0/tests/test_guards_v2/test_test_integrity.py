"""Tests for TestIntegrityGuard — using real files, no mocks."""

import textwrap
from pathlib import Path

from vibesrails.guards_v2.test_integrity import (
    TestIntegrityGuard,
)

guard = TestIntegrityGuard()


# ── Mock ratio detection ────────────────────────────────────


def test_high_mock_ratio_warns(tmp_path: Path) -> None:
    """File with >60% mocked tests triggers warn."""
    code = textwrap.dedent("""\
        from unittest.mock import patch, MagicMock

        def test_a():
            m = MagicMock()
            assert m.called is not None

        def test_b():
            m = MagicMock()
            assert m

        def test_c():
            m = MagicMock()
            assert True or m

        def test_d():
            m = MagicMock()
            assert m

        def test_real():
            assert 1 + 1 == 2

        def test_real2():
            assert "hello".upper() == "HELLO"
    """)
    f = tmp_path / "test_example.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    warns = [i for i in issues if "mock too much" in i.message]
    assert len(warns) == 1
    assert warns[0].severity == "warn"


def test_very_high_mock_ratio_blocks(tmp_path: Path) -> None:
    """File with >80% mocked tests triggers block."""
    code = textwrap.dedent("""\
        from unittest.mock import MagicMock

        def test_a():
            m = MagicMock()
            assert m

        def test_b():
            m = MagicMock()
            assert m

        def test_c():
            m = MagicMock()
            assert m

        def test_d():
            m = MagicMock()
            assert m

        def test_e():
            m = MagicMock()
            assert m
    """)
    f = tmp_path / "test_foo.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    blocks = [
        i for i in issues
        if "mock too much" in i.message and i.severity == "block"
    ]
    assert len(blocks) == 1


def test_low_mock_ratio_ok(tmp_path: Path) -> None:
    """File with <60% mocked tests has no mock-ratio issue."""
    code = textwrap.dedent("""\
        def test_a():
            assert 1 + 1 == 2

        def test_b():
            assert "x".upper() == "X"

        def test_c():
            assert [1, 2, 3]
    """)
    f = tmp_path / "test_clean.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    mock_issues = [i for i in issues if "mock too much" in i.message]
    assert mock_issues == []


# ── SUT mocking detection ───────────────────────────────────


def test_sut_mocking_detected(tmp_path: Path) -> None:
    """Mocking the module under test triggers block."""
    code = textwrap.dedent("""\
        from unittest.mock import patch

        def test_thing():
            with patch("myapp.scanner.do_scan"):
                assert True
    """)
    f = tmp_path / "test_scanner.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    sut = [i for i in issues if "mocks the code" in i.message]
    assert len(sut) == 1
    assert sut[0].severity == "block"


def test_sut_mocking_decorator(tmp_path: Path) -> None:
    """Decorator-style patch of SUT also detected."""
    code = textwrap.dedent("""\
        from unittest.mock import patch

        @patch("myapp.config.load")
        def test_load(mock_load):
            assert mock_load
    """)
    f = tmp_path / "test_config.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    sut = [i for i in issues if "mocks the code" in i.message]
    assert len(sut) >= 1


def test_mocking_other_module_ok(tmp_path: Path) -> None:
    """Mocking a different module is fine."""
    code = textwrap.dedent("""\
        from unittest.mock import patch
        import scanner

        def test_thing():
            with patch("requests.get"):
                assert scanner
    """)
    f = tmp_path / "test_scanner.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    sut = [i for i in issues if "mocks the code" in i.message]
    assert sut == []


# ── Assert-free detection ───────────────────────────────────


def test_assert_free_detected(tmp_path: Path) -> None:
    """Test with no assertions triggers block."""
    code = textwrap.dedent("""\
        def test_noop():
            x = 1 + 1
            print(x)
    """)
    f = tmp_path / "test_noop.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    af = [i for i in issues if "no assertions" in i.message]
    assert len(af) == 1
    assert af[0].severity == "block"


def test_pytest_raises_counts_as_assert(tmp_path: Path) -> None:
    """pytest.raises counts as an assertion."""
    code = textwrap.dedent("""\
        import pytest

        def test_raises():
            with pytest.raises(ValueError):
                int("not a number")
    """)
    f = tmp_path / "test_raises.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    af = [i for i in issues if "no assertions" in i.message]
    assert af == []


def test_assert_present_ok(tmp_path: Path) -> None:
    """Test with assert is not flagged as assert-free."""
    code = textwrap.dedent("""\
        def test_ok():
            assert 1 + 1 == 2
    """)
    f = tmp_path / "test_ok.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    af = [i for i in issues if "no assertions" in i.message]
    assert af == []


# ── Trivial assertions ──────────────────────────────────────


def test_trivial_assert_true(tmp_path: Path) -> None:
    """assert True is trivial."""
    code = textwrap.dedent("""\
        def test_lazy():
            assert True
    """)
    f = tmp_path / "test_lazy.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    triv = [i for i in issues if "Trivial assertion" in i.message]
    assert len(triv) == 1
    assert triv[0].severity == "warn"


def test_trivial_assert_equal_constants(tmp_path: Path) -> None:
    """assert 1 == 1 is trivial."""
    code = textwrap.dedent("""\
        def test_lazy():
            assert 1 == 1
    """)
    f = tmp_path / "test_lazy.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    triv = [i for i in issues if "Trivial assertion" in i.message]
    assert len(triv) == 1


def test_trivial_isinstance_object(tmp_path: Path) -> None:
    """assert isinstance(x, object) is trivial."""
    code = textwrap.dedent("""\
        def test_lazy():
            x = 42
            assert isinstance(x, object)
    """)
    f = tmp_path / "test_lazy.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    triv = [i for i in issues if "Trivial assertion" in i.message]
    assert len(triv) == 1


def test_real_assertion_not_trivial(tmp_path: Path) -> None:
    """Real assertions are not flagged."""
    code = textwrap.dedent("""\
        def test_real():
            assert 1 + 1 == 2
    """)
    f = tmp_path / "test_real.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    triv = [i for i in issues if "Trivial assertion" in i.message]
    assert triv == []


# ── Mock echo detection ─────────────────────────────────────


def test_mock_echo_detected(tmp_path: Path) -> None:
    """Mock return_value == assertion → warn."""
    code = textwrap.dedent("""\
        from unittest.mock import MagicMock

        def test_echo():
            m = MagicMock()
            m.return_value = 42
            result = m()
            assert result == 42
    """)
    f = tmp_path / "test_echo.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    echo = [i for i in issues if "mock returns what" in i.message]
    assert len(echo) == 1
    assert echo[0].severity == "warn"


def test_mock_echo_different_values_ok(tmp_path: Path) -> None:
    """Different mock return vs assertion is fine."""
    code = textwrap.dedent("""\
        from unittest.mock import MagicMock

        def test_transform():
            m = MagicMock()
            m.return_value = 10
            result = m() * 2
            assert result == 20
    """)
    f = tmp_path / "test_transform.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    echo = [i for i in issues if "mock returns what" in i.message]
    assert echo == []


# ── Missing imports detection ────────────────────────────────


def test_missing_imports_detected(tmp_path: Path) -> None:
    """Test file that doesn't import source package → warn."""
    code = textwrap.dedent("""\
        def test_nothing():
            assert 1 == 1
    """)
    f = tmp_path / "test_scanner.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    mi = [i for i in issues if "doesn't import" in i.message]
    assert len(mi) == 1


def test_has_imports_ok(tmp_path: Path) -> None:
    """Test file with source import is fine."""
    code = textwrap.dedent("""\
        from myapp import scanner

        def test_scan():
            assert scanner is not None
    """)
    f = tmp_path / "test_scanner.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    mi = [i for i in issues if "doesn't import" in i.message]
    assert mi == []


# ── Full scan integration ───────────────────────────────────


def test_scan_no_integration_tests(tmp_path: Path) -> None:
    """All-mocked test dir triggers integration warning."""
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    for name in ("test_a.py", "test_b.py"):
        (test_dir / name).write_text(textwrap.dedent("""\
            from unittest.mock import MagicMock

            def test_x():
                m = MagicMock()
                assert m
        """))
    issues = guard.scan(tmp_path)
    integ = [
        i for i in issues if "No integration tests" in i.message
    ]
    assert len(integ) == 1
    assert integ[0].severity == "warn"


def test_scan_with_integration_tests_ok(tmp_path: Path) -> None:
    """Dir with real tests does NOT trigger integration warn."""
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_unit.py").write_text(textwrap.dedent("""\
        from unittest.mock import MagicMock

        def test_mocked():
            m = MagicMock()
            assert m
    """))
    (test_dir / "test_integ.py").write_text(textwrap.dedent("""\
        import os

        def test_real_a():
            assert os.path.exists(".")

        def test_real_b():
            assert 1 + 1 == 2

        def test_real_c():
            assert "hello"
    """))
    issues = guard.scan(tmp_path)
    integ = [
        i for i in issues if "No integration tests" in i.message
    ]
    assert integ == []


# ── Good test file produces no issues ────────────────────────


def test_good_test_file_clean(tmp_path: Path) -> None:
    """A well-written test file produces no issues."""
    code = textwrap.dedent("""\
        from myapp import utils

        def test_add():
            assert utils is not None

        def test_upper():
            assert "hi".upper() == "HI"

        def test_list():
            assert [1, 2, 3]
    """)
    f = tmp_path / "test_utils.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    assert issues == []


# ── Non-test files are skipped ──────────────────────────────


def test_non_test_file_skipped(tmp_path: Path) -> None:
    """Files not starting with test_ are skipped."""
    code = "x = 1\n"
    f = tmp_path / "helper.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    assert issues == []


# ── Syntax error files handled ──────────────────────────────


def test_syntax_error_file_skipped(tmp_path: Path) -> None:
    """Files with syntax errors return empty list."""
    code = "def broken(:\n"
    f = tmp_path / "test_broken.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    assert issues == []


# ── Edge: empty test file ───────────────────────────────────


def test_empty_test_file(tmp_path: Path) -> None:
    """Empty test file produces no crash."""
    code = "# empty\n"
    f = tmp_path / "test_empty.py"
    f.write_text(code)
    issues = guard.scan_file(f, code)
    assert isinstance(issues, list)
