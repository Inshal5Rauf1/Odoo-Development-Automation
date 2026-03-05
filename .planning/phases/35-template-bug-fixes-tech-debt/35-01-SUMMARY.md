---
phase: 35-template-bug-fixes-tech-debt
plan: 01
subsystem: templates
tags: [jinja2, xml, odoo-views, cron, StrictUndefined, bugfix]

requires:
  - phase: 34-production-patterns
    provides: "archival pattern with wizard injection and cron injection"
provides:
  - "Safe wizard.trigger_state access in view_form.xml.j2 (17.0 and 18.0)"
  - "Dynamic doall rendering in cron_data.xml.j2 from spec value"
  - "4 regression tests covering archival+state and cron doall scenarios"
affects: []

tech-stack:
  added: []
  patterns: ["Jinja2 dict.get() guard for optional keys in StrictUndefined mode"]

key-files:
  created: []
  modified:
    - "python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2"
    - "python/src/odoo_gen_utils/templates/18.0/view_form.xml.j2"
    - "python/src/odoo_gen_utils/templates/shared/cron_data.xml.j2"
    - "python/tests/test_render_stages.py"

key-decisions:
  - "Used wizard.get('trigger_state') guard to conditionally render invisible attribute"
  - "Used cron.get('doall', false) with ternary for Python eval-compatible True/False output"

patterns-established:
  - "Jinja2 dict.get() guard: always use dict.get() for optional dict keys in templates with StrictUndefined"

requirements-completed: [PERF-04, TMPL-05]

duration: 10min
completed: 2026-03-05
---

# Phase 35 Plan 01: Template Bug Fixes Summary

**Fixed wizard.trigger_state StrictUndefined crash on archival wizards and cron doall hardcoding in Jinja2 templates**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-05T22:23:42Z
- **Completed:** 2026-03-05T22:34:20Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Fixed CRITICAL bug: view_form.xml.j2 (17.0 and 18.0) no longer crashes when archival wizard dict lacks trigger_state key
- Fixed LOW bug: cron_data.xml.j2 renders doall dynamically from spec value instead of hardcoded False
- Added 4 regression tests covering both bug scenarios
- Full test suite passes (357 tests in test_render_stages.py + test_renderer.py)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix view_form.xml.j2 wizard.trigger_state crash and cron_data.xml.j2 doall hardcoding** - `81ec4f6` (test: RED) + `1f9c71d` (fix: GREEN)
2. **Task 2: Add regression tests** - completed within Task 1 TDD flow (no separate commit needed)

_Note: TDD tasks combined -- tests written in RED phase, templates fixed in GREEN phase._

## Files Created/Modified
- `python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2` - Guarded wizard.trigger_state with dict.get()
- `python/src/odoo_gen_utils/templates/18.0/view_form.xml.j2` - Same guard as 17.0 version
- `python/src/odoo_gen_utils/templates/shared/cron_data.xml.j2` - Dynamic doall from cron.get('doall', false)
- `python/tests/test_render_stages.py` - 4 new regression tests in TestRenderModelsArchival class

## Decisions Made
- Used `wizard.get('trigger_state')` guard instead of adding trigger_state to archival wizard dicts -- keeps archival wizard minimal and matches existing dict.get() pattern in templates
- Used `'True' if cron.get('doall', false) else 'False'` ternary instead of Jinja2 `capitalize` filter -- more reliable for Python boolean-to-eval-string conversion

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test assertion matching wrong eval="True" on active field instead of doall field**
- **Found during:** Task 1 (RED phase)
- **Issue:** Initial test `assert 'eval="True"' in cron_xml` matched the `active` field's `eval="True"` instead of the `doall` field, causing false pass
- **Fix:** Changed assertion to line-by-line check: find the doall field line specifically and assert eval value
- **Files modified:** python/tests/test_render_stages.py
- **Verification:** Test correctly fails in RED phase, passes after template fix

**2. [Rule 1 - Bug] Fixed cron.doall StrictUndefined error in template**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Initial template fix `{{ 'True' if cron.doall else 'False' }}` caused StrictUndefined error when cron dict lacks doall key
- **Fix:** Changed to `{{ 'True' if cron.get('doall', false) else 'False' }}`
- **Files modified:** python/src/odoo_gen_utils/templates/shared/cron_data.xml.j2
- **Verification:** Both cron doall tests pass

**3. [Rule 1 - Bug] Fixed test file path: views file named academy_course_views.xml not academy_course_view.xml**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Test expected `academy_course_view.xml` but renderer produces `academy_course_views.xml`
- **Fix:** Updated file path in test assertions
- **Files modified:** python/tests/test_render_stages.py
- **Verification:** Tests find and read the correct file

---

**Total deviations:** 3 auto-fixed (3 bugs)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Issues Encountered
- render_module pipeline stops on first failed stage -- archival+state crash in render_views prevented all subsequent stages (wizards, cron) from running. This is by design but made debugging the cron issue require separate investigation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Both PERF-04 and TMPL-05 audit gaps are closed
- v3.1 milestone template bugs resolved
- No blockers

---
*Phase: 35-template-bug-fixes-tech-debt*
*Completed: 2026-03-05*
