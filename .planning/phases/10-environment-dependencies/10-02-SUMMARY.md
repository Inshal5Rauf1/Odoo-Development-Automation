---
phase: 10-environment-dependencies
plan: 02
subsystem: search/auth
tags: [wizard, auth, cli, ux]
dependency_graph:
  requires: [get_github_token from search/index.py]
  provides: [check_github_auth, AuthStatus, format_auth_guidance, --no-wizard CLI flag]
  affects: [cli.py build-index, cli.py search-modules, cli.py extend-module]
tech_stack:
  added: []
  patterns: [frozen dataclass, subprocess diagnostics, shared CLI helper]
key_files:
  created:
    - python/src/odoo_gen_utils/search/wizard.py
    - python/tests/test_wizard.py
  modified:
    - python/src/odoo_gen_utils/search/__init__.py
    - python/src/odoo_gen_utils/cli.py
    - python/tests/test_cli_build_index.py
decisions:
  - "Wizard outputs to stderr (err=True) so stdout remains clean for piping"
  - "extend-module gets auth check before cloning (was missing pre-existing)"
  - "format_auth_guidance returns static strings based on AuthStatus fields, not the guidance field"
metrics:
  duration_seconds: 301
  completed: "2026-03-03T09:20:27Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 9
  tests_total: 254
  files_created: 2
  files_modified: 3
---

# Phase 10 Plan 02: GitHub Auth Setup Wizard Summary

GitHub auth diagnostic wizard with check_github_auth() that auto-detects gh CLI install state, auth status, and env token presence, providing actionable remediation messages on CLI auth failures.

## What Was Built

### Task 1: GitHub auth setup wizard module (TDD)

Created `python/src/odoo_gen_utils/search/wizard.py` with:

- **AuthStatus** frozen dataclass: `gh_installed`, `gh_authenticated`, `token_source` ("env"/"gh_cli"/None), `guidance` (human-readable message)
- **check_github_auth()**: Checks GITHUB_TOKEN env var first (fast path), then shells out to `gh auth status` with 10s timeout. Handles FileNotFoundError (gh not installed), TimeoutExpired, non-zero returncode (not authenticated), and success.
- **format_auth_guidance()**: Converts AuthStatus into actionable multi-line strings with install URL or login command.

8 unit tests covering all auth states:
- `test_gh_not_installed` -- FileNotFoundError path
- `test_gh_not_authenticated` -- returncode=1 path
- `test_gh_authenticated` -- returncode=0 path
- `test_env_token_takes_precedence` -- GITHUB_TOKEN set, subprocess NOT called
- `test_timeout_handled` -- TimeoutExpired does not crash
- `test_format_guidance_not_installed` -- contains install URL
- `test_format_guidance_not_authenticated` -- contains "gh auth login"
- `test_format_guidance_authenticated` -- contains "OK"

Commit: 557c234

### Task 2: Integrate wizard into CLI commands with --no-wizard flag

Updated `python/src/odoo_gen_utils/cli.py`:

- Added `_handle_auth_failure(no_wizard: bool)` shared helper
- Added `--no-wizard` flag to `build-index`, `search-modules`, and `extend-module`
- Auth failure default: wizard diagnosis with actionable guidance to stderr
- Auth failure `--no-wizard`: minimal "GitHub authentication required" message
- Added auth pre-check to `extend-module` (was missing)
- Updated existing `test_no_token_exits_code_1` for new wizard output
- Added `test_no_token_no_wizard_exits_code_1` for --no-wizard path

Commit: e4b1bf9

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Click 8.3.1 CliRunner does not support mix_stderr parameter**
- **Found during:** Task 2
- **Issue:** Click 8.3.1 removed `mix_stderr` from CliRunner (it was a Click 7 feature). Test used `CliRunner(mix_stderr=False)` which raised TypeError.
- **Fix:** Used default `CliRunner()` which mixes stderr into `result.output` in Click 8+, asserting on `result.output` instead of `result.stderr`.
- **Files modified:** python/tests/test_cli_build_index.py
- **Commit:** e4b1bf9

## Verification Results

1. `uv run pytest tests/test_wizard.py -v` -- 8/8 passed
2. `uv run pytest tests/ -x -q` -- 254 passed, 9 skipped, 0 failures
3. `odoo-gen-utils build-index --help | grep no-wizard` -- flag visible
4. `odoo-gen-utils search-modules --help | grep no-wizard` -- flag visible
5. `odoo-gen-utils extend-module --help | grep no-wizard` -- flag visible

## Key Files

| File | Purpose |
|------|---------|
| `python/src/odoo_gen_utils/search/wizard.py` | AuthStatus dataclass, check_github_auth(), format_auth_guidance() |
| `python/src/odoo_gen_utils/cli.py` | _handle_auth_failure() helper, --no-wizard on 3 commands |
| `python/tests/test_wizard.py` | 8 unit tests for wizard module |
| `python/tests/test_cli_build_index.py` | Updated + new tests for wizard CLI integration |
| `python/src/odoo_gen_utils/search/__init__.py` | Exports AuthStatus, check_github_auth, format_auth_guidance |

## Self-Check: PASSED

- wizard.py: FOUND
- test_wizard.py: FOUND
- 10-02-SUMMARY.md: FOUND
- Commit 557c234: FOUND
- Commit e4b1bf9: FOUND
