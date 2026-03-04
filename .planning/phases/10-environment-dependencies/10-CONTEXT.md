# Phase 10: Environment & Dependencies - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Search and index features work with real GitHub API and a clean sentence-transformers install. Specifically: `gh auth status` succeeds, `search-modules` returns real results, `uv pip install .[search]` completes on CPU-only machine, and `build-index` + `index-status` work end-to-end.

This phase resolves DEBT-01 and DEBT-02. No new features, commands, or agents.

</domain>

<decisions>
## Implementation Decisions

### sentence-transformers Dependency Investigation
- Investigate whether any code path in the project uses sentence-transformers directly (vs ChromaDB's built-in ONNX embedding)
- If no code path uses it: remove `sentence-transformers` and `torch` from `[search]` extras in pyproject.toml
- This saves ~200MB of install size (torch CPU wheel alone is ~200MB; ChromaDB's ONNX model is ~22MB)
- All 243+ existing tests must still pass after removal
- E2E index build + search must still work without sentence-transformers

### Auth Failure UX: Auto-triggered Setup Wizard
- When any search/index/extend CLI command fails due to missing GitHub token, auto-trigger an interactive setup wizard
- Wizard checks three things in order:
  1. Is `gh` CLI installed? → If not, show install URL (https://cli.github.com/)
  2. Is `gh` authenticated? → If not, suggest `gh auth login`
  3. Can we get a token? → Confirm it works, show success message
- Scope is auth only — no Python version checks, no chromadb checks, no model cache checks
- User can skip with `--no-wizard` flag (for CI/scripting)
- Existing `get_github_token()` auth chain is NOT changed — wizard wraps it with better UX

### E2E Test Strategy
- Write pytest e2e tests that hit real GitHub API (not mocked)
- Two tiers with markers:
  - `@pytest.mark.e2e` — Subset test (5 known OCA repos, ~30s). Quick verification that auth + index + search pipeline works.
  - `@pytest.mark.e2e_slow` — Full OCA build (200+ repos, 3-5 min). Validates the real workload.
- Tests are skipped when `GITHUB_TOKEN` is not available (CI-friendly)
- Add both markers to `[tool.pytest.ini_options]` in pyproject.toml
- Do NOT test against production OCA org in CI without token — rate limits apply

### Claude's Discretion
- Exact wizard output formatting and colors
- How to structure e2e test files (single file vs split)
- Which 5 OCA repos to use for the subset test
- How to detect "gh installed but not authenticated" vs other failure modes
- Whether to add a `--skip-wizard` alias alongside `--no-wizard`

</decisions>

<specifics>
## Specific Ideas

- Wizard should feel helpful, not naggy — trigger once per command failure, not repeatedly
- Error messages should be actionable: "Run `gh auth login` to authenticate" not "Authentication failed"
- The GH_TOKEN vs GITHUB_TOKEN distinction should be documented clearly (our code reads GITHUB_TOKEN, gh CLI reads GH_TOKEN, but the fallback chain handles both)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_github_token()` in `search/index.py:34-56` — already implements correct auth chain, wizard wraps this
- `build_oca_index()` in `search/index.py` — has `progress_callback` parameter, useful for e2e test progress
- `get_index_status()` in `search/index.py` — returns `IndexStatus` dataclass, e2e tests assert on this
- `search_modules()` in `search/query.py` — has `github_fallback` parameter, e2e tests verify both paths

### Established Patterns
- Frozen dataclasses for all return types (IndexStatus, SearchResult, etc.)
- Click CLI with `@click.command()` decorators in `cli.py`
- Mocked tests use `@patch("odoo_gen_utils.search.index.Github")` pattern
- `DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "odoo-gen" / "chromadb"`

### Integration Points
- Wizard hooks into CLI commands (`build-index`, `search-modules`, `extend-module`) at the auth check point
- E2E tests use real `chromadb.PersistentClient` with `tmp_path` fixture
- pyproject.toml `[project.optional-dependencies]` section for dep changes

</code_context>

<deferred>
## Deferred Ideas

- Full environment check command (`check-env`) that validates Python version, chromadb, ONNX model cache, disk space — v1.2+
- `GH_TOKEN` as an additional env var to check alongside `GITHUB_TOKEN` in `get_github_token()` — low priority, fallback chain already covers this via `gh auth token`

</deferred>

---

*Phase: 10-environment-dependencies*
*Context gathered: 2026-03-03*
