"""Tests for PR Checklist Guard — real diff strings, no mocking except git subprocess."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from vibesrails.guards_v2.pr_checklist import PRChecklistGuard


def _diff(*file_sections):
    """Build a realistic git diff from (filename, body) tuples."""
    parts = []
    for fname, body in file_sections:
        parts.append(f"diff --git a/{fname} b/{fname}")
        parts.append(f"--- a/{fname}")
        parts.append(f"+++ b/{fname}")
        parts.append("@@ -1,5 +1,10 @@")
        parts.append(body)
    return "\n".join(parts)


# ── analyze_diff ───────────────────────────────────────


class TestAnalyzeDiff:
    def test_empty_diff_returns_nothing(self):
        assert PRChecklistGuard().analyze_diff("") == []

    def test_code_without_tests_triggers_add_tests(self):
        diff = _diff(("src/app.py", "+def hello():\n+    return 1"))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Add tests" in msgs

    def test_code_with_test_file_no_add_tests(self):
        diff = _diff(
            ("src/app.py", "+def hello():\n+    return 1"),
            ("tests/test_app.py", "+def test_hello():\n+    assert True"),
        )
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Add tests" not in msgs

    def test_breaking_change_signature_modified(self):
        diff = _diff((
            "lib/core.py",
            "-  def process(self, data):\n"
            "+  def process(self, data, strict=False):\n"
        ))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Document breaking changes" in msgs

    def test_private_func_change_is_not_breaking(self):
        diff = _diff((
            "lib/core.py",
            "-  def _helper(self, x):\n"
            "+  def _helper(self, x, y):\n"
        ))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Document breaking changes" not in msgs

    def test_same_signature_not_breaking(self):
        diff = _diff((
            "lib/core.py",
            "-  def process(self, data):\n"
            "+  def process(self, data):\n"
            "+      # new comment\n"
        ))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Document breaking changes" not in msgs

    def test_new_env_var_os_environ(self):
        diff = _diff(("config.py", "+    val = os.environ['SECRET_KEY']"))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Update .env.example" in msgs

    def test_new_env_var_os_getenv(self):
        diff = _diff(("settings.py", "+    db = os.getenv('DATABASE_URL')"))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Update .env.example" in msgs

    def test_no_env_var_no_update(self):
        diff = _diff(("utils.py", "+x = 42"))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Update .env.example" not in msgs

    def test_migration_needed_models_py(self):
        diff = _diff(("app/models.py", "+class User:\n+    pass"))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Create migration" in msgs

    def test_migration_needed_alembic(self):
        diff = _diff(("alembic/versions/001.py", "+revision = '001'"))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Create migration" in msgs

    def test_security_review_auth_file(self):
        diff = _diff(("auth/login.py", "+def login(): pass"))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Security review needed" in msgs

    def test_security_review_crypto_file(self):
        diff = _diff(("utils/crypto.py", "+import hashlib"))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Security review needed" in msgs

    def test_new_deps_requirements(self):
        diff = _diff(("requirements.txt", "+flask==3.0.0"))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Audit new deps" in msgs

    def test_new_deps_pyproject(self):
        diff = _diff(("pyproject.toml", '+dependencies = ["flask"]'))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Audit new deps" in msgs

    def test_api_changes_new_function(self):
        diff = _diff(("api.py", "+def get_users(request):\n+    return []"))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Update documentation" in msgs

    def test_api_changes_new_class(self):
        diff = _diff(("models.py", "+class UserSerializer:\n+    pass"))
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Update documentation" in msgs

    def test_all_issues_have_info_severity(self):
        diff = _diff(
            ("auth/models.py", "+class Token:\n+    pass"),
            ("requirements.txt", "+bcrypt==4.0"),
        )
        issues = PRChecklistGuard().analyze_diff(diff)
        assert all(i.severity == "info" for i in issues)
        assert len(issues) >= 3

    def test_complex_diff_multiple_checks(self):
        diff = _diff(
            ("auth/models.py", "+class Session:\n+    pass"),
            ("requirements.txt", "+redis==5.0"),
            ("config.py", "+    url = os.environ['REDIS_URL']"),
        )
        msgs = [i.message for i in PRChecklistGuard().analyze_diff(diff)]
        assert "Security review needed" in msgs
        assert "Audit new deps" in msgs
        assert "Update .env.example" in msgs
        assert "Create migration" in msgs


# ── generate_checklist ──────────────────────────────────


class TestGenerateChecklist:
    def test_empty_diff_returns_no_checklist(self):
        result = PRChecklistGuard().generate_checklist("")
        assert "No checklist" in result

    def test_checklist_markdown_format(self):
        diff = _diff(("src/app.py", "+def new_func(): pass"))
        result = PRChecklistGuard().generate_checklist(diff)
        assert result.startswith("## PR Checklist")
        assert "- [ ]" in result

    def test_checklist_contains_all_items(self):
        diff = _diff(
            ("auth/models.py", "+class User:\n+    pass"),
            ("requirements.txt", "+flask"),
        )
        result = PRChecklistGuard().generate_checklist(diff)
        assert "Security review needed" in result
        assert "Audit new deps" in result


# ── scan (mock only git subprocess) ─────────────────────


class TestScan:
    def test_scan_calls_git_diff_cached(self, tmp_path):
        mock_result = type("R", (), {"returncode": 0, "stdout": ""})()
        with patch(
            "subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            PRChecklistGuard().scan(tmp_path)
            mock_run.assert_called_once()
            assert mock_run.call_args[0][0] == ["git", "diff", "--cached"]

    def test_scan_returns_empty_on_failure(self, tmp_path):
        mock_result = type("R", (), {"returncode": 128, "stdout": ""})()
        with patch(
            "subprocess.run",
            return_value=mock_result,
        ):
            assert PRChecklistGuard().scan(tmp_path) == []

    def test_scan_handles_timeout(self, tmp_path):
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired("git", 30),
        ):
            assert PRChecklistGuard().scan(tmp_path) == []

    def test_scan_handles_file_not_found(self, tmp_path):
        with patch(
            "subprocess.run",
            side_effect=FileNotFoundError(),
        ):
            assert PRChecklistGuard().scan(tmp_path) == []

    def test_scan_with_real_diff_output(self, tmp_path):
        real_diff = (
            "diff --git a/app.py b/app.py\n"
            "+++ b/app.py\n"
            "+def hello(): pass\n"
        )
        mock_result = type("R", (), {"returncode": 0, "stdout": real_diff})()
        with patch(
            "subprocess.run",
            return_value=mock_result,
        ):
            issues = PRChecklistGuard().scan(tmp_path)
            msgs = [i.message for i in issues]
            assert "Add tests" in msgs
