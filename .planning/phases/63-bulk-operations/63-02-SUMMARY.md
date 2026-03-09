---
phase: 63-bulk-operations
plan: 02
subsystem: codegen
tags: [jinja2, templates, bulk-operations, wizard, transient-model, bus-bus, pipeline-stage]

# Dependency graph
requires:
  - phase: 63-bulk-operations
    provides: BulkOperationSpec Pydantic models, preprocessor at order=85, has_bulk_operations flag, bulk_wizards model dicts
  - phase: 62-portal-controllers
    provides: render_portal() pattern, STAGE_NAMES 13-entry constant, all_stages pattern
provides:
  - Four Jinja2 bulk wizard templates (model, line, views, JS)
  - render_bulk() as 14th pipeline stage generating wizard files per bulk operation
  - STAGE_NAMES with 14 entries (bulk as final stage)
  - Wizard TransientModel with 4-state machine, chunked batch processing, bus.bus progress
  - BUSINESS LOGIC stub zones for Logic Writer in _process_single() and action_preview()
affects: [logic-writer bulk stubs, e2e bulk wizard tests, future bulk operation types]

# Tech tracking
tech-stack:
  added: []
  patterns: [bulk wizard 4-state machine (select/preview/process/done), chunked batch processing with allow_partial branching, bus.bus progress notification, render_bulk pipeline stage]

key-files:
  created:
    - python/src/odoo_gen_utils/templates/shared/bulk_wizard_model.py.j2
    - python/src/odoo_gen_utils/templates/shared/bulk_wizard_line.py.j2
    - python/src/odoo_gen_utils/templates/shared/bulk_wizard_views.xml.j2
    - python/src/odoo_gen_utils/templates/shared/bulk_wizard_js.js.j2
    - python/tests/test_bulk_renderer.py
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/tests/test_manifest.py
    - python/tests/test_portal_renderer.py

key-decisions:
  - "Wizard class name uses source model class + operation id for uniqueness"
  - "Preview fields rendered as Char related fields via source_id (type resolution at render time)"
  - "Single shared bulk_progress.js for all bulk operations (not per-operation JS files)"
  - "render_bulk() follows same pattern as render_portal() -- separate stage function, not extending render_wizards()"

patterns-established:
  - "Bulk wizard TransientModel with _source_model, _batch_size, _allow_partial, _operation_type class attributes"
  - "4-state machine: select -> preview -> process -> done with state-conditional UI"
  - "Chunked batch processing with allow_partial (cr.commit per batch) vs all-or-nothing (cr.rollback)"
  - "bus.bus._sendone for progress with _logger.info fallback at 25% intervals"

requirements-completed: [BULK-02, BULK-03]

# Metrics
duration: 8min
completed: 2026-03-09
---

# Phase 63 Plan 02: Bulk Wizard Templates and render_bulk() Pipeline Stage Summary

**Four Jinja2 bulk wizard templates with 4-state machine, chunked batch processing, bus.bus progress, and render_bulk() as 14th pipeline stage**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-09T15:12:29Z
- **Completed:** 2026-03-09T15:20:47Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Four Jinja2 templates: wizard model (TransientModel with state machine, batch processing, bus.bus progress, stub zones), wizard line (preview fields, selected Boolean), wizard views (state-conditional form with progress bar), JS (bus listener updating progress bar)
- render_bulk() generates all bulk files per operation and updates wizards/__init__.py with imports
- Pipeline expanded to 14 stages with "bulk" as final stage after portal
- 57 new tests (48 template rendering + 9 integration) with full 2250-test regression suite green

## Task Commits

Each task was committed atomically:

1. **Task 1: Four Jinja2 bulk wizard templates**
   - `f77232d` (test: failing tests for bulk wizard templates)
   - `ff89d55` (feat: implement four bulk wizard Jinja2 templates)
2. **Task 2: render_bulk() pipeline stage and integration tests**
   - `d7e2a48` (test: failing tests for render_bulk() stage and STAGE_NAMES)
   - `8a9d46a` (feat: implement render_bulk() as 14th pipeline stage)

_Note: TDD tasks have test commit followed by implementation commit_

## Files Created/Modified
- `python/src/odoo_gen_utils/templates/shared/bulk_wizard_model.py.j2` - TransientModel wizard with 4-state machine, batch processing, bus.bus progress, BUSINESS LOGIC stub zones
- `python/src/odoo_gen_utils/templates/shared/bulk_wizard_line.py.j2` - Preview line TransientModel with wizard_id M2o, related preview fields, selected Boolean
- `python/src/odoo_gen_utils/templates/shared/bulk_wizard_views.xml.j2` - Multi-step wizard form view with state-conditional visibility, progress bar, result display
- `python/src/odoo_gen_utils/templates/shared/bulk_wizard_js.js.j2` - bus.bus progress listener updating o_bulk_progress element
- `python/src/odoo_gen_utils/renderer.py` - Added render_bulk() function and "bulk" to STAGE_NAMES and all_stages
- `python/tests/test_bulk_renderer.py` - 57 tests covering template rendering and render_bulk() integration
- `python/tests/test_manifest.py` - Updated stage count assertions from 13 to 14
- `python/tests/test_portal_renderer.py` - Updated stage count assertions from 13 to 14

## Decisions Made
- Wizard class name uses source model class + operation id for uniqueness (e.g., AdmissionApplicationBulkAdmitWizard)
- Preview fields rendered as Char related fields via source_id -- actual type resolution happens at Odoo runtime
- Single shared bulk_progress.js generated for all bulk operations (not per-operation JS files) to avoid JS duplication
- render_bulk() as separate stage function following render_portal() pattern (not extending render_wizards stage)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_portal_renderer.py stage count assertion**
- **Found during:** Task 2 (regression testing)
- **Issue:** test_portal_renderer.py::TestStageNamesIncludesPortal asserted STAGE_NAMES has 13 entries and portal is last; after adding "bulk" as 14th stage, these assertions failed
- **Fix:** Updated test_stage_count to assert 14 entries, test_portal_after_controllers to use index-based check (portal_idx == ctrl_idx + 1) instead of STAGE_NAMES[-1]
- **Files modified:** python/tests/test_portal_renderer.py
- **Verification:** Full regression suite passes (2250 tests)
- **Committed in:** 8a9d46a (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential fix to prevent regression. No scope creep.

## Issues Encountered
None -- plan executed smoothly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 63 Bulk Operations is now complete (Plan 01: schema/preprocessor/validation + Plan 02: templates/render stage)
- All four Jinja2 templates generate valid Python, XML, and JS output
- Pipeline has 14 stages; render_bulk() is fully integrated
- BULK-01 (batched create_multi), BULK-02 (wizard generation), BULK-03 (batch processing + progress) requirements satisfied
- Logic Writer can detect and fill stub zones in generated wizard code

## Self-Check: PASSED

All 6 created/modified files verified on disk. All 4 task commit hashes found in git log.

---
*Phase: 63-bulk-operations*
*Completed: 2026-03-09*
