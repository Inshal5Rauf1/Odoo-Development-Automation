---
phase: 11-live-integration-testing-i18n
plan: 01
subsystem: testing
tags: [docker, integration-tests, odoo-fixture, pytest-markers, live-validation]

# Dependency graph
requires:
  - phase: 10-environment-dependencies
    provides: "E2E test infrastructure patterns, pytest marker conventions"
  - "python/src/odoo_gen_utils/validation/docker_runner.py (existing)"
provides:
  - "Odoo 17.0 fixture module at tests/fixtures/docker_test_module/ for Docker integration testing"
  - "Live Docker integration tests (test_docker_integration.py) with 3 unmocked test functions"
  - "docker pytest marker registered in pyproject.toml"
  - "fixtures/conftest.py preventing Odoo-import errors during pytest collection"
affects: [11-02-i18n-extraction]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "docker skip pattern: pytestmark = pytest.mark.docker + skip_no_docker decorator using check_docker_available()"
    - "Fixture isolation: conftest.py with collect_ignore_glob to prevent Odoo module import during collection"
    - "Dual-purpose fixture: fields.Char/Text/Boolean/Many2one/Selection with string= attrs serves both Docker and i18n testing"

key-files:
  created:
    - python/tests/fixtures/docker_test_module/__init__.py
    - python/tests/fixtures/docker_test_module/__manifest__.py
    - python/tests/fixtures/docker_test_module/models/__init__.py
    - python/tests/fixtures/docker_test_module/models/test_model.py
    - python/tests/fixtures/docker_test_module/security/ir.model.access.csv
    - python/tests/fixtures/docker_test_module/tests/__init__.py
    - python/tests/fixtures/docker_test_module/tests/test_basic.py
    - python/tests/fixtures/conftest.py
    - python/tests/test_docker_integration.py
  modified:
    - python/pyproject.toml

key-decisions:
  - "Added fixtures/conftest.py with collect_ignore_glob to prevent pytest from trying to import Odoo-dependent fixture files"
  - "Used pytestmark = pytest.mark.docker at module level plus per-test @skip_no_docker decorator for dual-layer protection"
  - "Fixture model includes 5 field types with string= attributes to serve Plan 02 i18n extraction testing"

patterns-established:
  - "Docker skip pattern: check_docker_available() in skipif decorator, mirroring e2e GITHUB_TOKEN pattern from Phase 10"
  - "Fixture isolation: conftest.py with collect_ignore_glob prevents Odoo import errors without modifying pyproject.toml norecursedirs"

requirements-completed: [DEBT-03]

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 11 Plan 01: Docker Integration Tests and Fixture Module Summary

**Minimal Odoo 17.0 fixture module (5 field types) and 3 unmocked live Docker integration tests validating docker_install_module() and docker_run_tests() against real containers, with graceful skip when Docker daemon is unavailable**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T13:47:26Z
- **Completed:** 2026-03-03T13:50:26Z
- **Tasks:** 2
- **Files modified:** 10 (9 created, 1 modified)

## Accomplishments

- Created minimal but realistic Odoo 17.0 fixture module at `python/tests/fixtures/docker_test_module/`
- Fixture model `DockerTestModel` has 5 field types (Char, Text, Boolean, Many2one, Selection) all with `string=` attributes, serving dual purpose for Plan 02 i18n extraction testing
- Security CSV grants full CRUD to base.group_user, preventing AccessError in integration tests
- TransactionCase test (`test_basic.py`) validates record creation, field defaults
- Registered `docker` pytest marker in `pyproject.toml [tool.pytest.ini_options]`
- Created `python/tests/test_docker_integration.py` with 3 unmocked Docker integration tests
- Tests use `pytestmark = pytest.mark.docker` (module-level) and `@skip_no_docker` (per-test) for graceful skip
- Auto-fixed pytest collection error: added `fixtures/conftest.py` with `collect_ignore_glob` to prevent Odoo import failures
- All 263 existing tests continue to pass without regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create fixture module and register docker marker** - `0ef9b60` (feat)
2. **Task 2: Create live Docker integration tests** - `e35fab0` (feat)

## Files Created/Modified

- `python/pyproject.toml` - Added docker marker to [tool.pytest.ini_options]
- `python/tests/fixtures/conftest.py` - Prevents pytest from collecting Odoo-dependent fixture files (auto-fix)
- `python/tests/fixtures/docker_test_module/__init__.py` - Module root init
- `python/tests/fixtures/docker_test_module/__manifest__.py` - Odoo 17.0 module manifest
- `python/tests/fixtures/docker_test_module/models/__init__.py` - Models init
- `python/tests/fixtures/docker_test_module/models/test_model.py` - DockerTestModel with 5 field types
- `python/tests/fixtures/docker_test_module/security/ir.model.access.csv` - Full CRUD access rules
- `python/tests/fixtures/docker_test_module/tests/__init__.py` - Tests init
- `python/tests/fixtures/docker_test_module/tests/test_basic.py` - TransactionCase test
- `python/tests/test_docker_integration.py` - 3 unmocked Docker integration tests

## Decisions Made

- **fixtures/conftest.py auto-fix**: When pytest tried to import `docker_test_module/__init__.py`, it triggered `from odoo import fields, models` which fails outside Odoo. Fixed by adding `collect_ignore_glob = ["docker_test_module/**/*.py"]` in a conftest at the fixtures level. This is cleaner than modifying pyproject.toml `norecursedirs`.
- **Dual-layer docker skip**: `pytestmark = pytest.mark.docker` marks all tests for `-m "not docker"` filtering; `@skip_no_docker` individually skips each test when Docker daemon is unavailable. Mirrors Phase 10's e2e pattern.
- **Dual-purpose fixture model**: Fields with `string=` attributes on all 5 field types ensures Plan 02 (i18n extraction) can reuse this same fixture without modification.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pytest collection error from Odoo imports in fixture module**
- **Found during:** Task 1 verification
- **Issue:** `uv run pytest tests/ -m "not docker"` failed with `ModuleNotFoundError: No module named 'odoo'` because pytest tried to collect and import `docker_test_module/models/test_model.py` and `docker_test_module/tests/test_basic.py`
- **Fix:** Created `python/tests/fixtures/conftest.py` with `collect_ignore_glob = ["docker_test_module/**/*.py"]` to instruct pytest to skip collecting files inside the Odoo fixture module
- **Files modified:** `python/tests/fixtures/conftest.py` (created)
- **Commit:** Included in Task 1 commit `0ef9b60`

## User Setup Required

When Docker IS available, run live validation with:
```bash
cd python && uv run pytest tests/ -m docker -v
```

Tests skip automatically when Docker daemon is not running.

## Next Phase Readiness

- Plan 11-02 (i18n extraction) can reuse `docker_test_module` fixture directly — all fields have `string=` attributes ready for extraction testing
- Docker integration test pattern established — follow same `@skip_no_docker` + `pytestmark = pytest.mark.docker` convention

## Self-Check: PASSED

- [x] `python/tests/fixtures/docker_test_module/__manifest__.py` exists
- [x] `python/tests/fixtures/docker_test_module/models/test_model.py` contains `fields.Char`
- [x] `python/tests/fixtures/docker_test_module/security/ir.model.access.csv` contains `access_docker_test_model`
- [x] `python/tests/test_docker_integration.py` contains `pytest.mark.docker`
- [x] `python/pyproject.toml` contains `docker:`
- [x] Commit `0ef9b60` exists (Task 1)
- [x] Commit `e35fab0` exists (Task 2)
- [x] 263 existing tests pass, 3 docker tests collected

---
*Phase: 11-live-integration-testing-i18n*
*Completed: 2026-03-03*
