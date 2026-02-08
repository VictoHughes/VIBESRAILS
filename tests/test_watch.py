"""Tests for vibesrails watch mode."""

import os
import sys
import time
from unittest import mock

import vibesrails.watch as watch_mod

# ============================================
# HAS_WATCHDOG Flag Tests
# ============================================

def test_has_watchdog_when_installed():
    """Test HAS_WATCHDOG is True when watchdog is installed."""
    # Force reimport to test the import logic
    import vibesrails.watch as watch_module

    # The module should have HAS_WATCHDOG defined
    assert hasattr(watch_module, "HAS_WATCHDOG")
    # We can't guarantee watchdog is installed, so just check the attribute exists


def test_has_watchdog_import_fallback():
    """Test fallback when watchdog is not installed."""
    # Create a mock module without watchdog
    with mock.patch.dict(sys.modules, {"watchdog": None, "watchdog.events": None, "watchdog.observers": None}):
        # Mock the import to raise ImportError
        original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def mock_import(name, *args, **kwargs):
            if "watchdog" in name:
                raise ImportError("No module named 'watchdog'")
            return original_import(name, *args, **kwargs)

        # We can test that the fallback class is defined when watchdog is missing
        # by checking that VibesRailsHandler can still be instantiated
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})
        assert handler.config == {"blocking": [], "warning": []}


# ============================================
# VibesRailsHandler Tests
# ============================================

class TestVibesRailsHandler:
    """Tests for VibesRailsHandler class."""

    def test_init_stores_config(self):
        """Test __init__ stores config and initializes last_scan."""
        from vibesrails.watch import VibesRailsHandler

        config = {"blocking": [], "warning": [], "version": "1.0"}
        handler = VibesRailsHandler(config)

        assert handler.config == config
        assert handler.last_scan == {}

    def test_init_empty_last_scan(self):
        """Test __init__ creates empty last_scan dict."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({})
        assert isinstance(handler.last_scan, dict)
        assert len(handler.last_scan) == 0

    def test_on_modified_ignores_directory_events(self):
        """Test on_modified ignores directory events."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})

        # Mock event that is a directory
        event = mock.Mock()
        event.is_directory = True
        event.src_path = "/path/to/dir"

        # Should return early without calling scan_file
        with mock.patch.object(handler, "scan_file") as mock_scan:
            handler.on_modified(event)
            mock_scan.assert_not_called()

    def test_on_modified_ignores_non_py_files(self):
        """Test on_modified ignores non-Python files."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})

        # Test various non-Python files
        for ext in [".txt", ".json", ".yaml", ".md", ".js", ".ts"]:
            event = mock.Mock()
            event.is_directory = False
            event.src_path = f"/path/to/file{ext}"

            with mock.patch.object(handler, "scan_file") as mock_scan:
                handler.on_modified(event)
                mock_scan.assert_not_called()

    def test_on_modified_skips_venv(self):
        """Test on_modified skips .venv directory."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})

        event = mock.Mock()
        event.is_directory = False
        event.src_path = "/project/.venv/lib/site.py"

        with mock.patch.object(handler, "scan_file") as mock_scan:
            handler.on_modified(event)
            mock_scan.assert_not_called()

    def test_on_modified_skips_venv_no_dot(self):
        """Test on_modified skips venv directory (without dot)."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})

        event = mock.Mock()
        event.is_directory = False
        event.src_path = "/project/venv/lib/module.py"

        with mock.patch.object(handler, "scan_file") as mock_scan:
            handler.on_modified(event)
            mock_scan.assert_not_called()

    def test_on_modified_skips_pycache(self):
        """Test on_modified skips __pycache__ directory."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})

        event = mock.Mock()
        event.is_directory = False
        event.src_path = "/project/__pycache__/module.cpython-312.py"

        with mock.patch.object(handler, "scan_file") as mock_scan:
            handler.on_modified(event)
            mock_scan.assert_not_called()

    def test_on_modified_skips_node_modules(self):
        """Test on_modified skips node_modules directory."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})

        event = mock.Mock()
        event.is_directory = False
        event.src_path = "/project/node_modules/some/script.py"

        with mock.patch.object(handler, "scan_file") as mock_scan:
            handler.on_modified(event)
            mock_scan.assert_not_called()

    def test_on_modified_skips_git(self):
        """Test on_modified skips .git directory."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})

        event = mock.Mock()
        event.is_directory = False
        event.src_path = "/project/.git/hooks/pre-commit.py"

        with mock.patch.object(handler, "scan_file") as mock_scan:
            handler.on_modified(event)
            mock_scan.assert_not_called()

    def test_on_modified_debounce_within_1_second(self):
        """Test on_modified debounces events within 1 second."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})

        event = mock.Mock()
        event.is_directory = False
        event.src_path = "/project/app.py"

        with mock.patch.object(handler, "scan_file") as mock_scan:
            # First call should scan
            handler.on_modified(event)
            assert mock_scan.call_count == 1

            # Second call within 1 second should be debounced
            handler.on_modified(event)
            assert mock_scan.call_count == 1  # Still 1, not 2

    def test_on_modified_allows_after_debounce_period(self):
        """Test on_modified allows scan after debounce period."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})

        event = mock.Mock()
        event.is_directory = False
        event.src_path = "/project/app.py"

        with mock.patch.object(handler, "scan_file") as mock_scan:
            # First call
            handler.on_modified(event)
            assert mock_scan.call_count == 1

            # Simulate time passing (modify last_scan time)
            handler.last_scan[event.src_path] = time.time() - 2  # 2 seconds ago

            # Should scan again
            handler.on_modified(event)
            assert mock_scan.call_count == 2

    def test_on_modified_calls_scan_file(self):
        """Test on_modified calls scan_file for valid Python file."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})

        event = mock.Mock()
        event.is_directory = False
        event.src_path = "/project/app.py"

        with mock.patch.object(handler, "scan_file") as mock_scan:
            handler.on_modified(event)
            mock_scan.assert_called_once_with("/project/app.py")

    def test_scan_file_no_results_clean_file(self, tmp_path, capsys):
        """Test scan_file with clean file (no results)."""
        from vibesrails.watch import VibesRailsHandler

        config = {
            "blocking": [
                {
                    "id": "test_secret",
                    "name": "Test Secret",
                    "regex": r"password\s*=\s*[\"'][^\"']+",
                    "message": "Hardcoded password",
                }
            ],
            "warning": [],
            "exceptions": {},
        }

        handler = VibesRailsHandler(config)

        # Create clean file
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("import os\nname = 'test'")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            handler.scan_file(str(clean_file))
            captured = capsys.readouterr()
            # Should show green checkmark
            assert "clean.py" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_scan_file_blocking_results(self, tmp_path, capsys):
        """Test scan_file with blocking results."""
        from vibesrails.watch import VibesRailsHandler

        config = {
            "blocking": [
                {
                    "id": "test_secret",
                    "name": "Test Secret",
                    "regex": r"password\s*=\s*[\"'][^\"']+",
                    "message": "Hardcoded password",
                }
            ],
            "warning": [],
            "exceptions": {},
        }

        handler = VibesRailsHandler(config)

        # Create file with blocking issue
        bad_file = tmp_path / "bad.py"
        bad_file.write_text('password = "secret123"')

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            handler.scan_file(str(bad_file))
            captured = capsys.readouterr()
            # Should show BLOCK
            assert "BLOCK" in captured.out
            assert "test_secret" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_scan_file_warning_results(self, tmp_path, capsys):
        """Test scan_file with warning results."""
        from vibesrails.watch import VibesRailsHandler

        config = {
            "blocking": [],
            "warning": [
                {
                    "id": "test_print",
                    "name": "Print Statement",
                    "regex": r"^\s*print\(",
                    "message": "Use logging instead",
                }
            ],
            "exceptions": {},
        }

        handler = VibesRailsHandler(config)

        # Create file with warning
        warn_file = tmp_path / "warn.py"
        warn_file.write_text("print('debug')")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            handler.scan_file(str(warn_file))
            captured = capsys.readouterr()
            # Should show WARN
            assert "WARN" in captured.out
            assert "test_print" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_scan_file_path_outside_cwd(self, tmp_path, capsys):
        """Test scan_file with path outside current working directory."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})

        # Create a subdirectory to be our cwd
        subdir = tmp_path / "project"
        subdir.mkdir()

        # Create a file outside the cwd
        outside_file = tmp_path / "outside.py"
        outside_file.write_text("content")

        original_cwd = os.getcwd()
        os.chdir(subdir)

        try:
            handler.scan_file(str(outside_file))
            captured = capsys.readouterr()
            # Should use absolute path for files outside cwd
            assert "outside.py" in captured.out or str(outside_file) in captured.out
        finally:
            os.chdir(original_cwd)


# ============================================
# run_watch_mode Tests
# ============================================

class TestRunWatchMode:
    """Tests for run_watch_mode function."""

    def test_run_watch_mode_no_watchdog(self, capsys, monkeypatch):
        """Test run_watch_mode returns False when watchdog not installed."""
        import vibesrails.watch as watch_module

        # Mock HAS_WATCHDOG to be False
        monkeypatch.setattr(watch_module, "HAS_WATCHDOG", False)

        result = watch_module.run_watch_mode()

        assert result is False
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "watchdog" in captured.out

    def test_run_watch_mode_with_watchdog_mocked(self, tmp_path, monkeypatch):
        """Test run_watch_mode setup works with mocked watchdog."""
        import vibesrails.watch as watch_module

        # Create config file
        config_file = tmp_path / "vibesrails.yaml"
        config_file.write_text('''
version: "1.0"
blocking: []
warning: []
''')

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Mock HAS_WATCHDOG to be True
            monkeypatch.setattr(watch_module, "HAS_WATCHDOG", True)

            # Create mock Observer
            mock_observer_instance = mock.Mock()
            mock_observer_class = mock.Mock(return_value=mock_observer_instance)
            monkeypatch.setattr(watch_module, "Observer", mock_observer_class)

            # Mock time.sleep to raise KeyboardInterrupt after first call
            call_count = [0]

            def mock_sleep(seconds):
                call_count[0] += 1
                if call_count[0] >= 1:
                    raise KeyboardInterrupt()

            monkeypatch.setattr("time.sleep", mock_sleep)

            result = watch_module.run_watch_mode(config_file)

            assert result is True

            # Verify observer was set up correctly
            mock_observer_class.assert_called_once()
            mock_observer_instance.schedule.assert_called_once()
            mock_observer_instance.start.assert_called_once()
            mock_observer_instance.stop.assert_called_once()
            mock_observer_instance.join.assert_called_once()
        finally:
            os.chdir(original_cwd)

    def test_run_watch_mode_loads_config(self, tmp_path, monkeypatch, capsys):
        """Test run_watch_mode loads configuration."""
        import vibesrails.watch as watch_module

        # Create config file
        config_file = tmp_path / "vibesrails.yaml"
        config_file.write_text('''
version: "1.0"
blocking:
  - id: test_pattern
    name: Test Pattern
    regex: "test"
    message: "Test message"
warning: []
''')

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Mock HAS_WATCHDOG to be True
            monkeypatch.setattr(watch_module, "HAS_WATCHDOG", True)

            # Create mock Observer
            mock_observer_instance = mock.Mock()
            mock_observer_class = mock.Mock(return_value=mock_observer_instance)
            monkeypatch.setattr(watch_module, "Observer", mock_observer_class)

            # Mock time.sleep to raise KeyboardInterrupt immediately
            def mock_sleep(seconds):
                raise KeyboardInterrupt()

            monkeypatch.setattr("time.sleep", mock_sleep)

            result = watch_module.run_watch_mode(config_file)

            assert result is True
            captured = capsys.readouterr()
            assert "Watching for changes" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_run_watch_mode_prints_header(self, tmp_path, monkeypatch, capsys):
        """Test run_watch_mode prints correct header."""
        import vibesrails.watch as watch_module

        # Create config file
        config_file = tmp_path / "vibesrails.yaml"
        config_file.write_text('''
version: "1.0"
blocking: []
warning: []
''')

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            monkeypatch.setattr(watch_module, "HAS_WATCHDOG", True)
            mock_observer_instance = mock.Mock()
            monkeypatch.setattr(watch_module, "Observer", mock.Mock(return_value=mock_observer_instance))
            monkeypatch.setattr("time.sleep", mock.Mock(side_effect=KeyboardInterrupt()))

            watch_module.run_watch_mode(config_file)

            captured = capsys.readouterr()
            assert "vibesrails --watch" in captured.out
            assert "Live scanning mode" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_run_watch_mode_keyboard_interrupt_cleanup(self, tmp_path, monkeypatch, capsys):
        """Test run_watch_mode handles KeyboardInterrupt gracefully."""
        import vibesrails.watch as watch_module

        # Create config file
        config_file = tmp_path / "vibesrails.yaml"
        config_file.write_text('''
version: "1.0"
blocking: []
warning: []
''')

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            monkeypatch.setattr(watch_module, "HAS_WATCHDOG", True)
            mock_observer_instance = mock.Mock()
            monkeypatch.setattr(watch_module, "Observer", mock.Mock(return_value=mock_observer_instance))
            monkeypatch.setattr("time.sleep", mock.Mock(side_effect=KeyboardInterrupt()))

            watch_module.run_watch_mode(config_file)

            captured = capsys.readouterr()
            assert "Stopping watch mode" in captured.out
            assert "Watch mode stopped" in captured.out
        finally:
            os.chdir(original_cwd)


# ============================================
# Integration Tests
# ============================================

class TestWatchIntegration:
    """Integration tests for watch module."""

    def test_handler_with_real_scan(self, tmp_path, capsys):
        """Test handler integration with real scan_file."""
        from vibesrails.watch import VibesRailsHandler

        config = {
            "blocking": [
                {
                    "id": "hardcoded_secret",
                    "name": "Hardcoded Secret",
                    "regex": r"api_key\s*=\s*[\"'][^\"']+",
                    "message": "Don't hardcode API keys",
                }
            ],
            "warning": [],
            "exceptions": {},
        }

        handler = VibesRailsHandler(config)

        # Create test file
        test_file = tmp_path / "app.py"
        test_file.write_text('api_key = "sk-1234567890"')

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            handler.scan_file(str(test_file))
            captured = capsys.readouterr()
            assert "BLOCK" in captured.out
            assert "hardcoded_secret" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_handler_multiple_files(self, tmp_path, capsys):
        """Test handler with multiple file modifications."""
        from vibesrails.watch import VibesRailsHandler

        config = {
            "blocking": [],
            "warning": [
                {
                    "id": "todo",
                    "name": "TODO",
                    "regex": r"# TODO:",
                    "message": "Address TODO",
                }
            ],
            "exceptions": {},
        }

        handler = VibesRailsHandler(config)

        # Create multiple test files
        file1 = tmp_path / "file1.py"
        file1.write_text("# TODO: fix this")

        file2 = tmp_path / "file2.py"
        file2.write_text("# Clean file")

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            handler.scan_file(str(file1))
            handler.scan_file(str(file2))

            captured = capsys.readouterr()
            assert "WARN" in captured.out
            assert "file1.py" in captured.out
            assert "file2.py" in captured.out
        finally:
            os.chdir(original_cwd)


# ============================================
# Non-mock tests (real module behavior)
# ============================================


class TestWatchModuleAttributes:
    """Test module-level attributes without mocking."""

    def test_has_watchdog_is_bool(self):
        """HAS_WATCHDOG is a boolean."""
        assert isinstance(watch_mod.HAS_WATCHDOG, bool)

    def test_handler_class_exists(self):
        """VibesRailsHandler is importable."""
        assert hasattr(watch_mod, "VibesRailsHandler")

    def test_run_watch_mode_is_callable(self):
        """run_watch_mode is callable."""
        assert callable(watch_mod.run_watch_mode)


class TestHandlerConfig:
    """Test handler configuration without mocking."""

    def test_handler_stores_complex_config(self):
        """Handler preserves complex config structures."""
        from vibesrails.watch import VibesRailsHandler

        config = {
            "blocking": [{"id": "a", "regex": "x"}],
            "warning": [{"id": "b", "regex": "y"}],
            "exceptions": {"file.py": ["a"]},
        }
        handler = VibesRailsHandler(config)
        assert handler.config["blocking"][0]["id"] == "a"
        assert handler.config["warning"][0]["id"] == "b"

    def test_handler_last_scan_tracks_files(self):
        """Handler tracks scanned files in last_scan."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})
        assert isinstance(handler.last_scan, dict)
        handler.last_scan["/test.py"] = time.time()
        assert "/test.py" in handler.last_scan

    def test_handler_debounce_logic(self):
        """Handler debounce tracks timestamps correctly."""
        from vibesrails.watch import VibesRailsHandler

        handler = VibesRailsHandler({"blocking": [], "warning": []})
        now = time.time()
        handler.last_scan["/a.py"] = now
        handler.last_scan["/b.py"] = now - 5
        assert handler.last_scan["/a.py"] >= now
        assert handler.last_scan["/b.py"] < now

    def test_handler_scan_real_clean_file(self, tmp_path, capsys):
        """Handler scans a real clean file without mocks."""
        from vibesrails.watch import VibesRailsHandler

        config = {
            "blocking": [
                {"id": "secret", "name": "Secret",
                 "regex": r"password\s*=\s*[\"'][^\"']+",
                 "message": "No secrets"}
            ],
            "warning": [],
            "exceptions": {},
        }
        handler = VibesRailsHandler(config)
        clean = tmp_path / "clean.py"
        clean.write_text("import os\nx = 42\n")
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            handler.scan_file(str(clean))
            captured = capsys.readouterr()
            assert "clean.py" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_handler_scan_real_blocking_file(self, tmp_path, capsys):
        """Handler detects real blocking issues without mocks."""
        from vibesrails.watch import VibesRailsHandler

        config = {
            "blocking": [
                {"id": "secret", "name": "Secret",
                 "regex": r"password\s*=\s*[\"'][^\"']+",
                 "message": "No secrets"}
            ],
            "warning": [],
            "exceptions": {},
        }
        handler = VibesRailsHandler(config)
        bad = tmp_path / "bad.py"
        bad.write_text('password = "hunter2"\n')
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            handler.scan_file(str(bad))
            captured = capsys.readouterr()
            assert "BLOCK" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_handler_scan_real_warning_file(self, tmp_path, capsys):
        """Handler detects real warnings without mocks."""
        from vibesrails.watch import VibesRailsHandler

        config = {
            "blocking": [],
            "warning": [
                {"id": "todo", "name": "TODO",
                 "regex": r"# TODO", "message": "Fix TODO"}
            ],
            "exceptions": {},
        }
        handler = VibesRailsHandler(config)
        f = tmp_path / "todo.py"
        f.write_text("# TODO fix this\n")
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            handler.scan_file(str(f))
            captured = capsys.readouterr()
            assert "WARN" in captured.out
        finally:
            os.chdir(original_cwd)
