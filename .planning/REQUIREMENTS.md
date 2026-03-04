# Requirements: v2.0 Environment-Aware Generation

**Milestone:** v2.0
**Core thesis:** Move from "generate then validate" to "verify as you generate" by connecting agents to a live Odoo instance via MCP.

---

## Must-Have

### MCP-01: Odoo Dev Instance Setup
**As a** developer using odoo-gen, **I need** a running Odoo dev instance accessible via XML-RPC/JSON-RPC, **so that** agents can introspect the live environment during module generation.

**Acceptance criteria:**
- [x] Docker Compose config spins up Odoo 17.0 CE with PostgreSQL
- [x] Instance is accessible via XML-RPC at configurable host:port
- [x] Pre-installed with common modules (base, mail, sale, purchase, hr, account)
- [x] Startup script or CLI command to launch/stop the dev instance
- [x] Instance persists data between restarts (named volume)
- [x] Documented in README

### MCP-02: Odoo MCP Server — Model Introspection
**As a** code generation agent, **I need** to query the live Odoo instance for model schemas and field definitions, **so that** I can verify inheritance chains and field references before generating code.

**Acceptance criteria:**
- [ ] MCP server connects to Odoo via XML-RPC (`xmlrpc.client.ServerProxy`)
- [ ] Tool: `list_models` — returns all ir.model records with model name and description
- [ ] Tool: `get_model_fields` — returns ir.model.fields for a given model (name, type, relation, required, readonly)
- [ ] Tool: `list_installed_modules` — returns installed module names and versions
- [ ] Tool: `check_module_dependency` — verifies if a module is installed
- [ ] Tool: `get_view_arch` — retrieves XML view architecture for a model
- [ ] Authentication via environment variables (ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY)
- [ ] Graceful error handling when Odoo instance is unreachable
- [ ] Unit tests for each tool with mocked XML-RPC responses

### MCP-03: Inline Environment Verification — Model Generation
**As a** model generation agent, **I need** to verify inheritance chains and field references against the live Odoo instance during generation, **so that** errors are caught at source rather than during Docker validation.

**Acceptance criteria:**
- [ ] Before generating `_inherit` model: verify base model exists via MCP
- [ ] Before generating relational fields (Many2one, One2many, Many2many): verify target model exists
- [ ] Before generating field overrides: verify original field exists with expected type
- [ ] Verification results logged with pass/fail per check
- [ ] Generation proceeds with warnings (not blocking) when MCP is unavailable
- [ ] Integration test: generate model inheriting hr.employee → verify MCP checks fire

### MCP-04: Inline Environment Verification — View Generation
**As a** view generation agent, **I need** to verify field references in XML views against the actual model schema, **so that** views reference only fields that exist.

**Acceptance criteria:**
- [ ] Before generating form/tree/kanban views: fetch model fields via MCP
- [ ] Verify each `<field name="X">` references a real field on the model
- [ ] Verify inherited view targets exist (ref to base view)
- [ ] Report mismatches as warnings with suggested corrections
- [ ] Graceful degradation when MCP unavailable (fall back to current static generation)
- [ ] Integration test: generate view referencing non-existent field → verify warning raised

### DFIX-01: Expanded Docker Fix Patterns
**As a** developer, **I need** the auto-fix pipeline to handle all 5 common Docker error patterns, **so that** more failures are resolved automatically without human intervention.

**Acceptance criteria:**
- [ ] Pattern: missing module dependency → auto-add to manifest `depends`
- [ ] Pattern: missing field reference in view XML → suggest field addition or view fix
- [ ] Pattern: security access violation → auto-generate missing ACL entry
- [ ] Pattern: missing data file in manifest → auto-add to `data` list
- [ ] Pattern: missing mail.thread inheritance → existing fix (already implemented)
- [ ] Each pattern has unit tests with sample Docker error output
- [ ] `FIXABLE_DOCKER_PATTERNS` updated from 1/5 to 5/5
- [ ] Integration test: module with each error type → auto-fix resolves it

---

## Should-Have

### MCP-05: Context7 MCP Integration
**As a** code generation agent, **I need** real-time access to Odoo documentation via Context7, **so that** I can reference accurate API docs, field types, and widget options during generation.

**Acceptance criteria:**
- [ ] Context7 MCP server configured in agent environment
- [ ] Agents can query Odoo 17.0/18.0 API documentation on demand
- [ ] Knowledge base remains primary source (WRONG/CORRECT patterns); Context7 supplements
- [ ] Fallback: agents work without Context7 (existing static KB used)
- [ ] Documented setup instructions for Context7 MCP

### AFIX-01: Bounded Auto-Fix Iterations
**As a** developer, **I need** auto-fix loops to have explicit iteration caps, **so that** infinite cycling is prevented and failures escalate to human review.

**Acceptance criteria:**
- [ ] Pylint fix loop capped at configurable max (default: 5)
- [ ] Docker fix loop capped at configurable max (default: 5)
- [ ] When cap reached: stop, report remaining errors, escalate to human
- [ ] Cap configurable via config.json or CLI flag
- [ ] Unit test: simulate infinite loop scenario → verify cap triggers

### AFIX-02: CLI --auto-fix Integration Test
**As a** maintainer, **I need** an integration test for the `validate --auto-fix` CLI path, **so that** the full auto-fix pipeline is verified end-to-end.

**Acceptance criteria:**
- [ ] Test creates a module with known pylint violations
- [ ] Runs `validate --auto-fix` via CLI
- [ ] Asserts violations are resolved after auto-fix
- [ ] Test runs in CI (no Docker dependency for this test)
- [ ] Covers at least: unused import (W0611), missing mail.thread

---

## Could-Have

### OBS-01: Generation Pipeline Observability
**As a** developer debugging generation failures, **I need** visibility into artifact progression through generation stages, **so that** I can identify where generation went wrong.

**Acceptance criteria:**
- [ ] Each artifact (model, view, security, test) has a tracked state: pending → generated → validated → approved
- [ ] State stored as structured metadata (JSON or YAML)
- [ ] CLI command or log output shows current pipeline state
- [ ] State transitions logged with timestamps
- [ ] Graceful: does not block generation if state tracking fails

---

## Summary

| ID | Requirement | Priority | Category |
|----|-------------|----------|----------|
| MCP-01 | Odoo Dev Instance Setup | Must | Infrastructure |
| MCP-02 | Odoo MCP Server — Model Introspection | Must | MCP |
| MCP-03 | Inline Verification — Models | Must | Verification |
| MCP-04 | Inline Verification — Views | Must | Verification |
| DFIX-01 | Expanded Docker Fix Patterns | Must | Auto-Fix |
| MCP-05 | Context7 MCP Integration | Should | MCP |
| AFIX-01 | Bounded Auto-Fix Iterations | Should | Auto-Fix |
| AFIX-02 | CLI --auto-fix Integration Test | Should | Testing |
| OBS-01 | Generation Pipeline Observability | Could | Observability |

**Total:** 9 requirements (5 must, 3 should, 1 could)

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MCP-01 | Phase 15: Odoo Dev Instance | Complete |
| MCP-02 | Phase 16: Odoo MCP Server | Pending |
| MCP-03 | Phase 17: Inline Environment Verification | Pending |
| MCP-04 | Phase 17: Inline Environment Verification | Pending |
| DFIX-01 | Phase 18: Auto-Fix Hardening | Deferred to v2.1 |
| MCP-05 | Phase 19: Enhancements | Deferred to v2.1 |
| AFIX-01 | Phase 18: Auto-Fix Hardening | Deferred to v2.1 |
| AFIX-02 | Phase 18: Auto-Fix Hardening | Deferred to v2.1 |
| OBS-01 | Phase 19: Enhancements | Deferred to v2.1 |

**v2.0 scope:** 5 requirements (MCP-01 through MCP-04, mapped to Phases 15-17)
**v2.1 scope:** 4 requirements (DFIX-01, AFIX-01, AFIX-02, MCP-05, OBS-01, mapped to Phases 18-19)
