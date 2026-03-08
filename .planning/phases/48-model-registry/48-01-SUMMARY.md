---
phase: 48-model-registry
plan: 01
subsystem: architecture
tags: [model-registry, json, graphlib, comodel-validation, depends-inference, cycle-detection]

requires:
  - phase: 47-pydantic-spec-validation
    provides: "Pydantic spec schema with field types and comodel_name"
provides:
  - "ModelRegistry class with load/save/register/validate/infer/detect_cycles"
  - "known_odoo_models.json with 218 standard Odoo 17.0 models"
  - "ValidationResult with ERROR/WARNING/INFO severity tiers"
affects: [48-model-registry-plan-02, cli-integration, post-render-hooks]

tech-stack:
  added: [graphlib.TopologicalSorter]
  patterns: [dataclass-based registry entries, JSON persistence, three-tier validation severity]

key-files:
  created:
    - python/src/odoo_gen_utils/registry.py
    - python/src/odoo_gen_utils/data/known_odoo_models.json
    - python/tests/test_registry.py
  modified: []

key-decisions:
  - "218 known Odoo models across 54 modules (exceeds ~200 target)"
  - "8 mixin models identified (mail.thread, portal.mixin, etc.) with is_mixin=true"
  - "Frozen dataclass ModelEntry for immutable model records"
  - "Overwrite semantics: re-registering a module replaces all entries"

patterns-established:
  - "Three-tier validation: ERROR (blocks), WARNING (prints), INFO (logged)"
  - "Registry JSON structure: _meta + models + dependency_graph"
  - "Known models data file pattern: Path(__file__).parent / 'data' / '<file>.json'"

requirements-completed: [ARCH-02]

duration: 6min
completed: 2026-03-08
---

# Phase 48 Plan 01: Model Registry Core Summary

**ModelRegistry with 218 known Odoo models, comodel validation, depends inference, and cycle detection via graphlib.TopologicalSorter**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-08T01:20:46Z
- **Completed:** 2026-03-08T01:27:09Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments
- ModelRegistry class with full CRUD: load/save, register/remove, validate, infer, detect_cycles, list/show
- known_odoo_models.json shipping 218 standard Odoo 17.0 models across 54 modules (8 mixins)
- 25 unit tests covering all registry operations with 100% method coverage
- Three-tier validation severity (ERROR/WARNING/INFO) correctly categorized

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for ModelRegistry** - `fe5dc29` (test)
2. **Task 1 GREEN: Implement ModelRegistry + known_odoo_models.json** - `3f63160` (feat)

_TDD task: RED commit (failing tests) followed by GREEN commit (implementation passing all tests)_

## Files Created/Modified
- `python/src/odoo_gen_utils/registry.py` - ModelRegistry class (306 lines) with all registry operations
- `python/src/odoo_gen_utils/data/known_odoo_models.json` - 218 Odoo 17.0 models with module/fields/is_mixin
- `python/tests/test_registry.py` - 25 unit tests (329 lines) covering load/save, register/remove, validation, inference, cycles, severity

## Decisions Made
- 218 models shipped (exceeding ~200 target) covering base, mail, hr, account, sale, purchase, stock, product, project, CRM, event, fleet, maintenance, survey, MRP, POS, quality, and more
- 8 mixin models explicitly tagged (mail.thread, mail.activity.mixin, portal.mixin, utm.mixin, rating.mixin, image.mixin, format.address.mixin, resource.mixin)
- Frozen dataclass for ModelEntry ensures immutability of registered model records
- register_module() returns info messages list for overwrite notices

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed falsy empty-list default in test helper**
- **Found during:** Task 1 GREEN (test execution)
- **Issue:** `_make_spec(depends=[])` used `depends or ["base"]` which evaluated empty list as falsy, defaulting to `["base"]`
- **Fix:** Changed to `depends if depends is not None else ["base"]`
- **Files modified:** python/tests/test_registry.py
- **Verification:** test_infer_depends_from_known passes
- **Committed in:** 3f63160 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Test helper bug fix, no scope change.

## Issues Encountered
None beyond the test helper bug documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Registry core complete, ready for Plan 02 (CLI integration + post-render hooks)
- ModelRegistry API stable: register_module, validate_comodels, infer_depends, detect_cycles
- known_odoo_models.json ready for comodel reference validation

---
*Phase: 48-model-registry*
*Completed: 2026-03-08*
