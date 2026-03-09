---
phase: 63-bulk-operations
plan: 01
subsystem: codegen
tags: [pydantic, preprocessor, semantic-validation, jinja2, bulk-operations]

# Dependency graph
requires:
  - phase: 62-portal-controllers
    provides: Portal preprocessor pattern (order=95), E23 validation pattern, _resolve_model_fields helper
provides:
  - BulkOperationSpec and BulkWizardFieldSpec Pydantic models for spec validation
  - Bulk operations preprocessor at order=85 with wizard model dict generation
  - E24/E25 semantic validators for source_model and create_model existence
  - W8 warning validator for create_fields source reference validity
  - Batched _post_create_processing template enhancement (BULK-01)
  - has_bulk_operations flag in renderer context
affects: [63-02 bulk wizard templates, 63-03 bulk render stage]

# Tech tracking
tech-stack:
  added: []
  patterns: [bulk operation preprocessor at order=85, wizard model dict generation, E24/E25/W8 semantic validation]

key-files:
  created:
    - python/src/odoo_gen_utils/preprocessors/bulk_operations.py
    - python/tests/fixtures/bulk_spec.json
    - python/tests/test_bulk_schema.py
    - python/tests/test_bulk_preprocessor.py
    - python/tests/test_bulk_validation.py
  modified:
    - python/src/odoo_gen_utils/spec_schema.py
    - python/src/odoo_gen_utils/preprocessors/__init__.py
    - python/src/odoo_gen_utils/renderer_context.py
    - python/src/odoo_gen_utils/validation/semantic.py
    - python/src/odoo_gen_utils/templates/17.0/model.py.j2
    - python/tests/test_preprocessor_registry.py

key-decisions:
  - "Preprocessor handles Pydantic model_dump conversion (supports both dict and Pydantic input)"
  - "bulk_post_processing_batch_size set on source models by preprocessor for template rendering"
  - "Template uses elif chain: bulk_post_processing_batch_size first, then is_bulk fallback for backward compat"

patterns-established:
  - "Bulk wizard model dict with 4-state machine (select/preview/process/done)"
  - "Bulk wizard line model dict with wizard_id M2o and preview_fields as related"
  - "Source model enrichment with bulk_post_processing_batch_size for batched template generation"

requirements-completed: [BULK-01, BULK-02]

# Metrics
duration: 12min
completed: 2026-03-09
---

# Phase 63 Plan 01: Bulk Operations Schema, Preprocessor, Validation Summary

**BulkOperationSpec Pydantic models with order=85 preprocessor building wizard model dicts, E24/E25/W8 semantic validators, and batched _post_create_processing template enhancement**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-09T14:56:33Z
- **Completed:** 2026-03-09T15:08:42Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- BulkOperationSpec/BulkWizardFieldSpec validate state_transition, create_related, update_fields operation types with field_validator
- Preprocessor at order=85 enriches spec with wizard model dicts (4-state machine, result fields, wizard_fields), auto-adds "bus" to depends, sets has_bulk_operations flag
- E24 errors on non-existent source_model, E25 errors on non-existent create_model for create_related, W8 warns on invalid create_fields source references
- model.py.j2 generates batched _post_create_processing with configurable batch_size for bulk source models (BULK-01)
- 56 new tests across 4 test files, all passing with 2148 total suite tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: BulkOperationSpec Pydantic models, test fixture, and bulk preprocessor at order=85**
   - `66cfed6` (test: failing tests for schema and preprocessor)
   - `c2763ce` (feat: implement bulk schema, preprocessor, and renderer context)
2. **Task 2: E24/E25 semantic validation and BULK-01 batched create_multi template enhancement**
   - `a5072a7` (test: failing tests for E24/E25/W8 bulk validation)
   - `e68a445` (feat: add E24/E25/W8 validators and batched post-processing template)

_Note: TDD tasks have test commit followed by implementation commit_

## Files Created/Modified
- `python/src/odoo_gen_utils/spec_schema.py` - Added BulkOperationSpec, BulkWizardFieldSpec Pydantic models and bulk_operations field on ModuleSpec
- `python/src/odoo_gen_utils/preprocessors/bulk_operations.py` - New preprocessor at order=85 with wizard model dict generation
- `python/src/odoo_gen_utils/preprocessors/__init__.py` - Backward-compatible re-export of _process_bulk_operations
- `python/src/odoo_gen_utils/renderer_context.py` - has_bulk_operations flag, bulk manifest files, bulk_post_processing_batch_size in model context
- `python/src/odoo_gen_utils/validation/semantic.py` - E24, E25, W8 check functions wired into semantic_validate
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Batched _post_create_processing with elif chain for backward compat
- `python/tests/fixtures/bulk_spec.json` - Test fixture with state_transition and create_related operations
- `python/tests/test_bulk_schema.py` - 19 tests for Pydantic model validation
- `python/tests/test_bulk_preprocessor.py` - 14 tests for preprocessor enrichment and wizard model generation
- `python/tests/test_bulk_validation.py` - 12 tests for E24/E25/W8 semantic validation
- `python/tests/test_preprocessor_registry.py` - Updated to expect 17 preprocessors with order=85

## Decisions Made
- Preprocessor handles Pydantic model_dump conversion to support both dict and Pydantic model inputs
- bulk_post_processing_batch_size set on source models by preprocessor (not in renderer_context) for clean data flow
- Template uses elif chain: bulk_post_processing_batch_size takes priority, is_bulk fallback preserves backward compatibility
- W8 only checks source.X references (not wizard.X) since wizard fields are on the wizard model

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Jinja2 StrictUndefined regression in model.py.j2**
- **Found during:** Task 2 (template enhancement)
- **Issue:** Adding `{% if bulk_post_processing_batch_size %}` to model.py.j2 caused StrictUndefined error for non-bulk models because the variable was not in the template context
- **Fix:** Added `bulk_post_processing_batch_size` to `_build_model_context()` in renderer_context.py (defaults to None from model dict)
- **Files modified:** python/src/odoo_gen_utils/renderer_context.py
- **Verification:** test_academic_calendar E2E test passes again, all 2148 tests green
- **Committed in:** e68a445 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential fix to prevent regression. No scope creep.

## Issues Encountered
None beyond the auto-fixed regression above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Schema, preprocessor, and validation infrastructure complete for all bulk operation templates
- Plan 02 can build bulk wizard Jinja2 templates, render stage, and JS progress listener
- has_bulk_operations flag and bulk_wizards data available in renderer context

---
*Phase: 63-bulk-operations*
*Completed: 2026-03-09*
