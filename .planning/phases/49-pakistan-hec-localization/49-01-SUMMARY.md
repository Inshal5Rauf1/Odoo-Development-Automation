---
phase: 49-pakistan-hec-localization
plan: 01
subsystem: domain
tags: [pakistan, hec, cnic, phonenumbers, localization, preprocessor, odoo]

# Dependency graph
requires:
  - phase: 45-preprocessor-split
    provides: decorator-based preprocessor registry with pkgutil auto-discovery
provides:
  - Pakistan/HEC localization preprocessor at order=25
  - CNIC, phone, NTN, STRN, HEC registration field injection
  - GPA, credit_hours, degree_level, recognition_status field injection
  - PKR currency data file path injection via extra_data_files
  - pakistan optional-dependencies group (phonenumbers)
affects: [49-02, renderer-context, template-rendering]

# Tech tracking
tech-stack:
  added: [phonenumbers (optional)]
  patterns: [pk_field injection via preprocessor, model-prefixed SQL constraints, dispatch table for injectors]

key-files:
  created:
    - python/src/odoo_gen_utils/preprocessors/pakistan_hec.py
    - python/tests/test_pakistan_hec.py
  modified:
    - python/pyproject.toml
    - python/tests/test_preprocessor_registry.py

key-decisions:
  - "phonenumbers>=8.13,<10.0 upper bound (not <9.0) since 9.x is API-compatible"
  - "SQL constraint names prefixed with model variable name (_to_python_var) to avoid PostgreSQL collisions"
  - "Dispatch table pattern for pk_field injectors instead of if/elif chain"

patterns-established:
  - "Localization preprocessor pattern: check spec.localization, deep-copy models, inject per pk_fields"
  - "Model-prefixed SQL constraints: {model_var}_{field}_unique for PostgreSQL uniqueness"

requirements-completed: [DOMN-02]

# Metrics
duration: 4min
completed: 2026-03-08
---

# Phase 49 Plan 01: Pakistan/HEC Localization Preprocessor Summary

**TDD preprocessor (order=25) injecting CNIC/phone/NTN/STRN/HEC fields with model-prefixed SQL constraints and phonenumbers optional dependency**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-08T03:25:34Z
- **Completed:** 2026-03-08T03:29:46Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 4

## Accomplishments
- Pakistan/HEC localization preprocessor with 9 field injection helpers
- 34 unit tests covering all injection helpers, registration, immutability, and idempotency
- Preprocessor auto-discovered at order=25 via pkgutil (zero changes to __init__.py)
- pakistan optional-dependencies group added to pyproject.toml
- Full test suite green: 1241 passed, 36 skipped

## Task Commits

Each task was committed atomically:

1. **RED: Failing tests** - `bfa63a5` (test)
2. **GREEN: Implementation** - `6546cfe` (feat)

_TDD task: RED (tests first) then GREEN (implementation to pass)_

## Files Created/Modified
- `python/src/odoo_gen_utils/preprocessors/pakistan_hec.py` - Preprocessor with 9 injection helpers, dispatch table, string constant check_bodies
- `python/tests/test_pakistan_hec.py` - 34 unit tests across 8 test classes
- `python/pyproject.toml` - Added pakistan = ["phonenumbers>=8.13,<10.0"] optional dependency
- `python/tests/test_preprocessor_registry.py` - Updated counts from 11 to 12 preprocessors, added order=25 to pipeline sequence

## Decisions Made
- Used phonenumbers>=8.13,<10.0 upper bound (research showed 9.x is API-compatible, <9.0 would exclude current versions)
- SQL constraint names prefixed with _to_python_var(model.name) to avoid PostgreSQL collisions across models
- Used dispatch table (_PK_FIELD_INJECTORS dict) instead of if/elif chain for cleaner extensibility
- complex_constraints with check_body strings (not temporal type) so model.py.j2 renders full method bodies

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated registry integration tests for 12 preprocessors**
- **Found during:** GREEN implementation
- **Issue:** Existing test_preprocessor_registry.py expected exactly 11 preprocessors and order sequence [10,15,20,30,...]. Adding pakistan_hec at order=25 would break these tests.
- **Fix:** Updated count from 11 to 12 and added 25 to expected order sequence
- **Files modified:** python/tests/test_preprocessor_registry.py
- **Verification:** All 45 tests pass (34 new + 11 updated registry tests)
- **Committed in:** 6546cfe (part of GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking)
**Impact on plan:** Necessary update to existing tests to accommodate new preprocessor. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Preprocessor registered and fully tested
- Plan 02 can build on this to add template rendering integration and PKR currency XML generation
- extra_data_files key ready for renderer_context.py integration in Plan 02

## Self-Check: PASSED

- [x] pakistan_hec.py exists (369 lines, >200 min)
- [x] test_pakistan_hec.py exists (660 lines, >150 min)
- [x] pyproject.toml contains pakistan dependency group
- [x] Commit bfa63a5 (RED) exists
- [x] Commit 6546cfe (GREEN) exists
- [x] 49-01-SUMMARY.md exists
- [x] Full test suite green (1241 passed)

---
*Phase: 49-pakistan-hec-localization*
*Completed: 2026-03-08*
