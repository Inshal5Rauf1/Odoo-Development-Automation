---
phase: 14-cleanup-debug-the-tech-debt
plan: 01
subsystem: auto-fix
tags: [auto-fix, docker, pylint, cli, wiring]
dependency_graph:
  requires: []
  provides: [run_docker_fix_loop, docker-fix-dispatch, w0611-handling]
  affects: [cli-validate, auto-fix-pipeline]
tech_stack:
  added: []
  patterns: [dispatch-dict, keyword-matching, immutable-read-transform-write]
key_files:
  created: []
  modified:
    - python/src/odoo_gen_utils/auto_fix.py
    - python/src/odoo_gen_utils/cli.py
    - python/tests/test_auto_fix.py
decisions:
  - run_docker_fix_loop handles both Docker pattern dispatch and unused-import keyword detection
  - W0611 handling in run_pylint_fix_loop processes unused-import files before standard fixable codes
metrics:
  duration: 3min
  completed: "2026-03-04T00:37:00Z"
---

# Phase 14 Plan 01: Wire Orphaned Auto-Fix Functions Summary

run_docker_fix_loop dispatcher wired into CLI validate --auto-fix; fix_unused_imports called from both Docker and pylint paths for W0611

## What Was Done

### Task 1: Create run_docker_fix_loop and wire fix_unused_imports into pylint loop
- Created `run_docker_fix_loop(module_path, error_output)` in `auto_fix.py`
- Function calls `identify_docker_fix()` to detect pattern, dispatches to `fix_missing_mail_thread` via dict
- Also detects unused-import keywords in error output and dispatches to `fix_unused_imports`
- Extended `run_pylint_fix_loop` to handle W0611 violations by calling `fix_unused_imports` on affected files
- Added proper logging throughout
- **Commit:** `4939a54`

### Task 2: Wire run_docker_fix_loop into CLI validate command
- Added `run_docker_fix_loop` to import statement in `cli.py`
- After Docker validation failure with `--auto-fix`, calls `run_docker_fix_loop` and retries validation once if fix applied
- Added import verification test
- **Commit:** `2499ab8`

## Test Results

- 43 tests in test_auto_fix.py (37 existing + 6 new): all pass
- 317 tests in full suite: all pass (9 skipped, 0 failures)
- New tests: 4 for run_docker_fix_loop, 1 for pylint W0611 handling, 1 import verification

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **run_docker_fix_loop handles unused-import keywords directly** -- Since unused-import patterns (W0611) can appear in Docker output but aren't in `_DOCKER_PATTERN_KEYWORDS`, added separate keyword detection before the standard `identify_docker_fix` dispatch.
2. **W0611 processing order in pylint loop** -- W0611 violations are extracted and processed via `fix_unused_imports` before standard fixable codes, ensuring clean separation of concerns.

## Verification

- Import chain verified: `from odoo_gen_utils.auto_fix import run_docker_fix_loop` + `from odoo_gen_utils.cli import validate` both succeed
- All 3 orphaned functions now have runtime callers: `fix_missing_mail_thread` (via run_docker_fix_loop), `fix_unused_imports` (via both loops), `identify_docker_fix` (via run_docker_fix_loop)
