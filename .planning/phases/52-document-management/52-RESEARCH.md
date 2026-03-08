# Phase 52: Document Management - Research

**Researched:** 2026-03-08
**Domain:** Odoo document lifecycle generation, Binary storage, verification workflow, version gating
**Confidence:** HIGH

## Summary

Phase 52 generates a complete document management subsystem when `document_management: true` appears in a spec. The preprocessor follows the GENERATION pattern established by `academic_calendar.py` (Phase 50): it builds two complete model dicts (`document.type` and `document.document`) and appends them to the spec's models list. The verification workflow is self-contained (three states: pending/verified/rejected) and does NOT reuse the approval preprocessor from Phase 39. Version tracking uses a linked-list on the same model (no separate model). The Odoo 18 `discuss.channel` version gate is a template-level Jinja2 conditional injected via a `VERSION_GATES` dict in the render context.

The primary technical challenge is that the current model templates do NOT render several field attributes needed by document models: `attachment=True`, `readonly`, `copy`, `tracking`, `size`, `related`, and `model_field`. The preprocessor can generate correct field dicts, but the templates must be extended to render these attributes -- or the document preprocessor must use `complex_constraints` with `check_body` for the action methods and rely on the existing template's generic field rendering (which drops those attributes silently). The recommended approach is to add the missing field kwargs to the generic field template branch, as this benefits all future preprocessors too.

**Primary recommendation:** Follow the `academic_calendar.py` GENERATION pattern exactly. Build `_build_document_type_model()` and `_build_document_document_model()` helpers. Use `doc_*` prefixed constraint types for action methods (`doc_action_verify`, `doc_action_reject`, `doc_action_reset`, `doc_action_upload_new_version`) and `doc_file_validation` for the file constraint. Extend the model template's generic field branch to render `attachment`, `readonly`, `copy`, `tracking`, `size`, and `model_field` kwargs. Inject `VERSION_GATES` into `renderer_context.py`'s `_build_module_context()`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Two models generated: `document.type` (classification lookup) + `document.document` (actual files)
- GENERATION pattern (like academic_calendar) -- preprocessor creates complete model dicts
- No separate `document.version` model -- version tracking uses linked list on `document.document`
- **document.type** fields: name (Char, required), code (Char, required) + SQL UNIQUE, required_for (Selection: admission/enrollment/graduation/employment/always, default='admission'), max_file_size (Integer, default=5 MB), allowed_mime_types (Char, comma-separated default), sequence (Integer, default=10), active (Boolean, default=True), description (Text), _order = 'sequence, name'
- **document.document** fields: name (Char, required, tracking), document_type_id (Many2one to document.type, required), file (Binary, required, attachment=True), filename (Char), mime_type (Char, readonly), file_size (Integer, readonly, "File Size (KB)"), upload_date (Datetime, default=now, readonly), res_model (Char, index=True), res_id (Many2oneReference, model_field='res_model'), verification_state (Selection: pending/verified/rejected, default='pending', tracking), verified_by (Many2one res.users, readonly), verified_date (Datetime, readonly), rejection_reason (Text), version (Integer, default=1, readonly), previous_version_id (Many2one document.document, readonly), is_latest (Boolean, default=True, index=True), notes (Text), _inherit = ['mail.thread'], _order = 'create_date desc'
- Polymorphic res_model/res_id ownership (like ir.attachment), NOT fixed Many2one
- `attachment=True` on Binary stores files in filestore (not PostgreSQL)
- File validation constraint checks max_file_size and allowed_mime_types from document_type_id
- Separate `verification_state` field -- does NOT reuse approval preprocessor (Phase 39)
- Verification is binary (authentic or not), not multi-level approval chain
- Three states: pending -> verified or rejected
- Three action methods: action_verify(), action_reject(), action_reset_to_pending() with group checks
- Security roles: viewer (r), uploader (cru), verifier (cru), manager (crud)
- Version tracking via linked list: version (Integer), previous_version_id (Many2one to self), is_latest (Boolean, indexed)
- action_upload_new_version(): marks current as not latest, copies record with version+1, resets verification_state to pending
- Default tree/search views filter is_latest=True
- Version history via smart button (fa-history icon) showing all versions ordered by version desc
- Template-level Jinja2 conditional for mail.channel vs discuss.channel, NOT preprocessor-level
- VERSION_GATES dict pattern: `{'18.0': {'mail.channel': 'discuss.channel', 'mail.channel_all_employees': 'discuss.channel_general'}}`
- VERSION_GATES injected into Jinja2 render context alongside odoo_version
- Boolean trigger: `document_management: true` at module level
- Optional `document_config` dict for customization
- Pakistani university defaults for default_types: CNIC Copy, Transcript, Passport Photo, Domicile, Character Certificate
- Preprocessor order: 28 (after Pakistan=25, academic=27, before constraints=30)
- Module depends: `mail` added automatically
- All logic in `preprocessors/document_management.py` -- zero changes to core preprocessor files

### Claude's Discretion
- Internal helper function signatures (_build_document_type_model, _build_document_model)
- How to render Many2oneReference in templates (may need template branch if not already supported)
- Whether default_types generates XML data file or Python demo data
- Test fixture structure for document management tests
- Exact file size computation method (base64 decode length)

### Deferred Ideas (OUT OF SCOPE)
- OCR document classification (AI/ML scope creep)
- Document approval workflow (multi-level approval ON TOP of verification)
- Cross-module document requirements (e.g., "admission requires these 5 document types")
- Document expiry dates and renewal reminders
- Bulk document upload wizard
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOMN-01 | Document management -- document type classification, Binary file storage with `attachment=True`, verification workflow using separate `verification_state` field, simple version tracking | Preprocessor GENERATION pattern from academic_calendar.py; two model builder functions; complex_constraints for action methods; doc_* constraint type prefix for template rendering; template extension for field kwargs |
| DOMN-04 | Odoo 18 `discuss.channel` version gate -- template conditional for mail.channel (17.0) vs discuss.channel (18.0) rename | VERSION_GATES dict injected into _build_module_context(); Jinja2 conditional in templates; known_odoo_models.json already has both mail.channel and discuss.channel entries |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 | Preprocessor and test code | Project standard (Odoo 17 compatible) |
| Jinja2 | >=3.1 | Template rendering with StrictUndefined | Already used by renderer.py |
| pytest | >=8.0 | Test framework | Already used throughout project |
| Pydantic v2 | >=2.0 | Spec validation (extra='allow' passes document_management through) | Phase 47 established |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| copy (stdlib) | N/A | Deep copy for immutability tests | Test assertions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| GENERATION pattern (new models) | INJECTION pattern (add fields to existing models) | Generation is correct here -- document models are standalone, not augmenting existing models |
| Linked list versioning | Separate document.version model | User explicitly chose linked list -- simpler ACL, one model, proven pattern |
| Preprocessor-level version gate | Template-level Jinja2 conditional | Template-level is correct -- the rename is purely XML, not Python logic |

## Architecture Patterns

### Recommended Project Structure
```
preprocessors/
├── document_management.py  # NEW -- auto-discovered by pkgutil
renderer_context.py         # MODIFIED -- VERSION_GATES in _build_module_context()
templates/
├── 17.0/
│   ├── model.py.j2         # MODIFIED -- generic field branch extended with attachment/readonly/copy/tracking/size/model_field
│   └── view_form.xml.j2    # MODIFIED -- doc_* verification buttons + statusbar
├── 18.0/
│   ├── model.py.j2         # MODIFIED -- same extensions as 17.0
│   └── view_form.xml.j2    # MODIFIED -- same extensions as 17.0
tests/
├── test_document_management.py  # NEW -- unit + E2E tests
```

### Pattern 1: GENERATION Preprocessor (established by academic_calendar.py)
**What:** Preprocessor builds complete model dicts and appends to spec["models"]
**When to use:** When generating entirely new models that don't exist in the user's spec
**Example:**
```python
# Source: preprocessors/academic_calendar.py (existing pattern)
@register_preprocessor(order=28, name="document_management")
def _process_document_management(spec: dict[str, Any]) -> dict[str, Any]:
    if not spec.get("document_management"):
        return spec
    config = spec.get("document_config", {})
    new_models = list(spec.get("models", []))
    new_models.append(_build_document_type_model(config))
    new_models.append(_build_document_document_model(config))
    new_spec = {**spec, "models": new_models}
    # Inject mail dependency
    depends = list(new_spec.get("depends", []))
    if "mail" not in depends:
        depends.append("mail")
    new_spec["depends"] = depends
    return new_spec
```

### Pattern 2: Action Methods via complex_constraints (established by academic_calendar.py)
**What:** Action methods rendered as plain methods (not @api.constrains prefixed) using constraint type prefixes
**When to use:** When generating Python methods that are called from form buttons, not field constraints
**Example:**
```python
# Action methods use 'doc_action_*' type prefix
# The template renders these as:  def method_name(self):  (no @api.constrains)
{
    "name": "action_verify",
    "fields": ["verification_state"],
    "type": "doc_action_verify",
    "check_body": _ACTION_VERIFY_BODY,
}
```

### Pattern 3: Constraint Methods via complex_constraints (established by pakistan_hec.py)
**What:** File validation constraints rendered with @api.constrains decorator using type prefix
**When to use:** When generating validation that fires on field write (e.g., file size/mime type check)
**Example:**
```python
# File validation uses 'doc_file_validation' type prefix
# The template renders as:  @api.constrains("file")  def _check_file_validation(self):
{
    "name": "file_validation",
    "fields": ["file", "document_type_id"],
    "type": "doc_file_validation",
    "check_body": _FILE_VALIDATION_BODY,
}
```

### Pattern 4: VERSION_GATES Context Injection
**What:** Dict mapping Odoo version to XML ID renames, injected into Jinja2 context
**When to use:** When model names change between Odoo versions (e.g., mail.channel -> discuss.channel)
**Example:**
```python
# In renderer_context.py _build_module_context():
VERSION_GATES = {
    '18.0': {
        'mail.channel': 'discuss.channel',
        'mail.channel_all_employees': 'discuss.channel_general',
    }
}
ctx["version_gates"] = VERSION_GATES
# In templates:
# {% if odoo_version >= "18.0" %}discuss.channel{% else %}mail.channel{% endif %}
```

### Anti-Patterns to Avoid
- **Reusing approval preprocessor for verification:** Verification is binary (3 states), approval is multi-level chain. They have different field names, different group structures, different template rendering. Do NOT try to make approval_patterns handle verification.
- **Storing Binary data in PostgreSQL:** Always use `attachment=True` on Binary fields. Without it, file data goes into the database (bloats pg_dump, kills performance).
- **Mutating input spec:** Every preprocessor MUST return a new dict. Use `{**spec, "models": new_models}` pattern.
- **Modifying core preprocessor files:** All Phase 52 logic goes into `document_management.py`. The registry auto-discovers it via pkgutil.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Preprocessor registration | Manual import + function list | `@register_preprocessor(order=28)` decorator | Auto-discovery via pkgutil in `__init__.py` |
| Model dict structure | Custom model class | Plain dict matching existing pattern | Templates expect specific dict keys (name, description, fields, complex_constraints, etc.) |
| Security roles | Custom role injection | `security_roles` list in spec (existing pattern) | Security preprocessor handles role -> group XML generation |
| Constraint rendering | Inline Python generation | `complex_constraints` with `check_body` string + type prefix | Template already handles rendering based on type prefix |

**Key insight:** Phase 52 is entirely a preprocessor exercise. No new template files are created -- only existing templates are extended with new conditional branches for `doc_*` constraint types, field kwargs, and verification buttons.

## Common Pitfalls

### Pitfall 1: Template Silently Ignores Field Attributes
**What goes wrong:** Preprocessor generates field dicts with `attachment=True`, `readonly=True`, `tracking=True` etc., but the rendered Python file omits these attributes entirely.
**Why it happens:** The current generic field branch in `model.py.j2` only renders `string`, `required`, `index`, `default`, `help`, `groups`. All other kwargs are silently dropped.
**How to avoid:** Extend the generic field template branch to conditionally render `attachment`, `readonly`, `copy`, `tracking`, `size`, `related`, and `model_field` attributes. This is a template change, not a preprocessor change.
**Warning signs:** Generated `document_document.py` has `file = fields.Binary(string="File", required=True)` without `attachment=True`.

### Pitfall 2: Many2oneReference Needs model_field Parameter
**What goes wrong:** `res_id = fields.Many2oneReference()` renders without `model_field='res_model'`, causing Odoo runtime error.
**Why it happens:** `Many2oneReference` is not in the template's relational field branch (it only handles Many2one, One2many, Many2many). It falls through to the generic branch which doesn't render `model_field`.
**How to avoid:** Either add a `Many2oneReference` branch to the template, or (simpler) add `model_field` to the generic branch's conditional kwargs. The `Many2oneReference` field type IS already in `VALID_FIELD_TYPES` (spec_schema.py) but not handled specially in templates.
**Warning signs:** Generated code has `res_id = fields.Many2oneReference(string="Resource ID")` missing `model_field` parameter.

### Pitfall 3: doc_* Constraint Type Not Handled by Template
**What goes wrong:** Action methods like `action_verify()` render with `_check_` prefix or inside a `for rec in self:` wrapper, breaking the method signature.
**Why it happens:** The template's constraint rendering logic dispatches on type prefix: `pk_*` and `ac_year_*`/`ac_term_*` get `@api.constrains` + direct body, `ac_action*` gets plain method, and everything else gets `_check_` prefix + for-loop wrapper.
**How to avoid:** Add `doc_action*` type prefix handling to the model template, similar to `ac_action*`. Add `doc_file_validation` to the `pk_*`/`ac_year_*`/`ac_term_*` branch for @api.constrains rendering.
**Warning signs:** Generated `action_verify` method is named `_check_action_verify` or has wrong indentation.

### Pitfall 4: Preprocessor Order Collision
**What goes wrong:** If order=28 is already taken by another preprocessor, both run but with undefined relative order.
**Why it happens:** The registry sorts by order number. If two preprocessors have the same order, Python's sort stability determines execution order, which is fragile.
**How to avoid:** Verify no existing preprocessor uses order=28. Current registry: pakistan_hec=25, academic_calendar=27, constraints=30. Order 28 is available and correctly positioned.
**Warning signs:** Test that checks registration order fails.

### Pitfall 5: StrictUndefined Crashes on Missing Context Keys
**What goes wrong:** Template rendering fails with `jinja2.UndefinedError` because new context keys like `has_document_management` or `verification_state_field` are missing for non-document models.
**Why it happens:** StrictUndefined mode crashes on any undefined variable reference. All template conditionals must check keys that are guaranteed to exist.
**How to avoid:** Add default values for all new context keys in `_build_model_context()` (e.g., `has_document_verification = model.get("has_document_verification", False)`). This follows the established pattern from Phase 38 (audit), Phase 39 (approval), Phase 40 (notifications).
**Warning signs:** Rendering a non-document spec fails with UndefinedError mentioning a document-related variable.

### Pitfall 6: VERSION_GATES Dict Not Available in Template Context
**What goes wrong:** Template uses `version_gates` variable but it's not in the render context, causing StrictUndefined crash.
**Why it happens:** `VERSION_GATES` must be explicitly injected into both `_build_model_context()` and `_build_module_context()`.
**How to avoid:** Add `version_gates` to both context builders with an empty dict default.
**Warning signs:** Rendering ANY spec (not just document specs) crashes after adding version gate code to templates.

## Code Examples

Verified patterns from existing codebase (not external sources):

### GENERATION Preprocessor Structure
```python
# Source: preprocessors/academic_calendar.py lines 428-462
@register_preprocessor(order=27, name="academic_calendar")
def _process_academic_calendar(spec: dict[str, Any]) -> dict[str, Any]:
    if not spec.get("academic_calendar"):
        return spec  # Early return: same object (no-op)
    config = spec.get("academic_config", {})
    new_models = list(spec.get("models", []))
    new_models.append(_build_academic_year_model(default_term))
    new_models.append(_build_academic_term_model())
    new_spec = {**spec, "models": new_models}
    depends = list(new_spec.get("depends", []))
    if "mail" not in depends:
        depends.append("mail")
    new_spec["depends"] = depends
    return new_spec
```

### Model Dict with Fields, SQL Constraints, Complex Constraints
```python
# Source: preprocessors/academic_calendar.py lines 125-243
def _build_academic_year_model(default_term_structure: str = "semester") -> dict[str, Any]:
    return {
        "name": "academic.year",
        "description": "Academic Year",
        "model_order": "date_start desc",
        "fields": [...],
        "sql_constraints": [...],
        "complex_constraints": [
            {
                "name": "year_dates",
                "fields": ["date_start", "date_end"],
                "type": "ac_year_overlap",
                "check_body": _YEAR_OVERLAP_CHECK_BODY,
            },
            {
                "name": "action_confirm",
                "fields": ["term_structure"],
                "type": "ac_action_confirm",
                "check_body": _ACTION_CONFIRM_BODY,
            },
        ],
    }
```

### Template Constraint Dispatch (model.py.j2)
```jinja2
{# Source: templates/17.0/model.py.j2 lines 213-238 #}
{% for constraint in complex_constraints %}
{% if constraint.type == 'temporal' %}
    {# @api.constrains with check_expr #}
{% elif constraint.type.startswith('pk_') or constraint.type.startswith('ac_year_') or constraint.type.startswith('ac_term_') %}
    {# @api.constrains with check_body (direct render) #}
{% elif constraint.type.startswith('ac_action') %}
    {# Plain method: def method_name(self): #}
{% else %}
    {# Fallback: _check_ prefix with for-loop wrapper #}
{% endif %}
{% endfor %}
```

### Context Key Injection Pattern
```python
# Source: renderer_context.py lines 197-211 (Phase 38-40 pattern)
# Phase 38: audit trail context keys (defaults prevent StrictUndefined crashes)
has_audit = model.get("has_audit", False)
audit_fields = model.get("audit_fields", [])
# Phase 39: approval workflow context keys
has_approval = model.get("has_approval", False)
approval_levels = model.get("approval_levels", [])
```

### Test Structure Pattern
```python
# Source: tests/test_academic_calendar.py
def _make_spec(...) -> dict[str, Any]:
    """Build a minimal spec for preprocessor testing."""

def _process(spec: dict[str, Any]) -> dict[str, Any]:
    """Run the specific preprocessor on a spec."""
    from odoo_gen_utils.preprocessors.X import _process_X
    return _process_X(spec)

class TestPreprocessorRegistration:
    """Registration at order=N, function name, noop behavior."""

class TestModelGeneration:
    """Model creation, field verification, constraint verification."""

class TestImmutability:
    """Input not mutated, output is new dict."""

class TestE2E:
    """Full render_module() integration tests."""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Monolith preprocessors.py (1,715 lines) | Package with auto-discovery and decorator registry | Phase 45 (v3.3) | New preprocessors auto-discovered by pkgutil |
| Manual preprocessor imports | `@register_preprocessor(order=N)` decorator | Phase 45 | Zero __init__.py changes needed for new preprocessors |
| Hard-coded constraint rendering | Type-prefix dispatch (`pk_*`, `ac_*`) | Phase 49-50 | New prefixes (`doc_*`) follow same pattern |
| mail.channel only | mail.channel (17.0) / discuss.channel (18.0) | Odoo 18 release | Template-level version gates needed |

**Template field rendering gap (current limitation):**
- The generic field branch in model.py.j2 only renders: `string`, `required`, `index`, `default`, `help`, `groups`
- Missing but needed: `attachment`, `readonly`, `copy`, `tracking`, `size`, `related`, `model_field`
- This affects all preprocessors, not just Phase 52 (Pakistan HEC fields also have `tracking=True` and `copy=False` that are silently dropped)
- Phase 52 is the right time to fix this since Binary+attachment=True is a hard requirement

## Template Extension Analysis

### Fields Needing Template Support

The model.py.j2 generic field branch needs these conditionals added:

| Attribute | Odoo Kwarg | Type | Used By |
|-----------|-----------|------|---------|
| `attachment` | `attachment=True` | Boolean | Binary fields (document.document.file) |
| `readonly` | `readonly=True` | Boolean | Metadata fields (mime_type, file_size, upload_date, verified_by, verified_date, version) |
| `copy` | `copy=False` | Boolean | CNIC, NTN, STRN, HEC reg, document versioning |
| `tracking` | `tracking=True` | Boolean | CNIC, phone_pk, name, verification_state |
| `size` | `size=N` | Integer | CNIC (15), NTN (9), STRN (15) |
| `model_field` | `model_field='res_model'` | String | Many2oneReference (res_id) |

### Template Branches for doc_* Constraint Types

| Type Prefix | Template Rendering | Example |
|-------------|-------------------|---------|
| `doc_file_validation` | `@api.constrains(...)` + `_check_` prefix + direct body | File size/MIME check |
| `doc_action_verify` | Plain method `def action_verify(self):` + direct body | Verify button handler |
| `doc_action_reject` | Plain method `def action_reject(self):` + direct body | Reject button handler |
| `doc_action_reset` | Plain method `def action_reset_to_pending(self):` + direct body | Reset button handler |
| `doc_action_upload_new_version` | Plain method `def action_upload_new_version(self):` + direct body | New version handler |

### View Template Extensions

The `view_form.xml.j2` needs:
1. Verification buttons in header (Verify, Reject, Reset to Pending) with visibility conditions and group restrictions
2. `verification_state` statusbar widget
3. Smart button for version history (fa-history icon)
4. Default `is_latest=True` domain on tree/search views for document.document

## renderer_context.py Changes

### _build_model_context() Additions
```python
# Phase 52: document management context keys
has_document_verification = model.get("has_document_verification", False)
document_verification_actions = model.get("document_verification_actions", [])
has_document_versioning = model.get("has_document_versioning", False)
document_version_action = model.get("document_version_action", None)
```

### _build_module_context() Additions
```python
# Phase 52: VERSION_GATES for Odoo version-conditional template rendering
VERSION_GATES = {
    '18.0': {
        'mail.channel': 'discuss.channel',
        'mail.channel_all_employees': 'discuss.channel_general',
    }
}
ctx["version_gates"] = VERSION_GATES
```

### has_domain_constraints Extension
```python
# Phase 52: doc_file_validation constraints also need @api.constrains
has_domain_constraints = any(
    c.get("type", "").startswith("pk_")
    or c.get("type", "").startswith("ac_year_")
    or c.get("type", "").startswith("ac_term_")
    or c.get("type", "").startswith("doc_file_")  # NEW
    for c in complex_constraints
)
```

### needs_api and needs_translate Updates
```python
# Document verification action methods need translate for UserError messages
if has_document_verification:
    needs_translate = True
    needs_api = True  # for @api.constrains on file validation
```

## Security Role Design

The document management preprocessor should inject 4 security roles:

| Role | XML ID Pattern | Permissions | Record Rules |
|------|---------------|-------------|-------------|
| viewer | `group_{module}_document_viewer` | Read document.type + document.document | Own documents only (res_model + create_uid) |
| uploader | `group_{module}_document_uploader` | Create/Read/Update document.document, Read document.type | Own documents |
| verifier | `group_{module}_document_verifier` | Create/Read/Update document.document, Read document.type | All documents (for verification) |
| manager | `group_{module}_document_manager` | Full CRUD on both models | All records |

The preprocessor should add these to `spec["security_roles"]` following the implied_ids hierarchy: viewer < uploader < verifier < manager.

## Data Files for Default Document Types

**Recommended approach:** Generate XML data file via `extra_data_files` extension point (established in Phase 49 for PKR currency).

Add `data/document_type_data.xml` to `spec["extra_data_files"]` and render it in `renderer.py`'s `_render_extra_data_files()` function.

Default types (from CONTEXT.md):
```xml
<record id="document_type_cnic" model="document.type">
    <field name="name">CNIC Copy</field>
    <field name="code">cnic</field>
    <field name="required_for">admission</field>
    <field name="max_file_size">5</field>
    <field name="allowed_mime_types">application/pdf,image/jpeg,image/png</field>
    <field name="sequence">10</field>
</record>
<!-- ... similar for transcript, passport_photo, domicile, character_certificate -->
```

## Open Questions

1. **Template field kwargs -- scope of change**
   - What we know: The generic field branch misses attachment, readonly, copy, tracking, size, model_field
   - What's unclear: Should we fix ALL missing kwargs in Phase 52, or only the ones document management needs?
   - Recommendation: Fix all -- it's a small template change, benefits future phases, and retroactively fixes Pakistan HEC fields (tracking, copy, size already in field dicts but silently dropped)

2. **Verification buttons in view template -- conditional rendering**
   - What we know: Need header buttons for Verify/Reject/Reset with group checks and state visibility
   - What's unclear: Best place to add -- inline in view_form.xml.j2 with `has_document_verification` conditional, or separate template?
   - Recommendation: Inline in view_form.xml.j2 with conditional block (same pattern as approval buttons), since document verification is model-level context

3. **default_types: data XML vs demo data**
   - What we know: User specified Pakistani university defaults (CNIC Copy, Transcript, etc.)
   - What's unclear: Whether these go in `data/` (always loaded) or `demo/` (only with demo data flag)
   - Recommendation: Generate as `data/document_type_data.xml` (always loaded) -- these are reference/seed data, not demo records. Use `noupdate="1"` so users can customize.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | python/pyproject.toml (existing) |
| Quick run command | `python -m pytest python/tests/test_document_management.py -x -q` |
| Full suite command | `python -m pytest python/tests/ -x -q --ignore=python/tests/test_wizard.py` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOMN-01 | document_management: true generates document.type + document.document models | unit | `python -m pytest python/tests/test_document_management.py::TestPreprocessorGeneration -x` | Wave 0 |
| DOMN-01 | document.type has correct fields, SQL constraints | unit | `python -m pytest python/tests/test_document_management.py::TestDocumentTypeFields -x` | Wave 0 |
| DOMN-01 | document.document has correct fields, verification_state, versioning | unit | `python -m pytest python/tests/test_document_management.py::TestDocumentDocumentFields -x` | Wave 0 |
| DOMN-01 | Verification action methods generated correctly | unit | `python -m pytest python/tests/test_document_management.py::TestVerificationWorkflow -x` | Wave 0 |
| DOMN-01 | Version tracking action method generated correctly | unit | `python -m pytest python/tests/test_document_management.py::TestVersionTracking -x` | Wave 0 |
| DOMN-01 | File validation constraint generated | unit | `python -m pytest python/tests/test_document_management.py::TestFileValidation -x` | Wave 0 |
| DOMN-01 | Preprocessor is immutable (pure function) | unit | `python -m pytest python/tests/test_document_management.py::TestImmutability -x` | Wave 0 |
| DOMN-01 | Preprocessor registered at order=28 | unit | `python -m pytest python/tests/test_document_management.py::TestPreprocessorRegistration -x` | Wave 0 |
| DOMN-01 | E2E render produces correct Python with attachment=True, readonly, tracking | integration | `python -m pytest python/tests/test_document_management.py::TestDocumentManagementE2E -x` | Wave 0 |
| DOMN-04 | VERSION_GATES dict in render context | unit | `python -m pytest python/tests/test_document_management.py::TestVersionGates -x` | Wave 0 |
| DOMN-04 | Template uses discuss.channel for odoo_version >= 18.0 | integration | `python -m pytest python/tests/test_document_management.py::TestVersionGatesE2E -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest python/tests/test_document_management.py -x -q`
- **Per wave merge:** `python -m pytest python/tests/ -x -q --ignore=python/tests/test_wizard.py`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `python/tests/test_document_management.py` -- covers DOMN-01, DOMN-04
- [ ] No new test fixtures needed -- follows existing `_make_spec` / `_process` / `_find_model` helper pattern

## Sources

### Primary (HIGH confidence)
- `preprocessors/academic_calendar.py` -- GENERATION pattern reference (exact code studied)
- `preprocessors/pakistan_hec.py` -- INJECTION pattern reference, constraint body pattern
- `preprocessors/approval.py` -- Approval workflow pattern reference (verification differs)
- `preprocessors/_registry.py` -- Decorator-based registration API
- `preprocessors/__init__.py` -- Auto-discovery via pkgutil
- `renderer_context.py` -- Context builder patterns, StrictUndefined-safe defaults
- `templates/17.0/model.py.j2` -- Constraint type dispatch, field rendering gaps
- `templates/17.0/view_form.xml.j2` -- Button rendering in form header
- `templates/shared/security_group.xml.j2` -- Security role rendering
- `spec_schema.py` -- VALID_FIELD_TYPES includes Binary and Many2oneReference
- `data/known_odoo_models.json` -- Both mail.channel and discuss.channel registered
- `tests/test_academic_calendar.py` -- Test structure reference (81 tests)
- `tests/test_pakistan_hec.py` -- Test structure reference (55 tests)

### Secondary (MEDIUM confidence)
- [Odoo Forum: attachment=True](https://www.odoo.com/forum/help-1/what-does-attachmenttrue-do-173406) -- Binary field storage in filestore via ir.attachment
- [Odoo Forum: mail.channel](https://www.odoo.com/forum/help-1/i-need-to-add-a-channel-to-the-mail-channel-model-163148) -- Channel model API reference
- [GitHub: Odoo 16-to-17 migration notes](https://github.com/alexis-via/odoo-sample/blob/master/migrate_16-to-17.txt) -- Potential mail.channel -> discuss.channel migration reference
- [GitHub Issue: Odoo 18 mail migration](https://github.com/odoo/odoo/issues/234457) -- discuss_channel table in Odoo 18

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or official Odoo sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- uses only existing project patterns and libraries
- Architecture: HIGH -- follows established GENERATION preprocessor pattern exactly
- Pitfalls: HIGH -- identified from direct template code analysis (not theoretical)
- Template gaps: HIGH -- verified by reading model.py.j2 generic branch (lines 150-168)
- Version gates: MEDIUM -- mail.channel -> discuss.channel confirmed in known_odoo_models.json but exact Odoo version boundary (16->17 or 17->18) from CONTEXT.md user decision

**Research date:** 2026-03-08
**Valid until:** 2026-04-07 (30 days -- stable domain, no external dependencies changing)
