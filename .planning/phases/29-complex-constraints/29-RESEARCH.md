# Phase 29: Complex Constraints - Research

**Researched:** 2026-03-05
**Domain:** Odoo constraint patterns -- cross-model validation, temporal constraints, capacity constraints, create()/write() overrides, @api.constrains, ValidationError
**Confidence:** HIGH

## Summary

Phase 29 adds a `constraints` section to the spec format that enables three types of complex validation logic: (1) cross-model constraints that query related models during create/write (e.g., "enrollment count cannot exceed course capacity"), (2) temporal constraints that compare date/datetime fields within the same record (e.g., "end_date must be after start_date"), and (3) capacity constraints that count related records and enforce maximums (e.g., "max 30 students per section").

The current template already supports two constraint mechanisms: `sql_constraints` (rendered as `_sql_constraints` class attribute) and `constrained_fields` (fields with a `constrains` key, rendered as `@api.constrains` methods with TODO stubs). Phase 29 extends this by adding a spec-level `constraints` section that is processed by a new preprocessor (`_process_constraints()`) to enrich models with fully-implemented constraint methods -- not just stubs but real validation logic with proper `_()` translated error messages.

The key Odoo pattern distinction is: temporal constraints (same-record field comparisons) use `@api.constrains` decorators, while cross-model and capacity constraints require `create()`/`write()` overrides because `@api.constrains` does not support dotted field names (relational field paths) and only triggers when the decorated fields are included in the create/write call. The preprocessor must classify each constraint by type and generate the appropriate pattern.

**Primary recommendation:** Add a `constraints` section to the spec format at the root level (alongside `models`, `relationships`, `computation_chains`). Implement `_process_constraints()` as a preprocessor that classifies constraints by type (temporal, cross-model, capacity) and enriches model dicts with constraint method metadata. Extend the Jinja2 `model.py.j2` template (both 17.0 and 18.0) to render three patterns: `@api.constrains` for temporal, `create()` override for cross-model/capacity on create, `write()` override for cross-model/capacity on write. Wire into `render_module()` after `_process_computation_chains()`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SPEC-04 | Spec supports `constraints` section with cross-model validation, temporal constraints, and capacity constraints generating `create()`/`write()` overrides with `ValidationError` | `constraints` spec format with type classification, `_process_constraints()` preprocessor, template extensions for `@api.constrains` (temporal), `create()`/`write()` overrides (cross-model, capacity), `_()` translated error messages |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | (existing) | Template rendering -- template changes needed for constraint methods | Existing model.py.j2 already renders `@api.constrains` stubs; needs extension for create/write overrides |
| Python 3.12 | (existing) | All processing logic in renderer.py | Project requirement |

### Supporting
No new libraries needed. This is spec-processing logic + template extension using existing infrastructure.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Template-rendered constraint methods | AST-based code injection | Template approach is simpler, consistent with project patterns; AST injection would be over-engineering for generated code |
| Preprocessor enriching model dicts | Inline logic in `_build_model_context()` | Preprocessor is cleaner because constraints reference cross-model relationships; `_build_model_context()` operates on one model at a time |
| Three constraint types (temporal, cross-model, capacity) | Single generic constraint type | Three types map to distinct Odoo patterns (`@api.constrains` vs `create()`/`write()` override); conflating them produces incorrect code |

## Architecture Patterns

### Spec Format Design

The `constraints` section sits at the spec root level alongside `models`, `relationships`, `computation_chains`, and `wizards`:

```json
{
  "module_name": "university",
  "models": [...],
  "constraints": [
    {
      "type": "temporal",
      "model": "university.course",
      "fields": ["start_date", "end_date"],
      "condition": "end_date > start_date",
      "message": "End date must be after start date."
    },
    {
      "type": "cross_model",
      "model": "university.enrollment",
      "related_model": "university.course",
      "related_field": "enrollment_ids",
      "check_field": "max_students",
      "condition": "count <= capacity",
      "message": "Enrollment count cannot exceed course capacity of {capacity}."
    },
    {
      "type": "capacity",
      "model": "university.section",
      "count_field": "student_ids",
      "max_value": 30,
      "message": "A section cannot have more than {max} students."
    }
  ]
}
```

**Key design decisions:**

1. `type` distinguishes the three constraint patterns: `temporal`, `cross_model`, `capacity`
2. `model` identifies which model the constraint is applied to
3. `fields` (temporal) lists the fields passed to `@api.constrains` decorator
4. `related_model` + `related_field` + `check_field` (cross-model) identify the cross-model lookup path
5. `count_field` + `max_value` (capacity) identify the One2many to count and the limit
6. `message` is the user-facing error string, supporting `{placeholders}` for dynamic values, always wrapped in `_()`
7. Each constraint generates a uniquely named method (e.g., `_check_end_date_after_start_date`, `_check_enrollment_capacity`)

### Pattern 1: Temporal Constraint (same-record date comparison)

**What:** An `@api.constrains` method comparing date/datetime fields within the same record.

**When to use:** For constraints like "end_date must be after start_date", "deadline must be in the future".

**Odoo pattern:**
```python
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class Course(models.Model):
    _name = "university.course"

    start_date = fields.Date()
    end_date = fields.Date()

    @api.constrains("start_date", "end_date")
    def _check_date_order(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(
                    _("End date must be after start date.")
                )
```

**Critical detail:** Both field values must be checked for truthiness before comparison. Odoo allows `False` as the default for Date fields (meaning "not set"), and comparing `False < date_obj` raises a `TypeError`.

### Pattern 2: Cross-Model Constraint (query related model)

**What:** A `create()`/`write()` override that queries a related model to validate a business rule.

**When to use:** For constraints like "enrollment count cannot exceed course capacity". `@api.constrains` cannot be used because it does not support dotted field names.

**Odoo pattern:**
```python
from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class Enrollment(models.Model):
    _name = "university.enrollment"

    course_id = fields.Many2one("university.course", required=True)
    student_id = fields.Many2one("university.student", required=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_enrollment_capacity()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "course_id" in vals:
            self._check_enrollment_capacity()
        return result

    def _check_enrollment_capacity(self):
        for rec in self:
            course = rec.course_id
            enrollment_count = self.env["university.enrollment"].search_count([
                ("course_id", "=", course.id),
            ])
            if enrollment_count > course.max_students:
                raise ValidationError(
                    _("Enrollment count cannot exceed course capacity of %s.",
                      course.max_students)
                )
```

**Critical details:**
- Use `@api.model_create_multi` with `vals_list` (not `@api.model` with single `vals`) -- this is the modern Odoo pattern
- Call `super().create()` FIRST, then validate on the created records (post-create validation)
- In `write()`, only validate when the relevant field changes (`if "course_id" in vals`)
- The validation method is extracted to a private `_check_*` method so both `create()` and `write()` can call it
- Use `search_count()` for efficient counting instead of `search()` + `len()`

### Pattern 3: Capacity Constraint (count related records)

**What:** A `create()`/`write()` override that counts related records and enforces a maximum.

**When to use:** For constraints like "max 30 students per section". This is similar to cross-model but the max is a fixed value rather than a field on the related model.

**Odoo pattern:**
```python
class Section(models.Model):
    _name = "university.section"

    student_ids = fields.One2many("university.student.section", "section_id")
    max_students = fields.Integer(default=30)

    def write(self, vals):
        result = super().write(vals)
        self._check_section_capacity()
        return result

    def _check_section_capacity(self):
        for rec in self:
            if len(rec.student_ids) > rec.max_students:
                raise ValidationError(
                    _("A section cannot have more than %s students.",
                      rec.max_students)
                )
```

**Note:** When the max is a field on the model itself (like `max_students`), it could also be implemented as `@api.constrains("student_ids")`. However, `@api.constrains` on One2many fields only triggers when the One2many is modified via the parent form, not when child records are created/deleted independently. For robustness, the `create()`/`write()` override on the CHILD model (the one being created) is the reliable pattern.

### Pattern 4: Constraint Preprocessor

**What:** A `_process_constraints()` function that enriches model dicts with constraint metadata consumed by templates.

**When to use:** Called in `render_module()` after `_process_computation_chains()` but before model rendering.

**Implementation approach:**

```python
def _process_constraints(spec: dict[str, Any]) -> dict[str, Any]:
    """Enrich model specs with constraint method metadata from constraints section.

    For each constraint:
    1. Classify by type (temporal, cross_model, capacity)
    2. Locate target model in spec
    3. Inject constraint metadata into model dict

    Returns a new spec dict with enriched models. Pure function.
    """
    constraints = spec.get("constraints", [])
    if not constraints:
        return spec

    # Group constraints by model
    model_constraints: dict[str, list[dict]] = {}
    for constraint in constraints:
        model_name = constraint["model"]
        model_constraints.setdefault(model_name, []).append(constraint)

    # Deep-copy models and enrich with constraint metadata
    new_models = []
    for model in spec.get("models", []):
        mc = model_constraints.get(model["name"], [])
        if not mc:
            new_models.append(model)
            continue
        new_models.append({
            **model,
            "complex_constraints": mc,
        })

    return {**spec, "models": new_models}
```

### Pattern 5: Template Extension for Constraint Methods

**What:** Extend `model.py.j2` to render three constraint patterns based on type.

The template needs new blocks after the existing `constrained_fields` loop:

```jinja2
{# Phase 29: Complex constraints #}
{% for constraint in complex_constraints %}
{% if constraint.type == 'temporal' %}

    @api.constrains({% for f in constraint.fields %}"{{ f }}"{% if not loop.last %}, {% endif %}{% endfor %})
    def _check_{{ constraint.name }}(self):
        for rec in self:
            if {{ constraint.check_expr }}:
                raise ValidationError(
                    _("{{ constraint.message }}")
                )
{% elif constraint.type == 'cross_model' %}

    def _check_{{ constraint.name }}(self):
        for rec in self:
            {{ constraint.check_body | indent(12) }}
{% elif constraint.type == 'capacity' %}

    def _check_{{ constraint.name }}(self):
        for rec in self:
            {{ constraint.check_body | indent(12) }}
{% endif %}
{% endfor %}
{% if has_create_override %}

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
{% for constraint in create_constraints %}
        records._check_{{ constraint.name }}()
{% endfor %}
        return records
{% endif %}
{% if has_write_override %}

    def write(self, vals):
        result = super().write(vals)
{% for constraint in write_constraints %}
{% if constraint.write_trigger_fields %}
        if any(f in vals for f in {{ constraint.write_trigger_fields }}):
{% endif %}
            self._check_{{ constraint.name }}()
{% endfor %}
        return result
{% endif %}
```

### Recommended Project Structure

No new files needed. All changes go in existing files:

```
python/src/odoo_gen_utils/
    renderer.py          # Add: _process_constraints()
                         # Modify: render_module(), _build_model_context()

python/src/odoo_gen_utils/templates/17.0/
    model.py.j2          # Add: complex constraint blocks, create/write overrides

python/src/odoo_gen_utils/templates/18.0/
    model.py.j2          # Same additions as 17.0

python/tests/
    test_renderer.py     # Add: TestProcessConstraints
    test_render_stages.py # Add: TestRenderModelsComplexConstraints
```

### Anti-Patterns to Avoid

- **Using `@api.constrains` for cross-model validation:** `@api.constrains` does NOT support dotted field names. It silently ignores them. Cross-model constraints MUST use create/write overrides.
- **Pre-create validation in create():** Call `super().create()` FIRST, then validate. This is because the record needs to exist in the database for `search_count()` to include it. Pre-create validation would under-count by 1.
- **Unconditional validation in write():** In `write()`, only call the constraint check when the relevant field is being modified (check `if "field_name" in vals`). Otherwise, every write to any field triggers expensive cross-model queries.
- **Mutating model dicts in-place:** Follow project immutability convention -- `_process_constraints()` returns a new spec.
- **Single create/write override per constraint:** If a model has multiple cross-model/capacity constraints, they should share a single `create()` and single `write()` override that calls each check method. Multiple create/write overrides would clobber each other.
- **Forgetting `_()` on error messages:** All ValidationError messages MUST be wrapped in `_()` for i18n compliance. This is an OCA quality requirement.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Constraint type classification | Runtime type inference from spec fields | Explicit `type` key in constraint spec | Unambiguous, self-documenting, no guessing |
| `_()` translation wrapping | Manual string concatenation | Jinja2 template rendering with `_()` wrapper | Template ensures consistent formatting |
| Constraint method naming | Custom slug generation | `_check_{constraint_name}` convention | Matches Odoo convention, predictable names |

**Key insight:** The preprocessor should do the heavy lifting of classifying constraints and generating method metadata (name, body, trigger fields). The template should be a thin rendering layer, not contain business logic for constraint classification.

## Common Pitfalls

### Pitfall 1: @api.constrains Ignoring Dotted Names
**What goes wrong:** Developer uses `@api.constrains("course_id.max_students")` expecting it to trigger when the related field changes. Odoo silently ignores dotted names.
**Why it happens:** The `@api.constrains` decorator only accepts simple field names.
**How to avoid:** Cross-model constraints MUST use `create()`/`write()` overrides. The preprocessor must enforce this by classifying constraint type correctly.
**Warning signs:** Constraint never fires; no error, no warning, just silent bypass.

### Pitfall 2: Pre-Create Validation Under-Counts
**What goes wrong:** Capacity check runs BEFORE `super().create()`, so the new record is not yet in the database. `search_count()` returns N instead of N+1, and the capacity check passes when it should fail.
**Why it happens:** Developer validates before the database insert.
**How to avoid:** Always call `super().create()` FIRST, then run validation on the returned records. If validation fails, the transaction will be rolled back automatically.
**Warning signs:** Capacity of N allows N+1 records. Off-by-one errors in constraint checks.

### Pitfall 3: Write() Override Triggers on Every Field Change
**What goes wrong:** Every `write()` call triggers an expensive `search_count()` query, even when irrelevant fields are being updated (e.g., updating a description field triggers a capacity check).
**Why it happens:** The `write()` override does not check which fields are actually being modified.
**How to avoid:** Check `if "relevant_field" in vals:` before calling the constraint check in `write()`. Only trigger when the field that affects the constraint is being written.
**Warning signs:** Performance degradation on bulk write operations.

### Pitfall 4: Multiple create()/write() Overrides Clobbering Each Other
**What goes wrong:** Two constraint types on the same model each generate their own `create()` method. Only the last one survives in the template output.
**Why it happens:** Template generates multiple `def create()` blocks.
**How to avoid:** Generate a SINGLE `create()` override and a SINGLE `write()` override per model, calling all relevant constraint check methods from within each.
**Warning signs:** First constraint works, second silently does not.

### Pitfall 5: Date Comparison with False/None
**What goes wrong:** `rec.end_date < rec.start_date` raises `TypeError` when one of the dates is `False` (not set).
**Why it happens:** Odoo Date fields default to `False`, not `None` or a date object.
**How to avoid:** Always check `if rec.start_date and rec.end_date` before comparing. The generated temporal constraint template must include this guard.
**Warning signs:** `TypeError: '<' not supported between instances of 'bool' and 'datetime.date'` when creating records with unfilled date fields.

### Pitfall 6: ValidationError Without Translation
**What goes wrong:** Error message is a plain string `"End date must be after start date"` without `_()` wrapper.
**Why it happens:** Template does not wrap the message.
**How to avoid:** Template must render `_("message text")`. The `from odoo.tools.translate import _` import must be included when any constraint exists.
**Warning signs:** pylint-odoo E8501 warning; OCA CI rejects the module.

## Code Examples

### Temporal Constraint: Date Comparison (Generated Output)

```python
# Source: Odoo 17.0 constraints tutorial + ORM docs
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class UniversityCourse(models.Model):
    _name = "university.course"
    _description = "Course"

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    @api.constrains("start_date", "end_date")
    def _check_date_order(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(
                    _("End date must be after start date.")
                )
```

### Cross-Model Constraint: Enrollment Capacity (Generated Output)

```python
# Source: Odoo ORM create/write override pattern
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class UniversityEnrollment(models.Model):
    _name = "university.enrollment"
    _description = "Enrollment"

    course_id = fields.Many2one(
        comodel_name="university.course",
        string="Course",
        required=True,
    )
    student_id = fields.Many2one(
        comodel_name="university.student",
        string="Student",
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_enrollment_capacity()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "course_id" in vals:
            self._check_enrollment_capacity()
        return result

    def _check_enrollment_capacity(self):
        for rec in self:
            course = rec.course_id
            enrollment_count = self.env["university.enrollment"].search_count([
                ("course_id", "=", course.id),
            ])
            if course.max_students and enrollment_count > course.max_students:
                raise ValidationError(
                    _("Enrollment count cannot exceed course capacity of %s.",
                      course.max_students)
                )
```

### Capacity Constraint: Fixed Maximum (Generated Output)

```python
# Source: Odoo ORM pattern for record count enforcement
class UniversitySectionEnrollment(models.Model):
    _name = "university.section.enrollment"
    _description = "Section Enrollment"

    section_id = fields.Many2one(
        comodel_name="university.section",
        string="Section",
        required=True,
    )
    student_id = fields.Many2one(
        comodel_name="university.student",
        string="Student",
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_section_capacity()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "section_id" in vals:
            self._check_section_capacity()
        return result

    def _check_section_capacity(self):
        for rec in self:
            section = rec.section_id
            student_count = self.env["university.section.enrollment"].search_count([
                ("section_id", "=", section.id),
            ])
            if student_count > 30:
                raise ValidationError(
                    _("A section cannot have more than %s students.", 30)
                )
```

### Spec Example: Full Constraints Section

```json
{
  "module_name": "university",
  "depends": ["base", "mail"],
  "models": [
    {
      "name": "university.course",
      "fields": [
        {"name": "name", "type": "Char", "required": true},
        {"name": "start_date", "type": "Date"},
        {"name": "end_date", "type": "Date"},
        {"name": "max_students", "type": "Integer", "default": "50"}
      ]
    },
    {
      "name": "university.enrollment",
      "fields": [
        {"name": "course_id", "type": "Many2one", "comodel_name": "university.course", "required": true},
        {"name": "student_id", "type": "Many2one", "comodel_name": "university.student", "required": true}
      ]
    }
  ],
  "constraints": [
    {
      "type": "temporal",
      "model": "university.course",
      "name": "date_order",
      "fields": ["start_date", "end_date"],
      "condition": "end_date < start_date",
      "message": "End date must be after start date."
    },
    {
      "type": "cross_model",
      "model": "university.enrollment",
      "name": "enrollment_capacity",
      "trigger_fields": ["course_id"],
      "related_model": "university.enrollment",
      "count_domain_field": "course_id",
      "capacity_model": "university.course",
      "capacity_field": "max_students",
      "message": "Enrollment count cannot exceed course capacity of %s."
    }
  ]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `constrained_fields` with TODO stubs | Fully implemented constraint methods from `constraints` section | Phase 29 (this phase) | Generated constraints are functional, not just stubs |
| No cross-model validation | `create()`/`write()` overrides querying related models | Phase 29 (this phase) | Generator produces validation that references other models |
| No temporal constraint generation | `@api.constrains` with date comparison + False guards | Phase 29 (this phase) | Date validation generated from spec |
| No capacity enforcement | Count-based validation in create/write | Phase 29 (this phase) | Enrollment/section limits enforced automatically |

**Important note:** The existing `constrained_fields` mechanism (fields with a `constrains` key) should continue to work alongside the new `constraints` section. The new section generates fully-implemented methods; the old mechanism generates stubs. They are complementary, not replacements.

## Open Questions

1. **Should the preprocessor generate the full Python code body or structured metadata?**
   - What we know: Phase 26 (monetary) and Phase 28 (chains) used metadata enrichment -- the preprocessor adds keys to field/model dicts, and the template renders them. This keeps code generation in the template layer.
   - What's unclear: Constraint check bodies are more complex than field definitions. Should the preprocessor generate the full method body as a string, or pass structured data to the template?
   - Recommendation: Use structured metadata for the check expression/body. The preprocessor should generate template-friendly data (e.g., `check_expr`, `count_domain`, `capacity_ref`), and the template should render the Python code. This keeps the preprocessor testable and the template inspectable. For cross-model/capacity constraints, generate the body as a pre-rendered string that the template inserts with `{{ constraint.check_body }}`.

2. **Should capacity constraints support dynamic max values (field) vs static (integer)?**
   - What we know: Some constraints have a fixed max (always 30), others reference a field on the related model (course.max_students).
   - Recommendation: Support both. If `max_field` is provided, use the related model's field. If `max_value` is provided, use the static value. The preprocessor should handle both cases.

3. **How should `_()` translation work with dynamic values?**
   - What we know: Odoo `_()` supports `%s` positional formatting: `_("Cannot exceed %s students.", max_val)`.
   - Recommendation: Use `%s` placeholder in the message string, with the dynamic value as a second argument to `_()`. This is the standard Odoo i18n pattern.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `python/pyproject.toml` |
| Quick run command | `cd /home/inshal-rauf/Odoo_module_automation/python && .venv/bin/python -m pytest tests/test_renderer.py -x -q -k "Constraint"` |
| Full suite command | `cd /home/inshal-rauf/Odoo_module_automation/python && .venv/bin/python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPEC-04a | Cross-model constraint generates `create()` override with `search_count` + `ValidationError` | unit | `pytest tests/test_renderer.py::TestProcessConstraints::test_cross_model_generates_create_override -x` | Wave 0 |
| SPEC-04b | Cross-model constraint generates `write()` override with field-conditional check | unit | `pytest tests/test_renderer.py::TestProcessConstraints::test_cross_model_generates_write_override -x` | Wave 0 |
| SPEC-04c | Temporal constraint generates `@api.constrains` with date comparison | unit | `pytest tests/test_renderer.py::TestProcessConstraints::test_temporal_generates_api_constrains -x` | Wave 0 |
| SPEC-04d | Capacity constraint generates count + max validation in create/write | unit | `pytest tests/test_renderer.py::TestProcessConstraints::test_capacity_generates_count_check -x` | Wave 0 |
| SPEC-04e | All constraint methods include `_()` translated error messages | unit | `pytest tests/test_renderer.py::TestProcessConstraints::test_messages_have_translation -x` | Wave 0 |
| SPEC-04f | Spec without `constraints` section works unchanged (backward compat) | unit | `pytest tests/test_renderer.py::TestProcessConstraints::test_no_constraints_passthrough -x` | Wave 0 |
| SPEC-04g | Preprocessor does not mutate input spec | unit | `pytest tests/test_renderer.py::TestProcessConstraints::test_does_not_mutate_input -x` | Wave 0 |
| SPEC-04h | Multiple constraints on same model share single create/write override | unit | `pytest tests/test_renderer.py::TestProcessConstraints::test_multiple_constraints_single_override -x` | Wave 0 |
| SPEC-04i | Generated cross-model constraint renders correct Python in model.py | integration | `pytest tests/test_render_stages.py::TestRenderModelsComplexConstraints::test_cross_model_constraint_output -x` | Wave 0 |
| SPEC-04j | Generated temporal constraint renders correct Python in model.py | integration | `pytest tests/test_render_stages.py::TestRenderModelsComplexConstraints::test_temporal_constraint_output -x` | Wave 0 |
| SPEC-04k | Generated capacity constraint renders correct Python in model.py | integration | `pytest tests/test_render_stages.py::TestRenderModelsComplexConstraints::test_capacity_constraint_output -x` | Wave 0 |
| SPEC-04l | Backward compat: spec without constraints renders identically | integration | `pytest tests/test_render_stages.py::TestRenderModelsComplexConstraints::test_backward_compat -x` | Wave 0 |
| SPEC-04m | Template imports ValidationError and _ when constraints present | integration | `pytest tests/test_render_stages.py::TestRenderModelsComplexConstraints::test_imports_validation_error -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /home/inshal-rauf/Odoo_module_automation/python && .venv/bin/python -m pytest tests/test_renderer.py tests/test_render_stages.py -x -q -k "Constraint"`
- **Per wave merge:** `cd /home/inshal-rauf/Odoo_module_automation/python && .venv/bin/python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_renderer.py::TestProcessConstraints` -- constraint preprocessor unit tests (8 tests)
- [ ] `tests/test_render_stages.py::TestRenderModelsComplexConstraints` -- end-to-end rendering tests (5 tests)
- [ ] Template changes in both `17.0/model.py.j2` and `18.0/model.py.j2` for constraint rendering

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `renderer.py` -- existing `_process_relationships()`, `_process_computation_chains()` preprocessor patterns; `_build_model_context()` constraint handling (lines 530-540); `constrained_fields` and `has_constraints` context keys
- Codebase analysis: `model.py.j2` (17.0 + 18.0) -- existing `@api.constrains` rendering (lines 159-166), `_sql_constraints` rendering (lines 126-137), `ValidationError` import (lines 3-5)
- [Odoo 17.0 ORM API docs](https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html) -- `@api.constrains` limitations (no dotted names), `create()`/`write()` override signatures, `@api.model_create_multi`
- [Odoo Model Constraints guide](https://odoo-development.readthedocs.io/en/latest/dev/py/constraints.html) -- Python vs SQL constraints, `@api.constrains` decorator behavior, ValidationError pattern

### Secondary (MEDIUM confidence)
- [Odoo 17.0 Constraints Tutorial](https://www.odoo.com/documentation/17.0/developer/tutorials/server_framework_101/10_constraints.html) -- Official tutorial with examples of `@api.constrains` and SQL constraints
- [Odoo 19.0 ORM API docs](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html) -- Confirmed that `@api.constrains` still does not support dotted names in latest version; create/write override remains the pattern for cross-model validation
- [Odoo Forum: Date validation](https://www.odoo.com/forum/help-1/date-validation-end-date-start-end-134226) -- Community validation of date comparison pattern with False guards

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, extends existing template + preprocessor patterns, well-documented Odoo constraint API
- Architecture: HIGH -- follows established preprocessor pattern from Phase 27/28, constraint mechanisms well-understood in Odoo ecosystem
- Pitfalls: HIGH -- 6 pitfalls documented from Odoo ORM limitations (dotted names, pre-create counting, False date comparisons) and template engineering (single override, translation wrapping)

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain -- Odoo constraint API unchanged since v10, create/write override pattern is fundamental ORM)
