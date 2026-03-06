# Phase 39: Approval Workflows - Research

**Researched:** 2026-03-06
**Domain:** Odoo multi-level approval workflow generation, state machine pattern, group-gated action methods, ir.rule per approval stage
**Confidence:** HIGH

## Summary

Phase 39 extends the code generation pipeline with a complete multi-level approval workflow system. When a model spec contains an `approval` block, the preprocessor synthesizes a Selection `state` field with all approval levels (plus auto-prepended `draft` and optional `rejected`), generates group-gated action methods for each approval transition, produces header buttons with `invisible=` and `groups=` attributes, creates `ir.rule` record rules for stage-based visibility, and installs a write() guard that blocks direct state field modification.

The implementation follows established Phase 37/38 patterns precisely: a pure-function preprocessor (`_process_approval_patterns`) added to the chain in `render_module()` after `_process_security_patterns` and `_process_audit_patterns`, new context keys in `_build_model_context` with defaults to prevent StrictUndefined crashes, template blocks in both `model.py.j2` (17.0 and 18.0) and `view_form.xml.j2`, and additional `ir.rule` records via the existing `record_rules.xml.j2` template. The write() approval guard sits inside the audit wrapper in the stacking order: audit (outermost) -> approval state guard -> constraints -> cache -> super().

**Primary recommendation:** Follow the audit trail preprocessor pattern exactly. The approval preprocessor is structurally similar (pure function, spec enrichment, override_sources, template blocks) but adds view-layer complexity (header buttons, readonly locking) that the audit trail did not. Template changes must cover both 17.0 and 18.0 variants.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Rich spec format: each approval level is an object with `state`, `role`, `next`, optional `group`, optional `label`
- `draft` is ALWAYS auto-prepended as the initial state
- If `on_reject` is `"rejected"`, preprocessor auto-appends a `rejected` state to the Selection
- `role` field maps to module security role (Phase 37); optional `group` overrides with explicit XML ID
- Priority: explicit `group` > role-based resolution to `{module}.group_{role}`
- Two-layer enforcement: XML `groups=` hides buttons + Python `has_group()` raises UserError
- UserError (not AccessError) for business logic violations, with role name in message
- Write() state guard blocks direct state modification; bypass via `_force_state` context flag AND `env.is_superuser()`
- Stacking order: audit (outermost) -> approval state guard -> constraints -> cache -> super()
- Adds `"approval"` to `override_sources["write"]`
- Record rules: Two-tier (draft=creator+managers only, non-draft=all readers), not per-stage
- `lock_after` field controls when fields become readonly (default: `"draft"`)
- `editable_fields` list exempts specific fields from stage locking
- Auto-excluded from locking: `message_ids`, `activity_ids`
- `on_reject` is module-level target state: `"draft"` or `"rejected"`
- `reject_allowed_from` controls which stages get a reject button

### Claude's Discretion
- Exact Jinja2 template block structure for action methods
- Helper method names and organization
- How to render rejection reason field (if on_reject = "rejected")
- Button ordering in form header (approve, reject, reset)
- Test fixture organization for approval-specific tests
- Whether action methods call `self.write()` directly or use a helper

### Deferred Ideas (OUT OF SCOPE)
- Parallel approval paths
- Approval delegation
- Approval history/comments per transition
- SLA/deadline enforcement on approval stages
- Conditional approval routing (amount-based)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BIZL-01 | Models with `approval` in spec generate multi-level state field, action methods, group-gated header buttons, and `ir.rule` per approval stage | Preprocessor enriches spec with approval metadata (state Selection, action method specs, group references); model template renders action methods with has_group() + UserError; view template renders header buttons with invisible + groups; record_rules template generates two-tier ir.rule entries; write() guard blocks direct state modification |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1.x | Template rendering for model.py.j2, view_form.xml.j2, record_rules.xml.j2 | Already used throughout project |
| Python | 3.12 | Preprocessor + context builder code | Project standard |
| collections.defaultdict | stdlib | override_sources pattern for write stacking | Established in Phase 36 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.0+ | Unit/integration tests for preprocessor + templates | All test code |
| tempfile | stdlib | Temporary directories for render integration tests | Smoke tests |

### Alternatives Considered
None -- this phase uses only existing project infrastructure. No new dependencies.

## Architecture Patterns

### Recommended Project Structure
```
python/src/odoo_gen_utils/
  preprocessors.py          # Add _process_approval_patterns()
  renderer_context.py       # Add approval context keys to _build_model_context + _build_module_context
  renderer.py               # Wire _process_approval_patterns in render_module() chain
  templates/
    17.0/model.py.j2        # Approval action methods + write() state guard blocks
    17.0/view_form.xml.j2   # Header buttons with invisible= and groups= for approval
    18.0/model.py.j2        # Same approval blocks (18.0 variant)
    18.0/view_form.xml.j2   # Same header buttons (18.0 variant)
    shared/record_rules.xml.j2  # Extended with approval-stage ir.rule entries
python/tests/
  test_preprocessors.py     # Unit tests for _process_approval_patterns
  test_renderer.py          # Integration: approval templates rendered correctly
```

### Pattern 1: Approval Preprocessor (Pure Function)
**What:** `_process_approval_patterns(spec)` scans all models for an `approval` block, validates role references against `security_roles`, synthesizes the state Selection field with auto-prepended `draft` and optional `rejected`, builds action method metadata for each level, resolves group XML IDs, and enriches the model with approval-specific keys.
**When to use:** Called in `render_module()` after `_process_audit_patterns` (approval write guard sits inside audit wrapper).
**Example:**
```python
# Source: Modeled on _process_audit_patterns at preprocessors.py:1036
def _process_approval_patterns(spec: dict[str, Any]) -> dict[str, Any]:
    models = spec.get("models", [])
    approval_models = [m for m in models if m.get("approval")]
    if not approval_models:
        return spec

    module_name = spec["module_name"]
    security_roles = spec.get("security_roles", [])
    role_lookup = {r["name"]: r for r in security_roles}

    new_models = []
    for model in models:
        if not model.get("approval"):
            new_models.append(model)
            continue

        new_model = {**model, "fields": list(model.get("fields", []))}
        approval = model["approval"]
        levels = approval["levels"]

        # Validate all roles exist in security_roles
        for level in levels:
            role = level.get("role")
            if role and role not in role_lookup and not level.get("group"):
                raise ValueError(f"Approval role '{role}' not found in security.roles")

        # Build state Selection with auto-prepended draft
        state_selection = [("draft", approval.get("initial_label", "Draft"))]
        for level in levels:
            state_selection.append((level["state"], level.get("label", level["state"].replace("_", " ").title())))
        # Terminal state from last level's "next"
        terminal = levels[-1]["next"]
        state_selection.append((terminal, terminal.replace("_", " ").title()))
        # Optional rejected state
        on_reject = approval.get("on_reject", "draft")
        if on_reject == "rejected":
            state_selection.append(("rejected", "Rejected"))

        # Build action method specs
        action_methods = []
        for level in levels:
            group_xml_id = level.get("group") or f"{module_name}.group_{module_name}_{level['role']}"
            action_methods.append({
                "name": f"action_approve_{level['state']}",  # or action_{next_state}
                "from_state": level["state"],  # state that triggers this action
                "to_state": level["next"],
                "group_xml_id": group_xml_id,
                "role_label": role_lookup.get(level["role"], {}).get("label", level["role"]),
            })

        # Inject/replace state field
        # ... enrich model with has_approval, approval_levels, etc.

        # Add "approval" to override_sources["write"]
        new_model.setdefault("override_sources", defaultdict(set))
        new_model["override_sources"]["write"].add("approval")
        new_model["has_write_override"] = True

        new_models.append(new_model)

    return {**spec, "models": new_models}
```

### Pattern 2: Write() State Guard (Template Block)
**What:** A guard in the write() method that intercepts direct state field modifications and raises UserError. Only `_force_state` context flag or superuser bypass is allowed.
**When to use:** Rendered inside the write() method, AFTER the audit skip path but BEFORE the main super() call.
**Example:**
```python
# Source: CONTEXT.md locked decision
def write(self, vals):
    # [audit skip path first - if has_audit]
    # [audit old values capture - if has_audit]

    # Approval state guard
    if 'state' in vals and not self.env.context.get('_force_state'):
        if not self.env.is_superuser():
            raise UserError(_("State transitions must use action buttons."))

    # [cache clear - if is_cacheable]
    result = super().write(vals)
    # [write constraints - if any]
    # [audit log - if has_audit]
    return result
```

### Pattern 3: Group-Gated Action Method
**What:** Each approval level generates an action method that checks group membership, validates current state, then transitions.
**When to use:** Rendered as methods on the model class, one per approval level.
**Example:**
```python
# Source: CONTEXT.md locked decision
def action_approve_hod(self):
    self.ensure_one()
    if not self.env.user.has_group('uni_fee.group_hod'):
        raise UserError(_("Only the Head Of Department can approve at this stage."))
    if self.state != 'submitted':
        raise UserError(_("Record must be in 'Submitted' state to approve."))
    self.write({'state': 'approved_hod'})
```

### Pattern 4: Header Buttons with invisible + groups
**What:** Form view header buttons for each approval action, conditionally visible based on state and restricted by group.
**When to use:** Rendered in the `<header>` section of view_form.xml.j2 when `has_approval` is true.
**Example (Odoo 17.0+):**
```xml
<!-- Source: Odoo 17 uses invisible= not states= -->
<button name="action_approve_hod"
        string="Approve (HOD)"
        type="object"
        class="btn-primary"
        invisible="state != 'submitted'"
        groups="uni_fee.group_hod"/>
```

**Critical note:** Odoo 17 deprecated the `states=` attribute in favor of `invisible=` expressions. The CONTEXT.md references `states=` but the existing codebase already uses `invisible=` consistently. Templates MUST use `invisible="state != 'from_state'"` NOT `states="from_state"`.

### Pattern 5: Two-Tier Record Rules
**What:** Draft records visible only to creator + managers; non-draft records visible to all readers.
**When to use:** Generated as `ir.rule` XML records when model has `has_approval`.
**Example:**
```xml
<!-- Draft: creator + managers only -->
<record id="rule_fee_request_draft" model="ir.rule">
    <field name="name">Fee Request: Draft Records</field>
    <field name="model_id" ref="model_fee_request"/>
    <field name="groups" eval="[(4, ref('group_uni_fee_user'))]"/>
    <field name="domain_force">[
        '|',
        ('state', '!=', 'draft'),
        ('create_uid', '=', user.id)
    ]</field>
</record>
<!-- Managers see everything -->
<record id="rule_fee_request_manager" model="ir.rule">
    <field name="name">Fee Request: Manager Full Access</field>
    <field name="model_id" ref="model_fee_request"/>
    <field name="groups" eval="[(4, ref('group_uni_fee_manager'))]"/>
    <field name="domain_force">[(1, '=', 1)]</field>
</record>
```

### Anti-Patterns to Avoid
- **Using `states=` on buttons:** Deprecated in Odoo 17; use `invisible="state != '...'"` instead
- **Using AccessError for business logic:** Use UserError -- it shows a clean dialog to the user, not a permission-denied screen
- **Per-stage record rules:** Creates N*M rules that are hard to debug; use two-tier approach (draft vs non-draft)
- **Modifying state field in write() without context flag:** Creates infinite recursion when action methods call `self.write({'state': ...})`; action methods must use `self.with_context(_force_state=True).write(...)` or the guard must detect and pass through action-method-initiated writes
- **Putting approval guard outside audit wrapper:** Breaks the stacking contract; audit must capture state changes too

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| State field synthesis | Manual field dict construction | Preprocessor building from `approval.levels` spec | Edge cases: draft prepend, rejected append, duplicate detection, Selection ordering |
| Group reference resolution | Hardcoded XML IDs | `role` -> `{module}.group_{module}_{role}` lookup with optional `group` override | External group references need validation, role names vary per module |
| Button visibility conditions | Manual XML per button | Template loop over `approval_action_methods` list | Consistent invisible + groups attributes, version-aware (17 vs 18) |
| Write() stacking | Direct super() override | override_sources pattern + template conditionals | Multiple features (audit, approval, constraints, cache) share the write() method |

**Key insight:** The approval workflow is structurally parallel to the audit trail (Phase 38) -- a preprocessor enriches the spec, context keys feed template blocks, and write() stacking is managed through `override_sources`. The complexity is in the many moving parts (state field, N action methods, N buttons, 2 record rules, write guard, readonly locking) that must all be consistent with each other.

## Common Pitfalls

### Pitfall 1: StrictUndefined Crash on New Context Keys
**What goes wrong:** Adding `has_approval`, `approval_levels`, `approval_action_methods`, `lock_after`, `editable_fields` to template context without defaults causes StrictUndefined errors when rendering non-approval models.
**Why it happens:** Jinja2 StrictUndefined mode raises on any undefined variable access.
**How to avoid:** Add defaults in `_build_model_context`: `has_approval = model.get("has_approval", False)`, `approval_levels = model.get("approval_levels", [])`, etc. Gate ALL template blocks with `{% if has_approval %}`.
**Warning signs:** Smoke test with minimal spec (no approval) failing with UndefinedError.

### Pitfall 2: Write() Infinite Recursion from State Guard
**What goes wrong:** Action method calls `self.write({'state': 'next'})`, which hits the state guard and raises UserError.
**Why it happens:** The guard blocks ALL writes containing `state` in vals, including from action methods.
**How to avoid:** Action methods MUST write state using `self.with_context(_force_state=True).write({'state': ...})`. Template must generate this exact pattern. Both `_force_state` context flag AND `env.is_superuser()` bypass the guard.
**Warning signs:** Action methods raising "State transitions must use action buttons" error.

### Pitfall 3: Odoo 17 `states=` Deprecation
**What goes wrong:** Generating buttons with `states="submitted"` attribute instead of `invisible="state != 'submitted'"`.
**Why it happens:** CONTEXT.md mentions `states=` but Odoo 17 deprecated this in favor of `invisible=` expressions.
**How to avoid:** Template MUST use `invisible="{{ approval_state_field_name }} != '{{ from_state }}'"`. The existing codebase already follows this pattern (see import_wizard_form.xml.j2 and wizard trigger buttons).
**Warning signs:** Odoo 17 lint warnings about deprecated `states=` attribute.

### Pitfall 4: Approval Groups Not Coexisting with Phase 37 Record Rules
**What goes wrong:** Approval ir.rule entries conflict with Phase 37's ownership/department/company rules.
**Why it happens:** Multiple ir.rule records on the same model with different groups create unexpected additive/restrictive behavior.
**How to avoid:** Approval rules use `|` (OR) domain to be additive: either the record is non-draft OR the user is the creator. Manager rules use global `[(1,'=',1)]` domain. These coexist additively with Phase 37 rules.
**Warning signs:** Users unable to see records they should have access to.

### Pitfall 5: Missing needs_translate for UserError Messages
**What goes wrong:** Template generates `_("error message")` but `from odoo.tools.translate import _` is not imported.
**Why it happens:** The `needs_translate` flag is not updated to account for approval action methods.
**How to avoid:** Preprocessor must set `needs_translate = True` on models with approval (since action methods use `_()` for translatable error messages). Context builder must propagate this.
**Warning signs:** Python NameError on `_` when action methods run.

### Pitfall 6: State Field Conflict with Existing Field
**What goes wrong:** Model spec already has a manually defined `state` Selection field, and approval tries to inject another one.
**Why it happens:** Preprocessor doesn't check for existing state fields before synthesis.
**How to avoid:** Preprocessor must detect existing state/status fields and either (a) replace them with the approval-generated version or (b) raise a validation error if the existing field conflicts. The established pattern (renderer_context.py:72) already detects state fields.
**Warning signs:** Duplicate field definition in generated .py file.

## Code Examples

Verified patterns from the existing codebase:

### Preprocessor Pattern (from _process_audit_patterns)
```python
# Source: preprocessors.py:1036-1155
def _process_approval_patterns(spec: dict[str, Any]) -> dict[str, Any]:
    """Pre-process approval workflow configuration.

    For each model with approval block:
    1. Validates role references against security_roles
    2. Synthesizes state Selection field (draft + levels + terminal + optional rejected)
    3. Builds action method specs for each level transition
    4. Resolves group XML IDs (role-based or explicit override)
    5. Builds reject action spec (if reject_allowed_from specified)
    6. Sets lock_after, editable_fields for stage locking
    7. Sets approval-specific record_rule_scopes
    8. Adds "approval" to override_sources["write"]

    Returns a new spec dict. Pure function.
    """
    models = spec.get("models", [])
    approval_models = [m for m in models if m.get("approval")]
    if not approval_models:
        return spec

    module_name = spec["module_name"]
    security_roles = spec.get("security_roles", [])
    role_lookup = {r["name"]: r for r in security_roles}

    new_models = []
    for model in models:
        if not model.get("approval"):
            new_models.append(model)
            continue
        # ... enrichment logic following audit pattern

    return {**spec, "models": new_models}
```

### Context Keys Pattern (from _build_model_context)
```python
# Source: renderer_context.py:192-284 -- add after Phase 38 keys
# Phase 39: approval workflow context keys (defaults prevent StrictUndefined crashes)
has_approval = model.get("has_approval", False)
approval_levels = model.get("approval_levels", [])
approval_action_methods = model.get("approval_action_methods", [])
approval_reject_action = model.get("approval_reject_action", None)
approval_reset_action = model.get("approval_reset_action", None)
approval_state_field_name = model.get("approval_state_field_name", "state")
lock_after = model.get("lock_after", "draft")
editable_fields = model.get("editable_fields", [])
approval_record_rules = model.get("approval_record_rules", [])
on_reject = model.get("on_reject", "draft")
reject_allowed_from = model.get("reject_allowed_from", [])
```

### Write() Stacking with Approval Guard (Template)
```jinja2
{# Source: Follows model.py.j2 write() pattern at line 246+ #}
{% if has_write_override %}

    def write(self, vals):
{% if has_audit %}
        if self.env.context.get('_audit_skip'):
            {# ... audit skip path ... #}
            return result
        old_values = self._audit_read_old(vals)
{% endif %}
{% if has_approval %}
        # Approval state guard: block direct state modification
        if '{{ approval_state_field_name }}' in vals and not self.env.context.get('_force_state'):
            if not self.env.is_superuser():
                raise UserError(_("State transitions must use action buttons."))
{% endif %}
{% if is_cacheable %}
        self.clear_caches()
{% endif %}
        result = super().write(vals)
        {# ... constraints, audit log ... #}
        return result
{% endif %}
```

### Action Method Template Block
```jinja2
{# Approval action methods -- one per level #}
{% if has_approval %}
{% for action in approval_action_methods %}

    def {{ action.name }}(self):
        """{{ action.role_label }} approval: {{ action.from_state }} -> {{ action.to_state }}."""
        self.ensure_one()
        if not self.env.user.has_group('{{ action.group_xml_id }}'):
            raise UserError(_("Only the {{ action.role_label }} can approve at this stage."))
        if self.{{ approval_state_field_name }} != '{{ action.from_state }}':
            raise UserError(_(
                "Record must be in '{{ action.from_state_label }}' state to approve."
            ))
        self.with_context(_force_state=True).write({
            '{{ approval_state_field_name }}': '{{ action.to_state }}',
        })
{% endfor %}
{% if approval_reject_action %}

    def action_reject(self):
        """Reject and return to {{ on_reject }} state."""
        self.ensure_one()
        # Reject is allowed from specific stages only
        if self.{{ approval_state_field_name }} not in {{ reject_allowed_from }}:
            raise UserError(_("Rejection is not allowed from the current stage."))
        self.with_context(_force_state=True).write({
            '{{ approval_state_field_name }}': '{{ on_reject }}',
        })
{% endif %}
{% if approval_reset_action %}

    def action_reset_to_draft(self):
        """Reset record back to draft state."""
        self.ensure_one()
        self.with_context(_force_state=True).write({
            '{{ approval_state_field_name }}': 'draft',
        })
{% endif %}
{% endif %}
```

### Header Buttons Template Block
```jinja2
{# Source: Follows view_form.xml.j2 header pattern #}
{% if has_approval %}
{# Submit button (draft -> first level) #}
                    <button name="action_submit"
                            string="Submit"
                            type="object"
                            class="btn-primary"
                            invisible="{{ approval_state_field_name }} != 'draft'"/>
{% for action in approval_action_methods %}
                    <button name="{{ action.name }}"
                            string="{{ action.button_label }}"
                            type="object"
                            class="btn-primary"
                            invisible="{{ approval_state_field_name }} != '{{ action.from_state }}'"
                            groups="{{ action.group_xml_id }}"/>
{% endfor %}
{% if approval_reject_action %}
                    <button name="action_reject"
                            string="Reject"
                            type="object"
                            class="btn-danger"
                            invisible="{{ approval_state_field_name }} not in {{ reject_allowed_from }}"
                            groups="{{ approval_reject_action.group_xml_id }}"/>
{% endif %}
{% if approval_reset_action %}
                    <button name="action_reset_to_draft"
                            string="Reset to Draft"
                            type="object"
                            invisible="{{ approval_state_field_name }} not in ['{{ on_reject }}']"/>
{% endif %}
{% endif %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `attrs="{'invisible': [('state','=','draft')]}"` | `invisible="state == 'draft'"` | Odoo 17.0 | All button/field visibility must use new syntax |
| `states="draft,confirmed"` on buttons/fields | `invisible="state not in ('draft', 'confirmed')"` | Odoo 17.0 | Button visibility via `states=` is deprecated |
| Odoo workflow engine (wkf) | Python action methods on model | Odoo 11.0 | No built-in workflow engine; state machines are manual |
| `groups=` on `<field>` elements (17.0) | `groups=` attribute removed from fields (18.0) | Odoo 18.0 | 18.0 template must not use `groups=` on field declarations |

**Deprecated/outdated:**
- `states=` attribute: Replaced by `invisible=` expressions in Odoo 17.0+
- `attrs=` attribute: Replaced by direct `invisible=`, `readonly=`, `required=` attributes in Odoo 17.0+
- Odoo workflow engine: Removed in Odoo 11; state machines are now pure Python

## Open Questions

1. **Submit button generation**
   - What we know: `draft` is auto-prepended, the first level state (e.g., `submitted`) is the first transition target.
   - What's unclear: Should the submit action be generated as a separate `action_submit` method or as part of the first level's action method? The spec format implies there should be a `draft -> first_level_state` transition.
   - Recommendation: Generate `action_submit()` as a dedicated method gated by the role of the first level. The submit button is visible only in `draft` state.

2. **Reject button group assignment**
   - What we know: Reject is allowed from specific stages (`reject_allowed_from`).
   - What's unclear: Which group should gate the reject button? The approver at the current stage, or a combined set of all approver groups for reject-allowed stages?
   - Recommendation: The reject button should be visible to users who have ANY of the approver groups for stages in `reject_allowed_from`. Template can use the current-stage approver's group since the button is only visible when `state in reject_allowed_from`.

3. **Interaction between lock_after and readonly template**
   - What we know: Existing template already has `readonly="state != 'draft'"` on sequence fields.
   - What's unclear: How to conditionally extend this to all non-editable fields after `lock_after` stage without breaking the existing readonly logic.
   - Recommendation: Add `approval_readonly_expr` to context (e.g., `"state != 'draft'"`), and use it in field rendering: `readonly="{{ approval_readonly_expr }}"` for non-editable fields. `editable_fields` are exempt.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `python/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest tests/test_preprocessors.py -x -q` |
| Full suite command | `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BIZL-01a | Preprocessor enriches approval model with state Selection, action methods, record rules | unit | `cd python && python -m pytest tests/test_preprocessors.py -k "approval" -x` | Wave 0 |
| BIZL-01b | Non-approval model gets has_approval=False defaults in context | unit | `cd python && python -m pytest tests/test_renderer.py -k "approval_context_default" -x` | Wave 0 |
| BIZL-01c | Approval model context has all required keys | unit | `cd python && python -m pytest tests/test_renderer.py -k "approval_context_keys" -x` | Wave 0 |
| BIZL-01d | Rendered model.py has action methods with has_group + UserError | integration | `cd python && python -m pytest tests/test_renderer.py -k "approval_action_method" -x` | Wave 0 |
| BIZL-01e | Rendered view_form.xml has header buttons with invisible + groups | integration | `cd python && python -m pytest tests/test_renderer.py -k "approval_header_button" -x` | Wave 0 |
| BIZL-01f | Rendered model.py has write() state guard | integration | `cd python && python -m pytest tests/test_renderer.py -k "approval_write_guard" -x` | Wave 0 |
| BIZL-01g | render_module with approval completes without StrictUndefined crash | smoke | `cd python && python -m pytest tests/test_renderer.py -k "approval_smoke" -x` | Wave 0 |
| BIZL-01h | render_module without approval still works (no regression) | smoke | `cd python && python -m pytest tests/test_renderer.py -k "no_approval_regression" -x` | Wave 0 |
| BIZL-01i | Record rules generated for approval models | integration | `cd python && python -m pytest tests/test_renderer.py -k "approval_record_rules" -x` | Wave 0 |
| BIZL-01j | Preprocessor validates roles exist in security_roles | unit | `cd python && python -m pytest tests/test_preprocessors.py -k "approval_role_validation" -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest tests/test_preprocessors.py tests/test_renderer.py -x -q`
- **Per wave merge:** `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_preprocessors.py` -- add `TestApprovalPreprocessor` class (approval enrichment, validation, edge cases)
- [ ] `tests/test_renderer.py` -- add `TestApprovalIntegration` class (context defaults, template rendering, smoke tests)
- [ ] No framework install needed -- pytest already configured

## Sources

### Primary (HIGH confidence)
- Existing codebase: `preprocessors.py` (lines 927-1155) -- security and audit preprocessor patterns
- Existing codebase: `renderer_context.py` (lines 21-284) -- context builder with Phase 38 keys
- Existing codebase: `renderer.py` (lines 671-745) -- render_module pipeline with preprocessor chain
- Existing codebase: `model.py.j2` (17.0, lines 246-340) -- write() override with audit wrapper
- Existing codebase: `view_form.xml.j2` (17.0, lines 11-37) -- header section with statusbar
- Existing codebase: `record_rules.xml.j2` -- ir.rule template structure
- Existing codebase: `test_renderer.py` (lines 4202-4582) -- audit integration test patterns
- Existing codebase: `test_preprocessors.py` (lines 89-497) -- audit preprocessor test patterns

### Secondary (MEDIUM confidence)
- [Odoo 17 states= deprecation](https://www.odoo.com/forum/help-1/since-170-the-attrs-and-states-attributes-are-no-longer-used-239190) -- confirmed states= replaced by invisible= in Odoo 17
- [Odoo 17 view architectures](https://www.odoo.com/documentation/17.0/developer/reference/user_interface/view_architectures.html) -- official docs on form header button attributes
- [ir.rule domain_force patterns](https://odoo-development.readthedocs.io/en/latest/odoo/models/ir.rule.html) -- record rule domain patterns

### Tertiary (LOW confidence)
- [Odoo ir.rule state-based filtering](https://www.odoo.com/forum/help-1/can-i-create-irrule-that-lets-groups-have-only-specific-permissions-based-on-state-185373) -- community forum on state-based ir.rule (needs validation against Odoo source)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- uses only existing project infrastructure, no new dependencies
- Architecture: HIGH -- follows established Phase 37/38 preprocessor + template patterns exactly
- Pitfalls: HIGH -- most pitfalls derive from known issues (StrictUndefined, write recursion, states= deprecation) already encountered in prior phases
- Template patterns: HIGH -- based on existing working code in view_form.xml.j2 and model.py.j2
- Record rules: MEDIUM -- two-tier approach is simpler than per-stage but additive coexistence with Phase 37 rules needs careful testing

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable -- internal tooling, no external API changes expected)
