---
phase: 20-auto-fix-ast-migration
plan: 01
subsystem: auto-fix
tags: [ast, python, pylint-odoo, source-modification, splice]

# Dependency graph
requires: []
provides:
  - AST-based pylint fixer implementations for W8113, W8111, C8116, W8150, C8107
  - Shared AST splice utilities (_splice_remove_keyword, _splice_rename_keyword, _splice_remove_dict_entry)
  - Multi-line test coverage for field definition and manifest fixers
affects: [20-auto-fix-ast-migration]

# Tech tracking
tech-stack:
  added: []
  patterns: ["AST locate + string splice for source modification", "reverse-order processing to avoid line shifts"]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/auto_fix.py
    - python/tests/test_auto_fix.py

key-decisions:
  - "Hybrid AST locate + string splice approach preserves formatting while providing precise node locations"
  - "Shared utility functions reduce duplication across 5 fixers"

patterns-established:
  - "AST splice pattern: parse with ast.parse(), walk to find target node, splice source string at AST positions"
  - "Process modifications in reverse line order to avoid line-shift issues"

requirements-completed: [AFIX-01]

# Metrics
duration: 11min
completed: 2026-03-05
---

# Phase 20 Plan 01: AST Migration Summary

**Migrated all 5 pylint fixers from regex to AST-based source modification with shared splice utilities and 6 new multi-line test cases**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-05T06:35:38Z
- **Completed:** 2026-03-05T06:46:14Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- All 5 pylint fixers (W8113, W8111, C8116, W8150, C8107) now use ast.parse() instead of regex
- Shared AST splice utilities handle keyword removal, renaming, and dict entry removal
- Multi-line field definitions and manifest values are now correctly handled
- 67 tests pass (61 existing + 6 new), 6 integration tests pass, zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add multi-line test cases (TDD RED)** - `88ec797` (test)
2. **Task 2: Create AST splice utilities and migrate fixers (GREEN)** - `51acce2` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/auto_fix.py` - AST splice utilities and rewritten fixer functions
- `python/tests/test_auto_fix.py` - 6 new multi-line test cases in 3 test classes

## Decisions Made
- Used hybrid "AST locate + string splice" approach instead of ast.unparse() to preserve formatting
- Created 4 shared utility functions to reduce duplication across fixers
- Kept regex for violation message parsing (correct usage -- only fixer bodies migrated to AST)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AST-based fixers are complete and tested
- Ready for Plan 02 if additional AST migration work is planned

---
*Phase: 20-auto-fix-ast-migration*
*Completed: 2026-03-05*

## Self-Check: PASSED
