# Phase 31: Reports & Analytics - Research

**Researched:** 2026-03-06
**Domain:** Odoo QWeb report generation + graph/pivot dashboard view generation
**Confidence:** HIGH

## Summary

Phase 31 implements two distinct features in the `render_reports` stage: (1) QWeb PDF report generation with `ir.actions.report` XML, QWeb templates using `t-foreach`/`t-field`, optional paper format records, and a print button on the model's form view; and (2) graph/pivot dashboard view generation with `ir.ui.view` records containing `<graph>` and `<pivot>` arch elements with configurable measures, dimensions, and an `ir.actions.act_window` with `view_mode` including `graph,pivot`.

The codebase already has a placeholder `render_reports()` function returning `Result.ok([])` (wired in Phase 30, stage 9 of 10). This phase replaces the placeholder with real logic. The existing patterns from `render_cron`, `render_views`, and `render_wizards` provide clear blueprints -- each creates Jinja2 templates in `templates/shared/`, builds a context dict, calls `render_template()`, and returns `Result[list[Path]]`. The form view template (`view_form.xml.j2`) already has a `<header>` section (inside `{% if state_field %}`) where wizard buttons are injected; report print buttons follow the same pattern.

Odoo 17 uses `binding_model_id` on `ir.actions.report` to automatically add reports to the Print menu dropdown on a model's form/list views. This means no explicit button is needed in the form view header -- `binding_model_id` handles it. However, the success criteria says "form view gets a print button," so we should inject a `<button type="action">` in the form header as a direct print shortcut, in addition to `binding_model_id` for the Print menu.

**Primary recommendation:** Create 4 new Jinja2 templates (`report_action.xml.j2`, `report_template.xml.j2`, `graph_view.xml.j2`, `pivot_view.xml.j2`) in `templates/shared/`, implement `render_reports()` to produce report XML + QWeb template + optional paper format + graph/pivot views, extend `_build_module_context()` to add report/dashboard data files to the manifest, and modify `view_form.xml.j2` to inject print buttons for models with reports.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TMPL-01 | Generator produces QWeb report templates (`ir.actions.report` XML + QWeb template) with form view button, paper format, and `t-foreach`/`t-field` syntax | Report action XML template, QWeb template with `t-call`/`t-foreach`/`t-field`, paper format record, `binding_model_id` for Print menu + explicit button in form header |
| TMPL-02 | Generator produces graph and pivot view XML with configurable measures, dimensions, chart types, and `ir.actions.act_window` with graph/pivot view_mode | Graph view template with `<graph>` element + `type` attribute + measure fields, pivot view template with row/col/measure fields, modified action.xml.j2 to include `graph,pivot` in `view_mode` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | (existing) | Template rendering for report/graph/pivot XML | Already in use for all XML generation |
| Python 3.12 | (existing) | Render stage logic in renderer.py | Already in use |

### Supporting
No new libraries needed. This is pure template + pipeline logic.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate report_action.xml.j2 + report_template.xml.j2 | Single combined template | Separate files follow existing pattern (action.xml.j2 vs view_form.xml.j2 are separate) and are easier to maintain |
| Modifying action.xml.j2 to conditionally add graph,pivot | Separate dashboard_action.xml.j2 | Modifying existing template is simpler; dashboard action uses same `ir.actions.act_window` model as the existing action |

**Installation:**
No new packages needed.

## Architecture Patterns

### Recommended Project Structure

New/modified files:
```
python/src/odoo_gen_utils/
  renderer.py                                    # render_reports() implementation + _build_module_context() changes
  templates/shared/
    report_action.xml.j2                         # NEW: ir.actions.report + optional paper format
    report_template.xml.j2                       # NEW: QWeb t-call/t-foreach/t-field template
    graph_view.xml.j2                            # NEW: graph view ir.ui.view
    pivot_view.xml.j2                            # NEW: pivot view ir.ui.view
  templates/17.0/
    view_form.xml.j2                             # MODIFIED: inject print button in header
    action.xml.j2                                # MODIFIED: conditionally add graph,pivot to view_mode
  templates/18.0/
    view_form.xml.j2                             # MODIFIED: same print button injection
    action.xml.j2                                # MODIFIED: same view_mode extension
```

### Pattern 1: Odoo 17 ir.actions.report Record

**What:** The XML record that registers a report action with PDF rendering.
**When to use:** For each entry in `spec.reports`.

```xml
<!-- Source: Odoo 17.0 official docs + Odoo forum verification -->
<record id="report_{{ module_name }}_{{ report.xml_id }}" model="ir.actions.report">
    <field name="name">{{ report.name }}</field>
    <field name="model">{{ report.model_name }}</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">{{ module_name }}.report_{{ report.xml_id }}</field>
    <field name="binding_model_id" ref="model_{{ report.model_name | to_xml_id }}"/>
    <field name="binding_type">report</field>
{% if report.paper_format %}
    <field name="paperformat_id" ref="{{ module_name }}.paperformat_{{ report.xml_id }}"/>
{% endif %}
</record>
```

**Key fields:**
- `report_type`: Always `qweb-pdf` for PDF reports
- `report_name`: Must match the QWeb template `id` (prefixed with module name)
- `binding_model_id`: Auto-adds report to Print dropdown on the model's views
- `binding_type`: Defaults to `report` for `ir.actions.report`, but explicit is clearer
- `paperformat_id`: Optional ref to a `report.paperformat` record

### Pattern 2: QWeb Report Template

**What:** The HTML/QWeb template rendered by wkhtmltopdf into PDF.
**When to use:** Paired 1:1 with each ir.actions.report record.

```xml
<!-- Source: Odoo 17.0 QWeb Reports documentation -->
<template id="report_{{ report.xml_id }}">
    <t t-call="web.html_container">
        <t t-foreach="docs" t-as="doc">
            <t t-call="web.external_layout">
                <div class="page">
                    <h2><span t-field="doc.display_name"/></h2>
                    <table class="table table-sm">
                        <thead>
                            <tr>
{% for col in report.columns %}
                                <th>{{ col.label }}</th>
{% endfor %}
                            </tr>
                        </thead>
                        <tbody>
{% if report.detail_field %}
                            <tr t-foreach="doc.{{ report.detail_field }}" t-as="line">
{% for col in report.columns %}
                                <td><span t-field="line.{{ col.field }}"/></td>
{% endfor %}
                            </tr>
{% else %}
{% for col in report.columns %}
                            <tr>
                                <td>{{ col.label }}</td>
                                <td><span t-field="doc.{{ col.field }}"/></td>
                            </tr>
{% endfor %}
{% endif %}
                        </tbody>
                    </table>
                </div>
            </t>
        </t>
    </t>
</template>
```

**Key elements:**
- `t-call="web.html_container"`: Required wrapper for PDF reports
- `t-foreach="docs" t-as="doc"`: Iterates over selected records
- `t-call="web.external_layout"`: Adds company header/footer
- `t-field="doc.field_name"`: Renders field value with proper formatting
- `class="page"`: CSS page break boundary

### Pattern 3: Paper Format Record

**What:** Optional custom paper dimensions/margins for a report.
**When to use:** When `report.paper_format` is specified in the spec.

```xml
<!-- Source: Odoo report.paperformat model -->
<record id="paperformat_{{ report.xml_id }}" model="report.paperformat">
    <field name="name">{{ report.name }} Format</field>
    <field name="format">{{ report.paper_format.format | default('A4') }}</field>
    <field name="orientation">{{ report.paper_format.orientation | default('Portrait') }}</field>
    <field name="margin_top">{{ report.paper_format.margin_top | default(20) }}</field>
    <field name="margin_bottom">{{ report.paper_format.margin_bottom | default(20) }}</field>
    <field name="margin_left">{{ report.paper_format.margin_left | default(7) }}</field>
    <field name="margin_right">{{ report.paper_format.margin_right | default(7) }}</field>
    <field name="header_spacing">{{ report.paper_format.header_spacing | default(35) }}</field>
</record>
```

### Pattern 4: Graph View

**What:** Bar/line/pie chart visualization of model data.
**When to use:** For each model with `dashboards`/`analytics` entries.

```xml
<!-- Source: Odoo 17 Views documentation -->
<record id="view_{{ model_xml_id }}_graph" model="ir.ui.view">
    <field name="name">{{ model_name }}.view.graph</field>
    <field name="model">{{ model_name }}</field>
    <field name="arch" type="xml">
        <graph string="{{ dashboard.title | default(model_description + ' Analysis') }}"
               type="{{ dashboard.chart_type | default('bar') }}"
{% if dashboard.stacked %}
               stacked="True"
{% endif %}
        >
{% for dim in dashboard.dimensions %}
            <field name="{{ dim.field }}"{% if dim.interval %} interval="{{ dim.interval }}"{% endif %}/>
{% endfor %}
{% for measure in dashboard.measures %}
            <field name="{{ measure.field }}" type="measure"/>
{% endfor %}
        </graph>
    </field>
</record>
```

**Graph types:** `bar` (default), `line`, `pie`
**Field roles:** First field(s) without `type="measure"` are dimensions (grouping); fields with `type="measure"` are aggregated values.

### Pattern 5: Pivot View

**What:** Pivot table with row/column groupings and measures.
**When to use:** Paired with graph view for analytics.

```xml
<!-- Source: Odoo 17 Views documentation -->
<record id="view_{{ model_xml_id }}_pivot" model="ir.ui.view">
    <field name="name">{{ model_name }}.view.pivot</field>
    <field name="model">{{ model_name }}</field>
    <field name="arch" type="xml">
        <pivot string="{{ dashboard.title | default(model_description + ' Analysis') }}"
               disable_linking="True"
               sample="1"
        >
{% for row in dashboard.rows %}
            <field name="{{ row.field }}" type="row"{% if row.interval %} interval="{{ row.interval }}"{% endif %}/>
{% endfor %}
{% for col in dashboard.columns %}
            <field name="{{ col.field }}" type="col"{% if col.interval %} interval="{{ col.interval }}"{% endif %}/>
{% endfor %}
{% for measure in dashboard.measures %}
            <field name="{{ measure.field }}" type="measure"/>
{% endfor %}
        </pivot>
    </field>
</record>
```

**Key attributes:**
- `type="row"`: Vertical grouping dimension
- `type="col"`: Horizontal grouping dimension
- `type="measure"`: Aggregated numeric field (must be Integer, Float, or Monetary; must be `store=True` for computed fields)
- `interval`: For date fields -- `day`, `week`, `month`, `quarter`, `year`
- `disable_linking="True"`: Prevents drill-down to list view
- `sample="1"`: Shows sample data when no records exist

### Pattern 6: Dashboard Action (view_mode extension)

**What:** Extend the existing `ir.actions.act_window` to include graph and pivot views.
**When to use:** When a model has dashboard/analytics entries.

```xml
<!-- Modified action.xml.j2 -->
<record id="action_{{ model_name | to_xml_id }}" model="ir.actions.act_window">
    <field name="name">{{ model_description }}</field>
    <field name="res_model">{{ model_name }}</field>
    <field name="view_mode">tree,form{% if has_dashboard %},graph,pivot{% endif %}</field>
    ...
</record>
```

### Pattern 7: Form View Print Button

**What:** A button in the form view header that triggers report printing.
**When to use:** For models that have reports defined.

```xml
<!-- In view_form.xml.j2 header section -->
{% for report in model_reports %}
                    <button name="report_{{ module_name }}_{{ report.xml_id }}"
                            string="{{ report.button_label | default('Print ' + report.name) }}"
                            type="action"
                            class="btn-secondary"/>
{% endfor %}
```

**Note:** The `name` must match the `ir.actions.report` record's XML ID. The `type="action"` tells Odoo to look up the action by XML ID and execute it. Combined with `binding_model_id`, the report appears both as a direct button AND in the Print dropdown.

### Pattern 8: Render Stage Function

**What:** The `render_reports()` implementation following existing stage patterns.
**When to use:** Replaces the Phase 30 placeholder.

```python
def render_reports(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render QWeb report templates and graph/pivot dashboard views.

    Handles two spec sections:
    - spec["reports"]: ir.actions.report + QWeb template + optional paper format
    - spec["dashboards"]: graph view + pivot view per model

    Returns Result.ok([]) when neither section is present.
    """
    try:
        reports = spec.get("reports", [])
        dashboards = spec.get("dashboards", [])
        if not reports and not dashboards:
            return Result.ok([])
        created: list[Path] = []

        # Reports
        for report in reports:
            report_ctx = {**module_context, "report": report}
            created.append(render_template(
                env, "report_action.xml.j2",
                module_dir / "data" / f"report_{report['xml_id']}.xml",
                report_ctx,
            ))
            created.append(render_template(
                env, "report_template.xml.j2",
                module_dir / "data" / f"report_{report['xml_id']}_template.xml",
                report_ctx,
            ))

        # Dashboards (graph + pivot)
        for dashboard in dashboards:
            dash_ctx = {**module_context, "dashboard": dashboard,
                        "model_xml_id": _to_xml_id(dashboard["model_name"])}
            created.append(render_template(
                env, "graph_view.xml.j2",
                module_dir / "views" / f"{_to_xml_id(dashboard['model_name'])}_graph.xml",
                dash_ctx,
            ))
            created.append(render_template(
                env, "pivot_view.xml.j2",
                module_dir / "views" / f"{_to_xml_id(dashboard['model_name'])}_pivot.xml",
                dash_ctx,
            ))

        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_reports failed: {exc}")
```

### Pattern 9: Spec Schema for Reports and Dashboards

**What:** The expected structure of spec entries.
**When to use:** As the contract between spec input and template rendering.

```python
# Each spec["reports"] entry:
{
    "name": "Student Report Card",             # Human-readable name
    "model_name": "academy.student",           # Dotted Odoo model name
    "xml_id": "student_report_card",           # XML-safe ID suffix
    "columns": [                               # Fields to display
        {"field": "name", "label": "Student Name"},
        {"field": "enrollment_date", "label": "Enrolled"},
    ],
    "detail_field": "enrollment_ids",          # Optional: One2many for line items
    "button_label": "Print Report Card",       # Optional: form button label
    "paper_format": {                          # Optional: custom paper format
        "format": "A4",
        "orientation": "Portrait",
        "margin_top": 20,
    },
}

# Each spec["dashboards"] entry:
{
    "model_name": "academy.enrollment",        # Dotted Odoo model name
    "title": "Enrollment Analysis",            # Optional title
    "chart_type": "bar",                       # bar|line|pie (default: bar)
    "stacked": False,                          # Optional (default: False)
    "dimensions": [                            # Grouping fields (graph)
        {"field": "course_id"},
        {"field": "enrollment_date", "interval": "month"},
    ],
    "measures": [                              # Aggregated fields
        {"field": "total_fee"},
    ],
    "rows": [                                  # Pivot row groupings
        {"field": "course_id"},
    ],
    "columns": [                               # Pivot column groupings
        {"field": "enrollment_date", "interval": "quarter"},
    ],
}
```

### Anti-Patterns to Avoid

- **Omitting `binding_model_id`:** Without it, the report does not appear in the Print dropdown menu. Users expect Print menu integration.
- **Using `report_file` instead of `report_name`:** `report_file` is for non-QWeb (jasper/external) reports. QWeb reports use `report_name` pointing to the template XML ID.
- **Non-stored computed fields as measures:** Odoo aggregates measures via SQL. Non-stored computed fields cannot be used in graph/pivot views. The spec should only allow `store=True` fields as measures.
- **Forgetting `web.html_container`/`web.external_layout`:** Reports render as blank pages without these wrapping calls. They provide the HTML structure and company header/footer.
- **Missing `class="page"` on the content div:** Without it, wkhtmltopdf does not know where to insert page breaks between records.
- **Hardcoding graph type:** Always use a configurable `chart_type` field defaulting to `bar`. Different data patterns need different visualizations.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF rendering | Custom PDF library | Odoo's built-in wkhtmltopdf + QWeb | Odoo handles PDF rendering, headers, footers, pagination |
| Print menu integration | Custom JavaScript button | `binding_model_id` on `ir.actions.report` | Odoo's binding system auto-adds to Print menu |
| Report layout/header/footer | Custom HTML header/footer | `t-call="web.external_layout"` | Uses company's configured header/footer |
| Data aggregation in views | Custom SQL queries | Graph/pivot view arch + field `type="measure"` | Odoo handles SQL aggregation automatically |
| Paper format management | Hardcoded margins | `report.paperformat` record | Users can customize via Settings |

**Key insight:** Odoo's report and analytics infrastructure is declarative -- you describe what you want in XML, and Odoo handles rendering, aggregation, and UI integration. The generator should produce correct declarative XML, not procedural code.

## Common Pitfalls

### Pitfall 1: report_name Must Match Template ID
**What goes wrong:** Report action exists but clicking Print shows blank/error because the template cannot be found.
**Why it happens:** `report_name` value (e.g., `module.report_student_card`) does not match the QWeb `<template id="report_student_card">`.
**How to avoid:** Use the convention `report_name = f"{module_name}.report_{report.xml_id}"` and `template id = f"report_{report.xml_id}"`. Both derive from the same `xml_id`.
**Warning signs:** `Report template not found` error when printing, or blank PDF.

### Pitfall 2: Report Data Files Not in Manifest
**What goes wrong:** Report XML is generated but not loaded because it is not in `__manifest__.py["data"]`.
**Why it happens:** `_build_module_context()` does not add report data files to `data_files`.
**How to avoid:** Add `data/report_*.xml` files to `data_files` when `spec.get("reports")` is non-empty. Add `views/*_graph.xml` and `views/*_pivot.xml` to the view files list when dashboards exist.
**Warning signs:** Reports don't appear in Print menu; graph/pivot views not available.

### Pitfall 3: Graph/Pivot Views Not Accessible
**What goes wrong:** Graph and pivot views exist but users cannot switch to them.
**Why it happens:** The `ir.actions.act_window` `view_mode` still says `tree,form` without `graph,pivot`.
**How to avoid:** Modify `action.xml.j2` to conditionally append `,graph,pivot` when the model has dashboard entries. Pass `has_dashboard` flag in model context.
**Warning signs:** No graph/pivot icons in the view switcher toolbar.

### Pitfall 4: Measure Fields Not Stored
**What goes wrong:** Pivot/graph view shows "Cannot aggregate field X" or no data.
**Why it happens:** Computed fields used as measures lack `store=True`, so Odoo cannot perform SQL aggregation.
**How to avoid:** In the spec schema, validate that measure fields are numeric (Integer, Float, Monetary) types. Document that computed measures must have `store=True`. The generator should warn (not fail) when a measure references a field name not found on the model.
**Warning signs:** Empty pivot table, "Error loading data" in graph view.

### Pitfall 5: Print Button XML ID Mismatch
**What goes wrong:** Clicking the print button on the form raises "Action not found."
**Why it happens:** The button `name` attribute does not match the `ir.actions.report` record's full XML ID (including module prefix).
**How to avoid:** Use the naming convention `name="%(module_name.report_module_xml_id)d"` for cross-module references, or just the report record ID if same module. In the template: `name="%(report_{{ module_name }}_{{ report.xml_id }})d"`.
**Warning signs:** `MissingError: Record does not exist` when clicking Print button.

### Pitfall 6: QWeb Template Outside <odoo> Tag
**What goes wrong:** Template is silently ignored during module install.
**Why it happens:** QWeb templates must be wrapped in `<odoo>` root tag to be loaded as data files.
**How to avoid:** Always wrap report templates in `<?xml version="1.0" encoding="utf-8"?>\n<odoo>...</odoo>`.
**Warning signs:** Module installs fine but report template is not registered.

## Code Examples

### Report Spec Example

```json
{
    "module_name": "academy",
    "models": [
        {
            "name": "academy.student",
            "fields": [
                {"name": "name", "type": "Char", "required": true},
                {"name": "enrollment_date", "type": "Date"},
                {"name": "total_credits", "type": "Integer"}
            ]
        }
    ],
    "reports": [
        {
            "name": "Student Report Card",
            "model_name": "academy.student",
            "xml_id": "student_report_card",
            "columns": [
                {"field": "name", "label": "Student"},
                {"field": "enrollment_date", "label": "Enrollment Date"},
                {"field": "total_credits", "label": "Credits"}
            ],
            "button_label": "Print Report Card"
        }
    ],
    "dashboards": [
        {
            "model_name": "academy.student",
            "title": "Student Analysis",
            "chart_type": "bar",
            "dimensions": [
                {"field": "enrollment_date", "interval": "month"}
            ],
            "measures": [
                {"field": "total_credits"}
            ],
            "rows": [
                {"field": "enrollment_date", "interval": "quarter"}
            ],
            "columns": []
        }
    ]
}
```

### Module Context Enrichment for Reports/Dashboards

```python
# In _build_module_context():

# Phase 31: report data files
reports = spec.get("reports", [])
for report in reports:
    data_files.append(f"data/report_{report['xml_id']}.xml")
    data_files.append(f"data/report_{report['xml_id']}_template.xml")

# Phase 31: dashboard view files
dashboards = spec.get("dashboards", [])
dashboard_models = set()
for dashboard in dashboards:
    model_xml = _to_xml_id(dashboard["model_name"])
    if model_xml not in dashboard_models:
        dashboard_models.add(model_xml)
        # These go into the manifest after model views
```

### Model Context Enrichment

```python
# In _build_model_context():

# Phase 31: reports targeting this model
model_reports = [
    r for r in spec.get("reports", [])
    if r.get("model_name") == model["name"]
]

# Phase 31: dashboards targeting this model
model_dashboards = [
    d for d in spec.get("dashboards", [])
    if d.get("model_name") == model["name"]
]
has_dashboard = bool(model_dashboards)

# Add to return dict:
# "model_reports": model_reports,
# "has_dashboard": has_dashboard,
```

### Form View Print Button Injection

```jinja2
{# In view_form.xml.j2, inside the <header> section #}
{% for report in model_reports %}
                    <button name="%(report_{{ module_name }}_{{ report.xml_id }})d"
                            string="{{ report.button_label | default('Print') }}"
                            type="action"
                            class="btn-secondary"/>
{% endfor %}
```

### Action Template view_mode Extension

```jinja2
{# In action.xml.j2 #}
<field name="view_mode">tree,form{% if has_dashboard %},graph,pivot{% endif %}</field>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `<report>` shortcut tag | `<record model="ir.actions.report">` | Odoo 11+ | `<report>` still works but `<record>` is more explicit and standard |
| Manual Print button only | `binding_model_id` auto-binding | Odoo 11+ | Reports auto-appear in Print menu; manual button optional |
| `<openerp>` root tag | `<odoo>` root tag | Odoo 10+ | Standard for all XML data files |
| Separate graph/pivot actions | Single action with `view_mode=tree,form,graph,pivot` | Odoo 12+ | Unified action switches between all view types |

**Deprecated/outdated:**
- `<report>` shortcut tag: Still works but `<record model="ir.actions.report">` is preferred for clarity
- Separate `ir.actions.act_window` for graph/pivot: Use single action with extended `view_mode`

## Open Questions

1. **Should report template files go in `data/` or `report/`?**
   - What we know: Odoo convention allows both. Some modules use `report/` directory, others use `data/`.
   - Recommendation: Use `data/` for consistency with existing project patterns (cron_data.xml, sequences.xml). The report action and template are data files loaded at install.

2. **Should dashboard views have their own manifest file entries or be appended to existing view files?**
   - What we know: Existing views are per-model (`views/{model}_views.xml`). Graph/pivot are also per-model.
   - Recommendation: Separate files (`views/{model}_graph.xml`, `views/{model}_pivot.xml`) for clean separation. Add to manifest between model view files and menu.xml.

3. **How should `view_form.xml.j2` handle the print button when no `state_field` exists?**
   - What we know: Currently, the `<header>` section only renders when `state_field` is present. Print buttons need a header.
   - Recommendation: Create a `<header>` section also when `model_reports` is non-empty. The template already conditionally renders header content; extend the condition to `{% if state_field or model_reports %}`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `python/pyproject.toml` |
| Quick run command | `cd python && .venv/bin/python -m pytest tests/test_renderer.py tests/test_render_stages.py -x -q` |
| Full suite command | `cd python && .venv/bin/python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TMPL-01a | Spec with reports generates ir.actions.report XML | integration | `pytest tests/test_render_stages.py::TestRenderReports::test_report_generates_action_xml -x` | Wave 0 |
| TMPL-01b | Report action has binding_model_id + report_name | unit | `pytest tests/test_render_stages.py::TestRenderReports::test_report_action_fields -x` | Wave 0 |
| TMPL-01c | QWeb template has t-call/t-foreach/t-field | integration | `pytest tests/test_render_stages.py::TestRenderReports::test_report_qweb_template -x` | Wave 0 |
| TMPL-01d | Optional paper format record generated | unit | `pytest tests/test_render_stages.py::TestRenderReports::test_report_paper_format -x` | Wave 0 |
| TMPL-01e | Form view gets print button for report | integration | `pytest tests/test_render_stages.py::TestRenderReports::test_form_print_button -x` | Wave 0 |
| TMPL-01f | No reports: render_reports returns Result.ok([]) for report section | unit | `pytest tests/test_render_stages.py::TestRenderReports::test_no_reports_noop -x` | Wave 0 |
| TMPL-01g | Report data files appear in manifest | unit | `pytest tests/test_renderer.py::TestBuildModuleContextReports -x` | Wave 0 |
| TMPL-02a | Spec with dashboards generates graph view XML | integration | `pytest tests/test_render_stages.py::TestRenderDashboards::test_graph_view -x` | Wave 0 |
| TMPL-02b | Graph view has measures and dimensions | unit | `pytest tests/test_render_stages.py::TestRenderDashboards::test_graph_measures -x` | Wave 0 |
| TMPL-02c | Pivot view has row/col/measure fields | integration | `pytest tests/test_render_stages.py::TestRenderDashboards::test_pivot_view -x` | Wave 0 |
| TMPL-02d | Action view_mode includes graph,pivot when dashboard exists | integration | `pytest tests/test_render_stages.py::TestRenderDashboards::test_action_view_mode -x` | Wave 0 |
| TMPL-02e | No dashboards: no graph/pivot files generated | unit | `pytest tests/test_render_stages.py::TestRenderDashboards::test_no_dashboards_noop -x` | Wave 0 |
| TMPL-02f | Dashboard view files appear in manifest | unit | `pytest tests/test_renderer.py::TestBuildModuleContextDashboards -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && .venv/bin/python -m pytest tests/test_renderer.py tests/test_render_stages.py -x -q`
- **Per wave merge:** `cd python && .venv/bin/python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green (699+ tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `python/src/odoo_gen_utils/templates/shared/report_action.xml.j2` -- report action + paper format template
- [ ] `python/src/odoo_gen_utils/templates/shared/report_template.xml.j2` -- QWeb report body template
- [ ] `python/src/odoo_gen_utils/templates/shared/graph_view.xml.j2` -- graph view template
- [ ] `python/src/odoo_gen_utils/templates/shared/pivot_view.xml.j2` -- pivot view template
- [ ] `tests/test_render_stages.py::TestRenderReports` -- report generation tests
- [ ] `tests/test_render_stages.py::TestRenderDashboards` -- dashboard generation tests
- [ ] `tests/test_renderer.py::TestBuildModuleContextReports` -- manifest includes report files
- [ ] `tests/test_renderer.py::TestBuildModuleContextDashboards` -- manifest includes dashboard files
- [ ] `tests/test_renderer.py::TestBuildModelContextReports` -- model_reports and has_dashboard in context

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `renderer.py` (~1370 lines, 10 render stages, `render_reports()` placeholder at line 1229)
- Codebase analysis: `templates/17.0/action.xml.j2` (existing action template with `view_mode`)
- Codebase analysis: `templates/17.0/view_form.xml.j2` (form view with header/button injection pattern)
- Codebase analysis: `test_render_stages.py` (stage test patterns, `_make_spec()` helpers)
- [Odoo 17.0 QWeb Reports documentation](https://www.odoo.com/documentation/17.0/developer/reference/backend/reports.html) -- ir.actions.report, QWeb template structure, binding_model_id

### Secondary (MEDIUM confidence)
- [Odoo 17.0 Actions documentation](https://www.odoo.com/documentation/17.0/developer/reference/backend/actions.html) -- binding_model_id, binding_type
- [Odoo Pivot/Graph View examples](https://sgeede.com/blog/sgeede-knowledge-4/how-to-custom-pivot-graph-view-in-odoo-139) -- field type="row"/"col"/"measure" patterns
- [Odoo Forum: report.paperformat XML](https://www.odoo.com/forum/help-1/how-do-you-add-a-new-report-paper-format-in-a-module-using-xml-92372) -- paper format field names
- [Cybrosys: Pivot View in Odoo 17](https://www.cybrosys.com/blog/how-to-create-pivot-view-in-odoo-17) -- pivot view XML structure

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure pipeline extension
- Architecture: HIGH -- follows exact existing render stage pattern; placeholder already wired
- Pitfalls: HIGH -- Odoo report/view XML format well-documented; 6 pitfalls identified from official docs + forum posts
- Report XML format: HIGH -- verified against Odoo 17 official documentation
- Graph/Pivot XML format: HIGH -- verified against multiple sources including official docs

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable domain; report and view APIs unchanged since Odoo 12+)
