# Requirements: Odoo Module Automation

**Defined:** 2026-03-05
**Core Value:** Compress months of repetitive Odoo module development into days by extending GSD's orchestration with Odoo-specialized agents, knowledge, and validation.

## v3.1 Requirements

Requirements for v3.1 Design Flaws & Feature Gaps. Each maps to roadmap phases.

### Spec Design

- [ ] **SPEC-01**: Renderer auto-detects Monetary field patterns (amount, fee, salary, price, cost, balance) and generates `fields.Monetary` with `currency_id` injection — FLAW-04
- [ ] **SPEC-02**: Spec supports a `relationships` section with through-models for M2M with extra fields, self-referential M2M (with explicit relation/column params), and hierarchical parent_id patterns — FLAW-01
- [ ] **SPEC-03**: Spec supports `computation_chains` section defining multi-model computed field chains with correct `@api.depends`, `store=True`, and computation order via topological sort — FLAW-02
- [ ] **SPEC-04**: Spec supports `constraints` section with cross-model validation, temporal constraints, and capacity constraints generating `create()`/`write()` overrides with `ValidationError` — FLAW-03
- [ ] **SPEC-05**: Spec validation detects circular dependency chains and rejects them with actionable error messages before generation

### Template Generation

- [ ] **TMPL-01**: Generator produces QWeb report templates (`ir.actions.report` XML + QWeb template) with form view button, paper format, and `t-foreach`/`t-field` syntax — FLAW-08
- [ ] **TMPL-02**: Generator produces graph and pivot view XML with configurable measures, dimensions, chart types, and `ir.actions.act_window` with graph/pivot view_mode — FLAW-09
- [ ] **TMPL-03**: Generator produces HTTP controllers (`controllers/main.py`) with `@http.route`, JSON/HTTP types, authentication modes, CSRF protection, and input validation — FLAW-10
- [ ] **TMPL-04**: Generator produces import/export TransientModel wizards with `fields.Binary` upload, row validation, preview step, batch `_do_import()`, and xlsx export — FLAW-12
- [ ] **TMPL-05**: Generator produces `ir.cron` XML records in `data/data.xml` with interval, model reference, and `@api.model` stub method on the target model — FLAW-20
- [ ] **TMPL-06**: New render stages (`render_reports`, `render_controllers`, `render_cron`) wired into renderer pipeline returning `Result[list[Path]]`

### Performance Patterns

- [ ] **PERF-01**: Renderer auto-adds `index=True` to fields used in search view filters, record rule domains, or `_order`; generates composite `sql_constraints` for multi-field uniqueness — FLAW-14
- [ ] **PERF-02**: Models with `bulk: true` in spec generate `@api.model_create_multi` on `create()` with batched post-processing — FLAW-13
- [ ] **PERF-03**: Near-static reference models (few records, rarely written) generate `@tools.ormcache` on lookup methods with cache invalidation in `write()`/`create()` — FLAW-15
- [ ] **PERF-04**: Models with `archival: true` generate `active` field, archival wizard TransientModel, and `ir.cron` scheduled action for periodic archival — FLAW-16
- [ ] **PERF-05**: Computed fields appearing in tree views, search filters, or `_order` automatically get `store=True`; TransientModels get `_transient_max_hours` and `_transient_max_count`

## Future Requirements (v3.2+)

### Security

- **SECR-01**: Dynamic RBAC framework with role/permission models and runtime ir.model.access sync — FLAW-05
- **SECR-02**: Field-level security with `groups=` attributes on sensitive fields — FLAW-06
- **SECR-03**: Structured audit trail model with mixin and write() override — FLAW-07

### Business Logic

- **BIZL-01**: Multi-level approval workflows with conditional branching — FLAW-18
- **BIZL-02**: Notification/alert generation with mail.template and channel dispatch — FLAW-19
- **BIZL-03**: Webhook/event pattern with hook methods in create()/write() — FLAW-11

### Domain/Localization

- **DOMN-01**: Document management pattern with verification workflow — FLAW-21
- **DOMN-02**: Pakistan/HEC localization framework (CNIC, phone, PKR) — FLAW-22
- **DOMN-03**: Semester/academic calendar awareness — FLAW-23

### Tooling/DevOps

- **TOOL-01**: Migration script generation from spec diff — FLAW-17
- **TOOL-02**: Dev environment generation (docker-compose.dev.yml, devcontainer) — FLAW-24
- **TOOL-03**: Module dependency visualization (Mermaid graph) — FLAW-25
- **TOOL-04**: Spec diffing between versions — FLAW-26

### Architecture

- **ARCH-01**: Project context / model registry for cross-module awareness — FLAW-27
- **ARCH-02**: Structured generation manifest for checker — FLAW-28
- **ARCH-03**: Semantic validation beyond pylint+Docker — FLAW-29
- **ARCH-04**: Human checkpoint hooks in generation pipeline — FLAW-30
- **ARCH-05**: Generation state persistence with resume — FLAW-31

## Out of Scope

| Feature | Reason |
|---------|--------|
| odoo-gsd fork references (FLAW-32) | Deferred until GSD fork is complete |
| Full Pydantic spec validation | May add in v3.2 if spec complexity warrants it |
| QWeb PDF rendering validation in Docker | wkhtmltopdf testing too fragile for automated CI |
| openpyxl as core dependency | Only needed in generated module runtime, not in odoo-gen-utils |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SPEC-01 | TBD | Pending |
| SPEC-02 | TBD | Pending |
| SPEC-03 | TBD | Pending |
| SPEC-04 | TBD | Pending |
| SPEC-05 | TBD | Pending |
| TMPL-01 | TBD | Pending |
| TMPL-02 | TBD | Pending |
| TMPL-03 | TBD | Pending |
| TMPL-04 | TBD | Pending |
| TMPL-05 | TBD | Pending |
| TMPL-06 | TBD | Pending |
| PERF-01 | TBD | Pending |
| PERF-02 | TBD | Pending |
| PERF-03 | TBD | Pending |
| PERF-04 | TBD | Pending |
| PERF-05 | TBD | Pending |

**Coverage:**
- v3.1 requirements: 16 total
- Mapped to phases: 0
- Unmapped: 16 (pending roadmap creation)

---
*Requirements defined: 2026-03-05*
*Last updated: 2026-03-05 after initial definition*
