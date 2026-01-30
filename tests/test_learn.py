"""Tests for vibesrails learn mode."""

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

import vibesrails.learn as learn_module


# ============================================
# HAS_ANTHROPIC Flag Tests
# ============================================

def test_has_anthropic_flag_exists():
    """Test HAS_ANTHROPIC flag is defined."""
    import vibesrails.learn as learn_module

    assert hasattr(learn_module, "HAS_ANTHROPIC")


def test_has_anthropic_import_fallback():
    """Test fallback when anthropic is not installed."""
    # The module should handle import errors gracefully
    # We can test that analyze_with_claude returns None when HAS_ANTHROPIC is False
    import vibesrails.learn as learn_module

    # Save original value
    original_has_anthropic = learn_module.HAS_ANTHROPIC

    try:
        # Simulate anthropic not installed
        learn_module.HAS_ANTHROPIC = False

        result = learn_module.analyze_with_claude("test code")
        assert result is None
    finally:
        # Restore
        learn_module.HAS_ANTHROPIC = original_has_anthropic


# ============================================
# sample_codebase Tests
# ============================================

class TestSampleCodebase:
    """Tests for sample_codebase function."""

    def test_sample_codebase_no_files(self, tmp_path, monkeypatch):
        """Test sample_codebase with no Python files."""
        from vibesrails.learn import sample_codebase

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Mock get_all_python_files to return empty list
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files",
                lambda: []
            )

            result = sample_codebase()
            assert result == ""
        finally:
            os.chdir(original_cwd)

    def test_sample_codebase_with_files(self, tmp_path, monkeypatch):
        """Test sample_codebase with Python files."""
        from vibesrails.learn import sample_codebase

        # Create test files
        file1 = tmp_path / "app.py"
        file1.write_text("def main():\n    print('hello')")

        file2 = tmp_path / "utils.py"
        file2.write_text("def helper():\n    pass")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files",
                lambda: [str(file1), str(file2)]
            )

            result = sample_codebase()

            # Should contain file contents
            assert "def main():" in result
            assert "def helper():" in result
            # Should have file markers
            assert "# File:" in result
        finally:
            os.chdir(original_cwd)

    def test_sample_codebase_more_files_than_max(self, tmp_path, monkeypatch):
        """Test sample_codebase with more files than max_files."""
        from vibesrails.learn import sample_codebase

        # Create many test files
        files = []
        for i in range(30):
            f = tmp_path / f"module_{i}.py"
            f.write_text(f"# Module {i}")
            files.append(str(f))

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files",
                lambda: files
            )

            # With max_files=10, should only include 10 files
            result = sample_codebase(max_files=10)

            # Count file markers
            file_count = result.count("# File:")
            assert file_count == 10
        finally:
            os.chdir(original_cwd)

    def test_sample_codebase_random_sample(self, tmp_path, monkeypatch):
        """Test sample_codebase samples when files exceed max."""
        from vibesrails.learn import sample_codebase

        # Create 25 test files
        files = []
        for i in range(25):
            f = tmp_path / f"file_{i}.py"
            f.write_text(f"content_{i}")
            files.append(str(f))

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files",
                lambda: files
            )

            # Verify we get max_files samples, not all 25
            result = sample_codebase(max_files=5)
            # Should have at most 5 file sections (separated by ---)
            file_count = result.count("# File:")
            assert file_count <= 5
        finally:
            os.chdir(original_cwd)

    def test_sample_codebase_oserror_handling(self, tmp_path, monkeypatch):
        """Test sample_codebase handles OSError gracefully."""
        from vibesrails.learn import sample_codebase

        # Create a file that will exist in the list but cause an error
        good_file = tmp_path / "good.py"
        good_file.write_text("# Good file")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Include a non-existent file to trigger OSError
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files",
                lambda: [str(good_file), "/nonexistent/file.py"]
            )

            result = sample_codebase()

            # Should include good file content
            assert "# Good file" in result
            # Should not crash
        finally:
            os.chdir(original_cwd)

    def test_sample_codebase_unicode_error_handling(self, tmp_path, monkeypatch):
        """Test sample_codebase handles UnicodeDecodeError gracefully."""
        from vibesrails.learn import sample_codebase

        # Create a good file
        good_file = tmp_path / "good.py"
        good_file.write_text("# Good file")

        # Create a binary file that will cause UnicodeDecodeError
        binary_file = tmp_path / "binary.py"
        binary_file.write_bytes(b'\x80\x81\x82\x83\xff\xfe')

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files",
                lambda: [str(good_file), str(binary_file)]
            )

            result = sample_codebase()

            # Should include good file content
            assert "# Good file" in result
            # Should not crash due to binary file
        finally:
            os.chdir(original_cwd)

    def test_sample_codebase_max_lines_truncation(self, tmp_path, monkeypatch):
        """Test sample_codebase truncates files to max_lines_per_file."""
        from vibesrails.learn import sample_codebase

        # Create file with many lines
        long_file = tmp_path / "long.py"
        lines = [f"# Line {i}" for i in range(200)]
        long_file.write_text("\n".join(lines))

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files",
                lambda: [str(long_file)]
            )

            result = sample_codebase(max_lines_per_file=50)

            # Should contain first 50 lines but not line 100
            assert "# Line 0" in result
            assert "# Line 49" in result
            assert "# Line 100" not in result
        finally:
            os.chdir(original_cwd)

    def test_sample_codebase_separator(self, tmp_path, monkeypatch):
        """Test sample_codebase uses correct separator between files."""
        from vibesrails.learn import sample_codebase

        file1 = tmp_path / "a.py"
        file1.write_text("# A")

        file2 = tmp_path / "b.py"
        file2.write_text("# B")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files",
                lambda: [str(file1), str(file2)]
            )

            result = sample_codebase()

            # Should have separator between files
            assert "\n\n---\n\n" in result
        finally:
            os.chdir(original_cwd)


# ============================================
# analyze_with_claude Tests
# ============================================

class TestAnalyzeWithClaude:
    """Tests for analyze_with_claude function."""

    def test_analyze_with_claude_no_anthropic(self, monkeypatch):
        """Test analyze_with_claude returns None when anthropic not installed."""
        import vibesrails.learn as learn_module

        monkeypatch.setattr(learn_module, "HAS_ANTHROPIC", False)

        result = learn_module.analyze_with_claude("test code")
        assert result is None

    def test_analyze_with_claude_with_mocked_client(self, monkeypatch):
        """Test analyze_with_claude with mocked anthropic client."""
        import vibesrails.learn as learn_module

        monkeypatch.setattr(learn_module, "HAS_ANTHROPIC", True)

        # Create mock message response
        mock_message = mock.Mock()
        mock_message.content = [mock.Mock(text="```yaml\nsuggested: []\n```")]

        # Create mock client
        mock_client = mock.Mock()
        mock_client.messages.create.return_value = mock_message

        # Mock the anthropic module
        mock_anthropic = mock.Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        monkeypatch.setattr(learn_module, "anthropic", mock_anthropic)

        result = learn_module.analyze_with_claude("def foo(): pass")

        assert result == "```yaml\nsuggested: []\n```"

# ============================================
# run_learn_mode Tests
# ============================================

class TestRunLearnMode:
    """Tests for run_learn_mode function."""

    def test_run_learn_mode_no_anthropic(self, capsys, monkeypatch):
        """Test run_learn_mode returns False when anthropic not installed."""
        import vibesrails.learn as learn_module

        monkeypatch.setattr(learn_module, "HAS_ANTHROPIC", False)

        result = learn_module.run_learn_mode()

        assert result is False
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "anthropic" in captured.out

    def test_run_learn_mode_no_python_files(self, tmp_path, capsys, monkeypatch):
        """Test run_learn_mode returns False when no Python files found."""
        import vibesrails.learn as learn_module

        monkeypatch.setattr(learn_module, "HAS_ANTHROPIC", True)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Mock sample_codebase to return empty string
            monkeypatch.setattr(learn_module, "sample_codebase", lambda: "")

            result = learn_module.run_learn_mode()

            assert result is False
            captured = capsys.readouterr()
            assert "No Python files found" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_run_learn_mode_claude_api_error(self, tmp_path, capsys, monkeypatch):
        """Test run_learn_mode returns False on Claude API error."""
        import vibesrails.learn as learn_module

        monkeypatch.setattr(learn_module, "HAS_ANTHROPIC", True)
        monkeypatch.setattr(learn_module, "sample_codebase", lambda: "def foo(): pass")

        # Mock analyze_with_claude to raise exception
        def raise_api_error(code):
            raise Exception("API rate limit exceeded")

        monkeypatch.setattr(learn_module, "analyze_with_claude", raise_api_error)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = learn_module.run_learn_mode()

            assert result is False
            captured = capsys.readouterr()
            assert "Claude API error" in captured.out
            assert "ANTHROPIC_API_KEY" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_run_learn_mode_no_result_from_claude(self, tmp_path, capsys, monkeypatch):
        """Test run_learn_mode returns False when Claude returns None."""
        import vibesrails.learn as learn_module

        monkeypatch.setattr(learn_module, "HAS_ANTHROPIC", True)
        monkeypatch.setattr(learn_module, "sample_codebase", lambda: "def foo(): pass")
        monkeypatch.setattr(learn_module, "analyze_with_claude", lambda x: None)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = learn_module.run_learn_mode()

            assert result is False
            captured = capsys.readouterr()
            assert "No response from Claude" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_run_learn_mode_successful_analysis(self, tmp_path, capsys, monkeypatch):
        """Test run_learn_mode returns True on successful analysis."""
        import vibesrails.learn as learn_module

        monkeypatch.setattr(learn_module, "HAS_ANTHROPIC", True)
        monkeypatch.setattr(learn_module, "sample_codebase", lambda: "def foo(): pass")

        yaml_response = """```yaml
# Suggested patterns from learn mode
suggested:
  - id: test_pattern
    name: "Test Pattern"
    regex: "test"
    message: "Test message"
    level: "WARN"
```"""
        monkeypatch.setattr(learn_module, "analyze_with_claude", lambda x: yaml_response)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = learn_module.run_learn_mode()

            assert result is True
            captured = capsys.readouterr()
            assert "Suggested Patterns" in captured.out
            assert yaml_response in captured.out
            assert "Review suggestions" in captured.out
            assert "Human validation required" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_run_learn_mode_prints_header(self, tmp_path, capsys, monkeypatch):
        """Test run_learn_mode prints correct header."""
        import vibesrails.learn as learn_module

        monkeypatch.setattr(learn_module, "HAS_ANTHROPIC", True)
        monkeypatch.setattr(learn_module, "sample_codebase", lambda: "code")
        monkeypatch.setattr(learn_module, "analyze_with_claude", lambda x: "result")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            learn_module.run_learn_mode()

            captured = capsys.readouterr()
            assert "vibesrails --learn" in captured.out
            assert "Claude-powered pattern discovery" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_run_learn_mode_prints_progress(self, tmp_path, capsys, monkeypatch):
        """Test run_learn_mode prints progress messages."""
        import vibesrails.learn as learn_module

        monkeypatch.setattr(learn_module, "HAS_ANTHROPIC", True)
        monkeypatch.setattr(learn_module, "sample_codebase", lambda: "code")
        monkeypatch.setattr(learn_module, "analyze_with_claude", lambda x: "result")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            learn_module.run_learn_mode()

            captured = capsys.readouterr()
            assert "Sampling codebase" in captured.out
            assert "Analyzing with Claude" in captured.out
            assert "Collected samples from codebase" in captured.out
        finally:
            os.chdir(original_cwd)


# ============================================
# LEARN_PROMPT Tests
# ============================================

def test_learn_prompt_exists():
    """Test LEARN_PROMPT is defined."""
    from vibesrails.learn import LEARN_PROMPT

    assert LEARN_PROMPT is not None
    assert len(LEARN_PROMPT) > 0


def test_learn_prompt_contains_key_instructions():
    """Test LEARN_PROMPT contains essential instructions."""
    from vibesrails.learn import LEARN_PROMPT

    # Should instruct about security analysis
    assert "security" in LEARN_PROMPT.lower()
    assert "code quality" in LEARN_PROMPT.lower()

    # Should mention YAML format
    assert "yaml" in LEARN_PROMPT.lower()
    assert "vibesrails.yaml" in LEARN_PROMPT

    # Should describe pattern structure
    assert "id" in LEARN_PROMPT
    assert "regex" in LEARN_PROMPT
    assert "message" in LEARN_PROMPT
    assert "level" in LEARN_PROMPT


def test_learn_prompt_warns_about_common_patterns():
    """Test LEARN_PROMPT warns not to suggest common patterns."""
    from vibesrails.learn import LEARN_PROMPT

    assert "Don't suggest patterns that are already common" in LEARN_PROMPT


# ============================================
# Integration Tests
# ============================================

class TestLearnIntegration:
    """Integration tests for learn module."""

    def test_sample_codebase_integration(self, tmp_path, monkeypatch):
        """Test sample_codebase with real file operations."""
        from vibesrails.learn import sample_codebase

        # Create a project structure
        src = tmp_path / "src"
        src.mkdir()

        (src / "main.py").write_text("""
def main():
    '''Entry point.'''
    print('Starting app')

if __name__ == '__main__':
    main()
""")

        (src / "utils.py").write_text("""
def helper():
    '''Helper function.'''
    return 42
""")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files",
                lambda: [str(src / "main.py"), str(src / "utils.py")]
            )

            result = sample_codebase()

            assert "def main():" in result
            assert "def helper():" in result
            assert "# File:" in result
        finally:
            os.chdir(original_cwd)

    def test_full_workflow_mocked(self, tmp_path, capsys, monkeypatch):
        """Test full learn workflow with mocked Claude."""
        import vibesrails.learn as learn_module

        # Create test files
        (tmp_path / "app.py").write_text("dangerous_function(user_input)  # Risky!")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            monkeypatch.setattr(learn_module, "HAS_ANTHROPIC", True)
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files",
                lambda: [str(tmp_path / "app.py")]
            )

            # Mock Claude response
            claude_response = """```yaml
suggested:
  - id: dangerous_user_input
    name: "Dangerous with user input"
    regex: "dangerous_function\\\\(.*user.*\\\\)"
    message: "Never pass user input to dangerous_function"
    level: "BLOCK"
```"""
            monkeypatch.setattr(learn_module, "analyze_with_claude", lambda x: claude_response)

            result = learn_module.run_learn_mode()

            assert result is True
            captured = capsys.readouterr()
            assert "dangerous_user_input" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_empty_response_handling(self, tmp_path, capsys, monkeypatch):
        """Test handling of empty string response from Claude."""
        import vibesrails.learn as learn_module

        monkeypatch.setattr(learn_module, "HAS_ANTHROPIC", True)
        monkeypatch.setattr(learn_module, "sample_codebase", lambda: "code")
        # Empty string should be falsy
        monkeypatch.setattr(learn_module, "analyze_with_claude", lambda x: "")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = learn_module.run_learn_mode()

            assert result is False
            captured = capsys.readouterr()
            assert "No response from Claude" in captured.out
        finally:
            os.chdir(original_cwd)


# ============================================
# Non-mock tests (real behavior)
# ============================================


class TestLearnModuleAttributes:
    """Test module-level attributes without mocking."""

    def test_learn_prompt_is_string(self):
        """LEARN_PROMPT is a non-empty string."""
        assert isinstance(learn_module.LEARN_PROMPT, str)
        assert len(learn_module.LEARN_PROMPT) > 100

    def test_learn_prompt_mentions_yaml(self):
        """LEARN_PROMPT references YAML output format."""
        assert "yaml" in learn_module.LEARN_PROMPT.lower()

    def test_learn_prompt_mentions_regex(self):
        """LEARN_PROMPT asks for regex patterns."""
        assert "regex" in learn_module.LEARN_PROMPT.lower()

    def test_learn_prompt_mentions_level(self):
        """LEARN_PROMPT mentions severity levels."""
        prompt = learn_module.LEARN_PROMPT
        assert "BLOCK" in prompt or "WARN" in prompt

    def test_has_anthropic_is_bool(self):
        """HAS_ANTHROPIC is a boolean."""
        assert isinstance(learn_module.HAS_ANTHROPIC, bool)

    def test_sample_codebase_callable(self):
        """sample_codebase is callable."""
        assert callable(learn_module.sample_codebase)

    def test_analyze_with_claude_callable(self):
        """analyze_with_claude is callable."""
        assert callable(learn_module.analyze_with_claude)

    def test_run_learn_mode_callable(self):
        """run_learn_mode is callable."""
        assert callable(learn_module.run_learn_mode)


class TestSampleCodebaseReal:
    """Real file-based tests for sample_codebase."""

    def test_sample_empty_dir(self, tmp_path, monkeypatch):
        """sample_codebase returns '' when no files found."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files", lambda: []
            )
            assert learn_module.sample_codebase() == ""
        finally:
            os.chdir(original_cwd)

    def test_sample_single_file_content(self, tmp_path, monkeypatch):
        """sample_codebase includes file content."""
        f = tmp_path / "hello.py"
        f.write_text("print('hello')")
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files",
                lambda: [str(f)],
            )
            result = learn_module.sample_codebase()
            assert "print('hello')" in result
        finally:
            os.chdir(original_cwd)

    def test_sample_respects_max_files(self, tmp_path, monkeypatch):
        """sample_codebase limits file count."""
        files = []
        for i in range(10):
            p = tmp_path / f"f{i}.py"
            p.write_text(f"x = {i}")
            files.append(str(p))
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files", lambda: files
            )
            result = learn_module.sample_codebase(max_files=3)
            assert result.count("# File:") == 3
        finally:
            os.chdir(original_cwd)

    def test_sample_respects_max_lines(self, tmp_path, monkeypatch):
        """sample_codebase truncates long files."""
        f = tmp_path / "long.py"
        f.write_text("\n".join(f"line{i}" for i in range(200)))
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            monkeypatch.setattr(
                "vibesrails.learn.get_all_python_files", lambda: [str(f)]
            )
            result = learn_module.sample_codebase(max_lines_per_file=10)
            assert "line9" in result
            assert "line50" not in result
        finally:
            os.chdir(original_cwd)


class TestLearnPromptContent:
    """Pure non-mock tests for LEARN_PROMPT content."""

    def test_prompt_has_yaml_format_example(self):
        """LEARN_PROMPT includes YAML example block."""
        assert "```yaml" in learn_module.LEARN_PROMPT

    def test_prompt_mentions_id_field(self):
        """LEARN_PROMPT describes the id field."""
        assert "id:" in learn_module.LEARN_PROMPT

    def test_prompt_mentions_message_field(self):
        """LEARN_PROMPT describes the message field."""
        assert "message:" in learn_module.LEARN_PROMPT

    def test_prompt_mentions_level_field(self):
        """LEARN_PROMPT describes the level field."""
        assert "level:" in learn_module.LEARN_PROMPT

    def test_prompt_mentions_suggested_section(self):
        """LEARN_PROMPT references suggested section."""
        assert "suggested:" in learn_module.LEARN_PROMPT

    def test_prompt_warns_about_common(self):
        """LEARN_PROMPT warns not to suggest common patterns."""
        assert "common" in learn_module.LEARN_PROMPT.lower()

    def test_prompt_mentions_code_samples(self):
        """LEARN_PROMPT mentions code samples to analyze."""
        assert "CODE SAMPLES" in learn_module.LEARN_PROMPT

    def test_prompt_mentions_empty_response(self):
        """LEARN_PROMPT describes empty response format."""
        assert "suggested: []" in learn_module.LEARN_PROMPT

    def test_analyze_returns_none_without_anthropic(self):
        """analyze_with_claude returns None when HAS_ANTHROPIC is False."""
        original = learn_module.HAS_ANTHROPIC
        try:
            learn_module.HAS_ANTHROPIC = False
            assert learn_module.analyze_with_claude("code") is None
        finally:
            learn_module.HAS_ANTHROPIC = original

    def test_module_has_rate_limiting_import(self):
        """Learn module imports rate_limiting."""
        assert hasattr(learn_module, "with_rate_limiting")
