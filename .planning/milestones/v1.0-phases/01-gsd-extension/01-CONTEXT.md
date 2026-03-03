# Phase 1: GSD Extension + Odoo Foundation - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up odoo-gen as a working GSD extension that registers commands, provides Odoo-specific agent definitions, and can scaffold a valid Odoo 17.0 module via `/odoo-gen:new`. Delivers: extension structure, command registration, Odoo config fields, agent stubs, and a Python utility package with Jinja2 template engine.

Requirements: EXT-01, EXT-02, EXT-03, EXT-04, EXT-05

</domain>

<decisions>
## Implementation Decisions

### Scaffold Output Structure
- Full OCA directory structure from the start: `models/`, `views/`, `security/`, `tests/`, `data/`, `i18n/`, `static/description/`, `wizard/` (if needed)
- Split model files: one Python file per model (e.g., `models/inventory_item.py`, `models/stock_move.py`) — OCA convention
- Jinja2 templates produce real working content, not stubs — module must install and run on Odoo 17.0 on first scaffold
- Include demo data (`demo/` with sample records) and `README.rst` (module description, usage, credits) from day one — OCA requires both

### Command Invocation Flow
- `/odoo-gen:new` accepts an inline argument: `/odoo-gen:new "inventory tracking with stock moves and warehouse locations"`
- System parses the description, infers module spec (name, models, fields), then shows the inferred spec for user confirmation before generating
- Phase-by-phase announcements during scaffolding: "Generating models... Generating views... Generating security... Done! Module at ./my_module/"
- Scaffolded module is created in the current working directory (`./module_name/`)
- Smart Odoo-specific follow-up questions come in Phase 4 (INPT-01..04) — Phase 1 keeps input simple

### Extension Install Experience
- Single install script (`install.sh`): clone repo → run script → done
- install.sh checks for GSD at `~/.claude/get-shit-done/` — if missing, error with clear message and install URL (does not proceed)
- install.sh requires `uv` (fast Python package manager) — if missing, error with install link
- install.sh creates a Python venv, installs the utility package via `uv pip install`
- Commands are registered by adding `/odoo-gen:*` skill entries to `~/.claude/settings.json` (same pattern GSD uses)

### Agent Role Boundaries
- GSD handles all orchestration (inherited) — odoo-gen does not build its own orchestrator
- Each agent is a GSD agent definition (`.md` file with system prompt + tool access)
- `odoo-scaffold` is the single entry-point agent for Phase 1 — it handles the full scaffold end-to-end
- Specialist agents (odoo-model-gen, odoo-view-gen, odoo-security-gen, odoo-test-gen, odoo-validator) are stubs in Phase 1, activated in Phases 5-6
- Naming convention: `odoo-` prefix for all agents (consistent with GSD naming)
- Agent files live in `~/.claude/odoo-gen/agents/` (not copied into GSD) — `settings.json` references them
- Agents call the Python utility package via Bash tool: `odoo-gen-utils render`, `odoo-gen-utils list-templates`, etc.
- Python CLI namespace: `odoo-gen-utils <subcommand>` — clear, no conflicts

### Claude's Discretion
- Exact Jinja2 template structure and variable naming
- Python package internal architecture (modules, classes)
- install.sh implementation details (color output, progress)
- Agent .md prompt engineering and tool access definitions
- GSD config field defaults and validation logic

</decisions>

<specifics>
## Specific Ideas

- Module must install and run on first scaffold — this is the core value proposition ("months of work into days")
- Follow the same install pattern as GSD itself — familiarity for users who already use GSD
- `settings.json` skill entries are the registration mechanism — same as GSD's own commands
- v1 focus: get the pipeline working end-to-end. Polish and decomposition come in later phases
- User's words: "this is v1. further iterations can be in v2"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-gsd-extension*
*Context gathered: 2026-03-01*
