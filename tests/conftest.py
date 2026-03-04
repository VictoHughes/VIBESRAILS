"""Shared test fixtures for vibesrails tests."""

import logging
import os
import sys

import pytest

# Disable rate limiting for all tests by default.
# Individual tests that need to test rate limiting should
# monkeypatch this back to None or "1".
os.environ.setdefault("VIBESRAILS_RATE_LIMIT", "0")


class _StdoutHandler(logging.Handler):
    """A handler that always writes to the *current* sys.stdout.

    Unlike StreamHandler(sys.stdout), this resolves sys.stdout at emit-time
    so it works with pytest's capsys fixture.
    """

    def __init__(self):
        super().__init__()

    def emit(self, record):
        try:
            msg = self.format(record)
            sys.stdout.write(msg + "\n")
            sys.stdout.flush()
        except Exception:
            self.handleError(record)


@pytest.fixture(autouse=True)
def _setup_logging():
    """Route all vibesrails loggers to stdout so capsys can capture them."""
    handler = _StdoutHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger("vibesrails")
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    root_logger.propagate = False

    yield

    root_logger.removeHandler(handler)


# ============================================
# Scanner fixtures (shared across test_scanner_*.py)
# ============================================


@pytest.fixture
def sample_config():
    """Minimal config for testing."""
    return {
        "version": "1.0",
        "blocking": [
            {
                "id": "test_secret",
                "name": "Test Secret",
                "regex": r"password\s*=\s*[\"'][^\"']+",
                "message": "Hardcoded password",
            }
        ],
        "warning": [
            {
                "id": "test_print",
                "name": "Print Statement",
                "regex": r"^\s*print\(",
                "message": "Use logging instead",
                "skip_in_tests": True,
            }
        ],
        "exceptions": {},
    }


@pytest.fixture
def config_with_scope():
    """Config with scope filtering."""
    return {
        "version": "1.0",
        "blocking": [
            {
                "id": "api_only",
                "name": "API Pattern",
                "regex": r"api_secret",
                "message": "API secret detected",
                "scope": ["**/api/**", "api_*.py"],
            }
        ],
        "warning": [],
        "exceptions": {},
    }


@pytest.fixture
def config_with_exclude():
    """Config with exclude_regex."""
    return {
        "version": "1.0",
        "blocking": [
            {
                "id": "dangerous_call",
                "name": "Dangerous Call",
                "regex": r"dangerous_func\(",
                "message": "Avoid dangerous_func",
                "exclude_regex": r"#.*safe.*call",
            }
        ],
        "warning": [],
        "exceptions": {},
    }


@pytest.fixture
def config_with_pro_sections():
    """Config with bugs, architecture, maintainability sections."""
    return {
        "version": "1.0",
        "blocking": [],
        "warning": [],
        "bugs": [
            {
                "id": "bug1",
                "name": "Bug Pattern",
                "regex": r"bug_pattern",
                "message": "Bug detected",
                "level": "BLOCK",
            },
            {
                "id": "bug2",
                "name": "Bug Warning",
                "regex": r"bug_warn",
                "message": "Bug warning",
                "level": "WARN",
            },
        ],
        "architecture": [
            {
                "id": "arch1",
                "name": "Arch Pattern",
                "regex": r"arch_issue",
                "message": "Architecture issue",
                "level": "WARN",
            }
        ],
        "maintainability": [
            {
                "id": "maint1",
                "name": "Maint Pattern",
                "regex": r"maint_issue",
                "message": "Maintainability issue",
            }
        ],
        "exceptions": {},
    }


@pytest.fixture
def config_with_exceptions():
    """Config with file exceptions."""
    return {
        "version": "1.0",
        "blocking": [
            {
                "id": "test_secret",
                "name": "Test Secret",
                "regex": r"password\s*=",
                "message": "Hardcoded password",
            }
        ],
        "warning": [],
        "exceptions": {
            "test_files": {
                "reason": "Test files can have hardcoded values",
                "patterns": ["**/test_*.py", "**/conftest.py"],
                "allowed": ["test_secret"],
            }
        },
    }
