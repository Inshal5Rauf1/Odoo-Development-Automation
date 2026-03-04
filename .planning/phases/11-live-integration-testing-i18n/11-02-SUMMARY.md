---
phase: 11-live-integration-testing-i18n
plan: 02
subsystem: testing
tags: [python, ast, i18n, odoo, pot-generation, unit-tests, tdd]

# Dependency graph
requires:
  - phase: 10-environment-dependencies
    provides: Working test infrastructure, pyproject.toml with pytest markers
provides:
  - Extended extract_python_strings() that detects fields.*(string=...) patterns
  - 9 new unit tests in TestExtractFieldStrings class covering all field types
  - Fix for pre-existing pytest fixture collection error (norecursedirs)
affects:
  - Any future plan touching i18n_extractor.py or pot generation
  - Docker integration tests that use fixture modules

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD: RED (failing tests) committed before GREEN (implementation)"
    - "AST if/elif pattern to handle both ast.Name and ast.Attribute func nodes in same walk loop"
    - "pytest norecursedirs to exclude Odoo fixture modules from test collection"

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/i18n_extractor.py
    - python/tests/test_i18n_extractor.py
    - python/pyproject.toml

key-decisions:
  - "Used if/elif structure (not separate if blocks) to prevent a Call node from matching both Pattern 1 and Pattern 2 simultaneously"
  - "Added norecursedirs to pyproject.toml to fix pre-existing fixture collection error (tests/fixtures/docker_test_module imports odoo at import time)"
  - "Placed TestExtractFieldStrings between TestExtractPythonStrings and TestExtractXmlStrings for logical grouping"

patterns-established:
  - "AST Pattern 2: isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'fields' detects fields.*(keyword=...) calls"

requirements-completed: [DEBT-04]

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 11 Plan 02: i18n Field String= Extraction Summary

**AST walker extended to detect `fields.*(string="Label")` patterns, resolving DEBT-04: Odoo field labels now extracted into .pot files via 9 new TDD-verified unit tests**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T13:47:17Z
- **Completed:** 2026-03-03T13:50:07Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Extended `extract_python_strings()` AST walker with Pattern 2: `fields.*(string="text")` keyword argument detection
- Added `TestExtractFieldStrings` class with 9 unit tests covering all Odoo field types (Char, Many2one, Selection, Text, Boolean, Float)
- Verified TDD cycle: RED commit (fa9d48f) then GREEN commit (759ef23) — tests failed before implementation, passed after
- Fixed pre-existing pytest fixture collection error: `tests/fixtures/docker_test_module` was being imported by pytest, triggering `ModuleNotFoundError: No module named 'odoo'`
- All 263 existing tests continue to pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add field string= unit tests (RED phase)** - `fa9d48f` (test)
2. **Task 2: Extend extract_python_strings() AST walker (GREEN phase)** - `759ef23` (feat)

_Note: TDD tasks have two commits — test commit (RED) then implementation commit (GREEN)_

## Files Created/Modified
- `python/src/odoo_gen_utils/i18n_extractor.py` - Extended with fields.*(string=...) AST pattern, updated docstring
- `python/tests/test_i18n_extractor.py` - Added TestExtractFieldStrings class with 9 tests
- `python/pyproject.toml` - Added norecursedirs to exclude docker fixture module from pytest collection

## Decisions Made
- Used `if/elif` structure (not two separate `if` blocks) to prevent a single AST Call node from matching both the `_()` pattern and the `fields.*()` pattern simultaneously
- Added `norecursedirs = ["tests/fixtures/docker_test_module"]` to `pyproject.toml` to fix the pre-existing fixture collection error where the Odoo module fixture imports `from odoo import fields, models` at module load time
- Placed `TestExtractFieldStrings` between `TestExtractPythonStrings` and `TestExtractXmlStrings` for logical grouping (Python extraction tests together)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed pre-existing pytest fixture collection error**
- **Found during:** Task 2 (full suite regression check)
- **Issue:** `tests/fixtures/docker_test_module/__init__.py` auto-imports `models` which imports `test_model.py` which imports `from odoo import fields, models`. When pytest recursively collects `tests/`, it discovers this directory and tries to import it, causing `ModuleNotFoundError: No module named 'odoo'`. The existing `tests/fixtures/conftest.py` with `collect_ignore_glob` did not prevent the import-chain traversal.
- **Fix:** Added `norecursedirs = ["tests/fixtures/docker_test_module"]` to `[tool.pytest.ini_options]` in `pyproject.toml`. This prevents pytest from descending into the Odoo module fixture directory entirely.
- **Files modified:** `python/pyproject.toml`
- **Verification:** `uv run pytest tests/ -m "not docker" -x -q` now shows `263 passed, 9 skipped`
- **Committed in:** `759ef23` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix necessary to confirm "no regressions" success criterion. No scope creep — fix targeted the specific pre-existing issue that prevented full suite execution.

## Issues Encountered
- The `tests/fixtures/conftest.py` with `collect_ignore_glob = ["docker_test_module/**/*.py"]` did not prevent pytest from following `__init__.py` import chains. The `norecursedirs` approach at the `pyproject.toml` level is the correct solution.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DEBT-04 resolved: `extract_python_strings()` now extracts both `_()` calls and `fields.*(string=...)` patterns
- `.pot` file generation via `generate_pot()` will automatically include field label translations (deduplication of shared msgids already handled by existing code)
- Phase 11 Plan 01 (Docker integration tests) is the companion plan — both plans are independent (wave: 1)

## Self-Check: PASSED

- FOUND: python/src/odoo_gen_utils/i18n_extractor.py
- FOUND: python/tests/test_i18n_extractor.py
- FOUND: .planning/phases/11-live-integration-testing-i18n/11-02-SUMMARY.md
- FOUND commit: fa9d48f (test RED phase)
- FOUND commit: 759ef23 (feat GREEN phase + fix)

---
*Phase: 11-live-integration-testing-i18n*
*Completed: 2026-03-03*
