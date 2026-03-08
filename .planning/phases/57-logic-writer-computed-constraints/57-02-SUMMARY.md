---
phase: 57-logic-writer-computed-constraints
plan: 02
subsystem: validation
tags: [ast, semantic-validation, odoo-orm, compute, constraint, lint]

# Dependency graph
requires:
  - phase: 51-semantic-validation
    provides: E1-E6 + W1-W4 semantic validation framework, ValidationIssue dataclass
provides:
  - E7-E12 semantic validation checks for ORM pattern violations in method bodies
  - Bad-fill and good-fill fixture files for logic writer validation testing
  - AST helper functions for decorator detection, self-iteration checks, mapped/filtered syntax
affects: [57-logic-writer-computed-constraints, 58-module-extension, 60-iterative-refinement]

# Tech tracking
tech-stack:
  added: []
  patterns: [individual _check_eN functions, fixture-based AST validation testing, sidecar JSON for target field resolution]

key-files:
  created:
    - python/tests/fixtures/logic_writer/__init__.py
    - python/tests/fixtures/logic_writer/e7_missing_self_iteration.py
    - python/tests/fixtures/logic_writer/e8_no_target_set.py
    - python/tests/fixtures/logic_writer/e9_no_validation_error.py
    - python/tests/fixtures/logic_writer/e10_bare_field_access.py
    - python/tests/fixtures/logic_writer/e11_wrong_mapped_filtered.py
    - python/tests/fixtures/logic_writer/e12_write_in_compute.py
    - python/tests/fixtures/logic_writer/good_compute.py
    - python/tests/fixtures/logic_writer/good_constraint.py
  modified:
    - python/src/odoo_gen_utils/validation/semantic.py
    - python/tests/test_semantic_validation.py

key-decisions:
  - "E7 checks both self.field reads and writes without iteration (not just assignments) -- accessing self.field on multi-record recordset without loop reads only first record"
  - "E8 reads .odoo-gen-stubs.json sidecar first, falls back to _compute_X -> field X name inference"
  - "E12 only checks direct self.write/create/unlink, not loop variable aliases (rec.write) per CONTEXT.md spec"
  - "_SELF_SAFE_ATTRS frozenset exempts ORM methods/properties from E7 false positives (env, ids, mapped, filtered, etc.)"

patterns-established:
  - "_has_api_decorator() helper: reusable AST decorator detection for @api.depends/@api.constrains/@api.model"
  - "Fixture-based testing: SOURCE strings in fixture files used by _make_module_with_model helper"
  - "_read_sidecar_targets(): JSON sidecar resolution pattern for cross-subsystem metadata"

requirements-completed: [LGEN-03, LGEN-04, LGEN-07]

# Metrics
duration: 9min
completed: 2026-03-08
---

# Phase 57 Plan 02: E7-E12 Semantic Validation Summary

**6 AST-based ORM pattern checks (E7-E12) catching missing self iteration, unset target fields, missing ValidationError, bare field access, wrong mapped/filtered syntax, and write-in-compute -- with 8 bad-fill + 2 good-fill fixture files and 26 new tests**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-08T17:15:24Z
- **Completed:** 2026-03-08T17:25:13Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 11

## Accomplishments
- 6 new _check_eN functions in semantic.py following established pattern (E7-E12)
- 8 bad-fill fixture files (one per check) + 2 good-fill fixtures for clean-pass verification
- 26 new test methods across 7 test classes (TestE7 through TestE12 + TestCleanFills)
- Full integration into semantic_validate() -- 16 checks total (E1-E12, W1-W4)
- All 1777 non-Docker tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for E7-E12** - `0e25b5b` (test)
2. **Task 1 GREEN: Implement E7-E12 checks** - `dd245ca` (feat)

_Note: TDD task has two commits (test then feat)_

## Files Created/Modified
- `python/src/odoo_gen_utils/validation/semantic.py` - Added 6 check functions (_check_e7 through _check_e12), 8 AST helper functions, updated module docstring to 16 checks
- `python/tests/test_semantic_validation.py` - Added TestE7-TestE12 classes, TestCleanFills, _make_module_with_model helper (26 new test methods)
- `python/tests/fixtures/logic_writer/e7_missing_self_iteration.py` - Bad-fill: self.total = ... without for-loop
- `python/tests/fixtures/logic_writer/e8_no_target_set.py` - Bad-fill: compute never assigns to target field
- `python/tests/fixtures/logic_writer/e9_no_validation_error.py` - Bad-fill: constraint with no raise ValidationError
- `python/tests/fixtures/logic_writer/e10_bare_field_access.py` - Bad-fill: bare `amount` instead of `rec.amount`
- `python/tests/fixtures/logic_writer/e11_wrong_mapped_filtered.py` - Bad-fill: mapped(amount) and filtered('state == done')
- `python/tests/fixtures/logic_writer/e12_write_in_compute.py` - Bad-fill: self.write() inside compute
- `python/tests/fixtures/logic_writer/good_compute.py` - Correct compute with for-loop, mapped('field'), target assignment
- `python/tests/fixtures/logic_writer/good_constraint.py` - Correct constraint with for-loop, raise ValidationError

## Decisions Made
- E7 expanded to check both reads and writes of self.field without iteration (reading self.field on multi-record recordset silently reads only first record -- equally buggy as assignment)
- Added _SELF_SAFE_ATTRS frozenset to prevent E7 false positives on ORM methods/properties (self.env, self.mapped, self.filtered, etc.)
- E12 fixture uses self.write() (not rec.write()) since the check targets direct self receivers per the CONTEXT.md specification

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] E7 expanded to cover self.field reads (not just assignments)**
- **Found during:** Task 1 GREEN (test_constrains_also_checked failing)
- **Issue:** E7 originally only checked self.field assignments, but constraints typically read self.field without assigning -- this is equally buggy on multi-record recordsets
- **Fix:** Renamed _assigns_to_self_without_loop to _accesses_self_field_without_loop, added ast.Attribute detection for self.field reads, added _SELF_SAFE_ATTRS exemption set
- **Files modified:** python/src/odoo_gen_utils/validation/semantic.py
- **Verification:** test_constrains_also_checked now passes
- **Committed in:** dd245ca

**2. [Rule 1 - Bug] E12 fixture corrected to use self.write() instead of rec.write()**
- **Found during:** Task 1 GREEN (test_bad_fill_triggers_e12 failing)
- **Issue:** Fixture used rec.write() but E12 spec checks only direct self.write() calls
- **Fix:** Changed fixture to use self.write({'total': total}) without for-loop
- **Files modified:** python/tests/fixtures/logic_writer/e12_write_in_compute.py
- **Verification:** test_bad_fill_triggers_e12 now passes
- **Committed in:** dd245ca

---

**Total deviations:** 2 auto-fixed (2 bug fixes)
**Impact on plan:** Both fixes necessary for correctness. E7 expansion catches a real Odoo multi-record bug class. E12 fixture aligns with spec.

## Issues Encountered
None -- implementation was straightforward AST analysis following established _check_eN patterns.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 16 semantic validation checks (E1-E12, W1-W4) are operational
- Fixture library established in python/tests/fixtures/logic_writer/ for future logic writer testing
- Ready for Phase 57 remaining plans (report enrichment, golden fixture E2E) or Phase 58

## Self-Check: PASSED

All 11 created files verified. Both commits (0e25b5b, dd245ca) verified in git log.

---
*Phase: 57-logic-writer-computed-constraints*
*Completed: 2026-03-08*
