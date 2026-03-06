"""Tests for project phase detection."""

from unittest import mock

import yaml

from vibesrails.context.phase import (
    PhaseDetector,
    ProjectPhase,
)

# ============================================
# Phase detection — empty project (Phase 0)
# ============================================


def test_detect_phase0_empty_project(tmp_path):
    """Empty directory detects as DECIDE phase."""
    detector = PhaseDetector(tmp_path)
    result = detector.detect()
    assert result.phase == ProjectPhase.DECIDE
    assert not result.is_override
    assert len(result.missing_for_next) > 0


def test_detect_phase0_signals(tmp_path):
    """Empty project has all signals False/0."""
    detector = PhaseDetector(tmp_path)
    signals = detector.collect_signals()
    assert not signals.has_readme
    assert not signals.has_claude_md
    assert not signals.has_adr
    assert signals.test_count == 0
    assert signals.module_count == 0


# ============================================
# Phase 1 — SKELETON prerequisites
# ============================================


def test_detect_phase1_with_prerequisites(tmp_path):
    """Phase advances to SKELETON when gates are met."""
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "decisions.md").write_text("# Decisions")
    # Create typed functions (contracts)
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(3):
        (pkg / f"mod{i}.py").write_text(
            f"def func{i}(x: int) -> str:\n    return str(x)\n"
        )

    detector = PhaseDetector(tmp_path)
    result = detector.detect()
    assert result.phase == ProjectPhase.SKELETON


def test_phase1_missing_readme(tmp_path):
    """Without README, stays at DECIDE even with other gates."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "decisions.md").write_text("# Decisions")
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "mod.py").write_text("def f(x: int) -> str:\n    return str(x)\n")
    (pkg / "mod2.py").write_text("def g(x: int) -> str:\n    return str(x)\n")
    (pkg / "mod3.py").write_text("def h(x: int) -> str:\n    return str(x)\n")

    detector = PhaseDetector(tmp_path)
    result = detector.detect()
    assert result.phase == ProjectPhase.DECIDE
    assert "has_readme" in result.missing_for_next


# ============================================
# Phase 2 — FLESH OUT
# ============================================


def test_detect_phase2_with_tests(tmp_path):
    """Phase advances to FLESH_OUT with enough tests and modules."""
    # Phase 1 prerequisites
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "ADR").mkdir()
    (tmp_path / "ADR" / "001.md").write_text("# ADR 001")
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(4):
        (pkg / f"mod{i}.py").write_text(
            f"def func{i}(x: int) -> str:\n    return str(x)\n"
        )

    # Phase 2 prerequisites: 5+ tests, 3+ modules
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_content = "\n".join(
        [f"def test_case_{i}():\n    assert True\n" for i in range(6)]
    )
    (tests_dir / "test_main.py").write_text(test_content)

    # Mock pytest so it doesn't actually run
    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("no pytest")
        detector = PhaseDetector(tmp_path)
        result = detector.detect()

    assert result.phase == ProjectPhase.FLESH_OUT


# ============================================
# Phase 3 — STABILIZE
# ============================================


def test_detect_phase3_with_ci(tmp_path):
    """Phase advances to STABILIZE with CI and 50+ tests."""
    # Phase 1+2 prerequisites
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "decisions.md").write_text("# Dec")
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(4):
        (pkg / f"mod{i}.py").write_text(
            f"def func{i}(x: int) -> str:\n    return str(x)\n"
        )

    # 50+ tests
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_content = "\n".join(
        [f"def test_case_{i}():\n    assert True\n" for i in range(55)]
    )
    (tests_dir / "test_all.py").write_text(test_content)

    # CI + Changelog
    gh = tmp_path / ".github" / "workflows"
    gh.mkdir(parents=True)
    (gh / "ci.yml").write_text("name: CI")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n## [1.0.0]")

    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("no pytest/git")
        detector = PhaseDetector(tmp_path)
        result = detector.detect()

    assert result.phase == ProjectPhase.STABILIZE


# ============================================
# Phase 4 — DEPLOY
# ============================================


def test_detect_phase4_with_monitoring(tmp_path):
    """Phase advances to DEPLOY with monitoring and release tags."""
    # All prerequisites
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "ADR").mkdir()
    (tmp_path / "ADR" / "001.md").write_text("# ADR")
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(4):
        (pkg / f"mod{i}.py").write_text(
            f"def func{i}(x: int) -> str:\n    return str(x)\n"
        )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_content = "\n".join(
        [f"def test_case_{i}():\n    assert True\n" for i in range(55)]
    )
    (tests_dir / "test_all.py").write_text(test_content)
    gh = tmp_path / ".github" / "workflows"
    gh.mkdir(parents=True)
    (gh / "ci.yml").write_text("name: CI")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog")

    # Monitoring
    (tmp_path / "requirements.txt").write_text("sentry-sdk>=1.0\n")

    # Mock git tag to return 2 tags
    def mock_subprocess_run(cmd, **kwargs):
        if cmd[:2] == ["git", "tag"]:
            result = mock.Mock()
            result.returncode = 0
            result.stdout = "v1.0.0\nv1.1.0\n"
            return result
        raise FileNotFoundError("no pytest")

    with mock.patch("subprocess.run", side_effect=mock_subprocess_run):
        detector = PhaseDetector(tmp_path)
        result = detector.detect()

    assert result.phase == ProjectPhase.DEPLOY
    assert result.missing_for_next == []


# ============================================
# Manual override
# ============================================


def test_manual_override_via_methodology_yaml(tmp_path):
    """Methodology.yaml current_phase overrides detection."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    config = {"methodology": {"current_phase": 2}}
    (vr / "methodology.yaml").write_text(yaml.dump(config))

    detector = PhaseDetector(tmp_path)
    result = detector.detect()
    assert result.phase == ProjectPhase.FLESH_OUT
    assert result.is_override


def test_auto_override_means_no_override(tmp_path):
    """current_phase: auto means auto-detect."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    config = {"methodology": {"current_phase": "auto"}}
    (vr / "methodology.yaml").write_text(yaml.dump(config))

    detector = PhaseDetector(tmp_path)
    result = detector.detect()
    assert not result.is_override
    assert result.phase == ProjectPhase.DECIDE


# ============================================
# Signal collection details
# ============================================


def test_detect_adr_various_locations(tmp_path):
    """ADR detected in multiple directory names."""
    # Test a subset that doesn't collide on case-insensitive FS
    for i, adr_name in enumerate(["ADR", "docs/adr", "docs/decisions"]):
        test_dir = tmp_path / f"project_{i}"
        test_dir.mkdir()
        adr_path = test_dir / adr_name
        adr_path.mkdir(parents=True)
        (adr_path / "001.md").write_text("# ADR")

        detector = PhaseDetector(test_dir)
        signals = detector.collect_signals()
        assert signals.has_adr, f"Failed for {adr_name}"


def test_detect_ci_various_providers(tmp_path):
    """CI detected for GitHub, GitLab, CircleCI, Jenkins."""
    # GitHub
    gh = tmp_path / "gh_test"
    gh.mkdir()
    (gh / ".github" / "workflows").mkdir(parents=True)
    assert PhaseDetector(gh).collect_signals().has_ci

    # GitLab
    gl = tmp_path / "gl_test"
    gl.mkdir()
    (gl / ".gitlab-ci.yml").write_text("stages:")
    assert PhaseDetector(gl).collect_signals().has_ci

    # Jenkins
    jk = tmp_path / "jk_test"
    jk.mkdir()
    (jk / "Jenkinsfile").write_text("pipeline {}")
    assert PhaseDetector(jk).collect_signals().has_ci


def test_detect_docker(tmp_path):
    """Docker detected from Dockerfile or docker-compose."""
    d1 = tmp_path / "d1"
    d1.mkdir()
    (d1 / "Dockerfile").write_text("FROM python:3.12")
    assert PhaseDetector(d1).collect_signals().has_docker

    d2 = tmp_path / "d2"
    d2.mkdir()
    (d2 / "docker-compose.yml").write_text("version: '3'")
    assert PhaseDetector(d2).collect_signals().has_docker


def test_detect_monitoring_from_requirements(tmp_path):
    """Monitoring detected from requirements.txt patterns."""
    (tmp_path / "requirements.txt").write_text("datadog\nflask\n")
    assert PhaseDetector(tmp_path).collect_signals().has_monitoring


def test_detect_monitoring_from_pyproject(tmp_path):
    """Monitoring detected from pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["prometheus-client"]\n'
    )
    assert PhaseDetector(tmp_path).collect_signals().has_monitoring


def test_integration_tests_by_directory(tmp_path):
    """Integration tests detected via directory name."""
    tests = tmp_path / "tests" / "integration"
    tests.mkdir(parents=True)
    (tests / "test_api.py").write_text("def test_api(): pass\n")
    assert PhaseDetector(tmp_path).collect_signals().has_integration_tests


def test_contracts_need_three_files(tmp_path):
    """Contracts require typed functions in at least 3 files."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("def f(x: int) -> str:\n    return ''\n")
    (pkg / "b.py").write_text("def g() -> None:\n    pass\n")
    # Only 2 files — should be False
    assert not PhaseDetector(tmp_path).collect_signals().has_contracts

    (pkg / "c.py").write_text("def h(x: float) -> int:\n    return 0\n")
    # Now 3 — should be True
    assert PhaseDetector(tmp_path).collect_signals().has_contracts


# ============================================
# missing_for_next
# ============================================


def test_missing_for_next_at_deploy(tmp_path):
    """No missing items when at DEPLOY phase."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    config = {"methodology": {"current_phase": 4}}
    (vr / "methodology.yaml").write_text(yaml.dump(config))

    detector = PhaseDetector(tmp_path)
    result = detector.detect()
    assert result.missing_for_next == []


def test_missing_for_next_at_decide(tmp_path):
    """DECIDE phase lists what's needed for SKELETON."""
    detector = PhaseDetector(tmp_path)
    result = detector.detect()
    assert "has_readme" in result.missing_for_next
    assert "has_contracts" in result.missing_for_next


# ============================================
# init_methodology
# ============================================


def test_init_methodology_creates_files(tmp_path):
    """--init-methodology creates methodology.yaml, ADR/, ROADMAP.md."""
    from vibesrails.cli_setup import init_methodology

    assert init_methodology(tmp_path)

    assert (tmp_path / ".vibesrails" / "methodology.yaml").exists()
    assert (tmp_path / "ADR" / "001-template.md").exists()
    assert (tmp_path / "ROADMAP.md").exists()

    # Validate methodology.yaml is valid YAML
    content = yaml.safe_load(
        (tmp_path / ".vibesrails" / "methodology.yaml").read_text()
    )
    assert "methodology" in content
    assert content["methodology"]["current_phase"] == "auto"


def test_init_methodology_no_overwrite(tmp_path):
    """--init-methodology does not overwrite existing files."""
    # Create existing files
    (tmp_path / ".vibesrails").mkdir()
    (tmp_path / ".vibesrails" / "methodology.yaml").write_text("custom: true")
    (tmp_path / "ADR").mkdir()
    (tmp_path / "ROADMAP.md").write_text("# My Roadmap")

    from vibesrails.cli_setup import init_methodology

    result = init_methodology(tmp_path)
    assert not result  # Nothing to create

    # Verify originals unchanged
    assert (tmp_path / ".vibesrails" / "methodology.yaml").read_text() == "custom: true"
    assert (tmp_path / "ROADMAP.md").read_text() == "# My Roadmap"


# ============================================
# Preflight integration
# ============================================


def test_preflight_shows_phase(tmp_path):
    """check_project_phase returns phase info."""
    from vibesrails.preflight import check_project_phase

    results = check_project_phase(tmp_path)
    assert len(results) >= 1
    assert results[0].name == "Project phase"
    assert "DECIDE" in results[0].message
