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
