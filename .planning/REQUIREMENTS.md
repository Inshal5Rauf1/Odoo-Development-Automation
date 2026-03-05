# Requirements: Odoo Module Automation v3.0

**Defined:** 2026-03-05
**Core Value:** Compress months of repetitive Odoo module development into days by extending GSD's orchestration with Odoo-specialized agents, knowledge, and validation.

## v3.0 Requirements

### Auto-Fix Pipeline (AST Migration)

- [x] **AFIX-01**: Auto-fix functions use AST-based source modification instead of regex for all 5 pylint fixers (_fix_w8113, _fix_w8111, _fix_c8116, _fix_w8150, _fix_c8107), handling multi-line expressions correctly
- [x] **AFIX-02**: Unused import detection scans full AST body for name references instead of 4-name whitelist, removing any import with zero references in file body

### Template Correctness

- [x] **TMPL-01**: mail.thread injection respects per-model chatter flag (default true for top-level business models, false for config tables, line items, wizards, and models extending parents with mail.thread)
- [x] **TMPL-02**: Wizard template conditionally imports api only when @api decorators are used in generated wizard methods
- [x] **TMPL-03**: Wizard TransientModels receive ACL entries in ir.model.access.csv alongside regular models
- [x] **TMPL-04**: Test template uses display_name assertion instead of deprecated name_get() method, with version gate for Odoo 18.0 compatibility

### Validation Infrastructure

- [x] **VALD-01**: docker_install_module uses `docker compose run --rm` instead of `docker compose exec`, eliminating serialization race condition
- [x] **VALD-02**: Validation pipeline uses unified Result[T] type with success/data/errors fields across auto_fix, docker_runner, pylint_runner, and verifier modules

### Search Infrastructure

- [x] **SRCH-01**: GitHub API calls in index builder check X-RateLimit-Remaining header, sleep until reset when low, and retry with exponential backoff on 403/429 responses
- [x] **SRCH-02**: AST analyzer detects _inherit-only model extensions (models with _inherit but no _name) and records them in ModuleAnalysis.inherited_models

### Code Quality

- [x] **QUAL-01**: CLI defers heavy imports (chromadb, PyGithub, gitpython, Docker, validation stack) inside command functions, keeping module-level imports to click and stdlib only
- [x] **QUAL-02**: render_module decomposed from 371-line monolith into independently testable stage functions (render_manifest, render_models, render_views, render_security, render_wizards, render_tests, render_static)
- [x] **QUAL-03**: Docker compose file path resolved via importlib.resources or configuration instead of 5-level parent directory traversal

### Tech Debt Cleanup

- [ ] **DEBT-01**: All test files consuming docker_install_module and docker_run_tests correctly unwrap Result[T] objects (access .data before using InstallResult/TestResult fields)

## v3.1 Requirements (Deferred)

### Design Flaws — Feature Gaps

24 confirmed design flaws deferred from v3.0. See BUGS_FLAWS_DEBT.md FLAW-01 through FLAW-26 for full descriptions.

**Critical (v3.1 priority):**
- FLAW-04: Monetary field + currency_id pattern
- FLAW-14: Database performance (indexes, _order, store=True)
- FLAW-03: Cross-model constraint complexity
- FLAW-08: QWeb report template generation
- FLAW-19: Notification/email template generation
- FLAW-09: Dashboard/analytics view generation
- FLAW-10: HTTP controller generation

**High:**
- FLAW-01: Relationship pattern awareness (self-ref, hierarchical, through-model)
- FLAW-02: Computed field dependency chains
- FLAW-13: Bulk operation patterns (@api.model_create_multi)
- FLAW-18: Multi-level approval workflows

**Moderate:**
- FLAW-05, 06, 07, 11, 12, 15, 16, 20, 21, 24

**Low:**
- FLAW-17, 25, 26

## Out of Scope

| Feature | Reason |
|---------|--------|
| FLAW-22: Pakistan/HEC localization | Domain-specific, not general-purpose generator concern |
| FLAW-23: Semester/academic calendar | Domain-specific educational module, use OCA school/educa |
| Agent Lightning integration | Research showed architectural mismatch — agents are markdown files, not Python runtimes |
| Cognee integration | 30+ dependency explosion for 13 KB files too small for knowledge graph |
| Intelligence Layer (Layer 5) | Deferred pending baseline metrics and training data accumulation |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AFIX-01 | Phase 20 | Complete |
| AFIX-02 | Phase 20 | Complete |
| TMPL-01 | Phase 21 | Complete |
| TMPL-02 | Phase 21 | Complete |
| TMPL-03 | Phase 21 | Complete |
| TMPL-04 | Phase 21 | Complete |
| VALD-01 | Phase 22 | Complete |
| VALD-02 | Phase 23 | Complete |
| SRCH-01 | Phase 22 | Complete |
| SRCH-02 | Phase 22 | Complete |
| QUAL-01 | Phase 24 | Complete |
| QUAL-02 | Phase 24 | Complete |
| QUAL-03 | Phase 24 | Complete |
| DEBT-01 | Phase 25 | Pending |

**Coverage:**
- v3.0 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-03-05*
*Last updated: 2026-03-05 — traceability updated with phase mappings*
