# Architecture: v3.1 Design Flaws & Feature Gaps Integration

**Domain:** Odoo module automation -- spec extensions, new templates, new renderer stages, performance patterns
**Researched:** 2026-03-05
**Confidence:** HIGH -- all changes extend proven patterns already established in v3.0 (stage functions, Result[T], Jinja2 templates, spec-driven context building)

## Existing Architecture (Baseline)

### Current Pipeline: Spec -> Renderer -> Templates -> Module

```
                    CURRENT RENDER PIPELINE (v3.0)
                    ================================

  spec.json (input)
       |
       v
  render_module()  <-- orchestrator
       |
       |-- _build_module_context(spec)    <-- shared context
       |
       |-- stages[] (7 lambdas, each returns Result[list[Path]])
       |     |
       |     |-- render_manifest()        <-- manifest.py.j2, init_root.py.j2, init_models.py.j2
       |     |-- render_models()          <-- model.py.j2, view_form.xml.j2, action.xml.j2 (per model)
       |     |-- render_views()           <-- menu.xml.j2
       |     |-- render_security()        <-- security_group.xml.j2, access_csv.j2, record_rules.xml.j2
       |     |-- render_wizards()         <-- wizard.py.j2, wizard_form.xml.j2, init_wizards.py.j2
       |     |-- render_tests()           <-- test_model.py.j2, init_tests.py.j2
       |     |-- render_static()          <-- demo_data.xml.j2, sequences.xml.j2, readme.rst.j2
       |
       v
  created_files[]   <-- list[Path] of all generated files
  warnings[]        <-- VerificationWarning from MCP verifier
```

### Current Spec Shape (Relevant Fields)

```json
{
  "module_name": "my_module",
  "module_title": "My Module",
  "odoo_version": "17.0",
  "depends": ["base", "mail"],
  "models": [
    {
      "name": "my.model",
      "description": "My Model",
      "inherit": null,
      "chatter": null,
      "fields": [
        {"name": "name", "type": "Char", "required": true},
        {"name": "amount", "type": "Float", "compute": "_compute_amount", "depends": ["qty", "price"], "store": true}
      ],
      "sql_constraints": [{"name": "name_uniq", "definition": "UNIQUE(name)", "message": "..."}]
    }
  ],
  "wizards": [...]
}
```

### Current Template Inventory (21 files)

| Template | Directory | Rendered By |
|----------|-----------|-------------|
| manifest.py.j2 | shared | render_manifest |
| init_root.py.j2 | shared | render_manifest |
| init_models.py.j2 | shared | render_manifest |
| model.py.j2 | 17.0, 18.0 | render_models |
| view_form.xml.j2 | 17.0, 18.0 | render_models |
| action.xml.j2 | 17.0, 18.0 | render_models |
| menu.xml.j2 | shared | render_views |
| security_group.xml.j2 | shared | render_security |
| access_csv.j2 | shared | render_security |
| record_rules.xml.j2 | shared | render_security |
| wizard.py.j2 | shared | render_wizards |
| wizard_form.xml.j2 | shared | render_wizards |
| init_wizards.py.j2 | shared | render_wizards |
| test_model.py.j2 | shared | render_tests |
| init_tests.py.j2 | shared | render_tests |
| demo_data.xml.j2 | shared | render_static |
| sequences.xml.j2 | shared | render_static |
| readme.rst.j2 | shared | render_static |

### Current Context Builder (_build_model_context)

Already handles: computed_fields, onchange_fields, constrained_fields, sequence_fields, state_field, inherit_list, needs_api, has_company_field, mail.thread injection. This is the primary extension point for new spec fields.

## Integration Plan: New Features into Existing Architecture

### Overview of Changes

```
CHANGE CLASSIFICATION
=====================

SPEC EXTENSIONS (modify spec shape, context builders):
  1. relationships section       -- new top-level spec key
  2. computation_chains section  -- new top-level spec key
  3. constraints section         -- new top-level spec key
  4. monetary field detection    -- derived from existing fields[]

NEW TEMPLATES (new .j2 files):
  5. report.xml.j2               -- QWeb report template
  6. report.py.j2                -- Report Python model
  7. graph_view.xml.j2           -- Graph/pivot/cohort views
  8. controller.py.j2            -- HTTP controller
  9. import_export_wizard.py.j2  -- Import/export wizard
  10. cron.xml.j2                -- ir.cron scheduled actions

NEW RENDERER STAGES (new stage functions):
  11. render_reports()           -- orchestrates report templates
  12. render_controllers()      -- orchestrates controller templates
  13. render_cron()              -- orchestrates cron data

TEMPLATE MODIFICATIONS (extend existing .j2 files):
  14. model.py.j2               -- index=True, store=True, _order, ormcache, Monetary+currency_id
  15. init_root.py.j2           -- import controllers, reports subpackages
  16. manifest.py.j2            -- add report/cron/controller data files
  17. access_csv.j2             -- ACL rows for report models

CONTEXT BUILDER MODIFICATIONS:
  18. _build_model_context()    -- performance annotations, monetary detection
  19. _build_module_context()   -- manifest_files for reports/cron/controllers
```

### Detailed Integration Points

#### 1. Spec Extensions (Data Layer)

The spec JSON gains three new top-level sections. These do NOT change the existing models/fields/wizards structure -- they ADD alongside it.

```json
{
  "module_name": "...",
  "models": [...],
  "wizards": [...],

  "relationships": [
    {
      "type": "through_model",
      "source": "course.course",
      "target": "student.student",
      "through": "course.enrollment",
      "source_field": "course_id",
      "target_field": "student_id"
    },
    {
      "type": "hierarchical",
      "model": "department.department",
      "parent_field": "parent_id",
      "child_field": "child_ids"
    },
    {
      "type": "self_referential",
      "model": "employee.employee",
      "field": "manager_id",
      "inverse_field": "subordinate_ids"
    }
  ],

  "computation_chains": [
    {
      "chain": ["line.amount", "order.total_amount", "order.tax_amount", "order.grand_total"],
      "models": ["sale.order.line", "sale.order", "sale.order", "sale.order"],
      "description": "Line amounts roll up to order totals"
    }
  ],

  "constraints": [
    {
      "type": "cross_model",
      "models": ["sale.order", "sale.order.line"],
      "rule": "order.state == 'confirmed' implies all lines have product_id set",
      "method": "_check_confirmed_lines"
    },
    {
      "type": "temporal",
      "model": "project.task",
      "rule": "date_end >= date_start",
      "method": "_check_dates"
    },
    {
      "type": "capacity",
      "model": "room.booking",
      "rule": "count of bookings for room at time <= room.capacity",
      "method": "_check_capacity"
    }
  ],

  "reports": [
    {
      "name": "report_invoice",
      "model": "account.move",
      "report_type": "qweb-pdf",
      "title": "Invoice Report"
    }
  ],

  "controllers": [
    {
      "name": "api_controller",
      "route": "/api/v1",
      "auth": "user",
      "methods": [
        {"endpoint": "/items", "http_method": "GET", "description": "List items"},
        {"endpoint": "/items/<int:item_id>", "http_method": "GET", "description": "Get item"}
      ]
    }
  ],

  "cron_jobs": [
    {
      "name": "cleanup_old_records",
      "model": "my.model",
      "method": "action_cleanup_old",
      "interval_number": 1,
      "interval_type": "days",
      "description": "Clean up records older than 90 days"
    }
  ],

  "performance": {
    "indexed_fields": [
      {"model": "sale.order", "field": "partner_id"},
      {"model": "sale.order", "field": "date_order"}
    ],
    "order_by": {
      "sale.order": "date_order desc, id desc"
    },
    "cached_methods": [
      {"model": "product.template", "method": "_get_categories", "keys": ["self.id"]}
    ],
    "transient_models": ["import.wizard"],
    "archival": {
      "model": "sale.order",
      "active_field": true,
      "cleanup_days": 365
    }
  }
}
```

**Integration with existing code:** The spec is a plain dict parsed from JSON. No schema validation exists today (spec fields are accessed via `.get()` with defaults). The new sections follow the same pattern -- `.get("relationships", [])`, `.get("reports", [])`, etc. No breaking changes.

#### 2. Context Builder Modifications

**`_build_model_context()` additions:**

```python
# NEW: Monetary field auto-detection
has_monetary = any(f.get("type") == "Monetary" for f in fields)
needs_currency_id = has_monetary and not any(f.get("name") == "currency_id" for f in fields)

# NEW: Performance annotations from spec
perf = spec.get("performance", {})
model_order = perf.get("order_by", {}).get(model["name"])
indexed_fields_for_model = [
    entry["field"] for entry in perf.get("indexed_fields", [])
    if entry["model"] == model["name"]
]
cached_methods = [
    entry for entry in perf.get("cached_methods", [])
    if entry["model"] == model["name"]
]
is_transient = model["name"] in perf.get("transient_models", [])

# NEW: Relationship awareness
relationships = [
    r for r in spec.get("relationships", [])
    if r.get("model") == model["name"] or r.get("source") == model["name"] or r.get("target") == model["name"]
]

# NEW: Computation chains involving this model
chains = [
    c for c in spec.get("computation_chains", [])
    if model["name"] in c.get("models", [])
]

# NEW: Cross-model constraints involving this model
model_constraints = [
    c for c in spec.get("constraints", [])
    if model["name"] in (c.get("models", []) if isinstance(c.get("models"), list) else [c.get("model", "")])
]
```

**`_build_module_context()` additions:**

```python
# NEW: Report, controller, cron file paths for manifest
report_files = [f"report/{r['name']}_template.xml" for r in spec.get("reports", [])]
controller_files = []  # controllers don't go in manifest data
cron_files = ["data/cron.xml"] if spec.get("cron_jobs") else []

# Extend manifest_files computation
manifest_files.extend(report_files)
manifest_files.extend(cron_files)

# NEW: Flags for init_root.py.j2
has_controllers = bool(spec.get("controllers"))
has_reports = bool(spec.get("reports"))
```

#### 3. New Templates

| Template | Location | Purpose | Context Keys |
|----------|----------|---------|-------------|
| `report_template.xml.j2` | shared | QWeb report XML | report, model_name, fields |
| `report_action.xml.j2` | shared | Report action + paperformat | report, module_name |
| `graph_view.xml.j2` | shared | Graph/pivot view XML | model_name, measure_fields, dimension_fields |
| `controller.py.j2` | shared | HTTP controller class | controller, module_name |
| `init_controllers.py.j2` | shared | controllers/__init__.py | controllers |
| `import_export_wizard.py.j2` | shared | Bulk import/export wizard | wizard, model_name, fields |
| `cron.xml.j2` | shared | ir.cron data records | cron_jobs, module_name |

#### 4. New Renderer Stages

Three new stage functions, following the exact same pattern as existing ones:

```python
def render_reports(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render QWeb report templates and report actions."""
    try:
        reports = spec.get("reports", [])
        if not reports:
            return Result.ok([])
        created: list[Path] = []
        for report in reports:
            rctx = {**module_context, "report": report}
            rname = report["name"]
            created.append(render_template(
                env, "report_template.xml.j2",
                module_dir / "report" / f"{rname}_template.xml", rctx))
            created.append(render_template(
                env, "report_action.xml.j2",
                module_dir / "report" / f"{rname}_action.xml", rctx))
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_reports failed: {exc}")


def render_controllers(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render HTTP controllers and controllers/__init__.py."""
    try:
        controllers = spec.get("controllers", [])
        if not controllers:
            return Result.ok([])
        created: list[Path] = []
        created.append(render_template(
            env, "init_controllers.py.j2",
            module_dir / "controllers" / "__init__.py",
            {**module_context, "controllers": controllers}))
        for ctrl in controllers:
            cctx = {**module_context, "controller": ctrl}
            created.append(render_template(
                env, "controller.py.j2",
                module_dir / "controllers" / f"{ctrl['name']}.py", cctx))
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_controllers failed: {exc}")


def render_cron(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render ir.cron scheduled action data file."""
    try:
        cron_jobs = spec.get("cron_jobs", [])
        if not cron_jobs:
            return Result.ok([])
        created: list[Path] = []
        cctx = {**module_context, "cron_jobs": cron_jobs}
        created.append(render_template(
            env, "cron.xml.j2",
            module_dir / "data" / "cron.xml", cctx))
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_cron failed: {exc}")
```

**Integration into render_module():**

```python
stages = [
    lambda: render_manifest(env, spec, module_dir, ctx),
    lambda: render_models(env, spec, module_dir, ctx, verifier=verifier, warnings_out=all_warnings),
    lambda: render_views(env, spec, module_dir, ctx),
    lambda: render_security(env, spec, module_dir, ctx),
    lambda: render_wizards(env, spec, module_dir, ctx),
    lambda: render_reports(env, spec, module_dir, ctx),       # NEW
    lambda: render_controllers(env, spec, module_dir, ctx),   # NEW
    lambda: render_cron(env, spec, module_dir, ctx),          # NEW
    lambda: render_tests(env, spec, module_dir, ctx),
    lambda: render_static(env, spec, module_dir, ctx),
]
```

Reports and controllers go AFTER security (they need ACLs defined) and BEFORE tests (tests may reference reports). Cron goes before tests for the same reason.

#### 5. Template Modifications (Existing Files)

**model.py.j2 changes:**

```jinja2
{# Add after _description line #}
{% if model_order %}
    _order = "{{ model_order }}"
{% endif %}

{# Monetary currency_id auto-injection #}
{% if needs_currency_id %}
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
{% endif %}

{# Field-level index annotation #}
{% for field in fields %}
    {{ field.name }} = fields.{{ field.type }}(
        ...
{% if field.name in indexed_field_names %}
        index=True,
{% endif %}
    )
{% endfor %}

{# ormcache decorator on methods #}
{% if cached_methods %}
from odoo.tools import ormcache
{% endif %}

{% for cm in cached_methods %}
    @ormcache({{ cm.keys | map('quote') | join(', ') }})
    def {{ cm.method }}(self):
        # TODO: implement cached method
        pass
{% endfor %}
```

**init_root.py.j2 changes:**

```jinja2
from . import models
{% if has_wizards %}
from . import wizards
{% endif %}
{% if has_controllers %}
from . import controllers
{% endif %}
```

Note: `report/` subdirectory typically contains only XML templates, not Python models, so no `from . import report` is needed unless the report defines a custom Python parser class.

**manifest.py.j2 changes:** Already driven by `manifest_files` list in context. The `_compute_manifest_data()` function needs extension to include report and cron files.

**access_csv.j2 changes:** No change needed. Report models (`ir.actions.report`) are Odoo core models that do not need custom ACL entries.

## Component Boundary Map

```
MODIFIED vs NEW COMPONENTS
==========================

MODIFIED (extend existing files):
  renderer.py
    |-- _build_model_context()      +15 context keys
    |-- _build_module_context()     +5 context keys, manifest file list
    |-- _compute_manifest_data()    +report, cron file paths
    |-- render_module()             +3 stages in pipeline
    |-- _track_artifacts()          +REPORT, CONTROLLER, CRON kinds
  auto_fix.py
    |-- (no changes needed for v3.1)
  templates/shared/init_root.py.j2  +controllers conditional import
  templates/17.0/model.py.j2        +_order, index, ormcache, currency_id
  templates/18.0/model.py.j2        +same as 17.0

NEW (entirely new files):
  renderer.py (new functions, same file):
    |-- render_reports()
    |-- render_controllers()
    |-- render_cron()
  templates/shared/report_template.xml.j2
  templates/shared/report_action.xml.j2
  templates/shared/graph_view.xml.j2
  templates/shared/controller.py.j2
  templates/shared/init_controllers.py.j2
  templates/shared/import_export_wizard.py.j2
  templates/shared/cron.xml.j2
```

## Data Flow: Spec Through Pipeline

### Before v3.1

```
spec.json --> _build_module_context() --> shared context dict
                                              |
          --> _build_model_context()  --> per-model context dict
                                              |
          --> stage functions         --> render_template() calls
                                              |
          --> Jinja2 .j2 templates    --> output files
```

### After v3.1

```
spec.json (EXTENDED with relationships, reports, controllers, cron, performance)
    |
    v
_build_module_context()  (EXTENDED: +has_controllers, +has_reports, +cron manifest entries)
    |                                +report manifest entries
    v
shared context dict -----> render_manifest()
                    -----> render_models()       (per-model context EXTENDED with performance keys)
                    -----> render_views()
                    -----> render_security()
                    -----> render_wizards()
                    -----> render_reports()       NEW stage
                    -----> render_controllers()   NEW stage
                    -----> render_cron()          NEW stage
                    -----> render_tests()
                    -----> render_static()
    |
    v
output files (EXPANDED set: +report/*.xml, +controllers/*.py, +data/cron.xml)
```

### Key Data Flow Principle: Spec Sections Map to Stages

Each new spec section has a single owning stage. Cross-cutting concerns (like monetary detection) are resolved in context builders, not in stages.

| Spec Section | Primary Stage | Context Builder |
|-------------|---------------|-----------------|
| `models[]` | render_models | _build_model_context |
| `wizards[]` | render_wizards | render_wizards (inline) |
| `reports[]` | render_reports (NEW) | render_reports (inline) |
| `controllers[]` | render_controllers (NEW) | render_controllers (inline) |
| `cron_jobs[]` | render_cron (NEW) | render_cron (inline) |
| `relationships[]` | render_models (enriches model context) | _build_model_context |
| `computation_chains[]` | render_models (enriches model context) | _build_model_context |
| `constraints[]` | render_models (enriches model context) | _build_model_context |
| `performance{}` | render_models (field-level) + render_manifest (_order) | _build_model_context |

## Build Order (Dependency-Driven)

### Dependency Graph

```
                    LAYER 0: Spec Extensions
                    ========================
       No code changes needed. JSON is schema-free.
       Agent/human just produces richer specs.

                    LAYER 1: Context Builders
                    =========================
       _build_model_context() extensions
       _build_module_context() extensions
       _compute_manifest_data() extensions
              |
              | required by
              v
                    LAYER 2: Template Changes
                    =========================
       model.py.j2 (index, _order, ormcache, currency_id)
       init_root.py.j2 (controllers import)
              |
              | required by            independent of
              v                              |
                    LAYER 3: New Templates + Stages
                    ================================
       +-----------------+  +-------------------+  +-------------+
       | render_reports() |  | render_controllers |  | render_cron |
       | report_*.xml.j2  |  | controller.py.j2   |  | cron.xml.j2 |
       | graph_view.xml.j2|  | init_controllers   |  |             |
       +-----------------+  +-------------------+  +-------------+
              |                      |                      |
              | all require          |                      |
              v                      v                      v
                    LAYER 4: Pipeline Integration
                    =============================
       render_module() adds 3 stages
       _track_artifacts() adds new artifact kinds
              |
              v
                    LAYER 5: Tests
                    ==============
       Unit tests for each new stage
       Integration tests for full pipeline with new spec sections
       Golden path E2E with extended spec
```

### Recommended Phase Order

| Phase | What | Why This Order | Depends On |
|-------|------|----------------|------------|
| **1** | Spec design: relationships, computation_chains, constraints sections | Foundation. No code changes. Just define the spec shape. All downstream work reads this. | Nothing |
| **2** | Monetary detection + performance annotations in context builders | Small, self-contained changes to `_build_model_context()`. Modifies model.py.j2 only. Low risk. | Phase 1 (spec shape) |
| **3** | model.py.j2 template updates (index, _order, ormcache, Monetary+currency_id) | Template changes that consume the new context keys from Phase 2. | Phase 2 |
| **4** | render_reports() + QWeb report templates | Independent new stage. Report templates are XML-only (no Python model needed for basic reports). | Phase 1 (spec shape) |
| **5** | render_controllers() + controller templates | Independent new stage. Controllers need init_root.py.j2 update. | Phase 1 (spec shape) |
| **6** | render_cron() + cron.xml template | Simplest new stage (single XML data file). | Phase 1 (spec shape) |
| **7** | Graph/pivot/cohort views + import/export wizards | Analytics views extend render_models or render_views. Import/export wizards extend render_wizards. | Phase 1 |
| **8** | Pipeline integration (stages added to render_module, manifest updates) | Wire everything together. Requires all new stages to exist. | Phases 2-7 |
| **9** | Tests + golden path E2E with extended spec | Validate the entire pipeline with a spec that exercises all new features. | Phase 8 |

**Parallelizable:** Phases 4, 5, 6, 7 are independent of each other. They all depend only on Phase 1 (spec shape). They can be built in parallel or in any order.

**Critical path:** Phase 1 -> Phase 2 -> Phase 3 -> Phase 8 -> Phase 9. This is the path for performance annotations in models, which is the only chain with sequential dependencies.

## Architectural Patterns

### Pattern 1: Stage Function Contract

**What:** Every renderer stage follows the same contract: `(env, spec, module_dir, module_context) -> Result[list[Path]]`.

**Why:** Uniform error handling (Result.ok/Result.fail), composability (stages are lambdas in a list), independent testability (call one stage with mock inputs).

**Rule:** New stages MUST return `Result.ok([])` when their spec section is empty, not `Result.ok(None)` or skip execution. The pipeline calls `.extend(result.data or [])` and expects a list.

```python
# CORRECT
def render_reports(...) -> Result[list[Path]]:
    reports = spec.get("reports", [])
    if not reports:
        return Result.ok([])  # empty list, not None
    ...
```

### Pattern 2: Context Builder Layering

**What:** Module-level context (shared across all templates) goes in `_build_module_context()`. Per-model context goes in `_build_model_context()`. Stage-specific context is built inline in the stage function.

**Why:** Prevents context bloat. Not every template needs every key. The model template needs `indexed_field_names` but the report template does not.

**Rule:** New spec sections that create standalone output (reports, controllers, cron) build their template context INLINE in their stage function. Only cross-cutting concerns (monetary detection, performance flags that affect model.py.j2) go in the shared builders.

### Pattern 3: Immutable Context Extension

**What:** Use `{**module_context, "report": report}` to create new contexts. Never mutate `module_context` or `model_context` in place.

**Why:** Stages share the same `ctx` reference. Mutation in one stage would contaminate later stages.

**Rule:** Already enforced throughout v3.0. All new stages MUST follow this pattern.

### Pattern 4: Conditional File Generation

**What:** If a spec section is empty, generate zero files and return `Result.ok([])`. Do NOT generate stub files.

**Why:** Clean modules. A module without reports should not have an empty `report/` directory. Matches Odoo community conventions.

**Rule:** `render_reports()` returns `Result.ok([])` when `spec.get("reports", [])` is empty. The `manifest_files` list must also conditionally exclude report paths.

### Pattern 5: Template Directory Convention

**What:** New templates go in `shared/` unless they differ between Odoo 17.0 and 18.0. Version-specific templates go in `17.0/` or `18.0/` and override `shared/`.

**Why:** The `FileSystemLoader([version_dir, shared_dir])` fallback chain handles this automatically.

**Rule:** QWeb reports, controllers, and cron are syntax-identical between 17.0 and 18.0. Put them in `shared/`. If future Odoo versions change report syntax, add version-specific overrides.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Monolithic Context Builder

**What people do:** Add all 15+ new context keys to `_build_model_context()`, even keys only used by reports or controllers.
**Why it is wrong:** Context builder grows beyond 200 lines. Every template receives keys it does not use. StrictUndefined cannot catch typos in optional keys.
**Do this instead:** Add only model-relevant keys (performance, monetary, relationships) to `_build_model_context()`. Report/controller/cron contexts are built inline in their stage functions.

### Anti-Pattern 2: Nested Stage Dependencies

**What people do:** Make `render_reports()` call `render_models()` to get model context, or have stages return data that later stages consume.
**Why it is wrong:** Breaks the independent-stage contract. Stages become coupled. Order changes break things.
**Do this instead:** Stages read from `spec` (immutable input) and `module_context` (shared context). They do NOT read from other stages' outputs. If a report needs model field names, it reads `spec["models"]` directly.

### Anti-Pattern 3: Performance Annotations in Templates Only

**What people do:** Add `index=True` logic only in model.py.j2 without spec-level declaration, relying on template heuristics.
**Why it is wrong:** Heuristics guess wrong. A field named `partner_id` is usually indexed, but not always. Performance decisions should be explicit in the spec, not implicit in templates.
**Do this instead:** Performance annotations live in `spec["performance"]`. The context builder translates them into template-friendly keys. Templates render what the spec declares.

### Anti-Pattern 4: Separate Renderer File for Each Stage

**What people do:** Create `render_reports.py`, `render_controllers.py`, `render_cron.py` as separate modules.
**Why it is wrong:** Over-fragmentation. The existing 7 stages are all in `renderer.py` (~770 lines). Adding 3 more stages adds ~120 lines. Still well under 800 lines. Separate files add import complexity without benefit.
**Do this instead:** Keep all stage functions in `renderer.py`. If it exceeds 800 lines after adding all stages plus context builder extensions, THEN extract context builders into a `renderer_context.py` module.

## Generated Module Structure (After v3.1)

```
my_module/
  __init__.py                 # MODIFIED: +controllers import
  __manifest__.py             # MODIFIED: +report, cron data files
  models/
    __init__.py
    my_model.py               # MODIFIED: +_order, +index, +ormcache, +currency_id
  views/
    my_model_views.xml         # MODIFIED: +graph/pivot views appended
    my_model_action.xml
    menu.xml
  security/
    security.xml
    ir.model.access.csv
    record_rules.xml
  wizards/                     # existing
    __init__.py
    import_data.py             # NEW: import/export wizard
  controllers/                 # NEW directory
    __init__.py
    api_controller.py
  report/                      # NEW directory
    report_invoice_template.xml
    report_invoice_action.xml
  data/
    data.xml
    sequences.xml
    cron.xml                   # NEW file
  tests/
    __init__.py
    test_my_model.py
  demo/
    demo_data.xml
  static/description/index.html
  README.rst
  i18n/my_module.pot
```

## Scaling Considerations

| Concern | Impact | Approach |
|---------|--------|----------|
| Template count growth (21 -> 28) | Minimal. FileSystemLoader handles hundreds of templates efficiently. | No action needed. |
| Context builder complexity | `_build_model_context` grows from ~100 to ~130 lines. | Monitor. Extract to separate function if exceeding 150 lines. |
| Stage count growth (7 -> 10) | Minimal. Lambda list iteration is O(n) where n=10. | No action needed. |
| Spec size growth | Specs with all sections may reach 200+ lines of JSON. | Consider spec validation (JSON Schema or Pydantic) in a future milestone. |
| Manifest data file ordering | More file types increase ordering complexity. | Extend `_compute_manifest_data()` with clear section comments. |

## Sources

- Existing codebase: `renderer.py` (770 lines), `auto_fix.py`, `validation/types.py` -- HIGH confidence, direct source code analysis
- Odoo 17.0 QWeb Reports documentation: `ir.actions.report` model and QWeb template conventions -- HIGH confidence (Odoo official docs)
- Odoo 17.0 Controllers documentation: `http.Controller`, `@http.route` decorator -- HIGH confidence (Odoo official docs)
- Odoo 17.0 Scheduled Actions: `ir.cron` XML data format -- HIGH confidence (Odoo official docs)
- Odoo 17.0 Performance: `index=True`, `store=True`, `_order`, `@ormcache` -- HIGH confidence (Odoo official docs)

---
*Architecture research for: v3.1 Design Flaws & Feature Gaps integration with existing Odoo module automation pipeline*
*Researched: 2026-03-05*
