---
phase: 10-environment-dependencies
plan: 01
subsystem: testing
tags: [chromadb, onnx, pytest, e2e, github-api, dependency-cleanup]

# Dependency graph
requires:
  - phase: 08-search-fork-extend
    provides: "search/index.py, search/query.py, ChromaDB pipeline"
provides:
  - "Cleaned [search] extras without sentence-transformers/torch (~200MB savings)"
  - "E2E test infrastructure with e2e and e2e_slow pytest markers"
  - "test_e2e_github.py with 6 tests covering GitHub API integration (DEBT-01)"
  - "test_e2e_index.py with 5 tests covering ChromaDB pipeline (DEBT-02)"
  - "Sentinel test proving sentence-transformers is not required"
affects: [10-02-wizard, 11-live-testing]

# Tech tracking
tech-stack:
  added: []
  patterns: ["e2e test skip pattern with GITHUB_TOKEN guard", "session-scoped fixture for shared ChromaDB index"]

key-files:
  created:
    - python/tests/test_e2e_github.py
    - python/tests/test_e2e_index.py
  modified:
    - python/pyproject.toml

key-decisions:
  - "Removed sentence-transformers and torch from [search] extras -- ChromaDB uses built-in ONNX embedding, saving ~200MB"
  - "Used module-level pytestmark for e2e marker instead of per-test decorators"
  - "Session-scoped e2e_index_db fixture in test_e2e_github.py, module-scoped in test_e2e_index.py"

patterns-established:
  - "E2E skip pattern: pytestmark = pytest.mark.e2e + skip_no_token decorator for GITHUB_TOKEN-dependent tests"
  - "Sentinel test pattern: test_sentence_transformers_not_installed guards against accidental re-addition"
  - "ChromaDB ONNX verification: test_chromadb_onnx_embedding_without_sentence_transformers proves pipeline independence"

requirements-completed: [DEBT-01, DEBT-02]

# Metrics
duration: 5min
completed: 2026-03-03
---

# Phase 10 Plan 01: Remove Unused Deps and E2E Test Infrastructure Summary

**Removed sentence-transformers/torch from [search] extras (~200MB savings) and created 11 E2E tests covering GitHub API (DEBT-01) and ChromaDB pipeline (DEBT-02) with graceful skip when GITHUB_TOKEN unavailable**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-03T09:15:09Z
- **Completed:** 2026-03-03T09:20:41Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Removed sentence-transformers>=5.2 and torch>=2.6 from [search] extras, saving ~200MB install size
- Removed [[tool.uv.index]] pytorch-cpu and [tool.uv.sources] sections (only needed for torch)
- Added e2e and e2e_slow pytest markers to pyproject.toml
- Created test_e2e_github.py with 6 tests covering DEBT-01 (token check, index build, status, search, GitHub fallback, full build)
- Created test_e2e_index.py with 5 tests covering DEBT-02 (sentinel, ONNX embedding, persistent DB, status, relevance)
- Verified ChromaDB ONNX embedding works independently without sentence-transformers
- All 243 original tests continue to pass (plus 2 new non-skip tests = 246 passed, 9 skipped)

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove unused sentence-transformers/torch deps and add E2E markers** - `7e4b075` (chore)
2. **Task 2: Create E2E tests for GitHub API integration (DEBT-01)** - `7894055` (test)
3. **Task 3: Create E2E tests for ChromaDB index pipeline (DEBT-02)** - `f2bb7b1` (test)

## Files Created/Modified
- `python/pyproject.toml` - Removed sentence-transformers/torch deps, removed pytorch-cpu index config, added e2e/e2e_slow markers
- `python/tests/test_e2e_github.py` - 6 E2E tests for GitHub API integration (DEBT-01)
- `python/tests/test_e2e_index.py` - 5 E2E tests for ChromaDB index pipeline (DEBT-02)

## Decisions Made
- **Removed sentence-transformers and torch**: Confirmed via grep that zero code paths import either library. ChromaDB uses its own ONNX all-MiniLM-L6-v2 model (~22MB vs ~200MB for torch). Sentinel test guards against re-addition.
- **Module-level pytestmark**: Used `pytestmark = pytest.mark.e2e` at module level for cleaner marking, with `skip_no_token` decorator for tests needing GITHUB_TOKEN.
- **Separate fixture scopes**: session-scoped in test_e2e_github.py (shared across full test file), module-scoped in test_e2e_index.py (isolated for index-focused tests).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **Pre-existing test_wizard.py import error**: `tests/test_wizard.py` imports `odoo_gen_utils.search.wizard` which does not exist yet (planned for Plan 10-02). All test runs use `--ignore=tests/test_wizard.py`. Logged to deferred-items.md. Not caused by this plan's changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- E2E test infrastructure is in place with e2e and e2e_slow markers
- Plan 10-02 (auth setup wizard) can proceed -- test_wizard.py is already written, just needs the implementation module
- Phase 11 can use the same e2e test patterns for Docker live validation

## Self-Check: PASSED

- [x] python/tests/test_e2e_github.py exists
- [x] python/tests/test_e2e_index.py exists
- [x] 10-01-SUMMARY.md exists
- [x] Commit 7e4b075 exists (Task 1)
- [x] Commit 7894055 exists (Task 2)
- [x] Commit f2bb7b1 exists (Task 3)

---
*Phase: 10-environment-dependencies*
*Completed: 2026-03-03*
