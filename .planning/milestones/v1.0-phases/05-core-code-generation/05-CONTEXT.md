---
phase: 05-core-code-generation
created: 2026-03-02T15:21:02.041Z
status: context-captured
---

# Phase 5 Context: Core Code Generation

## Goal

System generates complete, real Odoo 17.0 module code (not stubs) from an approved
specification, following OCA standards.

## Requirements in Scope

CODG-01, CODG-02, CODG-03, CODG-04, CODG-05, CODG-06, CODG-07, CODG-08, CODG-09, CODG-10

## Codebase State at Phase 5 Start

### Already Working (Phases 1–4)

| Capability | File | Notes |
|---|---|---|
| `__manifest__.py` | `manifest.py.j2` | Correct 17.0 version format, data refs |
| `__init__.py` files | `init_root.py.j2`, `init_models.py.j2`, `init_tests.py.j2` | Root, models/, tests/ |
| Basic model fields | `model.py.j2` | All scalar + relational types, sql_constraints |
| Form + tree + search | `view_form.xml.j2` | Combined per-model, correct `<tree>` tag |
| Actions + menus | `action.xml.j2`, `menu.xml.j2` | Window actions, menu hierarchy |
| Security groups + ACLs | `security_group.xml.j2`, `access_csv.j2` | User/Manager roles |
| Basic tests | `test_model.py.j2` | TransactionCase, CRUD, name_get |
| README.rst | `readme.rst.j2` | OCA format, installation/config/usage |
| render-module CLI | `renderer.py` + `cli.py` | Takes spec.json → full OCA module |
| odoo-validator agent | `agents/odoo-validator.md` | Fully activated |

### Missing (Phase 5 Must Build)

| Gap | CODG req | Approach decided |
|---|---|---|
| Computed fields (`@api.depends`) | CODG-02 | Hybrid: Jinja2 declaration + agent writes method bodies |
| Onchange handlers | CODG-02 | Agent writes method bodies |
| `@api.constrains` decorators | CODG-02 | Agent writes method bodies |
| CRUD overrides (`create`, `write`) | CODG-02 | **Deferred to Phase 7** |
| `<header>` + statusbar widget | CODG-03 | Add to form template when state/status field exists |
| Wizard files (TransientModel) | CODG-07 | New `wizard.py.j2` + `wizard_form.xml.j2` templates |
| Data files (sequences) | CODG-06 | Auto-detect reference fields; new `sequences.xml.j2` |
| `generate.md` workflow | — | New workflow orchestrating specialist agents |
| odoo-model-gen activation | — | Write method bodies: computed, onchange, constrains |
| odoo-view-gen activation | — | Reads generated model files, enriches views |

### Stub Agents to Activate This Phase

- `agents/odoo-model-gen.md` — currently stub, KB @includes already wired
- `agents/odoo-view-gen.md` — currently stub, KB @includes already wired
- `agents/odoo-test-gen.md` — activate for computed field tests (CODG-02 coverage)

Note: `odoo-security-gen` stays stub — security generation is Phase 6.

## Decisions

### A — Complex Model Logic: Hybrid Two-Pass

**Decision:** Spec carries field-level compute/depends hints inline. Jinja2 renders field
declarations. `odoo-model-gen` agent AI-writes all method bodies.

**Spec schema extension** (inline in field objects):
```json
{
  "name": "total_amount",
  "type": "Float",
  "compute": "_compute_total",
  "depends": ["quantity", "unit_price"],
  "store": true
}
```

**Jinja2 renders the declaration:**
```python
total_amount = fields.Float(
    string="Total Amount",
    compute="_compute_total",
    store=True,
)
```

**odoo-model-gen writes the method body using KB context:**
```python
@api.depends('quantity', 'unit_price')
def _compute_total(self):
    for rec in self:
        rec.total_amount = rec.quantity * rec.unit_price
```

**Also applies to:**
- `@api.onchange` — field has `"onchange": true` hint in spec
- `@api.constrains` — field has `"constrains": ["field_a", "field_b"]` hint in spec

**Explicitly deferred to Phase 7:**
- CRUD overrides (`create`, `write`, `unlink`) — too context-dependent

### B — Agent Pipeline: New `generate.md` Workflow

**Decision:** spec.md ends with approval → triggers `generate.md` workflow.
`generate.md` orchestrates specialist agents in two waves.

**`/odoo-gen:plan` flow (spec mode):**
```
spec.md: NL parse → tiered questions → spec.json → approval
    ↓
generate.md:
  Wave 1 (parallel): odoo-model-gen + data-gen
      ↓
  Wave 2 (parallel): odoo-view-gen + odoo-test-gen
      ↓
  Commit + summary
```

**`/odoo-gen:new` flow (quick mode — unchanged):**
```
odoo-scaffold → render-module CLI → quick output
```

**Wave rationale:**
- Wave 1 first: model Python files must exist before view-gen reads them
- Wave 2 reads Wave 1 output: view-gen references actual computed field names from generated `.py` files
- test-gen reads model structure to generate meaningful tests

**New file to create:** `workflows/generate.md`
**No changes to:** `workflows/scaffold.md`, `workflows/spec.md` (spec.md gets one line added: call generate.md on approval)

### C — Wizard Generation: Explicit Spec Key + Templates

**Decision:** Wizards declared explicitly in spec.json. New templates render them.

**Spec schema:**
```json
"wizards": [{
  "name": "confirm.wizard",
  "target_model": "sale.order",
  "trigger_state": "confirmed",
  "fields": [
    {"name": "date_confirm", "type": "Date", "string": "Confirmation Date"},
    {"name": "notes", "type": "Text", "string": "Notes"}
  ]
}]
```

**Files generated:**
- `wizards/confirm_wizard.py` — TransientModel with `button_confirm()` action
- `views/confirm_wizard_form.xml` — dialog form view
- Button added to target model's form `<header>`:
  ```xml
  <button name="action_open_confirm_wizard"
          string="Confirm"
          type="object"
          invisible="state != 'draft'"/>
  ```
- `__manifest__.py` `data` section includes wizard view files

**New templates needed:** `wizard.py.j2`, `wizard_form.xml.j2`

**When wizard section is empty/absent:** no wizard files generated (zero wizards is valid)

### D — Data Files: Auto-Sequence on Reference Field

**Decision:** Auto-detect reference fields; generate `ir.sequence` and `_default_<field>()` method.

**Trigger:** Model has a `Char` field with name matching: `reference`, `ref`, `number`,
`sequence`, or `code` (where `required: true`)

**Generated files:**
- `data/sequences.xml` — `ir.sequence` record per detected sequence field
- Always emit a `data/data.xml` with a stub comment block
- Manifest `"data"` section includes both sequence + data files (before view files)

**Model gets:**
```python
@api.model
def _default_reference(self):
    return self.env['ir.sequence'].next_by_code('my.model') or '/'

reference = fields.Char(
    string="Reference",
    required=True,
    default=_default_reference,
    readonly=True,
    copy=False,
)
# NOTE: states= parameter is REMOVED in Odoo 17.0.
# To make field editable in draft, use view-level: readonly="state != 'draft'"
```

**Deferred to Phase 7:** `ir.cron`, `mail.template` data records

### E — README Format: Keep README.rst

**Decision:** README.rst is the OCA standard. Existing `readme.rst.j2` template is correct.
CODG-10 requirement has a documentation error (says `.md`, should be `.rst`).

**Action:** Planner to note the CODG-10 wording fix in planning. No code change needed.

**Rationale:** GitHub renders `.rst` fine. OCA submission requires `.rst`. Not worth two templates.

### F — Kanban Views: Deferred to Phase 7

**Decision:** Kanban views are a quality/UX enhancement, not required by CODG-03.
Form + tree + search satisfies the requirement. Kanban deferred.

### Bonus: State/Statusbar in Form Views

**Decision:** If a model has a `state` or `status` Selection field, the form view template
must render a `<header>` element:

```xml
<header>
  <!-- State action buttons generated here -->
  <field name="state" widget="statusbar"
         statusbar_visible="draft,confirmed,done"/>
</header>
```

This requires updating `view_form.xml.j2` to detect state fields and emit the `<header>` block.

### Bonus: CODG-09 Documentation Error

**Decision:** CODG-09 says `<list>` not `<tree>` — this is wrong for Odoo 17.0.
Our templates already use `<tree>` correctly.
Planner to add a requirement wording fix task (update REQUIREMENTS.md).

## Code Context

### render_module() function (renderer.py)

The main rendering entry point. Currently produces 15+ files from spec.json.
Phase 5 extends it to:
- Support `compute`, `depends`, `onchange`, `constrains` keys in field specs
- Detect sequence fields and generate `data/sequences.xml`
- Detect wizards and generate `wizards/*.py` + `views/*_wizard_form.xml`
- Detect state fields and render `<header>` in form views

### _build_model_context() (renderer.py)

Builds the per-model template context dict. Needs new keys:
- `computed_fields` — filtered list of fields with `compute` key
- `onchange_fields` — filtered list of fields with `onchange: true`
- `constrained_fields` — filtered list of fields with `constrains` list
- `sequence_fields` — filtered list of Char fields matching sequence name patterns
- `state_field` — the state/status Selection field if present (for statusbar)
- `wizards` — wizard specs from spec root (needed in model for button action method)

### model.py.j2 template

Needs to render:
- Computed field declarations with `compute=`, `depends` references (already has field slots)
- `readonly=True, states={"draft": [...]}` for sequence fields
- `default=_default_reference` for sequence fields
- Method signature stubs with correct `@api.depends`, `@api.onchange`, `@api.constrains`
  decorators (method bodies written by odoo-model-gen agent)

### view_form.xml.j2 template

Needs to add:
- `<header>` block with statusbar when state field detected
- State action button placeholders (e.g., `<!-- Action buttons generated by model-gen -->`)

## Integration Points

- **Phase 4 output** → `spec.json` is the Phase 5 input contract
- **Phase 2 knowledge base** → odoo-model-gen loads `models.md`, `views.md`, `inheritance.md`
- **Phase 3 validation** → `odoo-gen-utils validate` can verify Phase 5 output immediately
- **Phase 6 (next)** → Security gen + test gen get fully activated (Phase 5 only activates model-gen, view-gen)
- **Phase 7 (after)** → CRUD overrides, kanban views, i18n, cron, email templates

## Non-Decisions (Planner Decides)

- Whether `render-module` CLI gets extended OR only the agent pipeline uses the new features
- How odoo-model-gen "appends" computed method bodies to rendered files (rewrite vs append vs Write tool)
- Exact file ordering in `generate.md` commit strategy
- Test generation scope for computed fields (CODG-02 says tests must cover computed fields)
- Whether odoo-test-gen needs activation in Phase 5 or Phase 6

## Deferred Ideas (Not Phase 5)

- Kanban views (Phase 7)
- CRUD overrides (Phase 7)
- `ir.cron` and `mail.template` data records (Phase 7)
- `odoo-security-gen` activation (Phase 6)
- i18n `.pot` file (Phase 7 — QUAL-06)
