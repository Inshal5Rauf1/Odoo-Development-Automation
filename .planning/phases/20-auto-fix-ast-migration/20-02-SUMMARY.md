---
phase: 20-auto-fix-ast-migration
plan: 02
subsystem: auto-fix
tags: [ast, unused-imports, pylint, python]

requires:
  - phase: 20-auto-fix-ast-migration/01
    provides: AST splice utilities and base infrastructure
provides:
  - Full AST body scan for unused import detection (replaces 4-name whitelist)
  - _find_all_name_references helper using ast.walk + ast.Name
  - _find_all_in_module helper for __all__ export detection
affects: [auto-fix, validation, code-generation]

tech-stack:
  added: []
  patterns: [ast.walk full body scan for name references, __all__ awareness in import analysis]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/auto_fix.py
    - python/tests/test_auto_fix.py

key-decisions:
  - "Pure AST approach: only ast.Name references used for usage detection, no string search fallback"
  - "Star imports unconditionally preserved (never removed)"
  - "__all__ exports treated as used names even without local references"

patterns-established:
  - "AST body scan: _find_all_name_references collects all ast.Name nodes excluding import lines"
  - "Import unused detection: compare imported names against AST-derived used_names set"

requirements-completed: [AFIX-02]

duration: 6min
completed: 2026-03-05
---

# Phase 20 Plan 02: Unused Import Full AST Body Scan Summary

**Replaced 4-name import whitelist with full AST body scan using ast.walk + ast.Name for arbitrary unused import detection**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-05T06:49:58Z
- **Completed:** 2026-03-05T06:55:35Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Eliminated false negatives: any unused import is now detected regardless of name
- Added _find_all_name_references for complete AST body scanning
- Added _find_all_in_module for __all__ export awareness
- Deleted _IMPORT_USAGE_PATTERNS whitelist entirely (no fallback)
- 75 tests passing (67 existing + 8 new), 6 integration tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Wave 0 tests for full-body import scanning** - `939159d` (test) - TDD RED: 8 new tests, 6 failing
2. **Task 2: Rewrite fix_unused_imports with full AST body scan** - `2a8e042` (feat) - TDD GREEN: all 75 tests pass

## Files Created/Modified
- `python/src/odoo_gen_utils/auto_fix.py` - Replaced whitelist with AST body scan, added _find_all_name_references and _find_all_in_module helpers
- `python/tests/test_auto_fix.py` - Added 8 tests: TestUnusedImportsArbitraryNames (4), TestUnusedImportsStarImport (1), TestUnusedImportsAllExport (1), TestFormattingPreserved (2)

## Decisions Made
- Pure AST approach with no string search fallback -- ast.Name nodes capture all usage including attribute access chains
- Star imports unconditionally preserved since they may introduce any names
- __all__ exports treated as used to prevent removing re-exported names

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 20 (Auto-Fix AST Migration) complete with both plans done
- All auto-fix functions now use AST-based approaches
- Ready for Phase 21 or 22 (independent phases)

---
*Phase: 20-auto-fix-ast-migration*
*Completed: 2026-03-05*
