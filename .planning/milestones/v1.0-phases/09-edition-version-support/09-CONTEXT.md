# Phase 9: Edition & Version Support — Context

**Created:** 2026-03-03
**Phase goal:** System is aware of Odoo edition differences and can generate modules targeting both 17.0 and 18.0 with correct version-specific patterns
**Requirements:** VERS-01, VERS-02, VERS-03, VERS-04, VERS-05, VERS-06

## Locked Decisions

### Decision A: Template Architecture — Separate Directories
Use version-specific template directories with Jinja2 FileSystemLoader fallback chain:

```
templates/
  17.0/         # Version-specific (templates that differ between versions)
    view_form.xml.j2    # Uses <tree> tag
    view_tree.xml.j2    # Uses <tree> tag
    action.xml.j2       # view_mode="tree,form"
    model.py.j2         # Supports states=, group_operator=
  18.0/         # Version-specific for 18.0
    view_form.xml.j2    # Uses <list> tag, <chatter/> shorthand
    view_tree.xml.j2    # Uses <list> tag (not <tree>)
    action.xml.j2       # view_mode="list,form"
    model.py.j2         # No states=, aggregator= not group_operator=
  shared/       # Identical across versions (moved from current flat dir)
    access_csv.j2
    init_models.py.j2
    init_root.py.j2
    init_tests.py.j2
    init_wizards.py.j2
    menu.xml.j2
    readme.rst.j2
    security_group.xml.j2
    record_rules.xml.j2
    sequences.xml.j2
    demo_data.xml.j2
    wizard.py.j2
    wizard_form.xml.j2
    test_model.py.j2
    view_search.xml.j2
    manifest.py.j2      # Already uses {{ odoo_version }} variable
```

**Implementation:**
- `create_renderer()` → `create_versioned_renderer(version)` with FileSystemLoader([version_dir, shared_dir])
- `get_template_dir()` stays as entry point but internally resolves version
- `render_module()` reads `spec.get("odoo_version", "17.0")` and passes to renderer

**Rationale:** Explicit, debuggable, no inline conditionals. Each version's output is deterministic. Anti-pattern: never use `{% if odoo_version == '18.0' %}` inside templates.

### Decision B: Enterprise Check — Warning with Alternatives
When spec depends on Enterprise-only modules and edition is Community:
1. Show warning listing detected EE dependencies
2. For each, show OCA alternative (if available) with coverage notes
3. Let user decide: substitute with alternatives OR confirm EE dependency (they have Enterprise)
4. **Do NOT block generation** — user might actually have Enterprise license

**Integration points:**
- Check runs in spec.md workflow AFTER spec is built, BEFORE approval gate
- Also available as standalone `odoo-gen-utils check-edition` CLI command
- Enterprise registry is `data/enterprise_modules.json` (JSON data file, not Python code)

### Decision C: Full Agent Update
All 8 agents updated for version awareness:
1. Replace hardcoded "17.0" with `{{ odoo_version }}` or conditional sections
2. Deprecated API lists become version-conditional (17.0 list vs 18.0 list)
3. Git branch references use `odoo_version` (e.g., `-b {{ odoo_version }}`)
4. Agent descriptions include version range ("Odoo 17.0/18.0")

**Agents to update:**
- odoo-scaffold.md — version in specifics section
- odoo-model-gen.md — deprecated API list per version
- odoo-view-gen.md — tree vs list, chatter syntax
- odoo-test-gen.md — deprecated API list per version
- odoo-security-gen.md — minimal changes
- odoo-validator.md — Docker image per version (placeholder for now)
- odoo-search.md — git branch per version
- odoo-extend.md — git branch per version, manifest version

### Decision D: Docker 18.0 Deferred
- Phase 9 does NOT add Docker 18.0 validation
- Template correctness + pylint-odoo covers the immediate need
- odoo-validator.md gets a note: "18.0 Docker validation planned for future"
- Document as known limitation in CLAUDE.md

## Code Context

### Existing Files to Modify
- `python/src/odoo_gen_utils/renderer.py` — version-aware template resolution
- `python/src/odoo_gen_utils/cli.py` — `check-edition` CLI command
- `workflows/spec.md` — Enterprise check after spec build
- `defaults.json` — already has `odoo_version` and `edition`
- All 8 `agents/*.md` files — version-conditional content

### New Files to Create
- `python/src/odoo_gen_utils/data/enterprise_modules.json` — Enterprise module registry
- `python/src/odoo_gen_utils/edition.py` — Enterprise check functions
- `python/src/odoo_gen_utils/templates/17.0/` — moved templates (4-6 that differ)
- `python/src/odoo_gen_utils/templates/18.0/` — 18.0 variants (4-6 files)
- `python/src/odoo_gen_utils/templates/shared/` — moved templates (14-16 identical)
- `python/tests/test_edition.py` — Enterprise registry and check tests
- Knowledge base `Changed in 18.0` sections in models.md, views.md, manifest.md

### Integration Points
- `renderer.py:create_renderer()` → needs version param for FileSystemLoader
- `renderer.py:render_module()` → reads odoo_version from spec, passes to renderer
- `spec.md` Step 3 → calls check_enterprise_dependencies() after building spec
- `cli.py` → new `check-edition` command
- `defaults.json` → `odoo_version` field already exists, wiring needed

## Deferred Ideas
- Docker 18.0 validation (future enhancement)
- Odoo 19.0 support (when released)
- Automatic OCA module version verification (check if alternative has matching Odoo version branch)
- Enterprise module detection from module description (NLP-based, not just depends list)

## Open Questions (Resolved)
All gray areas resolved. No open questions remain.
