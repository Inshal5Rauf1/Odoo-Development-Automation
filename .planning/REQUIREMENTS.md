# Requirements: Agentic Odoo Module Development Workflow

**Defined:** 2026-03-01
**Core Value:** Compress months of repetitive Odoo module development into days by leveraging existing open-source modules and coordinating AI agents, so developers focus on business logic and design decisions.

## Workflow Sequence

The 12-step user workflow that defines the system's end-to-end flow:

```
 1. NL Input         — User describes module need in natural language
 2. Follow-up        — System asks structured questions to fill gaps
 3. Spec Parsing     — System generates structured module spec → user approves
 4. Module Search    — System semantically searches GitHub/OCA for similar modules
 5. Match Review     — System presents matches with scores and gap analysis
 6. Spec Refinement  — User adjusts spec based on what exists (e.g., "OCA handles X, I just need Y")
 7. Path Selection   — User picks: fork a match OR build from scratch
 8. Prior Art Load   — System loads Odoo knowledge base (erp_claude skills, OCA patterns, version conventions)
 9. Stage Generation — Models → Views → Security → Logic → Tests → Manifest/Data → README
10. Human Review     — Checkpoint after each generation stage (approve/change/reject)
11. Validation       — pylint-odoo + Docker install + test execution
12. Fix Loop         — Auto-fix what it can, surface remaining issues for human resolution
```

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Step 1-2: Input & Interaction

- [ ] **INPT-01**: User can describe a module need in natural language via CLI command
- [ ] **INPT-02**: System asks structured follow-up questions to fill gaps in the description (models, fields, views, inheritance, user groups)
- [ ] **INPT-03**: System parses user input into a structured module specification (model names, field types, relationships, views needed, workflow states)
- [ ] **INPT-04**: User can review and approve the parsed specification before generation begins

### Step 1: CLI Interface

- [ ] **CLI-01**: User can invoke the tool via CLI commands (e.g., `odoo-gen new`, `odoo-gen search`, `odoo-gen validate`)
- [ ] **CLI-02**: CLI displays rich terminal output (colored text, tables, progress indicators)
- [ ] **CLI-03**: CLI supports configuration file for default settings (target Odoo version, output directory, preferred edition)
- [ ] **CLI-04**: CLI provides help text and usage examples for all commands

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
- [ ] **KNOW-04**: Knowledge base is extensible — team can add custom skills/patterns that the system uses during generation

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
- [ ] **CODG-10**: System generates a README.md explaining the module purpose, installation, configuration, role assignment (via Settings → Users), and usage

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

- [ ] **REVW-01**: System pauses for human review after model generation (fields, relationships, constraints)
- [ ] **REVW-02**: System pauses for human review after view generation (form, list, search XML)
- [ ] **REVW-03**: System pauses for human review after security generation (groups, ACLs, record rules)
- [ ] **REVW-04**: System pauses for human review after business logic generation (computed fields, workflows, CRUD overrides)
- [ ] **REVW-05**: User can approve, request changes, or reject at each checkpoint
- [ ] **REVW-06**: System incorporates user feedback and regenerates the rejected section

### Step 11-12: Quality & Validation

- [ ] **QUAL-01**: System runs pylint-odoo on all generated Python and XML files
- [ ] **QUAL-02**: System reports pylint-odoo violations with file, line number, and fix suggestions
- [ ] **QUAL-03**: System spins up a Docker-based Odoo 17.0 + PostgreSQL environment for validation
- [ ] **QUAL-04**: System installs the generated module on the Docker Odoo instance and reports install success/failure
- [ ] **QUAL-05**: System runs the generated tests on the Docker Odoo instance and reports pass/fail results
- [ ] **QUAL-06**: System generates i18n `.pot` file for translatable strings
- [ ] **QUAL-07**: System parses Odoo error logs on validation failure and provides actionable diagnosis (which file, what broke, suggested fix)
- [ ] **QUAL-08**: All generated code targets Odoo 17.0 API exclusively (no mixing of deprecated API patterns)
- [ ] **QUAL-09**: System attempts to auto-fix pylint-odoo violations and re-validate before escalating to human
- [ ] **QUAL-10**: System attempts to auto-fix Docker install failures (missing dependencies, XML errors) and re-validate before escalating to human

### Edition & Version Support

- [ ] **VERS-01**: System knows which Odoo modules are Enterprise-only (e.g., `account_asset`, `helpdesk`, `quality_control`)
- [ ] **VERS-02**: System flags when user's description requires Enterprise-only dependencies
- [ ] **VERS-03**: System offers Community-compatible alternatives when Enterprise dependencies are detected
- [ ] **VERS-04**: System supports generating modules for Odoo 18.0 in addition to 17.0
- [ ] **VERS-05**: System uses version-specific templates and syntax rules per target version
- [ ] **VERS-06**: User can specify target Odoo version via CLI flag or configuration

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

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Web UI / browser interface | Massive scope increase; users are developers who live in terminals. CLI-only for v1. |
| Real-time collaborative editing | Single-user CLI workflow; 1-2 modules/week doesn't justify collaboration tooling |
| Autonomous deployment to production | ERP modules affect live business data; auto-deploying AI-generated code is reckless |
| Visual form/view designer | Building a visual Odoo view editor is a standalone project; XML generation is sufficient |
| Module marketplace / sharing | Distribution and quality control are tangential; OCA already serves this role |
| Full business logic without human review | "Silent failure" is the worst outcome in ERP; business logic must be human-reviewed |
| General-purpose code assistant | A module generator and a coding assistant are different products; stay focused |
| Post-install setup wizard | Standard Odoo Settings → Users UI is sufficient for role assignment |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 1: CLI Foundation | Pending |
| CLI-02 | Phase 1: CLI Foundation | Pending |
| CLI-03 | Phase 1: CLI Foundation | Pending |
| CLI-04 | Phase 1: CLI Foundation | Pending |
| QUAL-01 | Phase 2: Validation Infrastructure | Pending |
| QUAL-02 | Phase 2: Validation Infrastructure | Pending |
| QUAL-03 | Phase 2: Validation Infrastructure | Pending |
| QUAL-04 | Phase 2: Validation Infrastructure | Pending |
| QUAL-05 | Phase 2: Validation Infrastructure | Pending |
| QUAL-07 | Phase 2: Validation Infrastructure | Pending |
| QUAL-08 | Phase 2: Validation Infrastructure | Pending |
| INPT-01 | Phase 3: Input and Specification | Pending |
| INPT-02 | Phase 3: Input and Specification | Pending |
| INPT-03 | Phase 3: Input and Specification | Pending |
| INPT-04 | Phase 3: Input and Specification | Pending |
| KNOW-01 | Phase 4: Knowledge Base | Pending |
| KNOW-02 | Phase 4: Knowledge Base | Pending |
| KNOW-03 | Phase 4: Knowledge Base | Pending |
| KNOW-04 | Phase 4: Knowledge Base | Pending |
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
| SECG-01 | Phase 6: Security and Test Generation | Pending |
| SECG-02 | Phase 6: Security and Test Generation | Pending |
| SECG-03 | Phase 6: Security and Test Generation | Pending |
| SECG-04 | Phase 6: Security and Test Generation | Pending |
| SECG-05 | Phase 6: Security and Test Generation | Pending |
| TEST-01 | Phase 6: Security and Test Generation | Pending |
| TEST-02 | Phase 6: Security and Test Generation | Pending |
| TEST-03 | Phase 6: Security and Test Generation | Pending |
| TEST-04 | Phase 6: Security and Test Generation | Pending |
| TEST-05 | Phase 6: Security and Test Generation | Pending |
| TEST-06 | Phase 6: Security and Test Generation | Pending |
| REVW-01 | Phase 7: Human Review and Quality Loops | Pending |
| REVW-02 | Phase 7: Human Review and Quality Loops | Pending |
| REVW-03 | Phase 7: Human Review and Quality Loops | Pending |
| REVW-04 | Phase 7: Human Review and Quality Loops | Pending |
| REVW-05 | Phase 7: Human Review and Quality Loops | Pending |
| REVW-06 | Phase 7: Human Review and Quality Loops | Pending |
| QUAL-06 | Phase 7: Human Review and Quality Loops | Pending |
| QUAL-09 | Phase 7: Human Review and Quality Loops | Pending |
| QUAL-10 | Phase 7: Human Review and Quality Loops | Pending |
| SRCH-01 | Phase 8: Search and Fork-Extend | Pending |
| SRCH-02 | Phase 8: Search and Fork-Extend | Pending |
| SRCH-03 | Phase 8: Search and Fork-Extend | Pending |
| SRCH-04 | Phase 8: Search and Fork-Extend | Pending |
| SRCH-05 | Phase 8: Search and Fork-Extend | Pending |
| REFN-01 | Phase 8: Search and Fork-Extend | Pending |
| REFN-02 | Phase 8: Search and Fork-Extend | Pending |
| REFN-03 | Phase 8: Search and Fork-Extend | Pending |
| FORK-01 | Phase 8: Search and Fork-Extend | Pending |
| FORK-02 | Phase 8: Search and Fork-Extend | Pending |
| FORK-03 | Phase 8: Search and Fork-Extend | Pending |
| FORK-04 | Phase 8: Search and Fork-Extend | Pending |
| VERS-01 | Phase 9: Edition and Version Support | Pending |
| VERS-02 | Phase 9: Edition and Version Support | Pending |
| VERS-03 | Phase 9: Edition and Version Support | Pending |
| VERS-04 | Phase 9: Edition and Version Support | Pending |
| VERS-05 | Phase 9: Edition and Version Support | Pending |
| VERS-06 | Phase 9: Edition and Version Support | Pending |

**Coverage:**
- v1 requirements: 67 total
- Mapped to phases: 67
- Unmapped: 0

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-01 after roadmap phase mapping*
