# Phase 28: Computed Chains & Cycle Detection - Research

**Researched:** 2026-03-05
**Domain:** Odoo computed field dependency chains, topological ordering, circular dependency detection
**Confidence:** HIGH

## Summary

Phase 28 adds a `computation_chains` section to the spec format that enables multi-model computed field dependency chains -- the pattern where a parent model field (e.g., `sale.order.amount_total`) depends on child model fields (e.g., `sale.order.line.price_subtotal`) via dotted dependency paths in `@api.depends`. The current renderer already handles single-model computed fields (fields with `compute=` and `depends=` keys), but has no concept of cross-model dependency ordering, no `store=True` auto-injection for chained fields, and no circular dependency validation.

The core technical challenges are: (1) parsing `computation_chains` to enrich field specs with correct dotted `@api.depends` paths and `store=True`, (2) topologically sorting computed fields within each model so downstream fields are defined after their upstream dependencies, and (3) detecting circular dependency chains across the entire spec and rejecting them with actionable error messages before any code is generated.

Python 3.12's stdlib `graphlib.TopologicalSorter` provides both topological sort and cycle detection via `CycleError`, eliminating any need for external dependencies. The implementation pattern follows the established preprocessor approach from Phase 27 (`_process_relationships()`): a new `_process_computation_chains()` function transforms the spec before rendering, and a `_validate_no_cycles()` function runs before that to reject circular specs.

**Primary recommendation:** Add `_validate_no_cycles()` as a spec-level validation pass (called at the top of `render_module()` before `_process_relationships()`). Add `_process_computation_chains()` as a preprocessor that enriches field dicts with dotted `depends` paths and `store=True`. Use `graphlib.TopologicalSorter` for both sorting and cycle detection. Modify `_build_model_context()` to topologically sort `computed_fields` before passing to templates.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SPEC-03 | Spec supports `computation_chains` section defining multi-model computed field chains with correct `@api.depends`, `store=True`, and computation order via topological sort | `computation_chains` spec format, `_process_computation_chains()` preprocessor, dotted path generation, `store=True` injection, topological sort of `computed_fields` in `_build_model_context()` |
| SPEC-05 | Spec validation detects circular dependency chains and rejects them with actionable error messages before generation | `_validate_no_cycles()` using `graphlib.TopologicalSorter` + `CycleError`, called before any rendering in `render_module()` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| graphlib | stdlib (Python 3.12) | Topological sort + cycle detection | Built into Python 3.9+; `TopologicalSorter` provides `static_order()` for sorting and raises `CycleError` with cycle participants -- exactly what we need |
| Jinja2 | (existing) | Template rendering -- no template changes needed | Existing `model.py.j2` already renders `@api.depends` with dotted paths and `store=True` |
| Python 3.12 | (existing) | All processing logic in renderer.py | Project requirement |

### Supporting
No new libraries needed. This is pure spec-processing logic using stdlib.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `graphlib.TopologicalSorter` | Hand-rolled Kahn's algorithm | graphlib is battle-tested stdlib, handles edge cases, provides `CycleError` with cycle path for free |
| `graphlib.TopologicalSorter` | NetworkX `topological_sort()` | NetworkX is a 20MB+ dependency for a 20-line problem; graphlib is zero-dependency |
| Spec-level preprocessor | Inline logic in `_build_model_context()` | Preprocessor is cleaner because chains span models; `_build_model_context()` operates on one model at a time |

## Architecture Patterns

### Spec Format Design

The `computation_chains` section sits at the spec root level alongside `models`, `relationships`, and `wizards`:

```json
{
  "module_name": "university",
  "models": [
    {
      "name": "university.enrollment",
      "fields": [
        {"name": "grade", "type": "Float"},
        {"name": "credit_hours", "type": "Integer"},
        {"name": "weighted_grade", "type": "Float",
         "compute": "_compute_weighted_grade"}
      ]
    },
    {
      "name": "university.student",
      "fields": [
        {"name": "enrollment_ids", "type": "One2many",
         "comodel_name": "university.enrollment", "inverse_name": "student_id"},
        {"name": "gpa", "type": "Float",
         "compute": "_compute_gpa"}
      ]
    }
  ],
  "computation_chains": [
    {
      "field": "university.enrollment.weighted_grade",
      "depends_on": ["grade", "credit_hours"],
      "description": "grade * credit_hours"
    },
    {
      "field": "university.student.gpa",
      "depends_on": ["enrollment_ids.weighted_grade", "enrollment_ids.credit_hours"],
      "description": "sum(weighted_grade * credit_hours) / sum(credit_hours)"
    }
  ]
}
```

**Key design decisions:**

1. `field` uses dotted notation: `model_name.field_name` (e.g., `university.enrollment.weighted_grade`)
2. `depends_on` contains dependency paths as they would appear in `@api.depends` -- local fields are plain names, cross-model fields use Odoo dotted path syntax (e.g., `enrollment_ids.weighted_grade`)
3. All fields in `computation_chains` automatically get `store=True` (the whole point of chains is stored computed fields)
4. The `description` is optional documentation for the computation logic

### Pattern 1: Computation Chain Preprocessor

**What:** A `_process_computation_chains()` function that enriches field dicts in the spec with correct `depends` lists and `store=True` based on the `computation_chains` section.

**When to use:** Called in `render_module()` after `_process_relationships()` but before model rendering.

**Implementation:**

```python
def _process_computation_chains(spec: dict[str, Any]) -> dict[str, Any]:
    """Enrich computed field specs from computation_chains section.

    For each chain entry:
    1. Locate the target field in the matching model
    2. Set field.depends = chain.depends_on (the @api.depends paths)
    3. Set field.store = True
    4. Set field.compute if not already set (convention: _compute_{field_name})

    Returns a new spec dict with enriched models. Pure function.
    """
    chains = spec.get("computation_chains", [])
    if not chains:
        return spec

    # Build a lookup: model_name -> {field_name -> chain_entry}
    chain_lookup: dict[str, dict[str, dict]] = {}
    for chain in chains:
        # "university.enrollment.weighted_grade" -> model="university.enrollment", field="weighted_grade"
        parts = chain["field"].rsplit(".", 1)
        model_name, field_name = parts[0], parts[1]
        chain_lookup.setdefault(model_name, {})[field_name] = chain

    # Deep-copy models and enrich fields
    new_models = []
    for model in spec.get("models", []):
        model_chains = chain_lookup.get(model["name"], {})
        if not model_chains:
            new_models.append(model)
            continue

        new_fields = []
        for field in model.get("fields", []):
            fname = field.get("name", "")
            if fname in model_chains:
                chain = model_chains[fname]
                field = {
                    **field,
                    "depends": chain["depends_on"],
                    "store": True,
                    "compute": field.get("compute", f"_compute_{fname}"),
                }
            new_fields.append(field)
        new_models.append({**model, "fields": new_fields})

    return {**spec, "models": new_models}
```

### Pattern 2: Cycle Detection Before Generation

**What:** A `_validate_no_cycles()` function that builds a dependency graph from `computation_chains` and raises `ValueError` with cycle participants if circular dependencies exist.

**When to use:** Called at the very top of `render_module()`, before any processing or file generation.

**Implementation:**

```python
from graphlib import TopologicalSorter, CycleError

def _validate_no_cycles(spec: dict[str, Any]) -> None:
    """Validate that computation_chains contain no circular dependencies.

    Builds a directed graph where nodes are "model.field" identifiers
    and edges represent "depends on" relationships. Uses graphlib to
    detect cycles.

    Raises ValueError with actionable message naming cycle participants.
    """
    chains = spec.get("computation_chains", [])
    if not chains:
        return

    # Build model field inventory for resolving dotted paths
    model_fields: dict[str, set[str]] = {}
    for model in spec.get("models", []):
        model_fields[model["name"]] = {
            f.get("name", "") for f in model.get("fields", [])
        }

    # Build dependency graph: node = "model.field", edges = depends_on
    graph: dict[str, set[str]] = {}
    for chain in chains:
        node = chain["field"]  # e.g., "university.student.gpa"
        model_name = node.rsplit(".", 1)[0]
        deps: set[str] = set()
        for dep in chain.get("depends_on", []):
            if "." in dep:
                # Cross-model: "enrollment_ids.weighted_grade"
                # Resolve: find which model the relational field points to
                rel_field, target_field = dep.split(".", 1)
                # Look up the relational field's comodel
                target_model = _resolve_comodel(
                    spec, model_name, rel_field
                )
                if target_model:
                    deps.add(f"{target_model}.{target_field}")
            # Local fields don't create cross-chain dependencies
            # unless they themselves are in the chain
            else:
                local_node = f"{model_name}.{dep}"
                # Only add as dependency if it's also a chain node
                if any(c["field"] == local_node for c in chains):
                    deps.add(local_node)
        graph[node] = deps

    try:
        ts = TopologicalSorter(graph)
        list(ts.static_order())
    except CycleError as exc:
        cycle_nodes = exc.args[1]
        cycle_str = " -> ".join(str(n) for n in cycle_nodes)
        msg = (
            f"Circular dependency detected in computation_chains: "
            f"{cycle_str}. Break the cycle by removing one dependency."
        )
        raise ValueError(msg) from None


def _resolve_comodel(
    spec: dict[str, Any], model_name: str, field_name: str
) -> str | None:
    """Resolve the comodel_name of a relational field on a model."""
    for model in spec.get("models", []):
        if model["name"] == model_name:
            for field in model.get("fields", []):
                if field.get("name") == field_name:
                    return field.get("comodel_name")
    return None
```

### Pattern 3: Topological Sort of Computed Fields in Model Context

**What:** Within `_build_model_context()`, sort the `computed_fields` list so that fields depending on other computed fields in the same model come after their dependencies.

**When to use:** Always, when building model context -- ensures correct definition order in generated Python.

**Implementation:**

```python
# In _build_model_context(), after building computed_fields list:
if len(computed_fields) > 1:
    computed_fields = _topologically_sort_fields(computed_fields)
```

```python
def _topologically_sort_fields(
    computed_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort computed fields so dependencies come before dependents.

    Uses graphlib.TopologicalSorter. If fields have no inter-dependencies
    (common case), preserves original order.
    """
    field_names = {f["name"] for f in computed_fields}
    field_map = {f["name"]: f for f in computed_fields}

    graph: dict[str, set[str]] = {}
    for field in computed_fields:
        deps = set()
        for dep in field.get("depends", []):
            # Only consider local dependencies (no dots) that are
            # themselves computed fields
            if "." not in dep and dep in field_names:
                deps.add(dep)
        graph[field["name"]] = deps

    try:
        ts = TopologicalSorter(graph)
        sorted_names = list(ts.static_order())
    except CycleError:
        # Intra-model cycles caught by _validate_no_cycles already
        return computed_fields

    # Rebuild list in sorted order, append non-computed fields last
    result = []
    for name in sorted_names:
        if name in field_map:
            result.append(field_map[name])
    return result
```

### Pattern 4: Integration into render_module()

**What:** Wire the new functions into the existing render pipeline.

```python
def render_module(spec, template_dir, output_dir, verifier=None):
    # Phase 28: validate no circular dependencies FIRST
    _validate_no_cycles(spec)

    env = create_versioned_renderer(spec.get("odoo_version", "17.0"))
    # Phase 27: process relationships
    spec = _process_relationships(spec)
    # Phase 28: process computation chains
    spec = _process_computation_chains(spec)

    module_name = spec["module_name"]
    # ... rest of pipeline unchanged
```

### Recommended Project Structure

No new files needed. All changes go in existing files:

```
python/src/odoo_gen_utils/
    renderer.py          # Add: _validate_no_cycles(), _process_computation_chains(),
                         #       _topologically_sort_fields(), _resolve_comodel()
                         # Modify: render_module(), _build_model_context()

python/tests/
    test_renderer.py     # Add: TestProcessComputationChains, TestValidateNoCycles,
                         #       TestTopologicallySortFields
    test_render_stages.py # Add: TestRenderModelsComputedChains
```

### Anti-Patterns to Avoid

- **Separate module/file for graph logic:** The cycle detection + topological sort is ~60 lines total. Creating a new module for this is over-engineering. Keep it in `renderer.py` alongside the other preprocessors.
- **Validating cycles after partial generation:** Cycle detection MUST happen before ANY files are written. If the spec is invalid, no output should be produced.
- **Mutating field dicts in-place:** Follow project immutability convention -- `_process_computation_chains()` returns a new spec, not mutated originals.
- **Assuming all depends entries create graph edges:** Only entries that reference other computed chain fields create graph edges. A chain field depending on a plain (non-computed) field like `grade` does NOT create a graph edge -- `grade` is a leaf node.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Topological sort | Kahn's algorithm or DFS from scratch | `graphlib.TopologicalSorter.static_order()` | stdlib, O(V+E), handles edge cases, zero dependencies |
| Cycle detection | Custom DFS with visited/visiting sets | `graphlib.CycleError` from `TopologicalSorter.prepare()` | Provides cycle participant list in `exc.args[1]` for actionable error messages |
| Dependency graph resolution | Manual adjacency list construction | `TopologicalSorter(graph_dict)` constructor | Accepts `{node: {predecessors}}` dict directly |

**Key insight:** `graphlib.TopologicalSorter` gives us both topological sort AND cycle detection with cycle participant reporting in a single stdlib class. Using it means the entire graph logic is ~15 lines of glue code.

## Common Pitfalls

### Pitfall 1: Dotted Dependency Path Resolution
**What goes wrong:** A chain entry has `depends_on: ["enrollment_ids.weighted_grade"]` but the cycle detection graph uses this string literally instead of resolving it to `university.enrollment.weighted_grade`.
**Why it happens:** Dotted paths in `@api.depends` use the relational FIELD name (e.g., `enrollment_ids`), not the model name. The graph needs full model-qualified names to detect cross-model cycles.
**How to avoid:** `_validate_no_cycles()` must resolve dotted paths by looking up the relational field's `comodel_name` in the spec. The `_resolve_comodel()` helper does this.
**Warning signs:** Cycles not detected when they span models; false negative validation.

### Pitfall 2: store=True Not Set on Chain Fields
**What goes wrong:** A cross-model computed field generates correct `@api.depends("line_ids.subtotal")` but without `store=True`, so the field value is recomputed on every access instead of being stored and updated on dependency changes.
**Why it happens:** The current renderer only sets `store=True` if it is explicitly in the field spec. Chain fields need it implicitly.
**How to avoid:** `_process_computation_chains()` must inject `"store": True` on every field referenced in `computation_chains`.
**Warning signs:** Computed field works but is very slow on large datasets; field not searchable or groupable.

### Pitfall 3: Computed Field Ordering in Generated Python
**What goes wrong:** Field `total` depends on field `subtotal` (both computed), but `total` is defined before `subtotal` in the generated model file. Odoo processes field definitions top-to-bottom for some operations.
**Why it happens:** Fields are rendered in spec order, not dependency order.
**How to avoid:** `_build_model_context()` must topologically sort `computed_fields` before passing to templates. The template already iterates `{% for field in computed_fields %}` to generate `@api.depends` methods.
**Warning signs:** Fields that depend on other computed fields in the same model may not recompute correctly if Odoo processes them in definition order.

### Pitfall 4: CycleError Message Not Actionable
**What goes wrong:** The error says "cycle detected" but does not name the participating fields/models, leaving the user to manually inspect the spec.
**Why it happens:** Using a generic error message instead of extracting `CycleError.args[1]`.
**How to avoid:** Extract the cycle path from `CycleError.args[1]` and format it as: "Circular dependency: university.student.gpa -> university.enrollment.weighted_grade -> university.student.gpa".
**Warning signs:** Users cannot fix spec errors from the error message alone.

### Pitfall 5: Chain Fields Not Having compute= Set
**What goes wrong:** A field appears in `computation_chains` but does not have `compute=` in its field spec. The preprocessor enriches `depends` and `store` but the field still renders as a regular (non-computed) field.
**Why it happens:** The spec author forgot to add `compute=` to the field definition.
**How to avoid:** `_process_computation_chains()` must inject `compute` if not already set, using the convention `_compute_{field_name}`.
**Warning signs:** Field has `store=True` but no `@api.depends` decorator or compute method in generated code.

### Pitfall 6: render_module() Returns Partial Output on Cycle Error
**What goes wrong:** `_validate_no_cycles()` raises ValueError but some files have already been written (e.g., `__manifest__.py`).
**Why it happens:** Validation called too late in the pipeline.
**How to avoid:** Call `_validate_no_cycles()` as the FIRST operation in `render_module()`, before creating the Jinja2 environment or any directories.
**Warning signs:** Partial module directory left on disk after validation failure.

## Code Examples

### Odoo @api.depends with Dotted Path (Real-World Pattern)

```python
# Source: Odoo sale.order pattern (verified via Odoo forum + ORM docs)
class SaleOrder(models.Model):
    _name = "sale.order"

    order_line = fields.One2many(
        comodel_name="sale.order.line",
        inverse_name="order_id",
    )
    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        store=True,
        compute="_compute_amounts",
        currency_field="currency_id",
    )

    @api.depends("order_line.price_subtotal")
    def _compute_amounts(self):
        for order in self:
            order.amount_untaxed = sum(
                line.price_subtotal for line in order.order_line
            )


class SaleOrderLine(models.Model):
    _name = "sale.order.line"

    order_id = fields.Many2one(comodel_name="sale.order")
    product_uom_qty = fields.Float()
    price_unit = fields.Float()
    price_subtotal = fields.Monetary(
        string="Subtotal",
        store=True,
        compute="_compute_amount",
        currency_field="currency_id",
    )

    @api.depends("product_uom_qty", "price_unit")
    def _compute_amount(self):
        for line in self:
            line.price_subtotal = line.product_uom_qty * line.price_unit
```

**Key observations:**
- `price_subtotal` on `sale.order.line` depends on local fields (`product_uom_qty`, `price_unit`)
- `amount_untaxed` on `sale.order` depends on cross-model field via dotted path (`order_line.price_subtotal`)
- Both fields have `store=True` -- essential for stored computed chains
- The chain is: `price_unit` + `product_uom_qty` -> `price_subtotal` -> `amount_untaxed`

### graphlib.TopologicalSorter Usage

```python
# Source: Python 3.12 stdlib docs
from graphlib import TopologicalSorter, CycleError

# Successful sort
graph = {
    "university.student.gpa": {"university.enrollment.weighted_grade"},
    "university.enrollment.weighted_grade": set(),  # leaf node
}
ts = TopologicalSorter(graph)
order = list(ts.static_order())
# order: ["university.enrollment.weighted_grade", "university.student.gpa"]

# Cycle detection
cyclic_graph = {
    "A.x": {"B.y"},
    "B.y": {"A.x"},
}
ts = TopologicalSorter(cyclic_graph)
try:
    list(ts.static_order())
except CycleError as exc:
    cycle = exc.args[1]  # ['A.x', 'B.y', 'A.x']
    print(f"Cycle: {' -> '.join(str(n) for n in cycle)}")
```

### Spec Example: Full Computation Chain

```json
{
  "module_name": "university",
  "depends": ["base"],
  "models": [
    {
      "name": "university.enrollment",
      "fields": [
        {"name": "student_id", "type": "Many2one",
         "comodel_name": "university.student", "required": true},
        {"name": "course_id", "type": "Many2one",
         "comodel_name": "university.course", "required": true},
        {"name": "grade", "type": "Float"},
        {"name": "credit_hours", "type": "Integer"},
        {"name": "weighted_grade", "type": "Float",
         "compute": "_compute_weighted_grade"}
      ]
    },
    {
      "name": "university.student",
      "fields": [
        {"name": "name", "type": "Char", "required": true},
        {"name": "enrollment_ids", "type": "One2many",
         "comodel_name": "university.enrollment",
         "inverse_name": "student_id"},
        {"name": "gpa", "type": "Float",
         "compute": "_compute_gpa"},
        {"name": "total_credits", "type": "Integer",
         "compute": "_compute_total_credits"}
      ]
    }
  ],
  "computation_chains": [
    {
      "field": "university.enrollment.weighted_grade",
      "depends_on": ["grade", "credit_hours"],
      "description": "grade * credit_hours"
    },
    {
      "field": "university.student.gpa",
      "depends_on": ["enrollment_ids.weighted_grade", "enrollment_ids.credit_hours"],
      "description": "sum(weighted_grade * credit_hours) / sum(credit_hours)"
    },
    {
      "field": "university.student.total_credits",
      "depends_on": ["enrollment_ids.credit_hours"],
      "description": "sum(credit_hours)"
    }
  ]
}
```

**After `_process_computation_chains()`**, the `weighted_grade` field becomes:
```python
{
    "name": "weighted_grade",
    "type": "Float",
    "compute": "_compute_weighted_grade",
    "depends": ["grade", "credit_hours"],
    "store": True,
}
```

And the `gpa` field becomes:
```python
{
    "name": "gpa",
    "type": "Float",
    "compute": "_compute_gpa",
    "depends": ["enrollment_ids.weighted_grade", "enrollment_ids.credit_hours"],
    "store": True,
}
```

### Circular Dependency Error Message Format

```
ValueError: Circular dependency detected in computation_chains:
  university.student.gpa -> university.enrollment.weighted_grade -> university.student.gpa
Break the cycle by removing one dependency.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `depends` + `store=True` on each field | Derived from `computation_chains` section | Phase 28 (this phase) | Users declare chains once; preprocessor injects correct `depends` paths and `store=True` |
| No cycle detection | `graphlib.CycleError` with cycle path in error message | Phase 28 (this phase) | Invalid specs rejected before generation; users get actionable error |
| Computed fields in spec order | Topologically sorted in `_build_model_context()` | Phase 28 (this phase) | Downstream fields always reference already-defined upstream fields |
| No cross-model dependency awareness | Dotted path resolution via `_resolve_comodel()` | Phase 28 (this phase) | Generator produces correct `@api.depends("line_ids.subtotal")` patterns |

## Open Questions

1. **Should `computation_chains` be required or optional for computed fields?**
   - What we know: Existing specs already define computed fields inline with `compute=` and `depends=` on the field dict. The `computation_chains` section is a higher-level declaration.
   - What's unclear: Should we require ALL computed fields to be in `computation_chains`, or allow both inline and chain-based declaration?
   - Recommendation: Allow both. `computation_chains` entries override/enrich inline field specs. Fields with inline `compute` + `depends` that are NOT in `computation_chains` continue to work as before. This maintains backward compatibility.

2. **Should intra-model computed field chains also be in `computation_chains`?**
   - What we know: A model might have `subtotal` depending on `qty * price`, and `total` depending on `subtotal + tax`. These are same-model chains.
   - What's unclear: Should users declare these in `computation_chains` or just use inline `depends`?
   - Recommendation: Support both. If in `computation_chains`, the preprocessor enriches them. The topological sort in `_build_model_context()` works regardless of whether fields came from chains or inline specs.

3. **Should `_validate_no_cycles()` check inline computed fields too?**
   - What we know: A computed field can have `depends: ["other_computed_field"]` inline without being in `computation_chains`.
   - Recommendation: Yes, `_validate_no_cycles()` should build its graph from BOTH `computation_chains` AND inline computed field `depends`. This provides comprehensive cycle detection.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `python/pyproject.toml` |
| Quick run command | `cd /home/inshal-rauf/Odoo_module_automation/python && .venv/bin/python -m pytest tests/test_renderer.py -x -q -k "chain or cycle or topolog"` |
| Full suite command | `cd /home/inshal-rauf/Odoo_module_automation/python && .venv/bin/python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPEC-03a | `computation_chains` enriches field with `depends` list | unit | `pytest tests/test_renderer.py::TestProcessComputationChains::test_enriches_depends -x` | Wave 0 |
| SPEC-03b | `computation_chains` sets `store=True` on chain fields | unit | `pytest tests/test_renderer.py::TestProcessComputationChains::test_sets_store_true -x` | Wave 0 |
| SPEC-03c | `computation_chains` injects `compute` method name if missing | unit | `pytest tests/test_renderer.py::TestProcessComputationChains::test_injects_compute_name -x` | Wave 0 |
| SPEC-03d | Dotted dependency paths (e.g., `line_ids.subtotal`) preserved in enriched field | unit | `pytest tests/test_renderer.py::TestProcessComputationChains::test_dotted_paths_preserved -x` | Wave 0 |
| SPEC-03e | Computed fields sorted topologically within model context | unit | `pytest tests/test_renderer.py::TestTopologicallySortFields::test_sort_order -x` | Wave 0 |
| SPEC-03f | Generated model has `@api.depends` with dotted paths and `store=True` | integration | `pytest tests/test_render_stages.py::TestRenderModelsComputedChains::test_cross_model_depends -x` | Wave 0 |
| SPEC-03g | Spec without `computation_chains` works unchanged (backward compat) | unit | `pytest tests/test_renderer.py::TestProcessComputationChains::test_no_chains_passthrough -x` | Wave 0 |
| SPEC-05a | Circular dependency raises ValueError before file generation | unit | `pytest tests/test_renderer.py::TestValidateNoCycles::test_circular_raises -x` | Wave 0 |
| SPEC-05b | Error message names cycle participants | unit | `pytest tests/test_renderer.py::TestValidateNoCycles::test_error_names_participants -x` | Wave 0 |
| SPEC-05c | No cycle in valid chains passes validation | unit | `pytest tests/test_renderer.py::TestValidateNoCycles::test_valid_chains_pass -x` | Wave 0 |
| SPEC-05d | Cross-model circular dependency detected | unit | `pytest tests/test_renderer.py::TestValidateNoCycles::test_cross_model_cycle -x` | Wave 0 |
| SPEC-05e | `render_module()` raises before creating any files on cycle | integration | `pytest tests/test_render_stages.py::TestRenderModelsComputedChains::test_no_files_on_cycle -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /home/inshal-rauf/Odoo_module_automation/python && .venv/bin/python -m pytest tests/test_renderer.py tests/test_render_stages.py -x -q`
- **Per wave merge:** `cd /home/inshal-rauf/Odoo_module_automation/python && .venv/bin/python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_renderer.py::TestProcessComputationChains` -- chain preprocessor unit tests
- [ ] `tests/test_renderer.py::TestValidateNoCycles` -- cycle detection unit tests
- [ ] `tests/test_renderer.py::TestTopologicallySortFields` -- topological sort unit tests
- [ ] `tests/test_render_stages.py::TestRenderModelsComputedChains` -- end-to-end rendering with chains

## Sources

### Primary (HIGH confidence)
- [Python 3.12 graphlib documentation](https://docs.python.org/3/library/graphlib.html) -- `TopologicalSorter`, `CycleError`, `static_order()` API, cycle participant reporting
- Codebase analysis: `renderer.py` -- existing `_process_relationships()` preprocessor pattern, `_build_model_context()` computed field handling, `render_module()` pipeline
- Codebase analysis: `model.py.j2` (17.0 + 18.0) -- existing `@api.depends` + `store=True` template rendering (lines 87-110, 144-151)
- [Odoo ORM API documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html) -- `@api.depends` dotted path syntax, `store=True` behavior

### Secondary (MEDIUM confidence)
- [Odoo Forum: sum of order line fields](https://www.odoo.com/forum/help-1/how-to-compute-the-sum-of-order-line-field-and-place-it-in-sale-order-131238) -- `@api.depends("order_line.price_subtotal")` real-world pattern
- [Odoo Forum: @api.depends guidelines](https://www.odoo.com/forum/help-1/understanding-odoo-guidelines-vs-some-sale-order-api-depends-201983) -- Odoo's own sale.order computed chain pattern verification
- [Odoo 15.0 Computed Fields Tutorial](https://www.odoo.com/documentation/15.0/fr/developer/tutorials/getting_started/09_compute_onchange.html) -- official tutorial for computed fields and dependencies

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- graphlib is Python stdlib (3.9+), zero new dependencies, existing template already supports the output patterns
- Architecture: HIGH -- follows established preprocessor pattern from Phase 27, field enrichment pattern from Phase 26, well-understood graph algorithms
- Pitfalls: HIGH -- 6 pitfalls documented from codebase analysis and Odoo ORM behavior analysis

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain -- graphlib API unchanged since Python 3.9, Odoo computed field API unchanged since v10)
