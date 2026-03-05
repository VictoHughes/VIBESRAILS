/Users/stan/Dev/vibesrails
├── adapters
│   ├── __init__.py
│   └── semgrep_adapter.py
├── core
│   ├── __init__.py
│   ├── brief_enforcer.py
│   ├── brief_enforcer_patterns.py
│   ├── config_shield.py
│   ├── drift_metrics.py
│   ├── drift_tracker.py
│   ├── guardian.py
│   ├── hallucination_deep.py
│   ├── hallucination_registry.py
│   ├── input_validator.py
│   ├── learning_bridge.py
│   ├── learning_engine.py
│   ├── learning_profile.py
│   ├── logger.py
│   ├── path_validator.py
│   ├── prompt_shield.py
│   ├── prompt_shield_patterns.py
│   ├── rate_limiter.py
│   ├── secret_patterns.py
│   └── session_tracker.py
├── docs
│   ├── plans
│   ├── METRICS.md
│   ├── PROJECT_TREE.md
│   ├── RATE_LIMITING.md
│   ├── SEMGREP_INTEGRATION.md
│   ├── SENIOR_MODE.md
│   └── VIBESRAILS_GUIDE.md
├── storage
│   ├── __init__.py
│   └── migrations.py
├── tests
│   ├── test_advisors
│   │   ├── __init__.py
│   │   └── test_upgrade_advisor.py
│   ├── test_community
│   │   ├── __init__.py
│   │   └── test_pack_manager.py
│   ├── test_context
│   │   ├── __init__.py
│   │   ├── test_adapter.py
│   │   ├── test_detector.py
│   │   ├── test_mode.py
│   │   └── test_scorer.py
│   ├── test_core
│   │   ├── __init__.py
│   │   ├── test_brief_enforcer.py
│   │   ├── test_config_shield.py
│   │   ├── test_drift_tracker.py
│   │   ├── test_hallucination_deep.py
│   │   ├── test_learning_bridge.py
│   │   ├── test_learning_engine.py
│   │   ├── test_logger.py
│   │   ├── test_prompt_shield.py
│   │   ├── test_rate_limiter.py
│   │   ├── test_secret_patterns.py
│   │   └── test_session_tracker.py
│   ├── test_guards_v2
│   │   ├── __init__.py
│   │   ├── test_api_design.py
│   │   ├── test_architecture_bypass.py
│   │   ├── test_architecture_drift.py
│   │   ├── test_complexity.py
│   │   ├── test_database_safety.py
│   │   ├── test_dead_code.py
│   │   ├── test_dependency_audit.py
│   │   ├── test_dependency_audit_checks.py
│   │   ├── test_docstring.py
│   │   ├── test_env_safety.py
│   │   ├── test_git_workflow.py
│   │   ├── test_mutation.py
│   │   ├── test_mutation_engine.py
│   │   ├── test_mutation_visitors.py
│   │   ├── test_observability.py
│   │   ├── test_performance.py
│   │   ├── test_pr_checklist.py
│   │   ├── test_pre_deploy.py
│   │   ├── test_pre_deploy_checks.py
│   │   ├── test_test_integrity.py
│   │   └── test_type_safety.py
│   ├── test_hooks
│   │   ├── __init__.py
│   │   ├── test_hooks_cli_sync.py
│   │   ├── test_inbox.py
│   │   ├── test_post_tool_use.py
│   │   ├── test_pre_tool_use.py
│   │   ├── test_queue.py
│   │   └── test_scope_guard.py
│   ├── test_integration
│   │   ├── __init__.py
│   │   ├── test_e2e_realistic.py
│   │   ├── test_full_workflow.py
│   │   ├── test_learning_wiring.py
│   │   └── test_mcp_integration.py
│   ├── test_security
│   │   ├── __init__.py
│   │   ├── test_information_disclosure.py
│   │   ├── test_input_validation.py
│   │   ├── test_mcp_protocol.py
│   │   ├── test_path_traversal.py
│   │   ├── test_redos.py
│   │   ├── test_resource_exhaustion.py
│   │   ├── test_sql_injection.py
│   │   ├── test_sql_injection_deep.py
│   │   └── test_sqlite_wal.py
│   ├── test_storage
│   │   ├── __init__.py
│   │   ├── test_migrations.py
│   │   ├── test_migrations_v2.py
│   │   └── test_migrations_v3.py
│   ├── test_tools
│   │   ├── __init__.py
│   │   ├── test_check_config.py
│   │   ├── test_check_drift.py
│   │   ├── test_check_session.py
│   │   ├── test_deep_hallucination.py
│   │   ├── test_enforce_brief.py
│   │   ├── test_get_learning.py
│   │   ├── test_monitor_entropy.py
│   │   ├── test_scan_code.py
│   │   ├── test_scan_semgrep.py
│   │   ├── test_scan_senior.py
│   │   └── test_shield_prompt.py
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_assertions.py
│   ├── test_autofix.py
│   ├── test_cli_lifecycle.py
│   ├── test_cli_setup.py
│   ├── test_config.py
│   ├── test_decisions_template.py
│   ├── test_dialogue.py
│   ├── test_duplication_guard.py
│   ├── test_e2e_semgrep.py
│   ├── test_guardian.py
│   ├── test_integration_learning.py
│   ├── test_learn.py
│   ├── test_learn_command.py
│   ├── test_mcp_server.py
│   ├── test_pattern_detector.py
│   ├── test_pentest_fixes.py
│   ├── test_pentest_red_fixes.py
│   ├── test_placement_guard.py
│   ├── test_preflight.py
│   ├── test_rate_limiting.py
│   ├── test_scanner_core.py
│   ├── test_scanner_integration.py
│   ├── test_scanner_utils.py
│   ├── test_semgrep_integration.py
│   ├── test_senior_mode.py
│   ├── test_session_lock.py
│   ├── test_signature_index.py
│   ├── test_smart_setup_config.py
│   ├── test_smart_setup_detection.py
│   ├── test_smart_setup_edge.py
│   ├── test_smart_setup_integration.py
│   ├── test_structure_rules.py
│   ├── test_sync_claude.py
│   ├── test_throttle.py
│   ├── test_throttle_cli.py
│   ├── test_throttle_integration.py
│   └── test_watch.py
├── tools
│   ├── __init__.py
│   ├── check_config.py
│   ├── check_drift.py
│   ├── check_session.py
│   ├── deep_hallucination.py
│   ├── deep_hallucination_pedagogy.py
│   ├── enforce_brief.py
│   ├── get_learning.py
│   ├── monitor_entropy.py
│   ├── scan_code.py
│   ├── scan_code_pedagogy.py
│   ├── scan_semgrep.py
│   ├── scan_senior.py
│   └── shield_prompt.py
├── vibesrails
│   ├── adapters
│   │   ├── __init__.py
│   │   └── semgrep_adapter.py
│   ├── advisors
│   │   ├── __init__.py
│   │   └── upgrade_advisor.py
│   ├── claude_integration
│   │   ├── skills
│   │   │   ├── vibesrails-memo.md
│   │   │   ├── vibesrails-scan.md
│   │   │   └── vibesrails-setup.md
│   │   ├── CLAUDE.md.template
│   │   ├── hooks.json
│   │   └── rules_reminder.md
│   ├── community
│   │   ├── __init__.py
│   │   └── pack_manager.py
│   ├── config
│   │   ├── decisions.md.template
│   │   └── default.yaml
│   ├── context
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   ├── detector.py
│   │   ├── mode.py
│   │   └── scorer.py
│   ├── guardian
│   │   ├── __init__.py
│   │   ├── dialogue.py
│   │   ├── duplication_guard.py
│   │   ├── placement_guard.py
│   │   └── types.py
│   ├── guards_v2
│   │   ├── mutation
│   │   │   ├── __init__.py
│   │   │   ├── engine.py
│   │   │   ├── guard.py
│   │   │   ├── mutmut.py
│   │   │   └── visitors.py
│   │   ├── __init__.py
│   │   ├── _arch_layers.py
│   │   ├── _env_patterns.py
│   │   ├── _git_helpers.py
│   │   ├── _perf_patterns.py
│   │   ├── api_design.py
│   │   ├── architecture_bypass.py
│   │   ├── architecture_drift.py
│   │   ├── complexity.py
│   │   ├── database_safety.py
│   │   ├── dead_code.py
│   │   ├── dependency_audit.py
│   │   ├── dependency_audit_checks.py
│   │   ├── docstring.py
│   │   ├── env_safety.py
│   │   ├── git_workflow.py
│   │   ├── observability.py
│   │   ├── performance.py
│   │   ├── pr_checklist.py
│   │   ├── pre_deploy.py
│   │   ├── pre_deploy_checks.py
│   │   ├── test_integrity.py
│   │   ├── test_integrity_detectors.py
│   │   └── type_safety.py
│   ├── hooks
│   │   ├── __init__.py
│   │   ├── inbox.py
│   │   ├── post_tool_use.py
│   │   ├── pre_tool_use.py
│   │   ├── queue_processor.py
│   │   ├── session_lock.py
│   │   ├── session_scan.py
│   │   └── throttle.py
│   ├── learner
│   │   ├── __init__.py
│   │   ├── pattern_detector.py
│   │   ├── signature_index.py
│   │   └── structure_rules.py
│   ├── packs
│   │   ├── django.yaml
│   │   ├── fastapi.yaml
│   │   ├── security.yaml
│   │   └── web.yaml
│   ├── senior_mode
│   │   ├── __init__.py
│   │   ├── architecture_mapper.py
│   │   ├── claude_reviewer.py
│   │   ├── guards.py
│   │   ├── guards_analysis.py
│   │   └── report.py
│   ├── smart_setup
│   │   ├── __init__.py
│   │   ├── _vibe_patterns.py
│   │   ├── advanced_patterns.py
│   │   ├── claude_integration.py
│   │   ├── config_gen.py
│   │   ├── config_sections.py
│   │   ├── core.py
│   │   ├── detection.py
│   │   ├── i18n.py
│   │   └── vibe_mode.py
│   ├── __init__.py
│   ├── __main__.py
│   ├── ai_guardian.py
│   ├── assertions.py
│   ├── autofix.py
│   ├── cli.py
│   ├── cli_setup.py
│   ├── cli_v2.py
│   ├── config.py
│   ├── e2e_semgrep.py
│   ├── integration_learning.py
│   ├── learn.py
│   ├── learn_command.py
│   ├── learn_runner.py
│   ├── metrics.py
│   ├── preflight.py
│   ├── rate_limiting.py
│   ├── result_merger.py
│   ├── scan_runner.py
│   ├── scanner.py
│   ├── scanner_cli.py
│   ├── scanner_git.py
│   ├── scanner_types.py
│   ├── scanner_utils.py
│   ├── semgrep_adapter.py
│   ├── semgrep_integration.py
│   ├── sync_claude.py
│   ├── watch.py
│   └── yaml_safety.py
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CLAUDE.md
├── LICENSE
├── Makefile
├── README.md
├── SECURITY.md
├── claude code.command
├── mcp_server.py
├── mcp_tools.py
├── mcp_tools_ext.py
├── pyproject.toml
└── vibesrails.yaml

34 directories, 291 files
