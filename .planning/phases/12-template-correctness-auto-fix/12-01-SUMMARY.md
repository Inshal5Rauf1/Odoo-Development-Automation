---
phase: 12-template-correctness-auto-fix
plan: 01
subsystem: codegen
tags: [jinja2, templates, odoo, mail.thread, api-import, manifest, pylint-odoo]

# Dependency graph
requires:
  - phase: 09-edition-version-support
    provides: versioned template loader with 17.0/18.0 template directories
provides:
  - inherit_list context var in _build_model_context for mail.thread auto-inheritance
  - needs_api context var for conditional api import in model templates
  - Clean manifest template without superfluous installable/auto_install keys
  - Clean test template importing only AccessError (not ValidationError)
affects: [12-02-auto-fix, 13-golden-path-regression]

# Tech tracking
tech-stack:
  added: []
  patterns: [conditional-jinja2-import, list-based-inherit-rendering]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/templates/17.0/model.py.j2
    - python/src/odoo_gen_utils/templates/18.0/model.py.j2
    - python/src/odoo_gen_utils/templates/shared/manifest.py.j2
    - python/src/odoo_gen_utils/templates/shared/test_model.py.j2
    - python/tests/test_renderer.py

key-decisions:
  - "inherit_list as ordered list (not set) preserves explicit inherit position before mail mixins"
  - "needs_api computed from existing context vars (computed/onchange/constrained/sequence fields)"

patterns-established:
  - "Conditional Jinja2 import: {{ 'api, ' if needs_api }}fields, models"
  - "List-based _inherit rendering: {% for inh in inherit_list %} loop"

requirements-completed: [TMPL-01, TMPL-02, TMPL-03, TMPL-04]

# Metrics
duration: 5min
completed: 2026-03-03
---

# Phase 12 Plan 01: Template Correctness Fixes Summary

**Fixed 4 Jinja2 template bugs: mail.thread auto-inheritance, conditional api import, clean manifest keys, and unused ValidationError removal**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-03T17:08:06Z
- **Completed:** 2026-03-03T17:13:06Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- mail.thread and mail.activity.mixin automatically added to _inherit when mail is in depends (both 17.0 and 18.0 templates)
- api import conditionally included only when computed/onchange/constrained/sequence fields exist
- Removed superfluous installable and auto_install keys from manifest template (prevents pylint-odoo C8116)
- Removed unused ValidationError import from test template, keeping only AccessError
- 25 new tests added (18 unit + 7 integration), all 303 project tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add inherit_list and needs_api to renderer context + fix templates** (TDD)
   - `37acc25` (test) - Failing tests for 4 template correctness fixes (RED)
   - `1f24b70` (feat) - Fix 4 template correctness bugs TMPL-01 through TMPL-04 (GREEN)
2. **Task 2: Verify template fixes via full render integration test** - `6d7ef92` (test)

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Added inherit_list and needs_api context keys to _build_model_context
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Conditional api import, list-based _inherit rendering
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Same fixes as 17.0 template
- `python/src/odoo_gen_utils/templates/shared/manifest.py.j2` - Removed installable and auto_install lines
- `python/src/odoo_gen_utils/templates/shared/test_model.py.j2` - Removed ValidationError from import
- `python/tests/test_renderer.py` - Added 25 new tests (1289 lines total)

## Decisions Made
- inherit_list uses ordered list (not set) so explicit inherit appears first, mail mixins after
- needs_api computed from existing context vars rather than adding inline logic to templates
- Both 17.0 and 18.0 templates get identical fixes (they were already nearly identical)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 4 template bugs fixed, ready for Phase 12 Plan 02 (auto-fix expansion)
- inherit_list and needs_api context vars available for auto-fix detection logic
- 303 tests pass with zero regressions

## Self-Check: PASSED

All 7 files verified present. All 3 commits verified in git log.

---
*Phase: 12-template-correctness-auto-fix*
*Completed: 2026-03-03*
