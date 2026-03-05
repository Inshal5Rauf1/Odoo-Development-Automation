# Project Research Summary

**Project:** Odoo Module Automation v3.1 -- Design Flaws & Feature Gaps
**Domain:** Odoo module code generation (spec-driven template rendering pipeline)
**Researched:** 2026-03-05
**Confidence:** HIGH

## Executive Summary

The v3.1 milestone addresses 13 design flaws in the Odoo module generator, spanning spec design patterns (relationship awareness, computed dependency chains, monetary fields, complex constraints), new template types (QWeb reports, dashboard views, HTTP controllers, import/export wizards, cron jobs), and production performance patterns (indexing, ormcache, bulk operations, archival). The existing architecture -- a 7-stage Jinja2 rendering pipeline driven by a JSON spec -- is well-suited for this expansion. All 13 features integrate through the same proven patterns: extend the spec schema, enrich context builders, add or modify templates, wire new stage functions into the pipeline. Only one new external dependency is needed (openpyxl for import/export wizards).

The recommended approach is a three-phase build: (1) spec design extensions that fix foundational data model gaps (monetary detection, relationship awareness, computed chain validation, constraint generation), (2) new template types that expand the module generator's output repertoire (reports, dashboards, controllers, import/export wizards, cron), and (3) performance patterns that make generated modules production-ready (indexing, caching, bulk operations, archival). Phase 1 must complete before 2-3, but within Phase 2 the four template types are independent and parallelizable.

The primary risks are coordination failures when adding new renderer stages (5 coordination points per stage -- miss one and the generated module silently breaks) and security gaps in generated controllers and import wizards (auth defaults, CSRF, sudo misuse). Both are preventable with upfront checklists and secure-by-default templates. The circular computed dependency chain pitfall is the most dangerous runtime risk -- it produces modules that install cleanly but hang in production.

## Key Findings

### Recommended Stack

The existing validated stack (Python 3.12, Jinja2, Click, pylint-odoo, ChromaDB, Docker, MCP, Context7) requires almost no changes. This is fundamentally a template and spec-parsing milestone, not a technology integration.

**Stack delta:**
- **openpyxl >= 3.1.5**: Only new external dependency. Required by generated import/export wizard code (reads/writes .xlsx). 4MB, MIT license, zero-risk addition. Needed in Docker validation image and test venv, not in core tooling.
- **graphlib.TopologicalSorter (stdlib)**: Python 3.12 built-in for computed field dependency chain analysis and cycle detection. No install needed.
- **3 new Jinja2 filters**: Trivial string transforms (`to_report_id`, `to_cron_id`, `to_controller_route`) added to `renderer.py`. ~10 lines total.

**What NOT to add:** pandas (150MB overkill), networkx (stdlib covers it), any REST framework (Odoo has `http.Controller`), APScheduler/celery (Odoo has `ir.cron`), reportlab (Odoo uses wkhtmltopdf).

### Expected Features

**Must have (table stakes -- P1):**
- **Monetary field pattern** (FLAW-04) -- Auto-detect `fields.Monetary` and inject `currency_id`. Without this, modules crash at install with a cryptic AssertionError.
- **Relationship pattern awareness** (FLAW-01) -- Through-models, self-referential M2M, hierarchical parent_id. Current generator only produces flat relationships.
- **Computed field dependency chains** (FLAW-02) -- Multi-model `@api.depends` chains with topological sorting and cycle detection.
- **Complex constraint support** (FLAW-03) -- Cross-model validation, temporal locks, capacity checks via `create()`/`write()` overrides.
- **Database performance patterns** (FLAW-14) -- `index=True`, `store=True` selectivity, `_order`, `_transient` config. OCA review checklist items.
- **Scheduled action generation** (FLAW-20) -- `ir.cron` XML data records. One of the most common Odoo patterns, currently absent from templates.

**Should have (differentiators -- P2):**
- **QWeb report generation** (FLAW-08) -- Full pipeline: ir.actions.report + QWeb template + paper format + form button. No competitor handles this.
- **Dashboard/analytics views** (FLAW-09) -- Graph, pivot, cohort view XML + reporting menu items.
- **HTTP controller generation** (FLAW-10) -- `@http.route` controllers with auth, CSRF, error handling.
- **Import/export wizard generation** (FLAW-12) -- TransientModel with openpyxl parsing, row validation, preview, batch create.
- **Bulk operation patterns** (FLAW-13) -- `@api.model_create_multi`, batch processing with progress.
- **Reference data caching** (FLAW-15) -- `@tools.ormcache` with proper invalidation.
- **Archival/partitioning** (FLAW-16) -- `active` field, archive actions, cleanup crons.

**Defer (v3.2+):**
- Dynamic RBAC framework (FLAW-05) -- Separate product concern, too large.
- Audit trail beyond chatter (FLAW-07) -- Use OCA `auditlog` module instead.
- Webhook/event pattern (FLAW-11) -- Needs event bus architecture beyond template scope.
- Multi-level approval workflows (FLAW-18) -- Domain-specific, brittle to auto-generate.
- Notification/alert generation (FLAW-19) -- Tightly coupled, defer after mail.thread is solid.

### Architecture Approach

The architecture extends naturally. The existing 7-stage pipeline (`render_manifest` through `render_static`) gains 3 new stages (`render_reports`, `render_controllers`, `render_cron`), 12 new Jinja2 templates, and ~15 new context keys in `_build_model_context()`. The spec JSON gains 5 new top-level sections (`relationships`, `computation_chains`, `constraints`, `reports`, `controllers`, `cron_jobs`, `performance`) -- all additive, no breaking changes. The immutable context extension pattern (`{**module_context, "report": report}`) and `Result[list[Path]]` stage contract are preserved throughout.

**Major components affected:**
1. **Spec schema** -- 5 new top-level sections, all accessed via `.get()` with safe defaults
2. **Context builders** -- `_build_model_context()` gains ~15 keys (monetary, performance, relationships, chains, constraints); `_build_module_context()` gains manifest file entries for reports/cron
3. **Renderer pipeline** -- 3 new stage functions added between `render_wizards` and `render_tests`; `_compute_manifest_data()` extended for new file types
4. **Template inventory** -- Grows from 21 to ~33 files, all in `shared/` (no version-specific differences for new templates)

### Critical Pitfalls

1. **Circular computed dependency chains** -- Specs can create cross-model circular `@api.depends` that install cleanly but cause infinite recomputation loops at runtime. **Prevention:** Build a directed dependency graph with `graphlib.TopologicalSorter` and reject specs with cycles before rendering. Must be in Phase 1.

2. **Monetary fields without currency_id** -- `fields.Monetary` without a companion `currency_id` crashes at install with `AssertionError: unknown currency_field None`. **Prevention:** Auto-detect in `_build_model_context()` and inject `currency_id` if missing. Must be in Phase 1.

3. **Renderer pipeline coordination failures** -- Each new stage requires updates to 5 coordination points (stage list, manifest computation, module context, artifact tracking, `__init__.py`). Missing any one produces a module that silently omits features. **Prevention:** Establish a stage-addition checklist or registry pattern before adding the first new stage.

4. **Controller security gaps** -- Generated controllers default to insecure patterns: no CSRF on JSON routes, `auth='none'` without token validation, `sudo()` bypassing ACLs. **Prevention:** Secure-by-default templates: `auth='user'`, `csrf=True`, no `sudo()` without explicit justification.

5. **ir.cron with doall=True causing server overload** -- Missed cron executions replay simultaneously on restart. **Prevention:** Default to `doall=False`, generate batch processing with commit-per-batch.

## Implications for Roadmap

### Phase 1: Spec Design Extensions
**Rationale:** Everything downstream depends on a richer spec. Relationship awareness, monetary detection, computed chain validation, and constraint modeling are prerequisites for correct template generation. These are context builder changes and spec validation logic -- no new templates needed.
**Delivers:** Validated spec schema with relationships, computation_chains, constraints sections; monetary auto-detection; cycle detection in computed chains; `_build_model_context()` enriched with performance, relationship, and constraint keys.
**Addresses:** FLAW-04 (monetary), FLAW-01 (relationships), FLAW-02 (computed chains), FLAW-03 (constraints)
**Avoids:** Pitfall 1 (circular dependencies), Pitfall 2 (missing currency_id)
**Estimated scope:** ~500 lines of Python (spec validation + context builder extensions)

### Phase 2: Template Generation -- New Artifact Types
**Rationale:** With the spec enriched, the generator can produce new artifact types. Reports, controllers, cron, dashboards, and import/export wizards are independent of each other -- they share only the spec and module context. Build in any order or in parallel.
**Delivers:** 12 new Jinja2 templates; 3 new renderer stages; updated manifest computation; controllers and report directories in generated modules.
**Addresses:** FLAW-08 (reports), FLAW-09 (dashboards), FLAW-10 (controllers), FLAW-12 (import/export), FLAW-20 (cron)
**Avoids:** Pitfall 3 (QWeb wkhtmltopdf crashes), Pitfall 4 (controller security), Pitfall 5 (pipeline coordination), Pitfall 6 (cron doall)
**Uses:** openpyxl (for import/export wizard templates)
**Estimated scope:** ~800-1000 lines of Python + 12 template files

### Phase 3: Performance Patterns
**Rationale:** Performance patterns (indexing, caching, bulk operations, archival) build on top of the enriched models and new template infrastructure from Phases 1-2. They modify `model.py.j2` and reuse the cron infrastructure from Phase 2. These are polish features that make generated modules production-ready rather than scaffolds.
**Delivers:** `index=True` auto-detection (avoiding duplicates with Odoo auto-indexes), `_order` generation, `@tools.ormcache` with invalidation, `@api.model_create_multi` in import wizards, archival crons with batch processing.
**Addresses:** FLAW-14 (DB performance), FLAW-13 (bulk ops), FLAW-15 (caching), FLAW-16 (archival)
**Avoids:** Pitfall 7 (duplicate indexes), Pitfall 8 (ormcache on context-dependent methods)
**Estimated scope:** ~300-400 lines of template modifications + context builder logic

### Phase Ordering Rationale

- **Phase 1 before Phase 2:** New templates consume the enriched context keys. Attempting to generate reports or controllers without relationship awareness and performance annotations produces incomplete output.
- **Phase 2 items are parallelizable:** Reports, controllers, cron, dashboards, and import/export wizards are independent stages. They share no templates and no context keys beyond the base module context. Build them in any order.
- **Phase 3 after Phase 2:** Archival depends on cron infrastructure (Phase 2). Bulk operations complement import wizards (Phase 2). Caching and indexing modify `model.py.j2` which should be stable before adding performance decorators.
- **Critical path:** Phase 1 (spec) -> Phase 2 (templates) -> Phase 3 (performance) -> Integration tests validating the entire pipeline with a comprehensive spec.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (QWeb reports):** wkhtmltopdf rendering quirks are poorly documented. The `web.external_layout` template structure and page break behavior need hands-on testing.
- **Phase 2 (Import/export wizards):** The openpyxl integration pattern (base64 Binary field -> openpyxl Workbook -> row validation -> batch create) has several moving parts. Single-source reference.
- **Phase 3 (Odoo 18.0 declarative Index API):** The `from odoo import Index` API in Odoo 18.0 may require a version-specific `model.py.j2` override.

Phases with standard patterns (skip research-phase):
- **Phase 1 (all items):** Monetary field injection, relationship patterns, topological sort, and constraint generation are all well-documented in Odoo official docs with HIGH confidence sources.
- **Phase 2 (Controllers, Cron, Dashboards):** Standard Odoo patterns with official documentation.
- **Phase 3 (Indexing, Caching):** Well-documented ORM features.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Only 1 new dependency (openpyxl), verified on PyPI. All other features use existing stack or stdlib. |
| Features | HIGH | All 13 features verified against Odoo 17.0/18.0 official ORM docs. Competitor analysis confirms no generator handles these. |
| Architecture | HIGH | All changes extend proven patterns (stage functions, Result[T], Jinja2 templates). Existing codebase directly analyzed. |
| Pitfalls | HIGH | 8 critical pitfalls documented with verified sources (official docs, GitHub issues, community reports). Recovery strategies included. |

**Overall confidence:** HIGH

### Gaps to Address

- **Odoo 18.0 declarative Index API:** May require version-specific template. Research during Phase 3 implementation, not blocking.
- **Spec schema validation:** Currently no formal schema (all `.get()` with defaults). Adding 5 new spec sections increases the risk of malformed specs. Consider adding Pydantic or JSON Schema validation in Phase 1.
- **QWeb report PDF rendering validation:** Docker tests do not exercise wkhtmltopdf PDF generation. A report can install cleanly but crash when printing. Consider adding a PDF render step to Docker validation in Phase 2.
- **Import wizard file type security:** Generated wizards must validate uploaded file content type, not just extension.

## Sources

### Primary (HIGH confidence)
- [Odoo 17.0 ORM API](https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html) -- fields, depends, store, index, constraints, model_create_multi
- [Odoo 17.0 QWeb Reports](https://www.odoo.com/documentation/17.0/developer/reference/backend/reports.html) -- ir.actions.report, QWeb template structure
- [Odoo 18.0 Web Controllers](https://www.odoo.com/documentation/18.0/developer/reference/backend/http.html) -- http.route, auth levels, CSRF behavior
- [Odoo 17.0 Computed Fields tutorial](https://www.odoo.com/documentation/17.0/developer/tutorials/server_framework_101/08_compute_onchange.html) -- chain dependencies, store=True
- [Python graphlib docs](https://docs.python.org/3.12/library/graphlib.html) -- TopologicalSorter API
- [openpyxl PyPI](https://pypi.org/project/openpyxl/) -- version 3.1.5, MIT, dependencies
- Existing codebase analysis: `renderer.py` (770 lines), `auto_fix.py`, `validation/types.py`, 21 Jinja2 templates

### Secondary (MEDIUM confidence)
- [OCA excel_import_export Discussion](https://github.com/orgs/OCA/discussions/154) -- OCA xlsx wizard conventions
- [Odoo ormcache Guide (Cybrosys)](https://www.cybrosys.com/odoo/odoo-books/odoo-17-development/performance-optimisation/orm-cache/) -- cache usage patterns
- [Odoo Monetary Fields (Cybrosys)](https://www.cybrosys.com/odoo/odoo-books/odoo-17-development/creating-odoo-modules/monetary-fields/) -- currency_id pattern
- [Custom XLSX Import Wizard (Numla)](https://numla.com/blog/odoo-development-18/creating-custom-xlsx-import-wizard-in-odoo-286) -- openpyxl pattern
- [Odoo Query Optimizations 17-19 (Stormatics)](https://stormatics.tech/blogs/query-optimizations-in-odoo-versions-17-19-for-faster-postgresql-performance) -- declarative index API
- [Best Practices for Odoo Crons (Odoo Experience 2025)](https://www.odoo.com/event/odoo-experience-2025-6601/track/best-practices-to-design-odoo-crons-8754) -- doall, batch processing
- [JSON Route CSRF Issue #43151 (GitHub)](https://github.com/odoo/odoo/issues/43151) -- CSRF on JSON routes
- [ormcache Exception Issue #35289 (GitHub)](https://github.com/odoo/odoo/issues/35289) -- cache invalidation bugs

### Tertiary (LOW confidence)
- [Odoo Performance Optimization 2025 (Medium)](https://medium.com/@jacobweber005/odoo-app-performance-optimization-speed-scalability-trends-for-2025-aed068e6dabe) -- trends article, not authoritative

---
*Research completed: 2026-03-05*
*Ready for roadmap: yes*
