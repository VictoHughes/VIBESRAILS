"""Tests for ObservabilityGuard — real files, real AST parsing, no mocking."""

from pathlib import Path

import pytest

from vibesrails.guards_v2.observability import ObservabilityGuard


@pytest.fixture
def guard():
    return ObservabilityGuard()


@pytest.fixture
def src(tmp_path_factory):
    """Return a directory whose full path has no 'test_*' component.

    pytest's default ``tmp_path`` lives under a directory named after the
    test function (e.g. ``test_bare_print0/``), which the observability
    guard's ``_should_skip`` glob ``**/test_*`` matches.  We work around
    this by creating a temp directory with a neutral basename.
    """
    d = tmp_path_factory.mktemp("obs_src", numbered=True)
    return d


def _write(directory: Path, name: str, content: str) -> Path:
    """Write a Python file and return its path."""
    f = directory / name
    f.write_text(content, encoding="utf-8")
    return f


def _issues_for(guard, directory, name, content):
    """Write file, scan directory, return issues."""
    _write(directory, name, content)
    return guard.scan(directory)


def _msgs(issues):
    return [i.message for i in issues]


# ------------------------------------------------------------------
# print() detection
# ------------------------------------------------------------------

class TestBarePrint:
    def test_bare_print_detected(self, guard, src):
        issues = _issues_for(guard, src, "service.py", 'print("hello")\n')
        assert any("print()" in m for m in _msgs(issues))

    def test_print_with_fstring(self, guard, src):
        issues = _issues_for(guard, src, "service.py", 'print(f"val={1}")\n')
        assert any("print()" in m for m in _msgs(issues))

    def test_print_multiple_args(self, guard, src):
        issues = _issues_for(guard, src, "service.py", 'print("a", "b")\n')
        assert any("print()" in m for m in _msgs(issues))


# ------------------------------------------------------------------
# CLI / test / conftest files are skipped
# ------------------------------------------------------------------

class TestSkipFiles:
    def test_cli_file_skipped(self, guard, src):
        issues = _issues_for(guard, src, "cli.py", 'print("usage")\n')
        assert issues == []

    def test_cli_subcommand_skipped(self, guard, src):
        issues = _issues_for(guard, src, "cli_run.py", 'print("ok")\n')
        assert issues == []

    def test_main_file_skipped(self, guard, src):
        issues = _issues_for(guard, src, "__main__.py", 'print("start")\n')
        assert issues == []

    def test_test_file_skipped(self, guard, src):
        issues = _issues_for(guard, src, "test_foo.py", 'print("debug")\n')
        assert issues == []

    def test_conftest_skipped(self, guard, src):
        issues = _issues_for(guard, src, "conftest.py", 'print("setup")\n')
        assert issues == []


# ------------------------------------------------------------------
# traceback.print_exc()
# ------------------------------------------------------------------

class TestTracebackPrintExc:
    def test_traceback_print_exc_detected(self, guard, src):
        code = (
            "import traceback\n"
            "try:\n"
            "    pass\n"
            "except Exception:\n"
            "    traceback.print_exc()\n"
        )
        issues = _issues_for(guard, src, "handler.py", code)
        assert any("traceback.print_exc" in m for m in _msgs(issues))


# ------------------------------------------------------------------
# Silent except blocks
# ------------------------------------------------------------------

class TestSilentExcept:
    def test_except_pass_detected(self, guard, src):
        code = (
            "try:\n"
            "    do_stuff()\n"
            "except Exception:\n"
            "    pass\n"
        )
        issues = _issues_for(guard, src, "worker.py", code)
        assert any("silent" in m for m in _msgs(issues))

    def test_except_with_logging_ok(self, guard, src):
        code = (
            "try:\n"
            "    do_stuff()\n"
            "except Exception:\n"
            "    logger.error('fail')\n"
        )
        issues = _issues_for(guard, src, "worker.py", code)
        silent = [m for m in _msgs(issues) if "silent" in m]
        assert silent == []

    def test_except_with_raise_ok(self, guard, src):
        code = (
            "try:\n"
            "    x()\n"
            "except ValueError:\n"
            "    raise\n"
        )
        issues = _issues_for(guard, src, "worker.py", code)
        silent = [m for m in _msgs(issues) if "silent" in m]
        assert silent == []


# ------------------------------------------------------------------
# logging.log() without level
# ------------------------------------------------------------------

class TestLoggingWithoutLevel:
    def test_logging_log_no_level(self, guard, src):
        code = 'import logging\nlogging.log("oops")\n'
        issues = _issues_for(guard, src, "app.py", code)
        assert any("without explicit level" in m for m in _msgs(issues))

    def test_logging_log_with_level_ok(self, guard, src):
        code = "import logging\nlogging.log(logging.WARNING, 'msg')\n"
        issues = _issues_for(guard, src, "app.py", code)
        lvl = [m for m in _msgs(issues) if "without explicit level" in m]
        assert lvl == []


# ------------------------------------------------------------------
# print() used as logging (DEBUG:/ERROR: patterns)
# ------------------------------------------------------------------

class TestPrintAsLogging:
    def test_print_debug_pattern(self, guard, src):
        code = 'print(f"DEBUG: value={1}")\n'
        issues = _issues_for(guard, src, "app.py", code)
        assert any("print() used as logging" in m for m in _msgs(issues))

    def test_print_error_pattern(self, guard, src):
        code = 'print("ERROR: something broke")\n'
        issues = _issues_for(guard, src, "app.py", code)
        msgs = _msgs(issues)
        assert any("print()" in m for m in msgs)


# ------------------------------------------------------------------
# Clean code should not trigger
# ------------------------------------------------------------------

class TestCleanCode:
    def test_proper_logging_no_issues(self, guard, src):
        code = (
            "import logging\n"
            "logger = logging.getLogger(__name__)\n"
            "logger.info('started')\n"
        )
        issues = _issues_for(guard, src, "clean.py", code)
        assert issues == []

    def test_empty_file_no_issues(self, guard, src):
        issues = _issues_for(guard, src, "empty.py", "")
        assert issues == []
