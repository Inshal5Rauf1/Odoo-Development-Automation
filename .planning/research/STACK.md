# Stack Research: v3.1 Design Flaws & Feature Gaps

**Domain:** Odoo module automation -- spec design patterns, template generation, performance patterns
**Researched:** 2026-03-05
**Confidence:** HIGH

> **SCOPE:** This research covers ONLY the stack additions/changes needed for v3.1 features. The existing validated stack (Python 3.12, Jinja2, Click, pylint-odoo, ChromaDB, Docker, MCP, Context7) is unchanged. See previous STACK.md versions for prior research.

---

## Key Finding: Minimal New Dependencies

The v3.1 features are overwhelmingly **template and spec-parsing work**, not technology integrations. The existing stack (Jinja2 templates + Python spec analysis + AST-based tooling) already provides 90% of what is needed. Only one new library is genuinely required.

---

## New Stack Addition

### openpyxl (XLSX Import/Export Wizard Templates)

| Attribute | Value | Confidence |
|-----------|-------|------------|
| **Package** | `openpyxl` | HIGH (verified PyPI) |
| **Version** | 3.1.5 (Nov 2025) | HIGH (verified PyPI) |
| **Python** | >=3.8 | HIGH |
| **License** | MIT | HIGH |
| **Size** | ~4MB installed | HIGH |
| **Dependencies** | et_xmlfile only | HIGH |

**Why needed:** Import/export wizard templates must generate Python code that reads/writes `.xlsx` files. The generated Odoo modules will `import openpyxl` in their wizard code. Our templates need to produce correct openpyxl API calls, and our validation (Docker) needs openpyxl available in the Odoo container.

**Why openpyxl specifically:**
- Odoo's own web addon uses xlwt (old xls) and xlsxwriter (write-only). Neither reads xlsx.
- openpyxl handles both read AND write, which import wizards require.
- OCA's `excel_import_export` module uses openpyxl. Following OCA convention.
- No PyTorch, no heavy deps -- just `et_xmlfile` (~100KB).

**Integration points:**
1. **Jinja2 templates**: New `import_wizard.py.j2` and `export_wizard.py.j2` templates generate code that `import openpyxl`.
2. **Docker validation**: The Odoo Docker image needs openpyxl installed. Add to `docker-compose.yml` pip install or module `external_dependencies`.
3. **Module manifest**: Generated modules declare `"external_dependencies": {"python": ["openpyxl"]}`.

**NOT needed in our tooling venv:** openpyxl is only needed inside the generated modules (runtime), not in our template rendering pipeline. However, if we add template unit tests that import-check generated code, we would need it in the test venv.

### Installation

```bash
# Only needed in Docker validation image and generated module deps
# NOT in our core pyproject.toml dependencies

# For test venv (optional, only if testing generated import code):
uv add --dev openpyxl>=3.1.5
```

### pyproject.toml Change (Minimal)

```toml
[project.optional-dependencies]
# Add to existing test extras if testing generated wizard code
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "openpyxl>=3.1.5",  # For validating generated import/export wizard code
]
```

---

## No New Dependencies Needed For

These features are implemented entirely through new Jinja2 templates, spec-parsing logic, and knowledge base entries. No new Python libraries required.

### Spec Design Features

| Feature | Implementation | Why No New Deps |
|---------|---------------|-----------------|
| Relationship patterns (through-models, self-ref, hierarchical) | Spec parser logic + knowledge base rules | Pure Python dict/list analysis of spec structure |
| Computed field dependency chains | Spec parser + topological sort | `graphlib.TopologicalSorter` is in Python 3.12 stdlib |
| Complex constraints (cross-model, temporal, capacity) | Spec parser + template conditionals | Jinja2 `{% if %}` blocks in model.py.j2 |

### Template/Generation Features

| Feature | Implementation | Why No New Deps |
|---------|---------------|-----------------|
| Monetary field + currency_id injection | Spec analyzer + model.py.j2 extension | Pattern detection in spec dict, Jinja2 template output |
| QWeb report templates | New `report.xml.j2` + `report_template.xml.j2` | Pure XML/HTML generation via Jinja2 -- QWeb is just XML |
| Dashboard views (graph, pivot, cohort) | New `view_graph.xml.j2`, `view_pivot.xml.j2` | Pure XML generation via Jinja2 |
| HTTP controllers | New `controller.py.j2` + `controllers/__init__.py.j2` | Standard Odoo `http.Controller` -- pure Python template |
| Cron jobs (ir.cron) | New `cron.xml.j2` data file template | Pure XML data record generation via Jinja2 |

### Performance Features

| Feature | Implementation | Why No New Deps |
|---------|---------------|-----------------|
| Bulk operations (`@api.model_create_multi`) | model.py.j2 template extension | Decorator added in generated Python code |
| Database indexes | model.py.j2 `_sql_constraints` + index hints | Generated Python code uses Odoo's built-in index API |
| ormcache patterns | model.py.j2 template extension | `@tools.ormcache` is Odoo stdlib, not a pip dep |
| Archival/partitioning | model.py.j2 `active` field + cron.xml.j2 cleanup | Odoo's built-in active field pattern |

---

## Existing Stack Adequacy Assessment

### Jinja2 (Already Installed: >=3.1)

**Verdict: FULLY ADEQUATE.** All 8 new template types (report, graph, pivot, controller, cron, import_wizard, export_wizard, cohort) are Jinja2 templates rendering to Python or XML. No Jinja2 extensions or plugins needed.

Current Jinja2 features we already use that cover v3.1:
- `StrictUndefined` -- catches missing variables in new templates
- `FileSystemLoader` with version fallback -- new templates go in `shared/` or version-specific dirs
- Custom filters (`to_class`, `model_ref`, `to_python_var`, `to_xml_id`) -- reused in all new templates
- `trim_blocks`, `lstrip_blocks` -- clean output for XML templates

**New filters potentially needed:**

| Filter | Purpose | Implementation |
|--------|---------|----------------|
| `to_report_id` | Convert model name to QWeb report external ID | `lambda name: f"report_{name.replace('.', '_')}"` |
| `to_cron_id` | Convert action name to cron external ID | `lambda name: f"ir_cron_{name.replace('.', '_')}"` |
| `to_controller_route` | Convert model name to URL path | `lambda name: f"/{name.replace('.', '/')}"` |

These are trivial string transformations added to `_register_filters()` in `renderer.py`.

### Python stdlib (graphlib.TopologicalSorter)

**Verdict: FULLY ADEQUATE** for computed field dependency chain analysis.

```python
from graphlib import TopologicalSorter

# Example: resolving compute dependency order
deps = {"total": {"subtotal", "tax"}, "tax": {"subtotal"}, "subtotal": set()}
ts = TopologicalSorter(deps)
order = list(ts.static_order())  # ['subtotal', 'tax', 'total']
```

Available since Python 3.9, stable in 3.12. No external graph library needed.

### Python ast Module (Already Used Extensively)

**Verdict: FULLY ADEQUATE.** The existing AST-based auto-fix pipeline handles all the code analysis patterns needed for v3.1:
- Detecting monetary fields that need `currency_id` companion
- Analyzing compute dependency chains across model files
- Validating generated controller/wizard code for unused imports

### Docker Validation (Already Configured)

**Verdict: ADEQUATE with one addition.** The Docker `run --rm` pattern validates generated modules. For v3.1:
- QWeb reports require `wkhtmltopdf` -- already in Odoo Docker images
- Controllers need HTTP request testing -- covered by Odoo's test framework
- Cron jobs are XML data records -- validated by module install
- **Addition needed:** `openpyxl` must be pip-installed in the Docker image for import/export wizard validation

---

## Template File Plan (No Stack Impact, Pure Jinja2)

New templates to create in `python/src/odoo_gen_utils/templates/`:

| Template | Location | Generates |
|----------|----------|-----------|
| `report_action.xml.j2` | `shared/` | `ir.actions.report` record pointing to QWeb template |
| `report_template.xml.j2` | `shared/` | QWeb report body (`<t t-call="web.html_container">`) |
| `view_graph.xml.j2` | `shared/` | `<graph>` view with measure fields |
| `view_pivot.xml.j2` | `shared/` | `<pivot>` view with row/col/measure fields |
| `view_cohort.xml.j2` | `shared/` | `<cohort>` view (Enterprise only) |
| `controller.py.j2` | `shared/` | `http.Controller` with `@route` decorators |
| `init_controllers.py.j2` | `shared/` | Controllers `__init__.py` |
| `cron.xml.j2` | `shared/` | `ir.cron` XML data records |
| `import_wizard.py.j2` | `shared/` | TransientModel with openpyxl import logic |
| `export_wizard.py.j2` | `shared/` | TransientModel with openpyxl/xlsxwriter export logic |
| `import_wizard_form.xml.j2` | `shared/` | File upload wizard form view |
| `export_wizard_form.xml.j2` | `shared/` | Export config wizard form view |

**Version-specific overrides (17.0 vs 18.0):**
- Controller routes: identical across versions
- QWeb reports: identical across versions
- Dashboard views: `<cohort>` requires Enterprise, otherwise identical
- No version-specific templates expected for v3.1 features

---

## Renderer Changes Needed

### New Stage Functions

The existing 7-stage `render_module()` pipeline needs expansion:

| Current Stage | Status |
|---------------|--------|
| `render_manifest` | MODIFY -- add controller, report, cron files to manifest `data` list |
| `render_models` | MODIFY -- add monetary field injection, bulk operation decorators, index hints |
| `render_views` | MODIFY -- add graph/pivot/cohort view rendering |
| `render_security` | UNCHANGED |
| `render_wizards` | MODIFY -- add import/export wizard subtypes |
| `render_tests` | MODIFY -- add test templates for controllers, reports |
| `render_static` | MODIFY -- add cron.xml to data files |

New stages:

| New Stage | Purpose |
|-----------|---------|
| `render_controllers` | Generate `controllers/` directory with route handlers |
| `render_reports` | Generate QWeb report templates and actions |
| `render_crons` | Generate `data/cron.xml` with ir.cron records |

### New Spec Context Keys

`_build_model_context()` needs these additions:

| Key | Type | Purpose |
|-----|------|---------|
| `monetary_fields` | `list[dict]` | Fields with `type="Monetary"` needing `currency_id` |
| `has_monetary` | `bool` | Whether model has any Monetary fields |
| `compute_chain` | `list[str]` | Topologically sorted compute dependency order |
| `relationship_type` | `str` | `"standard"`, `"through"`, `"self_ref"`, `"hierarchical"` |
| `parent_store` | `bool` | Whether model uses `_parent_store = True` |
| `index_fields` | `list[str]` | Fields that should have `index=True` |
| `use_create_multi` | `bool` | Whether to add `@api.model_create_multi` |
| `ormcache_methods` | `list[dict]` | Methods needing `@tools.ormcache` |
| `is_archivable` | `bool` | Whether model has `active` field for soft-delete |
| `cron_actions` | `list[dict]` | Scheduled actions for this model |
| `controllers` | `list[dict]` | HTTP controller routes for this model |
| `reports` | `list[dict]` | QWeb reports for this model |

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| openpyxl 3.1.5 | xlsxwriter | xlsxwriter is write-only; import wizards need read capability |
| openpyxl 3.1.5 | pandas + openpyxl | pandas adds ~150MB of deps for simple row iteration. Overkill. |
| graphlib.TopologicalSorter (stdlib) | networkx | networkx is 5MB+ and we only need topological sort, which stdlib provides |
| Jinja2 templates for QWeb | Python string formatting | Jinja2 is already our rendering engine; adding another output method fragments the codebase |
| No new ORM/DB library | SQLAlchemy for index analysis | Odoo manages its own schema; we generate code, not run migrations |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pandas` | 150MB+ for simple xlsx row reading. Generated modules should use openpyxl directly. | openpyxl (4MB) |
| `networkx` | Overkill for topological sort. Only needed if building full dependency graphs. | `graphlib.TopologicalSorter` (stdlib) |
| `xlsxwriter` as new dep | Already available in Odoo's Python environment. Generated export wizards can use it without us adding it. | Reference in template; Odoo ships it |
| `wkhtmltopdf` (in tooling) | Only needed at runtime in Docker. Already in Odoo Docker images. | Docker validation handles this |
| `reportlab` | Odoo uses wkhtmltopdf for PDF, not reportlab. Wrong tool. | QWeb + wkhtmltopdf (Odoo's built-in approach) |
| `lxml` as new dep | Already available in Odoo's Python environment. We generate XML via Jinja2, not lxml. | Jinja2 template rendering |
| Any REST framework (Flask, FastAPI) | Generated controllers use Odoo's built-in `http.Controller`. No external framework. | Odoo's `odoo.http` module |
| `APScheduler` or `celery` | Odoo has `ir.cron` for scheduling. External schedulers conflict with Odoo's worker model. | `ir.cron` XML records |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| openpyxl>=3.1.5 | Python 3.12 | Verified on PyPI. No conflicts with existing deps. |
| openpyxl>=3.1.5 | Odoo 17.0 Docker image | Must be pip-installed in container. Add to module `external_dependencies`. |
| openpyxl>=3.1.5 | Odoo 18.0 Docker image | Same as 17.0. |
| graphlib (stdlib) | Python 3.9+ | Built-in. No install needed. |

### Odoo Version Differences Affecting Templates

| Feature | Odoo 17.0 | Odoo 18.0 | Template Impact |
|---------|-----------|-----------|-----------------|
| `@api.model_create_multi` | Available | Available | Same template for both |
| `tools.ormcache` | Available | Available | Same template for both |
| `_sql_constraints` | Tuple format | Tuple format | Same template for both |
| QWeb reports | `t-call="web.html_container"` | Same | Same template for both |
| HTTP controllers | `@route()` decorator | Same | Same template for both |
| `ir.cron` | XML `<record>` format | Same | Same template for both |
| `display_name` vs `name_get` | `name_get()` method | `_compute_display_name()` | Already handled in v3.0 version gate |
| Cohort view | Enterprise only | Enterprise only | Same; gate on edition in spec |
| Database indexes | `index=True` on field | Declarative Index API | May need version-specific template for 18.0 indexes |

**Action item:** The declarative Index API in Odoo 18.0 (`from odoo import models, Index`) may warrant a version-specific `model.py.j2` override in `templates/18.0/` for index definitions. Research this during implementation if generating explicit composite indexes.

---

## Docker Image Changes

The existing `docker-compose.yml` needs a minor addition for v3.1:

```yaml
# In the Odoo service, add pip install for import/export wizard deps
command: >
  bash -c "pip install openpyxl>=3.1.5 &&
  odoo --test-tags=${MODULE} -d test --stop-after-init"
```

Alternatively, generated modules declare `external_dependencies` in `__manifest__.py`:

```python
"external_dependencies": {
    "python": ["openpyxl"],
},
```

Odoo will check for openpyxl at module install time and raise a clear error if missing. This is the OCA-standard approach.

---

## Summary: Stack Delta for v3.1

| Category | Change | Impact |
|----------|--------|--------|
| **New dependency** | `openpyxl>=3.1.5` (test/Docker only) | +4MB, zero risk |
| **New stdlib usage** | `graphlib.TopologicalSorter` | Zero cost, already in Python 3.12 |
| **New Jinja2 filters** | 3 trivial string transforms | ~10 lines in renderer.py |
| **New templates** | 12 new `.j2` files | Core deliverable of v3.1 |
| **New renderer stages** | 3 new stage functions | ~200-300 lines total |
| **New spec context keys** | 12 new keys in `_build_model_context()` | ~100 lines in renderer.py |
| **Docker changes** | openpyxl pip install | 1-line addition |
| **pyproject.toml** | openpyxl in test extras | 1-line addition |

**Total new external dependencies: 1 (openpyxl)**
**Total new Python code: ~500-700 lines** (renderer extensions + spec analysis)
**Total new template files: 12**

This is a clean, low-risk stack evolution. The architecture stays the same. The renderer pipeline extends naturally. No paradigm shifts.

---

## Sources

- [openpyxl PyPI](https://pypi.org/project/openpyxl/) -- version 3.1.5 verified (HIGH confidence)
- [openpyxl Documentation](https://openpyxl.readthedocs.io/) -- API reference (HIGH confidence)
- [Odoo 17 QWeb Reports](https://www.odoo.com/documentation/17.0/developer/reference/backend/reports.html) -- report template patterns (HIGH confidence)
- [Odoo 17 Web Controllers](https://www.odoo.com/documentation/17.0/developer/reference/backend/http.html) -- controller route patterns (HIGH confidence)
- [Odoo 17 ORM API](https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html) -- ormcache, model_create_multi (HIGH confidence)
- [OCA excel_import_export Discussion](https://github.com/orgs/OCA/discussions/154) -- OCA xlsx wizard patterns (MEDIUM confidence)
- [Odoo 17 Scheduled Actions](https://www.cybrosys.com/blog/how-to-configure-scheduled-actions-in-odoo-17) -- ir.cron patterns (MEDIUM confidence)
- [Odoo Query Optimizations](https://stormatics.tech/blogs/query-optimizations-in-odoo-versions-17-19-for-faster-postgresql-performance) -- index/performance patterns (MEDIUM confidence)
- [Python graphlib docs](https://docs.python.org/3.12/library/graphlib.html) -- TopologicalSorter API (HIGH confidence)

---
*Stack research for: v3.1 Design Flaws & Feature Gaps*
*Researched: 2026-03-05*
