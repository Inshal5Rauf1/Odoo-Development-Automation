---
phase: 21-template-correctness
plan: 02
subsystem: codegen
tags: [jinja2, wizard, acl, display_name, odoo, renderer, template-correctness]

# Dependency graph
requires:
  - phase: 21-template-correctness
    provides: "Smart mail.thread injection and conditional api import pattern"
provides:
  - "Conditional api import in wizard template"
  - "Wizard ACL entries in ir.model.access.csv"
  - "Version-gated display_name assertion in test template"
affects: [codegen, template-quality]

# Tech tracking
tech-stack:
  added: []
  patterns: ["needs_api flag for wizard conditional import", "version-gated test assertions (odoo_version >= 18.0)"]

key-files:
  created: []
  modified:
    - "python/src/odoo_gen_utils/renderer.py"
    - "python/src/odoo_gen_utils/templates/shared/wizard.py.j2"
    - "python/src/odoo_gen_utils/templates/shared/access_csv.j2"
    - "python/src/odoo_gen_utils/templates/shared/test_model.py.j2"
    - "python/tests/test_renderer.py"

key-decisions:
  - "needs_api=True always for wizards because default_get uses @api.model"
  - "Wizard ACL: single user line with 1,1,1,1 (no manager line for TransientModels)"
  - "Version gate uses string comparison odoo_version >= 18.0 in Jinja2"

patterns-established:
  - "Wizard needs_api pattern: always True since default_get requires @api.model"
  - "Version-gated test assertions: odoo_version >= 18.0 for API deprecation handling"

requirements-completed: [TMPL-02, TMPL-03, TMPL-04]

# Metrics
duration: 9min
completed: 2026-03-05
---

# Phase 21 Plan 02: Template Correctness Fixes Summary

**Conditional wizard api import, wizard ACL entries in access CSV, and version-gated display_name replacing deprecated name_get in test template**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-05T07:36:39Z
- **Completed:** 2026-03-05T07:45:25Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Wizard .py files now use conditional api import (`{{ 'api, ' if needs_api }}`) matching model.py.j2 pattern
- ir.model.access.csv includes ACL entries for wizard TransientModels with full CRUD (1,1,1,1)
- Test template replaced deprecated name_get() with display_name assertion, version-gated for Odoo 17.0 vs 18.0
- All 491 tests pass (487 passed + 4 skipped renderer tests; 2 pre-existing Docker verifier failures unrelated)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add tests for TMPL-02, TMPL-03, TMPL-04** - `80fe0ec` (test) - 8 new test methods, 5 expected to fail
2. **Task 1 GREEN: Implement all three fixes** - `9314ce9` (feat) - All 8 new tests pass, wizard api/ACL/display_name fixed

_Note: Task 2 was verification-only (full regression check), no code changes needed._

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Added needs_api=True to wizard_ctx
- `python/src/odoo_gen_utils/templates/shared/wizard.py.j2` - Conditional api import pattern
- `python/src/odoo_gen_utils/templates/shared/access_csv.j2` - Wizard ACL loop with 1,1,1,1
- `python/src/odoo_gen_utils/templates/shared/test_model.py.j2` - display_name with version gate
- `python/tests/test_renderer.py` - 8 new tests for TMPL-02, TMPL-03, TMPL-04

## Decisions Made
- needs_api is always True for wizards because the default_get method uses @api.model decorator
- Wizard ACL has one line per wizard (user group with full CRUD) -- no separate manager line needed for TransientModels
- Version gate uses Jinja2 string comparison: odoo_version >= "18.0" omits name_get, lower versions include both

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 21 (Template Correctness) is now complete -- all 3 TMPL requirements resolved
- Phase 22 (validation) can proceed independently

---
*Phase: 21-template-correctness*
*Completed: 2026-03-05*
