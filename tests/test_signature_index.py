"""Tests for signature indexing."""
import tempfile
from pathlib import Path

from vibesrails.learner.signature_index import SignatureIndexer


def test_indexer_finds_functions():
    """Should index function signatures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create sample file with functions
        code_file = project / "utils.py"
        code_file.write_text('''
def validate_email(email: str) -> bool:
    """Validate email format."""
    return "@" in email

def parse_config(path: str) -> dict:
    """Parse config file."""
    return {}
''')

        indexer = SignatureIndexer(project)
        index = indexer.build_index()

        # Should find both functions
        assert len(index) == 2

        # Check validate_email signature
        validate_sig = next(s for s in index if s.name == "validate_email")
        assert validate_sig.file_path == "utils.py"
        assert validate_sig.line_number == 2
        assert "email" in validate_sig.parameters
        assert validate_sig.return_type == "bool"


def test_indexer_finds_classes():
    """Should index class signatures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        code_file = project / "models.py"
        code_file.write_text('''
class UserValidator:
    """Validates user data."""

    def validate(self, data: dict) -> bool:
        return True
''')

        indexer = SignatureIndexer(project)
        index = indexer.build_index()

        # Should find class and method
        class_sig = next(s for s in index if s.name == "UserValidator")
        assert class_sig.signature_type == "class"

        method_sig = next(s for s in index if s.name == "validate")
        assert method_sig.signature_type == "method"
        assert method_sig.parent_class == "UserValidator"


def test_indexer_search_finds_similar():
    """Should find similar function names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        (project / "utils.py").write_text('def validate_email(email: str) -> bool: pass')
        (project / "validators.py").write_text('def email_validator(email: str) -> bool: pass')

        indexer = SignatureIndexer(project)
        index = indexer.build_index()

        # Search for similar names
        similar = indexer.find_similar("validate_email", index)

        assert len(similar) >= 1
        # Should find email_validator as similar
        assert any("email" in s.name.lower() for s in similar)
