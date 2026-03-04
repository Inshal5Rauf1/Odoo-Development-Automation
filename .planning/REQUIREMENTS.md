# Requirements: v2.1 Auto-Fix & Enhancements

**Defined:** 2026-03-04
**Core Value:** Compress months of repetitive Odoo module development into days by extending GSD's orchestration with Odoo-specialized agents, knowledge, and validation.

## v2.1 Requirements

### Auto-Fix

- [ ] **DFIX-01**: Docker auto-fix pipeline identifies all 5 common error patterns (missing module dependency, missing field reference in view XML, security access violation, missing data file in manifest, missing mail.thread inheritance) and provides automated fixes for those that are mechanically deterministic (missing_import requires human judgment and escalates with actionable message)
- [ ] **AFIX-01**: Both pylint and Docker fix loops are capped at a configurable maximum (default: 5 iterations); when the cap is reached, remaining errors are reported and the loop stops
- [ ] **AFIX-02**: Running `validate --auto-fix` on a module with known pylint violations resolves them automatically, verified by an integration test that runs in CI without Docker

### MCP

- [ ] **MCP-05**: Agents can query Odoo 17.0/18.0 API documentation on demand via Context7 MCP, with the knowledge base remaining the primary source and Context7 supplementing; generation works without Context7 configured (graceful fallback)

### Observability

- [ ] **OBS-01**: Each artifact (model, view, security, test) has a tracked state (pending, generated, validated, approved) stored as structured metadata, visible via CLI output or log; state tracking does not block generation if it fails

## Future Requirements

None currently — v2.1 closes remaining v2.0 deferrals.

## Out of Scope

| Feature | Reason |
|---------|--------|
| MCP server expansion (new tools) | v2.0 shipped 6 tools which cover generation needs |
| Odoo 18.0 MCP testing | Primary target is 17.0; 18.0 deferred |
| Real-time collaborative generation | Single-user workflow |
| Web dashboard for observability | CLI/log output sufficient for v2.1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DFIX-01 | Phase 18: Auto-Fix Hardening | Pending |
| AFIX-01 | Phase 18: Auto-Fix Hardening | Pending |
| AFIX-02 | Phase 18: Auto-Fix Hardening | Pending |
| MCP-05 | Phase 19: Enhancements | Pending |
| OBS-01 | Phase 19: Enhancements | Pending |

**Coverage:**
- v2.1 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0

---
*Requirements defined: 2026-03-04*
*Last updated: 2026-03-04 after milestone v2.1 initialization*
