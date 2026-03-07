# Roadmap: Agentic Odoo Module Development Workflow

## Milestones

- **v1.0 Odoo Module Automation MVP** — Phases 1-9 (shipped 2026-03-03) | [Archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Tech Debt Cleanup** — Phases 10-11 (shipped 2026-03-03)
- **v1.2 Template Quality** — Phases 12-14 (shipped 2026-03-04) | [Archive](milestones/v1.2-ROADMAP.md)
- **v2.0 Environment-Aware Generation** — Phases 15-17 (shipped 2026-03-04)
- **v2.1 Auto-Fix & Enhancements** — Phases 18-19 (shipped 2026-03-04) | [Archive](milestones/v2.1-ROADMAP.md)
- **v3.0 Bug Fixes & Tech Debt** — Phases 20-25 (shipped 2026-03-05) | [Archive](milestones/v3.0-ROADMAP.md)
- **v3.1 Design Flaws & Feature Gaps** — Phases 26-35 (shipped 2026-03-05)
- **v3.2 Security, Business Logic & Context7** — Phases 36-43 (in progress)

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

- [x] Phase 10: Environment & Dependencies — completed 2026-03-03
- [x] Phase 11: Live Integration Testing & i18n — completed 2026-03-03

</details>

<details>
<summary>v1.2 Template Quality (Phases 12-14) — SHIPPED 2026-03-04</summary>

- [x] Phase 12: Template Correctness & Auto-Fix (2/2 plans) — completed 2026-03-03
- [x] Phase 13: Golden Path Regression Testing (1/1 plan) — completed 2026-03-03
- [x] Phase 14: Cleanup/Debug the Tech Debt (1/1 plan) — completed 2026-03-04

**Total:** 3 phases, 4 plans, 12 requirements | 29 commits

</details>

<details>
<summary>v2.0 Environment-Aware Generation (Phases 15-17) — SHIPPED 2026-03-04</summary>

- [x] Phase 15-17: 3 phases, 6 plans — completed 2026-03-04

</details>

<details>
<summary>v2.1 Auto-Fix & Enhancements (Phases 18-19) — SHIPPED 2026-03-04</summary>

- [x] Phase 18-19: 2 phases, 5 plans — completed 2026-03-04

</details>

<details>
<summary>v3.0 Bug Fixes & Tech Debt (Phases 20-25) — SHIPPED 2026-03-05</summary>

- [x] Phase 20-25: 6 phases, 11 plans — completed 2026-03-05

</details>

<details>
<summary>v3.1 Design Flaws & Feature Gaps (Phases 26-35) — SHIPPED 2026-03-05</summary>

- [x] Phase 26: Monetary Field Detection (1/1 plan) — completed 2026-03-05
- [x] Phase 27: Relationship Patterns (1/1 plan) — completed 2026-03-05
- [x] Phase 28: Computed Chains & Cycle Detection (1/1 plan) — completed 2026-03-05
- [x] Phase 29: Complex Constraints (1/1 plan) — completed 2026-03-05
- [x] Phase 30: Scheduled Actions & Render Pipeline (1/1 plan) — completed 2026-03-05
- [x] Phase 31: Reports & Analytics (1/1 plan) — completed 2026-03-05
- [x] Phase 32: Controllers & Import/Export (2/2 plans) — completed 2026-03-05
- [x] Phase 33: Database Performance (1/1 plan) — completed 2026-03-05
- [x] Phase 34: Production Patterns (2/2 plans) — completed 2026-03-05
- [x] Phase 35: Template Bug Fixes & Tech Debt (1/1 plan) — completed 2026-03-05

**Total:** 10 phases, 12 plans, 16 requirements

</details>

### v3.2 Security, Business Logic & Context7 (In Progress)

**Milestone Goal:** Add security patterns (RBAC, field-level, audit trail), business logic patterns (approval workflows, notifications, webhooks), developer tooling (spec diffing, migration scripts), and wire Context7 into the generation pipeline.

- [x] **Phase 36: Renderer Extraction** - Extract preprocessors and context builders from renderer.py into separate modules (completed 2026-03-06)
- [x] **Phase 37: Security Foundation** - RBAC group hierarchy, field-level groups= attribute, and per-role ACLs (completed 2026-03-06)
- [x] **Phase 38: Audit Trail** - Structured audit log model with write() override stacking and context flag guards (completed 2026-03-06)
- [x] **Phase 39: Approval Workflows** - Multi-level state field, group-gated action methods, and per-stage record rules (completed 2026-03-06)
- [x] **Phase 40: Notifications & Webhooks** - mail.template generation for state transitions and hook method stubs in create()/write() (completed 2026-03-06)
- [ ] **Phase 41: Spec Diffing & Migration** - CLI diff-spec command and gen-migration for pre/post migration scripts
- [x] **Phase 42: Context7 Pipeline** - Pre-fetch Context7 docs during render setup to enrich template context (completed 2026-03-07)
- [ ] **Phase 43: Integration Testing** - Multi-feature integration tests validating write() stacking, field access, and full approval+notification flow

## Phase Details

### Phase 36: Renderer Extraction
**Goal**: Preprocessors and context builders live in dedicated modules, reducing renderer.py from 1852 lines to ~800 and establishing override flag merge patterns before new features add complexity
**Depends on**: Nothing (prerequisite for all v3.2 work)
**Requirements**: INFR-01
**Success Criteria** (what must be TRUE):
  1. `preprocessors.py` exists as a standalone module containing all existing preprocessor functions, importable and callable from renderer.py
  2. `renderer_context.py` exists as a standalone module containing `_build_model_context` and `_build_module_context`
  3. renderer.py is under 900 lines with no behavior change -- all existing tests pass without modification
  4. Override flags use a `set[str]` of sources (not boolean) so new preprocessors cannot silently clobber earlier flags
  5. A minimal-spec smoke test exists that renders a bare-minimum spec through the full pipeline without StrictUndefined errors
**Plans**: 2 plans

Plans:
- [x] 36-01-PLAN.md — Extract renderer_utils.py and preprocessors.py, migrate override flags to set[str]
- [x] 36-02-PLAN.md — Extract renderer_context.py, slim renderer.py, add smoke test

### Phase 37: Security Foundation
**Goal**: Specs with custom security roles generate complete RBAC infrastructure -- group hierarchy XML, per-role ACL rows, field-level groups= attributes, and ownership/department record rules
**Depends on**: Phase 36 (preprocessors module must exist for `_process_security_patterns`)
**Requirements**: SECR-01, SECR-02
**Success Criteria** (what must be TRUE):
  1. A spec with `roles: [viewer, editor, manager]` generates `security_group.xml` with `res.groups` records and `implied_ids` chain (viewer < editor < manager)
  2. Each custom role gets corresponding `ir.model.access` CSV entries with appropriate CRUD permissions (viewer: read-only, editor: read/write, manager: full)
  3. Fields marked `sensitive: true` or with explicit `groups` in spec render with `groups="module.group_name"` attribute in the generated model file
  4. The security preprocessor cross-references `groups=` fields against search view filters and computed field dependencies, warning if a restricted field is used in a context accessible to lower-privilege roles
**Plans**: 2 plans

Plans:
- [x] 37-01-PLAN.md — Security preprocessor, group hierarchy, ACL matrix, record rules, template updates
- [x] 37-02-PLAN.md — Field-level groups= attribute, view auto-fix, model template groups= rendering

### Phase 38: Audit Trail
**Goal**: Models with `audit: true` generate a companion audit log model, a write() override with context flag recursion guard, and audit-specific views and ACLs
**Depends on**: Phase 36 (preprocessors extraction), Phase 37 (security groups for audit viewer role)
**Requirements**: SECR-03
**Success Criteria** (what must be TRUE):
  1. A spec with `audit: true` on a model generates an `audit.trail.log` companion model with fields for user, timestamp, model name, record ID, field name, old value, and new value
  2. The audited model gets a `write()` override that logs changed fields to the audit model, guarded by `self.env.context.get('_skip_audit')` to prevent infinite recursion
  3. Audit log entries are only writable by the audit system (create-only ACL for the audit model, no write/unlink for regular users)
  4. The write() override stacking pattern (context flag guard, super() call ordering) is established as a reusable template block for Phase 39 and 40 to extend
**Plans**: 2 plans

Plans:
- [ ] 38-01-PLAN.md — Audit preprocessor, renderer context defaults, auditor role injection, ACL
- [ ] 38-02-PLAN.md — Model template audit write() wrapper, helper methods, smoke test

### Phase 39: Approval Workflows
**Goal**: Models with `approval` in spec generate a complete multi-level approval workflow with state field, group-gated action methods, header buttons, and per-stage record rules
**Depends on**: Phase 37 (security groups for approver roles), Phase 38 (write() stacking pattern)
**Requirements**: BIZL-01
**Success Criteria** (what must be TRUE):
  1. A spec with `approval: {levels: [submitted, approved_l1, approved_l2, done]}` generates a Selection state field with those values and `action_submit()`, `action_approve_l1()`, `action_approve_l2()`, `action_done()` methods
  2. Each approval action method is gated by a security group check (e.g., only `group_approver_l1` can call `action_approve_l1`)
  3. Form view `<header>` section contains workflow buttons with `states=` and `groups=` attributes controlling visibility per approval stage
  4. `ir.rule` record rules restrict record visibility by approval stage (e.g., draft records visible only to creator and managers)
**Plans**: 2 plans

Plans:
- [ ] 39-01-PLAN.md — Approval preprocessor, context defaults, pipeline wiring, and unit tests
- [ ] 39-02-PLAN.md — Template blocks (action methods, header buttons, record rules), smoke tests

### Phase 40: Notifications & Webhooks
**Goal**: State transitions generate mail.template XML records with send_mail() calls, and models with webhooks generate extensible hook method stubs in create()/write()
**Depends on**: Phase 39 (state fields and action methods must exist for notification triggers)
**Requirements**: BIZL-02, BIZL-03
**Success Criteria** (what must be TRUE):
  1. State transitions with `notify: true` generate `mail.template` XML records with `noupdate="1"`, subject/body referencing the model fields, and `email_to` targeting relevant users
  2. Action methods for notifiable transitions include `self.env.ref('module.template_name').send_mail(self.id)` calls after the state change
  3. Models with `webhooks` in spec generate `_webhook_post_create(self, vals)` and `_webhook_post_write(self, vals, old_vals)` stub methods called from `create()` and `write()` overrides
  4. Webhook hooks use `self.env.context.get('_skip_webhooks')` guard to prevent recursion, consistent with the audit trail pattern from Phase 38
**Plans**: 2 plans

Plans:
- [ ] 40-01-PLAN.md — Notification and webhook preprocessors, renderer context defaults, pipeline wiring, unit tests
- [ ] 40-02-PLAN.md — Template rendering (mail_template_data.xml.j2, model.py.j2 notification/webhook blocks), smoke tests

### Phase 41: Spec Diffing & Migration
**Goal**: CLI commands compare spec versions and generate Odoo migration scripts from the structural differences
**Depends on**: Phase 36 (independent of security/workflow track, only needs stable renderer)
**Requirements**: TOOL-01, TOOL-04
**Success Criteria** (what must be TRUE):
  1. `odoo-gen diff-spec old.json new.json` outputs typed change objects categorizing each difference as added/removed/modified for models, fields, and relations
  2. `odoo-gen gen-migration old.json new.json --version 17.0.1.1.0` generates `migrations/17.0.1.1.0/pre-migrate.py` using only `cr.execute()` raw SQL (no ORM) and `post-migrate.py` using ORM calls
  3. Field type changes that lose data (e.g., Text to Integer) are flagged as warnings in the diff output, and migration scripts include safety comments
  4. The `deepdiff` library is added as a dependency and used for structural comparison with `ignore_order` for list fields
**Plans**: 2 plans

Plans:
- [ ] 41-01-PLAN.md — Spec differ module with deepdiff, destructiveness classification, diff-spec CLI command
- [ ] 41-02-PLAN.md — Migration generator with per-change helpers, backup/restore patterns, gen-migration CLI command

### Phase 42: Context7 Pipeline
**Goal**: Context7 documentation is pre-fetched during render setup and injected into template context as hints, enriching generated code with real-time Odoo API knowledge
**Depends on**: Phase 36 (renderer_context.py must exist for context injection point)
**Requirements**: PIPE-01
**Success Criteria** (what must be TRUE):
  1. Before the render chain starts, `context7_enrich()` batch-queries Context7 for relevant Odoo documentation based on the spec's models, fields, and patterns
  2. Results are injected as `c7_hints` dict into the template context, accessible in Jinja2 templates as optional enrichment
  3. Context7 failures (timeout, rate limit, network error) never block or fail the render pipeline -- generation proceeds with empty hints and a stderr warning
  4. A `--no-context7` CLI flag disables enrichment entirely for offline or CI usage
**Plans**: 2 plans

Plans:
- [ ] 42-01-PLAN.md — Core enrichment engine: context7_enrich(), pattern detection, disk cache, token truncation, unit tests
- [ ] 42-02-PLAN.md — Pipeline wiring: renderer/context/CLI integration, --no-context7/--fresh-context7 flags, pipeline tests

### Phase 43: Integration Testing
**Goal**: Multi-feature integration tests validate that security, audit, approval, notification, and webhook patterns work correctly in combination
**Depends on**: Phase 38, Phase 39, Phase 40 (all feature phases must be complete)
**Requirements**: INFR-02
**Success Criteria** (what must be TRUE):
  1. An integration test renders a spec combining audit + approval + notifications + webhooks and verifies that the generated write() method contains all override blocks in correct order (audit wraps approval wraps webhook)
  2. An integration test verifies that field-level `groups=` restrictions and approval-stage `ir.rule` records coexist without conflicts in the generated security files
  3. An integration test renders a full-featured spec through Docker validation, confirming the module installs and tests pass with all patterns active simultaneously
  4. A recursion guard test verifies that audit logging during an approval state change does not trigger infinite write() recursion
**Plans**: TBD

Plans:
- [ ] 43-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 36 -> 37 -> 38 -> 39 -> 40 -> 41 -> 42 -> 43

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-9 | v1.0 | 26/26 | Complete | 2026-03-03 |
| 10-11 | v1.1 | - | Complete | 2026-03-03 |
| 12-14 | v1.2 | 4/4 | Complete | 2026-03-04 |
| 15-17 | v2.0 | 6/6 | Complete | 2026-03-04 |
| 18-19 | v2.1 | 5/5 | Complete | 2026-03-04 |
| 20-25 | v3.0 | 11/11 | Complete | 2026-03-05 |
| 26-35 | v3.1 | 12/12 | Complete | 2026-03-05 |
| 36. Renderer Extraction | 2/2 | Complete    | 2026-03-06 | - |
| 37. Security Foundation | 2/2 | Complete   | 2026-03-06 | - |
| 38. Audit Trail | 1/2 | Complete    | 2026-03-06 | - |
| 39. Approval Workflows | 2/2 | Complete    | 2026-03-06 | - |
| 40. Notifications & Webhooks | 2/2 | Complete    | 2026-03-06 | - |
| 41. Spec Diffing & Migration | 1/2 | In Progress|  | - |
| 42. Context7 Pipeline | 2/2 | Complete   | 2026-03-07 | - |
| 43. Integration Testing | v3.2 | 0/? | Not started | - |

---
*Roadmap created: 2026-03-01*
*v1.0 shipped: 2026-03-03*
*v1.1 shipped: 2026-03-03*
*v1.2 shipped: 2026-03-04*
*v2.0 shipped: 2026-03-04*
*v2.1 shipped: 2026-03-04*
*v3.0 shipped: 2026-03-05*
*v3.1 shipped: 2026-03-05*
*v3.2 roadmap created: 2026-03-06*
