# Phase 36: Renderer Extraction - Research

**Researched:** 2026-03-06
**Domain:** Python module refactoring / code extraction
**Confidence:** HIGH

## Summary

This phase is a pure structural refactoring of `renderer.py` (1852 lines) into 4 modules: `renderer_utils.py` (~80 lines), `preprocessors.py` (~630 lines), `renderer_context.py` (~320 lines), and a slimmed `renderer.py` (~800 lines) retaining render stages and orchestration. No behavior changes are permitted -- all 796 existing tests must pass unchanged.

The key risk is breaking imports. Tests and production code import 20+ symbols from `odoo_gen_utils.renderer`. The extraction must maintain backward-compatible re-exports from `renderer.py` so that no downstream code needs modification. A secondary concern is the override flag migration from `bool` to `set[str]`, which must be done carefully since `_build_model_context` reads these flags and templates consume the boolean result.

**Primary recommendation:** Extract functions into new modules, then add re-exports in `renderer.py` so all existing imports continue to work. Change override flags in `_process_constraints` and `_process_production_patterns` (writers) and `_build_model_context` (reader) simultaneously, using `bool(model["override_sources"]["create"])` to maintain backward compatibility with templates.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `renderer_utils.py` -- shared utilities (_to_class, _to_python_var, _to_xml_id, _model_ref, _is_monetary_field, SEQUENCE_FIELD_NAMES, MONETARY_FIELD_PATTERNS). ~80 lines. Used by both preprocessors and context builders.
- `preprocessors.py` -- all 5 preprocessors + their helpers + _validate_no_cycles. ~630 lines. Public API: validate_no_cycles(), run() or individual process functions.
- `renderer_context.py` -- _build_model_context (as-is, 250 lines) + _build_module_context. ~320 lines.
- `renderer.py` -- render stages (10), template setup, orchestrator (render_module). Should land under ~800 lines.
- Override flags change from boolean to set[str] on the model dict itself
- Initialize in render_module before preprocessors run: `model["override_sources"] = defaultdict(set)`
- Preprocessors write: `model["override_sources"]["create"].add("constraints")`
- Context builder reads: `bool(model["override_sources"]["create"])`
- Move _build_model_context as-is to renderer_context.py. Do NOT break it into smaller pieces in this phase.
- Helper functions move with their preprocessors
- _validate_no_cycles goes to preprocessors.py
- Extract first, refactor internals second. One structural change per commit.

### Claude's Discretion
- Import organization and __init__.py re-exports
- Exact public API naming for preprocessors module (run_all vs individual functions)
- Whether to add __all__ exports

### Deferred Ideas (OUT OF SCOPE)
- Breaking _build_model_context into smaller pieces (separate follow-up)
- Further decomposition of render stages (not needed for v3.2)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFR-01 | renderer.py preprocessors and context builders extracted into separate modules before new features | Exact function-to-module mapping documented, import dependency graph analyzed, backward-compatible re-export strategy defined |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 | Runtime | Project constraint (Odoo 17 compat) |
| pytest | (existing) | Test runner | Already in use, 796 tests |
| graphlib | stdlib | TopologicalSorter | Used by _validate_no_cycles, _topologically_sort_fields |
| collections.defaultdict | stdlib | Override flag sets | defaultdict(set) for override_sources |

### Supporting
No new libraries needed. This is pure structural refactoring.

## Architecture Patterns

### Recommended Module Structure (after extraction)
```
python/src/odoo_gen_utils/
├── __init__.py              # unchanged
├── renderer.py              # ~800 lines: stages, setup, orchestrator
├── renderer_utils.py        # ~80 lines: shared converters + constants
├── renderer_context.py      # ~320 lines: _build_model_context, _build_module_context
├── preprocessors.py         # ~630 lines: 5 preprocessors + helpers
├── cli.py                   # unchanged (imports from renderer.py)
├── verifier.py              # unchanged
└── ...
```

### Pattern 1: Backward-Compatible Re-exports
**What:** After extracting functions to new modules, re-export them from renderer.py
**When to use:** Always, for this extraction -- tests and CLI import from renderer.py
**Example:**
```python
# renderer.py -- after extraction
from odoo_gen_utils.renderer_utils import (
    _is_monetary_field,
    _model_ref,
    _to_class,
    _to_python_var,
    _to_xml_id,
    MONETARY_FIELD_PATTERNS,
    SEQUENCE_FIELD_NAMES,
)
from odoo_gen_utils.preprocessors import (
    _process_computation_chains,
    _process_constraints,
    _process_performance,
    _process_production_patterns,
    _process_relationships,
    _validate_no_cycles,
)
from odoo_gen_utils.renderer_context import (
    _build_model_context,
    _build_module_context,
)
```

### Pattern 2: Import Dependency Graph (No Circular Deps)
**What:** Strict one-way dependency flow prevents circular imports
**Graph:**
```
renderer_utils.py  <-- preprocessors.py
renderer_utils.py  <-- renderer_context.py
preprocessors.py   <-- renderer.py (orchestrator)
renderer_context.py <-- renderer.py (orchestrator)
```
Neither `preprocessors.py` nor `renderer_context.py` import from each other. Both depend only on `renderer_utils.py`. `renderer.py` imports from all three.

### Anti-Patterns to Avoid
- **Cross-importing between preprocessors and context:** Would create circular deps. Use renderer_utils.py as the shared layer.
- **Moving _register_filters or create_versioned_renderer:** These stay in renderer.py -- they are template setup, not preprocessing or context building.
- **Removing underscore prefix on extracted functions:** Keep `_process_relationships` etc. as-is in the new modules. The re-exports maintain the same name.

## Exact Function-to-Module Mapping

### renderer_utils.py (~80 lines)
| Function/Constant | Lines in current renderer.py | Notes |
|-------------------|------------------------------|-------|
| `SEQUENCE_FIELD_NAMES` | 20 | frozenset constant |
| `MONETARY_FIELD_PATTERNS` | 23-28 | frozenset constant |
| `_is_monetary_field()` | 31-51 | Used by renderer_context.py |
| `_model_ref()` | 744-749 | Used as Jinja filter + by context |
| `_to_class()` | 752-757 | Used as Jinja filter + by preprocessors + context |
| `_to_python_var()` | 760-765 | Used everywhere |
| `_to_xml_id()` | 768-773 | Used by context + render stages |
| `INDEXABLE_TYPES` | 402-405 | Used by _process_performance |
| `NON_INDEXABLE_TYPES` | 408-410 | Used by _process_performance |

### preprocessors.py (~630 lines)
| Function | Lines | Helpers it needs |
|----------|-------|-----------------|
| `_validate_no_cycles()` | 235-278 | `_resolve_comodel` |
| `_process_relationships()` | 54-79 | `_synthesize_through_model`, `_inject_one2many_links`, `_enrich_self_referential_m2m` |
| `_synthesize_through_model()` | 82-133 | `_to_python_var` (from utils) |
| `_inject_one2many_links()` | 136-169 | `_to_python_var` (from utils) |
| `_enrich_self_referential_m2m()` | 172-220 | `_to_python_var` (from utils) |
| `_resolve_comodel()` | 223-232 | standalone |
| `_process_constraints()` | 281-398 | standalone (uses re) |
| `_process_performance()` | 413-435 | `_enrich_model_performance` |
| `_enrich_model_performance()` | 556-658 | standalone |
| `_process_computation_chains()` | 661-705 | standalone |
| `_topologically_sort_fields()` | 708-741 | standalone (used by renderer_context too) |
| `_process_production_patterns()` | 438-553 | standalone |

### renderer_context.py (~320 lines)
| Function | Lines | Dependencies |
|----------|-------|-------------|
| `_build_model_context()` | 885-1135 | `_to_python_var`, `_to_xml_id`, `SEQUENCE_FIELD_NAMES`, `_is_monetary_field`, `_topologically_sort_fields` (all from utils/preprocessors) |
| `_build_module_context()` | 1698-1757 | `_to_python_var`, `_to_xml_id`, `SEQUENCE_FIELD_NAMES`, `_compute_manifest_data`, `_compute_view_files` |
| `_compute_manifest_data()` | 1138-1190 | `_to_python_var`, `_to_xml_id` |
| `_compute_view_files()` | 1193-1208 | `_to_python_var` |

**Note:** `_topologically_sort_fields` is called by `_build_model_context` but logically belongs with preprocessors. It should live in `preprocessors.py` and be imported by `renderer_context.py`. This is safe because renderer_context.py does NOT export to preprocessors.py.

**Wait -- dependency issue:** `renderer_context.py` would need to import `_topologically_sort_fields` from `preprocessors.py`. This creates a dependency: `renderer_context.py -> preprocessors.py`. This is fine as long as `preprocessors.py` does NOT import from `renderer_context.py`. Verified: it does not.

Alternatively, `_topologically_sort_fields` could go to `renderer_utils.py` since it is a pure utility. This is Claude's discretion per CONTEXT.md. **Recommendation:** Put it in `renderer_utils.py` to keep the dependency graph simpler (both preprocessors and context depend only on utils).

### renderer.py (remains, ~800 lines)
| Function | Lines | Notes |
|----------|-------|-------|
| `_register_filters()` | 776-789 | Template setup |
| `create_versioned_renderer()` | 792-814 | Template setup |
| `create_renderer()` | 817-845 | Template setup (backward compat) |
| `render_template()` | 848-871 | Core rendering |
| `get_template_dir()` | 874-882 | Path utility |
| `render_manifest()` | 1211-1241 | Stage 1 |
| `render_models()` | 1244-1297 | Stage 2 |
| `render_views()` | 1300-1324 | Stage 3 |
| `render_security()` | 1327-1370 | Stage 4 |
| `render_wizards()` | 1373-1412 | Stage 5 |
| `render_tests()` | 1415-1445 | Stage 6 |
| `render_static()` | 1448-1511 | Stage 7 |
| `render_cron()` | 1514-1540 | Stage 8 |
| `render_reports()` | 1543-1590 | Stage 9 |
| `render_controllers()` | 1593-1695 | Stage 10 |
| `_track_artifacts()` | 1760-1783 | Artifact tracking |
| `render_module()` | 1786-1852 | Orchestrator |
| Re-exports | N/A | All moved symbols |

**Estimated line count:** ~620 lines of own code + ~30 lines of re-exports = ~650 lines (well under 800).

## Override Flag Migration Strategy

### Current State
`_process_constraints` and `_process_production_patterns` set boolean flags:
```python
# _process_constraints (line 394-395)
"has_create_override": bool(create_constraints),
"has_write_override": bool(write_constraints),

# _process_production_patterns (lines 475-481, 546-549)
new_model["has_create_override"] = True
new_model["has_write_override"] = True
# Later preserves existing:
if model.get("has_create_override"):
    new_model["has_create_override"] = True
```

### Migration Plan
1. In `render_module()`, before preprocessor chain, initialize on each model:
```python
for model in spec.get("models", []):
    model["override_sources"] = defaultdict(set)
```

2. In `_process_constraints`, change:
```python
# Before: "has_create_override": bool(create_constraints)
# After:
if create_constraints:
    new_model.setdefault("override_sources", defaultdict(set))["create"].add("constraints")
if write_constraints:
    new_model.setdefault("override_sources", defaultdict(set))["write"].add("constraints")
```

3. In `_process_production_patterns`, change:
```python
# Before: new_model["has_create_override"] = True
# After:
if is_bulk:
    new_model["override_sources"]["create"].add("bulk")
if is_cacheable:
    new_model["override_sources"]["create"].add("cache")
    new_model["override_sources"]["write"].add("cache")
```

4. In `_build_model_context`, change reads:
```python
# Before: has_create_override = model.get("has_create_override", False)
# After:
has_create_override = bool(model.get("override_sources", {}).get("create"))
has_write_override = bool(model.get("override_sources", {}).get("write"))
```

5. Template context keys remain `has_create_override` and `has_write_override` (bool values). Templates need zero changes.

### Important: Initialization Location
The `defaultdict(set)` initialization MUST happen in `render_module()` BEFORE the preprocessor chain runs, because `_process_relationships` runs first and may mutate models. The init loop should operate on the spec's models list. Since preprocessors create new model dicts (via `{**model, ...}`), the `override_sources` key will be carried forward by spread.

**Caution:** `_process_relationships` creates entirely new synthesized models (through-models) that won't have `override_sources`. Either:
- (a) Initialize in render_module after `_process_relationships`, or
- (b) Use `.get("override_sources", defaultdict(set))` defensively in preprocessors.

**Recommendation:** Option (a) -- initialize after `_process_relationships` since that preprocessor doesn't set override flags.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Circular import detection | Manual dep analysis | Python's import system + tests | If it imports, it works. Run tests. |
| Re-export compatibility | Complex __init__.py | Simple `from X import Y` in renderer.py | Python re-exports are trivial |

## Common Pitfalls

### Pitfall 1: Breaking Test Imports
**What goes wrong:** Tests import `_process_relationships`, `_build_model_context`, etc. directly from `odoo_gen_utils.renderer`. Moving these without re-exports breaks 357+ tests.
**Why it happens:** Extracting to new modules changes the canonical location.
**How to avoid:** Add re-exports in renderer.py for every moved symbol. Test with `python -m pytest python/tests/ -x` after each extraction.
**Warning signs:** ImportError in test output.

### Pitfall 2: Circular Imports Between New Modules
**What goes wrong:** If preprocessors.py imports from renderer_context.py or vice versa, Python raises ImportError.
**Why it happens:** Forgetting the dependency direction rule.
**How to avoid:** Both modules import only from renderer_utils.py. renderer.py imports from all three.
**Warning signs:** ImportError at module load time.

### Pitfall 3: defaultdict Spread Behavior
**What goes wrong:** `{**model}` copies `override_sources` by reference, not deep copy. Multiple preprocessors may share the same defaultdict instance if they spread from the same source.
**Why it happens:** Python dict spread is shallow.
**How to avoid:** Each preprocessor already creates `{**model, ...}` for enriched models. The `override_sources` ref is shared but since each preprocessor adds to it (not replaces), this is actually fine. But if a preprocessor creates a brand new model dict without carrying forward override_sources, it gets lost.
**Warning signs:** Missing override flags on models that should have them.

### Pitfall 4: Missing Symbols in Re-exports
**What goes wrong:** Forgetting to re-export a symbol that tests or CLI import.
**Why it happens:** There are 20+ symbols imported from renderer.py across the codebase.
**How to avoid:** Use the comprehensive import audit below.

### Pitfall 5: StrictUndefined Template Crash After Override Flag Change
**What goes wrong:** If `has_create_override` or `has_write_override` is not set in context, Jinja2 StrictUndefined raises.
**Why it happens:** Override flag migration changes how values flow but context keys must stay identical.
**How to avoid:** The minimal-spec smoke test catches this. Also, _build_model_context always sets these keys explicitly.

## Import Audit (All Symbols Imported from renderer.py)

### Top-level imports in test_renderer.py (line 13-26):
- `MONETARY_FIELD_PATTERNS` -> renderer_utils.py
- `_build_model_context` -> renderer_context.py
- `_build_module_context` -> renderer_context.py
- `_is_monetary_field` -> renderer_utils.py
- `_process_computation_chains` -> preprocessors.py
- `_process_constraints` -> preprocessors.py
- `_process_performance` -> preprocessors.py
- `_process_production_patterns` -> preprocessors.py
- `_topologically_sort_fields` -> renderer_utils.py (recommendation)
- `_validate_no_cycles` -> preprocessors.py
- `get_template_dir` -> stays in renderer.py
- `render_module` -> stays in renderer.py

### Inline imports in test_renderer.py:
- `_process_relationships` (11 occurrences) -> preprocessors.py

### Inline imports in test_render_stages.py:
- `_compute_view_files` -> renderer_context.py
- `_to_python_var` -> renderer_utils.py
- `_to_xml_id` -> renderer_utils.py
- `SEQUENCE_FIELD_NAMES` -> renderer_utils.py
- `_compute_manifest_data` -> renderer_context.py
- Top-level: `create_versioned_renderer`, all 10 render_* stages, `render_module` -> stays in renderer.py

### CLI imports (cli.py):
- `create_renderer` -> stays in renderer.py
- `create_versioned_renderer` -> stays in renderer.py
- `get_template_dir` -> stays in renderer.py
- `render_module` -> stays in renderer.py
- `render_template` -> stays in renderer.py

### Other test files:
- `test_verifier.py`: `get_template_dir`, `render_module` -> stays
- `test_artifact_state.py`: `get_template_dir`, `render_module` -> stays
- `test_golden_path.py`: `get_template_dir`, `render_module` -> stays

**Total unique symbols to re-export:** 15 symbols that move to new modules but must remain importable from `odoo_gen_utils.renderer`.

## Minimal-Spec Smoke Test Approach

### Purpose
Catch StrictUndefined regressions: render a bare-minimum spec through the full `render_module()` pipeline and verify it produces files without crashing.

### Design
```python
def test_minimal_spec_smoke():
    """Render a single-model, zero-features spec through full pipeline."""
    spec = {
        "module_name": "smoke_test",
        "depends": ["base"],
        "models": [{
            "name": "smoke.model",
            "description": "Smoke Test",
            "fields": [{"name": "name", "type": "Char"}],
        }],
        "wizards": [],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        files, warnings = render_module(spec, get_template_dir(), Path(tmpdir))
        assert len(files) > 0
        # Verify key files exist
        module_dir = Path(tmpdir) / "smoke_test"
        assert (module_dir / "__manifest__.py").exists()
        assert (module_dir / "models" / "smoke_model.py").exists()
```

### Placement
Add to `test_render_stages.py` or a new `test_smoke.py`. Runs in < 1 second.

## Code Examples

### Re-export pattern in renderer.py
```python
# Top of renderer.py after extraction
from odoo_gen_utils.renderer_utils import (
    _is_monetary_field,
    _model_ref,
    _to_class,
    _to_python_var,
    _to_xml_id,
    INDEXABLE_TYPES,
    MONETARY_FIELD_PATTERNS,
    NON_INDEXABLE_TYPES,
    SEQUENCE_FIELD_NAMES,
)
from odoo_gen_utils.preprocessors import (
    _process_computation_chains,
    _process_constraints,
    _process_performance,
    _process_production_patterns,
    _process_relationships,
    _topologically_sort_fields,  # if placed in preprocessors
    _validate_no_cycles,
)
from odoo_gen_utils.renderer_context import (
    _build_model_context,
    _build_module_context,
    _compute_manifest_data,
    _compute_view_files,
)

# These re-exports ensure all existing `from odoo_gen_utils.renderer import X`
# continue to work without modifying any downstream code.
```

### Override sources initialization in render_module()
```python
def render_module(spec, template_dir, output_dir, verifier=None):
    _validate_no_cycles(spec)
    env = create_versioned_renderer(spec.get("odoo_version", "17.0"))
    spec = _process_relationships(spec)

    # Initialize override_sources on all models (including synthesized ones)
    for model in spec.get("models", []):
        if "override_sources" not in model:
            model["override_sources"] = defaultdict(set)

    spec = _process_computation_chains(spec)
    spec = _process_constraints(spec)
    spec = _process_performance(spec)
    spec = _process_production_patterns(spec)
    # ... rest unchanged
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Boolean override flags | set[str] override_sources | Phase 36 | Enables v3.2 features to stack overrides without clobbering |
| Monolithic renderer.py | 4-module split | Phase 36 | Prerequisite for SECR/BIZL features |

## Open Questions

1. **_topologically_sort_fields placement: preprocessors.py or renderer_utils.py?**
   - What we know: Used by `_build_model_context` (context) and logically related to preprocessing
   - Recommendation: Place in `renderer_utils.py` to keep dependency graph simple (both preprocessors and context depend on utils only)

2. **Should __all__ be added to new modules?**
   - What we know: No existing module in the package uses __all__
   - Recommendation: Skip for consistency. The underscore prefix convention is sufficient.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | python/pytest.ini (existing) |
| Quick run command | `python -m pytest python/tests/test_renderer.py python/tests/test_render_stages.py -x -q` |
| Full suite command | `python -m pytest python/tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFR-01 | All existing tests pass after extraction | regression | `python -m pytest python/tests/ -x -q` | Yes (796 tests) |
| INFR-01 | Minimal-spec smoke test | smoke | `python -m pytest python/tests/test_render_stages.py::test_minimal_spec_smoke -x` | No - Wave 0 |
| INFR-01 | Override flags use set[str] | unit | `python -m pytest python/tests/test_renderer.py -k "override" -x` | Existing tests cover boolean output |

### Sampling Rate
- **Per task commit:** `python -m pytest python/tests/test_renderer.py python/tests/test_render_stages.py -x -q`
- **Per wave merge:** `python -m pytest python/tests/ -q`
- **Phase gate:** Full suite green (796 tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `test_minimal_spec_smoke` in test_render_stages.py -- bare-minimum spec through full pipeline
- No framework install needed (pytest already configured)
- No new fixtures needed

## Sources

### Primary (HIGH confidence)
- Direct analysis of `python/src/odoo_gen_utils/renderer.py` (1852 lines)
- Direct analysis of `python/tests/test_renderer.py` (3691 lines, top-level + 11 inline imports)
- Direct analysis of `python/tests/test_render_stages.py` (2103 lines, 3 inline imports)
- Grep audit of all `from odoo_gen_utils.renderer import` across entire codebase (6 files)
- CONTEXT.md locked decisions

### Secondary (MEDIUM confidence)
- Line count estimates for new modules (based on function line ranges in current file)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, pure refactoring
- Architecture: HIGH - function-to-module mapping derived from direct code analysis
- Pitfalls: HIGH - import audit is exhaustive, override flag migration path verified against actual code
- Override migration: HIGH - read every line that sets/reads has_create_override and has_write_override

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable -- internal refactoring, no external dependencies)
