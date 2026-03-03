---
phase: 01-gsd-extension
plan: 03
subsystem: infra
tags: [python, jinja2, click, odoo-17, templates, cli, scaffolding]

# Dependency graph
requires:
  - phase: none
    provides: greenfield
provides:
  - Python utility package (odoo-gen-utils) with CLI entry point
  - Jinja2 rendering engine with Odoo-specific filters (model_ref, to_class, to_python_var, to_xml_id)
  - 15 Jinja2 templates covering full Odoo 17.0 module structure
  - render-module function that produces complete OCA directory from spec dict
affects: [01-04, 02-knowledge-base, 03-validation, 05-code-generation]

# Tech tracking
tech-stack:
  added: [jinja2, click, hatchling, python-3.12]
  patterns: [FileSystemLoader, StrictUndefined, custom-jinja2-filters, spec-dict-driven-rendering]

key-files:
  created:
    - python/pyproject.toml
    - python/src/odoo_gen_utils/__init__.py
    - python/src/odoo_gen_utils/cli.py
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/templates/manifest.py.j2
    - python/src/odoo_gen_utils/templates/model.py.j2
    - python/src/odoo_gen_utils/templates/init_root.py.j2
    - python/src/odoo_gen_utils/templates/init_models.py.j2
    - python/src/odoo_gen_utils/templates/init_tests.py.j2
    - python/src/odoo_gen_utils/templates/view_form.xml.j2
    - python/src/odoo_gen_utils/templates/view_tree.xml.j2
    - python/src/odoo_gen_utils/templates/view_search.xml.j2
    - python/src/odoo_gen_utils/templates/action.xml.j2
    - python/src/odoo_gen_utils/templates/menu.xml.j2
    - python/src/odoo_gen_utils/templates/security_group.xml.j2
    - python/src/odoo_gen_utils/templates/access_csv.j2
    - python/src/odoo_gen_utils/templates/test_model.py.j2
    - python/src/odoo_gen_utils/templates/demo_data.xml.j2
    - python/src/odoo_gen_utils/templates/readme.rst.j2
  modified: []

key-decisions:
  - "Combined form+tree+search views into single view_form.xml.j2 per model (render_module outputs one combined view file per model)"
  - "Single menu.xml for all models rather than per-model menu files (cleaner OCA structure)"
  - "view_tree.xml.j2 and view_search.xml.j2 kept as standalone templates for single-template rendering via CLI"
  - "Demo data generates 3 records per model with incrementing sample values"
  - "Used hatchling build backend (modern, fast, pyproject.toml native)"

patterns-established:
  - "Spec dict pattern: all templates consume from a shared module spec dictionary structure"
  - "Filter-based name conversion: model_ref, to_class, to_python_var, to_xml_id filters centralize all Odoo naming conventions"
  - "StrictUndefined: missing template variables fail loudly, not silently"
  - "OCA directory structure: models/, views/, security/, tests/, demo/, static/description/, README.rst"
  - "Odoo 17.0 syntax only: <tree> (not <list>), inline invisible/readonly (not attrs), <odoo> (not <openerp>)"

requirements-completed: [EXT-05]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 1 Plan 3: Python Utility Package Summary

**Click CLI (render, list-templates, render-module) with Jinja2 engine and 15 Odoo 17.0 templates producing real installable module content**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T18:11:52Z
- **Completed:** 2026-03-01T18:15:39Z
- **Tasks:** 2
- **Files modified:** 19

## Accomplishments
- Python package with pyproject.toml, Click CLI entry point, and Jinja2 rendering engine with 4 custom Odoo filters
- 15 Jinja2 templates producing real, installable Odoo 17.0 module content (not stubs) following OCA conventions
- render_module function that takes a spec dict and outputs a complete module directory structure (manifest, models, views, security, tests, demo, README)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Python package structure, CLI entry point, and Jinja2 renderer** - `d6684c1` (feat)
2. **Task 2: Create all Jinja2 templates for Odoo 17.0 module scaffolding** - `849dba0` (feat)

## Files Created/Modified
- `python/pyproject.toml` - Package metadata with hatchling build, Jinja2/Click deps, odoo-gen-utils entry point
- `python/src/odoo_gen_utils/__init__.py` - Package init with version export
- `python/src/odoo_gen_utils/cli.py` - Click CLI with render, list-templates, render-module commands
- `python/src/odoo_gen_utils/renderer.py` - Jinja2 engine with StrictUndefined and Odoo filters (model_ref, to_class, to_python_var, to_xml_id)
- `python/src/odoo_gen_utils/templates/manifest.py.j2` - __manifest__.py with 17.0 version format and license key
- `python/src/odoo_gen_utils/templates/model.py.j2` - Model file with fields, constraints, relational field support
- `python/src/odoo_gen_utils/templates/init_root.py.j2` - Root __init__.py
- `python/src/odoo_gen_utils/templates/init_models.py.j2` - models/__init__.py with per-model imports
- `python/src/odoo_gen_utils/templates/init_tests.py.j2` - tests/__init__.py with per-test imports
- `python/src/odoo_gen_utils/templates/view_form.xml.j2` - Combined form+tree+search view using <tree> tag
- `python/src/odoo_gen_utils/templates/view_tree.xml.j2` - Standalone tree view
- `python/src/odoo_gen_utils/templates/view_search.xml.j2` - Standalone search view
- `python/src/odoo_gen_utils/templates/action.xml.j2` - Window action with empty state help
- `python/src/odoo_gen_utils/templates/menu.xml.j2` - Root menu with web_icon and model submenus
- `python/src/odoo_gen_utils/templates/security_group.xml.j2` - Category, User/Manager groups with implied_ids
- `python/src/odoo_gen_utils/templates/access_csv.j2` - ir.model.access.csv using model_ref filter
- `python/src/odoo_gen_utils/templates/test_model.py.j2` - TransactionCase tests with create/read/name_get
- `python/src/odoo_gen_utils/templates/demo_data.xml.j2` - Self-contained demo records (3 per model)
- `python/src/odoo_gen_utils/templates/readme.rst.j2` - OCA-format README with all standard sections

## Decisions Made
- Combined form+tree+search views into a single per-model view file in render_module (view_tree and view_search kept as standalone templates for individual rendering via CLI)
- Single menu.xml file for all models rather than per-model menu files
- Demo data generates 3 self-contained records per model (no external refs beyond depends modules)
- Used hatchling as build backend for modern pyproject.toml-native packaging

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Python utility package ready for installation via `uv pip install -e python/`
- Templates ready for end-to-end integration testing in Plan 01-04
- CLI commands (render, list-templates, render-module) ready for agent invocation via Bash tool

## Self-Check: PASSED

All 19 created files verified present on disk. Both task commits (d6684c1, 849dba0) verified in git log.

---
*Phase: 01-gsd-extension*
*Completed: 2026-03-01*
