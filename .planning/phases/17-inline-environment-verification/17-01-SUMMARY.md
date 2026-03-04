---
phase: 17-inline-environment-verification
plan: "01"
subsystem: verification
tags: [verifier, renderer, mcp, odoo-client, tdd]
dependency_graph:
  requires:
    - "python/src/odoo_gen_utils/mcp/odoo_client.py (OdooClient.search_read)"
    - "python/src/odoo_gen_utils/renderer.py (render_module, pre-existing)"
  provides:
    - "python/src/odoo_gen_utils/verifier.py (EnvironmentVerifier, VerificationWarning, build_verifier_from_env)"
    - "render_module() returns tuple[list[Path], list[VerificationWarning]]"
  affects:
    - "python/src/odoo_gen_utils/cli.py (render-module command now prints WARN lines to stderr)"
    - "python/tests/test_renderer.py (all call sites updated to unpack tuple)"
    - "python/tests/test_golden_path.py (render_module call site unaffected -- unassigned)"
tech_stack:
  added: []
  patterns:
    - "Constructor-injection for OdooClient mock (same as test_mcp_server.py)"
    - "TYPE_CHECKING guard to avoid circular import in verifier.py -> renderer.py chain"
    - "Lazy import of OdooClient inside build_verifier_from_env() to keep cold import fast"
    - "Graceful degradation: outer try/except per verify method returns [] on any error"
    - "Deduplication set in _check_relational_comodels prevents duplicate OdooClient queries"
key_files:
  created:
    - "python/src/odoo_gen_utils/verifier.py"
    - "python/tests/test_verifier.py"
  modified:
    - "python/src/odoo_gen_utils/renderer.py"
    - "python/src/odoo_gen_utils/cli.py"
    - "python/tests/test_renderer.py"
decisions:
  - "Lazy OdooClient import inside build_verifier_from_env: avoids ModuleNotFoundError when mcp subpackage is not installed and keeps module import fast"
  - "TYPE_CHECKING guard in renderer.py: prevents circular import since verifier imports from mcp while renderer imports from verifier"
  - "Test mock path is odoo_gen_utils.mcp.odoo_client.OdooClient not odoo_gen_utils.verifier.OdooClient because of lazy import -- documented in test"
  - "verifier.py line 331: slightly over 220-line guideline due to comprehensive docstrings; functionality is within bounds"
metrics:
  duration: "4min"
  completed: "2026-03-04"
  tasks: 2
  files: 5
---

# Phase 17 Plan 01: Inline Environment Verification Summary

Implemented EnvironmentVerifier with TDD (RED then GREEN), wired into render_module(), and updated all callers -- completing MCP-03 and MCP-04 inline verification requirements.

## What Was Built

**`python/src/odoo_gen_utils/verifier.py`** — New module implementing:
- `VerificationWarning` frozen dataclass with `check_type`, `subject`, `message`, `suggestion` fields
- `EnvironmentVerifier` class with `verify_model_spec()` and `verify_view_spec()` methods
- `_check_inherit()`: verifies `_inherit` base models via `ir.model`, skips `mail.thread`/`mail.activity.mixin`
- `_check_relational_comodels()`: verifies `comodel_name` targets via `ir.model`, deduplicates queries
- `_check_field_overrides()`: MCP-03 criterion #3 -- detects missing fields and ttype mismatches for override fields via `ir.model.fields`
- `_check_view_fields()`: verifies view field names via `ir.model.fields` (MCP-04)
- `_check_view_target()`: verifies inherited view targets via `ir.ui.view`
- `build_verifier_from_env()`: factory that reads `ODOO_URL` env var; returns no-op verifier when absent

**`python/src/odoo_gen_utils/renderer.py`** — Updated:
- `render_module()` new signature adds `verifier: EnvironmentVerifier | None = None`
- Return type changed to `tuple[list[Path], list[VerificationWarning]]`
- Verifier called per-model for model spec and view spec checks
- Fully backward-compatible: callers without verifier get `(files, [])` tuple

**`python/src/odoo_gen_utils/cli.py`** — Updated `render_module_cmd`:
- Calls `build_verifier_from_env()` to construct verifier from environment
- Unpacks `files, warnings = render_module(...)`
- Prints `WARN [check_type] subject: message` + `Suggestion: ...` lines to stderr

**`python/tests/test_verifier.py`** — New test file with 31 tests across 8 classes:
- `TestVerifierNoClient` (3 tests): no-op behavior
- `TestModelInheritCheck` (6 tests): inherit verification and mixin skip
- `TestRelationalComodelCheck` (6 tests): comodel checks and deduplication
- `TestFieldOverrideCheck` (3 tests): MCP-03 criterion #3
- `TestViewFieldCheck` (5 tests): view field verification and graceful degradation
- `TestViewInheritTarget` (3 tests): inherited view target verification
- `TestIntegrationWithRenderModule` (3 tests): end-to-end tuple return
- `TestBuildVerifierFromEnv` (2 tests): factory function

**`python/tests/test_renderer.py`** — 30 render_module call sites updated from `files = render_module(...)` to `files, _ = render_module(...)`.

## Decisions Made

1. **Lazy OdooClient import** inside `build_verifier_from_env()` avoids import errors when `mcp` subpackage is absent and keeps cold module import fast.

2. **TYPE_CHECKING guard** in `renderer.py` for `EnvironmentVerifier`/`VerificationWarning` imports prevents circular import (verifier imports mcp.odoo_client; renderer imports verifier).

3. **Patch path for test** is `odoo_gen_utils.mcp.odoo_client.OdooClient` not `odoo_gen_utils.verifier.OdooClient` because of the lazy import. Documented in test class.

4. **verifier.py 331 lines** -- slightly over the 220-line guideline due to comprehensive docstrings matching project standards. Functionality split across 6 private methods is clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TestViewInheritTarget.test_existing_target_returns_no_warnings had incorrect mock setup**
- **Found during:** Task 2 GREEN verification run
- **Issue:** Test set `mock_client.search_read.return_value = [{"name": "some.view"}]` globally, but the first `search_read` call in `verify_view_spec` is for `ir.model.fields` (not `ir.ui.view`). The mock returned `[{"name": "some.view"}]` for the fields call, making "name" look absent, causing a spurious `view_field` warning.
- **Fix:** Changed to `side_effect` list: first call returns field data `[{"name": "name"}]`, second call returns view data `[{"name": "some.view"}]`.
- **Files modified:** `python/tests/test_verifier.py`
- **Commit:** 3cdde2e

**2. [Rule 1 - Bug] TestBuildVerifierFromEnv patch path wrong**
- **Found during:** Task 2 GREEN verification run
- **Issue:** Test patched `odoo_gen_utils.verifier.OdooClient` but `OdooClient` is imported lazily inside `build_verifier_from_env()` (not at module level), so the attribute doesn't exist in the verifier module namespace.
- **Fix:** Changed patch path to `odoo_gen_utils.mcp.odoo_client.OdooClient`.
- **Files modified:** `python/tests/test_verifier.py`
- **Commit:** 3cdde2e

## Test Results

```
381 passed, 21 deselected, 5 warnings in 3.14s
(excluding: docker, e2e, e2e_slow)
```

- `test_verifier.py`: 31 passed (all 8 test classes green)
- `test_renderer.py`: all existing tests green (no regressions)
- `test_golden_path.py`: docker-marked, excluded from unit run

## Self-Check

All files verified to exist:
- python/src/odoo_gen_utils/verifier.py -- FOUND
- python/tests/test_verifier.py -- FOUND
- python/src/odoo_gen_utils/renderer.py -- MODIFIED
- python/src/odoo_gen_utils/cli.py -- MODIFIED
- python/tests/test_renderer.py -- MODIFIED

Commits verified:
- 1c62d31: test(17-01): add failing unit tests for EnvironmentVerifier (RED)
- 3cdde2e: feat(17-01): implement EnvironmentVerifier, wire into render_module (GREEN)
