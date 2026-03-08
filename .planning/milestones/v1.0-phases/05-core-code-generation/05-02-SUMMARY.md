---
phase: 05-core-code-generation
plan: "02"
subsystem: ai-agents-layer
tags: [agents, odoo-model-gen, odoo-view-gen, odoo-test-gen, two-pass-generation, odoo-17]
dependency_graph:
  requires:
    - "05-01 — Jinja2 rendering engine (produces # TODO stubs that model-gen fills)"
  provides:
    - "odoo-model-gen agent: full two-pass rewrite prompt for computed/onchange/constrains method bodies"
    - "odoo-view-gen agent: Wave 2 view enrichment with state action buttons"
    - "odoo-test-gen agent: Phase 5 scope computed field + constraint + onchange test generation"
  affects:
    - "agents/odoo-model-gen.md — Pass 2 of hybrid Jinja2+AI generation pipeline"
    - "agents/odoo-view-gen.md — Wave 2 of generate.md workflow"
    - "agents/odoo-test-gen.md — Phase 5 partial test generation"
tech_stack:
  added: []
  patterns:
    - "Two-pass generation: Jinja2 structural pass + AI method body pass"
    - "FORBIDDEN list pattern in agent prompts for Odoo 17.0 anti-patterns"
    - "for rec in self: iteration enforced for computed and constrained methods"
    - "self.field direct assignment enforced for onchange methods (single-record UI context)"
    - "inline invisible= without attrs= for Odoo 17.0 XML"
key_files:
  created: []
  modified:
    - agents/odoo-model-gen.md
    - agents/odoo-view-gen.md
    - agents/odoo-test-gen.md
decisions:
  - "odoo-model-gen uses Write tool to rewrite ENTIRE model file (not patch stubs inline) — safer than partial edits"
  - "odoo-view-gen Wave 2 only enriches <header> action buttons; kanban deferred to Phase 7"
  - "odoo-test-gen Phase 5 scope is computed/constraint/onchange only; full CRUD + access rights deferred to Phase 6"
  - "All three agents include FORBIDDEN list to prevent Odoo 17.0 anti-patterns (@api.multi, attrs=, <list>, SavepointCase)"
metrics:
  duration: "2 minutes"
  completed: "2026-03-02"
  tasks_completed: 2
  files_created: 0
  files_modified: 3
---

# Phase 5 Plan 02: AI Agents Layer Summary

**One-liner:** Fully activated three Odoo agents with FORBIDDEN/REQUIRED pattern enforcement: model-gen performs two-pass method body rewrite, view-gen enriches state buttons, test-gen generates computed/constraint/onchange tests with TransactionCase.

## What Was Built

### Task 1: Full odoo-model-gen agent system prompt

Replaced the stub "not yet available" content with a complete, production-ready system prompt:

- **Identity and mission**: Pass 2 of hybrid two-pass generation — reads Jinja2-rendered model file with `# TODO` stubs and rewrites ENTIRE file with complete OCA-compliant method bodies
- **Input/output contract**: Explicit Read model + spec.json, Write complete file at same path
- **FORBIDDEN list (8 rules)**: `@api.multi`, `@api.one`, `@api.returns`, `states=` field param, `self.pool.get()`, `_columns = {}`, `from openerp import`, SQL injection via string formatting
- **REQUIRED patterns (3 patterns)**:
  - Computed: `for rec in self:` with `rec.field = value`
  - Onchange: `self.field =` direct assignment (single-record UI context)
  - Constrains: `for rec in self:` with `raise ValidationError`
- **Execution steps**: 6-step protocol (Read model → Read spec → Identify TODOs → Infer logic → Write → Confirm)
- **KB @includes**: MASTER.md, models.md, inheritance.md
- **Wizard action method pattern**: `action_open_{xml_id}()` with `ensure_one()` and context defaults
- **Removed**: "not yet available" redirect to /odoo-gen:new

### Task 2: Full odoo-view-gen and partial odoo-test-gen prompts

**odoo-view-gen.md (Wave 2 view enrichment)**:
- **Identity**: Wave 2 of generate.md workflow — enriches XML after model files are complete
- **Input contract**: views XML + completed models .py + spec.json
- **What is enriched**: Only form view `<header>` state action buttons (kanban deferred to Phase 7, tree/search structure unchanged)
- **FORBIDDEN XML list (4 rules)**: `attrs=` attribute, `states=` on buttons, `<list>` tag (use `<tree>`), `widget="statusbar"` inside `<sheet>`
- **REQUIRED patterns**: `invisible="state != 'draft'"` inline, `class="btn-primary"` for main CTA, `statusbar_visible` no-spaces format
- **Full example**: Complete `<header>` block with draft/confirmed/done/cancelled button guards
- **KB @includes**: MASTER.md, views.md, actions.md
- **Removed**: "not yet available" redirect

**odoo-test-gen.md (Phase 5 partial scope)**:
- **Explicit Phase 5 scope**: computed field tests, constraint tests, onchange tests ONLY
- **REQUIRED patterns**: `TransactionCase`, `setUpClass` with `cls.Model = cls.env[model_name]`
- **Computed test template**: `test_compute_{field}_basic` + `test_compute_{field}_zero_case`
- **Constraint test template**: `test_{field}_constraint_valid` + `test_{field}_constraint_invalid` with `assertRaises(ValidationError)`
- **FORBIDDEN**: `SavepointCase`, `@api.multi`, direct DB queries
- **KB @includes**: MASTER.md, testing.md
- **Phase 6 note**: Full CRUD + access rights + workflow tests deferred

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 3da16ff | feat(05-02): fully activate odoo-model-gen agent with two-pass rewrite prompt |
| Task 2 | 3a6e83e | feat(05-02): fully activate odoo-view-gen and partial odoo-test-gen agents |

## Verification Results

```
# No "not yet available" stubs in any agent file:
grep -l "not yet available" agents/odoo-{model,view,test}-gen.md
(empty — all three fully activated)

# KB @includes present in all three agents:
agents/odoo-model-gen.md: MASTER.md, models.md, inheritance.md
agents/odoo-view-gen.md:  MASTER.md, views.md, actions.md
agents/odoo-test-gen.md:  MASTER.md, testing.md

# Keyword verification counts:
odoo-model-gen.md: 18 matches (FORBIDDEN|for rec in self|@api.depends|Write tool|rewrite)
odoo-view-gen.md:  17 matches (FORBIDDEN|invisible|statusbar|Wave 2|Write tool)
odoo-test-gen.md:  14 matches (TransactionCase|computed|assertRaises|ValidationError|Phase 5 scope)
```

## Deviations from Plan

None — plan executed exactly as written.

## Success Criteria Verification

- [x] odoo-model-gen.md: Contains FORBIDDEN list, `for rec in self:` requirement, Write tool rewrite pattern, wizard action method pattern, KB @includes, no "not yet available" text
- [x] odoo-view-gen.md: Contains FORBIDDEN XML list (attrs=, states=, list tag), state button invisible pattern, statusbar_visible requirement, KB @includes, no "not yet available" text
- [x] odoo-test-gen.md: Contains TransactionCase pattern, computed field test template (assertRaises for constraints), Phase 5 scope declaration, KB @includes
- [x] No agent file redirects to /odoo-gen:new as the only action

## Self-Check: PASSED
