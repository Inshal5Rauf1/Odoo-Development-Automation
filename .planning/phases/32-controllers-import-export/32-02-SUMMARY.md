---
phase: 32-controllers-import-export
plan: 02
subsystem: codegen
tags: [jinja2, import-export, openpyxl, transient-model, wizard, xlsx]

requires:
  - phase: 32-controllers-import-export/01
    provides: render_controllers() base with HTTP controller generation
provides:
  - Import/export wizard Jinja2 templates (import_wizard.py.j2, import_wizard_form.xml.j2)
  - render_controllers() extended with import wizard generation for models with import_export:true
  - _build_module_context enriched with has_import_export, external_dependencies, import_export_wizards
  - manifest.py.j2 external_dependencies support
  - access_csv.j2 import wizard ACL entries
affects: [validation, e2e-testing, search-fork]

tech-stack:
  added: [openpyxl (external_dependencies in generated manifest)]
  patterns: [import wizard state machine (upload/preview/done), magic byte file validation]

key-files:
  created:
    - python/src/odoo_gen_utils/templates/shared/import_wizard.py.j2
    - python/src/odoo_gen_utils/templates/shared/import_wizard_form.xml.j2
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/templates/shared/manifest.py.j2
    - python/src/odoo_gen_utils/templates/shared/access_csv.j2
    - python/tests/test_render_stages.py
    - python/tests/test_renderer.py

key-decisions:
  - "Import wizard files generated inside render_controllers() stage (not a separate stage)"
  - "Wizard init written directly by render_controllers combining spec_wizards and import_wizard imports"
  - "ACL entries for import wizards use default([]) in Jinja2 for backward compat"

patterns-established:
  - "Magic byte validation: check b'PK\\x03\\x04' for xlsx files before processing"
  - "State machine wizard: upload -> preview -> done with _reopen_wizard() pattern"
  - "external_dependencies rendering in manifest.py.j2 via conditional block"

requirements-completed: [TMPL-04]

duration: 6min
completed: 2026-03-06
---

# Phase 32 Plan 02: Import/Export Wizard Generation Summary

**TransientModel import wizard with magic byte xlsx validation, 3-state preview flow, batch import, and openpyxl export via 2 new Jinja2 templates**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-05T20:07:22Z
- **Completed:** 2026-03-05T20:13:11Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Import wizard template with Binary upload, PK\x03\x04 magic byte validation, preview step, batch import with error collection, and xlsx export via openpyxl
- Form view template with 3 state-dependent groups (upload/preview/done) and action buttons
- render_controllers() extended to generate wizard .py, form XML, and wizards/__init__.py for models with import_export:true
- _build_module_context enriched with has_import_export, external_dependencies (openpyxl), import_export_wizards list for ACL generation
- manifest.py.j2 now renders external_dependencies block when present
- access_csv.j2 includes import wizard ACL entries for security

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `d92d94a` (test)
2. **Task 1 GREEN: Import/export wizard implementation** - `8bac0d3` (feat)
3. **Task 2: Full suite regression** - no changes (727 passed, 9 skipped, 0 failures)

_TDD task had 2 commits (RED -> GREEN)_

## Files Created/Modified
- `python/src/odoo_gen_utils/templates/shared/import_wizard.py.j2` - TransientModel with Binary upload, magic byte validation, preview, batch import, xlsx export
- `python/src/odoo_gen_utils/templates/shared/import_wizard_form.xml.j2` - Multi-state form view with action buttons and act_window action
- `python/src/odoo_gen_utils/renderer.py` - Extended render_controllers() and _build_module_context() for import/export
- `python/src/odoo_gen_utils/templates/shared/manifest.py.j2` - Added external_dependencies conditional block
- `python/src/odoo_gen_utils/templates/shared/access_csv.j2` - Added import_export_wizards ACL loop
- `python/tests/test_render_stages.py` - TestRenderImportExport class (9 tests)
- `python/tests/test_renderer.py` - TestBuildModuleContextImportExport class (7 tests)

## Decisions Made
- Import wizard files generated inside render_controllers() stage rather than a new stage -- keeps the stage count at 10 and groups related functionality
- Wizard __init__.py written directly by render_controllers combining spec_wizards and import_wizard imports -- avoids conflict with render_wizards stage
- ACL template uses `default([])` for import_export_wizards -- backward compatible with existing specs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 32 complete -- both controller templates and import/export wizards implemented
- 727 tests passing with zero regressions
- Ready for Phase 33 (next milestone phase)

---
*Phase: 32-controllers-import-export*
*Completed: 2026-03-06*
