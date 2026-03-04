---
phase: 13-golden-path-regression-testing
plan: 01
subsystem: testing
tags: [pytest, docker, e2e, regression, odoo, jinja2, templates]

# Dependency graph
requires:
  - phase: 12-template-correctness-auto-fix
    provides: inherit_list, needs_api context vars, clean manifest/test templates
provides:
  - Golden path E2E regression test proving full pipeline (render + Docker install + Docker tests)
  - GOLDEN_PATH_SPEC constant exercising mail dependency, computed fields, and plain models
  - Module-scoped rendered_module fixture for shared render-once pattern
affects: [ci-integration, future-template-changes]

# Tech tracking
tech-stack:
  added: []
  patterns: [module-scoped-fixture-for-docker-e2e, staged-test-dependency-via-shared-fixture]

key-files:
  created:
    - python/tests/test_golden_path.py
  modified: []

key-decisions:
  - "depends=['base', 'mail'] (not 'hr') -- regression testing OUR templates, not Odoo dependency resolution"
  - "Module-scoped fixture renders once, shared by all 3 tests -- avoids triple render cost"
  - "test_golden_path_render has no skip_no_docker -- render does not need Docker"

patterns-established:
  - "Golden path spec as module-level constant for reproducible regression testing"
  - "Staged E2E tests: render -> install -> test, with automatic skip on fixture failure"

requirements-completed: [REGR-01, REGR-02]

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 13 Plan 01: Golden Path Regression Testing Summary

**E2E regression test renders hr_training module with mail/computed fields, Docker-installs in Odoo 17.0, and asserts all generated Odoo tests pass**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T17:41:46Z
- **Completed:** 2026-03-03T17:44:26Z
- **Tasks:** 2
- **Files created:** 1

## Accomplishments
- Golden path test renders hr_training module exercising mail dependency, computed fields (needs_api=True), and plain models (needs_api=False)
- All 15 expected files verified: manifest, models, views, security, and tests
- Docker install passes with InstallResult.success=True and no ImportError in logs
- Docker test execution passes: all generated Odoo tests return TestResult.passed=True with non-empty names
- Full project test suite (303 tests) passes with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create golden path E2E regression test** (TDD) - `e0a0c0f` (test)
2. **Task 2: Verify full suite and pyproject.toml** - No file changes (verification-only task)

## Files Created/Modified
- `python/tests/test_golden_path.py` - Golden path E2E regression test with 3 staged test methods, module-scoped fixture, and GOLDEN_PATH_SPEC constant

## Decisions Made
- Used `depends=["base", "mail"]` without `"hr"` -- the goal is regression testing our templates, not Odoo's dependency resolution. "base" + "mail" exercise all Phase 12 fixes.
- Module-scoped `rendered_module` fixture renders once and shares across all 3 tests, avoiding redundant Docker overhead.
- `test_golden_path_render` has no `@skip_no_docker` since rendering does not require Docker.
- Tests rely on alphabetical ordering (docker_install before docker_tests) and shared fixture for implicit dependency.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Golden path regression test is the "canary in the coal mine" for template quality
- Any future template change that breaks Odoo installation or test execution will be caught by this single test
- v1.2 Template Quality milestone is complete (Phases 12 + 13 done)

## Self-Check: PASSED

All 1 file verified present. All 1 commit verified in git log.

---
*Phase: 13-golden-path-regression-testing*
*Completed: 2026-03-03*
