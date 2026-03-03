---
phase: 06-security-test-generation
created: 2026-03-02T17:30:00Z
status: context-captured
---

# Phase 6 Context: Security & Test Generation

## Goal

Every generated Odoo 17.0 module has complete security infrastructure (ACLs, groups, record rules)
and a meaningful test suite that verifies real behavior — runnable via `/odoo-gen:validate`.

## Requirements in Scope

SECG-01, SECG-02, SECG-03, SECG-04, SECG-05, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06

## Codebase State at Phase 6 Start

### Already Working (Phases 1–5)

| Capability | File | Notes |
|---|---|---|
| `ir.model.access.csv` | `access_csv.j2` | User: read/write/create (no unlink); Manager: full CRUD |
| Security groups + category | `security_group.xml.j2` | User/Manager groups, module category, `implied_ids`, admin users |
| Basic tests | `test_model.py.j2` | create + read + name_get only |
| Computed/constraint/onchange tests | `odoo-test-gen.md` (Phase 5 scope) | 2 tests/computed, 2/constraint, 1/onchange |
| `odoo-security-gen.md` | `agents/odoo-security-gen.md` | Stub — not activated |
| `odoo-test-gen.md` | `agents/odoo-test-gen.md` | Partial — Phase 5 scope only |
| `generate.md` wave pipeline | `workflows/generate.md` | Wave 1: model-gen; Wave 2: view-gen + test-gen |

### Missing (Phase 6 Must Build)

| Gap | Requirement | Approach |
|---|---|---|
| Record rules for multi-company | SECG-03 | New `record_rules.xml.j2` template; auto-detect `company_id` field |
| `has_company_field` context key | SECG-03 | Extend `_build_model_context()` in renderer.py |
| CRUD write + unlink tests | TEST-02 | Expand `odoo-test-gen` scope + update test template |
| Access rights tests | TEST-03 | `with_user()` + `assertRaises(AccessError)` pattern |
| Workflow transition tests | TEST-06 | 1 test per state pair when `state_field` exists |
| `odoo-security-gen` full activation | SECG-01..05 | Write full system prompt (standalone use, not wave pipeline) |
| `odoo-test-gen` Phase 6 expansion | TEST-02..06 | Expand scope beyond Phase 5 computed/constraint/onchange |

---

## Decisions

### A — Multi-company Record Rules: Auto-detect via `company_id` field

**Decision:** Scan each model's fields in `_build_model_context()`. If a `Many2one` field named
`company_id` pointing to `res.company` exists, set `has_company_field = True`. Generate a
`security/record_rules.xml` file for that model.

**Detection pattern (same as sequence field detection in Phase 5):**
```python
has_company_field = any(
    f.get("name") == "company_id" and f.get("type") == "Many2one"
    for f in model_spec.get("fields", [])
)
```

**No override mechanism in v1.** If a model has a `company_id` field, it gets record rules.
Edge cases deferred to Phase 7.

**Domain pattern — use `company_ids` (OCA shorthand):**
```xml
<record id="rule_{{ model_var }}_company" model="ir.rule">
    <field name="name">{{ model_title }}: Company</field>
    <field name="model_id" ref="{{ model_ref }}"/>
    <field name="global" eval="True"/>
    <field name="domain_force">[('company_id', 'in', company_ids)]</field>
</record>
```

**Why `company_ids` (shorthand, not `user.company_ids.ids`):** In Odoo 17.0 record rule
evaluation context, `company_ids` is a pre-defined shorthand equivalent to `user.company_ids.ids`.
It is the OCA-preferred form — concise, readable, and confirmed correct by RESEARCH.md Pattern 2.
Both forms are functionally identical; `company_ids` is locked as the authoritative form for this
project.

**Supports multi-branch:** Users belonging to multiple companies can see records from all their
companies. Admin/root bypass is Odoo's built-in superuser behaviour.

**Rule scope:** Global rule (`<field name="global" eval="True"/>`) — no group restriction.
Applies to all users.

**New template:** `python/src/odoo_gen_utils/templates/record_rules.xml.j2`
**New renderer key:** `has_company_field` in `_build_model_context()` return dict
**Manifest:** `record_rules.xml` added to `data` section after `ir.model.access.csv`,
before view files.

---

### B — Default User Permission Model: Fixed Least-Privilege

**Decision:** Keep current `access_csv.j2` defaults unchanged. No per-spec configurability in v1.

| Role | read | write | create | unlink |
|---|---|---|---|---|
| User | 1 | 1 | 1 | 0 |
| Manager | 1 | 1 | 1 | 1 |

**Rationale:** Least privilege is correct OCA default. Users can create and edit records but
cannot permanently delete them. Only managers can delete. This is the right default for 95%
of business modules.

**No read-only role in Phase 6.** Deferred to Phase 7 as an optional third tier.
**No per-spec configurability in Phase 6.** Deferred to Phase 7.

---

### C — Test Scope & Depth: Phase 6 Expansion

**Decision:** `odoo-test-gen` Phase 6 scope adds three new test categories beyond Phase 5.

#### Full test scope table (Phase 5 + Phase 6 combined):

| Category | Tests Generated | Phase |
|---|---|---|
| create | 1 test (basic create with required fields) | 5 (via template) |
| read | 1 test (read required fields) | 5 (via template) |
| name_get | 1 test (if name field exists) | 5 (via template) |
| Computed fields | 2 per field (basic + zero_case) | 5 |
| Constraints | 2 per constraint (valid + invalid) | 5 |
| Onchange | 1 per handler | 5 |
| **write** | **1 test per model (update a field, assert changed)** | **6** |
| **unlink** | **1 test per model (delete record, assert gone)** | **6** |
| **Access rights** | **2 per model (user can-create + no-group cannot-create)** | **6** |
| **Workflow transitions** | **1 per state pair if state_field exists** | **6** |

#### Access rights test pattern (canonical):

```python
from odoo.exceptions import AccessError

def test_user_can_create(self):
    user = self.env['res.users'].create({
        'name': 'Test User',
        'login': 'test_user_create@example.com',
    })
    user.groups_id = [(4, self.env.ref('module_name.group_module_name_user').id)]
    record = self.Model.with_user(user).create({'name': 'Access Test', ...})
    self.assertTrue(record.id)

def test_no_group_cannot_create(self):
    user = self.env['res.users'].create({
        'name': 'No Group User',
        'login': 'no_group@example.com',
    })
    with self.assertRaises(AccessError):
        self.Model.with_user(user).create({'name': 'Should Fail', ...})
```

#### Write + unlink test pattern (canonical):

```python
def test_write(self):
    self.test_record.write({'name': 'Updated Name'})
    self.assertEqual(self.test_record.name, 'Updated Name')

def test_unlink(self):
    record_id = self.test_record.id
    self.test_record.unlink()
    self.assertFalse(self.env['{model_name}'].browse(record_id).exists())
```

#### Workflow transition test pattern (when state_field exists):

```python
def test_state_transition_{from_state}_to_{to_state}(self):
    self.assertEqual(self.test_record.{state_field}, '{from_state}')
    self.test_record.action_{to_state}()
    self.assertEqual(self.test_record.{state_field}, '{to_state}')
```

**Workflow test prerequisite:** `odoo-model-gen` (Phase 5) must have written `action_{state}()`
methods on the model. Test assumes those methods exist. If not present, test is skipped (odoo-test-gen
checks for method existence before generating transition test).

**Scope boundary — deferred to Phase 7:**
- Manager-specific access rights tests
- Field-level access tests (ir.model.fields access)
- Portal user tests
- Multi-company record rule tests (testing the record rules generated by SECG-03)

---

### D — odoo-security-gen Agent: Standalone Only, Not in Wave Pipeline

**Decision:** `odoo-security-gen` is NOT added to `generate.md` wave pipeline.

**Rationale:** Security generation is fully deterministic from the spec:
- `access_csv.j2` → covers SECG-01 and SECG-05 completely
- `security_group.xml.j2` → covers SECG-02 and SECG-04 completely
- `record_rules.xml.j2` (new) → covers SECG-03 when `has_company_field` is True

No AI judgment is required for standard security. Adding an AI agent to the pipeline for
deterministic output would add latency and failure risk with no benefit.

**odoo-security-gen activation in Phase 6:** Write the full system prompt so it's usable
as a standalone agent for:
1. Post-validation remediation — user runs `/odoo-gen:validate`, gets security violations,
   calls the agent to fix them
2. Complex customizations — custom record rules, field-level security, portal access rules
3. Security review on demand — agent audits generated security files against KB

**`generate.md` changes in Phase 6:**
- NO new waves added
- Wave 2 Task B prompt updated to expand `odoo-test-gen` scope to include
  write/unlink/access-rights/workflow tests

---

## Code Context

### renderer.py changes (Phase 6)

**`_build_model_context()` new keys:**
- `has_company_field` — bool: True if model has Many2one `company_id` field to res.company
- `workflow_states` — list: from `model.get("workflow_states", [])` (consumed by test_model.py.j2)

**`render_module()` new output:**
- `security/record_rules.xml` — if any model has `has_company_field=True`
  (one file for all models with company isolation, not per-model)

**Manifest `data` section ordering (updated canonical order):**
```
security/security.xml
security/ir.model.access.csv
security/record_rules.xml   ← NEW (only if has_company_field models exist)
data/sequences.xml          (if sequence fields)
data/data.xml
views/{model}_views.xml     (per model)
views/{model}_action.xml    (per model)
views/menu.xml
views/{wizard}_wizard_form.xml (per wizard)
```

### record_rules.xml.j2 (new template)

```xml
{# record_rules.xml.j2 -- Multi-company record rules #}
<?xml version="1.0" encoding="utf-8"?>
<odoo>
{% for model in models if model.has_company_field %}
    <record id="rule_{{ model.name | to_python_var }}_company" model="ir.rule">
        <field name="name">{{ model.name }}: Company</field>
        <field name="model_id" ref="{{ model.name | model_ref }}"/>
        <field name="global" eval="True"/>
        <field name="domain_force">[('company_id', 'in', company_ids)]</field>
    </record>
{% endfor %}
</odoo>
```

### test_model.py.j2 changes (Phase 6)

Add after existing create/read/name_get blocks:
- `test_write` method
- `test_unlink` method
- `test_user_can_create` method (imports `AccessError`)
- `test_no_group_cannot_create` method
- `test_state_transition_{from}_{to}` methods (conditional on `state_field`)

### odoo-test-gen.md changes (Phase 6)

Update Phase scope declaration from "Phase 5: computed/constraint/onchange" to full Phase 6 scope.
Add sections for write/unlink, access rights, and workflow patterns.

---

## Integration Points

- **Phase 5 output** → `generate.md` pipeline, `odoo-model-gen` method bodies, `state_field`
  detection already wired in `view_form.xml.j2`
- **Phase 3 validation** → `odoo-gen-utils validate` verifies generated security files
- **Phase 7 (next)** → CRUD overrides, read-only role, manager-specific access tests,
  portal user tests, multi-company record rule tests

## Deferred (Not Phase 6)

- Read-only user role (third tier below User)
- Per-spec permission configurability (e.g., `allow_user_delete: true`)
- Manager-specific access rights tests
- Multi-company record rule validation tests (testing the rules work correctly)
- Field-level access rules (ir.model.fields)
- Portal user access tests
- `ir.cron` and `mail.template` data records (Phase 7)
