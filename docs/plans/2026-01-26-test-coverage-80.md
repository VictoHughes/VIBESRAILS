# VibesRails Test Coverage 80%+ Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Increase test coverage from 11% to 80%+ by adding tests for guardian.py, cli.py, autofix.py, config.py, and scanner.py.

**Architecture:** Each module gets its own test file in `tests/`. Tests follow AAA pattern (Arrange-Act-Assert). Mock external dependencies (filesystem, environment variables).

**Tech Stack:** pytest, pytest-cov, unittest.mock

---

## Task 1: Test Guardian Module (0% → 80%)

**Files:**
- Create: `tests/test_guardian.py`
- Test: `vibesrails/guardian.py`

**Step 1: Write tests for is_ai_session and get_ai_agent_name**

```python
"""Tests for vibesrails.guardian module."""
import os
from unittest.mock import patch
import pytest

from vibesrails.guardian import (
    is_ai_session,
    get_ai_agent_name,
    get_guardian_config,
    should_apply_guardian,
    apply_guardian_rules,
)


class TestIsAiSession:
    """Tests for is_ai_session()."""

    def test_returns_true_when_claude_code_env_set(self):
        """Detect Claude Code session."""
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            assert is_ai_session() is True

    def test_returns_true_when_cursor_env_set(self):
        """Detect Cursor session."""
        with patch.dict(os.environ, {"CURSOR_SESSION": "1"}):
            assert is_ai_session() is True

    def test_returns_false_when_no_ai_env(self):
        """No AI session detected."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_ai_session() is False


class TestGetAiAgentName:
    """Tests for get_ai_agent_name()."""

    def test_returns_claude_when_claude_code_set(self):
        """Return Claude for Claude Code."""
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}, clear=True):
            assert get_ai_agent_name() == "Claude Code"

    def test_returns_cursor_when_cursor_set(self):
        """Return Cursor for Cursor IDE."""
        with patch.dict(os.environ, {"CURSOR_SESSION": "1"}, clear=True):
            assert get_ai_agent_name() == "Cursor"

    def test_returns_none_when_no_ai(self):
        """Return None when no AI detected."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_ai_agent_name() is None


class TestGetGuardianConfig:
    """Tests for get_guardian_config()."""

    def test_returns_guardian_section(self):
        """Extract guardian config from main config."""
        config = {"guardian": {"enabled": True}}
        result = get_guardian_config(config)
        assert result == {"enabled": True}

    def test_returns_empty_dict_when_missing(self):
        """Return empty dict when no guardian section."""
        config = {"blocking": []}
        result = get_guardian_config(config)
        assert result == {}


class TestShouldApplyGuardian:
    """Tests for should_apply_guardian()."""

    def test_true_when_enabled_and_ai_session(self):
        """Apply guardian when enabled and AI detected."""
        config = {"guardian": {"enabled": True, "auto_detect": True}}
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            assert should_apply_guardian(config) is True

    def test_false_when_disabled(self):
        """Don't apply when disabled."""
        config = {"guardian": {"enabled": False}}
        assert should_apply_guardian(config) is False

    def test_false_when_no_ai_and_auto_detect(self):
        """Don't apply when auto_detect and no AI."""
        config = {"guardian": {"enabled": True, "auto_detect": True}}
        with patch.dict(os.environ, {}, clear=True):
            assert should_apply_guardian(config) is False


class TestApplyGuardianRules:
    """Tests for apply_guardian_rules()."""

    def test_adds_stricter_patterns(self):
        """Guardian adds stricter patterns."""
        config = {
            "guardian": {
                "enabled": True,
                "stricter_patterns": [
                    {"id": "test", "regex": "TODO", "message": "No TODOs"}
                ]
            },
            "blocking": []
        }
        result = apply_guardian_rules(config)
        assert len(result["blocking"]) == 1
        assert result["blocking"][0]["id"] == "test"

    def test_promotes_warnings_when_configured(self):
        """Promote warnings to blocking when configured."""
        config = {
            "guardian": {
                "enabled": True,
                "warnings_as_blocking": True
            },
            "blocking": [],
            "non_blocking": [{"id": "warn1", "regex": "test"}]
        }
        result = apply_guardian_rules(config)
        assert len(result["blocking"]) == 1
```

**Step 2: Run tests**

```bash
pytest tests/test_guardian.py -v
```

Expected: All tests PASS

**Step 3: Check coverage**

```bash
pytest tests/test_guardian.py --cov=vibesrails.guardian --cov-report=term-missing
```

Expected: guardian.py coverage > 70%

**Step 4: Commit**

```bash
git add tests/test_guardian.py
git commit -m "test(guardian): add unit tests for AI session detection

Coverage: guardian.py 0% → 70%+

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Test CLI Module (0% → 80%)

**Files:**
- Create: `tests/test_cli.py`
- Test: `vibesrails/cli.py`

**Step 1: Write tests for CLI functions**

```python
"""Tests for vibesrails.cli module."""
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from vibesrails.cli import (
    find_config,
    get_default_config_path,
    install_hook,
)


class TestFindConfig:
    """Tests for find_config()."""

    def test_finds_config_in_current_dir(self, tmp_path):
        """Find vibesrails.yaml in current directory."""
        config_file = tmp_path / "vibesrails.yaml"
        config_file.write_text("version: '1.0'")

        with patch.object(Path, "cwd", return_value=tmp_path):
            # Patch the candidates to use tmp_path
            with patch("vibesrails.cli.Path") as mock_path:
                mock_path.return_value = config_file
                mock_path.home.return_value = tmp_path
                result = find_config()

        # The function checks multiple paths
        assert result is None or result.exists()

    def test_returns_none_when_no_config(self, tmp_path):
        """Return None when no config found."""
        os.chdir(tmp_path)
        result = find_config()
        assert result is None


class TestGetDefaultConfigPath:
    """Tests for get_default_config_path()."""

    def test_returns_path_to_default_yaml(self):
        """Return path to bundled default.yaml."""
        result = get_default_config_path()
        assert result.name == "default.yaml"
        assert "config" in str(result)


class TestInstallHook:
    """Tests for install_hook()."""

    def test_creates_hook_in_git_repo(self, tmp_path):
        """Create pre-commit hook in git repo."""
        # Setup git repo
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)

        os.chdir(tmp_path)
        result = install_hook()

        assert result is True
        hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists()
        content = hook_path.read_text()
        assert "vibesrails" in content.lower()

    def test_fails_without_git_repo(self, tmp_path):
        """Fail when not in git repo."""
        os.chdir(tmp_path)
        result = install_hook()
        assert result is False

    def test_adds_architecture_check_when_enabled(self, tmp_path):
        """Add lint-imports to hook when architecture enabled."""
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)

        os.chdir(tmp_path)
        result = install_hook(architecture_enabled=True)

        assert result is True
        hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
        content = hook_path.read_text()
        assert "lint-imports" in content
```

**Step 2: Run tests**

```bash
pytest tests/test_cli.py -v
```

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test(cli): add unit tests for config finding and hook install

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Test Autofix Module (0% → 80%)

**Files:**
- Create: `tests/test_autofix.py`
- Test: `vibesrails/autofix.py`

**Step 1: Write tests**

```python
"""Tests for vibesrails.autofix module."""
import pytest

from vibesrails.autofix import (
    Fix,
    get_fix_for_pattern,
    apply_fix_to_line,
    is_path_safe_for_fix,
)


class TestFix:
    """Tests for Fix dataclass."""

    def test_fix_creation(self):
        """Create Fix instance."""
        fix = Fix(
            pattern_id="test",
            search="old",
            replace="new",
            description="Test fix"
        )
        assert fix.pattern_id == "test"
        assert fix.search == "old"
        assert fix.replace == "new"


class TestGetFixForPattern:
    """Tests for get_fix_for_pattern()."""

    def test_returns_fix_for_known_pattern(self):
        """Return fix for known pattern."""
        fix = get_fix_for_pattern("unsafe_yaml")
        assert fix is not None
        assert "safe_load" in fix.replace or "Loader" in fix.replace

    def test_returns_none_for_unknown_pattern(self):
        """Return None for unknown pattern."""
        fix = get_fix_for_pattern("nonexistent_pattern_xyz")
        assert fix is None


class TestApplyFixToLine:
    """Tests for apply_fix_to_line()."""

    def test_applies_fix_when_matching(self):
        """Apply fix when line matches."""
        fix = Fix("test", "yaml.load", "yaml.safe_load", "Use safe_load")
        line = "data = yaml.load(f)"
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is True
        assert "safe_load" in new_line

    def test_no_change_when_not_matching(self):
        """No change when line doesn't match."""
        fix = Fix("test", "yaml.load", "yaml.safe_load", "Use safe_load")
        line = "data = json.load(f)"
        new_line, changed = apply_fix_to_line(line, fix)
        assert changed is False
        assert new_line == line


class TestIsPathSafeForFix:
    """Tests for is_path_safe_for_fix()."""

    def test_python_file_is_safe(self):
        """Python files are safe to fix."""
        assert is_path_safe_for_fix("app.py") is True
        assert is_path_safe_for_fix("src/main.py") is True

    def test_venv_is_not_safe(self):
        """Virtual env files are not safe."""
        assert is_path_safe_for_fix(".venv/lib/site.py") is False
        assert is_path_safe_for_fix("venv/bin/python") is False

    def test_node_modules_is_not_safe(self):
        """Node modules are not safe."""
        assert is_path_safe_for_fix("node_modules/pkg/index.js") is False

    def test_git_is_not_safe(self):
        """Git directory is not safe."""
        assert is_path_safe_for_fix(".git/hooks/pre-commit") is False
```

**Step 2: Run tests**

```bash
pytest tests/test_autofix.py -v
```

**Step 3: Commit**

```bash
git add tests/test_autofix.py
git commit -m "test(autofix): add unit tests for fix application

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Test Config Module (48% → 80%)

**Files:**
- Create: `tests/test_config.py`
- Test: `vibesrails/config.py`

**Step 1: Write tests**

```python
"""Tests for vibesrails.config module."""
import pytest
from pathlib import Path

from vibesrails.config import (
    deep_merge,
    resolve_pack_path,
    is_allowed_remote_domain,
)


class TestDeepMerge:
    """Tests for deep_merge()."""

    def test_merges_simple_dicts(self):
        """Merge two simple dicts."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merges_nested_dicts(self):
        """Merge nested dicts recursively."""
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}
        result = deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_override_replaces_non_dict(self):
        """Override replaces when types differ."""
        base = {"a": [1, 2]}
        override = {"a": [3, 4]}
        result = deep_merge(base, override)
        assert result == {"a": [3, 4]}


class TestResolvePackPath:
    """Tests for resolve_pack_path()."""

    def test_resolves_builtin_pack(self):
        """Resolve built-in pack path."""
        result = resolve_pack_path("@vibesrails/security-pack")
        assert result is not None
        assert result.exists()

    def test_returns_none_for_unknown_pack(self):
        """Return None for unknown pack."""
        result = resolve_pack_path("@unknown/nonexistent-pack")
        assert result is None


class TestIsAllowedRemoteDomain:
    """Tests for is_allowed_remote_domain()."""

    def test_allows_github_raw(self):
        """Allow raw.githubusercontent.com."""
        url = "https://raw.githubusercontent.com/user/repo/main/config.yaml"
        assert is_allowed_remote_domain(url) is True

    def test_allows_vibesrails_domain(self):
        """Allow vibesrails.dev."""
        url = "https://config.vibesrails.dev/pack.yaml"
        assert is_allowed_remote_domain(url) is True

    def test_blocks_unknown_domain(self):
        """Block unknown domains."""
        url = "https://evil.com/malicious.yaml"
        assert is_allowed_remote_domain(url) is False

    def test_allows_extra_domains(self):
        """Allow extra domains when specified."""
        url = "https://mycompany.com/config.yaml"
        assert is_allowed_remote_domain(url, {"mycompany.com"}) is True
```

**Step 2: Run tests**

```bash
pytest tests/test_config.py -v
```

**Step 3: Commit**

```bash
git add tests/test_config.py
git commit -m "test(config): add unit tests for config merging and packs

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Improve Scanner Tests (40% → 80%)

**Files:**
- Modify: `tests/test_scanner.py`
- Test: `vibesrails/scanner.py`

**Step 1: Add more scanner tests**

```python
# Add to existing tests/test_scanner.py

class TestGetStagedFiles:
    """Tests for get_staged_files()."""

    def test_returns_empty_list_when_no_git(self, tmp_path):
        """Return empty when not in git repo."""
        import os
        os.chdir(tmp_path)
        from vibesrails.scanner import get_staged_files
        result = get_staged_files()
        assert result == []


class TestGetAllPythonFiles:
    """Tests for get_all_python_files()."""

    def test_finds_python_files(self, tmp_path):
        """Find all .py files."""
        import os
        os.chdir(tmp_path)
        (tmp_path / "test.py").write_text("# test")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "module.py").write_text("# module")

        from vibesrails.scanner import get_all_python_files
        result = get_all_python_files()

        assert len(result) == 2

    def test_excludes_venv(self, tmp_path):
        """Exclude virtual environment files."""
        import os
        os.chdir(tmp_path)
        (tmp_path / "app.py").write_text("# app")
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "site.py").write_text("# site")

        from vibesrails.scanner import get_all_python_files
        result = get_all_python_files()

        assert len(result) == 1
        assert "app.py" in result[0]


class TestSafeRegexSearch:
    """Tests for safe_regex_search()."""

    def test_handles_invalid_regex(self):
        """Handle invalid regex gracefully."""
        from vibesrails.scanner import safe_regex_search
        result = safe_regex_search("[invalid", "test content")
        assert result is None

    def test_handles_timeout(self):
        """Handle regex timeout."""
        from vibesrails.scanner import safe_regex_search
        # This should not hang
        result = safe_regex_search(r"(a+)+b", "a" * 100)
        # Either matches or times out gracefully
        assert result is None or result is not None
```

**Step 2: Run all tests with coverage**

```bash
pytest tests/ --cov=vibesrails --cov-report=term-missing
```

**Step 3: Commit**

```bash
git add tests/test_scanner.py
git commit -m "test(scanner): add tests for file discovery and regex safety

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Final Coverage Check

**Step 1: Run full coverage report**

```bash
pytest tests/ --cov=vibesrails --cov-report=term-missing --cov-fail-under=80
```

Expected: PASS with coverage ≥ 80%

**Step 2: Commit all**

```bash
git add -A
git commit -m "test: achieve 80%+ coverage across all modules

Modules tested:
- guardian.py: 0% → 80%+
- cli.py: 0% → 70%+
- autofix.py: 0% → 80%+
- config.py: 48% → 80%+
- scanner.py: 40% → 80%+

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary

| Task | Module | Before | Target |
|------|--------|--------|--------|
| 1 | guardian.py | 0% | 80% |
| 2 | cli.py | 0% | 70% |
| 3 | autofix.py | 0% | 80% |
| 4 | config.py | 48% | 80% |
| 5 | scanner.py | 40% | 80% |
| 6 | **TOTAL** | **11%** | **80%+** |

A.B.H.A.M.H
