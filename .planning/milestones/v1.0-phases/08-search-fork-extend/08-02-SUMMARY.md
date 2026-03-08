---
phase: 08-search-fork-extend
plan: 02
subsystem: search
tags: [chromadb, semantic-search, cosine-similarity, github-fallback, gh-cli, click-cli, gap-analysis, spec-refinement]

# Dependency graph
requires:
  - phase: 08-search-fork-extend
    provides: ChromaDB vector index infrastructure, IndexEntry/IndexStatus types, build_oca_index, DEFAULT_DB_PATH
provides:
  - SearchResult frozen dataclass for query results
  - search_modules() semantic search function with cosine similarity scoring
  - GitHub fallback via `gh search repos` subprocess
  - format_results_text and format_results_json output formatters
  - search-modules CLI command with --limit, --json, --db-path, --github flags
  - odoo-search agent with 5-phase gap analysis workflow
  - Activated /odoo-gen:search command wired to odoo-search agent
affects: [08-03 fork-extend]

# Tech tracking
tech-stack:
  added: []
  patterns: [cosine distance to similarity conversion, subprocess-based GitHub CLI fallback, auto-build on first use, auto-fallback when OCA empty]

key-files:
  created:
    - python/src/odoo_gen_utils/search/query.py
    - python/tests/test_search_query.py
    - agents/odoo-search.md
  modified:
    - python/src/odoo_gen_utils/search/__init__.py
    - python/src/odoo_gen_utils/cli.py
    - commands/search.md

key-decisions:
  - "Cosine distance to similarity: 1.0 - (distance / 2.0) for 0.0-1.0 range"
  - "GitHub fallback results get fixed relevance_score=0.5 (unranked)"
  - "Auto-fallback to GitHub when OCA returns 0 results, even without --github flag"
  - "Refined spec overwrites original spec.json path (REFN-03 source of truth for all downstream)"
  - "Gap analysis runs only on selected result, not all 5 upfront (Decision A)"
  - "Follow-up queries independently re-query ChromaDB, no session state (Decision A)"

patterns-established:
  - "subprocess-based CLI fallback: call gh search repos --json for GitHub results"
  - "Auto-build pattern: check index status, build if empty before first search"
  - "Agent 5-phase workflow: search -> selection -> gap analysis -> spec refinement -> decision"

requirements-completed: [SRCH-01, SRCH-03, SRCH-04, SRCH-05, REFN-01, REFN-02, REFN-03]

# Metrics
duration: 4min
completed: 2026-03-03
---

# Phase 8 Plan 2: Search Query Flow & Gap Analysis Agent Summary

**Semantic search query with cosine similarity scoring, GitHub CLI fallback, gap analysis agent, and activated /odoo-gen:search command**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-03T00:54:08Z
- **Completed:** 2026-03-03T00:58:39Z
- **Tasks:** 2 (Task 1 TDD with RED/GREEN phases, Task 2 auto)
- **Files modified:** 6

## Accomplishments
- SearchResult frozen dataclass and search_modules() function with ChromaDB semantic search, cosine distance-to-similarity conversion, and default 5-result limit
- GitHub fallback via `gh search repos` subprocess when OCA results are empty (SRCH-01), plus auto-fallback in CLI even without --github flag
- odoo-search agent with complete 5-phase workflow: search, selection, gap analysis (SRCH-04), spec refinement (REFN-01/02/03), and decision (SRCH-05)
- 14 tests covering all query behaviors including GitHub fallback, cosine conversion, empty query validation, JSON output

## Task Commits

Each task was committed atomically:

1. **Task 1: Search query module with TDD tests (including GitHub fallback)**
   - `353cd91` (test: RED phase - failing tests for search query module)
   - `53d8c2f` (feat: GREEN phase - implement search query with GitHub fallback)
2. **Task 2: search-modules CLI command, odoo-search agent, activated search.md**
   - `af2b0bb` (feat: CLI command + agent + activated command)

_TDD Task 1 has RED (test) and GREEN (feat) commits_

## Files Created/Modified
- `python/src/odoo_gen_utils/search/query.py` - SearchResult dataclass, search_modules(), GitHub fallback, format functions (224 lines)
- `python/tests/test_search_query.py` - 14 tests covering all query behaviors (312 lines)
- `python/src/odoo_gen_utils/search/__init__.py` - Added exports: SearchResult, search_modules, format_results_text, format_results_json
- `python/src/odoo_gen_utils/cli.py` - Added search-modules Click command with --limit, --json, --db-path, --github flags
- `agents/odoo-search.md` - 5-phase agent: search, selection, gap analysis, spec refinement, decision (168 lines)
- `commands/search.md` - Activated command wired to odoo-search agent (replaced stub)

## Decisions Made
- Cosine distance to similarity conversion formula: `1.0 - (distance / 2.0)` maps ChromaDB's 0.0-2.0 range to 0.0-1.0 similarity
- GitHub fallback results get a fixed `relevance_score=0.5` since they are not semantically ranked
- Auto-fallback to GitHub when OCA returns 0 results happens in the CLI layer, even without `--github` flag (per Decision B)
- Refined spec overwrites the original spec.json path -- REFN-03 makes it the new source of truth for all downstream generation
- Gap analysis runs only on the user-selected result, not on all 5 results upfront (per Decision A)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - search depends on the index built in Plan 08-01. The search-modules command auto-builds the index on first use if it does not exist.

## Next Phase Readiness
- Search query flow complete, ready for Plan 08-03 (fork-extend command and companion module generation)
- odoo-search agent provides gap analysis that feeds into the fork workflow
- SearchResult and format functions available as public API
- CLI command registered and working with all options
- No blockers for next plan

## Self-Check: PASSED

All 6 files verified present. All 3 commits verified in git log.

---
*Phase: 08-search-fork-extend*
*Completed: 2026-03-03*
