# Roadmap: Agentic Odoo Module Development Workflow

## Milestones

- **v1.0 Odoo Module Automation MVP** — Phases 1-9 (shipped 2026-03-03) | [Archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Tech Debt Cleanup** — Phases 10-11 (shipped 2026-03-03)
- **v1.2 Template Quality** — Phases 12-14 (shipped 2026-03-04) | [Archive](milestones/v1.2-ROADMAP.md)
- **v2.0 Environment-Aware Generation** — Phases 15-17 (shipped 2026-03-04)
- **v2.1 Auto-Fix & Enhancements** — Phases 18-19 (shipped 2026-03-04) | [Archive](milestones/v2.1-ROADMAP.md)
- **v3.0 Bug Fixes & Tech Debt** — Phases 20-25 (shipped 2026-03-05) | [Archive](milestones/v3.0-ROADMAP.md)
- **v3.1 Design Flaws & Feature Gaps** — Phases 26-35 (shipped 2026-03-05)
- **v3.2 Security, Business Logic & Context7** — Phases 36-44 (shipped 2026-03-07) | [Archive](milestones/v3.2-ROADMAP.md)
- **v3.3 Test Fixes, Domain Patterns & Architecture** — Phases 45-54 (shipped 2026-03-08) | [Archive](milestones/v3.3-ROADMAP.md)
- **v4.0 LLM Logic Writer & Generation Capabilities** — Phases 55-63 (in progress)

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

- [x] Phase 26-35: 10 phases, 12 plans — completed 2026-03-05

</details>

<details>
<summary>v3.2 Security, Business Logic & Context7 (Phases 36-44) — SHIPPED 2026-03-07</summary>

- [x] Phase 36-44: 9 phases, 15 plans — completed 2026-03-07

</details>

<details>
<summary>v3.3 Test Fixes, Domain Patterns & Architecture (Phases 45-54) — SHIPPED 2026-03-08</summary>

- [x] Phase 45: Preprocessor Split (2/2 plans) — completed 2026-03-07
- [x] Phase 46: Test Infrastructure (1/1 plan) — completed 2026-03-07
- [x] Phase 47: Pydantic Spec Validation (3/3 plans) — completed 2026-03-08
- [x] Phase 48: Model Registry (2/2 plans) — completed 2026-03-08
- [x] Phase 49: Pakistan/HEC Localization (2/2 plans) — completed 2026-03-08
- [x] Phase 50: Academic Calendar (2/2 plans) — completed 2026-03-08
- [x] Phase 51: Semantic Validation (2/2 plans) — completed 2026-03-08
- [x] Phase 52: Document Management (2/2 plans) — completed 2026-03-08
- [x] Phase 53: Mermaid Graphs (2/2 plans) — completed 2026-03-08
- [x] Phase 54: Pipeline Quality of Life (2/2 plans) — completed 2026-03-08

**Total:** 10 phases, 20 plans, 14 requirements | 62 commits | 15,928 LOC Python | 1,730 tests

</details>

## v4.0 LLM Logic Writer & Generation Capabilities (In Progress)

**Milestone Goal:** Transform the system from a structural scaffolder (Jinja templates producing TODO stubs) into an AI code generator (LLM writes real method bodies), then add module extension, iterative refinement, computed chains, portal controllers, and bulk operations.

- [x] **Phase 55: Cleanup** - Fix docker exec race condition and delete deprecated artifact_state.py (completed 2026-03-08)
- [x] **Phase 56: Logic Writer Core** - StubDetector infrastructure and LLM integration point for generating method bodies (completed 2026-03-08)
- [x] **Phase 57: Logic Writer Computed & Constraints** - LLM generates _compute_*, _check_*, and validates output via semantic checker (completed 2026-03-08)
- [x] **Phase 58: Logic Writer Overrides & Actions** - LLM generates create/write overrides, action_*, and _cron_* methods (completed 2026-03-08)
- [x] **Phase 59: Module Extension Pattern** - Generate _inherit models, xpath view inheritance, and dependency validation (completed 2026-03-08)
- [x] **Phase 60: Iterative Refinement** - Add field/model to existing modules without full regeneration (completed 2026-03-09)
- [x] **Phase 61: Computed Chain Generator** - Cross-model computed field chains with dependency ordering and cycle detection (completed 2026-03-09)
- [ ] **Phase 62: Portal Controllers** - Generate portal.CustomerPortal controllers, QWeb templates, and portal record rules
- [ ] **Phase 63: Bulk Operations** - Generate model_create_multi, batch wizards, and chunked processing helpers

## Phase Details

### Phase 55: Cleanup
**Goal**: Eliminate known tech debt blocking v4.0 work -- the docker exec race condition and the deprecated artifact_state module
**Depends on**: Nothing (first phase of v4.0)
**Requirements**: CLEN-01, CLEN-02
**Success Criteria** (what must be TRUE):
  1. Running `docker compose run --rm` for module installation completes without serialization failures (no concurrent DB writes)
  2. No file named artifact_state.py exists in the codebase and no imports reference ModuleState, ArtifactState, save_state, or load_state
  3. All existing tests pass after the cleanup changes
**Plans:** 1/1 plans complete
Plans:
- [ ] 55-01-PLAN.md — Verify docker fix, delete artifact_state.py and all references

### Phase 56: Logic Writer Core
**Goal**: Belt produces a deterministic stub report (.odoo-gen-stubs.json) that detects TODO method stubs in generated Python files, assembles rich per-stub context, and classifies complexity -- enabling Claude Code to fill stubs externally
**Depends on**: Phase 55
**Requirements**: LGEN-01, LGEN-02
**Success Criteria** (what must be TRUE):
  1. StubDetector scans a generated .py file and returns a list of methods containing TODO/pass/constant-assign bodies with their line ranges
  2. MethodContext builder assembles field definitions, spec business_rules, and model registry context for each detected stub
  3. Belt generates .odoo-gen-stubs.json with per-stub context; Claude Code reads this report externally to implement stubs
  4. Complexity classifier deterministically routes stubs as budget or quality based on cross-model depends, target count, conditional rules, and method type
**Plans:** 2/2 plans complete
Plans:
- [ ] 56-01-PLAN.md — StubDetector + ContextBuilder (AST stub detection, per-stub context assembly)
- [ ] 56-02-PLAN.md — Classifier + Report + CLI integration + Agent prompt

### Phase 57: Logic Writer Computed & Constraints
**Goal**: Logic Writer generates correct _compute_* and _check_* method implementations that pass semantic validation
**Depends on**: Phase 56
**Requirements**: LGEN-03, LGEN-04, LGEN-07
**Success Criteria** (what must be TRUE):
  1. Generated _compute_* methods include correct @api.depends decorators matching the fields they read, and use self.mapped/filtered patterns for recordset operations
  2. Generated _check_* methods include correct @api.constrains decorators, raise ValidationError with user-facing messages, and handle cross-field validation logic
  3. Logic Writer output for computed and constraint methods passes the Phase 51 semantic validator (AST + XML cross-check) without errors -- field names resolve, ORM patterns are valid
**Plans:** 2/2 plans complete
Plans:
- [ ] 57-01-PLAN.md — Enrich stub report context (computation_hint, constraint_type, target_field_types, method_type, error_messages)
- [ ] 57-02-PLAN.md — Semantic validation E7-E12 checks for ORM pattern violations in method bodies

### Phase 58: Logic Writer Overrides & Actions
**Goal**: Logic Writer generates correct create/write overrides, action workflow methods, and cron scheduled logic
**Depends on**: Phase 56
**Requirements**: LGEN-05, LGEN-06
**Success Criteria** (what must be TRUE):
  1. Generated create()/write() overrides call super() correctly, implement business logic (auto-create related records, increment counters, trigger state changes), and do not duplicate audit/approval logic already handled by templates
  2. Generated action_* methods implement workflow state transitions with correct domain queries and recordset operations
  3. Generated _cron_* methods include @api.model decorator, use domain-based queries to select target records, and implement scheduled processing logic
**Plans:** 2/2 plans complete
Plans:
- [ ] 58-01-PLAN.md — Template markers + stub zone detection + context enrichment (action_context, cron_context, stub_zone)
- [ ] 58-02-PLAN.md — Semantic validation E13, W5, E15, E16 + skeleton preservation

### Phase 59: Module Extension Pattern
**Goal**: Users can generate extension modules that inherit and extend existing Odoo modules with new fields, modified views, and correct dependencies
**Depends on**: Phase 55
**Requirements**: MEXT-01, MEXT-02, MEXT-03
**Success Criteria** (what must be TRUE):
  1. Generated _inherit model files correctly extend base Odoo models (e.g., _inherit = "hr.payslip") with new fields and proper super() call patterns in overridden methods
  2. Generated xpath view XML injects fields into existing form/tree views from base modules at correct insertion points
  3. Generated __manifest__.py includes the extended module in depends and the model registry validates the base module exists before generation proceeds
**Plans:** 2/2 plans complete
Plans:
- [ ] 59-01-PLAN.md — Pydantic schema + preprocessor + templates + renderer integration (extension model/view generation)
- [ ] 59-02-PLAN.md — E17 validation for xpath field references + known_odoo_models common_views

### Phase 60: Iterative Refinement
**Goal**: Users can add fields or models to an already-generated module without regenerating unchanged files
**Depends on**: Phase 56, Phase 59
**Requirements**: ITER-01, ITER-02, ITER-03
**Success Criteria** (what must be TRUE):
  1. Adding a field to an existing model updates only the model file, relevant view XML, and security CSV -- other files remain untouched (verified by checksum or manifest comparison)
  2. Adding a new model creates its model file, updates __init__.py, adds views/security, and updates manifest depends -- existing model files are not regenerated
  3. Generation manifest tracks what exists, and only affected pipeline stages re-run (not the full pipeline) -- the model registry validates new references against existing models
**Plans:** 2/2 plans complete
Plans:
- [ ] 60-01-PLAN.md — Iterative subpackage core: spec stash, diff-to-stage mapping, conflict detection, stub-zone merge
- [ ] 60-02-PLAN.md — Renderer iterative mode, --force/--dry-run CLI flags, resolve command group

### Phase 61: Computed Chain Generator
**Goal**: Users can define cross-model computed field chains (e.g., exam result grade -> enrollment grade points -> student CGPA) and the system generates correct implementations across all models in the chain
**Depends on**: Phase 57
**Requirements**: CCHN-01, CCHN-02, CCHN-03
**Success Criteria** (what must be TRUE):
  1. Spec defines chain steps across models, and Logic Writer generates compute method implementations in each model that correctly read from source fields and write to target fields
  2. Generated @api.depends decorators use related field dot notation for cross-model triggers (e.g., @api.depends('enrollment_ids.grade_points')) and store=True is set for fields needing recomputation
  3. Chain validator detects dependency cycles, verifies all intermediate fields exist in the model registry, and confirms correct computation order before generation
**Plans:** 2/2 plans complete
Plans:
- [ ] 61-01-PLAN.md — Pydantic chain schema + preprocessor rewrite (order=22) + E18-E22 chain validation
- [ ] 61-02-PLAN.md — Chain context in StubContext + stub report serialization + end-to-end integration

### Phase 62: Portal Controllers
**Goal**: Users can generate portal-facing features with controllers, QWeb templates, and security rules that restrict data to the portal user's linked records
**Depends on**: Phase 58, Phase 59
**Requirements**: PRTL-01, PRTL-02, PRTL-03
**Success Criteria** (what must be TRUE):
  1. Generated portal controllers inherit portal.CustomerPortal with ir.http routes, proper authentication decorators, and JSON serialization of record data
  2. Generated QWeb templates inherit portal.portal_my_home, add portal menu items, and render page templates with correct t-field/t-foreach directives
  3. Generated portal record rules restrict data access to the portal user's linked records (e.g., parent sees only their child's enrollment data) with correct domain expressions
**Plans:** 2 plans
Plans:
- [ ] 62-01-PLAN.md — Pydantic schema + preprocessor (order=95) + E23 ownership path validation
- [ ] 62-02-PLAN.md — 6 Jinja portal templates + render_portal() pipeline stage

### Phase 63: Bulk Operations
**Goal**: Users can generate bulk operation patterns -- mass creation with batched post-processing, wizard-based batch operations, and chunked processing with progress notifications
**Depends on**: Phase 58
**Requirements**: BULK-01, BULK-02, BULK-03
**Success Criteria** (what must be TRUE):
  1. Generated @api.model_create_multi methods batch post-processing operations (notifications, sequence assignment) instead of running them per-record
  2. Generated bulk wizard TransientModels include domain-based record selection, a preview step showing affected records, confirmation action, and error collection for partial failures
  3. Generated _process_batch() helpers accept configurable batch_size, process records in chunks, and emit bus.bus progress notifications during long operations
**Plans**: TBD

## Progress

**Execution Order:** Phases 55-63 execute sequentially, with 57/58 parallelizable after 56, and 59 parallelizable with 56-58.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 55. Cleanup | 1/1 | Complete    | 2026-03-08 |
| 56. Logic Writer Core | 2/2 | Complete    | 2026-03-08 |
| 57. Logic Writer Computed & Constraints | 2/2 | Complete    | 2026-03-08 |
| 58. Logic Writer Overrides & Actions | 2/2 | Complete    | 2026-03-08 |
| 59. Module Extension Pattern | 2/2 | Complete    | 2026-03-08 |
| 60. Iterative Refinement | 2/2 | Complete    | 2026-03-09 |
| 61. Computed Chain Generator | 2/2 | Complete    | 2026-03-09 |
| 62. Portal Controllers | 0/2 | In progress | - |
| 63. Bulk Operations | 0/? | Not started | - |

---
*Roadmap created: 2026-03-01*
*v1.0 shipped: 2026-03-03*
*v1.1 shipped: 2026-03-03*
*v1.2 shipped: 2026-03-04*
*v2.0 shipped: 2026-03-04*
*v2.1 shipped: 2026-03-04*
*v3.0 shipped: 2026-03-05*
*v3.1 shipped: 2026-03-05*
*v3.2 shipped: 2026-03-07*
*v3.3 shipped: 2026-03-08*
*v4.0 roadmap created: 2026-03-08*
