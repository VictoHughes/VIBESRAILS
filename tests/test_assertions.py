"""Tests for vibesrails assertions system."""

import subprocess
from unittest import mock

from vibesrails.assertions import (
    AssertionResult,
    assertions_exit_code,
    check_baselines,
    check_rules,
    check_values,
    format_assertions_report,
    run_assertions,
)

# ============================================
# check_values
# ============================================


def test_check_values_found(tmp_path):
    """Value found in Python file returns ok."""
    py_file = tmp_path / "app.py"
    py_file.write_text('MODEL = "gpt-4o"\n')
    results = check_values(tmp_path, {"llm_model": "gpt-4o"})
    assert len(results) == 1
    assert results[0].status == "ok"
    assert "gpt-4o" in results[0].message


def test_check_values_not_found(tmp_path):
    """Value not found returns fail."""
    py_file = tmp_path / "app.py"
    py_file.write_text('MODEL = "gpt-3.5"\n')
    results = check_values(tmp_path, {"llm_model": "gpt-4o"})
    assert len(results) == 1
    assert results[0].status == "fail"
    assert "not found" in results[0].message


def test_check_values_multiple(tmp_path):
    """Multiple values checked independently."""
    py_file = tmp_path / "config.py"
    py_file.write_text('MODEL = "gpt-4o"\nRETRIES = 3\n')
    results = check_values(tmp_path, {"llm_model": "gpt-4o", "max_retries": 3})
    assert len(results) == 2
    assert results[0].status == "ok"  # gpt-4o found
    assert results[1].status == "ok"  # 3 found


def test_check_values_empty():
    """Empty values dict returns nothing."""
    results = check_values(None, {})
    assert results == []


def test_check_values_skips_venv(tmp_path):
    """Files in .venv are skipped."""
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "pkg.py").write_text('x = "target_value"\n')
    results = check_values(tmp_path, {"key": "target_value"})
    assert len(results) == 1
    assert results[0].status == "fail"


def test_check_values_integer(tmp_path):
    """Integer values are stringified for search."""
    py_file = tmp_path / "config.py"
    py_file.write_text("MAX_RETRIES = 3\n")
    results = check_values(tmp_path, {"max_retries": 3})
    assert len(results) == 1
    assert results[0].status == "ok"


def test_check_values_details_list(tmp_path):
    """Found files listed in details."""
    (tmp_path / "a.py").write_text("x = 42\n")
    (tmp_path / "b.py").write_text("y = 42\n")
    results = check_values(tmp_path, {"val": 42})
    assert results[0].status == "ok"
    assert len(results[0].details) == 2


# ============================================
# check_rules — fail_closed
# ============================================


def test_rule_fail_closed_ok(tmp_path):
    """No silent except/pass returns ok."""
    py_file = tmp_path / "app.py"
    py_file.write_text("try:\n    x = 1\nexcept ValueError:\n    log(e)\n")
    results = check_rules(tmp_path, {"fail_closed": True})
    assert len(results) == 1
    assert results[0].status == "ok"


def test_rule_fail_closed_violation(tmp_path):
    """Silent except/pass returns fail."""
    py_file = tmp_path / "app.py"
    py_file.write_text("try:\n    x = 1\nexcept Exception:\n    pass\n")
    results = check_rules(tmp_path, {"fail_closed": True})
    assert len(results) == 1
    assert results[0].status == "fail"
    assert "silent" in results[0].message.lower()


def test_rule_fail_closed_multiple_violations(tmp_path):
    """Multiple violations counted."""
    code = (
        "try:\n    a()\nexcept Exception:\n    pass\n"
        "\n"
        "try:\n    b()\nexcept ValueError:\n    pass\n"
    )
    py_file = tmp_path / "app.py"
    py_file.write_text(code)
    results = check_rules(tmp_path, {"fail_closed": True})
    assert results[0].status == "fail"
    assert "2" in results[0].message


def test_rule_fail_closed_disabled(tmp_path):
    """Disabled rule is skipped."""
    results = check_rules(tmp_path, {"fail_closed": False})
    assert results == []


# ============================================
# check_rules — single_entry_point
# ============================================


def test_rule_single_entry_point_ok(tmp_path):
    """One entry point returns ok."""
    (tmp_path / "main.py").write_text('if __name__ == "__main__":\n    run()\n')
    results = check_rules(tmp_path, {"single_entry_point": True})
    assert len(results) == 1
    assert results[0].status == "ok"


def test_rule_single_entry_point_multiple(tmp_path):
    """Multiple entry points returns fail."""
    (tmp_path / "main.py").write_text('if __name__ == "__main__":\n    run()\n')
    (tmp_path / "cli.py").write_text("if __name__ == '__main__':\n    cli()\n")
    results = check_rules(tmp_path, {"single_entry_point": True})
    assert len(results) == 1
    assert results[0].status == "fail"
    assert "2" in results[0].message


def test_rule_single_entry_point_zero(tmp_path):
    """Zero entry points is ok (library)."""
    (tmp_path / "lib.py").write_text("def hello():\n    pass\n")
    results = check_rules(tmp_path, {"single_entry_point": True})
    assert results[0].status == "ok"
    assert "0" in results[0].message


def test_rule_single_entry_point_skips_tests(tmp_path):
    """Test files with __main__ are excluded."""
    (tmp_path / "test_main.py").write_text('if __name__ == "__main__":\n    test()\n')
    results = check_rules(tmp_path, {"single_entry_point": True})
    assert results[0].status == "ok"


# ============================================
# check_rules — unknown
# ============================================


def test_rule_unknown(tmp_path):
    """Unknown rule returns fail."""
    results = check_rules(tmp_path, {"nonexistent_rule": True})
    assert len(results) == 1
    assert results[0].status == "fail"
    assert "Unknown" in results[0].message


def test_rules_empty():
    """Empty rules returns nothing."""
    results = check_rules(None, {})
    assert results == []


# ============================================
# check_baselines — test_count
# ============================================


def test_baseline_test_count_ok(tmp_path):
    """Test count meets baseline returns ok."""
    mock_result = mock.Mock(
        returncode=0,
        stdout="200 tests collected in 1.0s\n",
        stderr="",
    )
    with mock.patch("vibesrails.assertions.subprocess.run", return_value=mock_result):
        results = check_baselines(tmp_path, {"test_count": 100})
    assert len(results) == 1
    assert results[0].status == "ok"
    assert "200" in results[0].message


def test_baseline_test_count_below(tmp_path):
    """Test count below baseline returns fail."""
    mock_result = mock.Mock(
        returncode=0,
        stdout="50 tests collected in 0.5s\n",
        stderr="",
    )
    with mock.patch("vibesrails.assertions.subprocess.run", return_value=mock_result):
        results = check_baselines(tmp_path, {"test_count": 100})
    assert len(results) == 1
    assert results[0].status == "fail"
    assert "50" in results[0].message
    assert "delta: -50" in results[0].message


def test_baseline_test_count_collect_fail(tmp_path):
    """Failed collection returns fail."""
    with mock.patch(
        "vibesrails.assertions.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=60),
    ):
        results = check_baselines(tmp_path, {"test_count": 100})
    assert results[0].status == "fail"
    assert "Could not collect" in results[0].message


# ============================================
# check_baselines — zero_regressions
# ============================================


def test_baseline_zero_regressions_ok(tmp_path):
    """All tests passing returns ok."""
    mock_result = mock.Mock(returncode=0, stdout="100 passed\n")
    with mock.patch("vibesrails.assertions.subprocess.run", return_value=mock_result):
        results = check_baselines(tmp_path, {"zero_regressions": True})
    assert len(results) == 1
    assert results[0].status == "ok"


def test_baseline_zero_regressions_fail(tmp_path):
    """Failing tests returns fail."""
    mock_result = mock.Mock(returncode=1, stdout="3 failed, 97 passed\n")
    with mock.patch("vibesrails.assertions.subprocess.run", return_value=mock_result):
        results = check_baselines(tmp_path, {"zero_regressions": True})
    assert results[0].status == "fail"
    assert "3" in results[0].message


def test_baseline_zero_regressions_disabled(tmp_path):
    """Disabled zero_regressions skipped."""
    results = check_baselines(tmp_path, {"zero_regressions": False})
    assert results == []


def test_baselines_empty():
    """Empty baselines returns nothing."""
    results = check_baselines(None, {})
    assert results == []


# ============================================
# run_assertions (orchestrator)
# ============================================


def test_run_assertions_all_categories(tmp_path):
    """Orchestrator runs all three categories."""
    (tmp_path / "app.py").write_text('x = "hello"\n')
    config = {
        "values": {"greeting": "hello"},
        "rules": {"fail_closed": True},
    }
    # No baselines to avoid subprocess
    results = run_assertions(tmp_path, config)
    categories = {r.category for r in results}
    assert "values" in categories
    assert "rules" in categories


def test_run_assertions_empty_config(tmp_path):
    """Empty config returns no results."""
    results = run_assertions(tmp_path, {})
    assert results == []


# ============================================
# format_assertions_report
# ============================================


def test_format_report_header():
    """Report includes assertions header."""
    results = [AssertionResult("values", "x", "ok", "found")]
    report = format_assertions_report(results)
    assert "ASSERTIONS CHECK" in report


def test_format_report_grouped_by_category():
    """Report groups by category."""
    results = [
        AssertionResult("values", "a", "ok", "found"),
        AssertionResult("rules", "b", "fail", "violated"),
    ]
    report = format_assertions_report(results)
    assert "VALUES" in report
    assert "RULES" in report


def test_format_report_failure_summary():
    """Report shows failure count."""
    results = [
        AssertionResult("values", "a", "fail", "missing"),
        AssertionResult("rules", "b", "ok", "clean"),
    ]
    report = format_assertions_report(results)
    assert "1 assertion(s) failed" in report


def test_format_report_all_pass():
    """Report shows all passed."""
    results = [
        AssertionResult("values", "a", "ok", "found"),
        AssertionResult("rules", "b", "ok", "clean"),
    ]
    report = format_assertions_report(results)
    assert "All 2 assertion(s) passed" in report


# ============================================
# exit_code
# ============================================


def test_exit_code_all_pass():
    """All passing returns 0."""
    results = [AssertionResult("values", "a", "ok", "found")]
    assert assertions_exit_code(results) == 0


def test_exit_code_failure():
    """Any failure returns 1."""
    results = [
        AssertionResult("values", "a", "ok", "found"),
        AssertionResult("rules", "b", "fail", "violated"),
    ]
    assert assertions_exit_code(results) == 1


# ============================================
# preflight integration
# ============================================


def test_preflight_assertions_no_config(tmp_path):
    """Preflight assertions check skips when no config."""
    from vibesrails.preflight import check_assertions

    with mock.patch("vibesrails.preflight.find_config", return_value=None):
        result = check_assertions(tmp_path)
    assert result.status == "info"
    assert "skipped" in result.message.lower()


def test_preflight_assertions_no_section(tmp_path):
    """Preflight assertions check skips when no assertions section."""
    from vibesrails.preflight import check_assertions

    config_file = mock.Mock()
    config_file.exists.return_value = True
    with mock.patch("vibesrails.preflight.find_config", return_value=config_file):
        with mock.patch("vibesrails.preflight.load_config", return_value={"version": "1.0"}):
            result = check_assertions(tmp_path)
    assert result.status == "info"
    assert "skipped" in result.message.lower()


def test_preflight_assertions_failures(tmp_path):
    """Preflight assertions warns on failures."""
    from vibesrails.preflight import check_assertions

    config_file = mock.Mock()
    config_file.exists.return_value = True
    config = {
        "assertions": {
            "values": {"missing_val": "xyz123"},
        },
    }
    with mock.patch("vibesrails.preflight.find_config", return_value=config_file):
        with mock.patch("vibesrails.preflight.load_config", return_value=config):
            result = check_assertions(tmp_path)
    assert result.status == "warn"
    assert "failed" in result.message


def test_preflight_assertions_all_pass(tmp_path):
    """Preflight assertions ok when all pass."""
    from vibesrails.preflight import check_assertions

    (tmp_path / "app.py").write_text('val = "expected"\n')
    config_file = mock.Mock()
    config_file.exists.return_value = True
    config = {
        "assertions": {
            "values": {"key": "expected"},
        },
    }
    with mock.patch("vibesrails.preflight.find_config", return_value=config_file):
        with mock.patch("vibesrails.preflight.load_config", return_value=config):
            result = check_assertions(tmp_path)
    assert result.status == "ok"
    assert "passed" in result.message
