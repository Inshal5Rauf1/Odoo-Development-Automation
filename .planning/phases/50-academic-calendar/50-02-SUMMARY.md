---
phase: 50-academic-calendar
plan: 02
subsystem: domain
tags: [e2e-tests, academic-calendar, template-rendering, integration-tests]

# Dependency graph
requires:
  - phase: 50-academic-calendar
    provides: Academic calendar preprocessor generating academic.year/term/batch models with ac_* constraints
provides:
  - 14 E2E integration tests verifying full render_module() pipeline for academic calendar
  - Template bug fix for sequence field `required` attribute guard
affects: [template-rendering, future-domain-preprocessors]

# Tech tracking
tech-stack:
  added: []
  patterns: [e2e-render-module-testing, academic-calendar-pipeline-verification]

key-files:
  created: []
  modified:
    - python/tests/test_academic_calendar.py
    - python/src/odoo_gen_utils/templates/17.0/model.py.j2
    - python/src/odoo_gen_utils/templates/18.0/model.py.j2

key-decisions:
  - "Task 1 work already completed by Plan 01 (templates + renderer_context) -- verified and skipped"
  - "Template bug fix for sequence field required guard applied to both 17.0 and 18.0 templates"

patterns-established:
  - "E2E render test pattern: _make_e2e_spec() + _render(tmp_path) -> dict[relative_path, content]"

requirements-completed: [DOMN-03]

# Metrics
duration: 9min
completed: 2026-03-08
---

# Phase 50 Plan 02: Academic Calendar E2E Integration Tests Summary

**14 E2E integration tests verifying full render_module() pipeline for academic calendar with template bug fix for sequence field required attribute**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-08T08:15:51Z
- **Completed:** 2026-03-08T08:25:14Z
- **Tasks:** 2 (Task 1 verified as already complete, Task 2 executed)
- **Files modified:** 3

## Accomplishments
- 14 E2E integration tests covering complete module generation: model files, constraints, actions, imports, manifest, init
- Fixed pre-existing template bug: `field.required` accessed without `is defined` guard in sequence field check
- Verified Task 1 work (templates + renderer_context) already complete from Plan 01
- Full test suite green: 1343 passed (excluding pre-existing Docker mount failures)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend templates and renderer_context** - No commit (already complete from Plan 01, verified in place)
2. **Task 2: E2E integration tests and registry count** - `9818795` (feat)

## Files Created/Modified
- `python/tests/test_academic_calendar.py` - Added TestAcademicCalendarE2E class with 14 E2E tests and _make_e2e_spec() helper
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Fixed sequence field required guard (line 99)
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Same sequence field required guard fix

## Decisions Made
- Task 1 was already completed by Plan 01 (Wave 1) which extended templates and renderer_context. Verified and skipped.
- Registry count update (12->13) also already done by Plan 01. Verified in place.
- Template bug fix categorized as Rule 3 (blocking issue) since it prevented academic.batch model from rendering.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed template sequence field required guard**
- **Found during:** Task 2 (E2E tests revealed render failure for academic.batch)
- **Issue:** Line 99 in model.py.j2 (both 17.0 and 18.0) accessed `field.required` without `is defined` guard. This caused `jinja2.UndefinedError` for Char fields named `code` (in SEQUENCE_FIELD_NAMES) that lack a `required` key -- specifically academic.batch's code field.
- **Fix:** Changed `field.required` to `field.required is defined and field.required` in the sequence field elif branch, matching the pattern used elsewhere in the template.
- **Files modified:** python/src/odoo_gen_utils/templates/17.0/model.py.j2, python/src/odoo_gen_utils/templates/18.0/model.py.j2
- **Verification:** academic.batch renders successfully, all 14 E2E tests pass, full suite green
- **Committed in:** 9818795 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Template bug fix was necessary for academic.batch rendering. No scope creep.

## Issues Encountered
- Task 1 was entirely pre-completed by Plan 01 (Wave 1). The plan expected Task 1 to make template/renderer_context changes, but Plan 01 already did this work. Verified and moved on.
- Docker integration tests (test_docker_integration, test_golden_path, test_integration_multifeature) fail with pre-existing bind mount config error (missing odoo.conf). Not related to this plan's changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Academic calendar pipeline fully tested end-to-end
- Phase 50 complete -- preprocessor + templates + E2E tests all verified
- Ready for Phase 51 (next phase in v3.3 roadmap)

## Self-Check: PASSED

- FOUND: python/tests/test_academic_calendar.py
- FOUND: python/src/odoo_gen_utils/templates/17.0/model.py.j2
- FOUND: python/src/odoo_gen_utils/templates/18.0/model.py.j2
- FOUND: .planning/phases/50-academic-calendar/50-02-SUMMARY.md
- FOUND: commit 9818795 (feat E2E tests)

---
*Phase: 50-academic-calendar*
*Completed: 2026-03-08*
