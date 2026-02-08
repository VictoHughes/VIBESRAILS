"""Tests for vibesrails autofix module."""

import os

import pytest

from vibesrails.autofix import (
    FIXES,
    Fix,
    apply_fix_to_file,
    apply_fix_to_line,
    get_fix_for_pattern,
    is_path_safe_for_fix,
    show_fixable_patterns,
)

# ============================================
# Fix Dataclass Tests
# ============================================

class TestFixDataclass:
    """Tests for the Fix dataclass."""

    def test_fix_creation(self):
        """Test creating a Fix with all fields."""
        fix = Fix(
            pattern_id="test_pattern",
            search=r"old_func\(",
            replace="new_func(",
            description="Replace old_func with new_func",
        )
        assert fix.pattern_id == "test_pattern"
        assert fix.search == r"old_func\("
        assert fix.replace == "new_func("
        assert fix.description == "Replace old_func with new_func"

    def test_fix_equality(self):
        """Test that two identical fixes are equal."""
        fix1 = Fix(
            pattern_id="test",
            search="a",
            replace="b",
            description="desc",
        )
        fix2 = Fix(
            pattern_id="test",
            search="a",
            replace="b",
            description="desc",
        )
        assert fix1 == fix2

    def test_fix_inequality(self):
        """Test that different fixes are not equal."""
        fix1 = Fix(
            pattern_id="test1",
            search="a",
            replace="b",
            description="desc",
        )
        fix2 = Fix(
            pattern_id="test2",
            search="a",
            replace="b",
            description="desc",
        )
        assert fix1 != fix2

    def test_fixes_list_not_empty(self):
        """Test that FIXES list contains predefined fixes."""
        assert len(FIXES) > 0
        for fix in FIXES:
            assert isinstance(fix, Fix)
            assert fix.pattern_id
            assert fix.search
            assert fix.replace
            assert fix.description


# ============================================
# get_fix_for_pattern Tests
# ============================================

class TestGetFixForPattern:
    """Tests for get_fix_for_pattern function."""

    def test_get_existing_fix_unsafe_yaml(self):
        """Test getting fix for unsafe_yaml pattern."""
        fix = get_fix_for_pattern("unsafe_yaml")
        assert fix is not None
        assert fix.pattern_id == "unsafe_yaml"
        assert "safe_load" in fix.replace

    def test_get_existing_fix_none_comparison(self):
        """Test getting fix for none_comparison pattern."""
        fix = get_fix_for_pattern("none_comparison")
        assert fix is not None
        assert fix.pattern_id == "none_comparison"
        assert "is None" in fix.replace

    def test_get_existing_fix_none_comparison_not(self):
        """Test getting fix for none_comparison_not pattern."""
        fix = get_fix_for_pattern("none_comparison_not")
        assert fix is not None
        assert "is not None" in fix.replace

    def test_get_existing_fix_bool_comparison_true(self):
        """Test getting fix for bool_comparison_true pattern."""
        fix = get_fix_for_pattern("bool_comparison_true")
        assert fix is not None
        assert fix.pattern_id == "bool_comparison_true"

    def test_get_existing_fix_bool_comparison_false(self):
        """Test getting fix for bool_comparison_false pattern."""
        fix = get_fix_for_pattern("bool_comparison_false")
        assert fix is not None
        assert "not" in fix.replace

    def test_get_existing_fix_type_comparison(self):
        """Test getting fix for type_comparison pattern."""
        fix = get_fix_for_pattern("type_comparison")
        assert fix is not None
        assert "isinstance" in fix.replace

    def test_get_existing_fix_dict_get_none(self):
        """Test getting fix for dict_get_none pattern."""
        fix = get_fix_for_pattern("dict_get_none")
        assert fix is not None
        assert fix.pattern_id == "dict_get_none"

    def test_get_nonexistent_fix(self):
        """Test that non-existent pattern returns None."""
        fix = get_fix_for_pattern("nonexistent_pattern")
        assert fix is None

    def test_get_fix_empty_string(self):
        """Test that empty string returns None."""
        fix = get_fix_for_pattern("")
        assert fix is None

    def test_all_fixes_retrievable(self):
        """Test that all predefined fixes can be retrieved."""
        for expected_fix in FIXES:
            retrieved_fix = get_fix_for_pattern(expected_fix.pattern_id)
            assert retrieved_fix is not None
            assert retrieved_fix == expected_fix


# ============================================
# apply_fix_to_line Tests
# ============================================

class TestApplyFixToLine:
    """Tests for apply_fix_to_line function."""

    def test_apply_none_comparison_fix(self):
        """Test applying None comparison fix."""
        fix = get_fix_for_pattern("none_comparison")
        line = "if x == None:"
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is True
        assert new_line == "if x is None:"

    def test_apply_none_comparison_not_fix(self):
        """Test applying != None comparison fix."""
        fix = get_fix_for_pattern("none_comparison_not")
        line = "if value != None:"
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is True
        assert new_line == "if value is not None:"

    def test_apply_unsafe_yaml_fix(self):
        """Test applying unsafe yaml fix."""
        fix = get_fix_for_pattern("unsafe_yaml")
        line = "data = yaml.load(content)"  # vibesrails: ignore [unsafe_yaml]
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is True
        assert new_line == "data = yaml.safe_load(content)"

    def test_apply_unsafe_yaml_fix_with_file_handle(self):
        """Test applying unsafe yaml fix with file handle."""
        fix = get_fix_for_pattern("unsafe_yaml")
        line = "config = yaml.load(f)"  # vibesrails: ignore [unsafe_yaml]
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is True
        assert new_line == "config = yaml.safe_load(f)"

    def test_apply_bool_comparison_true_fix(self):
        """Test applying == True comparison fix."""
        fix = get_fix_for_pattern("bool_comparison_true")
        line = "if is_valid == True:"
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is True
        assert new_line == "if is_valid:"

    def test_apply_bool_comparison_false_fix(self):
        """Test applying == False comparison fix."""
        fix = get_fix_for_pattern("bool_comparison_false")
        line = "if enabled == False:"
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is True
        assert new_line == "if not enabled:"

    def test_apply_type_comparison_fix(self):
        """Test applying type() == fix."""
        fix = get_fix_for_pattern("type_comparison")
        line = "if type(obj) == MyClass:"
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is True
        assert new_line == "if isinstance(obj, MyClass):"

    def test_apply_dict_get_none_fix(self):
        """Test applying dict.get() with None default fix."""
        fix = get_fix_for_pattern("dict_get_none")
        line = "value = data.get('key', None)"
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is True
        assert new_line == "value = data.get('key')"

    def test_no_change_when_pattern_not_found(self):
        """Test that non-matching line is unchanged."""
        fix = get_fix_for_pattern("unsafe_yaml")
        line = "data = json.load(f)"
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is False
        assert new_line == line

    def test_preserves_indentation(self):
        """Test that indentation is preserved."""
        fix = get_fix_for_pattern("none_comparison")
        line = "        if x == None:"
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is True
        assert new_line == "        if x is None:"

    def test_empty_line(self):
        """Test with empty line."""
        fix = get_fix_for_pattern("none_comparison")
        line = ""
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is False
        assert new_line == ""

    def test_multiple_occurrences_on_line(self):
        """Test that multiple occurrences on same line are fixed."""
        fix = get_fix_for_pattern("none_comparison")
        line = "if x == None and y == None:"
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is True
        assert new_line == "if x is None and y is None:"


# ============================================
# is_path_safe_for_fix Tests
# ============================================

class TestIsPathSafeForFix:
    """Tests for is_path_safe_for_fix function."""

    def test_safe_path_in_cwd(self, tmp_path):
        """Test that path within cwd is safe."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            assert is_path_safe_for_fix(str(test_file)) is True
        finally:
            os.chdir(original_cwd)

    def test_safe_nested_path(self, tmp_path):
        """Test that nested path within cwd is safe."""
        nested_dir = tmp_path / "subdir" / "nested"
        nested_dir.mkdir(parents=True)
        test_file = nested_dir / "test.py"
        test_file.write_text("content")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            assert is_path_safe_for_fix(str(test_file)) is True
        finally:
            os.chdir(original_cwd)

    def test_unsafe_path_outside_cwd(self, tmp_path):
        """Test that path outside cwd is unsafe."""
        # Create a file in tmp_path but change cwd to a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        outside_file = tmp_path / "outside.py"
        outside_file.write_text("content")

        original_cwd = os.getcwd()
        os.chdir(subdir)
        try:
            assert is_path_safe_for_fix(str(outside_file)) is False
        finally:
            os.chdir(original_cwd)

    def test_unsafe_path_traversal(self, tmp_path):
        """Test that path traversal attempt is blocked."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Attempt path traversal
            traversal_path = "../../../etc/passwd"
            assert is_path_safe_for_fix(traversal_path) is False
        finally:
            os.chdir(original_cwd)

    def test_relative_path_within_cwd(self, tmp_path):
        """Test that relative path within cwd is safe."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            assert is_path_safe_for_fix("test.py") is True
        finally:
            os.chdir(original_cwd)

    def test_absolute_path_within_cwd(self, tmp_path):
        """Test that absolute path within cwd is safe."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            assert is_path_safe_for_fix(str(test_file.resolve())) is True
        finally:
            os.chdir(original_cwd)


# ============================================
# apply_fix_to_file Tests
# ============================================

class TestApplyFixToFile:
    """Tests for apply_fix_to_file function."""

    def test_apply_fix_single_occurrence(self, tmp_path):
        """Test fixing single occurrence in file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("if x == None:\n    pass\n")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            fix = get_fix_for_pattern("none_comparison")
            changes = apply_fix_to_file(str(test_file), fix, dry_run=False, backup=False)

            assert len(changes) == 1
            assert changes[0][0] == 1  # Line number
            assert "== None" in changes[0][1]  # Old line
            assert "is None" in changes[0][2]  # New line

            # Verify file was modified
            content = test_file.read_text()
            assert "is None" in content
            assert "== None" not in content
        finally:
            os.chdir(original_cwd)

    def test_apply_fix_multiple_occurrences(self, tmp_path):
        """Test fixing multiple occurrences in file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("if x == None:\n    pass\nif y == None:\n    return\n")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            fix = get_fix_for_pattern("none_comparison")
            changes = apply_fix_to_file(str(test_file), fix, dry_run=False, backup=False)

            assert len(changes) == 2
            assert changes[0][0] == 1
            assert changes[1][0] == 3

            content = test_file.read_text()
            assert content.count("is None") == 2
            assert "== None" not in content
        finally:
            os.chdir(original_cwd)

    def test_apply_fix_dry_run(self, tmp_path):
        """Test dry run mode does not modify file."""
        test_file = tmp_path / "test.py"
        original_content = "if x == None:\n    pass\n"
        test_file.write_text(original_content)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            fix = get_fix_for_pattern("none_comparison")
            changes = apply_fix_to_file(str(test_file), fix, dry_run=True, backup=False)

            assert len(changes) == 1  # Changes are reported

            # Verify file was NOT modified
            content = test_file.read_text()
            assert content == original_content
        finally:
            os.chdir(original_cwd)

    def test_apply_fix_with_backup(self, tmp_path):
        """Test that backup file is created."""
        test_file = tmp_path / "test.py"
        original_content = "if x == None:\n    pass\n"
        test_file.write_text(original_content)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            fix = get_fix_for_pattern("none_comparison")
            apply_fix_to_file(str(test_file), fix, dry_run=False, backup=True)

            # Verify backup was created
            backup_file = tmp_path / "test.py.bak"
            assert backup_file.exists()
            assert backup_file.read_text() == original_content
        finally:
            os.chdir(original_cwd)

    def test_apply_fix_no_backup(self, tmp_path):
        """Test that backup is not created when disabled."""
        test_file = tmp_path / "test.py"
        test_file.write_text("if x == None:\n    pass\n")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            fix = get_fix_for_pattern("none_comparison")
            apply_fix_to_file(str(test_file), fix, dry_run=False, backup=False)

            # Verify backup was NOT created
            backup_file = tmp_path / "test.py.bak"
            assert not backup_file.exists()
        finally:
            os.chdir(original_cwd)

    def test_apply_fix_no_match(self, tmp_path):
        """Test applying fix when no matches found."""
        test_file = tmp_path / "test.py"
        original_content = "x = 1\ny = 2\n"
        test_file.write_text(original_content)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            fix = get_fix_for_pattern("none_comparison")
            changes = apply_fix_to_file(str(test_file), fix, dry_run=False, backup=False)

            assert len(changes) == 0

            # Verify file unchanged
            assert test_file.read_text() == original_content
        finally:
            os.chdir(original_cwd)

    def test_apply_fix_path_outside_cwd(self, tmp_path):
        """Test that fixing file outside cwd is blocked."""
        # Create file in tmp_path
        test_file = tmp_path / "test.py"
        test_file.write_text("if x == None:\n    pass\n")

        # Create subdirectory and change to it
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        original_cwd = os.getcwd()
        os.chdir(subdir)
        try:
            fix = get_fix_for_pattern("none_comparison")
            changes = apply_fix_to_file(str(test_file), fix, dry_run=False, backup=False)

            # Should return empty list (blocked)
            assert len(changes) == 0
        finally:
            os.chdir(original_cwd)

    def test_apply_fix_preserves_line_structure(self, tmp_path):
        """Test that file structure is preserved after fix."""
        test_file = tmp_path / "test.py"
        original_content = "# Comment\nif x == None:\n    pass\n# End"
        test_file.write_text(original_content)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            fix = get_fix_for_pattern("none_comparison")
            apply_fix_to_file(str(test_file), fix, dry_run=False, backup=False)

            content = test_file.read_text()
            lines = content.split("\n")
            assert len(lines) == 4  # Same number of lines
            assert lines[0] == "# Comment"
            assert "is None" in lines[1]
            assert lines[2] == "    pass"
            assert lines[3] == "# End"
        finally:
            os.chdir(original_cwd)

    def test_apply_fix_yaml_pattern(self, tmp_path):
        """Test applying yaml.safe_load fix."""
        test_file = tmp_path / "test.py"
        # vibesrails: ignore-next-line [unsafe_yaml]
        test_file.write_text("import yaml\ndata = yaml.load(content)\n")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            fix = get_fix_for_pattern("unsafe_yaml")
            changes = apply_fix_to_file(str(test_file), fix, dry_run=False, backup=False)

            assert len(changes) == 1
            content = test_file.read_text()
            assert "yaml.safe_load(content)" in content
        finally:
            os.chdir(original_cwd)

    def test_apply_fix_empty_file(self, tmp_path):
        """Test applying fix to empty file."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            fix = get_fix_for_pattern("none_comparison")
            changes = apply_fix_to_file(str(test_file), fix, dry_run=False, backup=False)

            assert len(changes) == 0
            assert test_file.read_text() == ""
        finally:
            os.chdir(original_cwd)


# ============================================
# show_fixable_patterns Tests
# ============================================

class TestShowFixablePatterns:
    """Tests for show_fixable_patterns function."""

    def test_show_fixable_patterns_output(self, capsys):
        """Test that show_fixable_patterns prints pattern info."""
        show_fixable_patterns()

        captured = capsys.readouterr()
        output = captured.out

        # Should contain header
        assert "Auto-fixable Patterns" in output

        # Should list all pattern IDs
        for fix in FIXES:
            assert fix.pattern_id in output
            assert fix.description in output

    def test_show_fixable_patterns_lists_all_fixes(self, capsys):
        """Test that all fixes are listed."""
        show_fixable_patterns()

        captured = capsys.readouterr()
        output = captured.out

        # Count pattern IDs in output
        for fix in FIXES:
            assert f"[{fix.pattern_id}]" in output


# ============================================
# Integration Tests
# ============================================

class TestAutofixIntegration:
    """Integration tests combining multiple autofix functions."""

    def test_full_fix_workflow(self, tmp_path):
        """Test complete workflow: detect, get fix, apply."""
        # Create file with multiple fixable issues
        test_file = tmp_path / "multi.py"
        # vibesrails: ignore-next-line [unsafe_yaml]
        test_file.write_text("import yaml\n\ndef process(data, flag):\n    if data == None:\n        return\n    if flag == True:\n        config = yaml.load(data)\n        return config\n")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Apply multiple fixes
            patterns = ["none_comparison", "bool_comparison_true", "unsafe_yaml"]
            for pattern_id in patterns:
                fix = get_fix_for_pattern(pattern_id)
                if fix:
                    apply_fix_to_file(str(test_file), fix, dry_run=False, backup=False)

            content = test_file.read_text()
            assert "is None" in content
            assert "== None" not in content
            # bool_comparison_true turns "flag == True" into just "flag"
            assert "== True" not in content
            assert "yaml.safe_load(data)" in content
        finally:
            os.chdir(original_cwd)

    def test_fix_chaining_dry_run_then_apply(self, tmp_path):
        """Test dry run followed by actual apply."""
        test_file = tmp_path / "test.py"
        original_content = "if x == None:\n    pass\n"
        test_file.write_text(original_content)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            fix = get_fix_for_pattern("none_comparison")

            # First dry run
            changes_dry = apply_fix_to_file(str(test_file), fix, dry_run=True, backup=False)
            assert len(changes_dry) == 1
            assert test_file.read_text() == original_content  # Unchanged

            # Then actual apply
            changes_real = apply_fix_to_file(str(test_file), fix, dry_run=False, backup=False)
            assert len(changes_real) == 1
            assert "is None" in test_file.read_text()  # Changed
        finally:
            os.chdir(original_cwd)

    def test_all_builtin_fixes_are_valid_regex(self):
        """Test that all built-in fix patterns are valid regex."""
        import re

        for fix in FIXES:
            # Should not raise
            compiled = re.compile(fix.search)
            assert compiled is not None


# ============================================
# run_autofix Tests
# ============================================

class TestRunAutofix:
    """Tests for run_autofix function."""

    @pytest.fixture
    def sample_config(self):
        """Minimal config for autofix testing."""
        return {
            "version": "1.0",
            "blocking": [
                {
                    "id": "unsafe_yaml",
                    "name": "Unsafe YAML",
                    "regex": r"yaml\.load\([^)]+\)",
                    "message": "Use yaml.safe_load instead",
                }
            ],
            "warning": [
                {
                    "id": "none_comparison",
                    "name": "None Comparison",
                    "regex": r"\w+\s*==\s*None",
                    "message": "Use 'is None' instead",
                }
            ],
            "exceptions": {},
        }

    def test_run_autofix_dry_run(self, tmp_path, sample_config, capsys):
        """Test run_autofix in dry run mode."""
        from vibesrails.autofix import run_autofix

        test_file = tmp_path / "test.py"
        original_content = "if x == None:\n    pass\n"
        test_file.write_text(original_content)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            files_modified = run_autofix(
                sample_config,
                [str(test_file)],
                dry_run=True,
                backup=False
            )

            # Dry run should report 0 files modified
            assert files_modified == 0

            # File should be unchanged
            assert test_file.read_text() == original_content

            # Output should indicate dry run
            captured = capsys.readouterr()
            assert "dry run" in captured.out
            assert "WOULD FIX" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_run_autofix_applies_fixes(self, tmp_path, sample_config, capsys):
        """Test run_autofix actually applies fixes."""
        from vibesrails.autofix import run_autofix

        test_file = tmp_path / "test.py"
        test_file.write_text("if x == None:\n    pass\n")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            files_modified = run_autofix(
                sample_config,
                [str(test_file)],
                dry_run=False,
                backup=False
            )

            assert files_modified == 1

            # File should be changed
            content = test_file.read_text()
            assert "is None" in content

            # Output should indicate fix
            captured = capsys.readouterr()
            assert "FIXED" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_run_autofix_no_fixable_issues(self, tmp_path, sample_config, capsys):
        """Test run_autofix with clean file."""
        from vibesrails.autofix import run_autofix

        test_file = tmp_path / "clean.py"
        test_file.write_text("x = 1\ny = 2\n")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            files_modified = run_autofix(
                sample_config,
                [str(test_file)],
                dry_run=False,
                backup=False
            )

            assert files_modified == 0

            captured = capsys.readouterr()
            assert "Fixed 0 issue(s)" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_run_autofix_multiple_files(self, tmp_path, sample_config, capsys):
        """Test run_autofix with multiple files."""
        from vibesrails.autofix import run_autofix

        file1 = tmp_path / "test1.py"
        file1.write_text("if x == None:\n    pass\n")

        file2 = tmp_path / "test2.py"
        file2.write_text("if y == None:\n    return\n")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            files_modified = run_autofix(
                sample_config,
                [str(file1), str(file2)],
                dry_run=False,
                backup=False
            )

            assert files_modified == 2

            assert "is None" in file1.read_text()
            assert "is None" in file2.read_text()
        finally:
            os.chdir(original_cwd)

    def test_run_autofix_with_backup(self, tmp_path, sample_config):
        """Test run_autofix creates backups."""
        from vibesrails.autofix import run_autofix

        test_file = tmp_path / "test.py"
        original_content = "if x == None:\n    pass\n"
        test_file.write_text(original_content)

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            run_autofix(
                sample_config,
                [str(test_file)],
                dry_run=False,
                backup=True
            )

            # Backup should exist
            backup_file = tmp_path / "test.py.bak"
            assert backup_file.exists()
            assert backup_file.read_text() == original_content
        finally:
            os.chdir(original_cwd)

    def test_run_autofix_no_backup_flag(self, tmp_path, sample_config, capsys):
        """Test run_autofix output mentions no backup."""
        from vibesrails.autofix import run_autofix

        test_file = tmp_path / "test.py"
        test_file.write_text("if x == None:\n    pass\n")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            run_autofix(
                sample_config,
                [str(test_file)],
                dry_run=False,
                backup=False
            )

            captured = capsys.readouterr()
            assert "no backup" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_run_autofix_pattern_without_fix(self, tmp_path, capsys):
        """Test run_autofix skips patterns without fixes."""
        from vibesrails.autofix import run_autofix

        # Config with pattern that has no fix
        config = {
            "version": "1.0",
            "blocking": [
                {
                    "id": "custom_pattern_no_fix",
                    "name": "Custom Pattern",
                    "regex": r"bad_code\(",
                    "message": "Don't use bad_code",
                }
            ],
            "warning": [],
            "exceptions": {},
        }

        test_file = tmp_path / "test.py"
        test_file.write_text("bad_code()\n")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            files_modified = run_autofix(
                config,
                [str(test_file)],
                dry_run=False,
                backup=False
            )

            # No fix available, so no files modified
            assert files_modified == 0
        finally:
            os.chdir(original_cwd)
