"""Tests for detect_project_type() in vibesrails.context.detector."""

from __future__ import annotations

from pathlib import Path

from vibesrails.context.detector import detect_project_type


def test_detect_web_flask(tmp_path: Path) -> None:
    """requirements.txt with flask → web."""
    (tmp_path / "requirements.txt").write_text("flask==3.0\nwerkzeug\n")
    assert detect_project_type(tmp_path) == "web"


def test_detect_web_django(tmp_path: Path) -> None:
    """manage.py present → web (Django project)."""
    (tmp_path / "manage.py").write_text("# Django manage script\n")
    assert detect_project_type(tmp_path) == "web"


def test_detect_web_fastapi(tmp_path: Path) -> None:
    """requirements.txt with fastapi + uvicorn → web."""
    (tmp_path / "requirements.txt").write_text("fastapi\nuvicorn\n")
    assert detect_project_type(tmp_path) == "web"


def test_detect_cli(tmp_path: Path) -> None:
    """pyproject.toml with [project.scripts] and no web/ml/data deps → cli."""
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'mytool'\n\n[project.scripts]\nmytool = 'mytool.cli:main'\n"
    )
    assert detect_project_type(tmp_path) == "cli"


def test_detect_library(tmp_path: Path) -> None:
    """pyproject.toml + src/ dir, no markers → library."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'mylib'\n")
    (tmp_path / "src").mkdir()
    assert detect_project_type(tmp_path) == "library"


def test_detect_ml(tmp_path: Path) -> None:
    """requirements.txt with torch + transformers → ml."""
    (tmp_path / "requirements.txt").write_text("torch\ntransformers\n")
    assert detect_project_type(tmp_path) == "ml"


def test_detect_data(tmp_path: Path) -> None:
    """requirements.txt with pandas + scipy → data."""
    (tmp_path / "requirements.txt").write_text("pandas\nscipy\n")
    assert detect_project_type(tmp_path) == "data"


def test_detect_unknown(tmp_path: Path) -> None:
    """Only README.md present → unknown."""
    (tmp_path / "README.md").write_text("# My project\n")
    assert detect_project_type(tmp_path) == "unknown"
