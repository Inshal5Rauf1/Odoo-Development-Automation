---
phase: 05-core-code-generation
plan: "01"
subsystem: jinja2-rendering-engine
tags: [renderer, templates, computed-fields, wizards, sequences, form-views]
dependency_graph:
  requires: []
  provides:
    - "_build_model_context() with 9 new context keys for Phase 5 template features"
    - "wizard.py.j2 — TransientModel wizard Python file rendering"
    - "wizard_form.xml.j2 — Wizard dialog form XML rendering"
    - "sequences.xml.j2 — ir.sequence XML records with noupdate=1"
    - "init_wizards.py.j2 — __init__.py for wizards/ subdirectory"
    - "render_module() generating wizard and sequence files with canonical manifest ordering"
  affects:
    - "model.py.j2 — now emits sequence/computed/onchange/constrains method stubs"
    - "view_form.xml.j2 — now emits <header> + statusbar + wizard buttons"
    - "init_root.py.j2 — conditionally imports wizards subpackage"
    - "manifest.py.j2 — uses canonical manifest_files ordering"
tech_stack:
  added: []
  patterns:
    - "Jinja2 template extension with StrictUndefined (use `is defined` checks for optional dict keys)"
    - "Canonical manifest data ordering: security -> sequences -> data -> views -> wizard views"
    - "TDD: write tests first (RED), then implement (GREEN)"
key_files:
  created:
    - python/src/odoo_gen_utils/templates/wizard.py.j2
    - python/src/odoo_gen_utils/templates/wizard_form.xml.j2
    - python/src/odoo_gen_utils/templates/sequences.xml.j2
    - python/src/odoo_gen_utils/templates/init_wizards.py.j2
    - python/tests/test_renderer.py
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/templates/model.py.j2
    - python/src/odoo_gen_utils/templates/view_form.xml.j2
    - python/src/odoo_gen_utils/templates/init_root.py.j2
    - python/src/odoo_gen_utils/templates/manifest.py.j2
decisions:
  - "Used `field.compute is defined and field.compute` check in Jinja2 to handle optional dict keys with StrictUndefined mode"
  - "Jinja2 `{% set is_state = state_field and field.name == state_field.name %}` pattern to avoid ternary syntax errors in if blocks"
  - "sequences.xml.j2 uses sequence_models list (model + sequence_fields pairs) rather than per-model rendering"
  - "manifest.py.j2 now uses manifest_files list for canonical ordering instead of view_files only"
metrics:
  duration: "7 minutes"
  completed: "2026-03-02"
  tasks_completed: 2
  files_created: 5
  files_modified: 5
  tests_added: 34
  tests_total: 122
---

# Phase 5 Plan 01: Jinja2 Rendering Engine Extension Summary

**One-liner:** Extended Jinja2 renderer with computed/sequence/wizard/state-field support, producing @api.depends stubs, ir.sequence records, TransientModel dialogs, and statusbar headers deterministically from spec.

## What Was Built

### Task 1: Extend _build_model_context() and render_module()

Extended `renderer.py` with 9 new context keys in `_build_model_context()`:
- `computed_fields` — fields with `compute` key
- `onchange_fields` — fields with `onchange` key
- `constrained_fields` — fields with `constrains` key
- `sequence_fields` — Char fields matching sequence names (reference/ref/number/code/sequence) with required=True
- `sequence_field_names` — list version of SEQUENCE_FIELD_NAMES for template use
- `state_field` — the state/status Selection field or None
- `wizards` — wizard specs from spec root
- `has_computed` — bool
- `has_sequence_fields` — bool

`render_module()` extended to:
- Always generate `data/data.xml` stub
- Generate `data/sequences.xml` when sequence fields detected
- Generate `wizards/__init__.py`, `wizards/<wizard_var>.py`, `views/<wizard_xml_id>_wizard_form.xml`
- Use canonical manifest ordering via `_compute_manifest_data()`

Created 4 new templates: `wizard.py.j2`, `wizard_form.xml.j2`, `sequences.xml.j2`, `init_wizards.py.j2`

### Task 2: Extend model.py.j2, view_form.xml.j2, init_root.py.j2, manifest.py.j2

Extended `model.py.j2`:
- Sequence Char field rendered with `readonly=True, copy=False, default=_default_<field>`
- Computed field rendered with `compute=`, `store=`
- `@api.model def _default_<field>()` method stub per sequence field
- `@api.depends(...)` stub method per computed field (with # TODO body)
- `@api.onchange(...)` stub method per onchange field
- `@api.constrains(...)` stub method per constrained field
- `ValidationError` import added when constrained_fields exist

Extended `view_form.xml.j2`:
- `<header>` block rendered when state/status Selection field detected
- Statusbar widget with `statusbar_visible` from selection options
- Wizard trigger buttons in `<header>` with `invisible` expression
- Sequence fields render as `readonly="state != 'draft'"` in view

Updated `init_root.py.j2` to conditionally import `wizards` subpackage.
Updated `manifest.py.j2` to use `manifest_files` list with canonical ordering.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Test RED | 853269a | test(05-01): add failing tests for _build_model_context new keys |
| Task 1 | 1c9a65c | feat(05-01): extend renderer.py and create wizard/sequence templates |
| Task 2 | 9363c61 | feat(05-01): extend model.py.j2 and view_form.xml.j2 with Phase 5 template features |

## Verification Results

```
python -m pytest python/tests/ -x -q
122 passed, 5 warnings in 0.48s
```

Sample render output (test_phase5 with compute + sequence + wizard + state):
```
test_phase5/__init__.py          (from . import models; from . import wizards)
test_phase5/__manifest__.py      (canonical data ordering: security -> seq -> data -> views -> wizard views)
test_phase5/data/data.xml        (stub)
test_phase5/data/sequences.xml   (<odoo noupdate="1"> ir.sequence record)
test_phase5/models/test_order.py (@api.depends stub, sequence field declaration, @api.model _default_reference)
test_phase5/views/test_order_views.xml  (<header> with statusbar + wizard button)
test_phase5/wizards/__init__.py
test_phase5/wizards/test_wizard.py  (TransientModel, default_get, button_confirm)
test_phase5/views/test_wizard_wizard_form.xml  (<footer> with buttons, target="new" action)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Jinja2 StrictUndefined fails on missing dict keys**
- **Found during:** Task 2 template implementation
- **Issue:** `{% elif field.compute %}` raised `UndefinedError` because StrictUndefined doesn't allow accessing missing dict attributes; spec fields without `compute` key caused failures
- **Fix:** Changed to `{% elif field.compute is defined and field.compute %}` pattern for all optional field attributes
- **Files modified:** `python/src/odoo_gen_utils/templates/model.py.j2`
- **Commit:** 9363c61 (included in task commit)

**2. [Rule 1 - Bug] Jinja2 ternary syntax in if block caused TemplateSyntaxError**
- **Found during:** Task 2 view_form.xml.j2 implementation
- **Issue:** `{% if field.name != 'name' and field.name != state_field.name if state_field else field.name != 'name' %}` raised `TemplateSyntaxError` — Python ternary is not valid Jinja2 if-block syntax
- **Fix:** Extracted to `{% set is_state = state_field and field.name == state_field.name %}` first, then used `{% if not is_state and ... %}`
- **Files modified:** `python/src/odoo_gen_utils/templates/view_form.xml.j2`
- **Commit:** 9363c61 (included in task commit)

## Success Criteria Verification

- [x] pytest passes all existing + new renderer tests (0 failures — 122 total)
- [x] render_module() with compute fields produces @api.depends stubs with # TODO bodies
- [x] render_module() with required Char field named "reference" produces data/sequences.xml with noupdate="1"
- [x] render_module() with wizards array produces wizards/__init__.py, wizards/*.py, views/*_wizard_form.xml
- [x] Form views for models with state Selection field contain <header><field widget="statusbar"> block
- [x] Manifest data section follows canonical load order (security first, wizard views last)
- [x] No states= parameter appears in any generated code (uses readonly=True on field + readonly="state != 'draft'" in view)

## Self-Check: PASSED
