# Roadmap: Agentic Odoo Module Development Workflow

## Milestones

- **v1.0 Odoo Module Automation MVP** — Phases 1-9 (shipped 2026-03-03) | [Archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Tech Debt Cleanup** — Phases 10-11 (in progress)

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

### v1.1 Tech Debt Cleanup

- [x] **Phase 10: Environment & Dependencies** — GitHub auth, PyTorch CPU-only clean install verification (completed 2026-03-03)
- [x] **Phase 11: Live Integration Testing & i18n** — Docker live validation, field string= i18n extraction (completed 2026-03-03)

## Phase Details

### Phase 10: Environment & Dependencies
**Goal**: Search and index features work with real GitHub API and a clean sentence-transformers install
**Depends on**: v1.0 shipped
**Requirements**: DEBT-01, DEBT-02
**Success Criteria** (what must be TRUE):
  1. `gh auth status` succeeds and `odoo-gen-utils search-modules "inventory"` returns results from GitHub API
  2. A fresh `uv venv` + `uv pip install .[search]` completes without errors on CPU-only machine
  3. `odoo-gen-utils build-index` successfully crawls OCA repos and builds a ChromaDB index
  4. `odoo-gen-utils index-status` reports indexed module count > 0
**Plans**: 2 plans (Wave 1 parallel)
Plans:
- [x] 10-01-PLAN.md — Remove unused deps (sentence-transformers/torch), add E2E test infrastructure
- [x] 10-02-PLAN.md — GitHub auth setup wizard with --no-wizard flag

### Phase 11: Live Integration Testing & i18n
**Goal**: Docker validation runs against real Odoo 17.0 containers and i18n extracts field string= translations
**Depends on**: Phase 10
**Requirements**: DEBT-03, DEBT-04
**Success Criteria** (what must be TRUE):
  1. `odoo-gen-utils validate <module> --docker` spins up a real Odoo 17.0 + PostgreSQL container, installs the module, and reports pass/fail
  2. At least one integration test runs against the live Docker daemon (not mocked)
  3. `odoo-gen-utils extract-i18n <module>` extracts `fields.Char(string="My Label")` patterns into the .pot file
  4. Existing 243+ tests continue to pass (no regressions)
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 10. Environment & Dependencies | v1.1 | Complete    | 2026-03-03 | 2026-03-03 |
| 11. Live Integration Testing & i18n | 2/2 | Complete    | 2026-03-03 | - |

---
*Roadmap created: 2026-03-01*
*v1.0 shipped: 2026-03-03*
*v1.1 started: 2026-03-03*
