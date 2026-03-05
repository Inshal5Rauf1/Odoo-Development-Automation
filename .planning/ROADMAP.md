# Roadmap: Agentic Odoo Module Development Workflow

## Milestones

- **v1.0 Odoo Module Automation MVP** — Phases 1-9 (shipped 2026-03-03) | [Archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Tech Debt Cleanup** — Phases 10-11 (shipped 2026-03-03)
- **v1.2 Template Quality** — Phases 12-14 (shipped 2026-03-04) | [Archive](milestones/v1.2-ROADMAP.md)
- **v2.0 Environment-Aware Generation** — Phases 15-17 (shipped 2026-03-04)
- **v2.1 Auto-Fix & Enhancements** — Phases 18-19 (shipped 2026-03-04) | [Archive](milestones/v2.1-ROADMAP.md)
- **v3.0 Bug Fixes & Tech Debt** — Phases 20-25 (shipped 2026-03-05) | [Archive](milestones/v3.0-ROADMAP.md)
- **v3.1 Design Flaws & Feature Gaps** — Phases 26-34 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-9) — SHIPPED 2026-03-03</summary>

- [x] Phase 1: GSD Extension + Odoo Foundation (4/4 plans) — completed 2026-03-01
- [x] Phase 2: Knowledge Base (3/3 plans) — completed 2026-03-01
- [x] Phase 3: Validation Infrastructure (3/3 plans) — completed 2026-03-01
- [x] Phase 4: Input & Specification (2/2 plans) — completed 2026-03-02
- [x] Phase 5: Core Code Generation (3/3 plans) — completed 2026-03-02
- [x] Phase 6: Security & Test Generation (2/2 plans) — completed 2026-03-02
- [x] Phase 7: Human Review & Quality Loops (3/3 plans) — completed 2026-03-03
- [x] Phase 8: Search & Fork-Extend (3/3 plans) — completed 2026-03-03
- [x] Phase 9: Edition & Version Support (3/3 plans) — completed 2026-03-03

**Total:** 9 phases, 26 plans, 68 requirements | 139 commits | 4,150 LOC Python | 243 tests

</details>

<details>
<summary>v1.1 Tech Debt Cleanup (Phases 10-11) — SHIPPED 2026-03-03</summary>

- [x] Phase 10: Environment & Dependencies — completed 2026-03-03
- [x] Phase 11: Live Integration Testing & i18n — completed 2026-03-03

</details>

<details>
<summary>v1.2 Template Quality (Phases 12-14) — SHIPPED 2026-03-04</summary>

- [x] Phase 12: Template Correctness & Auto-Fix (2/2 plans) — completed 2026-03-03
- [x] Phase 13: Golden Path Regression Testing (1/1 plan) — completed 2026-03-03
- [x] Phase 14: Cleanup/Debug the Tech Debt (1/1 plan) — completed 2026-03-04

**Total:** 3 phases, 4 plans, 12 requirements | 29 commits | 1/1 | Complete    | 2026-03-05 | +7,753 LOC Python | 494 tests

</details>

### v3.1 Design Flaws & Feature Gaps (In Progress)

**Milestone Goal:** Close foundational design gaps in spec design, template generation, and performance patterns to produce richer, production-grade Odoo modules.

- [x] **Phase 26: Monetary Field Detection** - Auto-detect monetary patterns and inject currency_id (completed 2026-03-05)
- [x] **Phase 27: Relationship Patterns** - Through-models, self-referential M2M, hierarchical parent_id (completed 2026-03-05)
- [x] **Phase 28: Computed Chains & Cycle Detection** - Multi-model dependency chains with topological sort and circular dependency rejection (completed 2026-03-05)
- [x] **Phase 29: Complex Constraints** - Cross-model validation, temporal, and capacity constraints (completed 2026-03-05)
- [x] **Phase 30: Scheduled Actions & Render Pipeline** - ir.cron generation and new renderer stage wiring (completed 2026-03-05)
- [ ] **Phase 31: Reports & Analytics** - QWeb report templates and graph/pivot dashboard views
- [ ] **Phase 32: Controllers & Import/Export** - HTTP controllers and bulk import/export wizards
- [ ] **Phase 33: Database Performance** - Index auto-detection, store=True selectivity, transient model config
- [ ] **Phase 34: Production Patterns** - Bulk operations, reference caching, and archival strategies

## Phase Details

### Phase 26: Monetary Field Detection
**Goal**: Spec fields matching monetary patterns (amount, fee, salary, price, cost, balance) automatically become fields.Monetary with currency_id companion field injected
**Depends on**: Nothing (standalone quick win, prevents install-crashing AssertionError)
**Requirements**: SPEC-01
**Success Criteria** (what must be TRUE):
  1. A spec with a field named "amount" or "total_price" renders as `fields.Monetary` (not `fields.Float`) in the generated model
  2. When any field is detected as monetary, a `currency_id` Many2one to `res.currency` is auto-injected into the model if not already present
  3. The generated module installs without `AssertionError: unknown currency_field None`
**Plans**: 1 plan
Plans:
- [ ] 31-01-PLAN.md — QWeb report templates, graph/pivot dashboard views, render_reports() implementation

### Phase 27: Relationship Patterns
**Goal**: Spec supports rich relationship declarations that generate through-models for M2M with extra fields, self-referential M2M with explicit relation/column params, and hierarchical parent_id with parent_path
**Depends on**: Phase 26
**Requirements**: SPEC-02
**Success Criteria** (what must be TRUE):
  1. A spec declaring a M2M relationship with extra fields (e.g., enrollment with grade + date) generates a dedicated through-model with the extra fields and two Many2one links
  2. A spec declaring a self-referential M2M (e.g., prerequisite courses) generates correct `relation`, `column1`, `column2` parameters to avoid ambiguous table names
  3. A spec declaring `hierarchical: true` on a model generates `parent_id`, `child_ids`, and `parent_path` fields with `_parent_name` and `_parent_store = True`
  4. Through-models get their own security ACL entries and are included in `__init__.py`
**Plans**: 1 plan
Plans:
- [ ] 27-01-PLAN.md — Relationship preprocessor + template extensions for through-models, self-referential M2M, and hierarchical models



### Phase 28: Computed Chains & Cycle Detection
**Goal**: Spec supports multi-model computed field dependency chains with correct topological ordering, and rejects circular dependencies before generation
**Depends on**: Phase 27 (relationship awareness needed for cross-model references)
**Requirements**: SPEC-03, SPEC-05
**Success Criteria** (what must be TRUE):
  1. A spec with `computation_chains` defining fields across models generates `@api.depends` with correct dotted paths (e.g., `line_ids.subtotal`) and `store=True`
  2. Computed fields render in topologically sorted order so downstream fields reference already-defined upstream fields
  3. A spec containing a circular dependency chain (A depends on B depends on A) is rejected with an actionable error message naming the cycle participants before any files are generated
  4. The generated module with multi-model computed chains installs and computes values correctly
**Plans**: 1 plan
Plans:
- [ ] 28-01-PLAN.md — Cycle detection, chain preprocessor, topological sort, and integration tests

### Phase 29: Complex Constraints
**Goal**: Spec supports cross-model validation, temporal constraints, and capacity constraints that generate create()/write() overrides with ValidationError
**Depends on**: Phase 27 (relationship patterns needed for cross-model references)
**Requirements**: SPEC-04
**Success Criteria** (what must be TRUE):
  1. A spec with a cross-model constraint (e.g., "enrollment count cannot exceed course capacity") generates a `write()` or `create()` override that queries the related model and raises `ValidationError`
  2. A spec with a temporal constraint (e.g., "end_date must be after start_date") generates a `@api.constrains` method with the date comparison
  3. A spec with a capacity constraint (e.g., "max 30 students per section") generates validation logic that counts related records before allowing creation
  4. All generated constraint methods include proper `_()` translated error messages
**Plans**: 1 plan
Plans:
- [ ] 29-01-PLAN.md — Constraint preprocessor, template extensions for temporal/cross-model/capacity constraints, unit + integration tests

### Phase 30: Scheduled Actions & Render Pipeline
**Goal**: Generator produces ir.cron XML records with model method stubs, and new render stages are wired into the renderer pipeline
**Depends on**: Phase 26 (renderer pipeline must be stable before adding stages)
**Requirements**: TMPL-05, TMPL-06
**Success Criteria** (what must be TRUE):
  1. A spec with `cron_jobs` entries generates `data/data.xml` containing `ir.cron` records with correct interval_type, interval_number, model_id reference, and code/method reference
  2. The target model gets an `@api.model` stub method matching the cron's method reference
  3. Generated crons default to `doall="False"` (preventing server overload on missed executions)
  4. New render stages (`render_reports`, `render_controllers`, `render_cron`) are wired into the pipeline, each returning `Result[list[Path]]` and updating manifest data
**Plans**: 1 plan
Plans:
- [ ] 30-01-PLAN.md — Cron XML generation, render stage wiring, model method stubs, and pipeline expansion to 10 stages



### Phase 31: Reports & Analytics
**Goal**: Generator produces QWeb report templates with print buttons and graph/pivot dashboard views with configurable measures
**Depends on**: Phase 30 (render_reports stage must exist in pipeline)
**Requirements**: TMPL-01, TMPL-02
**Success Criteria** (what must be TRUE):
  1. A spec with `reports` entries generates `ir.actions.report` XML, a QWeb template with `t-foreach`/`t-field` data binding, and an optional paper format record
  2. The report's form view gets a print button that triggers the report action
  3. A spec with `dashboards` or analytics entries generates graph view XML with measures/dimensions and pivot view XML with row/column/measure groupings
  4. Dashboard views are accessible via `ir.actions.act_window` with `view_mode` including `graph,pivot`
**Plans**: 1 plan
Plans:
- [ ] 31-01-PLAN.md — QWeb report templates, graph/pivot dashboard views, render_reports() implementation

### Phase 32: Controllers & Import/Export
**Goal**: Generator produces HTTP controllers with secure defaults and import/export TransientModel wizards with file upload, validation, and batch processing
**Depends on**: Phase 30 (render_controllers stage must exist in pipeline)
**Requirements**: TMPL-03, TMPL-04
**Success Criteria** (what must be TRUE):
  1. A spec with `controllers` entries generates `controllers/main.py` with `@http.route` decorators, and `controllers/__init__.py` is created and imported from the module root
  2. Generated controllers default to `auth='user'` and `csrf=True` (secure by default); JSON routes include proper error handling
  3. A spec with `import_export: true` on a model generates a TransientModel wizard with `fields.Binary` upload, row validation, preview step, and batch `_do_import()` method
  4. The import wizard validates file content type (not just extension) and the export action produces xlsx output
**Plans**: 1 plan
Plans:
- [ ] 31-01-PLAN.md — QWeb report templates, graph/pivot dashboard views, render_reports() implementation

### Phase 33: Database Performance
**Goal**: Generated models automatically get index=True on filterable fields, store=True on computed fields used in views, and TransientModels get cleanup configuration
**Depends on**: Phase 28 (store=True depends on computed chain awareness)
**Requirements**: PERF-01, PERF-05
**Success Criteria** (what must be TRUE):
  1. Fields referenced in search view filters, record rule domains, or `_order` automatically get `index=True` in the generated model
  2. Multi-field uniqueness constraints generate `_sql_constraints` entries
  3. Computed fields that appear in tree views, search filters, or `_order` automatically get `store=True`
  4. TransientModel classes get `_transient_max_hours` and `_transient_max_count` attributes
**Plans**: 1 plan
Plans:
- [ ] 31-01-PLAN.md — QWeb report templates, graph/pivot dashboard views, render_reports() implementation

### Phase 34: Production Patterns
**Goal**: Generated modules support bulk operations, reference data caching, and archival strategies for production-scale usage
**Depends on**: Phase 30 (archival uses cron infrastructure), Phase 33 (performance context keys)
**Requirements**: PERF-02, PERF-03, PERF-04
**Success Criteria** (what must be TRUE):
  1. Models with `bulk: true` in spec generate `@api.model_create_multi` on `create()` with batched post-processing
  2. Near-static reference models generate `@tools.ormcache` on lookup methods with cache invalidation in `write()` and `create()`
  3. Models with `archival: true` generate an `active` field, an archival wizard TransientModel, and an `ir.cron` scheduled action for periodic cleanup
  4. Archival crons use batch processing with commit-per-batch to avoid long transactions
**Plans**: 1 plan
Plans:
- [ ] 31-01-PLAN.md — QWeb report templates, graph/pivot dashboard views, render_reports() implementation

## Progress

**Execution Order:**
Phases execute in numeric order: 26 -> 27 -> 28 -> 29 -> 30 -> 31 -> 32 -> 33 -> 34

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-9 | v1.0 | 26/26 | Complete | 2026-03-03 |
| 10-11 | v1.1 | - | Complete | 2026-03-03 |
| 12-14 | v1.2 | 4/4 | Complete | 2026-03-04 |
| 15-17 | v2.0 | 6/6 | Complete | 2026-03-04 |
| 18-19 | v2.1 | 5/5 | Complete | 2026-03-04 |
| 20-25 | v3.0 | 11/11 | Complete | 2026-03-05 |
| 26. Monetary Field Detection | 1/1 | Complete    | 2026-03-05 | - |
| 27. Relationship Patterns | 1/1 | Complete    | 2026-03-05 | - |
| 28. Computed Chains & Cycle Detection | 1/1 | Complete    | 2026-03-05 | - |
| 29. Complex Constraints | v3.1 | 0/1 | Not started | - |
| 30. Scheduled Actions & Render Pipeline | 1/1 | Complete    | 2026-03-05 | - |
| 31. Reports & Analytics | v3.1 | 0/TBD | Not started | - |
| 32. Controllers & Import/Export | v3.1 | 0/TBD | Not started | - |
| 33. Database Performance | v3.1 | 0/TBD | Not started | - |
| 34. Production Patterns | v3.1 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-03-01*
*v1.0 shipped: 2026-03-03*
*v1.1 shipped: 2026-03-03*
*v1.2 shipped: 2026-03-04*
*v2.0 shipped: 2026-03-04*
*v2.1 shipped: 2026-03-04*
*v3.0 shipped: 2026-03-05*
*v3.1 roadmap created: 2026-03-05*
