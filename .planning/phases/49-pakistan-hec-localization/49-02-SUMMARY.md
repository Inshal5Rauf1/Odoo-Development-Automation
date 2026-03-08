---
phase: 49-pakistan-hec-localization
plan: 02
subsystem: domain
tags: [pakistan, hec, pkr, currency, localization, template, renderer, e2e, odoo]

# Dependency graph
requires:
  - phase: 49-pakistan-hec-localization
    provides: Pakistan/HEC preprocessor at order=25 with pk_field injection and extra_data_files
  - phase: 45-preprocessor-split
    provides: decorator-based preprocessor registry with pkgutil auto-discovery
provides:
  - extra_data_files extension point in renderer_context.py for localization data files
  - PKR currency XML data file rendering in renderer.py
  - pk_* constraint template branch with @api.constrains in model.py.j2 (17.0 + 18.0)
  - has_pk_constraints flag for needs_api computation
  - End-to-end integration tests proving full Pakistan module generation
affects: [renderer-pipeline, localization-framework]

# Tech tracking
tech-stack:
  added: []
  patterns: [extra_data_files extension point for localization preprocessors, pk_* template elif branch with @api.constrains]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/renderer_context.py
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/templates/17.0/model.py.j2
    - python/src/odoo_gen_utils/templates/18.0/model.py.j2
    - python/tests/test_pakistan_hec.py

key-decisions:
  - "Extracted _render_extra_data_files helper + _PKR_CURRENCY_XML constant to keep render_static under 80-line limit"
  - "pk_* constraints render check_body directly (no wrapping for-loop) since their check_body includes its own for rec in self: loop"

patterns-established:
  - "extra_data_files extension point: preprocessors add file paths, renderer_context includes in manifest, renderer.py writes files"
  - "pk_* template branch: elif constraint.type.startswith('pk_') renders @api.constrains + direct check_body (no double loop)"

requirements-completed: [DOMN-02]

# Metrics
duration: 3min
completed: 2026-03-08
---

# Phase 49 Plan 02: Pakistan Rendering Pipeline Integration Summary

**PKR currency XML rendering, extra_data_files manifest integration, pk_* @api.constrains template branch, and 10 E2E integration tests proving full Pakistan module generation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T03:32:55Z
- **Completed:** 2026-03-08T03:36:31Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- extra_data_files extension point wired into manifest via renderer_context.py (generic, future-proof for other localizations)
- PKR currency XML data file rendered to data/ directory with base.PKR activation record
- pk_* constraint types render with @api.constrains decorator and full check_body in both 17.0 and 18.0 templates
- has_pk_constraints flag ensures api is imported when pk_* constraints exist
- 10 end-to-end integration tests proving complete Pakistan module generation via render_module()
- Full regression green: 1251 passed, 36 skipped (was 1241 -- +10 new E2E tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire extra_data_files into renderer pipeline and render PKR data file** - `811e7fb` (feat)
2. **Task 2: Template pk_* branch + needs_api flag + E2E integration tests** - `5812cb1` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer_context.py` - extra_data_files extension point in _build_module_context + has_pk_constraints in needs_api
- `python/src/odoo_gen_utils/renderer.py` - _PKR_CURRENCY_XML constant + _render_extra_data_files helper
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - elif branch for pk_* constraints with @api.constrains
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - elif branch for pk_* constraints with @api.constrains
- `python/tests/test_pakistan_hec.py` - TestPakistanE2E class with 10 integration tests

## Decisions Made
- Extracted PKR XML content into module-level `_PKR_CURRENCY_XML` constant and `_render_extra_data_files` helper to keep `render_static` under the 80-line size limit enforced by test_render_stages.py
- pk_* constraint check_body rendered with `indent(8)` (not `indent(12)`) since it includes its own `for rec in self:` loop -- avoids double-loop nesting that the generic else branch would cause

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Refactored render_static to stay under 80-line limit**
- **Found during:** Task 1 (extra data file rendering)
- **Issue:** Adding 14 lines of PKR XML rendering inline to render_static pushed it to 82 lines, failing test_stage_function_under_80_lines[render_static]
- **Fix:** Extracted `_PKR_CURRENCY_XML` constant and `_render_extra_data_files()` helper function outside render_static; render_static calls the helper in one line
- **Files modified:** python/src/odoo_gen_utils/renderer.py
- **Verification:** render_static is now 66 lines; all 1251 tests pass
- **Committed in:** 811e7fb (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking)
**Impact on plan:** Necessary refactoring to comply with existing code quality tests. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 49 (Pakistan/HEC Localization) fully complete: preprocessor (Plan 01) + rendering pipeline (Plan 02)
- End-to-end path verified: spec with localization: "pk" produces complete module with CNIC/phone/HEC fields, PKR data file, @api.constrains decorators, correct manifest
- Ready for Phase 50

## Self-Check: PASSED

- [x] renderer_context.py contains "extra_data_files" extension point
- [x] renderer.py contains _PKR_CURRENCY_XML constant and _render_extra_data_files helper
- [x] model.py.j2 (17.0) contains pk_* elif branch
- [x] model.py.j2 (18.0) contains pk_* elif branch
- [x] test_pakistan_hec.py contains TestPakistanE2E class
- [x] Commit 811e7fb (Task 1) exists
- [x] Commit 5812cb1 (Task 2) exists
- [x] Full test suite green (1251 passed)

---
*Phase: 49-pakistan-hec-localization*
*Completed: 2026-03-08*
