---
phase: 08-search-fork-extend
plan: 01
subsystem: search
tags: [chromadb, pygithub, vector-index, ast-literal-eval, click-cli, oca]

# Dependency graph
requires:
  - phase: 01-gsd-extension
    provides: Python utility package with Click CLI and pyproject.toml
provides:
  - ChromaDB vector index infrastructure for OCA module search
  - build-index and index-status CLI commands
  - IndexEntry and IndexStatus frozen dataclasses
  - Safe manifest parsing via ast.literal_eval
  - GitHub token detection (env var + gh CLI)
  - pyproject.toml [search] optional-dependencies with CPU torch config
affects: [08-02 search query, 08-03 fork-extend]

# Tech tracking
tech-stack:
  added: [chromadb, sentence-transformers, torch, PyGithub, gitpython]
  patterns: [lazy import for optional dependencies, frozen dataclass types, ChromaDB persistent client]

key-files:
  created:
    - python/src/odoo_gen_utils/search/__init__.py
    - python/src/odoo_gen_utils/search/types.py
    - python/src/odoo_gen_utils/search/index.py
    - python/tests/test_search_index.py
    - python/tests/test_cli_build_index.py
    - commands/index.md
  modified:
    - python/pyproject.toml
    - python/src/odoo_gen_utils/cli.py

key-decisions:
  - "ast.literal_eval for manifest parsing -- safe against malicious manifests, never uses eval()"
  - "get_github_token is public API (no underscore) -- exported from search/__init__.py for CLI and external use"
  - "Lazy imports for chromadb and github -- CLI loads without search dependencies installed"
  - "CPU-only torch via uv index config -- avoids pulling full CUDA toolkit"

patterns-established:
  - "Optional dependency pattern: try/except import with None fallback for heavy packages"
  - "ChromaDB collection naming: 'odoo_modules' with cosine HNSW space"
  - "Index entry ID format: 'oca/{repo_name}/{module_name}'"

requirements-completed: [FORK-04, SRCH-01, SRCH-02]

# Metrics
duration: 5min
completed: 2026-03-03
---

# Phase 8 Plan 1: Vector Index Infrastructure Summary

**ChromaDB vector index with OCA repo crawl via PyGithub, safe manifest parsing, build-index/index-status CLI commands, and CPU-only torch config**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-03T00:45:35Z
- **Completed:** 2026-03-03T00:50:59Z
- **Tasks:** 2 (both TDD with RED/GREEN phases)
- **Files modified:** 8

## Accomplishments
- Complete search package (types.py, index.py, __init__.py) with OCA crawl, manifest parsing, and ChromaDB upsert pipeline
- build-index and index-status CLI commands with auth error handling matching CONTEXT.md Decision D exactly
- 21 tests total (17 unit + 4 CLI) all passing, covering index build, status, auth, manifest parsing, document text building
- pyproject.toml with [search] optional-dependencies and CPU-only torch index configuration
- GSD command stub commands/index.md for /odoo-gen:index registration

## Task Commits

Each task was committed atomically:

1. **Task 1: Types, index module, and TDD test scaffold**
   - `5ffc03b` (test: RED phase - failing tests for search index)
   - `3c1a959` (feat: GREEN phase - implement search index with OCA crawl)
2. **Task 2: CLI commands (build-index, index-status) and index.md command stub**
   - `7b4a6a8` (test: RED phase - failing CLI tests)
   - `0e665f0` (feat: GREEN phase - CLI commands and command stub)

_TDD tasks have RED (test) and GREEN (feat) commits_

## Files Created/Modified
- `python/src/odoo_gen_utils/search/__init__.py` - Public API exports for search package
- `python/src/odoo_gen_utils/search/types.py` - Frozen dataclasses: IndexEntry, IndexStatus
- `python/src/odoo_gen_utils/search/index.py` - OCA crawl, manifest parse, ChromaDB upsert pipeline (185 lines)
- `python/tests/test_search_index.py` - 17 tests for index build, entry structure, auth, manifest parsing
- `python/tests/test_cli_build_index.py` - 4 tests for build-index and index-status CLI commands
- `python/pyproject.toml` - [search] optional-dependencies + CPU torch index config
- `python/src/odoo_gen_utils/cli.py` - build-index and index-status Click commands
- `commands/index.md` - GSD command stub for /odoo-gen:index

## Decisions Made
- `ast.literal_eval` for manifest parsing -- safe against malicious manifests, never uses `eval()`
- `get_github_token` is public API (no underscore prefix) -- exported from `search/__init__.py` for CLI and external consumers
- Lazy imports for `chromadb` and `github` modules -- CLI loads without search dependencies installed
- CPU-only torch via `[[tool.uv.index]]` config with explicit pytorch-cpu URL -- avoids pulling full CUDA toolkit (~2GB savings)
- ChromaDB collection metadata stores `hnsw:space: cosine` and `last_built` timestamp

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. Search dependencies are optional (`pip install odoo-gen-utils[search]`).

## Next Phase Readiness
- Search index infrastructure complete, ready for Plan 08-02 (search query flow with ChromaDB semantic search)
- `build_oca_index`, `get_index_status`, `get_github_token` all available as public API
- ChromaDB collection uses cosine similarity, ready for query integration
- No blockers for next plan

---
*Phase: 08-search-fork-extend*
*Completed: 2026-03-03*
