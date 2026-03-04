---
phase: 03-validation-infrastructure
plan: 01
subsystem: validation
tags: [pylint-odoo, dataclasses, subprocess, json2, pytest, static-analysis]

# Dependency graph
requires:
  - phase: 01-gsd-extension
    provides: "Python package structure (pyproject.toml, odoo_gen_utils package)"
provides:
  - "Immutable validation dataclasses (Violation, TestResult, InstallResult, ValidationReport)"
  - "pylint-odoo runner with JSON2 parsing and pylintrc support"
  - "Markdown and JSON report formatters for validation results"
  - "36 unit tests covering types, runner, and reporting"
affects: [03-02-PLAN, 03-03-PLAN, 07-quality-loops]

# Tech tracking
tech-stack:
  added: [pylint-odoo 10.0.1, pytest 9.0.2]
  patterns: [frozen-dataclasses, subprocess-tool-invocation, json2-output-parsing, severity-sorted-reports]

key-files:
  created:
    - python/src/odoo_gen_utils/validation/__init__.py
    - python/src/odoo_gen_utils/validation/types.py
    - python/src/odoo_gen_utils/validation/pylint_runner.py
    - python/src/odoo_gen_utils/validation/report.py
    - python/tests/__init__.py
    - python/tests/test_validation_types.py
    - python/tests/test_pylint_runner.py
    - python/tests/test_report.py
  modified:
    - python/pyproject.toml

key-decisions:
  - "Tuples instead of lists for frozen dataclass fields (immutability compliance)"
  - "noqa F401 annotations on __init__.py re-exports to prevent linter from stripping public API"
  - "Recursive tuple-to-list conversion in format_report_json for JSON compatibility"

patterns-established:
  - "Frozen dataclasses with tuple fields for immutable domain objects"
  - "subprocess.run with JSON2 output parsing for external tool integration"
  - "Severity-ordered violation reporting (error > warning > convention > refactor > info)"
  - "TDD workflow: RED (failing tests) -> GREEN (minimal implementation) -> commit"

requirements-completed: [QUAL-01, QUAL-02, QUAL-08]

# Metrics
duration: 5min
completed: 2026-03-02
---

# Phase 03 Plan 01: Pylint-Odoo Integration Summary

**pylint-odoo 10.0.1 integration with frozen dataclass types, JSON2 parsing, and dual-format (markdown/JSON) report generation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-01T20:09:33Z
- **Completed:** 2026-03-01T20:14:59Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Frozen immutable dataclasses (Violation, TestResult, InstallResult, ValidationReport) with tuple fields for thread-safe validation state
- pylint-odoo runner that invokes `pylint --load-plugins=pylint_odoo --output-format=json2` with timeout handling, error recovery, and optional .pylintrc-odoo override support
- Dual-format report generation: structured 3-section markdown (violations table, install result, test results) with summary header, and JSON dict for machine consumption by Phase 7 auto-fix loops
- 36 unit tests covering all components with mocked subprocess calls

## Task Commits

Each task was committed atomically:

1. **Task 1: Create validation types and pylint runner with tests** - `0264c7f` (feat)
2. **Task 2: Create report formatter with tests** - `49e922a` (feat)

_Note: TDD tasks had RED->GREEN phases within each commit_

## Files Created/Modified
- `python/pyproject.toml` - Added pylint-odoo>=10.0 dependency, pytest>=8.0 test dependency
- `python/src/odoo_gen_utils/validation/__init__.py` - Public API exports with noqa annotations
- `python/src/odoo_gen_utils/validation/types.py` - 4 frozen dataclasses (Violation, TestResult, InstallResult, ValidationReport)
- `python/src/odoo_gen_utils/validation/pylint_runner.py` - parse_pylint_output + run_pylint_odoo functions
- `python/src/odoo_gen_utils/validation/report.py` - format_report_markdown + format_report_json functions
- `python/tests/__init__.py` - Test package init
- `python/tests/test_validation_types.py` - 13 tests for dataclass construction, immutability, defaults
- `python/tests/test_pylint_runner.py` - 11 tests for command construction, JSON2 parsing, error handling
- `python/tests/test_report.py` - 12 tests for markdown/JSON output in all report states

## Decisions Made
- Used tuples instead of lists for frozen dataclass fields to maintain immutability (lists are mutable and would break frozen=True contract)
- Added `# noqa: F401` annotations to `__init__.py` re-exports because a ruff PostToolUse hook was automatically stripping "unused" imports that serve as the package's public API
- Implemented recursive `_tuples_to_lists()` conversion in `format_report_json()` because `dataclasses.asdict()` preserves tuples, which need to be lists for JSON compatibility

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed tuple-to-list conversion in format_report_json**
- **Found during:** Task 2 (report formatter implementation)
- **Issue:** `dataclasses.asdict()` preserves tuples but JSON expects lists. Test `test_format_report_json_empty` failed: `assert () == []`
- **Fix:** Added `_tuples_to_lists()` recursive converter applied to `dataclasses.asdict()` output
- **Files modified:** python/src/odoo_gen_utils/validation/report.py
- **Verification:** All 12 report tests pass including JSON roundtrip
- **Committed in:** 49e922a (Task 2 commit)

**2. [Rule 3 - Blocking] Fixed linter stripping __init__.py re-exports**
- **Found during:** Task 2 (updating __init__.py with report exports)
- **Issue:** PostToolUse ruff hook was removing import statements from __init__.py that it classified as unused (F401), destroying the package's public API surface
- **Fix:** Added `# noqa: F401` annotations to each re-export line and `__all__` list
- **Files modified:** python/src/odoo_gen_utils/validation/__init__.py
- **Verification:** File content stable after writes, imports work from package
- **Committed in:** 49e922a (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
- Pre-existing test files (`test_docker_runner.py`, `test_log_parser.py`) from Plan 02 scope cause collection errors when running `pytest tests/` broadly. Scoped test runs to plan-specific files only. These files are out of scope for Plan 01.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Validation types and pylint runner ready for Plan 02 (Docker runner) to use
- Report formatter ready for Plan 03 (CLI wiring) to invoke
- pylint-odoo 10.0.1 installed and importable in the extension venv

## Self-Check: PASSED

All 9 created files verified on disk. Both task commits (0264c7f, 49e922a) verified in git log.

---
*Phase: 03-validation-infrastructure*
*Completed: 2026-03-02*
