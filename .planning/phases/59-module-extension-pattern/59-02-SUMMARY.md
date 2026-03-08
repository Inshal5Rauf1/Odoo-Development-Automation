---
phase: 59-module-extension-pattern
plan: 02
subsystem: validation
tags: [semantic-validation, xpath, e17, w6, known-odoo-models, common-views, extension]

# Dependency graph
requires:
  - phase: 59-module-extension-pattern
    provides: Extension spec schema, preprocessor, templates, renderer integration (Plan 01)
provides:
  - E17 validation check for extension xpath field references (three-tier strategy)
  - W6 warning for unknown base models
  - common_views entries for 8 frequently extended Odoo models
  - End-to-end semantic validation of generated extension modules
affects: [60-iterative-refinement, validation-enhancements]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Three-tier validation: known models (error) -> registry (error) -> unknown (warning)"
    - "Regex field extraction from xpath expressions for static validation"
    - "Deduplicated W6 warnings per model (warned_models set)"

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/validation/semantic.py
    - python/src/odoo_gen_utils/data/known_odoo_models.json
    - python/tests/test_semantic_validation.py
    - python/tests/test_extension_pattern.py

key-decisions:
  - "E17 only validates field[@name=...] xpath patterns -- page, group, and other element xpaths are skipped"
  - "W6 warnings deduplicated per model name to avoid flooding output"
  - "E17 checks both known_odoo_models.json and ModelRegistry for field lookup"

patterns-established:
  - "Extension xpath validation follows same (errors, warnings) tuple return pattern"

requirements-completed: [MEXT-03]

# Metrics
duration: 11min
completed: 2026-03-09
---

# Phase 59 Plan 02: E17 Xpath Field Validation Summary

**E17 three-tier xpath field validation (known/registry/unknown) with W6 unknown model warnings and common_views for 8 frequently extended Odoo models**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-08T20:13:09Z
- **Completed:** 2026-03-08T20:24:26Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments
- E17 check catches xpath field references to non-existent fields on known Odoo models (Tier 1) and registry models (Tier 2)
- W6 warning emitted for unknown base models (Tier 3) without blocking generation
- common_views added for hr.employee, res.partner, sale.order, purchase.order, account.move, product.template, stock.picking, crm.lead
- semantic_validate() now runs 21 checks total (E1-E17 errors, W1-W6 warnings)
- 9 new tests including end-to-end extension module semantic validation
- Full test suite: 1844 passed, 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1: E17 validation check + W6 unknown model warning + known_odoo_models common_views** - `ac41266` (feat)

_Note: TDD task with RED (tests written first, 4 failing) -> GREEN (implementation, all 8 passing)_

## Files Created/Modified
- `python/src/odoo_gen_utils/validation/semantic.py` - Added _check_e17() with three-tier validation, W6 warning, wired into semantic_validate(); docstring updated to 21 checks
- `python/src/odoo_gen_utils/data/known_odoo_models.json` - Added common_views entries for 8 frequently extended models (form, tree, search view XML IDs)
- `python/tests/test_semantic_validation.py` - Added TestE17ExtensionXpathValidation class with 8 tests (bad field, good field, registry tier2, unknown model W6, non-inherited skip, page xpath skip, group xpath skip, common_views data)
- `python/tests/test_extension_pattern.py` - Added TestExtensionSemanticValidation class with end-to-end test proving zero false positives on generated extension output

## Decisions Made
- E17 uses regex `field\[@name=['"](\w+)['"]\]` to extract field names from xpath expressions -- only field references are validated, not page/group/other elements
- W6 warnings are deduplicated per model name using a `warned_models` set to avoid duplicate warnings when multiple xpaths reference the same unknown model
- E17 wired after W5 in semantic_validate() pipeline (last check before timing)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- ModelRegistry has no `register_model` method; test used `register_module` with spec dict format instead. Test adapted to use the correct API.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 59 (Module Extension Pattern) fully complete -- schema, preprocessor, templates, renderer, and validation all done
- Extension modules pass all 21 semantic validation checks with zero false positives
- Ready for Phase 60 (Iterative Refinement) or next milestone phase

## Self-Check: PASSED

All files exist, commit hash verified.

---
*Phase: 59-module-extension-pattern*
*Completed: 2026-03-09*
