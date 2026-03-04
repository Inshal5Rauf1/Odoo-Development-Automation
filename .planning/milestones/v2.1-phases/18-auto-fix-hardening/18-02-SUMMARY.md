---
phase: 18-auto-fix-hardening
plan: 02
subsystem: auto-fix
tags: [integration-test, cli, pylint, auto-fix, fixture, tdd]

# Dependency graph
requires:
  - phase: 18-auto-fix-hardening
    plan: 01
    provides: "auto_fix.py with pylint/Docker fix loops, fix_unused_imports, fix_missing_mail_thread"
provides:
  - "Integration test proving validate --auto-fix resolves unused imports, redundant string=, and mail.thread"
  - "Fixture module with 4 deliberate fixable violations for testing"
  - "Bug fix: pylint fix loop now continues after W0611 fixes shift line numbers"
affects: [19-cli-enhancements, validation]

# Tech tracking
tech-stack:
  added: []
  patterns: ["multi-cycle mock with line-number shift simulation", "shutil.copytree fixture isolation"]

key-files:
  created:
    - "python/tests/test_auto_fix_integration.py"
    - "python/tests/fixtures/auto_fix_module/__init__.py"
    - "python/tests/fixtures/auto_fix_module/__manifest__.py"
    - "python/tests/fixtures/auto_fix_module/models/__init__.py"
    - "python/tests/fixtures/auto_fix_module/models/training.py"
    - "python/tests/fixtures/auto_fix_module/views/training_views.xml"
  modified:
    - "python/src/odoo_gen_utils/auto_fix.py"
    - "python/tests/fixtures/conftest.py"

key-decisions:
  - "Mock run_pylint_odoo with multi-cycle behavior to simulate realistic line-number shifts after import removal"
  - "Test mail.thread fix separately via direct function call rather than CLI (mail.thread is a Docker-detected pattern, not pylint)"

patterns-established:
  - "Fixture module pattern: tests/fixtures/{name}/ with deliberate violations for integration testing"
  - "Multi-cycle pylint mock: return different violations per cycle to simulate line-number shifts"

requirements-completed: [AFIX-02]

# Metrics
duration: 6min
completed: 2026-03-04
---

# Phase 18 Plan 02: Auto-Fix Integration Test Summary

**Integration test suite proving validate --auto-fix resolves unused imports, redundant string=, and mail.thread violations on a fixture module, with a bug fix for premature loop exit after W0611 line shifts**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-04T16:28:03Z
- **Completed:** 2026-03-04T16:34:30Z
- **Tasks:** 2
- **Files created/modified:** 8

## Accomplishments
- Created fixture module at tests/fixtures/auto_fix_module/ with 4 deliberate fixable violations (unused api, unused ValidationError, redundant string="Name", missing mail.thread)
- 6 integration tests proving the full validate --auto-fix --pylint-only CLI flow resolves known violations
- Discovered and fixed a bug in run_pylint_fix_loop where W0611 fixes shifted line numbers causing W8113 fixes to fail silently
- 405 total tests pass (67 auto_fix tests), no regressions

## Task Commits

Each task was committed atomically (TDD: test + fix):

1. **Task 1: Create fixture module with known fixable violations** - `7bb30d4` (feat)
2. **Task 2: Integration test for validate --auto-fix CLI**
   - `71a8dda` test(18-02): add integration tests for validate --auto-fix CLI
   - `2c1a083` fix(18-02): fix pylint fix loop exiting early after W0611 shifts line numbers

## Files Created/Modified
- `python/tests/fixtures/auto_fix_module/` - Fixture module with deliberate violations (5 files)
- `python/tests/fixtures/conftest.py` - Updated to exclude auto_fix_module from pytest collection
- `python/tests/test_auto_fix_integration.py` - 6 integration tests for full CLI auto-fix pipeline
- `python/src/odoo_gen_utils/auto_fix.py` - Bug fix: run_pylint_fix_loop continues cycling after W0611 fixes

## Decisions Made
- Mocked run_pylint_odoo with multi-cycle behavior (returning updated line numbers per cycle) rather than running real pylint-odoo, because real pylint returns paths relative to CWD which don't match module-relative paths needed by fix functions
- Tested fix_missing_mail_thread via direct function call rather than through CLI, since mail.thread detection is a Docker-pattern (not pylint) and CLI only runs it in Docker mode

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed premature loop exit in run_pylint_fix_loop after W0611 line shifts**
- **Found during:** Task 2 (Integration test revealed string= not being fixed)
- **Issue:** When fix_unused_imports removed import lines (W0611), line numbers shifted for subsequent violations (W8113). The loop checked `cycle_fixed == 0` for non-W0611 violations and exited, even though W0611 fixes had been applied and a new pylint cycle with updated line numbers would fix W8113.
- **Fix:** Added `w0611_applied` tracking; loop now continues to next cycle when W0611 fixes were applied but other fixable violations failed due to stale line numbers
- **Files modified:** python/src/odoo_gen_utils/auto_fix.py (lines 329-358)
- **Verification:** All 67 auto_fix tests pass, 405 total tests pass
- **Committed in:** `2c1a083`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential correctness fix discovered by integration testing. The auto-fix pipeline now correctly handles the common case where unused import removal shifts line numbers for subsequent fixes.

## Issues Encountered
None beyond the bug documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 18 complete: all auto-fix hardening done
- 405 tests passing (67 auto_fix unit + integration), no Docker required
- Both unused imports and redundant string= violations are fixed in a single validate --auto-fix run
- Ready for Phase 19 (CLI enhancements)

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 18-auto-fix-hardening*
*Completed: 2026-03-04*
