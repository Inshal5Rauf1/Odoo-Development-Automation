# Roadmap: Agentic Odoo Module Development Workflow

## Milestones

- **v1.0 Odoo Module Automation MVP** — Phases 1-9 (shipped 2026-03-03) | [Archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Tech Debt Cleanup** — Phases 10-11 (shipped 2026-03-03)
- **v1.2 Template Quality** — Phases 12-14 (shipped 2026-03-04) | [Archive](milestones/v1.2-ROADMAP.md)
- **v2.0 Environment-Aware Generation** — Phases 15-17 (shipped 2026-03-04)
- **v2.1 Auto-Fix & Enhancements** — Phases 18-19 (shipped 2026-03-04) | [Archive](milestones/v2.1-ROADMAP.md)
- **v3.0 Bug Fixes & Tech Debt** — Phases 20-24 (in progress)

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

<details>
<summary>v2.0 Environment-Aware Generation (Phases 15-17) — SHIPPED 2026-03-04</summary>

- [x] Phase 15: Odoo Dev Instance (2/2 plans) — completed 2026-03-04
- [x] Phase 16: Odoo MCP Server (2/2 plans) — completed 2026-03-04
- [x] Phase 17: Inline Environment Verification (2/2 plans) — completed 2026-03-04

</details>

<details>
<summary>v2.1 Auto-Fix & Enhancements (Phases 18-19) — SHIPPED 2026-03-04</summary>

- [x] Phase 18: Auto-Fix Hardening (2/2 plans) — completed 2026-03-04
- [x] Phase 19: Enhancements (3/3 plans) — completed 2026-03-04

**Total:** 2 phases, 5 plans, 5 requirements | 25 commits | +4,994 LOC Python | 444 tests

</details>

### v3.0 Bug Fixes & Tech Debt (In Progress)

**Milestone Goal:** Fix all confirmed bugs and pay down technical debt identified in codebase audit. 13 requirements across auto-fix, templates, validation, search, and code quality.

- [x] **Phase 20: Auto-Fix AST Migration** - Replace regex-based fixers with AST-based source modification and full-body import scanning (completed 2026-03-05)
- [x] **Phase 21: Template Correctness** - Fix mail.thread injection, wizard imports, wizard ACLs, and deprecated name_get (completed 2026-03-05)
- [x] **Phase 22: Validation & Search Fixes** - Docker exec race condition, GitHub rate limiting, and AST _inherit-only detection (completed 2026-03-05)
- [ ] **Phase 23: Unified Result Type** - Cross-cutting Result[T] type across validation pipeline modules
- [ ] **Phase 24: Code Quality & Decomposition** - Lazy CLI imports, render_module decomposition, Docker path resolution

## Phase Details

### Phase 20: Auto-Fix AST Migration
**Goal**: Auto-fix pipeline produces correct fixes for multi-line expressions and detects all unused imports without false positives
**Depends on**: Nothing (independent of other v3.0 phases)
**Requirements**: AFIX-01, AFIX-02
**Success Criteria** (what must be TRUE):
  1. All 5 pylint fixers (_fix_w8113, _fix_w8111, _fix_c8116, _fix_w8150, _fix_c8107) use AST to parse and modify source code instead of regex
  2. Multi-line string= expressions (e.g., spanning parentheses) are correctly fixed without corrupting surrounding code
  3. Unused import detection scans the full AST body for name references and removes any import with zero references, not just a hardcoded whitelist
  4. Existing auto-fix test suite passes with AST implementation (no regressions)
**Plans:** 2/2 plans complete
Plans:
- [ ] 20-01-PLAN.md — Migrate 5 pylint fixers to AST-based splice with shared utilities
- [ ] 20-02-PLAN.md — Rewrite unused import detection with full AST body scan

### Phase 21: Template Correctness
**Goal**: Generated modules have correct mail.thread usage, wizard imports, wizard ACLs, and modern test assertions
**Depends on**: Nothing (independent of other v3.0 phases)
**Requirements**: TMPL-01, TMPL-02, TMPL-03, TMPL-04
**Success Criteria** (what must be TRUE):
  1. mail.thread inheritance is added only to top-level business models (not config tables, line items, wizards, or models extending parents that already have mail.thread)
  2. Wizard template imports `api` only when the generated wizard methods use @api decorators
  3. Generated ir.model.access.csv includes ACL entries for TransientModel wizards alongside regular models
  4. Test template asserts on display_name instead of calling deprecated name_get(), with version gate for Odoo 18.0
**Plans:** 2/2 plans complete
Plans:
- [ ] 21-01-PLAN.md — Smart mail.thread injection with line item detection and chatter flag
- [ ] 21-02-PLAN.md — Wizard conditional api import, wizard ACLs, display_name test assertion

### Phase 22: Validation & Search Fixes
**Goal**: Docker validation avoids race conditions and search indexing handles rate limits and _inherit-only models
**Depends on**: Nothing (independent of other v3.0 phases)
**Requirements**: VALD-01, SRCH-01, SRCH-02
**Success Criteria** (what must be TRUE):
  1. docker_install_module uses `docker compose run --rm` instead of `docker compose exec`, eliminating serialization race conditions from concurrent Odoo processes
  2. GitHub API calls check X-RateLimit-Remaining header, sleep until reset when exhausted, and retry with exponential backoff on 403/429 responses
  3. AST analyzer detects models with _inherit but no _name and records them in ModuleAnalysis.inherited_models as model extensions
**Plans:** 2/2 plans complete
Plans:
- [ ] 22-01-PLAN.md — Fix docker_install_module to use run --rm pattern (VALD-01)
- [ ] 22-02-PLAN.md — GitHub rate limit handling + _inherit-only AST detection (SRCH-01, SRCH-02)

### Phase 23: Unified Result Type
**Goal**: Validation pipeline has consistent error handling through a shared Result[T] type
**Depends on**: Nothing (can start independently, but must complete before Phase 24)
**Requirements**: VALD-02
**Success Criteria** (what must be TRUE):
  1. A unified Result[T] type with success, data, and errors fields exists and is used by auto_fix, docker_runner, pylint_runner, and verifier modules
  2. Callers of validation functions receive structured Result objects instead of mixed return types (tuples, booleans, exceptions)
  3. Error messages from validation pipeline are consistently formatted and accessible through Result.errors
**Plans**: TBD

### Phase 24: Code Quality & Decomposition
**Goal**: CLI starts fast, render_module is maintainable, and Docker path is robust
**Depends on**: Phase 23 (decomposed render functions should use Result type)
**Requirements**: QUAL-01, QUAL-02, QUAL-03
**Success Criteria** (what must be TRUE):
  1. CLI module-level imports contain only click and stdlib; heavy libraries (chromadb, PyGithub, gitpython, Docker, validation stack) are imported inside command functions
  2. render_module is decomposed into independently testable stage functions (render_manifest, render_models, render_views, render_security, render_wizards, render_tests, render_static) each under 80 lines
  3. Docker compose file path is resolved via importlib.resources or configuration instead of 5-level parent directory traversal
  4. All decomposed render functions return Result types from Phase 23
**Plans**: TBD

## Progress

**Execution Order:**
Phases 20-22 can execute in parallel (independent). Phase 23 before Phase 24 (dependency).

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-9 | v1.0 | 26/26 | Complete | 2026-03-03 |
| 10-11 | v1.1 | - | Complete | 2026-03-03 |
| 12-14 | v1.2 | 4/4 | Complete | 2026-03-04 |
| 15-17 | v2.0 | 6/6 | Complete | 2026-03-04 |
| 18-19 | v2.1 | 5/5 | Complete | 2026-03-04 |
| 20. Auto-Fix AST Migration | 2/2 | Complete    | 2026-03-05 | - |
| 21. Template Correctness | 2/2 | Complete   | 2026-03-05 | - |
| 22. Validation & Search Fixes | 2/2 | Complete   | 2026-03-05 | - |
| 23. Unified Result Type | v3.0 | 0/? | Not started | - |
| 24. Code Quality & Decomposition | v3.0 | 0/? | Not started | - |

---
*Roadmap created: 2026-03-01*
*v1.0 shipped: 2026-03-03*
*v1.1 shipped: 2026-03-03*
*v1.2 shipped: 2026-03-04*
*v2.0 shipped: 2026-03-04*
*v2.1 shipped: 2026-03-04*
*v3.0 roadmap added: 2026-03-05*
