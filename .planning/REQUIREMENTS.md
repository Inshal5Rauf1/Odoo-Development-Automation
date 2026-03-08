# Requirements: Odoo Module Automation

**Defined:** 2026-03-08
**Core Value:** Compress months of repetitive Odoo module development into days by extending GSD's orchestration with Odoo-specialized agents, knowledge, and validation.

## v4.0 Requirements

Requirements for v4.0 LLM Logic Writer & Generation Capabilities. Each maps to roadmap phases.

### Cleanup

- [x] **CLEN-01**: Fix docker_install_module() to use `docker compose run --rm` instead of `docker compose exec`, eliminating the serialization race condition documented in BUG-H2
- [x] **CLEN-02**: Delete artifact_state.py and remove all references to ModuleState, ArtifactState, save_state(), load_state() — GenerationManifest (Phase 54) is the replacement

### LLM Generation

- [x] **LGEN-01**: Logic Writer infrastructure — StubDetector that identifies TODO method bodies in generated Python files, MethodContext builder that assembles field definitions + spec business_rules + model registry context for each stub
- [x] **LGEN-02**: LLM integration point — call LLM with method context + KB/Context7 patterns, parse response, write implementation back into generated .py file; model routing (quality for complex, budget for simple)
- [x] **LGEN-03**: Computed field implementations — _compute_* methods with correct @api.depends, self.mapped/filtered patterns, store=True recomputation triggers
- [x] **LGEN-04**: Constraint implementations — _check_* methods with correct @api.constrains, ValidationError with user-facing messages, cross-field validation logic
- [x] **LGEN-05**: create()/write() override implementations — super() call pattern, business logic (auto-create related records, increment counters, trigger state changes), not audit/approval (already template-generated)
- [x] **LGEN-06**: Action and cron method implementations — action_* workflow transitions, _cron_* scheduled logic with correct @api.model decorator and domain queries
- [x] **LGEN-07**: Logic Writer output passes semantic validation (Phase 51 AST + XML cross-check) — generated method bodies reference correct field names and use valid ORM patterns

### Module Extension

- [ ] **MEXT-01**: Generate _inherit models that extend existing Odoo modules (e.g., _inherit = "hr.payslip" to add Pakistani tax fields) with correct super() patterns
- [ ] **MEXT-02**: Generate xpath view inheritance XML to inject fields into existing form/tree views from base modules
- [ ] **MEXT-03**: Generate correct __manifest__.py depends for extended modules and validate base module exists in Odoo model registry

### Iterative Refinement

- [ ] **ITER-01**: Add field to existing generated module — read generation manifest, inject field into model, update view XML, re-validate, without regenerating unchanged files
- [ ] **ITER-02**: Add model to existing generated module — create model file, update __init__.py, add views/security, update manifest depends, without regenerating existing models
- [ ] **ITER-03**: Re-run only affected stages using generation manifest to detect what exists and model registry to validate new references

### Computed Chains

- [ ] **CCHN-01**: Cross-model computed field chains — spec defines chain steps (e.g., exam.result.grade → enrollment.grade_points → student.cgpa), Logic Writer generates implementations across models
- [ ] **CCHN-02**: Correct @api.depends with related field notation for cross-model triggers and store=True strategy for fields that need recomputation when source changes
- [ ] **CCHN-03**: Chain validation — verify dependency order, detect cycles, ensure all intermediate fields exist in model registry

### Portal

- [ ] **PRTL-01**: Generate portal controllers inheriting portal.CustomerPortal with ir.http routes, authentication, and JSON serialization
- [ ] **PRTL-02**: Generate QWeb portal templates inheriting portal.portal_my_home with portal menu items and page templates
- [ ] **PRTL-03**: Generate portal-specific record rules restricting data to the portal user's linked records (e.g., parent sees only their child's data)

### Bulk Operations

- [ ] **BULK-01**: Generate @api.model_create_multi with batched post-processing — notifications chunked, not per-record
- [ ] **BULK-02**: Generate bulk wizard TransientModels with domain-based record selection, preview step, confirmation, and error collection
- [ ] **BULK-03**: Generate _process_batch() helpers with configurable batch_size, chunked processing, and bus.bus progress notifications

## Future Requirements (v4.1+)

### Deferred (build when pain demands it)

- **DFRD-01**: Pattern retriever (IMP-00A) — ChromaDB KB indexing for Logic Writer. Trigger: Logic Writer output quality plateaus.
- **DFRD-02**: Integration test runner (CHK-03) — cross-module Docker workflow tests. Trigger: generating 10+ modules reveals patterns semantic validation misses.
- **DFRD-03**: odoo-gsd orchestrator fork — specialized GSD for Odoo. Trigger: manual orchestration of 3-4 modules becomes unbearable.
- **DFRD-04**: Migration script generation (IMP-12) — spec diff → pre/post-migration. Trigger: first real module needs a schema change.
- **DFRD-05**: Archival strategy (IMP-27) — semester-based archival, mail.message cleanup. Trigger: data volume demands it.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Parent institution dashboard (IMP-03B) | Over-scoped. Basic security (Phase 37) is sufficient. |
| Setup wizard generator (NEW-07) | One-time use, low ROI. |
| ORM caching generation (IMP-17) | Premature optimization. Odoo's own ORM cache handles most cases. |
| KB versioning (IMP-22) | Only matters when Odoo 19.0 ships. |
| ChromaDB build optimization (IMP-19) | 3-5 min build time is acceptable. |
| Progress visibility (IMP-23) | Cosmetic, zero capability gain. |
| Devcontainer generation (IMP-24) | Contributors already have dev setup. |
| Full 7-pass LLM pipeline (IMP-00B complete) | Pass 2 (Logic Writer) only. Add other passes when needed. |
| View XML via LLM | Too structural, LLM adds noise. Jinja handles views well. |
| Security CSV via LLM | Deterministic, no creativity needed. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLEN-01 | Phase 55 | Complete |
| CLEN-02 | Phase 55 | Complete |
| LGEN-01 | Phase 56 | Complete |
| LGEN-02 | Phase 56 | Complete |
| LGEN-03 | Phase 57 | Complete |
| LGEN-04 | Phase 57 | Complete |
| LGEN-05 | Phase 58 | Complete |
| LGEN-06 | Phase 58 | Complete |
| LGEN-07 | Phase 57 | Complete |
| MEXT-01 | Phase 59 | Pending |
| MEXT-02 | Phase 59 | Pending |
| MEXT-03 | Phase 59 | Pending |
| ITER-01 | Phase 60 | Pending |
| ITER-02 | Phase 60 | Pending |
| ITER-03 | Phase 60 | Pending |
| CCHN-01 | Phase 61 | Pending |
| CCHN-02 | Phase 61 | Pending |
| CCHN-03 | Phase 61 | Pending |
| PRTL-01 | Phase 62 | Pending |
| PRTL-02 | Phase 62 | Pending |
| PRTL-03 | Phase 62 | Pending |
| BULK-01 | Phase 63 | Pending |
| BULK-02 | Phase 63 | Pending |
| BULK-03 | Phase 63 | Pending |

**Coverage:**
- v4.0 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-03-08*
*Last updated: 2026-03-08 after milestone v4.0 definition*
