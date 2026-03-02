# Roadmap: Agentic Odoo Module Development Workflow

## Overview

This roadmap delivers odoo-gen, a GSD extension that specializes the GSD orchestration framework for automated Odoo 17.0 module development. We inherit GSD's full orchestration layer (context management, state persistence, checkpoint coordination, agent spawning, git integration) and build Odoo-specific agents, knowledge, workflows, and validation tools on top.

The build order: extension setup first (so we have a working GSD extension), then knowledge base (so agents have Odoo expertise), then validation (so we can verify output), then input/spec parsing, then the generation pipeline (code → security → tests), then human review wiring, then search/fork (the differentiator), and finally multi-version support. Each phase produces a usable, testable capability.

Nine phases cover all 68 Odoo-specific requirements (plus 13 inherited from GSD).

## Key Architectural Difference from v1 Roadmap

**Old plan:** Build standalone Python CLI from scratch (Typer, custom config, custom state, custom orchestration).
**New plan:** Extend GSD. No standalone CLI. The AI coding assistant is the interface. We build:
1. GSD extension files (agents, commands, workflows, templates)
2. Odoo knowledge base (rules, patterns, references)
3. Python utility package (template rendering, validation, search)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: GSD Extension + Odoo Foundation** — Extension structure, command registration, Odoo config, agent definitions, Python utility package with Jinja2 scaffold engine
- [x] **Phase 2: Knowledge Base** — Odoo 17 coding patterns, OCA standards, pylint-odoo rules, version-specific references, extensible skill system
- [x] **Phase 3: Validation Infrastructure** — pylint-odoo integration, Docker-based Odoo 17.0 environment, module install testing, quality reporting
- [x] **Phase 4: Input & Specification** — Natural language module description, structured Odoo follow-up questions, spec parsing, user approval flow
- [ ] **Phase 5: Core Code Generation** — Models, views, actions, manifests, init files, data, wizards, and README generation with OCA standards compliance
- [ ] **Phase 6: Security & Test Generation** — ACLs, group hierarchy, record rules, comprehensive test suite generation
- [ ] **Phase 7: Human Review & Quality Loops** — GSD checkpoint wiring at each generation stage, feedback incorporation, i18n generation, auto-fix loops
- [ ] **Phase 8: Search & Fork-Extend** — Semantic search of GitHub/OCA repos, match scoring, spec refinement, fork-and-extend workflow, local vector index
- [ ] **Phase 9: Edition & Version Support** — CE/EE awareness, Enterprise dependency detection, Community alternatives, Odoo 18.0 template support

## Phase Details

### Phase 1: GSD Extension + Odoo Foundation
**Goal**: odoo-gen is a working GSD extension that registers commands, provides Odoo-specific agent definitions, and can scaffold a valid Odoo 17.0 module via `/odoo-gen:new`
**Depends on**: GSD installed in `~/.claude/get-shit-done/`
**Requirements**: EXT-01, EXT-02, EXT-03, EXT-04, EXT-05
**Success Criteria** (what must be TRUE):
  1. User can clone odoo-gen into `~/.claude/odoo-gen/` and run a setup command that registers all commands
  2. User can invoke `/odoo-gen:new` in their AI coding assistant and it triggers the module scaffolding workflow
  3. Odoo-specific config fields (odoo_version, edition, output_dir, api_keys) are available in GSD config
  4. Agent definitions exist for odoo-scaffold, odoo-model-gen, odoo-view-gen, odoo-security-gen, odoo-test-gen, odoo-validator (stubs for now, implemented in later phases)
  5. Python utility package installs via `uv pip install` and provides Jinja2 template rendering that produces a valid Odoo 17.0 module with real content (model, views, security, tests)
  6. All stub commands (/odoo-gen:validate, /odoo-gen:search, /odoo-gen:research, /odoo-gen:plan, /odoo-gen:phases, /odoo-gen:extend, /odoo-gen:history) are registered and show informative descriptions
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Extension structure, install.sh, config defaults, and agent definitions
- [x] 01-02-PLAN.md — All 12 /odoo-gen:* command registrations
- [x] 01-03-PLAN.md — Python utility package with CLI, renderer, and Jinja2 templates
- [x] 01-04-PLAN.md — Scaffold workflow, help workflow, and end-to-end integration verification

### Phase 2: Knowledge Base
**Goal**: Odoo agents have access to comprehensive coding patterns, OCA standards, and version-specific references that prevent common mistakes during generation
**Depends on**: Phase 1
**Requirements**: KNOW-01, KNOW-02, KNOW-03, KNOW-04
**Success Criteria** (what must be TRUE):
  1. Before generation, agents can load Odoo 17.0 coding patterns (ORM conventions, field types, decorator usage, view syntax) from knowledge base files
  2. Knowledge base includes OCA coding standards and pylint-odoo rule explanations so generated code avoids known violations
  3. Knowledge base includes Odoo 17.0-specific API references (e.g., `<list>` not `<tree>`, inline `invisible`/`readonly` not `attrs`)
  4. Team can add custom skills and patterns to the knowledge base that agents use during subsequent generation runs (follows GSD skills system pattern)
  5. Knowledge base organized as GSD-compatible skill files (rules/*.md) following UI UX Pro Max Skill architecture pattern
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md -- MASTER.md + core category files (models, views, security, manifest)
- [x] 02-02-PLAN.md -- Remaining category files (testing, actions, data, i18n, controllers, wizards, inheritance)
- [x] 02-03-PLAN.md -- Custom rules extensibility, agent KB wiring, install.sh update

### Phase 3: Validation Infrastructure
**Goal**: Any Odoo module can be validated against real Odoo 17.0 and OCA quality standards, getting actionable pass/fail results
**Depends on**: Phase 1 (Python utility package)
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-04, QUAL-05, QUAL-07, QUAL-08
**Success Criteria** (what must be TRUE):
  1. `/odoo-gen:validate` runs pylint-odoo on target module and reports violations with file, line number, and fix suggestions
  2. System spins up a Docker Odoo 17.0 + PostgreSQL environment, installs the target module, and reports install success or failure
  3. System runs the module's tests on the Docker Odoo instance and reports pass/fail results per test
  4. When validation fails, system parses Odoo error logs and provides actionable diagnosis (which file broke, what went wrong, suggested fix)
  5. All validation checks enforce Odoo 17.0 API exclusively (deprecated patterns from older versions are flagged)
**Plans**: TBD

Plans:
- [x] 03-01-PLAN.md -- pylint-odoo integration and Docker-based validation environment
- [x] 03-02-PLAN.md -- Module install testing and test execution
- [x] 03-03-PLAN.md -- Error diagnosis and CLI integration

### Phase 4: Input & Specification
**Goal**: User can describe a module need in plain English and get back a structured, approved module specification ready for generation
**Depends on**: Phase 1, Phase 2 (knowledge base informs follow-up questions)
**Requirements**: INPT-01, INPT-02, INPT-03, INPT-04
**Success Criteria** (what must be TRUE):
  1. User can type a natural language description of a module need and the system accepts it as input
  2. System asks targeted Odoo-specific follow-up questions about models, fields, views, inheritance, and user groups to fill gaps
  3. System produces a structured module specification (model names, field types, relationships, views needed, workflow states) from the conversation
  4. User can review the parsed specification and explicitly approve it before any generation begins
**Plans**: TBD

Plans:
- [x] 04-01-PLAN.md -- Specification workflow, plan command, dual-mode agent
- [x] 04-02-PLAN.md -- Approval flow, spec rendering, user review options

### Phase 5: Core Code Generation
**Goal**: System generates complete, real Odoo module code (not stubs) from an approved specification, following OCA standards
**Depends on**: Phase 2 (knowledge base), Phase 3 (validation), Phase 4 (spec input)
**Requirements**: CODG-01, CODG-02, CODG-03, CODG-04, CODG-05, CODG-06, CODG-07, CODG-08, CODG-09, CODG-10
**Success Criteria** (what must be TRUE):
  1. Given an approved spec, system generates a complete `__manifest__.py` with correct version prefix, dependencies, data file references, and metadata
  2. System generates Python model files with real fields, computed fields, onchange handlers, constraints, and CRUD overrides matching the spec
  3. System generates XML view files (form, list, search), action files, and menu files that correctly reference generated models and fields
  4. All generated Python follows OCA coding standards (PEP 8, 120 char lines, proper import ordering) and all XML uses Odoo 17.0 syntax
  5. System generates wizard files, data files, init files, and a README as needed by the module spec
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md — Renderer extensions + new Jinja2 templates (computed stubs, sequences, wizards, statusbar)
- [x] 05-02-PLAN.md — Agent activation: odoo-model-gen, odoo-view-gen, odoo-test-gen full system prompts
- [ ] 05-03-PLAN.md — generate.md workflow + spec.md trigger hook + REQUIREMENTS.md wording fixes

### Phase 6: Security & Test Generation
**Goal**: Every generated module has complete security infrastructure and a meaningful test suite that verifies real behavior
**Depends on**: Phase 5
**Requirements**: SECG-01, SECG-02, SECG-03, SECG-04, SECG-05, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06
**Success Criteria** (what must be TRUE):
  1. System generates `ir.model.access.csv` with correct model references and CRUD permissions, plus a security group hierarchy (User/Manager) with proper `implied_ids`
  2. Every generated model has at least one access control rule — no model is invisible to non-admin users
  3. System generates record rules for multi-company scenarios and a module category for the group hierarchy
  4. System generates test files using `TransactionCase` with real assertions covering CRUD, access rights, computed fields, constraints, and workflow transitions
  5. Generated tests are runnable via `/odoo-gen:validate` and exercise the actual security rules
**Plans**: 2 plans

Plans:
- [ ] 06-01-PLAN.md — TDD: has_company_field detection + record_rules.xml.j2 template + renderer extensions (SECG-01, SECG-03, SECG-04, SECG-05)
- [ ] 06-02-PLAN.md — Expand test_model.py.j2 + activate odoo-test-gen + activate odoo-security-gen + update generate.md (SECG-02, SECG-04, TEST-01..06)

### Phase 7: Human Review & Quality Loops
**Goal**: GSD checkpoints are wired to each Odoo generation stage, with feedback incorporation and auto-fix before escalating
**Depends on**: Phase 5, Phase 6
**Requirements**: REVW-01, REVW-02, REVW-03, REVW-04, REVW-05, REVW-06, QUAL-06, QUAL-09, QUAL-10
**Success Criteria** (what must be TRUE):
  1. System pauses (via GSD checkpoint) for human review after each generation stage (models, views, security, business logic) and waits for explicit approval
  2. User can approve, request changes, or reject at each checkpoint, and the system regenerates the rejected section incorporating feedback
  3. System generates an i18n `.pot` file for all translatable strings in the module
  4. When pylint-odoo violations are found, system attempts auto-fix and re-validates before escalating remaining issues to the user
  5. When Docker install or test failures occur, system attempts auto-fix and re-validates before escalating
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

### Phase 8: Search & Fork-Extend
**Goal**: User can search for existing Odoo modules, see how they overlap with their need, and fork-and-extend a match instead of building from scratch
**Depends on**: Phase 5
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, REFN-01, REFN-02, REFN-03, FORK-01, FORK-02, FORK-03, FORK-04
**Success Criteria** (what must be TRUE):
  1. `/odoo-gen:search` returns ranked results from both GitHub and OCA repositories with relevance scores and feature overlap analysis
  2. System presents gap analysis showing which parts of the user's spec are already covered and which need to be built
  3. User can select a match to fork or choose to build from scratch, and can adjust their spec based on what exists
  4. When forking, system clones the module, analyzes its structure, and generates delta code to match the refined specification
  5. System maintains a local vector index of OCA/GitHub module descriptions for fast semantic matching
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD
- [ ] 08-03: TBD

### Phase 9: Edition & Version Support
**Goal**: System is aware of Odoo edition differences and can generate modules targeting both 17.0 and 18.0 with correct version-specific patterns
**Depends on**: Phase 2 (knowledge base), Phase 5 (generation)
**Requirements**: VERS-01, VERS-02, VERS-03, VERS-04, VERS-05, VERS-06
**Success Criteria** (what must be TRUE):
  1. When a user's module description requires Enterprise-only dependencies, system detects and flags them with Community-compatible alternatives
  2. System knows which standard Odoo modules are Enterprise-only and warns accordingly
  3. User can specify target Odoo version via config or command parameter, and the system uses version-specific templates and syntax rules
  4. System can generate modules for Odoo 18.0 in addition to 17.0, using correct version-specific API patterns for each
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9
(Phases 2 and 3 can execute in parallel after Phase 1; Phase 5 depends on 2, 3, and 4)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. GSD Extension + Odoo Foundation | 4/4 | Complete | 2026-03-01 |
| 2. Knowledge Base | 3/3 | Complete | 2026-03-01 |
| 3. Validation Infrastructure | 3/3 | Complete | 2026-03-01 |
| 4. Input & Specification | 2/2 | Complete | 2026-03-02 |
| 5. Core Code Generation | 2/3 | In Progress|  |
| 6. Security & Test Generation | 2/2 | Complete | 2026-03-02 |
| 7. Human Review & Quality Loops | 0/2 | Not started | - |
| 8. Search & Fork-Extend | 0/3 | Not started | - |
| 9. Edition & Version Support | 0/2 | Not started | - |

---
*Roadmap created: 2026-03-01*
*Revised: 2026-03-01 — architecture pivot to GSD extension*
*Revised: 2026-03-02 — Phase 5 plans defined*
*Revised: 2026-03-02 — Phase 6 plans defined (06-01, 06-02)*
