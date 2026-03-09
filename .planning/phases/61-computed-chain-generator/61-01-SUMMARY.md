---
phase: 61-computed-chain-generator
plan: 01
subsystem: preprocessor
tags: [pydantic, computation-chains, validation, preprocessor, cross-model]

# Dependency graph
requires:
  - phase: 60-iterative-refinement
    provides: Iterative rendering pipeline with preprocessor registry
provides:
  - ChainStepSpec and ChainSpec Pydantic models for chain spec validation
  - Sequence-based chain preprocessor at order=22 with field auto-injection
  - 5 chain validators (E18-E22) for type, traversal, store, cycle, and existence checks
  - CGPA and fee penalty test fixtures for chain scenarios
  - Backward compatibility with old per-field chain format
affects: [62-portal-view-generator, logic-writer, context-builder]

# Tech tracking
tech-stack:
  added: []
  patterns: [sequence-based-chain-spec, chain-meta-enrichment, augmented-spec-validation]

key-files:
  created:
    - python/tests/test_computation_chains.py
    - python/tests/test_chain_validation.py
    - python/tests/fixtures/cgpa_chain_spec.json
    - python/tests/fixtures/fee_penalty_chain_spec.json
  modified:
    - python/src/odoo_gen_utils/spec_schema.py
    - python/src/odoo_gen_utils/preprocessors/computation_chains.py
    - python/tests/test_preprocessor_registry.py

key-decisions:
  - "Validators use augmented spec (chain-declared fields pre-injected) to avoid false positives on cross-step dependencies"
  - "Old per-field format preserved via _process_old_format fallback for backward compatibility"
  - "Validators co-located in computation_chains.py (not validation.py) since they need chain-parsed data"
  - "E20 store propagation uses stored_overrides parameter for testability"

patterns-established:
  - "Augmented spec pattern: build temp spec with chain-declared fields before validation"
  - "Chain meta enrichment: _chain_meta dict attached to field dicts for downstream context builder"

requirements-completed: [CCHN-01, CCHN-02, CCHN-03]

# Metrics
duration: 16min
completed: 2026-03-09
---

# Phase 61 Plan 01: Computed Chain Generator Summary

**Sequence-based chain preprocessor with Pydantic validation, 5 chain validators (E18-E22), and cross-model field auto-injection at order=22**

## Performance

- **Duration:** 16 min
- **Started:** 2026-03-09T01:18:50Z
- **Completed:** 2026-03-09T01:35:01Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Rewrote computation_chains preprocessor from per-field format (order=20) to sequence-based chain format (order=22) with Pydantic schema validation
- Implemented 5 chain-specific validators (E18-E22) catching type mismatches, traversal errors, store gaps, cross-chain cycles, and missing fields
- Maintained full backward compatibility with old per-field chain format (1962 tests pass, 48 new tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Pydantic chain schema + sequence-based preprocessor rewrite** - `f140f66` (feat)
2. **Task 2: E18-E22 chain validation checks** - `1bc77de` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/spec_schema.py` - Added ChainStepSpec and ChainSpec Pydantic models
- `python/src/odoo_gen_utils/preprocessors/computation_chains.py` - Complete rewrite: order=22, sequence-based, 5 validators, chain meta enrichment
- `python/tests/test_computation_chains.py` - 25 tests for schema and preprocessor behavior
- `python/tests/test_chain_validation.py` - 23 tests for E18-E22 validators
- `python/tests/fixtures/cgpa_chain_spec.json` - CGPA chain fixture (4 steps, 3 models)
- `python/tests/fixtures/fee_penalty_chain_spec.json` - Fee penalty chain fixture (3 steps, 2 models)
- `python/tests/test_preprocessor_registry.py` - Updated expected order from 20 to 22

## Decisions Made
- Validators use augmented spec (chain-declared fields pre-injected) to avoid false positives on cross-step dependencies within the same chain set
- Old per-field format preserved via _process_old_format fallback for backward compatibility
- Validators co-located in computation_chains.py (not validation.py) since they need chain-parsed ChainSpec data
- E20 store propagation uses stored_overrides parameter for testability without requiring full spec construction

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] False positives from E19/E22 on chain-declared fields**
- **Found during:** Task 2 (E18-E22 validators)
- **Issue:** E19 and E22 validators flagged fields that are auto-added by other steps in the same chain (e.g., grade_point on exam.result is declared by chain step but not yet in spec at validation time)
- **Fix:** Added _build_augmented_spec() that pre-injects chain-declared fields into a temporary spec copy before running validators
- **Files modified:** python/src/odoo_gen_utils/preprocessors/computation_chains.py
- **Verification:** CGPA and fee penalty fixture tests pass without false errors
- **Committed in:** 1bc77de (Task 2 commit)

**2. [Rule 3 - Blocking] Registry order test expected order=20**
- **Found during:** Task 1 (preprocessor rewrite)
- **Issue:** test_preprocessor_registry.py::test_registry_order_matches_pipeline hardcoded expected order=20 for computation_chains
- **Fix:** Updated expected order from 20 to 22
- **Files modified:** python/tests/test_preprocessor_registry.py
- **Verification:** Full test suite passes
- **Committed in:** f140f66 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Chain preprocessor ready for downstream context builder integration (chain_context in stub reports)
- All chain validators active in pipeline, catching errors before Jinja rendering
- 1962 tests passing (48 new), full backward compatibility maintained

---
## Self-Check: PASSED

All 7 files verified present. Both commit hashes (f140f66, 1bc77de) confirmed in git log. ChainStepSpec class exists in spec_schema.py. order=22 in computation_chains.py. Test files exceed 100 lines minimum (618 and 660 lines).

---
*Phase: 61-computed-chain-generator*
*Completed: 2026-03-09*
