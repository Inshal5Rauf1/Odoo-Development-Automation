---
phase: 07-human-review-quality-loops
plan: 03
subsystem: validation
tags: [pylint-odoo, auto-fix, docker, escalation, cli]

# Dependency graph
requires:
  - phase: 03-validation-infrastructure
    provides: "ValidationReport, Violation types, pylint_runner, error_patterns"
  - phase: 07-01
    provides: "i18n extractor and extract-i18n CLI command"
  - phase: 07-02
    provides: "generate.md with checkpoints and Step 3.5"
provides:
  - "auto_fix.py module with pylint and Docker auto-fix logic"
  - "validate CLI --auto-fix flag"
  - "generate.md Step 3.6 validation + auto-fix instructions"
affects: [08-search-fork-extend, 09-edition-version]

# Tech tracking
tech-stack:
  added: []
  patterns: [max-2-cycle-fix-loop, escalation-grouped-by-file, immutable-file-rewrite]

key-files:
  created:
    - python/src/odoo_gen_utils/auto_fix.py
    - python/tests/test_auto_fix.py
  modified:
    - python/src/odoo_gen_utils/cli.py
    - workflows/generate.md

key-decisions:
  - "Keyword matching for Docker pattern identification (simple, sufficient for 4 patterns)"
  - "Regex-based file rewriting for pylint fixes (read -> transform -> write back, immutable)"
  - "Step 3.6 validation is informational, does not block commit"

patterns-established:
  - "Fix loop pattern: run validator -> fix fixable -> re-run -> escalate remaining"
  - "Escalation format: grouped by file, file:line reference, one suggestion per violation"

requirements-completed: [QUAL-09, QUAL-10]

# Metrics
duration: 7min
completed: 2026-03-03
---

# Phase 7 Plan 3: Auto-Fix Loops Summary

**Pylint and Docker auto-fix loops with 5 fixable pylint codes, 4 Docker patterns, max-2-cycle enforcement, and grouped file:line escalation format**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-02T20:30:57Z
- **Completed:** 2026-03-02T20:38:24Z
- **Tasks:** 2 (Task 1 TDD, Task 2 wiring)
- **Files modified:** 4

## Accomplishments
- Created auto_fix.py with mechanical fixes for 5 pylint-odoo violation codes (W8113, W8111, C8116, W8150, C8107)
- Implemented Docker error pattern identification for 4 fixable patterns (xml_parse_error, missing_acl, missing_import, manifest_load_order)
- Added --auto-fix flag to validate CLI command with max-2-cycle loop and escalation output
- Added Step 3.6 (validation + auto-fix) to generate.md workflow between i18n extraction and commit
- 22 auto-fix tests pass, 169 total tests pass (0 regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: failing tests** - `99b8a75` (test)
2. **Task 1 GREEN: auto_fix module** - `405277f` (feat)
3. **Task 2: CLI + generate.md wiring** - `c699015` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/auto_fix.py` - Pylint and Docker auto-fix logic with 5 fixable codes, 4 Docker patterns, escalation formatter
- `python/tests/test_auto_fix.py` - 22 tests covering all fix handlers, batch processing, loop cycles, Docker identification, escalation
- `python/src/odoo_gen_utils/cli.py` - Added --auto-fix flag to validate command, imports auto_fix functions
- `workflows/generate.md` - Added Step 3.6 with QUAL-09 pylint auto-fix and QUAL-10 Docker auto-fix instructions

## Decisions Made
- Used keyword matching for Docker pattern identification (simple string matching against known error text patterns from error_patterns.json)
- Regex-based file rewriting for all pylint fixes: read content, apply regex transformation, write back (no in-place mutation)
- Step 3.6 validation is explicitly informational -- does NOT block the commit step to ensure generated code is always available

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 7 complete (all 3 plans done: i18n extractor, checkpoint wiring, auto-fix loops)
- Ready for Phase 8 (Search & Fork-Extend)
- All REVW and QUAL requirements for Phase 7 are satisfied

---
*Phase: 07-human-review-quality-loops*
*Completed: 2026-03-03*
