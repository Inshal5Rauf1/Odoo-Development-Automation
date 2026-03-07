---
phase: 45-preprocessor-split
plan: 02
subsystem: infra
tags: [preprocessors, renderer, refactoring, pipeline, registry]

# Dependency graph
requires:
  - phase: 45-preprocessor-split-01
    provides: preprocessor package with registry, auto-discovery, run_preprocessors(), and 11 domain files
provides:
  - renderer.py simplified pipeline using run_preprocessors()
  - deleted old monolithic preprocessors.py
  - complete preprocessor split migration verified by 613+ tests
affects: [46-test-fixes, renderer, preprocessors]

# Tech tracking
tech-stack:
  added: []
  patterns: [decorator-based preprocessor registry with run_preprocessors() entry point]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/preprocessors/__init__.py
    - python/src/odoo_gen_utils/preprocessors/relationships.py

key-decisions:
  - "Added backward-compatible re-exports in renderer.py for test imports that reference preprocessor functions via renderer module"
  - "Made _init_override_sources mutate in-place to match original inline behavior that tests depend on"
  - "Added registry re-discovery in run_preprocessors() to handle cleared registry after test isolation fixtures"

patterns-established:
  - "run_preprocessors(spec) as single entry point for entire preprocessing pipeline"
  - "Registry auto-recovery: run_preprocessors re-discovers if registry was cleared"

requirements-completed: [INFR-01]

# Metrics
duration: 22min
completed: 2026-03-07
---

# Phase 45 Plan 02: Renderer Wiring Summary

**Simplified renderer pipeline from 15 lines to 3 lines via run_preprocessors(), deleted 1,715-line monolith, 613 tests green with zero modifications**

## Performance

- **Duration:** 22 min
- **Started:** 2026-03-07T11:23:37Z
- **Completed:** 2026-03-07T11:45:52Z
- **Tasks:** 1
- **Files modified:** 4 (3 modified, 1 deleted)

## Accomplishments
- Replaced 10 individual preprocessor imports and calls in renderer.py with single `run_preprocessors(spec)` call
- Removed inline override_sources initialization loop (now handled by `_init_override_sources` at order=15)
- Deleted old monolithic preprocessors.py.bak (1,715 lines removed)
- All 613 preprocessor/renderer/render_stages tests pass with zero test file modifications
- Full suite (1,079 passed) matches pre-existing baseline exactly

## Task Commits

Each task was committed atomically:

1. **Task 1: Update renderer.py to use run_preprocessors and remove old monolith** - `d39ecad` (feat)

**Plan metadata:** (pending)

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Simplified imports (2 lines vs 12) and pipeline (3 lines vs 15), added backward-compatible re-exports
- `python/src/odoo_gen_utils/preprocessors/__init__.py` - Added _rediscover() for registry resilience and enhanced run_preprocessors() with empty-registry detection
- `python/src/odoo_gen_utils/preprocessors/relationships.py` - Fixed _init_override_sources to mutate in-place (matching original behavior)
- `python/src/odoo_gen_utils/preprocessors.py.bak` - Deleted (old monolith)

## Decisions Made
- Added backward-compatible re-exports of 6 preprocessor functions in renderer.py because tests import them via `from odoo_gen_utils.renderer import _process_X`. This maintains API compatibility without modifying tests.
- Changed `_init_override_sources` from immutable (creating new dicts) to in-place mutation to match the original inline behavior in renderer.py that tests and callers depend on.
- Added registry auto-recovery in `run_preprocessors()` to handle the edge case where `clear_registry()` in test fixtures empties the registry before subsequent test classes call `render_module()`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Registry emptied by test fixtures caused 101 test failures**
- **Found during:** Task 1 (test verification)
- **Issue:** `test_preprocessor_registry.py` has an `autouse=True` fixture calling `clear_registry()` after each test. When run before `test_renderer.py`, the registry was empty, so `run_preprocessors()` was a no-op, causing 101 downstream test failures.
- **Fix:** Added `_rediscover()` function in `preprocessors/__init__.py` that re-imports submodules when registry is empty. `run_preprocessors()` calls it defensively before iterating.
- **Files modified:** `python/src/odoo_gen_utils/preprocessors/__init__.py`
- **Verification:** Full 613 test pass count restored
- **Committed in:** d39ecad (Task 1 commit)

**2. [Rule 1 - Bug] Immutable _init_override_sources broke mutation-dependent test**
- **Found during:** Task 1 (full suite verification)
- **Issue:** `_init_override_sources` (created in Plan 01) used immutable pattern (`{**model, ...}`) creating new model dicts. Test `test_override_sources_has_audit` expected caller's original spec to be mutated by `render_module()`, matching the old inline `model["override_sources"] = defaultdict(set)` behavior.
- **Fix:** Changed `_init_override_sources` to mutate models in-place with `model["override_sources"] = defaultdict(set)`, matching original behavior.
- **Files modified:** `python/src/odoo_gen_utils/preprocessors/relationships.py`
- **Verification:** Test passes in isolation and in full suite. Full suite failure count matches pre-existing baseline (15 failed, all pre-existing).
- **Committed in:** d39ecad (Task 1 commit)

**3. [Rule 3 - Blocking] Tests import preprocessor functions from renderer module**
- **Found during:** Task 1 (test verification)
- **Issue:** `test_renderer.py` imports `_process_computation_chains`, `_process_constraints`, `_process_performance`, `_process_production_patterns`, `_process_relationships`, `_process_security_patterns` from `odoo_gen_utils.renderer`. After removing individual imports, these were unavailable.
- **Fix:** Added backward-compatible re-export block in renderer.py importing these 6 functions from the preprocessors package.
- **Files modified:** `python/src/odoo_gen_utils/renderer.py`
- **Verification:** `ImportError` resolved, all 613 tests pass
- **Committed in:** d39ecad (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep. The deviations were caused by Plan 01's `_init_override_sources` using an immutable pattern and tests depending on mutation side-effects, plus test infrastructure relying on cross-module imports.

## Issues Encountered
- Removed `from graphlib import CycleError, TopologicalSorter` and `from collections import defaultdict` from renderer.py since they were only used by the removed inline code
- The `preprocessors.py` file had already been renamed to `.bak` by Plan 01, so deletion targeted the `.bak` file

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 45 (Preprocessor Split) is fully complete
- Ready for Phase 46 (Test Infrastructure / Test Fixes)
- 36 pre-existing broken tests remain (addressed by Phase 46)

## Self-Check: PASSED

- renderer.py: FOUND
- preprocessors/__init__.py: FOUND
- preprocessors/relationships.py: FOUND
- preprocessors.py: CONFIRMED DELETED
- preprocessors.py.bak: CONFIRMED DELETED
- 45-02-SUMMARY.md: FOUND
- Commit d39ecad: FOUND

---
*Phase: 45-preprocessor-split*
*Completed: 2026-03-07*
