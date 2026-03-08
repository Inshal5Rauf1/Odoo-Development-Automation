# Phase 53: Mermaid Graphs - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate `.mmd` Mermaid diagram files for module dependency DAGs and model ER diagrams, renderable in GitHub and VS Code. Two scopes: module-level (auto-generated after render) and project-level (explicit CLI command from registry). All logic lives in a new `mermaid.py` module -- zero changes to existing rendering pipeline beyond an auto-generation hook call.

</domain>

<decisions>
## Implementation Decisions

### Output File Placement & Naming
- Module-level diagrams go inside the generated module dir in a `docs/` subfolder:
  ```
  uni_fee/
  ├── __manifest__.py
  ├── models/
  ├── views/
  ├── security/
  └── docs/
      ├── dependencies.mmd     # module dependency DAG
      └── er_diagram.mmd       # model ER diagram
  ```
- Project-level diagrams go in `.planning/diagrams/`:
  ```
  .planning/
  ├── model_registry.json
  └── diagrams/
      ├── project_dependencies.mmd   # all modules DAG
      └── project_er.mmd            # all models ER
  ```
- Module-level diagrams are auto-generated after each successful render (post-semantic-validation hook)
- Project-level diagrams are generated via explicit `odoo-gen mermaid --project` command (reads registry)
- `.mmd` files are developer docs, NOT added to `__manifest__.py` data files -- not loaded by Odoo

### Diagram Content & Detail Level
- **Dependency DAG**: Direct deps only, NOT transitive
  - Transitive deps turn clean DAG into spaghetti -- direct deps show what the module actually imports/references
  - External Odoo modules (base, mail, hr) get a different style from project modules:
    ```mermaid
    graph TD
        uni_fee --> uni_core
        uni_fee --> uni_student
        uni_fee --> mail:::external
        classDef external fill:#f0f0f0,stroke:#999,stroke-dasharray: 5 5
    ```
- **ER Diagram**: Relational fields + key non-relational fields
  - ALL relational fields (Many2one, One2many, Many2many) -- always shown as relationships
  - Key non-relational fields: name, state, type/Selection fields, Monetary fields, computed fields with `store=True`
  - EXCLUDE: technical fields (create_uid, write_date, message_ids, activity_ids), Binary fields, Text/Html fields, non-stored computed fields
  - Show field type (Char, Monetary, Selection) next to field name
  - Do NOT show constraints or defaults -- too noisy
  - Cross-module references shown with dotted lines (model lives in different module); same-module references use solid lines:
    ```mermaid
    erDiagram
        fee_invoice }o..|| uni_student : student_id
    ```

### CLI Command Structure
- Single `mermaid` command at top level (NOT under `registry` subgroup -- mermaid is visualization, not data management)
- Flags:
  ```
  odoo-gen mermaid --module uni_fee --type deps
  odoo-gen mermaid --module uni_fee --type er
  odoo-gen mermaid --module uni_fee --type all    # both
  odoo-gen mermaid --project --type deps
  odoo-gen mermaid --project --type er
  odoo-gen mermaid --project --type all
  odoo-gen mermaid --module uni_fee --type er --stdout
  ```
- `--type` defaults to `all`
- `--stdout` prints to stdout instead of writing to file
- Auto-generation hook: after `render_module()` succeeds and semantic validation passes, auto-generate both `.mmd` files into the module's `docs/` folder. No extra CLI call needed for the common case.

### Identifier Sanitization
- Underscores replacing dots: `res.partner` → `res_partner`
- Sanitization function: `_mermaid_id(name)` replaces `.` and `-` with `_`
- For flowchart (dependency DAG): quoted labels with brackets for display, IDs use underscores
  ```mermaid
  graph TD
      uni_fee["uni_fee"]
      mail["mail"]
  ```
- For erDiagram: Mermaid uses ID as display name -- `uni_student` is readable enough, no separate display label needed
- Edge case collision (theoretically `uni.student` and `uni_student`): prefix with module name `uni_core__uni_student`. In practice this never happens.

### Claude's Discretion
- Internal helper function signatures and organization within `mermaid.py`
- Which fields qualify as "key non-relational" -- heuristic for filtering (name, state, Selection, Monetary, stored computed)
- How to detect external vs project modules (registry membership check)
- How the auto-generation hook integrates into CLI generate flow
- Test fixture design

</decisions>

<specifics>
## Specific Ideas

- User provided exact Mermaid syntax examples for both diagram types including `classDef external` styling for dependency DAG
- User specified dotted lines (`}o..||`) for cross-module ER references vs solid lines for same-module
- User specified external module marker icon pattern: `mail["mail"]` with `:::external` classDef
- User specified `_mermaid_id()` function signature with `.` and `-` → `_` replacement
- User specified exact file naming: `dependencies.mmd` and `er_diagram.mmd` (module-level), `project_dependencies.mmd` and `project_er.mmd` (project-level)
- User specified auto-generation happens AFTER semantic validation passes, not before

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `registry.py`: `ModelRegistry` with `_dependency_graph` (module → deps), `_models` (model_name → ModelEntry with fields dict), `list_modules()`, `show_model()` -- exact data source for both diagrams
- `registry.py`: `_known_models` dict loaded from `known_odoo_models.json` -- can distinguish external Odoo models from project models
- `cli.py`: Click CLI with `@main.command()` pattern -- mermaid command follows same pattern
- `validation/semantic.py`: Post-generation validation pattern -- similar hook point for auto-generation

### Established Patterns
- CLI lazy imports: commands import heavy modules inside function body (not at module level)
- Registry operations live in CLI layer, not inside render pipeline
- `render_module()` returns `(file_paths, warnings)` -- auto-generation hook can use the output_dir from this
- `@main.command()` with `@click.option()` for flags

### Integration Points
- `mermaid.py` -- new module (pure functions, no class needed)
- `cli.py` -- new `mermaid` command with `--module`, `--project`, `--type`, `--stdout` flags
- `cli.py` `render_module_cmd()` -- auto-generation hook call after successful render + validation
- `docs/` directory creation in generated module output

</code_context>

<deferred>
## Deferred Ideas

- Cross-module Mermaid with full registry (ARCH-09 in v3.4+) -- needs registry battle-tested first
- Interactive Mermaid viewer (HTML page with pan/zoom) -- nice-to-have, not in scope
- Mermaid-to-PNG rendering in CI -- external tool concern, not our job
- Class diagram (methods, constraints) -- too detailed for auto-generated overview

</deferred>

---

*Phase: 53-mermaid-graphs*
*Context gathered: 2026-03-08*
