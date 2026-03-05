# Phase 33: Database Performance - Research

**Researched:** 2026-03-06
**Domain:** Odoo ORM performance patterns (index, store, sql_constraints, TransientModel cleanup)
**Confidence:** HIGH

## Summary

Phase 33 adds a preprocessor step to `render_module()` that automatically enriches field specs with performance attributes based on how fields are used in views, search filters, record rules, and ordering. The core logic is: analyze the spec to find which fields appear in search views, tree views, `_order`, and record rule domains, then set `index=True` on filterable fields, `store=True` on computed fields used in views, auto-generate `_sql_constraints` from multi-field uniqueness declarations, and add `_transient_max_hours`/`_transient_max_count` to TransientModel classes.

This phase depends on Phase 28's computation chain awareness (knowing which fields are computed) and builds a new preprocessor function `_process_performance()` that runs in `render_module()` after `_process_computation_chains()`. The template changes are minimal since `index=True` and `store=True` are already supported in the model.py.j2 templates -- the main work is in the preprocessor and expanding the template to render `index=True` for ALL field types (currently only Many2one/One2many/Many2many render it).

**Primary recommendation:** Implement a `_process_performance()` pure function preprocessor (matching the pattern of `_process_relationships`, `_process_computation_chains`, `_process_constraints`) that enriches field dicts and model dicts with performance attributes, plus template updates for `_order`, `_transient_max_hours`/`_transient_max_count`, and `index=True` on non-relational fields.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PERF-01 | Renderer auto-adds `index=True` to fields used in search view filters, record rule domains, or `_order`; generates composite `_sql_constraints` for multi-field uniqueness | Preprocessor `_process_performance()` scans view_fields/search criteria/model._order to set field.index=True; auto-generates `_sql_constraints` list from `unique_together` spec key |
| PERF-05 | Computed fields appearing in tree views, search filters, or `_order` automatically get `store=True`; TransientModels get `_transient_max_hours` and `_transient_max_count` | Same preprocessor identifies computed fields visible in views and sets store=True; TransientModel templates get cleanup class attributes |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | >=3.1 | Template rendering | Already in project; no new deps needed |
| Python graphlib | stdlib | Already imported for cycle detection | No new deps |

### Supporting
No new libraries needed. This phase is purely preprocessor logic + template updates.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Preprocessor approach | Template-level logic | Preprocessor is cleaner -- keeps templates simple, testable as pure function |
| Manual `_order` in spec | Auto-detect from first Char field | Auto-detect is fragile; require explicit `_order` in spec |

## Architecture Patterns

### Recommended Project Structure

No new files needed. Changes go into existing files:
```
python/src/odoo_gen_utils/
    renderer.py               # New _process_performance() function + _build_model_context updates
    templates/17.0/model.py.j2 # Add _order, _transient_*, index=True for non-relational fields
    templates/18.0/model.py.j2 # Same as 17.0
python/tests/
    test_renderer.py           # Unit tests for _process_performance()
    test_render_stages.py      # Integration tests for full render pipeline
```

### Pattern 1: Performance Preprocessor (Pure Function)

**What:** A `_process_performance(spec) -> spec` function that enriches field dicts with `index=True` and `store=True`, and model dicts with `_sql_constraints` and `_order`.

**When to use:** Called in `render_module()` after `_process_computation_chains()` and `_process_constraints()`, before building contexts.

**Example:**
```python
def _process_performance(spec: dict[str, Any]) -> dict[str, Any]:
    """Enrich fields with index/store and models with _order/_sql_constraints.

    Analyzes:
    1. Search view fields (Char/Many2one in search) -> index=True
    2. Record rule domains -> index=True on domain fields
    3. Model _order -> index=True on order fields
    4. Computed fields in tree views/search/order -> store=True
    5. unique_together spec -> _sql_constraints
    6. TransientModel flag -> _transient_max_hours/_transient_max_count

    Pure function -- does NOT mutate the input spec.
    """
    new_models = []
    for model in spec.get("models", []):
        # ... analyze and enrich
        pass
    return {**spec, "models": new_models}
```

### Pattern 2: Field Usage Analysis

**What:** Determine which fields need `index=True` by analyzing how they are used across the spec.

**Index-worthy fields (Odoo conventions):**
1. Fields in search view filters: Currently, the `view_form.xml.j2` template puts `Char` and `Many2one` fields in `<search>` view. These need `index=True`.
2. Fields in record rule domains: The `record_rules.xml.j2` uses `company_id` in domain. Any field in a domain filter needs indexing.
3. Fields in `_order`: Any field used in the model's `_order` attribute needs indexing for efficient sorting.
4. Selection fields used as group-by filters in search views also benefit from indexing.

**Detection logic:**
```python
# Fields that appear in search view (from view_form.xml.j2 logic):
search_fields = {
    f["name"] for f in fields
    if f.get("type") in ("Char", "Many2one")
    and not f.get("internal")
}

# Fields in _order:
order_str = model.get("order", "")
order_fields = {part.strip().split()[0] for part in order_str.split(",") if part.strip()}

# Fields in record rule domains (company_id is auto-handled):
# Domain fields from spec.get("record_rules", []) if present

# Union = needs index
index_fields = search_fields | order_fields | domain_fields
```

### Pattern 3: Computed Field Store Detection

**What:** Computed fields that appear in tree views, search filters, or `_order` MUST have `store=True` to be usable in those contexts.

**Why:** Odoo cannot search/filter/sort on non-stored computed fields because they don't exist in the database. Without `store=True`, the field would silently fail in search/sort.

**Detection logic:**
```python
# Tree view shows first 6 non-relational, non-Html, non-Text fields
tree_fields = {
    f["name"] for idx, f in enumerate(view_fields)
    if f.get("type") not in ("One2many", "Html", "Text") and idx < 6
}

# Search fields (Char, Many2one)
search_fields = {
    f["name"] for f in view_fields
    if f.get("type") in ("Char", "Many2one")
}

# Order fields
order_fields = ...  # as above

# Computed fields in any of these sets need store=True
visible_fields = tree_fields | search_fields | order_fields
for field in fields:
    if field.get("compute") and field["name"] in visible_fields:
        field = {**field, "store": True}
```

### Pattern 4: SQL Constraints from Uniqueness Spec

**What:** A `unique_together` key in the model spec generates `_sql_constraints`.

**Odoo format:**
```python
_sql_constraints = [
    ("unique_name_company", "UNIQUE(name, company_id)", "Name must be unique per company."),
]
```

**Spec format (proposed):**
```yaml
models:
  - name: academy.course
    unique_together:
      - fields: [name, company_id]
        message: "Course name must be unique per company."
      - fields: [code]
        message: "Course code must be unique."
```

**Generation logic:**
```python
sql_constraints = []
for unique in model.get("unique_together", []):
    constraint_name = "unique_" + "_".join(unique["fields"])
    definition = "UNIQUE(%s)" % ", ".join(unique["fields"])
    sql_constraints.append({
        "name": constraint_name,
        "definition": definition,
        "message": unique.get("message", f"{'_'.join(unique['fields'])} must be unique."),
    })
```

### Pattern 5: TransientModel Cleanup Configuration

**What:** TransientModels should have `_transient_max_hours` and `_transient_max_count` to control automatic cleanup.

**Odoo defaults:** `_transient_max_hours = 1.0`, `_transient_max_count = 0` (no limit). For generated wizards, sensible defaults are:
- `_transient_max_hours = 1.0` (clean up after 1 hour)
- `_transient_max_count = 0` (no record count limit -- hour-based cleanup is sufficient)

**Spec override:**
```yaml
wizards:
  - name: confirm.wizard
    transient_max_hours: 2.0
    transient_max_count: 1000
```

**Template change in wizard.py.j2 and import_wizard.py.j2:**
```jinja2
class {{ wizard_class }}(models.TransientModel):
    _name = "{{ wizard.name }}"
    _description = "..."
    _transient_max_hours = {{ wizard.transient_max_hours | default(1.0) }}
    _transient_max_count = {{ wizard.transient_max_count | default(0) }}
```

### Anti-Patterns to Avoid
- **Indexing everything:** Only index fields actually used in search/filter/sort. Over-indexing slows writes.
- **Missing store=True on view-referenced computed fields:** Causes silent failures -- field shows in tree but cannot be sorted/searched.
- **Hardcoded _order without index:** `_order = "date desc"` without `index=True` on `date` causes full table scans.
- **Forgetting _sql_constraints message i18n:** Messages should be plain strings (Odoo handles i18n for sql_constraints differently than ValidationError).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Index detection | Custom field analysis from XML | Preprocessor analyzing spec dict | Spec dict already contains all info needed -- no need to parse generated XML |
| SQL constraint syntax | String formatting | Dict-based constraint generation | Consistent with existing `sql_constraints` passthrough pattern |

## Common Pitfalls

### Pitfall 1: Non-stored computed fields in search views
**What goes wrong:** A computed field without `store=True` appears in a search view. Odoo silently ignores it for filtering/grouping, confusing users.
**Why it happens:** Developer adds a computed field and it shows up in tree view, but forgets store=True.
**How to avoid:** The preprocessor must detect this case and auto-set `store=True`.
**Warning signs:** Search filter that silently does nothing.

### Pitfall 2: index=True on One2many/Many2many
**What goes wrong:** Attempting to add `index=True` to One2many or Many2many fields makes no sense (they are virtual; the FK is on the other table).
**Why it happens:** Naive "index all filterable fields" logic.
**How to avoid:** Only index Char, Integer, Float, Date, Datetime, Boolean, Selection, Many2one fields. Exclude One2many, Many2many, Html, Text, Binary.
**Warning signs:** `index=True` on a One2many field definition.

### Pitfall 3: _sql_constraints with non-existent fields
**What goes wrong:** `unique_together` references a field name that doesn't exist in the model.
**Why it happens:** Typo in spec or field was renamed.
**How to avoid:** Validate that all fields in `unique_together` exist in the model's field list.
**Warning signs:** PostgreSQL error on module install: `column "xyz" does not exist`.

### Pitfall 4: _order field doesn't exist
**What goes wrong:** `_order = "priority desc, name"` but model has no `priority` field.
**Why it happens:** Copy-paste from another model.
**How to avoid:** Validate `_order` fields exist in the model's field list during preprocessing.
**Warning signs:** Odoo logs warning or errors on model load.

### Pitfall 5: Template rendering order for index=True
**What goes wrong:** The `index=True` attribute is not rendered for non-relational fields because the current template only handles it in the Many2one/One2many/Many2many branch.
**Why it happens:** Original template design only considered relational field indexing.
**How to avoid:** Add `index=True` rendering to ALL field type branches in model.py.j2 (Char, Integer, Float, Date, Datetime, Boolean, Selection, and the generic else branch).
**Warning signs:** Field dict has `index: True` but generated Python code doesn't include `index=True`.

## Code Examples

### Current Template Gap: index=True only for relational fields

In `model.py.j2`, the `{% if field.index is defined and field.index %}` block only appears inside the Many2one/One2many/Many2many branch. Non-relational fields (Char, Integer, etc.) fall through to the generic `{% else %}` block which does NOT render `index=True`.

**Fix required:** Add `index=True` rendering to the generic field block:
```jinja2
{% else %}
    {{ field.name }} = fields.{{ field.type }}(
        string="{{ field.string | default(field.name | replace('_', ' ') | title) }}",
{% if field.required is defined and field.required %}
        required=True,
{% endif %}
{% if field.index is defined and field.index %}
        index=True,
{% endif %}
{% if field.default is defined %}
        default="{{ field.default }}",
{% endif %}
{% if field.help is defined %}
        help="{{ field.help }}",
{% endif %}
    )
{% endif %}
```

### _order Template Addition

Currently not rendered. Add to model.py.j2 after `_parent_store`:
```jinja2
{% if model_order is defined and model_order %}
    _order = "{{ model_order }}"
{% endif %}
```

### TransientModel Cleanup Attributes

Add to wizard.py.j2 and import_wizard.py.j2:
```jinja2
    _transient_max_hours = {{ transient_max_hours | default(1.0) }}
    _transient_max_count = {{ transient_max_count | default(0) }}
```

### Preprocessor Integration Point

In `render_module()`, add after line 1517:
```python
# Phase 33: performance optimization (index, store, sql_constraints, transient config)
spec = _process_performance(spec)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual index=True in spec | Auto-detect from view/search usage | Phase 33 | Prevents forgotten indexes |
| store=True only from computation_chains | Also from view/search/order analysis | Phase 33 | Computed fields work in tree/search |
| No _sql_constraints auto-gen | Auto from unique_together | Phase 33 | Database-level uniqueness enforcement |
| No TransientModel cleanup config | Auto _transient_max_hours/count | Phase 33 | Prevents wizard record bloat |

**Odoo version note:** Both Odoo 17.0 and 18.0 use the same `index=True` parameter on fields. Odoo 18.0 also supports `Index` objects for more complex index types (partial, expression-based), but `index=True` (simple B-tree) is sufficient for auto-generation. No version-specific template differences needed for Phase 33.

## Open Questions

1. **Should `_order` be auto-inferred or always explicit in spec?**
   - What we know: Odoo default `_order` is `id`, which is rarely what users want.
   - What's unclear: Whether auto-inferring (e.g., "use `name asc` if model has a `name` field") is useful or surprising.
   - Recommendation: Require explicit `order` key in model spec. If not provided, don't render `_order` (use Odoo's default). This is safer and more predictable.

2. **Should Selection fields used as group-by filters get `index=True`?**
   - What we know: The search view template generates group-by filters for Selection and Many2one fields.
   - What's unclear: Selection fields typically have low cardinality; indexes on low-cardinality columns can be counterproductive.
   - Recommendation: Index Selection fields used in group-by. PostgreSQL handles low-cardinality indexes reasonably, and it helps with `WHERE state = 'draft'` type queries that are very common in Odoo.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 |
| Config file | `python/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest tests/test_renderer.py -x -q` |
| Full suite command | `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-01 | Search view fields get index=True | unit | `python -m pytest tests/test_renderer.py -x -k "test_performance_index_search_fields"` | Wave 0 |
| PERF-01 | Record rule domain fields get index=True | unit | `python -m pytest tests/test_renderer.py -x -k "test_performance_index_domain_fields"` | Wave 0 |
| PERF-01 | _order fields get index=True | unit | `python -m pytest tests/test_renderer.py -x -k "test_performance_index_order_fields"` | Wave 0 |
| PERF-01 | unique_together -> _sql_constraints | unit | `python -m pytest tests/test_renderer.py -x -k "test_performance_sql_constraints"` | Wave 0 |
| PERF-05 | Computed fields in tree view get store=True | unit | `python -m pytest tests/test_renderer.py -x -k "test_performance_store_computed_tree"` | Wave 0 |
| PERF-05 | Computed fields in search/order get store=True | unit | `python -m pytest tests/test_renderer.py -x -k "test_performance_store_computed_search"` | Wave 0 |
| PERF-05 | TransientModel gets cleanup attrs | unit | `python -m pytest tests/test_renderer.py -x -k "test_transient_cleanup_attrs"` | Wave 0 |
| PERF-01+05 | Full render pipeline with performance | integration | `python -m pytest tests/test_render_stages.py -x -k "test_performance"` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest tests/test_renderer.py -x -q`
- **Per wave merge:** `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_renderer.py` -- add test_performance_* functions (8 new test cases)
- [ ] `tests/test_render_stages.py` -- add integration test for performance preprocessing

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `renderer.py` (1555 lines), `model.py.j2` (17.0 + 18.0), `view_form.xml.j2`, `wizard.py.j2`, `import_wizard.py.j2`
- Existing preprocessor pattern: `_process_relationships()`, `_process_computation_chains()`, `_process_constraints()` -- all pure functions returning new spec dicts
- Odoo 17.0 ORM: `index=True` creates B-tree index; `store=True` persists computed field to DB column; `_sql_constraints` creates PostgreSQL constraints; `_transient_max_hours`/`_transient_max_count` control TransientModel cleanup

### Secondary (MEDIUM confidence)
- Odoo 18.0 Index API: Supports `Index` objects for advanced indexing, but `index=True` remains valid and sufficient for auto-generation

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new libraries, purely internal preprocessor + template changes
- Architecture: HIGH - Follows exact same pattern as 3 prior preprocessors (relationships, chains, constraints)
- Pitfalls: HIGH - Based on direct codebase analysis; template gap for index=True on non-relational fields is verified

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable -- internal project patterns unlikely to change)
