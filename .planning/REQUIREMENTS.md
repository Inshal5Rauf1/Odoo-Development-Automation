# Requirements: Agentic Odoo Module Development Workflow

**Defined:** 2026-03-01
**Revised:** 2026-03-01 (architecture pivot to GSD extension)
**Core Value:** Compress months of repetitive Odoo module development into days by extending GSD's orchestration with Odoo-specialized agents, knowledge, and validation.

## Workflow Sequence

The 12-step user workflow. The user interacts via their AI coding assistant (Claude Code, Gemini, Codex, OpenCode) with GSD + odoo-gen extension installed.

```
 1. NL Input         — User describes module need in natural language
 2. Follow-up        — System asks Odoo-specific questions to fill gaps
 3. Spec Parsing     — System generates structured module spec → user approves
 4. Module Search    — System semantically searches GitHub/OCA for similar modules
 5. Match Review     — System presents matches with scores and gap analysis
 6. Spec Refinement  — User adjusts spec based on what exists
 7. Path Selection   — User picks: fork a match OR build from scratch
 8. Prior Art Load   — System loads Odoo knowledge base (OCA patterns, version conventions)
 9. Stage Generation — Models → Views → Security → Logic → Tests → Manifest/Data → README
10. Human Review     — GSD checkpoint after each generation stage (approve/change/reject)
11. Validation       — pylint-odoo + Docker install + test execution
12. Fix Loop         — Auto-fix what it can, surface remaining issues for human resolution
```

## Requirement Categories

Requirements are split into two categories:
- **GSD-INHERITED**: Provided by GSD orchestration layer. We configure and wire them, not build them.
- **ODOO-SPECIFIC**: Pure Odoo domain work that we build from scratch.

## v1 Requirements

### GSD-Inherited (13 requirements — configured, not built)

These capabilities come from GSD. Our work is wiring them to Odoo-specific workflows.

- [x] **GSD-01**: Command invocation via AI coding assistant (GSD command registration system)
- [x] **GSD-02**: Rich terminal output — colored text, tables, progress indicators (GSD + AI assistant UI)
- [x] **GSD-03**: Configuration file for default settings (GSD `.planning/config.json` extended with Odoo fields)
- [x] **GSD-04**: Help text and usage descriptions for all commands (GSD command metadata)
- [x] **GSD-05**: Checkpoint-based human review — pause after each stage for approval (GSD checkpoint pattern)
- [x] **GSD-06**: Approve, request changes, or reject at each checkpoint (GSD feedback loop)
- [x] **GSD-07**: Incorporate feedback and regenerate rejected sections (GSD revision pattern)
- [x] **GSD-08**: State persistence — resume interrupted generation (GSD STATE.md)
- [x] **GSD-09**: Extensible knowledge base — team adds custom skills/patterns (GSD skills system)
- [x] **GSD-10**: Context management — fresh context per agent, prevent hallucination (GSD core feature)
- [x] **GSD-11**: Wave-based parallel execution for independent tasks (GSD execute-phase)
- [x] **GSD-12**: Git integration — atomic commits per task (GSD git patterns)
- [x] **GSD-13**: Agent spawning with specialized roles (GSD Task tool + agent definitions)

### Step 1: Extension Setup (NEW — replaces old CLI-01..04)

- [x] **EXT-01**: odoo-gen extension installs into `~/.claude/` alongside GSD with a single clone + setup command
- [x] **EXT-02**: Extension registers all odoo-gen commands with GSD command system
- [x] **EXT-03**: Extension adds Odoo-specific configuration fields (odoo_version, edition, output_dir, api_keys) to GSD config
- [x] **EXT-04**: Extension provides Odoo-specific agent definitions that GSD can spawn
- [x] **EXT-05**: Extension includes Python utility package (installable via `uv`/`pip`) for template rendering, validation, and search

### Step 1-2: Input & Interaction

- [ ] **INPT-01**: User can describe a module need in natural language via GSD command
- [ ] **INPT-02**: System asks structured follow-up questions to fill gaps in the description (models, fields, views, inheritance, user groups)
- [ ] **INPT-03**: System parses user input into a structured module specification (model names, field types, relationships, views needed, workflow states)
- [ ] **INPT-04**: User can review and approve the parsed specification before generation begins

### Step 4-7: Search & Reuse

- [ ] **SRCH-01**: System semantically searches GitHub repositories for Odoo modules similar to the user's description
- [ ] **SRCH-02**: System semantically searches OCA repositories for similar modules
- [ ] **SRCH-03**: System scores and ranks candidate modules by relevance to the user's intent
- [ ] **SRCH-04**: System presents top matches to the user with relevance scores, feature overlap, and gap analysis
- [ ] **SRCH-05**: User can select a match to fork-and-extend, or choose to build from scratch

### Step 6: Spec Refinement

- [ ] **REFN-01**: After viewing search results, user can adjust the module specification based on what already exists
- [ ] **REFN-02**: System highlights which parts of the spec are already covered by the matched module and which need to be built
- [ ] **REFN-03**: Adjusted spec replaces the original for all downstream generation steps

### Step 7: Fork & Extend

- [ ] **FORK-01**: System clones the selected matching module into the output directory
- [ ] **FORK-02**: System analyzes the forked module's structure (models, views, security, data files)
- [ ] **FORK-03**: System generates delta code to extend the forked module to match the user's refined specification
- [ ] **FORK-04**: System maintains a local vector index of OCA/GitHub module descriptions for fast semantic matching

### Step 8: Prior Art & Knowledge Base

- [ ] **KNOW-01**: System loads Odoo-specific knowledge base before generation (coding patterns, ORM conventions, version-specific syntax)
- [ ] **KNOW-02**: Knowledge base includes OCA coding standards, pylint-odoo rules, and common pitfall avoidance patterns
- [ ] **KNOW-03**: Knowledge base includes version-specific references (Odoo 17.0 API, field types, view syntax changes)
- [ ] **KNOW-04**: Knowledge base is extensible — team can add custom skills/patterns via GSD skills system

### Step 9: Code Generation

- [ ] **CODG-01**: System generates complete `__manifest__.py` with correct version prefix, dependencies, data file references, and metadata
- [ ] **CODG-02**: System generates Python model files with real fields, computed fields, onchange handlers, constraints, and CRUD overrides
- [ ] **CODG-03**: System generates XML view files (form, list, search views) that reference the generated models and fields correctly
- [ ] **CODG-04**: System generates action and menu XML files that wire views to the Odoo UI
- [ ] **CODG-05**: System generates `__init__.py` files with correct import chains for all Python modules
- [ ] **CODG-06**: System generates data files (sequences, default configuration) where the module spec requires them
- [ ] **CODG-07**: System generates wizard (TransientModel) files when the module spec includes multi-step user flows
- [ ] **CODG-08**: All generated Python code follows OCA coding standards (PEP 8, 120 char line length, proper import ordering)
- [ ] **CODG-09**: All generated XML uses correct Odoo 17.0 syntax (e.g., `<list>` not `<tree>`, inline `invisible`/`readonly` expressions not `attrs`)
- [ ] **CODG-10**: System generates a README.md explaining the module purpose, installation, configuration, role assignment, and usage

### Step 9: Security Generation

- [ ] **SECG-01**: System generates `ir.model.access.csv` with correct model references and CRUD permissions for all generated models
- [ ] **SECG-02**: System generates security group hierarchy (User and Manager roles) with proper `implied_ids` chains
- [ ] **SECG-03**: System generates record rules for multi-company scenarios when applicable
- [ ] **SECG-04**: System generates module category for the security group hierarchy
- [ ] **SECG-05**: Every generated model has at least one access control rule (no invisible-to-non-admin models)

### Step 9: Test Generation

- [ ] **TEST-01**: System generates `tests/__init__.py` and test files using `TransactionCase` base class
- [ ] **TEST-02**: Generated tests include model CRUD tests (create, read, update, delete)
- [ ] **TEST-03**: Generated tests include access rights tests (user role vs manager role permissions)
- [ ] **TEST-04**: Generated tests include computed field tests (verify calculations produce correct results)
- [ ] **TEST-05**: Generated tests include constraint tests (verify validation rules reject invalid data)
- [ ] **TEST-06**: Generated tests include workflow/state transition tests when the module has state machines

### Step 10: Human Review

*Note: GSD provides the checkpoint mechanism (GSD-05, GSD-06, GSD-07). These requirements specify WHERE checkpoints occur in the Odoo workflow.*

- [ ] **REVW-01**: System pauses for human review after model generation (fields, relationships, constraints)
- [ ] **REVW-02**: System pauses for human review after view generation (form, list, search XML)
- [ ] **REVW-03**: System pauses for human review after security generation (groups, ACLs, record rules)
- [ ] **REVW-04**: System pauses for human review after business logic generation (computed fields, workflows, CRUD overrides)
- [ ] **REVW-05**: User can approve, request changes, or reject at each checkpoint (wired to GSD-06)
- [ ] **REVW-06**: System incorporates user feedback and regenerates the rejected section (wired to GSD-07)

### Step 11-12: Quality & Validation

- [x] **QUAL-01**: System runs pylint-odoo on all generated Python and XML files
- [x] **QUAL-02**: System reports pylint-odoo violations with file, line number, and fix suggestions
- [x] **QUAL-03**: System spins up a Docker-based Odoo 17.0 + PostgreSQL environment for validation
- [x] **QUAL-04**: System installs the generated module on the Docker Odoo instance and reports install success/failure
- [x] **QUAL-05**: System runs the generated tests on the Docker Odoo instance and reports pass/fail results
- [ ] **QUAL-06**: System generates i18n `.pot` file for translatable strings
- [ ] **QUAL-07**: System parses Odoo error logs on validation failure and provides actionable diagnosis (which file, what broke, suggested fix)
- [x] **QUAL-08**: All generated code targets Odoo 17.0 API exclusively (no mixing of deprecated API patterns)
- [ ] **QUAL-09**: System attempts to auto-fix pylint-odoo violations and re-validate before escalating to human
- [ ] **QUAL-10**: System attempts to auto-fix Docker install failures (missing dependencies, XML errors) and re-validate before escalating to human

### Edition & Version Support

- [ ] **VERS-01**: System knows which Odoo modules are Enterprise-only (e.g., `account_asset`, `helpdesk`, `quality_control`)
- [ ] **VERS-02**: System flags when user's description requires Enterprise-only dependencies
- [ ] **VERS-03**: System offers Community-compatible alternatives when Enterprise dependencies are detected
- [ ] **VERS-04**: System supports generating modules for Odoo 18.0 in addition to 17.0
- [ ] **VERS-05**: System uses version-specific templates and syntax rules per target version
- [ ] **VERS-06**: User can specify target Odoo version via config or command parameter

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Multi-Agent Specialization

- **MAGT-01**: System uses separate specialized agents for models, views, security, and business logic
- **MAGT-02**: Agents review each other's output (maker-checker pattern)
- **MAGT-03**: System routes generation tasks to the most appropriate agent (Claude, Codex, Gemini)

### Advanced Module Intelligence

- **INTL-01**: System makes smart inheritance decisions (_inherit vs xpath vs new model) when extending forked modules
- **INTL-02**: System generates incremental diffs at each stage for fine-grained review
- **INTL-03**: System auto-resolves `__manifest__.py` dependencies by analyzing inherited models and referenced groups

### Agent Optimization (informed by Agent Lightning)

- **AOPT-01**: System captures generation traces (what was generated, what passed/failed validation)
- **AOPT-02**: System uses feedback loops to improve generation prompts over time
- **AOPT-03**: System optimizes per-agent performance based on success metrics

## Out of Scope

| Feature | Reason |
|---------|--------|
| Standalone CLI tool (pip install) | We extend GSD; the AI coding assistant IS the interface |
| Web UI / browser interface | Users interact via AI coding assistant terminal |
| Building our own orchestration | GSD provides this — proven, tested, maintained |
| Real-time collaborative editing | Single-user workflow via AI coding assistant |
| Autonomous deployment to production | ERP modules affect live business data; human deploys |
| Visual form/view designer | XML generation via agents is sufficient |
| Module marketplace / sharing | OCA already serves this role |
| Full business logic without human review | Silent failure in ERP is worst outcome |
| General-purpose code assistant | Module generator, not coding assistant |
| Post-install setup wizard | Standard Odoo Settings → Users UI suffices |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GSD-01..13 | Inherited (all phases) | Inherited |
| EXT-01 | Phase 1: GSD Extension + Odoo Foundation | Complete |
| EXT-02 | Phase 1: GSD Extension + Odoo Foundation | Complete |
| EXT-03 | Phase 1: GSD Extension + Odoo Foundation | Complete |
| EXT-04 | Phase 1: GSD Extension + Odoo Foundation | Complete |
| EXT-05 | Phase 1: GSD Extension + Odoo Foundation | Complete |
| KNOW-01 | Phase 2: Knowledge Base | Pending |
| KNOW-02 | Phase 2: Knowledge Base | Pending |
| KNOW-03 | Phase 2: Knowledge Base | Pending |
| KNOW-04 | Phase 2: Knowledge Base | Pending |
| QUAL-01 | Phase 3: Validation Infrastructure | Complete |
| QUAL-02 | Phase 3: Validation Infrastructure | Complete |
| QUAL-03 | Phase 3: Validation Infrastructure | Complete |
| QUAL-04 | Phase 3: Validation Infrastructure | Complete |
| QUAL-05 | Phase 3: Validation Infrastructure | Complete |
| QUAL-07 | Phase 3: Validation Infrastructure | Pending |
| QUAL-08 | Phase 3: Validation Infrastructure | Complete |
| INPT-01 | Phase 4: Input & Specification | Pending |
| INPT-02 | Phase 4: Input & Specification | Pending |
| INPT-03 | Phase 4: Input & Specification | Pending |
| INPT-04 | Phase 4: Input & Specification | Pending |
| CODG-01 | Phase 5: Core Code Generation | Pending |
| CODG-02 | Phase 5: Core Code Generation | Pending |
| CODG-03 | Phase 5: Core Code Generation | Pending |
| CODG-04 | Phase 5: Core Code Generation | Pending |
| CODG-05 | Phase 5: Core Code Generation | Pending |
| CODG-06 | Phase 5: Core Code Generation | Pending |
| CODG-07 | Phase 5: Core Code Generation | Pending |
| CODG-08 | Phase 5: Core Code Generation | Pending |
| CODG-09 | Phase 5: Core Code Generation | Pending |
| CODG-10 | Phase 5: Core Code Generation | Pending |
| SECG-01 | Phase 6: Security & Test Generation | Pending |
| SECG-02 | Phase 6: Security & Test Generation | Pending |
| SECG-03 | Phase 6: Security & Test Generation | Pending |
| SECG-04 | Phase 6: Security & Test Generation | Pending |
| SECG-05 | Phase 6: Security & Test Generation | Pending |
| TEST-01 | Phase 6: Security & Test Generation | Pending |
| TEST-02 | Phase 6: Security & Test Generation | Pending |
| TEST-03 | Phase 6: Security & Test Generation | Pending |
| TEST-04 | Phase 6: Security & Test Generation | Pending |
| TEST-05 | Phase 6: Security & Test Generation | Pending |
| TEST-06 | Phase 6: Security & Test Generation | Pending |
| REVW-01 | Phase 7: Human Review & Quality Loops | Pending |
| REVW-02 | Phase 7: Human Review & Quality Loops | Pending |
| REVW-03 | Phase 7: Human Review & Quality Loops | Pending |
| REVW-04 | Phase 7: Human Review & Quality Loops | Pending |
| REVW-05 | Phase 7: Human Review & Quality Loops | Pending |
| REVW-06 | Phase 7: Human Review & Quality Loops | Pending |
| QUAL-06 | Phase 7: Human Review & Quality Loops | Pending |
| QUAL-09 | Phase 7: Human Review & Quality Loops | Pending |
| QUAL-10 | Phase 7: Human Review & Quality Loops | Pending |
| SRCH-01 | Phase 8: Search & Fork-Extend | Pending |
| SRCH-02 | Phase 8: Search & Fork-Extend | Pending |
| SRCH-03 | Phase 8: Search & Fork-Extend | Pending |
| SRCH-04 | Phase 8: Search & Fork-Extend | Pending |
| SRCH-05 | Phase 8: Search & Fork-Extend | Pending |
| REFN-01 | Phase 8: Search & Fork-Extend | Pending |
| REFN-02 | Phase 8: Search & Fork-Extend | Pending |
| REFN-03 | Phase 8: Search & Fork-Extend | Pending |
| FORK-01 | Phase 8: Search & Fork-Extend | Pending |
| FORK-02 | Phase 8: Search & Fork-Extend | Pending |
| FORK-03 | Phase 8: Search & Fork-Extend | Pending |
| FORK-04 | Phase 8: Search & Fork-Extend | Pending |
| VERS-01 | Phase 9: Edition & Version Support | Pending |
| VERS-02 | Phase 9: Edition & Version Support | Pending |
| VERS-03 | Phase 9: Edition & Version Support | Pending |
| VERS-04 | Phase 9: Edition & Version Support | Pending |
| VERS-05 | Phase 9: Edition & Version Support | Pending |
| VERS-06 | Phase 9: Edition & Version Support | Pending |

**Coverage:**
- GSD-inherited: 13 (free)
- Odoo-specific (EXT): 5 (new)
- Odoo-specific (carried forward): 63
- Total v1: 81 (13 inherited + 68 built)
- Mapped to phases: 68 built requirements mapped
- Unmapped: 0

---
*Requirements defined: 2026-03-01*
*Revised: 2026-03-01 — architecture pivot to GSD extension, added EXT-01..05, recategorized GSD-01..13*
