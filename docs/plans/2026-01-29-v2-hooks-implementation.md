# V2 Hooks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add proactive security hooks (PreToolUse scan, PostToolUse verify) and inter-session communication (queue + mobile inbox) to vibesrails.

**Architecture:** Four components: (1) PreToolUse hook that scans code before write; (2) PostToolUse hook that verifies after write; (3) queue system via .claude/queue.jsonl; (4) mobile inbox via .claude/inbox.md.

**Tech Stack:** Python 3.10+, Claude Code hooks API (JSON stdin, exit codes), vibesrails scanner

---

## Task 1: PreToolUse Hook - Scan Before Write

- Create: vibesrails/hooks/__init__.py, vibesrails/hooks/pre_tool_use.py
- Create: tests/test_hooks/__init__.py, tests/test_hooks/test_pre_tool_use.py
- Modify: all hooks.json (add PreToolUse entry)
- TDD: 7 tests, then implement, then update hooks.json, then commit

## Task 2: PostToolUse Hook - Verify After Write

- Create: vibesrails/hooks/post_tool_use.py, tests/test_hooks/test_post_tool_use.py
- Modify: all hooks.json (add PostToolUse verify entry)
- Warn-only (exit 0 always). TDD: 4 tests.

## Task 3: Inter-Session Queue (.claude/queue.jsonl)

- Create: vibesrails/hooks/queue_processor.py, tests/test_hooks/test_queue.py
- Modify: vibesrails/cli.py (add --queue flag), all hooks.json
- TDD: 4 tests. Functions: add_task, get_pending_tasks, mark_done, format_pending_summary.

## Task 4: Mobile Inbox (.claude/inbox.md)

- Create: vibesrails/hooks/inbox.py, tests/test_hooks/test_inbox.py
- Modify: vibesrails/cli.py (add --inbox flag), all hooks.json
- TDD: 5 tests. Functions: check_inbox, clear_inbox, create_inbox.

## Task 5: Sync All Installer Templates + Final Verification

- Copy canonical hooks.json to all installers
- Run full test suite, vibesrails self-scan, ruff
- Final commit
