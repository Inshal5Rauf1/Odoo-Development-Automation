---
phase: 58-logic-writer-overrides-actions
plan: 02
subsystem: validation
tags: [ast, semantic-validation, super-call, state-check, cron-decorator, skeleton-diff]

# Dependency graph
requires:
  - phase: 58-logic-writer-overrides-actions
    provides: BUSINESS LOGIC markers, _find_stub_zones(), action_context, cron_context
  - phase: 57-logic-writer-computed-constraints
    provides: E7-E12 semantic validation pattern, _has_api_decorator, _ParsedModel
provides:
  - E13 check for missing super() in create/write overrides
  - W5 warning for action methods modifying state without precondition check
  - E15 check for cron methods missing @api.model decorator
  - E16 skeleton diff check for exclusion zone violations
  - _has_super_call() AST helper for super() detection
  - _has_state_precondition() helper for state check detection
  - _lines_outside_zones() for zone-aware line comparison
  - Skeleton copy step in render pipeline for E16 baseline
affects: [logic-writer-agent-prompt, future-auto-fix-suggestions]

# Tech tracking
tech-stack:
  added: []
  patterns: [zone-aware-line-comparison, skeleton-baseline-diff, state-precondition-detection]

key-files:
  created:
    - python/tests/fixtures/logic_writer/e13_no_super_call.py
    - python/tests/fixtures/logic_writer/e15_cron_no_api_model.py
    - python/tests/fixtures/logic_writer/e16_exclusion_zone_violation.py
    - python/tests/fixtures/logic_writer/w5_no_state_check.py
    - python/tests/fixtures/logic_writer/good_override.py
    - python/tests/fixtures/logic_writer/good_action.py
    - python/tests/fixtures/logic_writer/good_cron.py
  modified:
    - python/src/odoo_gen_utils/validation/semantic.py
    - python/src/odoo_gen_utils/renderer.py
    - python/tests/test_semantic_validation.py

key-decisions:
  - "E16 compares lines outside marker zones by extracting non-zone lines from both files, avoiding line-shift issues when stub filling adds/removes lines"
  - "Marker lines (START/END) are considered outside the zone (template-generated) but content between them is inside (editable)"
  - "E16 import of _find_stub_zones is at function level to avoid circular import (validation is not a leaf of logic_writer)"
  - "Skeleton copy in renderer copies only .py files and is wrapped in try/except to never block module generation"

patterns-established:
  - "Zone-aware line comparison for skeleton diff: extract outside-zone lines then compare sequences"
  - "State precondition detection via AST: if-check on .state or filtered(lambda) with .state reference"
  - "_has_super_call detects both Python 3 super() and old-style super(Class, self) forms"

requirements-completed: [LGEN-05, LGEN-06]

# Metrics
duration: 9min
completed: 2026-03-09
---

# Phase 58 Plan 02: E13, W5, E15, E16 Semantic Checks & Skeleton Copy Summary

**4 new semantic validation checks for override/action/cron pattern violations with zone-aware skeleton diff for exclusion zone detection**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-08T18:51:57Z
- **Completed:** 2026-03-08T19:01:00Z
- **Tasks:** 1
- **Files modified:** 10

## Accomplishments
- E13 catches create/write overrides missing super() call (both Python 3 and old-style super)
- W5 warns on action_* methods that modify state without precondition check (if-check or filtered lambda)
- E15 catches _cron_* methods without @api.model decorator
- E16 detects template code modifications outside BUSINESS LOGIC marker zones via skeleton comparison
- Skeleton copy step added to render pipeline (non-blocking, copies .py files)
- 7 new fixture files (bad + good) and 18 new tests, all passing
- semantic_validate() now runs 20 checks total (E1-E13, E15-E16, W1-W5)

## Task Commits

Each task was committed atomically:

1. **Task 1: E13 + W5 + E15 + E16 semantic checks** - `3c465b6` (test), `3aecedd` (feat)

_Note: TDD task has two commits (test -> feat)_

## Files Created/Modified
- `python/src/odoo_gen_utils/validation/semantic.py` - Added E13, W5, E15, E16 checks + helpers (_has_super_call, _has_state_precondition, _lines_outside_zones)
- `python/src/odoo_gen_utils/renderer.py` - Added skeleton copy step for E16 baseline
- `python/tests/test_semantic_validation.py` - 5 new test classes with 18 tests
- `python/tests/fixtures/logic_writer/e13_no_super_call.py` - Bad override without super()
- `python/tests/fixtures/logic_writer/w5_no_state_check.py` - Bad action without state check
- `python/tests/fixtures/logic_writer/e15_cron_no_api_model.py` - Bad cron without @api.model
- `python/tests/fixtures/logic_writer/e16_exclusion_zone_violation.py` - Skeleton + filled pairs for zone diff testing
- `python/tests/fixtures/logic_writer/good_override.py` - Correct create/write with super()
- `python/tests/fixtures/logic_writer/good_action.py` - Correct action with state check
- `python/tests/fixtures/logic_writer/good_cron.py` - Correct cron with @api.model

## Decisions Made
- E16 zone-aware comparison extracts lines outside marker zones from both skeleton and filled files, then compares the sequences -- avoids line-shift issues when stub filling changes line count inside zones
- Marker lines (START/END) are considered outside the zone (template-generated) while content between them is inside (editable)
- _find_stub_zones import at function level in E16 to avoid circular import
- Skeleton copy is wrapped in try/except so failures never block module generation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed E16 line-by-line comparison for variable-length zones**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** Naive line-by-line comparison broke when filled file had more lines inside marker zone than skeleton (lines shifted)
- **Fix:** Implemented _lines_outside_zones() to extract non-zone lines from both files and compare the sequences independently
- **Files modified:** python/src/odoo_gen_utils/validation/semantic.py
- **Verification:** E16 inside-markers-clean test passes
- **Committed in:** 3aecedd (feat commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for correct E16 behavior. No scope creep.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 20 semantic checks operational (E1-E13, E15-E16, W1-W5)
- Skeleton preservation in render pipeline enables E16 validation
- Phase 58 complete -- ready for Phase 59 or next milestone phase
- 78 semantic validation tests + 1804 full suite tests all passing

## Self-Check: PASSED

All 11 files verified present. Both commits (3c465b6, 3aecedd) verified in git log.

---
*Phase: 58-logic-writer-overrides-actions*
*Completed: 2026-03-09*
