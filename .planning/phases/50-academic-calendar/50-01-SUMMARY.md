---
phase: 50-academic-calendar
plan: 01
subsystem: domain
tags: [preprocessor, academic-calendar, odoo, tdd, constraints]

# Dependency graph
requires:
  - phase: 49-pakistan-hec-localization
    provides: Domain preprocessor pattern (pk_* constraints, register_preprocessor decorator)
  - phase: 45-preprocessor-split
    provides: Preprocessor registry with decorator auto-discovery
provides:
  - Academic calendar preprocessor at order=27 generating academic.year/term/batch models
  - ac_* constraint type support in templates (17.0 and 18.0)
  - needs_api detection for ac_year_*/ac_term_* domain constraints
affects: [50-02, template-rendering, renderer-context]

# Tech tracking
tech-stack:
  added: []
  patterns: [model-generation-preprocessor, ac_constraint_prefix, ac_action_method_rendering]

key-files:
  created:
    - python/src/odoo_gen_utils/preprocessors/academic_calendar.py
    - python/tests/test_academic_calendar.py
  modified:
    - python/src/odoo_gen_utils/renderer_context.py
    - python/src/odoo_gen_utils/templates/17.0/model.py.j2
    - python/src/odoo_gen_utils/templates/18.0/model.py.j2
    - python/tests/test_preprocessor_registry.py

key-decisions:
  - "ac_year_*/ac_term_* rendered with @api.constrains; ac_action_* rendered as plain methods"
  - "has_pk_constraints renamed to has_domain_constraints covering pk_ + ac_year_/ac_term_ prefixes"
  - "Registry count updated 12->13 with academic_calendar at order=27"

patterns-established:
  - "Model-generation preprocessor: builds complete model dicts and appends to spec['models']"
  - "ac_action_* constraint type renders as def {name}(self) without _check_ prefix"

requirements-completed: [DOMN-03]

# Metrics
duration: 7min
completed: 2026-03-08
---

# Phase 50 Plan 01: Academic Calendar Preprocessor Summary

**TDD academic calendar preprocessor generating academic.year/term/batch with overlap prevention, term auto-generation, and state workflow via ac_* constraint types**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-08T08:05:09Z
- **Completed:** 2026-03-08T08:12:58Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 6

## Accomplishments
- 78 unit tests covering model generation, fields, constraints, config, immutability
- Academic calendar preprocessor at order=27 with 3 builder functions and pure-function main
- Template extended for ac_year_*/ac_term_* (with @api.constrains) and ac_action_* (plain methods)
- renderer_context.py needs_api detection extended for domain constraints

## Task Commits

Each task was committed atomically:

1. **Task 1: RED - Write failing tests** - `015d497` (test)
2. **Task 2: GREEN - Implement preprocessor** - `15afb74` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/preprocessors/academic_calendar.py` - Domain preprocessor (462 lines): 3 model builders, constraint check_body constants, action method bodies
- `python/tests/test_academic_calendar.py` - 78 unit tests (823 lines) covering all DOMN-03 sub-requirements
- `python/src/odoo_gen_utils/renderer_context.py` - Extended has_domain_constraints for ac_year_*/ac_term_* needs_api detection
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Added ac_* constraint rendering branches
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Same ac_* constraint rendering branches
- `python/tests/test_preprocessor_registry.py` - Updated registry count 12->13 and pipeline order

## Decisions Made
- ac_year_overlap and ac_term_overlap constraints render with @api.constrains (like pk_*), while ac_action_* renders as plain methods
- Renamed has_pk_constraints to has_domain_constraints to cover both pk_ and ac_ prefixes
- enrolled_count compute returns 0 with TODO comment (enrollment integration deferred)
- available_seats compute depends on capacity and enrolled_count fields

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated preprocessor registry count tests**
- **Found during:** Task 2 (GREEN implementation)
- **Issue:** test_preprocessor_registry.py expected 12 preprocessors; adding academic_calendar makes 13
- **Fix:** Updated count from 12 to 13, added order=27 to expected pipeline sequence
- **Files modified:** python/tests/test_preprocessor_registry.py
- **Verification:** Full test suite passes (1329 passed)
- **Committed in:** 15afb74 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Registry count test update was necessary for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Preprocessor generates well-formed model dicts consumable by existing render pipeline
- Template rendering for ac_* constraints ready (both 17.0 and 18.0)
- Plan 02 (E2E integration tests) can verify full render pipeline with academic calendar

## Self-Check: PASSED

- FOUND: python/src/odoo_gen_utils/preprocessors/academic_calendar.py
- FOUND: python/tests/test_academic_calendar.py
- FOUND: .planning/phases/50-academic-calendar/50-01-SUMMARY.md
- FOUND: commit 015d497 (test RED)
- FOUND: commit 15afb74 (feat GREEN)

---
*Phase: 50-academic-calendar*
*Completed: 2026-03-08*
