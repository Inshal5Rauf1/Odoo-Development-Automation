---
phase: 62-portal-controllers
plan: 02
subsystem: codegen
tags: [jinja2, portal, qweb, controller, record-rules, odoo-portal, customer-portal]

# Dependency graph
requires:
  - phase: 62-portal-controllers-plan-01
    provides: "PortalSpec Pydantic models, portal preprocessor at order=95, E23 ownership validation"
provides:
  - "Six Jinja portal templates: controller, home counter, list, detail, editable, rules"
  - "render_portal() function as 13th pipeline stage"
  - "Portal pipeline integration after controllers stage"
affects: [logic-writer-portal-stubs, portal-testing, manifest-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [portal-controller-generation, qweb-portal-templates, portal-record-rules-generation]

key-files:
  created:
    - "python/src/odoo_gen_utils/templates/shared/portal_controller.py.j2"
    - "python/src/odoo_gen_utils/templates/shared/portal_home_counter.xml.j2"
    - "python/src/odoo_gen_utils/templates/shared/portal_list.xml.j2"
    - "python/src/odoo_gen_utils/templates/shared/portal_detail.xml.j2"
    - "python/src/odoo_gen_utils/templates/shared/portal_detail_editable.xml.j2"
    - "python/src/odoo_gen_utils/templates/shared/portal_rules.xml.j2"
  modified:
    - "python/src/odoo_gen_utils/renderer.py"
    - "python/tests/test_manifest.py"
    - "python/tests/test_portal_renderer.py"

key-decisions:
  - "Controller class named {ModuleName}Portal (e.g. UniStudentPortalPortal) via _to_class(module_name) + 'Portal'"
  - "Separate render_portal() stage function (not extending render_controllers) for clean separation"
  - "Portal templates rendered per-page: one list XML, one detail XML per page, one shared home counter XML"
  - "Controllers __init__.py updated additively (preserves existing imports)"

patterns-established:
  - "Portal controller template: CustomerPortal inheritance with counter/domain/list/detail/report patterns"
  - "QWeb template hierarchy: home counter inherits portal.portal_my_home, list uses portal.portal_table, detail uses 2-column card"
  - "Record rules template: explicit all-four permissions, separate read and write rules for editable models"

requirements-completed: [PRTL-01, PRTL-02, PRTL-03]

# Metrics
duration: 10min
completed: 2026-03-09
---

# Phase 62 Plan 02: Portal Templates and Rendering Pipeline Summary

**Six Jinja templates generating Odoo 17 portal controllers with CustomerPortal inheritance, QWeb pages with portal_table/portal_docs_entry, and base.group_portal record rules, integrated as the 13th render_portal() pipeline stage**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-09T09:25:53Z
- **Completed:** 2026-03-09T09:36:20Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Six Jinja portal templates producing correct Odoo 17 portal output: controller with CustomerPortal inheritance, QWeb home counter/list/detail/editable templates, and record rules with base.group_portal
- render_portal() stage function integrated as 13th pipeline stage after controllers
- Controller template generates counters with check_access_rights guard, domain helpers, list/detail routes with pager, editable POST handlers with allowed_fields whitelist, report download routes with _show_report()
- QWeb templates use portal.portal_docs_entry, portal.portal_table, portal.portal_layout with BUSINESS LOGIC stub zones for Logic Writer
- Record rules use noupdate=1, explicit all-four permissions, separate write rule for editable models
- 70 new tests (52 template + 18 integration) all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Six Jinja portal templates** (TDD)
   - `2faa689` (test: failing tests for portal templates)
   - `9242ff6` (feat: implement six Jinja portal templates)
2. **Task 2: render_portal() stage and pipeline integration**
   - `e3dd0ab` (feat: render_portal() stage + pipeline + integration tests)

## Files Created/Modified
- `python/src/odoo_gen_utils/templates/shared/portal_controller.py.j2` - Controller class template inheriting CustomerPortal with counters, domain helpers, list/detail routes, editable POST, report download
- `python/src/odoo_gen_utils/templates/shared/portal_home_counter.xml.j2` - QWeb home counter entries inheriting portal.portal_my_home with portal_docs_entry
- `python/src/odoo_gen_utils/templates/shared/portal_list.xml.j2` - QWeb list page with portal_table, searchbar, pagination, empty state
- `python/src/odoo_gen_utils/templates/shared/portal_detail.xml.j2` - QWeb detail page with 2-column card layout, sidebar, back button, report actions
- `python/src/odoo_gen_utils/templates/shared/portal_detail_editable.xml.j2` - QWeb editable form with CSRF token, read-only fields, editable inputs, save button
- `python/src/odoo_gen_utils/templates/shared/portal_rules.xml.j2` - Portal record rules with base.group_portal, noupdate=1, explicit permissions
- `python/src/odoo_gen_utils/renderer.py` - Added render_portal() function, "portal" to STAGE_NAMES (13 entries), portal stage in all_stages pipeline
- `python/tests/test_manifest.py` - Updated stage count assertions from 12 to 13
- `python/tests/test_portal_renderer.py` - 70 tests: template rendering + render_portal() integration

## Decisions Made
- Controller class named `{ModuleName}Portal` via `_to_class(module_name) + 'Portal'` -- consistent with existing controller naming convention
- Separate `render_portal()` function (not extending `render_controllers()`) -- portal generation is structurally different (inherits CustomerPortal, generates QWeb, generates rules)
- Portal templates rendered per-page with one shared home counter XML -- matches Odoo module layout convention
- Controllers `__init__.py` updated additively -- preserves existing imports from render_controllers stage

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Portal generation pipeline complete -- spec with portal section produces fully functional Odoo portal module
- All portal Pydantic schema, preprocessor, validation (Plan 01), templates, and rendering (Plan 02) integrated
- BUSINESS LOGIC stub zones present in controller for Logic Writer integration
- Pre-existing Docker test failures (bind mount path issue) are out of scope and do not affect portal functionality

## Self-Check: PASSED

All 8 files verified present. All 3 commit hashes verified in git log.

---
*Phase: 62-portal-controllers*
*Completed: 2026-03-09*
