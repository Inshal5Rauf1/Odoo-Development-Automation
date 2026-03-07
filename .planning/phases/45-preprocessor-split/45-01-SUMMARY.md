---
phase: 45-preprocessor-split
plan: 01
subsystem: infra
tags: [python, preprocessor, decorator-registry, pkgutil, refactoring]

# Dependency graph
requires: []
provides:
  - "preprocessors/ package with decorator-based registry"
  - "run_preprocessors(spec) single entry point for pipeline"
  - "@register_preprocessor(order=N) decorator for adding new preprocessors"
  - "Auto-discovery via pkgutil (no __init__.py edits needed)"
  - "11 domain files with isolated preprocessor logic"
affects: [49-document-management, 50-portal-patterns, 52-discuss-patterns, 54-pipeline-qol]

# Tech tracking
tech-stack:
  added: []
  patterns: [decorator-based-registry, pkgutil-auto-discovery, explicit-order-pipeline]

key-files:
  created:
    - python/src/odoo_gen_utils/preprocessors/_registry.py
    - python/src/odoo_gen_utils/preprocessors/__init__.py
    - python/src/odoo_gen_utils/preprocessors/relationships.py
    - python/src/odoo_gen_utils/preprocessors/validation.py
    - python/src/odoo_gen_utils/preprocessors/constraints.py
    - python/src/odoo_gen_utils/preprocessors/performance.py
    - python/src/odoo_gen_utils/preprocessors/production.py
    - python/src/odoo_gen_utils/preprocessors/security.py
    - python/src/odoo_gen_utils/preprocessors/audit.py
    - python/src/odoo_gen_utils/preprocessors/approval.py
    - python/src/odoo_gen_utils/preprocessors/notifications.py
    - python/src/odoo_gen_utils/preprocessors/webhooks.py
    - python/src/odoo_gen_utils/preprocessors/computation_chains.py
    - python/tests/test_preprocessor_registry.py
  modified: []

key-decisions:
  - "Used decorator+list registry pattern (not class-based plugins) for simplicity"
  - "Used pkgutil.iter_modules for auto-discovery (not manual import list)"
  - "validation.py NOT registered in pipeline (raises exceptions, not a transformer)"
  - "_init_override_sources extracted from renderer.py inline code into order=15 preprocessor"
  - "_resolve_comodel kept in relationships.py with validation.py importing from it (one-directional)"

patterns-established:
  - "Decorator registry: @register_preprocessor(order=N, name='x') for pipeline registration"
  - "Auto-discovery: pkgutil.iter_modules + importlib.import_module in __init__.py"
  - "Order spacing: multiples of 10 for easy future insertion"
  - "Backward-compatible re-exports: all public names available from package __init__.py"

requirements-completed: [INFR-01]

# Metrics
duration: 9min
completed: 2026-03-07
---

# Phase 45 Plan 01: Preprocessor Split Summary

**Split 1,715-line preprocessors.py monolith into 13-file package with decorator-based registry, auto-discovery via pkgutil, and 11 ordered pipeline stages**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-07T11:10:07Z
- **Completed:** 2026-03-07T11:19:52Z
- **Tasks:** 2
- **Files created:** 15

## Accomplishments
- Extracted all 11 preprocessor pipeline functions into individual domain files with @register_preprocessor decorators
- Created _registry.py with register_preprocessor, get_registered_preprocessors, clear_registry
- Created __init__.py with pkgutil auto-discovery and run_preprocessors entry point
- All 27+ functions re-exported for full backward compatibility (zero test modifications needed)
- Added _init_override_sources (order=15) to replace inline renderer.py loop
- 11 registry tests (7 unit + 4 integration) all pass green
- All 70 existing preprocessor tests pass unchanged
- All 531 renderer tests pass unchanged (1 pre-existing failure excluded)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create registry infrastructure and registry tests** - `08dfcf6` (test)
2. **Task 2: Split preprocessors.py into domain files with decorators and create __init__.py** - `3dc8728` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/preprocessors/_registry.py` - Decorator registry with PreprocessorFn type, register/get/clear functions
- `python/src/odoo_gen_utils/preprocessors/__init__.py` - Auto-discovery, run_preprocessors, backward-compatible re-exports
- `python/src/odoo_gen_utils/preprocessors/relationships.py` - _process_relationships (order=10) + _init_override_sources (order=15) + 4 helpers
- `python/src/odoo_gen_utils/preprocessors/validation.py` - _validate_no_cycles (NOT registered, raises exceptions)
- `python/src/odoo_gen_utils/preprocessors/computation_chains.py` - _process_computation_chains (order=20)
- `python/src/odoo_gen_utils/preprocessors/constraints.py` - _process_constraints (order=30)
- `python/src/odoo_gen_utils/preprocessors/performance.py` - _process_performance (order=40) + _enrich_model_performance
- `python/src/odoo_gen_utils/preprocessors/production.py` - _process_production_patterns (order=50)
- `python/src/odoo_gen_utils/preprocessors/security.py` - _process_security_patterns (order=60) + 8 helpers
- `python/src/odoo_gen_utils/preprocessors/audit.py` - _process_audit_patterns (order=70) + _build_audit_log_model
- `python/src/odoo_gen_utils/preprocessors/approval.py` - _process_approval_patterns (order=80)
- `python/src/odoo_gen_utils/preprocessors/notifications.py` - _process_notification_patterns (order=90) + 2 helpers
- `python/src/odoo_gen_utils/preprocessors/webhooks.py` - _process_webhook_patterns (order=100)
- `python/src/odoo_gen_utils/preprocessors.py.bak` - Backup of original monolith for reference
- `python/tests/test_preprocessor_registry.py` - 11 tests: 7 unit + 4 integration

## Decisions Made
- Used decorator+list registry (not class-based plugins) -- simplest solution for a linear pipeline
- Used pkgutil.iter_modules for auto-discovery -- zero manual __init__.py maintenance when adding files
- validation.py NOT registered (raises exceptions, called separately before pipeline)
- _init_override_sources extracted as order=15 preprocessor (was inline in renderer.py)
- _resolve_comodel stays in relationships.py; validation.py imports from it (one-directional, safe)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Renamed preprocessors.py to preprocessors_legacy.py in Task 1**
- **Found during:** Task 1 (registry TDD tests)
- **Issue:** The old `preprocessors.py` file shadowed the new `preprocessors/` package directory, making `_registry.py` unreachable. Python resolves `.py` files before package directories.
- **Fix:** Renamed `preprocessors.py` to `preprocessors_legacy.py` and created a shim `__init__.py` that re-exported all legacy names. In Task 2, the shim was replaced with the full auto-discovery `__init__.py` and the legacy file was renamed to `.bak`.
- **Files modified:** preprocessors.py (renamed), preprocessors/__init__.py (shim created)
- **Verification:** All 70 existing tests continued passing through both stages
- **Committed in:** 08dfcf6 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The file rename was necessary to unblock package import. No scope creep. The .bak rename still happened as planned.

## Issues Encountered
- Pre-existing test failure `test_auto_fix_logs_info_message` in test_renderer.py -- confirmed this existed before any changes (not caused by the split). Out of scope for this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- preprocessors/ package complete with auto-discovery and decorator registry
- Plan 02 can update renderer.py to call run_preprocessors() instead of individual functions
- Future domain pattern phases (49, 50, 52) can add new preprocessor files without editing __init__.py
- Old preprocessors.py.bak available for reference; can be deleted in Plan 02

## Self-Check: PASSED

- All 15 created files verified present on disk
- Both task commits (08dfcf6, 3dc8728) verified in git log
- All 11 registry tests pass
- All 70 existing preprocessor tests pass
- All 531 renderer tests pass (excluding 1 pre-existing failure)
- Backward-compatible imports verified
- Registry returns exactly 11 entries in correct order

---
*Phase: 45-preprocessor-split*
*Completed: 2026-03-07*
