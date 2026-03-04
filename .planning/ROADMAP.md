# Roadmap: Agentic Odoo Module Development Workflow

## Milestones

- **v1.0 Odoo Module Automation MVP** — Phases 1-9 (shipped 2026-03-03) | [Archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Tech Debt Cleanup** — Phases 10-11 (shipped 2026-03-03)
- **v1.2 Template Quality** — Phases 12-14 (shipped 2026-03-04) | [Archive](milestones/v1.2-ROADMAP.md)
- **v2.0 Environment-Aware Generation** — Phases 15-17 (in progress)
- **v2.1 Auto-Fix & Enhancements** — Phases 18-19 (planned)

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

- [x] **Phase 10: Environment & Dependencies** — GitHub auth, clean install verification (completed 2026-03-03)
- [x] **Phase 11: Live Integration Testing & i18n** — Docker live validation, field string= i18n extraction (completed 2026-03-03)

</details>

<details>
<summary>v1.2 Template Quality (Phases 12-14) — SHIPPED 2026-03-04</summary>

- [x] Phase 12: Template Correctness & Auto-Fix (2/2 plans) — completed 2026-03-03
- [x] Phase 13: Golden Path Regression Testing (1/1 plan) — completed 2026-03-03
- [x] Phase 14: Cleanup/Debug the Tech Debt (1/1 plan) — completed 2026-03-04

**Total:** 3 phases, 4 plans, 12 requirements | 29 commits | +3,550 LOC Python | 309 tests

</details>

### v2.0 Environment-Aware Generation (Phases 15-17)

**Milestone Goal:** Move from "generate then validate" to "verify as you generate" by connecting agents to a live Odoo instance via MCP.

- [x] **Phase 15: Odoo Dev Instance** - Docker Compose Odoo 17 CE dev environment with XML-RPC access (completed 2026-03-04)
- [x] **Phase 16: Odoo MCP Server** - 6-tool MCP server for live model introspection via XML-RPC (completed 2026-03-04)
- [x] **Phase 17: Inline Environment Verification** - Model and view agents verify against live instance during generation (completed 2026-03-04)

### v2.1 Auto-Fix & Enhancements (Phases 18-19) — PLANNED

- [ ] **Phase 18: Auto-Fix Hardening** - Expand Docker fix patterns to 5/5, cap fix loops, integration test
- [ ] **Phase 19: Enhancements** - Context7 live docs and generation pipeline observability

## Phase Details

### Phase 15: Odoo Dev Instance
**Goal**: Developers have a running Odoo 17 CE instance accessible via XML-RPC that agents can query
**Depends on**: Phase 14 (v1.2 complete)
**Requirements**: MCP-01
**Success Criteria** (what must be TRUE):
  1. Running `docker compose up` from the project starts Odoo 17 CE with PostgreSQL and pre-installed modules (base, mail, sale, purchase, hr, account)
  2. XML-RPC calls to the instance succeed at the configured host:port (e.g., `xmlrpc.client.ServerProxy` can authenticate and call `execute_kw`)
  3. Instance data persists across `docker compose down` and `docker compose up` cycles (named volume)
  4. A CLI command or script starts and stops the dev instance without manual Docker knowledge
**Plans:** 2/2 plans complete

Plans:
- [x] 15-01-PLAN.md — Docker Compose dev environment config + management script + XML-RPC smoke test
- [x] 15-02-PLAN.md — Unit tests (config validation) + Docker integration tests (live instance verification)

### Phase 16: Odoo MCP Server
**Goal**: Code generation agents can query the live Odoo instance for model schemas, field definitions, installed modules, and view architectures through a standardized MCP tool interface
**Depends on**: Phase 15
**Requirements**: MCP-02
**Success Criteria** (what must be TRUE):
  1. MCP server connects to Odoo via XML-RPC using environment variables (ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY) and exposes 6 tools: `list_models`, `get_model_fields`, `list_installed_modules`, `check_module_dependency`, `get_view_arch`, plus authentication check
  2. Each tool returns structured data (e.g., `get_model_fields` returns field name, type, relation, required, readonly for any model)
  3. MCP server handles Odoo-unreachable gracefully (returns error response, does not crash)
  4. Unit tests with mocked XML-RPC responses cover all 6 tools
**Plans:** 2/2 plans complete

Plans:
- [x] 16-01-PLAN.md — OdooClient wrapper + MCP server with 6 tools + unit tests (TDD)
- [x] 16-02-PLAN.md — Claude Code MCP configuration + live instance verification checkpoint

### Phase 17: Inline Environment Verification
**Goal**: Model and view generation agents verify inheritance chains, field references, and view targets against the live Odoo instance during generation, catching errors at source instead of during Docker validation
**Depends on**: Phase 16
**Requirements**: MCP-03, MCP-04
**Success Criteria** (what must be TRUE):
  1. When generating a model with `_inherit`, the agent verifies the base model exists in the live instance before writing the file; when generating relational fields, the agent verifies the target model exists
  2. When generating form/tree/kanban views, the agent verifies each `<field name="X">` references a real field on the model; inherited view targets are verified to exist
  3. Verification mismatches produce warnings with suggested corrections (not hard blocks) so generation can proceed
  4. When the MCP server is unavailable, generation falls back to current static behavior with no errors
  5. Integration tests demonstrate: (a) model inheriting hr.employee triggers MCP checks, (b) view referencing non-existent field triggers a warning
**Plans:** 2/2 plans complete

Plans:
- [x] 17-01-PLAN.md — EnvironmentVerifier + VerificationWarning (TDD) + renderer.py wiring + caller updates
- [x] 17-02-PLAN.md — Docker integration tests (live Odoo) + CLI warning output checkpoint

### Phase 18: Auto-Fix Hardening
**Goal**: The auto-fix pipeline handles all 5 common Docker error patterns and has bounded iteration caps so failures escalate to human review instead of looping forever
**Depends on**: Phase 14 (independent of MCP work; can run in parallel with Phases 15-17)
**Requirements**: DFIX-01, AFIX-01, AFIX-02
**Success Criteria** (what must be TRUE):
  1. `FIXABLE_DOCKER_PATTERNS` handles 5/5 error patterns: missing module dependency, missing field reference in view XML, security access violation, missing data file in manifest, and missing mail.thread inheritance
  2. Both pylint and Docker fix loops are capped at a configurable maximum (default: 5 iterations); when the cap is reached, remaining errors are reported and the loop stops
  3. Running `validate --auto-fix` on a module with known pylint violations (unused import, missing mail.thread) resolves them automatically, verified by an integration test that runs in CI without Docker
  4. Each new Docker fix pattern has unit tests with sample error output proving the pattern matches and the fix is applied correctly
**Plans**: TBD

### Phase 19: Enhancements
**Goal**: Agents have access to live Odoo documentation via Context7 and the generation pipeline exposes observable state for debugging failures
**Depends on**: Phase 16 (Context7 benefits from MCP infrastructure patterns)
**Requirements**: MCP-05, OBS-01
**Success Criteria** (what must be TRUE):
  1. Agents can query Odoo 17.0/18.0 API documentation on demand via Context7 MCP, with the knowledge base remaining the primary source and Context7 supplementing
  2. Generation works without Context7 configured (graceful fallback to existing static knowledge base)
  3. Each artifact (model, view, security, test) has a tracked state (pending, generated, validated, approved) stored as structured metadata, visible via CLI output or log
  4. State tracking does not block generation if it fails (graceful degradation)
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 15. Odoo Dev Instance | v2.0 | 2/2 | Complete | 2026-03-04 |
| 16. Odoo MCP Server | v2.0 | 2/2 | Complete | 2026-03-04 |
| 17. Inline Environment Verification | v2.0 | 2/2 | Complete | 2026-03-04 |
| 18. Auto-Fix Hardening | v2.1 | 0/? | Deferred | - |
| 19. Enhancements | v2.1 | 0/? | Deferred | - |

---
*Roadmap created: 2026-03-01*
*v1.0 shipped: 2026-03-03*
*v1.1 shipped: 2026-03-03*
*v1.2 shipped: 2026-03-04*
*v2.0 roadmap added: 2026-03-04*
*v2.0 shipped: 2026-03-04*
