# Roadmap: Agentic Odoo Module Development Workflow

## Overview

This roadmap delivers `odoo-gen`, a CLI tool that automates Odoo 17.0 module development through AI agents. The build order follows a dependency chain: CLI foundation first, then the validation gate (so every subsequent phase can verify its output), then the generation pipeline (input -> knowledge -> code -> security/tests -> review), then the search-and-fork differentiator, and finally multi-version support. Each phase produces a usable, testable capability. Nine phases cover all 67 v1 requirements at comprehensive depth.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: CLI Foundation** - Project skeleton with Typer CLI, configuration system, state management, and Jinja2 module scaffolding
- [ ] **Phase 2: Validation Infrastructure** - Docker-based Odoo 17.0 environment, pylint-odoo integration, module install testing, and quality reporting
- [ ] **Phase 3: Input and Specification** - Natural language module description, structured follow-up questions, spec parsing, and user approval flow
- [ ] **Phase 4: Knowledge Base** - Odoo-specific coding patterns, OCA standards, version-specific references, and extensible skill system
- [ ] **Phase 5: Core Code Generation** - Models, views, actions, manifests, init files, data, wizards, and README generation with OCA standards compliance
- [ ] **Phase 6: Security and Test Generation** - ACLs, group hierarchy, record rules, and comprehensive test suite generation
- [ ] **Phase 7: Human Review and Quality Loops** - Checkpoint system at each generation stage, feedback incorporation, i18n generation, and auto-fix loops
- [ ] **Phase 8: Search and Fork-Extend** - Semantic search of GitHub/OCA repos, match scoring, spec refinement, fork-and-extend workflow, and local vector index
- [ ] **Phase 9: Edition and Version Support** - CE/EE awareness, Enterprise dependency detection, Community alternatives, and Odoo 18.0 template support

## Phase Details

### Phase 1: CLI Foundation
**Goal**: Developer can install and run `odoo-gen` with working CLI commands, configuration, and empty-but-valid Odoo module scaffolding
**Depends on**: Nothing (first phase)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. User can run `odoo-gen new` and `odoo-gen validate` commands from the terminal and see structured help output
  2. User can run `odoo-gen --help` and see usage examples for all available commands
  3. CLI displays colored text, tables, and progress indicators during operation
  4. User can set default Odoo version, output directory, and edition in a configuration file that persists across sessions
  5. Running `odoo-gen new` scaffolds a valid Odoo 17.0 module directory structure (manifest, init, models dir, views dir, security dir, tests dir)
**Plans**: TBD

Plans:
- [ ] 01-01: TBD
- [ ] 01-02: TBD

### Phase 2: Validation Infrastructure
**Goal**: Developer can validate any Odoo module against real Odoo 17.0 and OCA quality standards, getting actionable pass/fail results
**Depends on**: Phase 1
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-04, QUAL-05, QUAL-07, QUAL-08
**Success Criteria** (what must be TRUE):
  1. User can run `odoo-gen validate <module_path>` and get a pylint-odoo report with file, line number, and fix suggestions for every violation
  2. System spins up a Docker Odoo 17.0 + PostgreSQL environment, installs the target module, and reports install success or failure
  3. System runs the module's tests on the Docker Odoo instance and reports pass/fail results per test
  4. When validation fails, system parses Odoo error logs and provides actionable diagnosis (which file broke, what went wrong, suggested fix)
  5. All validation checks enforce Odoo 17.0 API exclusively (deprecated patterns from older versions are flagged)
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Input and Specification
**Goal**: Developer can describe a module need in plain English and get back a structured, approved module specification ready for generation
**Depends on**: Phase 1
**Requirements**: INPT-01, INPT-02, INPT-03, INPT-04
**Success Criteria** (what must be TRUE):
  1. User can type a natural language description of a module need via the CLI and the system accepts it as input
  2. System asks targeted follow-up questions about models, fields, views, inheritance, and user groups to fill gaps in the description
  3. System produces a structured module specification (model names, field types, relationships, views needed, workflow states) from the conversation
  4. User can review the parsed specification and explicitly approve it before any generation begins
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

### Phase 4: Knowledge Base
**Goal**: Generation agents have access to Odoo-specific coding patterns, OCA standards, and version-specific references that prevent common mistakes
**Depends on**: Phase 1
**Requirements**: KNOW-01, KNOW-02, KNOW-03, KNOW-04
**Success Criteria** (what must be TRUE):
  1. Before generation, system loads Odoo 17.0 coding patterns (ORM conventions, field types, decorator usage, view syntax) into agent context
  2. Knowledge base includes OCA coding standards and pylint-odoo rule explanations so generated code avoids known violations
  3. Knowledge base includes Odoo 17.0-specific API references (e.g., `<list>` not `<tree>`, inline `invisible`/`readonly` not `attrs`)
  4. Team can add custom skills and patterns to the knowledge base that the system uses during subsequent generation runs
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

### Phase 5: Core Code Generation
**Goal**: System generates complete, real Odoo module code (not stubs) from an approved specification, following OCA standards
**Depends on**: Phase 2, Phase 3, Phase 4
**Requirements**: CODG-01, CODG-02, CODG-03, CODG-04, CODG-05, CODG-06, CODG-07, CODG-08, CODG-09, CODG-10
**Success Criteria** (what must be TRUE):
  1. Given an approved spec, system generates a complete `__manifest__.py` with correct version prefix, dependencies, data file references, and metadata
  2. System generates Python model files with real fields, computed fields, onchange handlers, constraints, and CRUD overrides matching the spec
  3. System generates XML view files (form, list, search), action files, and menu files that correctly reference generated models and fields
  4. All generated Python follows OCA coding standards (PEP 8, 120 char lines, proper import ordering) and all XML uses Odoo 17.0 syntax
  5. System generates wizard files, data files, init files, and a README as needed by the module spec
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD
- [ ] 05-03: TBD

### Phase 6: Security and Test Generation
**Goal**: Every generated module has complete security infrastructure and a meaningful test suite that verifies real behavior
**Depends on**: Phase 5
**Requirements**: SECG-01, SECG-02, SECG-03, SECG-04, SECG-05, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06
**Success Criteria** (what must be TRUE):
  1. System generates `ir.model.access.csv` with correct model references and CRUD permissions, plus a security group hierarchy (User/Manager) with proper `implied_ids`
  2. Every generated model has at least one access control rule -- no model is invisible to non-admin users
  3. System generates record rules for multi-company scenarios and a module category for the group hierarchy
  4. System generates test files using `TransactionCase` with real assertions covering CRUD, access rights, computed fields, constraints, and workflow transitions
  5. Generated tests are runnable via `odoo-gen validate` and exercise the actual security rules (user role vs manager role permissions)
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

### Phase 7: Human Review and Quality Loops
**Goal**: Developer reviews and approves each generation stage with the ability to request changes, and the system auto-fixes what it can before escalating
**Depends on**: Phase 5, Phase 6
**Requirements**: REVW-01, REVW-02, REVW-03, REVW-04, REVW-05, REVW-06, QUAL-06, QUAL-09, QUAL-10
**Success Criteria** (what must be TRUE):
  1. System pauses for human review after each generation stage (models, views, security, business logic) and waits for explicit approval
  2. User can approve, request changes, or reject at each checkpoint, and the system regenerates the rejected section incorporating feedback
  3. System generates an i18n `.pot` file for all translatable strings in the module
  4. When pylint-odoo violations are found, system attempts auto-fix and re-validates before escalating remaining issues to the user
  5. When Docker install or test failures occur, system attempts auto-fix (missing dependencies, XML errors) and re-validates before escalating
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

### Phase 8: Search and Fork-Extend
**Goal**: Developer can search for existing Odoo modules, see how they overlap with their need, and fork-and-extend a match instead of building from scratch
**Depends on**: Phase 5
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, REFN-01, REFN-02, REFN-03, FORK-01, FORK-02, FORK-03, FORK-04
**Success Criteria** (what must be TRUE):
  1. User can run `odoo-gen search <description>` and get ranked results from both GitHub and OCA repositories with relevance scores and feature overlap analysis
  2. System presents gap analysis showing which parts of the user's spec are already covered by a matched module and which need to be built
  3. User can select a match to fork or choose to build from scratch, and can adjust their spec based on what already exists
  4. When forking, system clones the module, analyzes its structure, and generates delta code to extend it to match the refined specification
  5. System maintains a local vector index of OCA/GitHub module descriptions for fast semantic matching without repeated API calls
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD
- [ ] 08-03: TBD

### Phase 9: Edition and Version Support
**Goal**: System is aware of Odoo edition differences and can generate modules targeting both 17.0 and 18.0 with correct version-specific patterns
**Depends on**: Phase 4, Phase 5
**Requirements**: VERS-01, VERS-02, VERS-03, VERS-04, VERS-05, VERS-06
**Success Criteria** (what must be TRUE):
  1. When a user's module description requires Enterprise-only dependencies, system detects and flags them with Community-compatible alternatives
  2. System knows which standard Odoo modules are Enterprise-only (e.g., `account_asset`, `helpdesk`, `quality_control`) and warns accordingly
  3. User can specify target Odoo version via CLI flag or config file, and the system uses version-specific templates and syntax rules
  4. System can generate modules for Odoo 18.0 in addition to 17.0, using correct version-specific API patterns for each
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9
(Phases 3 and 4 can execute in parallel after Phase 1; Phase 5 depends on 2, 3, and 4)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. CLI Foundation | 0/2 | Not started | - |
| 2. Validation Infrastructure | 0/2 | Not started | - |
| 3. Input and Specification | 0/1 | Not started | - |
| 4. Knowledge Base | 0/1 | Not started | - |
| 5. Core Code Generation | 0/3 | Not started | - |
| 6. Security and Test Generation | 0/2 | Not started | - |
| 7. Human Review and Quality Loops | 0/2 | Not started | - |
| 8. Search and Fork-Extend | 0/3 | Not started | - |
| 9. Edition and Version Support | 0/2 | Not started | - |
