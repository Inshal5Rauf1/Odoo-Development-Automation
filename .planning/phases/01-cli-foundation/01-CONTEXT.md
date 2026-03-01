# Phase 1: CLI Foundation - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Project skeleton with Typer CLI, configuration system, state management, and Jinja2 module scaffolding. Developer can install and run `odoo-gen` with working CLI commands, configuration, and valid Odoo 17.0 module scaffolding. No AI generation in this phase — just the CLI shell and scaffold.

</domain>

<decisions>
## Implementation Decisions

### Command design
- Tool name: `odoo-gen`
- Starting a module: `odoo-gen new` starts an interactive conversation (no description argument required)
- v1 commands:
  - `odoo-gen new` — start new module creation (interactive 12-step workflow)
  - `odoo-gen resume` — resume a paused/interrupted generation
  - `odoo-gen status` — show current generation state and progress
  - `odoo-gen search <description>` — find similar modules on GitHub/OCA
  - `odoo-gen index` — rebuild/update the local OCA/GitHub vector index
  - `odoo-gen validate <path>` — run pylint-odoo + Docker install + tests
  - `odoo-gen config` — view/set default settings
  - `odoo-gen extend <module>` — shortcut to fork and add features to an existing module
  - `odoo-gen history` — list previously generated modules with timestamps
  - `odoo-gen help` — standard help (Typer auto-generates)
- Phase 1 implements: `new` (scaffold only, no AI), `validate` (stub), `config`, `status`, `help`
- Other commands are stubs/placeholders in Phase 1, implemented in later phases

### Config & defaults
- Config file location: `~/.odoo-gen/config.toml` (global, home directory)
- Format: TOML (Python ecosystem standard, supports comments)
- Configurable settings:
  - `odoo_version` — default target version (17.0 or 18.0)
  - `edition` — default edition (ce, ee, or both)
  - `output_dir` — where generated modules are saved
  - `api_keys` — section for Claude, Codex, Gemini API keys
- CLI flags override config file settings (e.g., `odoo-gen new --version 18.0` overrides config default)

### Scaffold output
- Scaffold produces a working installable example module (not just empty dirs)
- Example module includes: one model with 3-4 fields, form + list view, basic security (one group, one ACL), working `__manifest__.py`
- Always-created directories: `models/`, `views/`, `security/`, `tests/`
- Optional directories (`data/`, `wizards/`, `controllers/`, `static/`, `report/`) created only when the spec requires them
- Scaffold serves as proof the pipeline works — developer can install on Odoo immediately

### CLI feedback & UX
- Default verbosity: chatty — shows progress, agent activity, file creation in real-time
- `--quiet` flag for silent/minimal output (CI pipelines)
- Progress display: stage announcements (print each stage name as it starts/completes, no animation)
- Interactive conversation: inline terminal prompts — questions appear in terminal, user types answers or selects from numbered options
- No TUI (full-screen terminal UI) — keep it simple with inline prompts

### Claude's Discretion
- Color scheme and styling (Rich library choices)
- Exact TOML config key naming
- Help text wording and examples
- Error message formatting
- How the example scaffold model/fields are structured

</decisions>

<specifics>
## Specific Ideas

- Command naming follows Unix convention: lowercase, hyphenated (`odoo-gen` not `OdooGen`)
- Config follows Python ecosystem patterns (TOML like pyproject.toml, ruff.toml)
- Scaffold should feel immediately useful — not a skeleton you have to fill in manually
- The erp_claude repo (Baptiste-banani/erp_claude) provides Odoo-specific patterns that inform the scaffold templates

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-cli-foundation*
*Context gathered: 2026-03-01*
