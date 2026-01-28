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


class TestGuards:
    """Tests for Senior Mode guards."""

    def test_diff_size_guard_warns_on_large_diff(self):
        """DiffSizeGuard warns when diff exceeds threshold."""
        from vibesrails.senior_mode.guards import DiffSizeGuard

        guard = DiffSizeGuard(max_lines=100)
        large_diff = "\n".join([f"+line{i}" for i in range(150)])

        issues = guard.check(large_diff)

        assert len(issues) == 1
        assert "150" in issues[0].message

    def test_diff_size_guard_passes_small_diff(self):
        """DiffSizeGuard passes when diff is small."""
        from vibesrails.senior_mode.guards import DiffSizeGuard

        guard = DiffSizeGuard(max_lines=100)
        small_diff = "\n".join([f"+line{i}" for i in range(50)])

        issues = guard.check(small_diff)

        assert len(issues) == 0

    def test_error_handling_guard_detects_bare_except(self):
        """ErrorHandlingGuard detects bare except clauses."""
        from vibesrails.senior_mode.guards import ErrorHandlingGuard

        guard = ErrorHandlingGuard()
        code = '''
try:
    risky()
except:
    pass
'''
        issues = guard.check(code, "test.py")

        assert len(issues) >= 1
        assert any("except" in i.message.lower() for i in issues)

    def test_hallucination_guard_detects_missing_import(self):
        """HallucinationGuard detects imports that don't exist."""
        from vibesrails.senior_mode.guards import HallucinationGuard

        guard = HallucinationGuard()
        code = "from nonexistent_module_xyz import something"

        issues = guard.check(code, "test.py")

        assert len(issues) >= 1
        assert "nonexistent_module_xyz" in issues[0].message

    def test_dependency_guard_detects_new_deps(self):
        """DependencyGuard detects new dependencies added."""
        from vibesrails.senior_mode.guards import DependencyGuard

        guard = DependencyGuard()
        old_reqs = "requests==2.28.0\n"
        new_reqs = "requests==2.28.0\nnew-package==1.0.0\n"

        issues = guard.check(old_reqs, new_reqs)

        assert len(issues) == 1
        assert "new-package" in issues[0].message

    def test_test_coverage_guard_warns_no_tests(self):
        """TestCoverageGuard warns when code added without tests."""
        from vibesrails.senior_mode.guards import TestCoverageGuard

        guard = TestCoverageGuard(min_ratio=0.5)
        code_diff = "\n".join([f"+def func{i}(): pass" for i in range(30)])
        test_diff = ""

        issues = guard.check(code_diff, test_diff)

        assert len(issues) == 1
        assert "test" in issues[0].message.lower()


class TestClaudeReviewer:
    """Tests for targeted Claude review."""

    def test_should_review_sensitive_file(self):
        """ClaudeReviewer triggers on sensitive files."""
        from vibesrails.senior_mode.claude_reviewer import ClaudeReviewer

        reviewer = ClaudeReviewer()

        assert reviewer.should_review("auth/login.py", "+def login(): pass") is True
        assert reviewer.should_review("utils/helpers.py", "+def format(): pass") is False

    def test_should_review_complex_diff(self):
        """ClaudeReviewer triggers on complex changes."""
        from vibesrails.senior_mode.claude_reviewer import ClaudeReviewer

        reviewer = ClaudeReviewer()
        complex_diff = "\n".join([f"+    if x > {i}: return {i}" for i in range(50)])

        assert reviewer.should_review("simple.py", complex_diff) is True

    def test_review_returns_structured_result(self, monkeypatch):
        """review() returns structured result."""
        from vibesrails.senior_mode.claude_reviewer import ClaudeReviewer, ReviewResult

        reviewer = ClaudeReviewer()
        monkeypatch.setattr(
            reviewer, "_call_claude",
            lambda x: '{"score": 8, "issues": [], "strengths": ["clean code"]}'
        )

        result = reviewer.review("def foo(): pass", "simple.py")

        assert isinstance(result, ReviewResult)
        assert result.score == 8

    def test_review_without_anthropic(self, monkeypatch):
        """review() handles missing anthropic gracefully."""
        from vibesrails.senior_mode import claude_reviewer
        monkeypatch.setattr(claude_reviewer, "HAS_ANTHROPIC", False)

        from vibesrails.senior_mode.claude_reviewer import ClaudeReviewer

        reviewer = ClaudeReviewer()
        result = reviewer.review("def foo(): pass", "test.py")

        assert result.reviewed is False
        assert "not installed" in result.skip_reason


class TestSeniorReport:
    """Tests for Senior Mode report."""

    def test_generate_report_includes_guards(self):
        """Report includes guard issues."""
        from vibesrails.senior_mode.report import SeniorReport
        from vibesrails.senior_mode.guards import GuardIssue

        issues = [
            GuardIssue(guard="TestGuard", severity="warn", message="Test warning"),
        ]

        report = SeniorReport(guard_issues=issues)
        output = report.generate()

        assert "Test warning" in output
        assert "SENIOR MODE" in output

    def test_generate_report_includes_review(self):
        """Report includes Claude review when present."""
        from vibesrails.senior_mode.report import SeniorReport
        from vibesrails.senior_mode.claude_reviewer import ReviewResult

        review = ReviewResult(score=8, issues=["minor issue"], strengths=["clean"])

        report = SeniorReport(review_result=review)
        output = report.generate()

        assert "8" in output
        assert "minor issue" in output

    def test_has_blocking_issues(self):
        """has_blocking_issues() returns True when blocking issues exist."""
        from vibesrails.senior_mode.report import SeniorReport
        from vibesrails.senior_mode.guards import GuardIssue

        blocking = [GuardIssue(guard="Test", severity="block", message="Critical")]
        warning = [GuardIssue(guard="Test", severity="warn", message="Minor")]

        assert SeniorReport(guard_issues=blocking).has_blocking_issues() is True
        assert SeniorReport(guard_issues=warning).has_blocking_issues() is False


class TestSeniorModeIntegration:
    """Integration tests for complete Senior Mode flow."""

    def test_full_flow(self, tmp_path):
        """Test complete Senior Mode flow."""
        from vibesrails.senior_mode import ArchitectureMapper, SeniorGuards
        from vibesrails.senior_mode.report import SeniorReport

        # Setup project
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "auth.py").write_text('''
def login(user, password):
    try:
        check(user)
    except:
        pass
''')

        # 1. Generate architecture
        mapper = ArchitectureMapper(tmp_path)
        arch = mapper.generate_map()
        assert "main.py" in arch

        # 2. Run guards
        guards = SeniorGuards()
        code = (tmp_path / "auth.py").read_text()
        issues = guards.check_all(
            code_diff="+def login(): pass",
            files=[("auth.py", code)]
        )

        # Should detect bare except
        assert any("except" in str(i.message).lower() for i in issues)

        # 3. Generate report
        report = SeniorReport(guard_issues=issues)
        output = report.generate()
        assert "SENIOR MODE" in output

    def test_all_components_importable(self):
        """All Senior Mode components can be imported."""
        from vibesrails.senior_mode import (
            ArchitectureMapper,
            SeniorGuards,
            ClaudeReviewer,
            ReviewResult,
            GuardIssue,
        )
        from vibesrails.senior_mode.report import SeniorReport

        # All classes exist
        assert ArchitectureMapper is not None
        assert SeniorGuards is not None
        assert ClaudeReviewer is not None
        assert SeniorReport is not None
