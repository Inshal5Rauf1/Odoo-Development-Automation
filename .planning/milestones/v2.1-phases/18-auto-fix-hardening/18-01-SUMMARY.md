---
phase: 18-auto-fix-hardening
plan: 01
subsystem: auto-fix
tags: [docker-fix, xml-parse, acl, manifest, iteration-cap, pylint]

# Dependency graph
requires:
  - phase: 14-auto-fix-wiring
    provides: "auto_fix.py with pylint fix loop and Docker fix identification"
provides:
  - "3 new Docker fix functions: fix_xml_parse_error, fix_missing_acl, fix_manifest_load_order"
  - "Configurable iteration caps for both pylint and Docker fix loops (DEFAULT_MAX_FIX_ITERATIONS=5)"
  - "Multi-iteration Docker fix loop with revalidate_fn support"
affects: [19-cli-enhancements, validation, docker-validation]

# Tech tracking
tech-stack:
  added: []
  patterns: ["dispatch dict with needs_error_output flag", "revalidate_fn callback for multi-iteration loops"]

key-files:
  created: []
  modified:
    - "python/src/odoo_gen_utils/auto_fix.py"
    - "python/tests/test_auto_fix.py"
    - "python/src/odoo_gen_utils/cli.py"

key-decisions:
  - "missing_import pattern excluded from dispatch -- requires human action (install package or add module dependency)"
  - "Dispatch dict uses (fix_func, needs_error_output) tuple to handle both old and new function signatures"
  - "run_docker_fix_loop returns tuple[bool, str] instead of just bool for richer error reporting"
  - "Iteration cap message uses actionable text: 'Remaining errors require manual review'"

patterns-established:
  - "Revalidate callback pattern: pass revalidate_fn to enable multi-iteration fix loops"
  - "Dispatch with signature adaptation: tuple of (function, needs_extra_args) for mixed signatures"

requirements-completed: [DFIX-01, AFIX-01]

# Metrics
duration: 9min
completed: 2026-03-04
---

# Phase 18 Plan 01: Auto-Fix Hardening Summary

**3 new Docker fix functions (XML parse, ACL, manifest order) with configurable 5-iteration caps on both fix loops**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-04T16:15:07Z
- **Completed:** 2026-03-04T16:24:40Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Implemented fix_xml_parse_error: detects mismatched XML closing tags via lxml error pattern and heuristic tag analysis, auto-corrects typos
- Implemented fix_missing_acl: creates security/ir.model.access.csv with proper access rules for all models found in models/, updates __manifest__.py data list
- Implemented fix_manifest_load_order: reorders manifest data list so action definitions (ir.actions.act_window) precede action references (menus)
- Wired all 3 new functions into run_docker_fix_loop dispatch dict (4 of 5 patterns now have fix functions)
- Replaced hardcoded MAX_FIX_CYCLES=2 with configurable DEFAULT_MAX_FIX_ITERATIONS=5
- Both run_pylint_fix_loop and run_docker_fix_loop accept max_iterations parameter
- run_docker_fix_loop restructured as true loop with revalidate_fn callback for multi-pass fixing
- CLI validate command now passes revalidate_fn for multi-iteration Docker fixes

## Task Commits

Each task was committed atomically (TDD: test + feat per task):

1. **Task 1: Implement 3 Docker fix functions and wire dispatch**
   - `89b0884` test(18-01): add failing tests for 3 Docker fix functions and dispatch
   - `16607a5` feat(18-01): implement 3 Docker fix functions and wire dispatch

2. **Task 2: Add configurable iteration caps to both fix loops**
   - `520d99d` test(18-01): add failing tests for configurable iteration caps
   - `4d9d02d` feat(18-01): add configurable iteration caps to both fix loops

## Files Created/Modified
- `python/src/odoo_gen_utils/auto_fix.py` - 3 new fix functions, dispatch wiring, iteration cap refactor, run_docker_fix_loop loop restructure
- `python/tests/test_auto_fix.py` - 18 new tests (10 for Task 1 + 8 for Task 2), updated existing tests for new signatures
- `python/src/odoo_gen_utils/cli.py` - Updated validate command to use new run_docker_fix_loop return type and pass revalidate_fn

## Decisions Made
- missing_import pattern excluded from dispatch -- requires human action (install a Python package or add an Odoo module dependency), which cannot be mechanically determined
- Dispatch dict uses (fix_func, needs_error_output) tuple pattern to handle both old-style (module_path only) and new-style (module_path, error_output) function signatures without breaking existing code
- run_docker_fix_loop changed from returning bool to tuple[bool, str] for richer downstream reporting
- Iteration cap message uses actionable language: "Iteration cap (N) reached. Remaining errors require manual review."

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- TDD cycle count tests needed file regeneration in mock_run_pylint to prevent early loop exit (the fix function modifies the file, so subsequent cycles find nothing to fix unless the file is reset). Resolved by writing the original source back inside the mock callback.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 5 Docker error patterns identified, 4 of 5 have fix functions
- Both fix loops accept configurable iteration caps
- 61 auto_fix tests pass, 399 full suite tests pass
- Ready for Phase 18 Plan 02 or Phase 19

## Self-Check: PASSED

All 4 files verified present. All 4 commit hashes verified in git log.

---
*Phase: 18-auto-fix-hardening*
*Completed: 2026-03-04*
