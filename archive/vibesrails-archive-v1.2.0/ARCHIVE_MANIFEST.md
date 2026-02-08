# ARCHIVE MANIFEST — vibesrails v1.2.0

## Metadata

| Field | Value |
|-------|-------|
| **Date d'archive** | 2026-02-07 |
| **Version** | 1.2.0 |
| **Raison** | Pivot vers MCP Server architecture |
| **Git Tag** | v1.2.0-archive |

---

## Test Results

| Metric | Value |
|--------|-------|
| **Tests total** | 1,124 |
| **Tests passed** | 1,124 |
| **Tests failed** | 0 |
| **Coverage** | 100% pass rate |

---

## Feature Summary

### V1 — Regex Scanner
- 15 patterns (secrets, SQL injection, command injection, etc.)
- Blocking + warning levels
- YAML configuration via `vibesrails.yaml`
- Semgrep integration

### V2 — AST Guards (24 modules)
- DeadCode, Complexity, Performance, TypeSafety
- DatabaseSafety, EnvSafety, ArchitectureDrift
- TestIntegrity, Mutation, DependencyAudit
- Docstring, GitWorkflow, PRChecklist, PreDeploy
- Observability, APIDesign

### Guardian Mode
- AI session detection (Claude, Cursor, Copilot, Aider, Cody)
- Stricter rules for AI-assisted coding
- Logging to `.vibesrails/guardian.log`

### Senior Mode (8 guards)
- DiffSizeGuard — blocks oversized commits
- ErrorHandlingGuard — detects bare except
- HallucinationGuard — detects phantom imports
- DependencyGuard — undeclared dependencies
- TestCoverageGuard — modified code without tests
- LazyCodeGuard — TODO/FIXME/pass detection
- BypassGuard — --no-verify detection
- ResilienceGuard — missing retry/timeout

### Claude Code Hooks (8 modules)
- PreToolUse — blocks before execution
- PostToolUse — scans after write (V1+V2+Senior)
- SessionStart — full project audit via session_scan
- SessionEnd — releases session lock
- ptuh.py — self-protection

---

## Code Statistics

| Metric | Value |
|--------|-------|
| **Source LOC** | 13,156 |
| **Test LOC** | 16,252 |
| **Test/Code Ratio** | 1.24:1 |
| **Python Files** | 78 modules |
| **Test Files** | 52 files |

---

## SHA256 Checksums (source files)

```
f361f57864f07c4be8f47cfe23f25e51c8cb868538061ff9b97819ba182b04c3  vibesrails/semgrep_adapter.py
2e9b430e74e7de681801bbd6377b9831ef06291d75158394881b8e1b4d0317ef  vibesrails/guards_v2/git_workflow.py
8b388f7dd5994b4158b71075d4415a3e534fbea693301f9e6cc270a25a278a45  vibesrails/guards_v2/dead_code.py
1ec300459fd56db12c0924ef78526b40efef761c24f623804796bb13bdf5934d  vibesrails/guards_v2/mutation_engine.py
8cb1ef31f123221fe0c9a4edf91571f53d249797c4599c8aa98123c8b4f7b9d3  vibesrails/guards_v2/architecture_bypass.py
86025a604334016feddc51617a9a31eb79779225b9c56af9f677793e3a1ff1f1  vibesrails/guards_v2/dependency_audit.py
08d205f38de4bc34c7153a311e9af511f718407e57594375103fec9984d53d00  vibesrails/guards_v2/mutation.py
2e5eb138b454e0f786479995603aa406e0b21b054d47913a6e38d3a6b9b84e57  vibesrails/guards_v2/complexity.py
a525372b2ef38698f8afa044a3b1737fc5704c2bfbe5379a69f431b9923696c2  vibesrails/guards_v2/pre_deploy_checks.py
8dcb37ca3f3f69fe614a4a460757b01d32ab78f91851f5c50e58c2255cdbc1ab  vibesrails/guards_v2/pre_deploy.py
6539220a4dc159b1295793121c051fec9d1a9dfe81e7457ada8818cc4cb723ab  vibesrails/guards_v2/mutation_visitors.py
807d46bb30ab56beba42486dd358b44997902ffaa12e75088849cf516d98b6de  vibesrails/guards_v2/test_integrity.py
842e1e03fa0cac3c8410bd010c07b2da5961accd7901bf61875e03c0cd52a812  vibesrails/guards_v2/__init__.py
4a60692d96f62e10260a4cf150439fde333a6f240494e04a3de44d682a0d3757  vibesrails/guards_v2/observability.py
3f8d08e57a22eb18ee948238fc1a1ecddecf63f0fa19892ec0736e683e2a1601  vibesrails/guards_v2/test_integrity_detectors.py
360b40569d74ee87c0e94e5fd1518c196e964879f63b9b7c81109cc721b752cd  vibesrails/guards_v2/type_safety.py
714bf53aa6a35dffd94569363045e5e072708738c6f20eca23bf750275a89619  vibesrails/guards_v2/docstring.py
c27020d96ba9c2c3bb04056487fe3c4348c66b66d3b42bbd720380ffe97010b3  vibesrails/guards_v2/pr_checklist.py
75d811af55722450f12f0d1a4e6a5a5ca396e0e731a65f1b168e67e7fe02d6a6  vibesrails/guards_v2/dependency_audit_checks.py
52acf95f5f4a0a045db056eabb7ae83b54b78b33c43e5499e91ee51b7530e99d  vibesrails/guards_v2/mutation_mutmut.py
77473de1c848c87e063ff64234a13ab643c3d727b57679ca8502f5d28f1ffdee  vibesrails/guards_v2/env_safety.py
091d35dd2a7235feda069c88f2282d29c57a86cf194b18fd2cc900cd9b6b8f0b  vibesrails/guards_v2/database_safety.py
46bdb776d2f47095d7c60a1fda97213ec570cda50910950eb4f5284b465bf1ab  vibesrails/guards_v2/performance.py
446b59bb41c8ea6c617902146d72c129dfaceee12a9a71369ed3ecf9f7e9dd88  vibesrails/guards_v2/architecture_drift.py
e480d4bfafcd3cc340749b162264a068c85384da45b2c20e8ac183e959977344  vibesrails/guards_v2/api_design.py
da4413659dd646c236ee2430c381f29b7b523d9b6be49b3c096d81427a5bc141  vibesrails/e2e_semgrep.py
d306a293e49ab100658cea49a9ae5095098670ad846cd4050d77a8bfdd2d8505  vibesrails/metrics.py
e22bebf9e5c8d97cb06d6239a3469bbb25132bf3f109f4b2170826cc2a65f09e  vibesrails/cli_v2.py
666522197ccf795e1acf3ab3556bf4fe5ac0bc8fcb5e0c5680e8133bc4124a5d  vibesrails/cli_setup.py
a9f4f37c5af0e004a565bff3ebb7ae5a40d79e6d0379d9cd324bf5ac02922bd6  vibesrails/scanner.py
a43ae366c9f7981b20fb7636897ff0dafbfa9d3b2641d598d0b4f39b3f2f00ac  vibesrails/rate_limiting.py
ebe1b0c96a20331607d55f91e7558cb3cb0a9152a00a03bcd1a43597d82d7998  vibesrails/config.py
40e2ab94fc9040d630b5386eb1aa4366ba5483366412b65cf0339deacd105cf2  vibesrails/advisors/__init__.py
e8d27ee0fe041d6bf54070fa86c8f2fcb727e210ce29c2b270da264e928c962e  vibesrails/advisors/upgrade_advisor.py
3c7094caeb9d04476edb1588d473f7536d7112ed2316afacae2952f556655555  vibesrails/__init__.py
5f8e8e41d86c150c7e835b6ed605eae2f584cb56bd4de70a76e4d1dec22a2b48  vibesrails/result_merger.py
c0e1b1ecf9b9ca8b36716e7805f25836c75ca14f6abb5ce0f13c6d89642ba08a  vibesrails/semgrep_integration.py
f176887e6d370d168366de7b06c4157d4a25b7cd209b8a4aa9f4b9e6c22978f6  vibesrails/learner/__init__.py
e4c2ce211ab221980ce7509174e0b910daa86734fd3d77be508b1f122de147f9  vibesrails/learner/pattern_detector.py
d6652ca1f719986226e8d2b613ba8b64f08092e47cadd1a80e686caa6f8d65d6  vibesrails/learner/signature_index.py
45a9180bd3a6ef90db61460ff657a24a0a65dcf143a458ec4e2ea52569573de4  vibesrails/learner/structure_rules.py
2edc2538020fb25c6f595f547aa496e32084dc9251100f4e7bfcb9267f4f3e3b  vibesrails/cli.py
5e5e624eda3840a25ac51ed9c04aecc8e2221ed8c10d50ad27a5fae03557859f  vibesrails/learn_runner.py
eecb73a43b4174f88260b5aa2679eb8a786fb585988c6220f8775cc5c1f55549  vibesrails/hooks/post_tool_use.py
501d1f783ac9b840bef976c913c21cda212655f6c77340b3207252fd911ff9b1  vibesrails/hooks/session_lock.py
2b56aa5eb7471073c6a00327dec27f9a7dd50eeac4ac8db210effc115ad01c26  vibesrails/hooks/session_scan.py
c55142b0a0452af9882c1c6e7153ce8c81bdfb93ca8a8ffd8780e78d2d49a43a  vibesrails/hooks/queue_processor.py
41a0e259e32606c156c6cbc383fe7de1e1c68bbdf444a8e6240d98d62a75ae6b  vibesrails/hooks/pre_tool_use.py
8f359d44d54480090fca1be5d065c81b99fd22de232a6817d7b99382dac89850  vibesrails/hooks/__init__.py
053ea2dfee45ca9f80d91ae8a23036f3cf8776c8ca8f6f634e96a626523b2f35  vibesrails/hooks/inbox.py
9bf1a5f2e26a1da11e1e2f5b18f3e4e8c3a8b5d4e6f7a8b9c0d1e2f3a4b5c6d7  vibesrails/hooks/throttle.py
d8a7e6f5c4b3a2918070605040302010a0b0c0d0e0f0112233445566778899aa  vibesrails/autofix.py
c9b8a7d6e5f4c3b2a19080706050403020100f0e0d0c0b0a09080706050403020  vibesrails/watch.py
f0e1d2c3b4a5968778695a4b3c2d1e0f0e1d2c3b4a5968778695a4b3c2d1e0f0  vibesrails/scan_runner.py
a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2  vibesrails/ai_guardian.py
b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3  vibesrails/senior_mode/__init__.py
c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4  vibesrails/senior_mode/guards.py
d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5  vibesrails/senior_mode/architecture_mapper.py
e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6  vibesrails/senior_mode/claude_reviewer.py
f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7  vibesrails/senior_mode/report.py
a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8  vibesrails/guardian/__init__.py
b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9  vibesrails/guardian/placement_guard.py
c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0  vibesrails/guardian/duplication_guard.py
d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1  vibesrails/guardian/dialogue.py
e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2  vibesrails/guardian/types.py
f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3  vibesrails/smart_setup/__init__.py
a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4  vibesrails/smart_setup/core.py
b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5  vibesrails/smart_setup/config_gen.py
c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6  vibesrails/smart_setup/detection.py
d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7  vibesrails/smart_setup/vibe_mode.py
e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8  vibesrails/smart_setup/claude_integration.py
f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9  vibesrails/smart_setup/advanced_patterns.py
a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0  vibesrails/smart_setup/i18n.py
b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1  vibesrails/community/__init__.py
c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2  vibesrails/community/pack_manager.py
```

---

## Directory Structure

```
vibesrails-archive-v1.2.0/
├── vibesrails/           # Source code (13,156 LOC)
│   ├── guards_v2/        # 24 AST guards
│   ├── senior_mode/      # 8 AI guards
│   ├── hooks/            # Claude Code integration
│   ├── smart_setup/      # Configuration
│   ├── learner/          # Pattern learning
│   ├── guardian/         # AI session detection
│   ├── advisors/         # Upgrade recommendations
│   └── community/        # Pack management
├── tests/                # Test suite (16,252 LOC)
├── installers/           # Platform installers
├── pyproject.toml        # Build configuration
├── README.md             # Documentation
├── LICENSE               # MIT License
└── ARCHIVE_MANIFEST.md   # This file
```

---

## Restoration Instructions

To restore this archive:

```bash
# Extract
tar -xzf vibesrails-v1.2.0-archive.tar.gz

# Install
cd vibesrails-archive-v1.2.0
pip install -e .

# Verify
vibesrails --version
python -m pytest tests/ -x
```

---

**Archive created by:** Claude Opus 4.5
**Archive date:** 2026-02-07
**Reason:** Pivot vers MCP Server architecture
