---
phase: 08-search-fork-extend
verified: 2026-03-03T07:30:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Run odoo-gen-utils build-index with a real GITHUB_TOKEN against live OCA repos"
    expected: "Index builds in ~3-5 minutes, modules stored in ChromaDB at ~/.local/share/odoo-gen/chromadb/"
    why_human: "Requires live GitHub auth and OCA network access; can't mock real crawl in tests"
  - test: "Run odoo-gen-utils search-modules 'customer invoicing' and review result quality"
    expected: "5 ranked results with relevance scores, matching modules returned, OCA badges present"
    why_human: "Semantic search quality requires subjective evaluation with real index"
  - test: "Run odoo-gen-utils extend-module sale_order_type --repo sale-workflow and inspect output"
    expected: "Module cloned via sparse checkout, companion sale_order_type_ext/ created, analysis output shown"
    why_human: "Requires live git clone from GitHub; test suite mocks subprocess.run"
---

# Phase 8: Search & Fork-Extend Verification Report

**Phase Goal:** User can search for existing Odoo modules, see how they overlap with their need, and fork-and-extend a match instead of building from scratch
**Verified:** 2026-03-03T07:30:00Z
**Status:** PASSED
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | odoo-gen-utils build-index crawls OCA repos via PyGithub and stores module metadata in ChromaDB | VERIFIED | `index.py:133` creates `chromadb.PersistentClient`, `index.py:139` uses `Github(token).get_organization("OCA")`, upserts to `odoo_modules` collection |
| 2 | odoo-gen-utils index-status reports index age, module count, and storage location | VERIFIED | `cli.py:439` calls `get_index_status(db_path)`, human-readable output includes `module_count`, `last_built`, `db_path`; JSON output available |
| 3 | Index build fails with clear auth error when no GITHUB_TOKEN or gh auth token available | VERIFIED | `cli.py:406-412` prints exact auth error: "Index build requires GitHub authentication. Run: gh auth login..." then `sys.exit(1)` |
| 4 | search optional-dependencies install chromadb, sentence-transformers, torch (CPU-only), PyGithub, gitpython | VERIFIED | `pyproject.toml:20-26` has `[project.optional-dependencies] search = [...]` with all 5 packages; `pyproject.toml:38-44` has `[[tool.uv.index]]` pytorch-cpu |
| 5 | Index entries contain module_name, summary, category, depends, oca_repo, github_url metadata | VERIFIED | `index.py:204-216` upserts metadata dict with all required fields: `module_name`, `oca_repo`, `org`, `category`, `depends`, `version`, `license`, `summary`, `url`, `stars`, `last_pushed` |
| 6 | odoo-gen-utils search-modules returns 5 ranked results with name, score, OCA badge, summary | VERIFIED | `query.py:148-208` - default `n_results=5`, sorted by `relevance_score` descending; `format_results_text` produces `[score%] name (org/repo) [badge] + summary + url` |
| 7 | Results are sorted by relevance score (highest first), using cosine similarity converted to 0.0-1.0 | VERIFIED | `query.py:51` formula `1.0 - (distance / 2.0)` converts ChromaDB cosine distance; `query.py:205-206` sorts descending |
| 8 | search-modules --github flag falls back to gh search repos when OCA results are empty | VERIFIED | `query.py:202-203` checks `if not results and github_fallback`, calls `_github_search_fallback()`; `cli.py:463-468` registers `--github` flag |
| 9 | Gap analysis runs only on the selected result; refined spec replaces original spec.json (REFN-03) | VERIFIED | `agents/odoo-search.md:53` "User picks a result number: Proceed to Phase 3 for that module"; `cli.py:610` overwrites original spec.json; `agents/odoo-search.md:161` documents REFN-03 |
| 10 | System clones a single OCA module via git sparse checkout (not entire repo) | VERIFIED | `fork.py:41-52` runs `git clone --no-checkout --filter=blob:none --sparse -b {branch}`, then sparse-checkout set, then checkout |
| 11 | System analyzes forked module structure: models, fields, views, security groups, data files | VERIFIED | `analyzer.py:217-282` - AST parsing for models/fields (`_extract_models_from_file`), XML for views (`_extract_view_types`), XML for security groups (`_extract_security_groups`), manifest for data files |
| 12 | Companion _ext module is generated (never modifies original); delta code uses _inherit and xpath | VERIFIED | `fork.py:69-95` `setup_companion_dir()` creates `{module}_ext/`; `agents/odoo-extend.md:13` "CRITICAL RULE: NEVER modify files in the original cloned module directory"; agent Phase 3 documents `_inherit` and `xpath` patterns |

**Score:** 12/12 truths verified

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python/pyproject.toml` | `[search]` optional-dependencies + CPU torch index config | VERIFIED | Lines 20-44: chromadb, sentence-transformers, torch, PyGithub, gitpython; pytorch-cpu uv index config |
| `python/src/odoo_gen_utils/search/__init__.py` | Public API exports for search package | VERIFIED | 41 lines; exports all 14 public symbols including `build_oca_index`, `get_github_token`, `get_index_status`, `search_modules`, `clone_oca_module`, `analyze_module`, `ModuleAnalysis`, etc. |
| `python/src/odoo_gen_utils/search/index.py` | OCA crawl, manifest parse, ChromaDB upsert pipeline | VERIFIED | 289 lines (min 80 required); full implementation with `build_oca_index`, `get_index_status`, `_parse_manifest_safe`, `get_github_token`, `DEFAULT_DB_PATH` |
| `python/src/odoo_gen_utils/search/types.py` | Frozen dataclasses: IndexEntry, IndexStatus | VERIFIED | 32 lines (min 20); `IndexEntry` has 10 fields, `IndexStatus` has 5 fields, both `@dataclass(frozen=True)` |
| `python/src/odoo_gen_utils/cli.py` | `build-index` and `index-status` Click commands | VERIFIED | Commands registered at lines 391 and 430; correct options including `--token`, `--db-path`, `--update`, `--json` |
| `python/tests/test_search_index.py` | Tests for index build, entry structure, auth error handling | VERIFIED | 355 lines (min 60); 17 tests passing |
| `python/tests/test_cli_build_index.py` | Tests for build-index and index-status CLI commands | VERIFIED | 73 lines (min 30); 4 tests passing |
| `commands/index.md` | GSD command stub for /odoo-gen:index | VERIFIED | Exists with correct `name: odoo-gen:index`, workflow steps, objective |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python/src/odoo_gen_utils/search/query.py` | Query encoding, ChromaDB search, result formatting, GitHub fallback | VERIFIED | 257 lines (min 50); `search_modules()`, `SearchResult`, `format_results_text`, `format_results_json`, `_github_search_fallback` |
| `python/tests/test_search_query.py` | Tests for search query, ranking, result format, GitHub fallback | VERIFIED | 412 lines (min 60); 14 tests passing |
| `python/src/odoo_gen_utils/cli.py` | `search-modules` Click command with `--github` flag | VERIFIED | Command registered at line 458; `--github` flag at line 463 |
| `agents/odoo-search.md` | Agent: gap analysis, spec refinement, SRCH-04/05, REFN-01..03 | VERIFIED | 215 lines (min 80); 5-phase workflow: search, selection, gap analysis, spec refinement, decision |
| `commands/search.md` | Activated search command wired to odoo-search agent | VERIFIED | No "not yet available" stub; references `@~/.claude/odoo-gen/agents/odoo-search.md` |

### Plan 03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python/src/odoo_gen_utils/search/fork.py` | Git sparse checkout clone for OCA modules | VERIFIED | 95 lines (min 40); `clone_oca_module()` uses `subprocess.run(check=True)`; `setup_companion_dir()` creates `{module}_ext/` structure |
| `python/src/odoo_gen_utils/search/analyzer.py` | Module structure analysis: models, fields, views, security | VERIFIED | 350 lines (min 60); `analyze_module()`, `ModuleAnalysis`, `format_analysis_text`; AST + XML parsing |
| `python/tests/test_search_fork.py` | Tests for clone, analyze, companion module | VERIFIED | 434 lines (min 80); 21 tests passing |
| `python/src/odoo_gen_utils/cli.py` | `extend-module` Click command | VERIFIED | Command registered at line 542 with `--repo`, `--output-dir`, `--spec-file`, `--branch`, `--json` options |
| `agents/odoo-extend.md` | Agent: delta code generation using _inherit, xpath | VERIFIED | 310 lines (min 100); 5-phase workflow with explicit `_inherit` and `xpath` code patterns |
| `commands/extend.md` | Activated extend command wired to odoo-extend agent | VERIFIED | No "not yet available" stub; references `@~/.claude/odoo-gen/agents/odoo-extend.md` |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py` | `search/__init__.py` | `from odoo_gen_utils.search import` | WIRED | Line 15: `from odoo_gen_utils.search import build_oca_index, get_github_token, get_index_status` |
| `cli.py` | `search/index.py` | `from odoo_gen_utils.search.index import DEFAULT_DB_PATH` | WIRED | Line 18: exact import present and used at lines 414, 482 |
| `search/index.py` | `chromadb.PersistentClient` | ChromaDB collection upsert | WIRED | Line 133: `client = chromadb.PersistentClient(path=db_path)`, line 218: `collection.upsert(...)` |
| `search/index.py` | `github.Github` | PyGithub OCA org crawl | WIRED | Line 139: `gh = Github(token)`, line 140: `org = gh.get_organization("OCA")` |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `search/query.py` | `chromadb.PersistentClient` | `collection.query()` | WIRED | Line 179: `client = chromadb.PersistentClient(path=resolved_path)`, line 184: `collection.query(...)` |
| `search/query.py` | `subprocess (gh search repos)` | GitHub CLI fallback | WIRED | Line 112-116: `subprocess.run(["gh", "search", "repos", query, "--json", ...])` |
| `cli.py` | `search/query.py` | `import search_modules` | WIRED | Lines 19-23: `from odoo_gen_utils.search.query import format_results_json, format_results_text, search_modules` |
| `agents/odoo-search.md` | `cli.py` | `odoo-gen-utils search-modules` CLI invocation | WIRED | Lines 20, 26, 200: CLI commands documented in agent workflow |
| `commands/search.md` | `agents/odoo-search.md` | agent reference in `execution_context` | WIRED | Line 15: `@~/.claude/odoo-gen/agents/odoo-search.md` |

### Plan 03 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `search/fork.py` | `git sparse-checkout` | `subprocess.run` with `check=True` | WIRED | Lines 41-66: all three git commands use `check=True`; sparse-checkout at line 56 |
| `search/analyzer.py` | `ast module` | `ast.parse` for model extraction | WIRED | Line 70: `tree = ast.parse(source, filename=str(filepath))` used in model extraction |
| `cli.py` | `search/fork.py` | `import clone_oca_module` | WIRED | Line 17: `from odoo_gen_utils.search.fork import clone_oca_module, setup_companion_dir` |
| `agents/odoo-extend.md` | `cli.py` | `odoo-gen-utils extend-module` CLI invocation | WIRED | Lines 22, 217, 291: CLI invocation documented in agent workflow |
| `commands/extend.md` | `agents/odoo-extend.md` | agent reference in `execution_context` | WIRED | Line 13: `@~/.claude/odoo-gen/agents/odoo-extend.md` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| SRCH-01 | 08-01 + 08-02 | Semantically searches GitHub repos for similar modules | SATISFIED | `query.py:99-145` `_github_search_fallback()` via `gh search repos`; `cli.py:463` `--github` flag; auto-fallback at `cli.py:524` |
| SRCH-02 | 08-01 | Semantically searches OCA repositories for similar modules | SATISFIED | `index.py:140-141` crawls OCA org via PyGithub; ChromaDB vector index stores OCA modules |
| SRCH-03 | 08-02 | Scores and ranks candidate modules by relevance to user's intent | SATISFIED | `query.py:39-51` cosine distance to 0.0-1.0 similarity; `query.py:205-206` sorted descending |
| SRCH-04 | 08-02 | Presents top matches with relevance scores, feature overlap, and gap analysis | SATISFIED | `agents/odoo-search.md` Phase 3 (Gap Analysis) runs on selected result; `format_results_text` includes scores and badges |
| SRCH-05 | 08-02 | User can select a match to fork-and-extend, or choose to build from scratch | SATISFIED | `agents/odoo-search.md:169-176` Phase 5 decision: "Fork and extend" triggers `/odoo-gen:extend`; "Build from scratch" triggers `/odoo-gen:new` |
| REFN-01 | 08-02 | User can adjust module specification based on what already exists | SATISFIED | `agents/odoo-search.md:130-135` Phase 4.2 Spec Adjustment |
| REFN-02 | 08-02 | System highlights covered vs. gap parts of spec | SATISFIED | `agents/odoo-search.md:137-153` Phase 4.3 Highlight Coverage with explicit covered/extension-needed sections |
| REFN-03 | 08-02 + 08-03 | Adjusted spec replaces original for all downstream generation steps | SATISFIED | `cli.py:600-611` REFN-03 logic: saves to `_ext/spec.json` AND overwrites original spec path; both agents document this |
| FORK-01 | 08-03 | System clones selected matching module into output directory | SATISFIED | `fork.py:14-66` `clone_oca_module()` with git sparse checkout; `cli.py:581` `clone_oca_module(repo, module_name, out_path, branch=branch)` |
| FORK-02 | 08-03 | System analyzes forked module's structure (models, views, security, data files) | SATISFIED | `analyzer.py:217-282` `analyze_module()` extracts via AST + XML; `ModuleAnalysis` has all 10 structural fields |
| FORK-03 | 08-03 | System generates delta code to extend forked module to match refined spec | SATISFIED | `agents/odoo-extend.md` Phase 3 Delta Code Generation with `_inherit`, `xpath`, companion `__manifest__.py` patterns |
| FORK-04 | 08-01 | System maintains local vector index of OCA/GitHub module descriptions | SATISFIED | `index.py:31` `DEFAULT_DB_PATH = ~/.local/share/odoo-gen/chromadb`; ChromaDB persistent collection `odoo_modules` |

**All 12 requirements SATISFIED.**

---

## Anti-Patterns Found

No anti-patterns detected. Scan results:

- No `TODO`, `FIXME`, `XXX`, `HACK`, `PLACEHOLDER`, "not yet available", "coming soon" in any implementation files
- No `return null`, `return {}`, `return []` stub patterns in core functions (valid returns of empty tuples/None for error conditions are intentional and documented)
- No `console.log` (Python project; no `print` left in library code — all output is through `click.echo` in CLI layer)
- Manifest parsing uses `ast.literal_eval` exclusively (line 72 of `index.py`); `eval()` is never called
- `get_github_token` is a public function (no underscore prefix), correctly exported from `search/__init__.py`
- Both commands.search.md and commands/extend.md are fully activated (no "not yet available" stubs)

---

## Test Results

Full test suite run: **225 passed, 5 warnings, 0 failed**

Phase 8 specific tests: **56 passed, 0 failed**

| Test File | Tests | Result | Lines |
|-----------|-------|--------|-------|
| `tests/test_search_index.py` | 17 | All PASSED | 355 |
| `tests/test_cli_build_index.py` | 4 | All PASSED | 73 |
| `tests/test_search_query.py` | 14 | All PASSED | 412 |
| `tests/test_search_fork.py` | 21 | All PASSED | 434 |

TDD workflow confirmed: RED commits precede GREEN commits for all TDD tasks:
- `5ffc03b` (test RED) → `3c1a959` (feat GREEN) — Plan 01, Task 1
- `7b4a6a8` (test RED) → `0e665f0` (feat GREEN) — Plan 01, Task 2
- `353cd91` (test RED) → `53d8c2f` (feat GREEN) — Plan 02, Task 1
- `9e613bd` (test RED) → `d32d6dd` (feat GREEN) — Plan 03, Task 1

---

## Human Verification Required

### 1. Live OCA Index Build

**Test:** Set `GITHUB_TOKEN` env var or run `gh auth login`, then run `odoo-gen-utils build-index`
**Expected:** Build completes in 3-5 minutes; prints progress "Indexing OCA repos... N/total"; ends with "Indexed X modules from OCA"; ChromaDB files appear at `~/.local/share/odoo-gen/chromadb/`
**Why human:** Requires live GitHub authentication and OCA network access; tests mock PyGithub

### 2. Semantic Search Quality

**Test:** After building index, run `odoo-gen-utils search-modules "manage customer subscriptions with recurring billing"`
**Expected:** 5 ranked results returned with names, relevance scores (0-100%), OCA badges, and summaries that are meaningfully related to subscription/billing modules
**Why human:** Semantic relevance quality requires subjective human evaluation with a real populated index

### 3. Git Sparse Checkout Clone

**Test:** Run `odoo-gen-utils extend-module sale_order_type --repo sale-workflow --output-dir /tmp/test_fork`
**Expected:** Sparse checkout clones only `sale_order_type/` directory (not full repo); `oca_sale-workflow/sale_order_type/` and `oca_sale-workflow/sale_order_type_ext/` directories created; analysis output shows models, fields, views
**Why human:** Requires live `git clone` from GitHub; fork tests mock `subprocess.run`

---

## Gaps Summary

No gaps found. All 12 must-haves are verified at all three levels:

1. **Exists** - All 16 required files are present in the codebase
2. **Substantive** - All files exceed minimum line requirements; no placeholder implementations detected
3. **Wired** - All key links verified: CLI imports search package; search package imports ChromaDB and PyGithub; agent workflows reference CLI commands; command files reference agent files

The full pipeline is implemented end-to-end:
- `build-index` crawls OCA → ChromaDB (FORK-04, SRCH-02)
- `search-modules` queries ChromaDB, falls back to GitHub (SRCH-01, SRCH-03)
- `odoo-search` agent does gap analysis + spec refinement (SRCH-04, SRCH-05, REFN-01/02/03)
- `extend-module` sparse-clones + analyzes + sets up companion dir (FORK-01, FORK-02)
- `odoo-extend` agent generates delta code with `_inherit`/`xpath` (FORK-03)

---

_Verified: 2026-03-03T07:30:00Z_
_Verifier: Claude (gsd-verifier)_
