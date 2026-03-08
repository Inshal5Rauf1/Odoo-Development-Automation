---
phase: 09-edition-version-support
plan: 03
subsystem: cli-integration
tags: [check-edition, version-awareness, agents, knowledge-base, 18.0]
dependency_graph:
  requires:
    - phase: 09-01
      provides: "Enterprise module registry and check_enterprise_dependencies()"
    - phase: 09-02
      provides: "Versioned templates (17.0/18.0/shared) and create_versioned_renderer()"
  provides:
    - "check-edition CLI command for Enterprise dependency detection"
    - "Version-aware render command (--var odoo_version=18.0)"
    - "Version-aware list-templates command (--version flag)"
    - "Spec workflow Step 3.5 Enterprise compatibility check"
    - "All 8 agents updated for 17.0/18.0 version awareness"
    - "Knowledge base Changed in 18.0 sections in models.md, views.md, manifest.md, MASTER.md"
  affects: [spec-workflow, cli, agents, knowledge-base]
tech_stack:
  added: []
  patterns: ["Edition check in spec workflow before approval gate", "Version-conditional agent sections"]
key_files:
  created: []
  modified:
    - python/src/odoo_gen_utils/cli.py
    - workflows/spec.md
    - agents/odoo-scaffold.md
    - agents/odoo-model-gen.md
    - agents/odoo-view-gen.md
    - agents/odoo-test-gen.md
    - agents/odoo-security-gen.md
    - agents/odoo-validator.md
    - agents/odoo-search.md
    - agents/odoo-extend.md
    - knowledge/models.md
    - knowledge/views.md
    - knowledge/manifest.md
    - knowledge/MASTER.md
decisions:
  - "check-edition exits 0 always (warnings are informational per Decision B -- never blocks)"
  - "render command uses create_versioned_renderer when --var odoo_version is provided"
  - "list-templates shows version labels ([17.0], [18.0], [shared]) for directory-based templates"
  - "spec.md Step 3.5 offers 3 options for EE deps: substitute/keep/remove"
  - "18.0 Docker validation deferred (noted in odoo-validator.md)"
metrics:
  duration: 5 min
  completed: "2026-03-03T04:47:00Z"
  tasks_completed: 2
  tasks_total: 2
  test_count: 243
  test_pass: 243
requirements-completed: [VERS-01, VERS-02, VERS-03, VERS-04, VERS-05, VERS-06]
---

# Phase 9 Plan 03: CLI Integration, Agent Updates, and KB 18.0 Sections Summary

CLI check-edition command wired to edition.py, spec.md edition check before approval, all 8 agents updated for 17.0/18.0 dual-version awareness, and "Changed in 18.0" sections added to 4 knowledge base files.

## Tasks Completed

| # | Task | Type | Commit | Key Files |
|---|------|------|--------|-----------|
| 1 | CLI check-edition command + render command version support | auto | a060e65 | cli.py |
| 2 | Agent updates + spec workflow + knowledge base 18.0 sections | auto | d8f9ba4 | 13 files (spec.md, 8 agents, 4 KB files) |

## What Was Built

### CLI check-edition Command (cli.py)
- New `check-edition` subcommand: reads spec JSON, checks `depends` against Enterprise registry
- Reports each EE dependency with module name, display name, category, and OCA alternative
- `--json` flag outputs machine-readable warning list
- Always exits 0 (informational, never blocks -- Decision B)
- Tested with EE deps (helpdesk), clean deps (base, mail), and JSON output

### Version-Aware render Command (cli.py)
- `--var odoo_version=18.0` now triggers `create_versioned_renderer("18.0")` instead of default renderer
- Without `odoo_version`, falls back to standard `create_renderer()` (backward compatible)

### Version-Aware list-templates Command (cli.py)
- New `--version` option to filter templates by Odoo version (e.g., `--version 18.0`)
- Shows directory labels: `[17.0]`, `[18.0]`, `[shared]` for each template
- Lists all version directories when no `--version` specified
- Fallback to flat directory listing for pre-reorganization layouts

### Spec Workflow Edition Check (spec.md)
- New Step 3.5 between spec build (Phase 3) and approval gate (Phase 4)
- Runs `odoo-gen-utils check-edition` on the built spec
- Presents 3 user options: (a) substitute with OCA alternatives, (b) keep as-is, (c) remove
- Informational only -- never blocks generation

### Agent Version Awareness (8 agents)
- **odoo-scaffold.md**: Version-specific rules split into 17.0/18.0 sections, reads odoo_version from spec/config
- **odoo-model-gen.md**: Version-conditional deprecated API section (states, aggregator, _search_display_name)
- **odoo-view-gen.md**: Version-conditional view syntax (tree vs list, view_mode, chatter)
- **odoo-test-gen.md**: 18.0 test pattern differences (no states= testing, aggregator, _search_display_name)
- **odoo-security-gen.md**: "17.0/18.0" in description, version-independent security note
- **odoo-validator.md**: "17.0/18.0" in description, 18.0 Docker validation deferred note
- **odoo-search.md**: Git branch uses `{odoo_version}` instead of hardcoded "17.0"
- **odoo-extend.md**: Git branch uses `{odoo_version}`, version-specific extension patterns

### Knowledge Base "Changed in 18.0" Sections (4 files)
- **models.md**: states= removal, group_operator->aggregator, _name_search->_search_display_name, name_get deprecation, check_access consolidation, numbercall removal (with WRONG/CORRECT/Why examples)
- **views.md**: tree->list (hard error), view_mode tree->list, chatter shorthand preferred, ir.ui.view type removal (with WRONG/CORRECT/Why examples)
- **manifest.md**: Version prefix 18.0.X.Y.Z, no structural changes (with WRONG/CORRECT/Why example)
- **MASTER.md**: 17.0/18.0 support announcement, key breaking changes summary, template directory reference, Enterprise awareness note

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

```
cd python && uv run pytest tests/ -x -q
# Result: 243 passed, 5 warnings in 1.41s

cd python && uv run odoo-gen-utils check-edition --help
# Result: Command registered with correct description and options

grep -l "18.0" agents/*.md | wc -l
# Result: 8 (all agents)

grep -l "Changed in 18.0" knowledge/models.md knowledge/views.md knowledge/manifest.md | wc -l
# Result: 3 (all three KB files)
```

## Self-Check: PASSED

All claims verified:
- check-edition CLI command works and reports EE warnings
- spec.md has edition check step before approval gate
- All 8 agents updated for 17.0/18.0 version awareness
- KB files have "Changed in 18.0" sections
- Full test suite passes with no regressions (243/243)
