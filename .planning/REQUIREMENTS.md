# Requirements: v1.2 Template Quality

**Defined:** 2026-03-03
**Core Value:** Compress months of repetitive Odoo module development into days by extending GSD's orchestration with Odoo-specialized agents, knowledge, and validation.

## v1.2 Requirements

Requirements for this release. Each maps to roadmap phases.

### Template Fixes

- [ ] **TMPL-01**: model.py.j2 adds `_inherit = ['mail.thread', 'mail.activity.mixin']` when `mail` is in depends (both 17.0 and 18.0)
- [ ] **TMPL-02**: model.py.j2 only imports `api` when @api.* decorators are used (both 17.0 and 18.0)
- [ ] **TMPL-03**: manifest.py.j2 does not emit `installable: True` or `auto_install: False` (Odoo defaults)
- [ ] **TMPL-04**: test_model.py.j2 does not import unused `ValidationError`

### Regression Prevention

- [ ] **REGR-01**: Golden path E2E test renders a realistic module spec (with mail dependency), Docker-installs it, and asserts successful installation
- [ ] **REGR-02**: Golden path E2E test runs the generated module's Odoo tests inside Docker and asserts they pass

### Auto-Fix Expansion

- [ ] **AFIX-01**: Auto-fix detects missing `mail.thread` inheritance when chatter XML references exist and adds the `_inherit` line
- [ ] **AFIX-02**: Auto-fix detects and removes unused imports in generated Python files (e.g., `ValidationError`, `api`)

### Knowledge Base

- [ ] **KNOW-01**: Model generation knowledge file documents when `_inherit = ['mail.thread', 'mail.activity.mixin']` is required
- [ ] **KNOW-02**: Model generation knowledge file documents the relationship between `mail` dependency, chatter XML, and model inheritance

## Future Requirements

(Deferred to v1.3+)

- Odoo 18.0 Docker validation (17.0 first)
- Auto-fix for more structural patterns (computed field dependencies, security group references)
- Template linting tool that validates template output against Odoo schema

## Out of Scope

| Feature | Reason |
|---------|--------|
| New commands or agents | v1.2 is quality hardening only |
| Odoo 18.0 Docker validation | 17.0 coverage first, 18.0 in future milestone |
| Template performance optimization | Not needed at current scale |
| UI/UX changes to CLI output | No user-facing workflow changes |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TMPL-01 | Phase 12 | Pending |
| TMPL-02 | Phase 12 | Pending |
| TMPL-03 | Phase 12 | Pending |
| TMPL-04 | Phase 12 | Pending |
| REGR-01 | Phase 13 | Pending |
| REGR-02 | Phase 13 | Pending |
| AFIX-01 | Phase 12 | Pending |
| AFIX-02 | Phase 12 | Pending |
| KNOW-01 | Phase 12 | Pending |
| KNOW-02 | Phase 12 | Pending |

**Coverage:**
- v1.2 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 after roadmap creation*
