---
phase: 57-logic-writer-computed-constraints
plan: 01
subsystem: logic-writer
tags: [stub-context, computation-hint, constraint-type, frozen-dataclass, classification]

# Dependency graph
requires:
  - phase: 56-logic-writer-core
    provides: StubInfo, StubContext, build_stub_context, _stub_to_dict, classify_complexity
provides:
  - Enriched StubContext with method_type, computation_hint, constraint_type, target_field_types, error_messages
  - Classification functions for compute patterns and constraint patterns
  - Enriched JSON report serialization with conditional field inclusion
affects: [57-02, 58-logic-writer-overrides-actions, 61-computed-chain-generator]

# Tech tracking
tech-stack:
  added: []
  patterns: [frozenset-keyword-matching, conditional-json-field-omission, decorator-arg-parsing]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/logic_writer/context_builder.py
    - python/src/odoo_gen_utils/logic_writer/report.py
    - python/tests/test_context_builder.py
    - python/tests/test_stub_report.py

key-decisions:
  - "Classification functions are private helpers inside context_builder.py (not classifier.py)"
  - "Empty/default enrichment values omitted from JSON to avoid clutter"
  - "Error messages use _() wrapper and %() named interpolation per Odoo convention"
  - "currency_field and digits added to _build_model_fields extraction keys"

patterns-established:
  - "Conditional JSON field inclusion: only add enriched fields when non-empty"
  - "Frozenset keyword matching for constraint_type and computation_hint classification"
  - "_parse_depends_args regex extraction of decorator arguments"

requirements-completed: [LGEN-03, LGEN-04]

# Metrics
duration: 5min
completed: 2026-03-08
---

# Phase 57 Plan 01: Enriched StubContext Summary

**Enriched StubContext with method_type, computation_hint, constraint_type, target_field_types, and error_messages fields plus classification logic and updated report JSON serialization**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-08T17:15:20Z
- **Completed:** 2026-03-08T17:20:38Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added 5 new fields to StubContext frozen dataclass with backward-compatible defaults (all 17 existing tests unchanged)
- Implemented 5 classification/builder functions: _classify_method_type, _classify_computation_hint, _classify_constraint_type, _build_target_field_types, _generate_error_messages
- Updated report serialization to conditionally include enriched fields, omitting empty values from JSON
- Added 46 new tests (34 context_builder + 12 report) -- all 99 combined tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Enrich StubContext with new fields and classification logic** - `a432180` (test), `f2181c5` (feat)
2. **Task 2: Update report serialization for enriched context** - `000ea6d` (test), `8681d2d` (feat)

_Note: TDD tasks have multiple commits (test -> feat)_

## Files Created/Modified
- `python/src/odoo_gen_utils/logic_writer/context_builder.py` - Added 5 new StubContext fields, 5 classification/builder functions, decorator arg parsing
- `python/src/odoo_gen_utils/logic_writer/report.py` - Updated _stub_to_dict with conditional enrichment field inclusion
- `python/tests/test_context_builder.py` - Added 34 new tests for method_type, computation_hint, constraint_type, target_field_types, error_messages
- `python/tests/test_stub_report.py` - Added 12 new tests for enriched report schema fields and omission

## Decisions Made
- Classification functions (_classify_method_type, _classify_computation_hint, etc.) placed inside context_builder.py as private helpers, not in classifier.py -- keeps the enrichment logic co-located with the dataclass it populates
- Empty/default enrichment values omitted from JSON output -- avoids "computation_hint": "" clutter in non-compute stubs
- Error messages use Odoo convention: _() wrapper for translations, %() named interpolation for field labels
- Added currency_field and digits to _build_model_fields extraction keys (previously missing, needed for target_field_types)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added currency_field and digits to _build_model_fields extraction**
- **Found during:** Task 1 (target_field_types implementation)
- **Issue:** _build_model_fields did not extract currency_field or digits keys from field definitions, but _build_target_field_types needs them
- **Fix:** Added "currency_field" and "digits" to the extraction key tuple in _build_model_fields
- **Files modified:** python/src/odoo_gen_utils/logic_writer/context_builder.py
- **Verification:** Monetary type test passes with currency_field populated
- **Committed in:** f2181c5 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential for correct target_field_types extraction. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Enriched StubContext provides method_type, computation_hint, constraint_type, target_field_types, error_messages
- Report JSON includes all enriched fields with empty value omission
- Ready for Phase 57 Plan 02 (E7-E12 semantic validation checks)
- Ready for Phase 58 (overrides/actions -- method_type classification already handles create/write/action_*/cron_*)

---
*Phase: 57-logic-writer-computed-constraints*
*Completed: 2026-03-08*
