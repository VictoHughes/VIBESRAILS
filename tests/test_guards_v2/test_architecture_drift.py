"""Tests for ArchitectureDriftGuard."""

import json
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from vibesrails.guards_v2.architecture_drift import (
    ArchitectureDriftGuard,
    _layer_for_dir,
    _allowed_deps,
)


@pytest.fixture
def guard():
    return ArchitectureDriftGuard()


@pytest.fixture
def layered_project(tmp_path):
    """Create a project with layered architecture."""
    # domain layer
    domain = tmp_path / "domain"
    domain.mkdir()
    (domain / "__init__.py").write_text("")
    (domain / "entity.py").write_text(
        "class User:\n    pass\n"
    )

    # services layer
    services = tmp_path / "services"
    services.mkdir()
    (services / "__init__.py").write_text("")
    (services / "user_service.py").write_text(
        "from domain.entity import User\n"
        "class UserService:\n"
        "    def get(self) -> User:\n"
        "        return User()\n"
    )

    # api layer (violates: imports domain directly)
    api = tmp_path / "api"
    api.mkdir()
    (api / "__init__.py").write_text("")
    (api / "routes.py").write_text(
        "from domain.entity import User\n"
        "def get_user():\n"
        "    return User()\n"
    )
    return tmp_path


# --- Layer detection ---

def test_layer_for_dir_domain():
    assert _layer_for_dir("domain") == "domain"
    assert _layer_for_dir("models") == "domain"


def test_layer_for_dir_service():
    assert _layer_for_dir("services") == "service"
    assert _layer_for_dir("application") == "service"


def test_layer_for_dir_presentation():
    assert _layer_for_dir("api") == "presentation"
    assert _layer_for_dir("routes") == "presentation"
    assert _layer_for_dir("views") == "presentation"


def test_layer_for_dir_infra():
    assert _layer_for_dir("infrastructure") == "infrastructure"
    assert _layer_for_dir("adapters") == "infrastructure"


def test_layer_for_dir_unknown():
    assert _layer_for_dir("utils") is None


def test_allowed_deps():
    assert _allowed_deps("domain") == []
    assert _allowed_deps("service") == ["domain"]
    assert _allowed_deps("presentation") == ["service"]
    assert _allowed_deps("infrastructure") == ["domain"]


def test_detect_layers(guard, layered_project):
    layers = guard.detect_layers(layered_project)
    assert layers["domain"] == "domain"
    assert layers["services"] == "service"
    assert layers["api"] == "presentation"


# --- Re-export detection ---

def test_reexport_detected(guard, tmp_path):
    """Module that only re-exports should be flagged."""
    mod = tmp_path / "reexporter.py"
    mod.write_text(textwrap.dedent("""\
        from domain.entity import User
        from domain.entity import Order
        from services.user_service import UserService
        from services.order_service import OrderService
        __all__ = ["User", "Order", "UserService", "OrderService"]
    """))
    issues = guard._detect_reexport_modules(tmp_path)
    assert len(issues) == 1
    assert "Re-export" in issues[0].message


def test_reexport_not_flagged_normal_module(guard, tmp_path):
    """Normal module with code should not be flagged."""
    mod = tmp_path / "normal.py"
    mod.write_text(textwrap.dedent("""\
        from os import path
        def do_work():
            return path.exists("/tmp")
        def more_work():
            return 42
    """))
    issues = guard._detect_reexport_modules(tmp_path)
    assert len(issues) == 0


# --- Wrapper class detection ---

def test_wrapper_detected(guard, tmp_path):
    """Class delegating all methods should be flagged."""
    mod = tmp_path / "wrapper.py"
    mod.write_text(textwrap.dedent("""\
        class UserWrapper:
            def __init__(self, inner):
                self._inner = inner
            def get_name(self):
                return self._inner.get_name()
            def get_email(self):
                return self._inner.get_email()
            def save(self):
                return self._inner.save()
    """))
    issues = guard._detect_wrapper_classes(tmp_path)
    assert len(issues) == 1
    assert "UserWrapper" in issues[0].message


def test_wrapper_not_flagged_real_class(guard, tmp_path):
    """Class with real logic should not be flagged."""
    mod = tmp_path / "real.py"
    mod.write_text(textwrap.dedent("""\
        class RealService:
            def __init__(self):
                self.data = []
            def add(self, item):
                self.data.append(item)
                return len(self.data)
            def clear(self):
                self.data = []
                return True
    """))
    issues = guard._detect_wrapper_classes(tmp_path)
    assert len(issues) == 0


# --- Function-level import detection ---

def test_function_level_import_detected(guard, tmp_path):
    """Import inside function of layer module should flag."""
    mod = tmp_path / "sneaky.py"
    mod.write_text(textwrap.dedent("""\
        def get_entity():
            from domain.entity import Entity
            return Entity()
    """))
    issues = guard._detect_function_level_imports(tmp_path)
    assert len(issues) == 1
    assert "domain.entity" in issues[0].message


def test_function_level_import_non_layer_ok(guard, tmp_path):
    """Import of non-layer module inside function is OK."""
    mod = tmp_path / "ok.py"
    mod.write_text(textwrap.dedent("""\
        def compute():
            from math import sqrt
            return sqrt(4)
    """))
    issues = guard._detect_function_level_imports(tmp_path)
    assert len(issues) == 0


# --- TYPE_CHECKING bypass ---

def test_type_checking_bypass_detected(guard, tmp_path):
    """TYPE_CHECKING import of layer module should flag."""
    mod = tmp_path / "typed.py"
    mod.write_text(textwrap.dedent("""\
        from __future__ import annotations
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from domain.entity import User
        def process(u: "User") -> None:
            pass
    """))
    issues = guard._detect_type_checking_bypass(tmp_path)
    assert len(issues) == 1
    assert "TYPE_CHECKING" in issues[0].message


def test_type_checking_normal_import_ok(guard, tmp_path):
    """TYPE_CHECKING with non-layer import is OK."""
    mod = tmp_path / "ok_typed.py"
    mod.write_text(textwrap.dedent("""\
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from collections import OrderedDict
    """))
    issues = guard._detect_type_checking_bypass(tmp_path)
    assert len(issues) == 0


# --- Drift tracking ---

def test_drift_tracking_first_run(guard, tmp_path):
    """First run should record but not warn."""
    issues = guard._track_drift(tmp_path, 3)
    assert len(issues) == 0
    drift_file = (
        tmp_path / ".vibesrails" / "metrics"
        / "architecture_drift.jsonl"
    )
    assert drift_file.exists()
    data = json.loads(drift_file.read_text().strip())
    assert data["violations"] == 3


def test_drift_tracking_increasing(guard, tmp_path):
    """Increasing violations should warn."""
    guard._track_drift(tmp_path, 2)
    issues = guard._track_drift(tmp_path, 5)
    assert len(issues) == 1
    assert "increasing" in issues[0].message.lower()


def test_drift_tracking_decreasing(guard, tmp_path):
    """Decreasing violations should not warn."""
    guard._track_drift(tmp_path, 5)
    issues = guard._track_drift(tmp_path, 3)
    assert len(issues) == 0


def test_drift_tracking_stable(guard, tmp_path):
    """Stable violations should not warn."""
    guard._track_drift(tmp_path, 3)
    issues = guard._track_drift(tmp_path, 3)
    assert len(issues) == 0


# --- Snapshot ---

def test_snapshot_save_load(guard, layered_project):
    """Snapshot should save and be loadable."""
    path = guard.take_snapshot(layered_project)
    assert path.exists()
    data = json.loads(path.read_text())
    assert isinstance(data, dict)
    assert len(data) > 0


def test_snapshot_contains_imports(guard, tmp_path):
    """Snapshot should capture import relationships."""
    mod = tmp_path / "example.py"
    mod.write_text("from os import path\nimport json\n")
    path = guard.take_snapshot(tmp_path)
    data = json.loads(path.read_text())
    assert "example.py" in data
    assert "os" in data["example.py"]
    assert "json" in data["example.py"]


# --- Import-linter integration ---

def test_linter_with_violations(guard, tmp_path):
    """Linter violations should be reported."""
    config = tmp_path / ".importlinter"
    config.write_text("[importlinter]\nroot_package=app\n")
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = (
        "Contract: layers BROKEN\n"
        "api imports domain (violated)\n"
    )
    with patch("subprocess.run", return_value=mock_result):
        issues = guard.scan_with_linter(tmp_path)
    assert len(issues) >= 1
    assert any("BROKEN" in i.message for i in issues)


def test_linter_clean(guard, tmp_path):
    """Clean linter run returns no issues."""
    config = tmp_path / ".importlinter"
    config.write_text("[importlinter]\nroot_package=app\n")
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "All contracts OK\n"
    with patch("subprocess.run", return_value=mock_result):
        issues = guard.scan_with_linter(tmp_path)
    assert len(issues) == 0


def test_linter_not_installed(guard, tmp_path):
    """Missing linter should not crash."""
    config = tmp_path / ".importlinter"
    config.write_text("[importlinter]\nroot_package=app\n")
    with patch(
        "subprocess.run", side_effect=FileNotFoundError
    ):
        issues = guard.scan_with_linter(tmp_path)
    assert len(issues) == 0


# --- Auto-config generation ---

def test_auto_generate_config(guard, tmp_path):
    """Should generate config for layered project."""
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "__init__.py").write_text("")
    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "__init__.py").write_text("")
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "__init__.py").write_text("")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=""
        )
        issues = guard.scan_with_linter(tmp_path)
    config = tmp_path / ".importlinter"
    assert config.exists()
    content = config.read_text()
    assert "importlinter" in content


# --- Full scan ---

def test_full_scan_clean(guard, tmp_path):
    """Clean project returns no block issues."""
    mod = tmp_path / "clean.py"
    mod.write_text("def hello():\n    return 42\n")
    issues = guard.scan(tmp_path)
    block_issues = [i for i in issues if i.severity == "block"]
    assert len(block_issues) == 0


def test_full_scan_with_issues(guard, tmp_path):
    """Project with bypasses should return issues."""
    mod = tmp_path / "sneaky.py"
    mod.write_text(textwrap.dedent("""\
        def get_entity():
            from domain.entity import Entity
            return Entity()
    """))
    issues = guard.scan(tmp_path)
    warn_issues = [i for i in issues if i.severity == "warn"]
    assert len(warn_issues) >= 1


# --- Report ---

def test_report_clean(guard, tmp_path):
    """Clean project report."""
    mod = tmp_path / "clean.py"
    mod.write_text("x = 1\n")
    report = guard.generate_report(tmp_path)
    assert "OK" in report


def test_report_with_issues(guard, tmp_path):
    """Report with issues should list them."""
    mod = tmp_path / "sneaky.py"
    mod.write_text(textwrap.dedent("""\
        def get_entity():
            from domain.entity import Entity
            return Entity()
    """))
    report = guard.generate_report(tmp_path)
    assert "issues" in report.lower() or "Issue" in report


# --- Edge cases ---

def test_empty_project(guard, tmp_path):
    """Empty project should not crash."""
    issues = guard.scan(tmp_path)
    assert isinstance(issues, list)


def test_syntax_error_file(guard, tmp_path):
    """File with syntax error should be skipped."""
    mod = tmp_path / "broken.py"
    mod.write_text("def broken(\n")
    issues = guard.scan(tmp_path)
    assert isinstance(issues, list)


def test_wrapper_single_method_not_flagged(guard, tmp_path):
    """Class with only 1 non-init method not flagged."""
    mod = tmp_path / "small_wrapper.py"
    mod.write_text(textwrap.dedent("""\
        class Tiny:
            def __init__(self, inner):
                self._inner = inner
            def do(self):
                return self._inner.do()
    """))
    issues = guard._detect_wrapper_classes(tmp_path)
    assert len(issues) == 0
