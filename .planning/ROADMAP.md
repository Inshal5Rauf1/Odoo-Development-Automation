# Roadmap: Agentic Odoo Module Development Workflow

## Milestones

- **v1.0 Odoo Module Automation MVP** — Phases 1-9 (shipped 2026-03-03) | [Archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Tech Debt Cleanup** — Phases 10-11 (shipped 2026-03-03)
- **v1.2 Template Quality** — Phases 12-13 (in progress)

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

### v1.2 Template Quality

- [x] **Phase 12: Template Correctness & Auto-Fix** - Fix template bugs, expand auto-fix for structural issues, update knowledge base with mail.thread rules (completed 2026-03-03)
- [ ] **Phase 13: Golden Path Regression Testing** - E2E test that renders a realistic module, Docker-installs it, runs its tests, and asserts everything passes

## Phase Details

### Phase 12: Template Correctness & Auto-Fix
**Goal**: Generated modules produce correct Python code out of the box -- proper inheritance, minimal imports, clean manifests -- and auto-fix catches any remaining structural issues
**Depends on**: v1.1 shipped (Phase 11)
**Requirements**: TMPL-01, TMPL-02, TMPL-03, TMPL-04, AFIX-01, AFIX-02, KNOW-01, KNOW-02
**Success Criteria** (what must be TRUE):
  1. A module spec with `mail` in depends renders model.py containing `_inherit = ['mail.thread', 'mail.activity.mixin']` (both 17.0 and 18.0 templates)
  2. A module spec with no `@api.*` decorators renders model.py that does NOT import `api` from odoo
  3. Rendered `__manifest__.py` contains no `installable` or `auto_install` keys (Odoo defaults omitted)
  4. Rendered test files do not import `ValidationError` unless the test actually uses it
  5. Running the auto-fix on a module with chatter XML but missing `mail.thread` inheritance adds the `_inherit` line, and running it on files with unused imports removes them
**Plans:** 2/2 plans complete
Plans:
- [x] 12-01-PLAN.md — Fix 4 template bugs (mail.thread inheritance, conditional api import, clean manifest, clean test imports)
- [x] 12-02-PLAN.md — Expand auto-fix (missing mail.thread, unused imports) and update knowledge base

### Phase 13: Golden Path Regression Testing
**Goal**: A single E2E test proves that the full pipeline (render templates with realistic spec, Docker install, run Odoo tests) produces a working module -- catching template regressions automatically
**Depends on**: Phase 12
**Requirements**: REGR-01, REGR-02
**Success Criteria** (what must be TRUE):
  1. An E2E test renders a realistic module spec (including mail dependency, chatter views, computed fields) through the template engine and produces a complete module directory
  2. The rendered module installs successfully in a Docker Odoo 17.0 instance (no ImportError, no registry errors)
  3. The rendered module's own Odoo tests run inside Docker and all pass (zero failures)
**Plans:** 1 plan
Plans:
- [ ] 13-01-PLAN.md — Golden path E2E regression test (render + Docker install + Docker test execution)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 12. Template Correctness & Auto-Fix | v1.2 | 2/2 | Complete | 2026-03-03 |
| 13. Golden Path Regression Testing | v1.2 | 0/1 | Not started | - |

---
*Roadmap created: 2026-03-01*
*v1.0 shipped: 2026-03-03*
*v1.1 shipped: 2026-03-03*
*v1.2 started: 2026-03-03*
