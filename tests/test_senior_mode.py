"""Tests for Senior Mode."""
import pytest
from pathlib import Path


class TestArchitectureMapper:
    """Tests for ArchitectureMapper."""

    def test_generate_map_returns_markdown(self, tmp_path):
        """generate_map returns valid markdown string."""
        from vibesrails.senior_mode import ArchitectureMapper

        # Create minimal project structure
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "utils.py").write_text("def helper(): pass")

        mapper = ArchitectureMapper(tmp_path)
        result = mapper.generate_map()

        assert isinstance(result, str)
        assert "# Architecture Map" in result
        assert "main.py" in result

    def test_generate_map_includes_classes_and_functions(self, tmp_path):
        """generate_map includes class and function info."""
        from vibesrails.senior_mode import ArchitectureMapper

        (tmp_path / "models.py").write_text("""
class User:
    pass

class Order:
    pass

def create_user():
    pass
""")

        mapper = ArchitectureMapper(tmp_path)
        result = mapper.generate_map()

        assert "User" in result
        assert "models.py" in result

    def test_save_creates_architecture_md(self, tmp_path):
        """save() creates ARCHITECTURE.md file."""
        from vibesrails.senior_mode import ArchitectureMapper

        (tmp_path / "app.py").write_text("def run(): pass")

        mapper = ArchitectureMapper(tmp_path)
        output_path = mapper.save()

        assert output_path.exists()
        assert output_path.name == "ARCHITECTURE.md"
        content = output_path.read_text()
        assert "# Architecture Map" in content

    def test_identifies_sensitive_zones(self, tmp_path):
        """Sensitive files are marked in output."""
        from vibesrails.senior_mode import ArchitectureMapper

        (tmp_path / "auth.py").write_text("def login(): pass")
        (tmp_path / "utils.py").write_text("def format(): pass")

        mapper = ArchitectureMapper(tmp_path)
        result = mapper.generate_map()

        assert "auth.py" in result
        assert "Sensitive" in result or "sensitive" in result.lower()
