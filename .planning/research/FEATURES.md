# Feature Research: v3.1 Design Flaws & Feature Gaps

**Domain:** Odoo module automation — spec design patterns, template generation, performance patterns
**Researched:** 2026-03-05
**Confidence:** HIGH (all 13 features verified against Odoo ORM docs and community patterns)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any serious Odoo module generator must handle. Without these, the generated modules feel like toy scaffolds rather than production code.

| Feature | Why Expected | Complexity | FLAW | Notes |
|---------|--------------|------------|------|-------|
| Monetary field pattern (currency_id) | Every Odoo app with amounts uses `fields.Monetary` + `currency_id`. Generating `fields.Float` for money is a beginner mistake visible in every form view. | LOW | FLAW-04 | Auto-detect from field names (amount, fee, price, cost, salary, balance, penalty). Add `currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)` once per model. Well-documented pattern, zero ambiguity. |
| Relationship pattern awareness | Through-models, self-referential M2M, hierarchical parent_id are fundamental ORM patterns. A generator that only produces flat Many2one/One2many is incomplete. | MEDIUM | FLAW-01 | Self-referential M2M requires explicit `relation`, `column1`, `column2` parameters (ORM auto-naming fails when model=comodel). Through-models need a dedicated model with two Many2one fields + composite unique constraint. parent_id hierarchy needs `_parent_name`, `_parent_store`, `parent_path`. |
| Computed field dependency chains | Multi-level `@api.depends` chains across models (e.g., line totals -> order total -> partner balance) are standard Odoo. Single-level-only compute is a visible limitation. | MEDIUM | FLAW-02 | Odoo ORM supports path-based depends (`@api.depends('line_ids.price_total')`). `store=True` triggers automatic recomputation. Limitation: cannot chain through M2M/O2M in related fields. Must generate correct computation order. |
| Database performance patterns | `index=True`, `store=True` on computed fields in views, `sql_constraints`, `_order` — these are OCA review checklist items. Missing them means modules fail code review. | LOW | FLAW-14 | Auto-detect: index fields used in search filters and record rules. Set `store=True` on computed fields in tree/search views. Generate `_order` from model semantics. Add `_transient_max_hours`/`_transient_max_count` to TransientModels. |
| Scheduled action (ir.cron) generation | ir.cron is one of the most common Odoo patterns. Knowledge base documents it but templates never generate it. Any module with recurring tasks needs cron. | LOW | FLAW-20 | Standard XML data record in `data/data.xml` within `<data noupdate="1">`. Method on model with `@api.model` decorator. Must batch processing (few seconds per execution) to avoid blocking workers. Odoo deactivates crons after 5 consecutive failures over 7 days. |
| Complex constraint support | Cross-model validation, temporal locks, capacity checks — these are `create()`/`write()` overrides with `ValidationError`. Every non-trivial Odoo module has them. | MEDIUM | FLAW-03 | Generate `create()`/`write()` overrides. Each constraint queries related models, raises `ValidationError` with translatable message. Must call `super()` correctly. Temporal constraints check date fields. Capacity constraints use `search_count()`. |

### Differentiators (Competitive Advantage)

Features that elevate generated modules from "scaffolds you rewrite" to "production-ready code you extend." No competing Odoo generator (Gemini-Odoo-Module-Generator, Odoo Studio) handles these.

| Feature | Value Proposition | Complexity | FLAW | Notes |
|---------|-------------------|------------|------|-------|
| QWeb report template generation | Universities/businesses need transcripts, invoices, certificates. Generating the full report pipeline (ir.actions.report + QWeb template + paper format + form button) saves hours of boilerplate per report. | HIGH | FLAW-08 | Requires: XML `ir.actions.report` record, QWeb template with `t-foreach`/`t-field`/`t-esc`, paper format definition, button in form view. Templates must use `external_layout` for headers/footers. PDF rendered by wkhtmltopdf. Must handle multi-record reports. |
| Dashboard/analytics view generation | Graph, pivot, and cohort views are standard Odoo view types but rarely auto-generated. Providing them out-of-the-box makes modules immediately useful for managers. | MEDIUM | FLAW-09 | Graph view XML with `<field type="measure">` and `<field type="row/col">`. Pivot view XML with same field semantics. `ir.actions.act_window` with `view_mode` including graph/pivot. Menu item under "Reporting" parent. Cohort view needs `date_start`/`date_stop` fields on model. |
| HTTP controller / REST endpoint generation | Middleware integration, webhooks, portal pages all need `@http.route` controllers. No generator produces these. | MEDIUM | FLAW-10 | Generate `controllers/main.py` + `controllers/__init__.py`. Routes with `type='json'` or `type='http'`, auth levels (`api_key` in Odoo 17+, `user`, `public`). JSON serialization (recordsets to dicts). CSRF handling (`csrf=False` for API endpoints). Error handling with HTTP status codes. Must add `controllers` import to root `__init__.py`. |
| Import/export wizard generation | Bulk data operations (enrollment lists, fee schedules, grade imports) are universal. Generating the full wizard with file parsing, validation, preview, and batch creation is a major time saver. | HIGH | FLAW-12 | TransientModel with `fields.Binary` for upload. Parse with `openpyxl` (xlsx) or `csv` module. Row-by-row validation collecting errors into `line_ids` One2many. Preview step. Batch `create()` in `_do_import()`. Export: build xlsx, return as download via `base64.b64encode`. New dependency: `openpyxl` in manifest `external_dependencies`. |
| Bulk operation patterns | `@api.model_create_multi`, batch processing with progress — these prevent timeout disasters at scale. Generating them proactively is preventive engineering. | MEDIUM | FLAW-13 | `@api.model_create_multi` on `create()` with batched post-processing. Batch processing wizard: domain-based selection, `_process_batch(records, batch_size=100)` chunking, `bus.bus` progress notifications. Must handle error collection (partial success). |
| Reference data caching (ormcache) | `@tools.ormcache` on frequently-called lookup methods for near-static data prevents unnecessary DB queries. Subtle but impactful for performance. | LOW | FLAW-15 | `@tools.ormcache('self.id')` on lookup methods. Cache invalidation in `write()` and `create()` via `self.env.registry.clear_cache()`. Critical: never return recordsets from cached methods (causes psycopg2 errors — cursor closed). Only cache ID-based lookups returning plain values. |
| Archival/partitioning strategy | `active` field with archive actions, cleanup crons, `_transient_max_hours` — production modules need data lifecycle management. | LOW | FLAW-16 | `active = fields.Boolean(default=True)`. Server actions for archive/unarchive. Cron for age-based archival. `mail.message` cleanup cron (delete tracking messages older than retention period). Odoo's built-in `Base: Auto-vacuum internal data` handles TransientModel cleanup; configure via `_transient_max_hours` (default 1 hour). |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full dynamic RBAC framework (FLAW-05) | Institutions want granular roles beyond User/Manager. | Generating a dynamic RBAC engine (uni.role, uni.role.permission, runtime ir.model.access sync) is a separate product. Couples generator to a specific security architecture, bloats every module, and the sync mechanism is fragile. | Defer to a dedicated `uni_security` module designed manually. For v3.1, focus on generating more security groups from spec (not just 2) and `groups=` attributes on sensitive fields. |
| Audit trail beyond chatter (FLAW-07) | HEC compliance requires structured audit logs. | Generating a full audit mixin overriding `write()` on every model adds significant overhead. The mixin must use `sudo()`, handle recursive writes, and manage its own storage. Easy to get wrong. | Defer to a dedicated module. The OCA `auditlog` module exists and is production-tested. Reference it in generated docs rather than reinventing. |
| Webhook/event pattern (FLAW-11) | Enrollment triggers notifications, integrations. | Event-driven hooks require an event bus architecture, external API clients, retry logic, and error handling far beyond template generation scope. | Generate `_post_create_hook()` and `_post_write_hook()` stub methods that modules can fill in. Do not generate external API clients. |
| Multi-level approval workflows (FLAW-18) | Many business processes need approval chains. | State machines with conditional branching, multi-approver logic, delegation, and timeout escalation are domain-specific and brittle to auto-generate. | Defer to v3.2. For v3.1, generate clean state Selection fields with button methods and group-based access — the foundation approval workflows build on. |
| Notification/alert generation (FLAW-19) | State changes should trigger emails/WhatsApp. | Generating `mail.template` XML with `${object.field}` syntax and multi-channel dispatch creates tightly-coupled notification code. | Defer to v3.2. For v3.1, mail.thread (already fixed in v3.0) provides chatter notifications out of the box. |

## Feature Dependencies

```
FLAW-04: Monetary fields (standalone, no dependencies)

FLAW-01: Relationship patterns
    |--- enhances ---> FLAW-02: Computed dependency chains (chains often cross relationships)
    |--- enhances ---> FLAW-03: Complex constraints (cross-model constraints need relationship awareness)

FLAW-02: Computed dependency chains
    |--- requires ---> FLAW-14: DB performance patterns (store=True strategy is critical)

FLAW-14: DB performance patterns
    |--- enhances ---> FLAW-16: Archival/partitioning (_transient cleanup, index strategy)
    |--- enhances ---> FLAW-15: Reference data caching (ormcache complements index strategy)

FLAW-20: Scheduled actions (standalone, but enables FLAW-16 archival crons)
    |--- enhances ---> FLAW-16: Archival/partitioning (cron-driven cleanup)

FLAW-08: QWeb reports (standalone)

FLAW-09: Dashboard views (standalone)

FLAW-10: HTTP controllers (standalone)

FLAW-12: Import/export wizards
    |--- enhances ---> FLAW-13: Bulk operations (import wizards use batch create)

FLAW-13: Bulk operations (standalone, but enhanced by FLAW-12)
```

### Dependency Notes

- **FLAW-01 (relationships) enhances FLAW-02 (computed chains):** Dependency chains frequently traverse relationships (e.g., `line_ids.subtotal` on an order). Relationship pattern awareness makes chain generation more accurate.
- **FLAW-02 (computed chains) requires FLAW-14 (DB performance):** `store=True` strategy is critical for computed chains. Without it, chains cause N+1 query problems. These should be implemented together or FLAW-14 first.
- **FLAW-12 (import/export) enhances FLAW-13 (bulk ops):** Import wizards are the primary consumer of `@api.model_create_multi` and batch processing patterns. Implementing together creates synergy.
- **FLAW-20 (cron) enhances FLAW-16 (archival):** Archival strategies depend on scheduled actions for automated cleanup. FLAW-20 should land before or alongside FLAW-16.

## MVP Definition

### Phase 1: Spec Design Patterns (foundation for everything else)

- [ ] FLAW-04: Monetary field pattern -- LOW complexity, HIGH impact, zero dependencies, immediate quality improvement
- [ ] FLAW-01: Relationship pattern awareness -- MEDIUM complexity, unlocks FLAW-02 and FLAW-03
- [ ] FLAW-02: Computed field dependency chains -- MEDIUM complexity, requires relationship awareness
- [ ] FLAW-03: Complex constraint support -- MEDIUM complexity, requires relationship awareness

### Phase 2: Template Generation Capabilities (new artifact types)

- [ ] FLAW-08: QWeb report generation -- HIGH complexity, but standalone; differentiator
- [ ] FLAW-09: Dashboard/analytics views -- MEDIUM complexity, standalone; differentiator
- [ ] FLAW-10: HTTP controller generation -- MEDIUM complexity, standalone; differentiator
- [ ] FLAW-12: Import/export wizard generation -- HIGH complexity, pairs with FLAW-13

### Phase 3: Performance Patterns (production-readiness)

- [ ] FLAW-20: Scheduled action generation -- LOW complexity, enables FLAW-16
- [ ] FLAW-13: Bulk operation patterns -- MEDIUM complexity, pairs with FLAW-12
- [ ] FLAW-14: Database performance patterns -- LOW complexity, HIGH impact on module quality
- [ ] FLAW-15: Reference data caching -- LOW complexity, subtle but impactful
- [ ] FLAW-16: Archival/partitioning strategy -- LOW complexity, needs FLAW-20 for crons

### Deferred to v3.2+

- [ ] FLAW-05: Dynamic RBAC framework -- too large, separate product concern
- [ ] FLAW-07: Audit trail beyond chatter -- use OCA auditlog module instead
- [ ] FLAW-11: Webhook/event pattern -- needs event bus architecture
- [ ] FLAW-18: Multi-level approval workflows -- domain-specific, brittle to auto-generate
- [ ] FLAW-19: Notification/alert generation -- tightly-coupled, defer after mail.thread is solid

## Feature Prioritization Matrix

| Feature | FLAW | User Value | Impl Cost | Priority | Phase |
|---------|------|------------|-----------|----------|-------|
| Monetary field pattern | FLAW-04 | HIGH | LOW | P1 | 1 |
| Relationship patterns | FLAW-01 | HIGH | MEDIUM | P1 | 1 |
| Computed dependency chains | FLAW-02 | HIGH | MEDIUM | P1 | 1 |
| Complex constraints | FLAW-03 | HIGH | MEDIUM | P1 | 1 |
| Database performance patterns | FLAW-14 | HIGH | LOW | P1 | 3 |
| Scheduled actions | FLAW-20 | HIGH | LOW | P1 | 3 |
| QWeb report generation | FLAW-08 | HIGH | HIGH | P2 | 2 |
| Dashboard/analytics views | FLAW-09 | MEDIUM | MEDIUM | P2 | 2 |
| HTTP controllers | FLAW-10 | MEDIUM | MEDIUM | P2 | 2 |
| Import/export wizards | FLAW-12 | MEDIUM | HIGH | P2 | 2 |
| Bulk operations | FLAW-13 | MEDIUM | MEDIUM | P2 | 3 |
| Reference data caching | FLAW-15 | MEDIUM | LOW | P2 | 3 |
| Archival/partitioning | FLAW-16 | MEDIUM | LOW | P2 | 3 |

**Priority key:**
- P1: Must have -- table stakes that make generated modules production-viable
- P2: Should have -- differentiators and production-readiness polish

## Existing Infrastructure Each Feature Touches

Understanding what already exists is critical for scoping implementation work.

| Feature | Existing Code Touched | New Files Created |
|---------|----------------------|-------------------|
| FLAW-04: Monetary | `renderer.py` (model context builder), `model.py.j2` | None -- modify existing templates |
| FLAW-01: Relationships | `renderer.py` (field generation), spec schema | None -- spec schema extension + template logic |
| FLAW-02: Computed chains | `renderer.py` (field generation), `model.py.j2` | None -- spec schema extension |
| FLAW-03: Constraints | `renderer.py` (model context), `model.py.j2` | None -- spec schema + template logic |
| FLAW-08: QWeb reports | `renderer.py` (new render stage), manifest template | `report_action.xml.j2`, `report_template.xml.j2` |
| FLAW-09: Dashboards | `renderer.py` (new render stage), action template | `view_graph.xml.j2`, `view_pivot.xml.j2` |
| FLAW-10: Controllers | `renderer.py` (new render stage), `init_root.py.j2` | `controller.py.j2`, `init_controllers.py.j2` |
| FLAW-12: Import/export | `renderer.py` (new render stage), manifest | `import_wizard.py.j2`, `import_wizard_form.xml.j2` |
| FLAW-20: Cron | `renderer.py` (data stage) | `cron.xml.j2` or extend existing data.xml generation |
| FLAW-13: Bulk ops | `model.py.j2` (create_multi), renderer | `bulk_wizard.py.j2` (optional) |
| FLAW-14: DB perf | `renderer.py` (field attrs), `model.py.j2` | None -- auto-detect in existing pipeline |
| FLAW-15: Caching | `model.py.j2` (method decorators) | None -- pattern injection in model template |
| FLAW-16: Archival | `model.py.j2` (active field), cron generation | Reuses FLAW-20 cron infrastructure |

## Competitor Feature Analysis

| Feature | Odoo Studio | Gemini-Odoo-Generator | Our Approach |
|---------|-------------|----------------------|--------------|
| Monetary fields | Auto-detects in UI | Not handled | Auto-detect from field names + spec type |
| Relationships | UI drag-drop, no through-models | Basic M2O only | Through-models, self-ref M2M, parent_id hierarchy |
| Computed chains | Single-level only | Not handled | Multi-model chains with correct depends paths |
| QWeb reports | Manual template editor | Not handled | Full pipeline: action + template + paper format + button |
| Dashboard views | Built-in dashboard builder | Not handled | Generate graph/pivot XML + menu items |
| HTTP controllers | Not supported | Not handled | Full controller with auth, CORS, error handling |
| Import/export | Built-in generic import | Not handled | Domain-specific wizard with validation + preview |
| Cron jobs | UI configuration | Not handled | XML data records + model methods |
| DB performance | Not exposed | Not handled | Auto-detect index, store, _order, _transient |
| Caching | Not exposed | Not handled | ormcache on lookup methods with invalidation |

## Sources

- [Odoo 17.0 ORM API documentation](https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html) -- HIGH confidence: official docs for fields, depends, store, index, constraints
- [Odoo 17.0 Computed Fields tutorial](https://www.odoo.com/documentation/17.0/developer/tutorials/server_framework_101/08_compute_onchange.html) -- HIGH confidence: chain dependencies, store=True behavior
- [Odoo 18.0 QWeb Reports](https://www.odoo.com/documentation/18.0/developer/reference/backend/reports.html) -- HIGH confidence: ir.actions.report pattern, template structure
- [Odoo 18.0 Web Controllers](https://www.odoo.com/documentation/18.0/developer/reference/backend/http.html) -- HIGH confidence: http.route, auth levels, CSRF
- [Odoo 17.0 ORM Cache (Cybrosys)](https://www.cybrosys.com/odoo/odoo-books/odoo-17-development/performance-optimisation/orm-cache/) -- MEDIUM confidence: ormcache usage patterns, never return recordsets
- [Odoo Monetary Fields (Cybrosys)](https://www.cybrosys.com/odoo/odoo-books/odoo-17-development/creating-odoo-modules/monetary-fields/) -- MEDIUM confidence: currency_id pattern
- [Odoo Self-referential M2M (Forum)](https://www.odoo.com/forum/help-1/model-with-many2many-relation-to-his-self-87223) -- MEDIUM confidence: relation/column1/column2 requirement
- [ir.cron patterns (readthedocs)](https://odoo-development.readthedocs.io/en/latest/odoo/models/ir.cron.html) -- MEDIUM confidence: cron XML structure, noupdate requirement
- [Mastering Odoo Controller Routes (Dec 2025)](https://medium.com/@niralchaudhary9/mastering-odoo-controller-routes-the-complete-developers-guide-5b47302ff1c7) -- MEDIUM confidence: api_key auth (Odoo 17+), CORS patterns
- [Custom XLSX Import Wizard (Numla)](https://numla.com/blog/odoo-development-18/creating-custom-xlsx-import-wizard-in-odoo-286) -- MEDIUM confidence: openpyxl pattern, base64 handling
- [Odoo Query Optimizations 17-19 (Stormatics)](https://stormatics.tech/blogs/query-optimizations-in-odoo-versions-17-19-for-faster-postgresql-performance) -- MEDIUM confidence: declarative index API in 18.x+
- [Odoo Performance Optimization 2025 (Medium)](https://medium.com/@jacobweber005/odoo-app-performance-optimization-speed-scalability-trends-for-2025-aed068e6dabe) -- LOW confidence: trends article, not authoritative

---
*Feature research for: Odoo module automation v3.1 -- Design Flaws & Feature Gaps*
*Researched: 2026-03-05*
