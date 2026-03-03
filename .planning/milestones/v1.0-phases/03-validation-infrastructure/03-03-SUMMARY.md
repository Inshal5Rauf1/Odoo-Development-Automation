---
phase: 03-validation-infrastructure
plan: 03
subsystem: validation
tags: [error-diagnosis, cli, click, json-patterns, odoo-17-deprecated, agent-definition]

# Dependency graph
requires:
  - phase: 03-validation-infrastructure
    provides: "Pylint runner, Docker runner, log parser, report formatter, validation types"
provides:
  - "25-pattern error diagnosis library covering model, view, security, import, deprecated API, and database errors"
  - "diagnose_errors() engine matching log text against patterns with actionable fix suggestions"
  - "validate CLI subcommand running full pipeline: pylint -> Docker install -> Docker tests -> diagnosis -> report"
  - "Functional odoo-validator agent definition (replaced stub)"
  - "Functional validate command documentation (replaced stub)"
affects: [07-quality-loops]

# Tech tracking
tech-stack:
  added: []
  patterns: [json-pattern-library, regex-diagnosis-engine, cli-pipeline-orchestration, graceful-degradation]

key-files:
  created:
    - python/src/odoo_gen_utils/validation/data/error_patterns.json
    - python/src/odoo_gen_utils/validation/data/__init__.py
    - python/src/odoo_gen_utils/validation/error_patterns.py
    - python/tests/test_error_patterns.py
    - python/tests/test_cli_validate.py
  modified:
    - python/src/odoo_gen_utils/validation/__init__.py
    - python/src/odoo_gen_utils/cli.py
    - agents/odoo-validator.md
    - commands/validate.md

key-decisions:
  - "Module-level caching for loaded error patterns (avoid repeated JSON file I/O)"
  - "IGNORECASE | MULTILINE flags on all pattern regexes for robust matching across log formats"
  - "Unrecognized errors fall back to raw traceback (not silent failure)"
  - "validate CLI uses sys.exit(1) for violations/failures, 0 for clean"

patterns-established:
  - "JSON data file + Python loader pattern for extensible pattern libraries"
  - "CLI pipeline orchestration: sequential steps with graceful degradation at each stage"
  - "Stub-to-functional agent/command upgrade pattern for phased delivery"

requirements-completed: [QUAL-07, QUAL-08]

# Metrics
duration: 6min
completed: 2026-03-02
---

# Phase 03 Plan 03: Error Diagnosis & CLI Integration Summary

**25-pattern error diagnosis engine with validate CLI subcommand orchestrating pylint + Docker + diagnosis pipeline, plus functional agent/command definitions replacing stubs**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-01T20:21:04Z
- **Completed:** 2026-03-01T20:27:09Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- 25-pattern JSON error library covering 6 categories: model/field (8), XML/view (5), security (3), import/dependency (3), Odoo 17.0 deprecated API (4), common (2)
- diagnose_errors() matches patterns against log text, returns severity-tagged diagnosis with actionable fix suggestions; unrecognized errors fall back to raw traceback
- validate CLI subcommand runs full pipeline (pylint-odoo -> Docker install -> Docker tests -> diagnosis -> report) with --pylint-only, --json, and --pylintrc options
- Graceful degradation: Docker-unavailable skips Docker steps, pylint still runs
- odoo-validator.md agent and commands/validate.md upgraded from stubs to functional definitions
- 27 TDD tests passing (18 error patterns + 9 CLI validate)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create error pattern library and diagnosis engine with tests** - `990d079` (feat)
2. **Task 2: Create validate CLI subcommand with tests and update agent/command** - `900cafa` (feat)

_Note: Both tasks followed TDD (RED-GREEN) workflow_

## Files Created/Modified
- `python/src/odoo_gen_utils/validation/data/error_patterns.json` - Library of 25 common Odoo error patterns with regex, explanation, suggestion, severity
- `python/src/odoo_gen_utils/validation/data/__init__.py` - Data package init
- `python/src/odoo_gen_utils/validation/error_patterns.py` - load_error_patterns() and diagnose_errors() functions with module-level caching
- `python/src/odoo_gen_utils/validation/__init__.py` - Updated with full public API exports (all modules)
- `python/src/odoo_gen_utils/cli.py` - Added validate subcommand with pipeline orchestration
- `python/tests/test_error_patterns.py` - 18 tests covering pattern loading, all error categories, edge cases
- `python/tests/test_cli_validate.py` - 9 tests covering help, flags, error cases, exit codes
- `agents/odoo-validator.md` - Functional agent definition with capabilities, usage, interpretation guide
- `commands/validate.md` - Full command documentation with usage examples, report format, requirements

## Decisions Made
- Used module-level caching (`_CACHED_PATTERNS`) for loaded error patterns to avoid repeated JSON file I/O on each diagnose_errors() call
- Applied IGNORECASE | MULTILINE flags on all pattern regexes for robust matching across different Odoo log line formats
- Unrecognized errors fall back to raw traceback extraction (not silent failure) -- users always get some diagnostic output
- validate CLI exits with code 1 when any violations, install failures, or test failures are found (code 0 only when fully clean)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Complete Phase 3 validation infrastructure delivered: pylint-odoo + Docker + error diagnosis + CLI + reporting
- All validation functions exported from odoo_gen_utils.validation package
- validate CLI ready for Phase 7 auto-fix loop integration via --json flag
- odoo-validator agent functional and ready for /odoo-gen:validate command invocation

## Self-Check: PASSED

All 9 created/modified files verified on disk. Both task commits (990d079, 900cafa) verified in git log.

---
*Phase: 03-validation-infrastructure*
*Completed: 2026-03-02*
