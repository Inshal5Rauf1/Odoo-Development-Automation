---
phase: 08-search-fork-extend
created: 2026-03-03T00:00:00Z
status: context-captured
---

# Phase 8: Search & Fork-Extend - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `/odoo-gen:search` and `/odoo-gen:extend` commands backed by a local ChromaDB vector index of OCA module metadata. Users can semantically search for existing modules, see gap analysis, and fork-and-extend a match instead of building from scratch. The index is built by crawling OCA repos via PyGithub and stored locally.

**Depends on:** Phase 5 (spec JSON contract, odoo-scaffold agent, render-module pipeline)
**Requirements in scope:** SRCH-01..05, REFN-01..03, FORK-01..04

</domain>

<decisions>
## Implementation Decisions

### A — Search Result Format (SRCH-03, SRCH-04)

**5 results returned** per search query.

Each result shows:
- Module name + OCA repo (e.g. `sale_order_type` from `OCA/sale-workflow`)
- Relevance score (0.0–1.0, cosine similarity)
- OCA badge (✓ OCA / GitHub)
- One-line summary (from `__manifest__.py` summary field)
- Coverage % — what fraction of the user's query intent is covered (rough LLM estimate)

**Gap analysis runs only for the selected result** (not for all 5 upfront). After user selects a result, the `odoo-search` agent performs structured comparison of the user's spec JSON vs the module's manifest + README to produce:
- Covered: list of spec fields/models already in the module
- Missing: list of spec fields/models the user would need to add
- Conflicts: any architectural mismatches (e.g. different base model)

**SRCH-04 follow-up refinement:** User can type follow-up queries to narrow results. Each follow-up re-queries ChromaDB with the refined text. No session state needed — each query is independent.

---

### B — Index Scope & Build Trigger (FORK-04, SRCH-01, SRCH-02)

**Scope: OCA-only primary index.** Live `gh search repos` fallback for broader GitHub search (only if user explicitly requests with `--github` flag or no OCA results found).

**Build trigger: auto-build on first use** with progress indicator.
- When user runs `/odoo-gen:search` and no index exists: display "Building OCA module index for the first time (this takes ~3-5 minutes)..." then auto-build.
- Subsequent searches use the existing index (fast, <1 second).
- User can manually refresh with `/odoo-gen:index` command.

**Storage location:** `~/.local/share/odoo-gen/chromadb/` (XDG base dir standard).

**Index contents per module entry:**
- `module_name` (technical name)
- `display_name` (from manifest `name` field)
- `summary` (from manifest `summary` field)
- `description` (first 500 chars from manifest `description` or README)
- `depends` (comma-joined list)
- `category` (manifest `category`)
- `oca_repo` (repository name, e.g. `sale-workflow`)
- `github_url` (full HTTPS clone URL)
- `stars` (repo star count)
- `last_pushed` (ISO timestamp for freshness check)

**Embedding text:** Concatenation of `display_name + " " + summary + " " + description` — natural language, NOT source code.

**GitHub auth:** Hard block at index build time. If `GITHUB_TOKEN` env var is not set AND `gh auth token` fails, display:
```
Index build requires GitHub authentication.
Run: gh auth login
Or set: export GITHUB_TOKEN=your_token
Then re-run your search.
```
No graceful degradation at build time — unauthenticated rate limit (60 req/hr) is too low to crawl ~200 OCA repos. Search against an existing index works fully offline.

---

### C — Fork Output Structure (FORK-01..03)

**Companion module pattern** — never modify the cloned original.

Output directory layout after `/odoo-gen:extend`:
```
$OUTPUT_DIR/
  {original_module}/          ← cloned original (read-only reference)
  {original_module}_ext/      ← generated companion module (the delta)
    __manifest__.py           ← depends: ['{original_module}']
    __init__.py
    models/
      {model}.py              ← uses _inherit = '{original.model}'
    views/
      {model}_views.xml       ← uses xpath to extend original views
    security/
      ir.model.access.csv     ← only new model ACLs (if any new models added)
    tests/
      test_{model}.py         ← tests for new fields/methods only
```

**User gets both:** cloned original + companion `_ext` module. The companion is what gets installed on top of the original. Both directories committed together if in a git repo.

**Naming convention:** `{original_module}_ext` (not `{original_module}_custom` or `{original_module}_v2`). If the user's spec has a different `module_name`, use that instead.

**REFN-01..03 (spec refinement):** After gap analysis, user can approve the refined spec (which excludes already-covered fields) before delta code generation starts. The refined spec is saved as `{module_name}_ext/spec.json` — same contract as Phase 4 output.

---

### D — GitHub Auth Handling (SRCH-01, FORK-04)

**Hard block at index build time only.** Auth is NOT checked at search time (existing index works offline).

Auth detection priority:
1. `GITHUB_TOKEN` environment variable
2. `gh auth token` CLI output
3. If both fail → display auth instructions and exit with code 1

**No `gh auth login` auto-trigger** — just display the instructions. User runs it themselves.

**PyGithub instantiation:**
```python
token = os.environ.get("GITHUB_TOKEN") or _get_gh_cli_token()
github = Github(token) if token else Github()  # anonymous if no token
if not token:
    raise SystemExit("GitHub token required. Run: gh auth login")
```

**`/odoo-gen:index` command:** Explicit index build/refresh. Accepts `--update` flag (re-index only repos pushed since last index update, using `last_pushed` timestamps). Full rebuild without flag.

</decisions>

<specifics>
## Specific Ideas

- User approved all recommendations without modification
- Progress indicator during auto-build: show count of repos processed (e.g. "Indexing OCA repos... 47/200")
- Coverage % is a rough estimate from the LLM — not a precise metric, label it clearly as "~X% coverage"
- The `_ext` suffix is a conventional Odoo community pattern for companion modules

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `python/src/odoo_gen_utils/cli.py` (Click): 3 new commands — `build-index`, `search-modules`, `index-status`. Same Click pattern as existing `validate`, `extract-i18n`.
- `python/src/odoo_gen_utils/renderer.py` (`render_module()`): reused to generate the companion `_ext` module from the refined spec (FORK-03).
- `python/src/odoo_gen_utils/templates/`: all existing Jinja2 templates used for companion module generation — no new templates for standard files.
- `agents/odoo-scaffold.md`: extended or referenced by new `agents/odoo-search.md` for spec refinement flow.
- `workflows/scaffold.md`: REFN-01..03 plugs into existing spec workflow after gap analysis — spec is updated, then normal generation proceeds.

### Established Patterns
- `optional-dependencies` in `pyproject.toml`: new `[search]` extra group. Users who don't need search don't install chromadb/torch (~185MB overhead).
- Module context dict pattern (`_build_model_context()`): gap analysis output feeds into the same context used by the render pipeline.
- `ValidationResult` / `Violation` types: reused for search result typing where applicable.

### Integration Points
- `commands/search.md`: stub exists — activate it by wiring to new `odoo-search` agent.
- `commands/extend.md`: stub exists — activate it by wiring to new `odoo-extend` agent.
- `commands/index.md`: NEW command needed — stub doesn't exist yet.
- ChromaDB storage: `~/.local/share/odoo-gen/chromadb/` (separate from project directory — shared across all odoo-gen sessions).
- `pyproject.toml`: add `[project.optional-dependencies] search = [...]` + uv CPU-only torch index config.

</code_context>

<deferred>
## Deferred Ideas

- Broader GitHub search (non-OCA modules) beyond `--github` flag fallback — Phase 9
- Scheduled/cron index refresh — Phase 9 or post-v1
- README/DESCRIPTION.rst inclusion in index (start manifest-only; add if search quality insufficient — can be done as a patch)
- Local git repo search (user's own modules as search targets) — post-v1
- Star/quality filtering (e.g. --min-stars 50) — Phase 9
- DESCRIPTION.rst fragment extraction as separate indexing tier — post-v1

</deferred>

---

*Phase: 08-search-fork-extend*
*Context gathered: 2026-03-03*
