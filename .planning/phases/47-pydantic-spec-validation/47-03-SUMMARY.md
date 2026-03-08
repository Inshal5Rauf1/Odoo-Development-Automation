---
phase: 47-pydantic-spec-validation
plan: 03
subsystem: architecture
tags: [pydantic, model_dump, exclude_none, backward-compat, preprocessors]

requires:
  - phase: 47-pydantic-spec-validation (plan 02)
    provides: model_dump() call at pipeline boundary in renderer.py
provides:
  - exclude_none=True model_dump preserving .get() fallback semantics across all preprocessors
  - Immutable audit test verifying rendered output instead of input dict mutation side effects
affects: [48-domain-pattern-library, preprocessors, renderer]

tech-stack:
  added: []
  patterns: [exclude_none=True at validation boundary, test-via-output not side-effect]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/tests/test_integration_multifeature.py

key-decisions:
  - "exclude_none=True at model_dump() boundary (not per-preprocessor .get() hardening) -- single fix point, preserves idiomatic .get() pattern across all 11 preprocessors"
  - "Audit test verifies generated file content (def write, _audit_) instead of spec dict mutation -- aligns with immutable pipeline semantics from model_dump()"

patterns-established:
  - "exclude_none=True: All model_dump() calls at validation boundary must use exclude_none=True to preserve key-absence semantics"
  - "Test rendered output: Tests should verify generated file content, not rely on input dict mutation side effects"

requirements-completed: [ARCH-01]

duration: 2min
completed: 2026-03-08
---

# Phase 47 Plan 03: Test Regression Fix Summary

**exclude_none=True in model_dump() fixes 3 computation chain regressions; audit test rewritten to verify rendered output instead of input dict mutation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-08T00:51:37Z
- **Completed:** 2026-03-08T00:53:59Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Fixed 3 computation chain test failures (test_cross_model_depends, test_chain_field_has_compute_method, test_topological_order_in_output) by adding exclude_none=True to model_dump()
- Fixed test_override_sources_has_audit by rewriting it to verify generated model file content instead of relying on input dict mutation
- Full test suite passes: 1202 passed, 40 skipped, 3 Docker-only failures (pre-existing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix model_dump() to use exclude_none=True in renderer.py** - `b1a1214` (fix)
2. **Task 2: Fix test_override_sources_has_audit to not rely on input dict mutation** - `29d716f` (fix)

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Changed model_dump() to model_dump(exclude_none=True) at pipeline boundary (line 735)
- `python/tests/test_integration_multifeature.py` - Rewrote test_override_sources_has_audit to verify audit trail in generated model file

## Decisions Made
- Fixed at model_dump() boundary rather than hardening each preprocessor's .get() calls -- single fix point covering all 11 preprocessors
- Audit test checks rendered file content (`def write(` and `_audit_` markers) rather than spec dict mutation -- cleaner and aligned with immutable pipeline semantics

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 47 (Pydantic Spec Validation) fully complete with zero regressions
- ARCH-01 requirement satisfied: backward-compatible validation at pipeline boundary
- Ready for Phase 48 (next phase in v3.3 roadmap)

## Self-Check: PASSED

- FOUND: python/src/odoo_gen_utils/renderer.py
- FOUND: python/tests/test_integration_multifeature.py
- FOUND: .planning/phases/47-pydantic-spec-validation/47-03-SUMMARY.md
- FOUND: b1a1214 (Task 1 commit)
- FOUND: 29d716f (Task 2 commit)

---
*Phase: 47-pydantic-spec-validation*
*Completed: 2026-03-08*
