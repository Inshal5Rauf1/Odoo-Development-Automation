# Phase 5: Core Code Generation - Research

**Researched:** 2026-03-02
**Domain:** Jinja2 + AI hybrid code generation for Odoo 17.0 modules
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**A — Complex Model Logic: Hybrid Two-Pass**
Spec carries field-level compute/depends hints inline. Jinja2 renders field declarations.
`odoo-model-gen` agent AI-writes all method bodies. Spec schema extension:
```json
{
  "name": "total_amount",
  "type": "Float",
  "compute": "_compute_total",
  "depends": ["quantity", "unit_price"],
  "store": true
}
```
Jinja2 renders the declaration; odoo-model-gen writes the method body. Also applies to
`@api.onchange` (field has `"onchange": true`) and `@api.constrains` (field has
`"constrains": ["field_a", "field_b"]`). CRUD overrides explicitly deferred to Phase 7.

**B — Agent Pipeline: New `generate.md` Workflow**
spec.md ends with approval → triggers `generate.md`. Wave 1 (parallel): odoo-model-gen +
data-gen. Wave 2 (parallel): odoo-view-gen + odoo-test-gen. No changes to `scaffold.md`
or `spec.md` except one line added to spec.md calling generate.md on approval.

**C — Wizard Generation: Explicit Spec Key + Templates**
Wizards declared explicitly in spec.json `"wizards"` array. New `wizard.py.j2` and
`wizard_form.xml.j2` templates. Button added to target model form `<header>`. Manifest
`data` includes wizard view files. Zero wizards is valid.

**D — Data Files: Auto-Sequence on Reference Field**
Trigger: Model has Char field named `reference`, `ref`, `number`, `sequence`, or `code`
with `required: true`. Generated: `data/sequences.xml` (ir.sequence per field),
`data/data.xml` (stub). Model gets `_default_reference()` method. Manifest `data` section
includes sequence + data files before view files. `ir.cron` and `mail.template` deferred
to Phase 7.

**E — README Format: Keep README.rst**
Existing `readme.rst.j2` is correct. CODG-10 wording fix needed in REQUIREMENTS.md.
No code change required.

**F — Kanban Views: Deferred to Phase 7**
Form + tree + search satisfies CODG-03. No kanban in Phase 5.

**Bonus: State/Statusbar in Form Views**
If model has `state` or `status` Selection field, `view_form.xml.j2` renders `<header>`
with `<field name="state" widget="statusbar" statusbar_visible="..."/>`.

**Bonus: CODG-09 Documentation Error**
Our templates already use `<tree>` correctly. Planner adds a REQUIREMENTS.md wording fix
task. No template change needed.

### Claude's Discretion

- Whether `render-module` CLI gets extended OR only the agent pipeline uses the new features
- How odoo-model-gen "appends" computed method bodies to rendered files (rewrite vs append vs Write tool)
- Exact file ordering in `generate.md` commit strategy
- Test generation scope for computed fields (CODG-02 says tests must cover computed fields)
- Whether odoo-test-gen needs activation in Phase 5 or Phase 6

### Deferred Ideas (OUT OF SCOPE)

- Kanban views (Phase 7)
- CRUD overrides (Phase 7)
- `ir.cron` and `mail.template` data records (Phase 7)
- `odoo-security-gen` activation (Phase 6)
- i18n `.pot` file (Phase 7 — QUAL-06)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CODG-01 | Generate complete `__manifest__.py` with correct version prefix, dependencies, data file references, and metadata | Manifest load order documented; sequence + wizard data refs need adding |
| CODG-02 | Generate Python model files with real fields, computed fields, onchange handlers, constraints, and CRUD overrides | Two-pass hybrid pattern fully documented; method body stubs + AI fill pattern |
| CODG-03 | Generate XML view files (form, list, search views) referencing generated models correctly | Header/statusbar pattern documented; existing view_form.xml.j2 extended |
| CODG-04 | Generate action and menu XML files wiring views to Odoo UI | Existing action.xml.j2 and menu.xml.j2 already correct; no changes needed |
| CODG-05 | Generate `__init__.py` files with correct import chains | Existing init templates already correct; wizard subdir needs adding |
| CODG-06 | Generate data files (sequences, default configuration) where spec requires them | ir.sequence pattern fully documented with prefix/padding/code format |
| CODG-07 | Generate wizard (TransientModel) files when spec includes multi-step user flows | Complete wizard pattern documented: py + form XML + footer buttons + target="new" action |
| CODG-08 | All generated Python code follows OCA standards (PEP 8, 120 char, import ordering) | OCA conventions fully documented in knowledge/MASTER.md + models.md |
| CODG-09 | All generated XML uses correct Odoo 17.0 syntax (`<tree>` not `<list>`, inline modifiers) | Already correct; REQUIREMENTS.md wording fix needed per CONTEXT.md decision |
| CODG-10 | System generates README explaining module purpose, installation, configuration, role assignment, and usage | Existing readme.rst.j2 is correct OCA format; CODG-10 says .md but OCA uses .rst |
</phase_requirements>

---

## Summary

Phase 5 extends the existing Jinja2 rendering pipeline with three concrete additions: (1) computed/onchange/constrains method stub generation in `model.py.j2` with AI-written bodies by `odoo-model-gen`, (2) new wizard templates (`wizard.py.j2`, `wizard_form.xml.j2`) and sequence templates (`sequences.xml.j2`), and (3) the `generate.md` workflow that orchestrates two waves of specialist agents.

The project already has a mature, verified knowledge base covering all Odoo 17.0 specifics (models.md, views.md, wizards.md, data.md, testing.md). Every Odoo 17.0 API pattern needed for Phase 5 is documented there with WRONG/CORRECT examples. Research confirms these are accurate for Odoo 17.0. The primary research value for Phase 5 is understanding: how to structure the two-pass file generation (Jinja2 stub + AI rewrite), how to prompt odoo-model-gen to produce consistent OCA-compliant method bodies, and what exact code patterns go into the new templates.

The two-pass generation strategy is: Jinja2 writes the complete model file including method stubs marked with `# TODO: implement` placeholders, then `odoo-model-gen` reads the file and rewrites it completely with proper method bodies. This full-file-rewrite approach is cleaner than append-based approaches because it avoids marker string fragility and produces a consistent, lint-clean result. The agent uses the Write tool to overwrite the file.

**Primary recommendation:** Use full-file-rewrite pattern for odoo-model-gen pass (not append/patch). Provide the agent with the Jinja2-rendered file as read context plus spec JSON field hints. Generate method stubs with clear dependency/onchange/constraint metadata in comments so the agent knows exactly what to implement.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.x (already installed) | Template rendering for all structural code | Existing renderer.py uses Jinja2; StrictUndefined catches missing vars |
| Python stdlib (pathlib, json) | 3.12 | File I/O, spec loading | Already used in renderer.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jinja2.StrictUndefined | (built-in) | Fail loudly on missing template variables | All templates — already configured in create_renderer() |
| odoo.tests.common.TransactionCase | Odoo 17.0 | Test base class | All generated test files (SavepointCase is deprecated) |
| odoo.exceptions.ValidationError | Odoo 17.0 | Constraint error raising | All @api.constrains methods |
| odoo.exceptions.UserError | Odoo 17.0 | Business logic errors in action methods | Action methods that can fail |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Full-file rewrite by agent | Append to file with markers | Append is fragile (marker strings can be misplaced); rewrite produces consistent lint-clean result |
| Full-file rewrite by agent | AST manipulation (ast module) | AST manipulation is high complexity, hard to preserve formatting; not needed when agent does natural language writing |
| Jinja2 stub + AI method bodies | Pure AI generation (no Jinja2) | Pure AI cannot guarantee consistent field declaration syntax; Jinja2 guarantees structure, AI fills logic |
| Inline `invisible` expressions | `attrs` dict | `attrs` is removed in Odoo 17.0 — hard breakage |

**Installation:** No new packages needed. All required libraries are already installed.

---

## Architecture Patterns

### Recommended Project Structure (Phase 5 Additions)

```
python/src/odoo_gen_utils/
  templates/
    model.py.j2            # EXTEND: add computed/onchange/constrains stubs
    view_form.xml.j2       # EXTEND: add <header>/statusbar when state field detected
    wizard.py.j2           # NEW
    wizard_form.xml.j2     # NEW
    sequences.xml.j2       # NEW

agents/
  odoo-model-gen.md        # ACTIVATE: full system prompt for method body writing
  odoo-view-gen.md         # ACTIVATE: full system prompt for view enrichment
  odoo-test-gen.md         # PARTIAL ACTIVATE: computed field test scope

workflows/
  generate.md              # NEW: two-wave orchestration workflow
  spec.md                  # MINOR EDIT: add one line calling generate.md on approval
```

### Pattern 1: Jinja2 Stub + AI Method Body Rewrite (Two-Pass)

**What:** Jinja2 renders complete model file including method stubs. Agent reads the file + spec, then rewrites the file with complete method bodies.

**When to use:** Any field with `compute`, `onchange`, or `constrains` key in spec.

**Jinja2 stub output (pass 1):**
```python
# Source: model.py.j2 extension — renders stub when field has compute key

total_amount = fields.Float(
    string="Total Amount",
    compute="_compute_total_amount",
    store=True,
)

@api.depends('quantity', 'unit_price')
def _compute_total_amount(self):
    # TODO: implement — depends on quantity, unit_price
    for rec in self:
        rec.total_amount = 0.0
```

**AI rewrite output (pass 2 by odoo-model-gen):**
```python
# Source: odoo-model-gen agent using knowledge/models.md patterns

total_amount = fields.Float(
    string="Total Amount",
    compute="_compute_total_amount",
    store=True,
)

@api.depends('quantity', 'unit_price')
def _compute_total_amount(self):
    for rec in self:
        rec.total_amount = rec.quantity * rec.unit_price
```

### Pattern 2: State Field Detection in view_form.xml.j2

**What:** Template inspects fields list for a Selection field named `state` or `status`. If found, renders `<header>` block with statusbar before `<sheet>`.

**When to use:** Any model with a `state` or `status` Selection field.

**Template logic:**
```jinja2
{# view_form.xml.j2 — detect state field #}
{% set state_field = namespace(found=none) %}
{% for field in fields %}
  {% if field.name in ('state', 'status') and field.type == 'Selection' %}
    {% set state_field.found = field %}
  {% endif %}
{% endfor %}

<form string="{{ model_description }}">
{% if state_field.found %}
    <header>
        <!-- Action buttons generated by odoo-model-gen -->
        <field name="{{ state_field.found.name }}" widget="statusbar"
               statusbar_visible="{{ state_field.found.selection | map(attribute=0) | join(',') }}"/>
    </header>
{% endif %}
    <sheet>
```

**Exact Odoo 17.0 statusbar XML (verified from knowledge/views.md):**
```xml
<header>
    <button name="action_confirm" string="Confirm"
            type="object" class="btn-primary"
            invisible="state != 'draft'"/>
    <button name="action_done" string="Done"
            type="object" class="btn-primary"
            invisible="state != 'confirmed'"/>
    <field name="state" widget="statusbar"
           statusbar_visible="draft,confirmed,done"/>
</header>
```

- `statusbar_visible` is a comma-separated string (no spaces) of state keys to show as steps
- Buttons use `invisible="state != 'draft'"` NOT the removed `states="draft"` attribute
- `class="btn-primary"` on primary action buttons, plain on secondary
- Cancel button: `invisible="state in ('done', 'cancelled')"`

### Pattern 3: ir.sequence + _default_reference() Pattern

**What:** When auto-sequence is detected on a Char field, generate sequences.xml and add `_default_reference()` to the model.

**When to use:** Model has Char field named `reference`, `ref`, `number`, `sequence`, or `code` with `required: true`.

**Exact sequences.xml pattern (verified from knowledge/data.md):**
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
    <record id="seq_{{ module_name }}_{{ model_var }}" model="ir.sequence">
        <field name="name">{{ model_description }} Sequence</field>
        <field name="code">{{ model_name }}</field>
        <field name="prefix">{{ module_prefix }}/%(year)s/%(month)s/</field>
        <field name="padding">5</field>
        <field name="number_next">1</field>
        <field name="number_increment">1</field>
    </record>
</odoo>
```

- `noupdate="1"` prevents overwriting on module update (critical)
- `code` = the model name dot-notation (used in `next_by_code()` call)
- `prefix` pattern: `REF/%(year)s/%(month)s/` generates `REF/2024/03/00001`
- `padding=5` zero-fills to 5 digits

**Model method pattern (Jinja2-rendered, not AI-written):**
```python
@api.model
def _default_{{ sequence_field.name }}(self):
    return self.env['ir.sequence'].next_by_code('{{ model_name }}') or '/'

{{ sequence_field.name }} = fields.Char(
    string="{{ sequence_field.string }}",
    required=True,
    default=_default_{{ sequence_field.name }},
    readonly=True,
    copy=False,
)
```

Note: `states={"draft": [("readonly", False)]}` from CONTEXT.md Decision D is the **Odoo 16 pattern** — this is removed in Odoo 17.0. The correct Odoo 17.0 approach is to use `readonly=True` on the field and rely on view-level `readonly="state != 'draft'"` on the field in the form view. See Pitfall 2 below.

### Pattern 4: Wizard TransientModel Pattern

**What:** Generate wizard Python file and form XML from spec `wizards` array.

**wizard.py.j2 pattern (verified from knowledge/wizards.md):**
```python
from odoo import api, fields, models


class {{ wizard.name | to_class }}(models.TransientModel):
    _name = "{{ wizard.name }}"
    _description = "{{ wizard.name | replace('.', ' ') | title }}"

{% for field in wizard.fields %}
    {{ field.name }} = fields.{{ field.type }}(
        string="{{ field.string }}",
{% if field.required %}
        required=True,
{% endif %}
    )
{% endfor %}

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if self._context.get('active_model') == '{{ wizard.target_model }}':
            defaults['{{ wizard.target_model | to_python_var }}_id'] = self._context.get('active_id')
        return defaults

    def button_confirm(self):
        self.ensure_one()
        # TODO: implement wizard action (written by odoo-model-gen agent)
        return {'type': 'ir.actions.act_window_close'}
```

**wizard_form.xml.j2 pattern (verified from knowledge/wizards.md):**
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_{{ wizard.name | to_xml_id }}_form" model="ir.ui.view">
        <field name="name">{{ wizard.name }}.form</field>
        <field name="model">{{ wizard.name }}</field>
        <field name="arch" type="xml">
            <form string="{{ wizard.name | replace('.', ' ') | title }}">
                <group>
{% for field in wizard.fields %}
                    <field name="{{ field.name }}"/>
{% endfor %}
                </group>
                <footer>
                    <button name="button_confirm"
                            string="Confirm"
                            type="object"
                            class="btn-primary"/>
                    <button string="Cancel"
                            special="cancel"/>
                </footer>
            </form>
        </field>
    </record>

    <record id="action_{{ wizard.name | to_xml_id }}" model="ir.actions.act_window">
        <field name="name">{{ wizard.name | replace('.', ' ') | title }}</field>
        <field name="res_model">{{ wizard.name }}</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
        <field name="context">{'default_{{ wizard.target_model | to_python_var }}_id': active_id}</field>
    </record>
</odoo>
```

**Button on parent model's form view (added by view_form.xml.j2 when wizard present):**
```xml
<button name="%({{ module_name }}.action_{{ wizard.name | to_xml_id }})d"
        string="{{ wizard.button_label | default('Open Wizard') }}"
        type="action"
        class="btn-primary"
        invisible="state != '{{ wizard.trigger_state }}'"/>
```

Key wizard rules (from knowledge/wizards.md):
- `<footer>` not `<header>` for wizard buttons — dialogs use footer
- `special="cancel"` (not a method call) for cancel button
- `target="new"` on the action — opens as modal dialog
- `ensure_one()` in action method — wizard always single instance
- `default_get()` with `active_id` context — not direct context access in action

### Pattern 5: Two-Wave generate.md Workflow

**What:** Markdown workflow file orchestrating specialist agents in two sequential waves.

**When to use:** Called automatically when user approves spec in spec.md.

**generate.md structure:**
```markdown
# Generate Workflow

## Overview

Orchestrates complete Odoo module generation from an approved spec.json.
Called from spec.md after user approval.

## Input

- `$MODULE_NAME` — module technical name
- `$SPEC_PATH` — path to approved spec.json (e.g., `./$MODULE_NAME/spec.json`)
- `$OUTPUT_DIR` — target output directory (default: current directory)

## Step 1: Render Structural Files (Jinja2)

Run the render-module CLI to produce all structural files:
```bash
odoo-gen-utils render-module \
  --spec-file "$SPEC_PATH" \
  --output-dir "$OUTPUT_DIR"
```

This produces: __manifest__.py, __init__.py, models/*.py (with stubs), views/*.xml,
security/*, tests/*, data/sequences.xml (if any), wizards/*.py (if any), README.rst

## Step 2: Wave 1 (Parallel)

Spawn these agents in parallel using the Task tool:

### Task A: odoo-model-gen
Read each generated models/*.py file. For each model that has TODO stubs (computed
fields, onchange handlers, constraints), rewrite the file with complete OCA-compliant
method bodies. Use spec.json field hints for depends/onchange/constrains metadata.

### Task B: data-gen (inline, no separate agent needed)
Verify data/sequences.xml is correct. If spec has wizards, ensure wizard __init__.py
and manifest data entries are present. No agent needed — render-module handles this.

(Wave 1 completes when odoo-model-gen finishes all model files)

## Step 3: Wave 2 (Parallel)

Spawn these agents in parallel:

### Task C: odoo-view-gen
Read all generated views/*.xml files AND the now-complete models/*.py files.
Enrich form views: add action buttons for each workflow state transition (matching
action_xxx methods that odoo-model-gen wrote). Add wizard trigger buttons to parent
model form headers. Ensure all field references match actual generated model fields.

### Task D: odoo-test-gen (scoped to computed fields only in Phase 5)
Read models/*.py to find computed fields, constraints, and onchange handlers.
Generate test methods for each: set dependency values, assert computed result.
Append to existing tests/test_{model}.py files or rewrite them.

## Step 4: Commit

Commit all generated files:
```bash
git add "$OUTPUT_DIR/$MODULE_NAME/"
git commit -m "feat($MODULE_NAME): generate complete Odoo module from spec"
```

## Step 5: Report

Show summary: files generated, models/views/tests count, next step (validate).
```

### Pattern 6: odoo-model-gen Agent Prompt Design

**What:** System prompt structure for the model-gen agent to produce consistent OCA method bodies.

**Key design principles:**
1. Give the agent the Jinja2-rendered file (full context, not just stubs)
2. Give the agent the spec.json field definitions for the model being processed
3. Load knowledge/models.md + knowledge/MASTER.md via @include
4. Give explicit output contract: "rewrite the entire file, preserve all field declarations exactly, only fill in TODO method bodies"
5. Include a negative examples list to prevent hallucinations

**Anti-hallucination constraints for odoo-model-gen prompt:**
```
FORBIDDEN (will break Odoo 17.0):
- @api.multi decorator (removed)
- @api.one decorator (removed)
- @api.returns decorator (removed)
- attrs= in XML (removed)
- states= attribute on buttons (removed)
- from openerp import (removed)
- _columns = {} or _defaults = {} (old API)
- env.cr.execute() without parameterized queries (SQL injection)
- self.pool.get() (removed)

REQUIRED for computed fields:
- Iterate `for rec in self:` (not `self.field = ...` directly)
- @api.depends decorator with exact field paths from spec
- Method defined AFTER field declaration
- store=True fields: iteration pattern
- store=False fields: same iteration pattern

REQUIRED for constraints:
- @api.constrains decorator
- Iterate `for rec in self:`
- Raise ValidationError (not UserError, not Exception)
- Clear message with field names

REQUIRED for onchange:
- @api.onchange decorator
- Method name: _onchange_{field_name}
- Can assign to self directly (onchange runs on single record UI context)
- Return None (not a value) — or return warning dict if needed
```

### Anti-Patterns to Avoid

- **Append-only file modification:** Appending method bodies after EOF breaks because computed field declarations and method bodies must be in the same class body. Use full-file rewrite.
- **Marker-based patching:** Using `# COMPUTED_METHODS_START` markers is fragile — if Jinja2 or another pass changes the file, markers move. Agent should read the full file and rewrite it.
- **AI generating field declarations:** Jinja2 owns field declarations. The agent ONLY writes method bodies. Never let the agent change field type, string, or attribute parameters.
- **Statusbar without `<header>`:** Must be inside `<header>`, never inside `<sheet>` or `<form>` directly.
- **`states` attribute on buttons:** Completely removed in Odoo 17.0. Use `invisible="state != 'draft'"`.
- **`<list>` tag for Odoo 17:** Use `<tree>`. `<list>` is Odoo 18+.
- **Wizard buttons in `<header>`:** Wizard dialogs use `<footer>`, not `<header>`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Odoo 17.0 field declaration syntax | Custom field serializer | Jinja2 template with StrictUndefined | Already working; field types fully mapped in model.py.j2 |
| XML external ID naming | Custom naming function | `to_xml_id` filter (already in renderer.py) | Consistent convention, already tested |
| Sequence code format | Custom sequence logic | `ir.sequence` XML record + `next_by_code()` | Odoo manages sequence numbering, gaps, concurrent access |
| Wizard close action | Custom response dict builder | `{"type": "ir.actions.act_window_close"}` | Standard Odoo return value, nothing to abstract |
| Model name to class name | Custom converter | `to_class` filter (already in renderer.py) | Already handles all edge cases |
| StatusBar state list | Custom state parser | Jinja2 `| map(attribute=0) | join(',')` | Direct from selection array; no custom logic needed |
| Computed field body inference | Rule-based code generator | odoo-model-gen AI agent | Too many patterns; AI handles context-dependent logic |

**Key insight:** The Jinja2 layer already handles all deterministic structure. The AI layer handles all context-dependent logic. Never mix these concerns.

---

## Common Pitfalls

### Pitfall 1: Agent Writes `states=` on Sequence Char Field

**What goes wrong:** CONTEXT.md Decision D shows `states={"draft": [("readonly", False)]}` on the sequence Char field. This is the Odoo 16 pattern and causes a warning/error in Odoo 17.0.

**Why it happens:** The CONTEXT.md example was written with Odoo 16 syntax. The `states` parameter on field definitions was deprecated and removed.

**How to avoid:** The Jinja2 template should NOT render `states=` on fields. Instead, render `readonly=True` on the field declaration. The view template should add `readonly="state != 'draft'"` on the field element in the form view for sequence fields.

**Warning signs:** `AttributeError` or deprecation warning mentioning `states` on field objects at Odoo startup.

**Correct Odoo 17.0 pattern:**
```python
# In model — Jinja2 renders this
reference = fields.Char(
    string="Reference",
    required=True,
    default=_default_reference,
    readonly=True,
    copy=False,
)
```
```xml
<!-- In form view — view_form.xml.j2 adds readonly expression for sequence fields -->
<field name="reference" readonly="state != 'draft'"/>
```

### Pitfall 2: odoo-model-gen Forgetting to Iterate Self

**What goes wrong:** Agent writes `self.total = self.qty * self.price` in a computed method. This fails when the method is called on a multi-record recordset.

**Why it happens:** LLMs see single-record patterns more often in training data.

**How to avoid:** The agent prompt must include the iteration rule as a hard constraint. The Jinja2 stub should already iterate: `for rec in self: rec.field = 0.0` giving the agent the correct pattern to follow.

**Warning signs:** `ValueError: Expected singleton` at runtime, or silent incorrect behavior in batch operations.

### Pitfall 3: Wizard Button Uses `type="object"` with Action Name

**What goes wrong:** Developer writes `<button name="action_open_wizard" type="object"/>` in parent form header. This calls a Python method `action_open_wizard()` on the parent model rather than opening the wizard action directly.

**Why it happens:** Two correct patterns exist and are easy to confuse.

**How to avoid:** For wizard launch buttons, use `type="action"` with the XML ID reference pattern:
```xml
<button name="%(module_name.action_wizard_xml_id)d"
        type="action"
        string="Open Wizard"/>
```
OR write an `action_open_wizard()` method on the parent model that returns the action dict. The second approach is more flexible (can add domain/context). Document which pattern the templates use.

**Recommendation:** Templates use the method approach (`type="object"`, method returns action dict) because it allows adding context (active record ID) cleanly. The `%(xml_id)d` pattern requires the action to be in the same module and loaded before the button XML.

### Pitfall 4: `statusbar_visible` Lists States That Don't Exist in Selection

**What goes wrong:** `statusbar_visible="draft,confirmed,cancelled,done"` but the Selection field only has `[("draft", "Draft"), ("confirmed", "Confirmed"), ("done", "Done")]`. Odoo silently ignores unknown states, but OCA linting may flag it.

**Why it happens:** Manual editing of statusbar_visible without syncing to the selection array.

**How to avoid:** Generate `statusbar_visible` directly from the selection array using Jinja2:
```jinja2
statusbar_visible="{{ field.selection | map(attribute=0) | join(',') }}"
```
This guarantees statusbar_visible always matches the actual selection values.

### Pitfall 5: Manifest `data` Load Order Wrong When Adding Wizard + Sequence Files

**What goes wrong:** Wizard view XML references security groups that haven't loaded yet. Sequence XML uses `ref()` to records not yet loaded.

**Why it happens:** Manifest `data` list order is strict. Odoo loads files in declaration order.

**How to avoid:** Follow the canonical load order (verified from knowledge/data.md):
1. `security/security.xml` — groups and categories first
2. `security/ir.model.access.csv` — ACLs reference groups
3. `data/sequences.xml` — sequence records (with noupdate="1")
4. `data/data.xml` — other default data
5. `views/*_views.xml` — form/tree/search views
6. `views/*_action.xml` — window actions
7. `views/menu.xml` — menus reference actions
8. `views/*_wizard_form.xml` — wizard views (after main views)

**Warning signs:** `ValueError: External ID not found` during module install.

### Pitfall 6: `generate.md` Wave 2 Reads Stale Jinja2-Generated Files

**What goes wrong:** `odoo-view-gen` (Wave 2) reads the view files before Wave 1 (`odoo-model-gen`) has written the completed model files. The view enrichment references method names that don't exist yet.

**Why it happens:** Parallel agents in Wave 2 start before Wave 1 completes.

**How to avoid:** The `generate.md` workflow must enforce sequential wave execution — Wave 1 fully completes before Wave 2 spawns. The workflow must call `odoo-model-gen` synchronously and only spawn Wave 2 Tasks after confirmation that Wave 1 Tasks completed.

**Warning signs:** View gen agent references `action_confirm` but the model file still has `# TODO: implement` stub.

### Pitfall 7: Missing `wizards/` in `__init__.py` and Manifest

**What goes wrong:** Wizard Python file exists at `wizards/confirm_wizard.py` but `__init__.py` doesn't import `wizards` and `__manifest__.py` doesn't list wizard view XML in `data`.

**Why it happens:** render_module() in renderer.py currently only handles `models/`, `views/`, `security/`, `tests/`. New `wizards/` directory is not wired.

**How to avoid:** Extend renderer.py to:
- Generate `wizards/__init__.py` when wizards exist
- Update `__init__.py` root to include `from . import wizards`
- Append wizard view XML paths to manifest `data` list (after main views, before menu)
- Generate a `views/{wizard_name}_form.xml` (in views/, not wizards/)

**Warning signs:** `ImportError` when Odoo loads the module, or wizard view not found.

---

## Code Examples

Verified patterns from project knowledge base (HIGH confidence — from existing knowledge/*.md files):

### Computed Field: Full Two-Pass Example

```python
# Pass 1: Jinja2 stub output (model.py.j2 renders this)
# Source: knowledge/models.md computed fields pattern

total_amount = fields.Float(
    string="Total Amount",
    compute="_compute_total_amount",
    store=True,
)

@api.depends('quantity', 'unit_price')
def _compute_total_amount(self):
    # TODO: implement — depends on quantity, unit_price
    for rec in self:
        rec.total_amount = 0.0
```

```python
# Pass 2: odoo-model-gen rewrites the file with this body
# Source: knowledge/models.md "Iterate self in compute methods"

@api.depends('quantity', 'unit_price')
def _compute_total_amount(self):
    for rec in self:
        rec.total_amount = rec.quantity * rec.unit_price
```

### Onchange Handler Pattern

```python
# Source: knowledge/models.md decorators table + MASTER.md naming conventions

@api.onchange('partner_id')
def _onchange_partner_id(self):
    if self.partner_id:
        self.currency_id = self.partner_id.property_purchase_currency_id.id
```

Note: onchange methods can assign to `self` directly (not `for rec in self`). Onchange runs in UI context on a single record. Return `None` normally; return `{'warning': {'title': ..., 'message': ...}}` for validation warnings.

### Constraint Pattern

```python
# Source: knowledge/models.md "@api.constrains for Python validation"

from odoo.exceptions import ValidationError

@api.constrains('date_start', 'date_end')
def _check_date_range(self):
    for rec in self:
        if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
            raise ValidationError(
                _("End date must be after start date.")
            )
```

### ir.sequence in sequences.xml

```xml
<!-- Source: knowledge/data.md "Define sequences with ir.sequence" -->
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
    <record id="seq_my_module_order" model="ir.sequence">
        <field name="name">My Module Order</field>
        <field name="code">my.module.order</field>
        <field name="prefix">ORD/%(year)s/%(month)s/</field>
        <field name="padding">5</field>
        <field name="number_next">1</field>
        <field name="number_increment">1</field>
    </record>
</odoo>
```

### State Field Detection in Jinja2 Template

```jinja2
{# Source: knowledge/views.md "Complete statusbar with conditional buttons" #}
{# Used in view_form.xml.j2 to detect state/status Selection field #}

{% set state_field = namespace(found=none) %}
{% for f in fields %}
  {% if f.name in ('state', 'status') and f.type == 'Selection' %}
    {% set state_field.found = f %}
  {% endif %}
{% endfor %}

{% if state_field.found %}
            <header>
                <!-- Action buttons to be enriched by odoo-view-gen -->
                <field name="{{ state_field.found.name }}" widget="statusbar"
                       statusbar_visible="{{ state_field.found.selection | map(attribute=0) | join(',') }}"/>
            </header>
{% endif %}
```

### Wizard Confirm Action Method

```python
# Source: knowledge/wizards.md "Return act_window_close to close the wizard"

def button_confirm(self):
    self.ensure_one()
    target = self.env[self._context.get('active_model')].browse(
        self._context.get('active_id')
    )
    # Write wizard data to target record
    target.write({'state': 'confirmed'})
    return {'type': 'ir.actions.act_window_close'}
```

### TransactionCase Test for Computed Field

```python
# Source: knowledge/testing.md "Set dependency fields, then assert computed value"

from odoo.tests.common import TransactionCase


class TestMyModuleOrder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Order = cls.env['my.module.order']

    def test_compute_total_amount(self):
        order = self.Order.create({
            'name': 'Test Order',
            'quantity': 5.0,
            'unit_price': 20.0,
        })
        self.assertEqual(order.total_amount, 100.0)

    def test_compute_total_amount_zero_quantity(self):
        order = self.Order.create({
            'name': 'Zero Order',
            'quantity': 0.0,
            'unit_price': 20.0,
        })
        self.assertEqual(order.total_amount, 0.0)
```

### TransactionCase Test for Constraint

```python
# Source: knowledge/testing.md "Use assertRaises(ValidationError) with invalid data"

from odoo.exceptions import ValidationError

def test_constraint_date_range_invalid(self):
    with self.assertRaises(ValidationError):
        self.Order.create({
            'name': 'Bad Dates',
            'date_start': '2024-03-15',
            'date_end': '2024-03-01',  # End before start
        })

def test_constraint_date_range_valid(self):
    order = self.Order.create({
        'name': 'Good Dates',
        'date_start': '2024-03-01',
        'date_end': '2024-03-15',
    })
    self.assertTrue(order.id)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@api.model` for batch create | `@api.model_create_multi` | Odoo 17.0 | Batch-first; single dict still works but deprecated path |
| `attrs="{'invisible': [...]}"` | `invisible="expression"` | Odoo 17.0 | BREAKING — attrs removed entirely |
| `states="draft"` on buttons | `invisible="state != 'draft'"` | Odoo 17.0 | BREAKING — states attribute removed |
| `column_invisible` in attrs | `column_invisible="expression"` | Odoo 17.0 | New dedicated attribute |
| `<openerp>` root XML tag | `<odoo>` | Odoo 10 | Hard error if used |
| `<list>` for list views | `<tree>` (17.0) / `<list>` (18.0+) | Odoo 18 introduced `<list>` | Must use `<tree>` in 17.0 |
| `<div class="oe_chatter">` + fields | `<chatter/>` shorthand | Odoo 17.0 | Simpler; only if model inherits mail.thread |
| `SavepointCase` | `TransactionCase` | Odoo 17.0 | SavepointCase deprecated |
| `_constraints` list | `@api.constrains` decorator | Odoo 13 | Old API fully removed |
| `@api.multi` / `@api.one` | Methods work on recordsets by default | Odoo 13 | AttributeError if used |
| `fields.states={"draft": ...}` (field parameter) | `readonly="state != 'draft'"` in view XML | Odoo 17.0 | Field parameter removed |

**Deprecated/outdated patterns to never generate:**
- `@api.multi`, `@api.one`, `@api.returns` decorators
- `attrs=` attribute in XML
- `states=` attribute on buttons or fields in XML
- `<list>` tag for list views in Odoo 17.0
- `states={"draft": [...]}` parameter on field definitions
- `SavepointCase` as test base class

---

## Open Questions

1. **render-module CLI extension vs agent-only path**
   - What we know: CONTEXT.md leaves this as Claude's discretion
   - What's unclear: Should `render-module --spec-file` be extended to handle all new features (computed stubs, sequences, wizards), or should it only be used for the structural pass with agents doing the rest?
   - Recommendation: Extend render-module for all Jinja2-renderable features (field stubs, header detection, wizard templates, sequences.xml). The CLI should produce the complete Jinja2-renderable output. Agents then do the AI-requiring pass. This keeps render-module testable in isolation (no AI required for unit tests).

2. **odoo-test-gen scope in Phase 5**
   - What we know: CODG-02 requires tests covering computed fields. Phase 5 partially activates odoo-test-gen.
   - What's unclear: How much test generation to activate — just computed field tests, or full model test rewrite?
   - Recommendation: Partial activation — odoo-test-gen in Phase 5 appends computed/constraint/onchange test methods to existing `test_{model}.py` files generated by the Jinja2 template. Full test generation (access rights, workflow) stays Phase 6.

3. **Field-level `readonly` vs view-level `readonly` for sequence fields**
   - What we know: CONTEXT.md Decision D shows `states={"draft": [...]}` pattern which is Odoo 16.
   - What's unclear: Exact Odoo 17.0 replacement for sequence Char field edit control.
   - Recommendation (confirmed from views.md): Use `readonly=True` on field declaration + `readonly="state != 'draft'"` in form view XML. The `states=` parameter on field definitions is removed in 17.0.

---

## Sources

### Primary (HIGH confidence)
- `/home/inshal-rauf/Odoo_module_automation/knowledge/models.md` — computed fields, constraints, decorators, OCA conventions, Odoo 17.0 changes
- `/home/inshal-rauf/Odoo_module_automation/knowledge/views.md` — form views, statusbar, header pattern, inline modifiers, Odoo 17.0 changes
- `/home/inshal-rauf/Odoo_module_automation/knowledge/wizards.md` — TransientModel, footer buttons, target="new", default_get, ensure_one
- `/home/inshal-rauf/Odoo_module_automation/knowledge/data.md` — ir.sequence format, noupdate, manifest load order
- `/home/inshal-rauf/Odoo_module_automation/knowledge/testing.md` — TransactionCase, setUpClass, computed field tests, constraint tests
- `/home/inshal-rauf/Odoo_module_automation/knowledge/MASTER.md` — naming conventions, import ordering, global rules
- `/home/inshal-rauf/Odoo_module_automation/python/src/odoo_gen_utils/renderer.py` — existing render engine, filter functions, render_module() entry point
- `/home/inshal-rauf/Odoo_module_automation/python/src/odoo_gen_utils/templates/model.py.j2` — current template structure to extend
- `/home/inshal-rauf/Odoo_module_automation/python/src/odoo_gen_utils/templates/view_form.xml.j2` — current form template to extend
- `/home/inshal-rauf/Odoo_module_automation/.planning/phases/05-core-code-generation/05-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- `STATE.md` accumulated decisions — confirms `states` parameter deprecation, `<tree>` vs `<list>` decision
- `CONTEXT.md` wizard and sequence patterns — confirmed against wizards.md and data.md

### Tertiary (LOW confidence)
- None — all claims sourced from project knowledge base or existing code

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing codebase, no new dependencies
- Architecture: HIGH — all patterns verified from project knowledge base
- Pitfalls: HIGH — sourced from existing WRONG/CORRECT examples in knowledge files
- Code examples: HIGH — taken directly from knowledge/*.md verified patterns

**Research date:** 2026-03-02
**Valid until:** 2026-06-01 (Odoo 17.0 patterns are stable; knowledge base already maintained)
