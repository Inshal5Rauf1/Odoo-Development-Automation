---
phase: 59-module-extension-pattern
plan: 01
subsystem: codegen
tags: [pydantic, jinja2, xpath, _inherit, extension, odoo, preprocessor]

# Dependency graph
requires:
  - phase: 58-logic-writer-overrides-actions
    provides: BUSINESS LOGIC START/END marker pattern for method stubs
provides:
  - ExtensionSpec Pydantic schema (extends block in ModuleSpec)
  - Extension preprocessor (order=12): depends injection, selection normalization
  - _build_extension_context() and _build_extension_view_context() in renderer_context.py
  - extension_model.py.j2 template (_inherit model with fields, computed, constraints, methods)
  - extension_views.xml.j2 template (xpath Pattern A/B/C with auto two-column layout)
  - render_extensions() stage in render_module() pipeline
  - Updated init_models.py.j2 with extension model imports
affects: [60-iterative-refinement, validation-semantic-e17, logic-writer-extension-stubs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Extension _inherit models via 'extends' spec block coexisting with 'models'"
    - "Preprocessor auto-injects base_module into depends list"
    - "View inheritance via xpath with Pattern A (after field), B (new page), C (inside group)"
    - "Auto two-column group layout when page has 4+ fields"

key-files:
  created:
    - python/src/odoo_gen_utils/preprocessors/extensions.py
    - python/src/odoo_gen_utils/templates/shared/extension_model.py.j2
    - python/src/odoo_gen_utils/templates/shared/extension_views.xml.j2
    - python/tests/test_extension_pattern.py
    - python/tests/fixtures/extension_spec.json
  modified:
    - python/src/odoo_gen_utils/spec_schema.py
    - python/src/odoo_gen_utils/renderer_context.py
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/preprocessors/__init__.py
    - python/src/odoo_gen_utils/templates/shared/init_models.py.j2
    - python/tests/test_preprocessor_registry.py
    - python/tests/test_manifest.py

key-decisions:
  - "Extensions preprocessor at order=12 (between relationships@10 and init_override_sources@15)"
  - "Extension model files named after base model (hr_employee.py not hr_employee_ext.py)"
  - "View record XML ID format: view_{base_model_var}_{view_type}_inherit_{module_name}"
  - "Extensions stage placed after models in pipeline (greenfield first, then extensions)"

patterns-established:
  - "Extension spec uses 'extends' array alongside 'models' in same ModuleSpec"
  - "comodel alias normalized to comodel_name by preprocessor for template compatibility"
  - "values alias normalized to selection for Selection fields by preprocessor"

requirements-completed: [MEXT-01, MEXT-02, MEXT-03]

# Metrics
duration: 14min
completed: 2026-03-09
---

# Phase 59 Plan 01: Module Extension Pattern Summary

**Pydantic schema, preprocessor, Jinja2 templates, and renderer integration for generating _inherit extension modules with fields, xpath views, and manifest depends**

## Performance

- **Duration:** 14 min
- **Started:** 2026-03-08T19:55:08Z
- **Completed:** 2026-03-08T20:09:18Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Full extension spec schema (7 new Pydantic models) added to ModuleSpec with duplicate base_model validator
- Extensions preprocessor auto-injects base_module into depends and normalizes field aliases
- Two new Jinja2 templates: extension_model.py.j2 (_inherit with fields, computed, constraints, BUSINESS LOGIC markers) and extension_views.xml.j2 (xpath Pattern A/B/C with auto two-column layout)
- render_extensions() stage integrated into render_module() pipeline as 12th stage
- init_models.py.j2 now imports both greenfield and extension model files
- 31 extension tests + full suite green (1841 passed, 0 failures)

## Task Commits

Each task was committed atomically:

1. **Task 1: Pydantic schema + preprocessor + extension context builder** - `6def6f9` (feat)
2. **Task 2: Extension templates + renderer integration + init_models update** - `db1d8e4` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/spec_schema.py` - Added ExtensionSpec, ExtensionFieldSpec, ViewInsertionSpec, ViewExtensionSpec, ExtensionComputedSpec, ExtensionConstraintSpec, ExtensionMethodSpec; extends field on ModuleSpec
- `python/src/odoo_gen_utils/preprocessors/extensions.py` - New preprocessor (order=12) for depends injection and field normalization
- `python/src/odoo_gen_utils/renderer_context.py` - Added _build_extension_context() and _build_extension_view_context(); updated _build_module_context() with extension keys
- `python/src/odoo_gen_utils/renderer.py` - Added render_extensions() function and "extensions" stage; STAGE_NAMES 11 -> 12
- `python/src/odoo_gen_utils/templates/shared/extension_model.py.j2` - _inherit model template with all field types, computed, constraints, method stubs
- `python/src/odoo_gen_utils/templates/shared/extension_views.xml.j2` - xpath view inheritance template with Pattern A/B/C
- `python/src/odoo_gen_utils/templates/shared/init_models.py.j2` - Updated to import extension model files
- `python/src/odoo_gen_utils/preprocessors/__init__.py` - Added backward-compatible re-export
- `python/tests/test_extension_pattern.py` - 31 tests covering schema, preprocessor, context, templates, renderer
- `python/tests/fixtures/extension_spec.json` - hr.employee extension + uni.faculty.publication greenfield
- `python/tests/test_preprocessor_registry.py` - Updated count 14 -> 15 and order list
- `python/tests/test_manifest.py` - Updated stage count 11 -> 12

## Decisions Made
- Extensions preprocessor runs at order=12 (before init_override_sources@15) to avoid order conflict and ensure depends injection happens early
- Extension model files are named after the base model (e.g., `hr_employee.py` for extending hr.employee) following standard Odoo convention
- View record XML ID format: `view_{base_model_var}_{view_type}_inherit_{module_name}` for unique identification
- Extensions stage placed after models but before views in pipeline so greenfield renders first

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Preprocessor order conflict at order=15**
- **Found during:** Task 1 (preprocessor implementation)
- **Issue:** Plan specified order=15 for extensions preprocessor, but init_override_sources already registered at order=15
- **Fix:** Changed extensions preprocessor to order=12 (between relationships@10 and init_override_sources@15)
- **Files modified:** python/src/odoo_gen_utils/preprocessors/extensions.py
- **Verification:** Registry test passes with correct order sequence
- **Committed in:** 6def6f9 (Task 1 commit)

**2. [Rule 1 - Bug] Registry count and stage count test assertions**
- **Found during:** Task 1 and Task 2 (test verification)
- **Issue:** Existing tests hardcoded preprocessor count (14) and stage count (11); adding new preprocessor and stage broke them
- **Fix:** Updated test_preprocessor_registry.py (14->15, order list) and test_manifest.py (11->12)
- **Files modified:** python/tests/test_preprocessor_registry.py, python/tests/test_manifest.py
- **Verification:** All registry and manifest tests pass
- **Committed in:** 6def6f9, db1d8e4

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both necessary for correctness. No scope creep.

## Issues Encountered
- Test assertion `_name not in content` was too broad (matched `comodel_name`); fixed to check `\n    _name = ` specifically

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Extension pattern complete and tested; ready for Phase 59 Plan 02 (E17 validation + known_odoo_models common_views)
- Logic Writer (Phases 56-58) will automatically detect BUSINESS LOGIC markers in extension model stubs
- Iterative refinement (Phase 60) can use same extends machinery for field additions to existing generated modules

---
*Phase: 59-module-extension-pattern*
*Completed: 2026-03-09*
