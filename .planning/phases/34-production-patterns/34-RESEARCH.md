# Phase 34: Production Patterns - Research

**Researched:** 2026-03-06
**Domain:** Odoo ORM performance patterns (bulk create, ORM cache, archival)
**Confidence:** HIGH

## Summary

Phase 34 adds three production-scale patterns to the Odoo module generator: bulk operations via `@api.model_create_multi`, reference data caching via `@tools.ormcache`, and archival strategies via `active` field + cron cleanup. All three patterns follow the established preprocessor + template extension architecture used in Phases 28-33.

The existing codebase already has the foundational pieces: Phase 29 introduced `create()`/`write()` overrides in the model template (both 17.0 and 18.0 templates already use `@api.model_create_multi` for constraint post-processing), Phase 30 provides cron infrastructure, and Phase 33 established the `_process_performance()` preprocessor. Phase 34 extends these with a new `_process_production_patterns()` preprocessor that enriches the spec with bulk, caching, and archival metadata, plus template additions for ormcache imports and archival wizard/cron generation.

A critical integration point: the existing `has_create_override` and `has_write_override` flags from Phase 29 constraints must merge cleanly with the new bulk/caching overrides. The template already renders `@api.model_create_multi def create()` when `has_create_override` is true -- the bulk pattern needs the same decorator but with different post-processing logic (batched operations), and caching needs `self.clear_caches()` calls in both `create()` and `write()`. This means the template must be refactored to handle combined scenarios (constraints + bulk + cache invalidation in a single create/write override).

**Primary recommendation:** Add a `_process_production_patterns()` preprocessor that runs after `_process_performance()`, enriching models with `bulk`, `cacheable`, and `archival` flags. Extend model templates to conditionally add `from odoo import tools` import, `@tools.ormcache` decorators on lookup methods, `self.clear_caches()` in create/write, `active` field for archival models, and batch archival cron methods. Generate archival wizards using the existing wizard rendering infrastructure and archival crons using the existing cron infrastructure.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PERF-02 | Models with `bulk: true` generate `@api.model_create_multi` on `create()` with batched post-processing | Odoo ORM API: `@api.model_create_multi` receives `vals_list`, returns recordset; post-processing loops over created records; pre-processing can compute shared values once outside loop |
| PERF-03 | Near-static reference models generate `@tools.ormcache` on lookup methods with cache invalidation in `write()`/`create()` | `from odoo import tools` + `@tools.ormcache('key')` decorator; invalidation via `self.clear_caches()` in create/write overrides |
| PERF-04 | Models with `archival: true` generate `active` field, archival wizard TransientModel, and `ir.cron` scheduled action | Active field enables Odoo built-in archive/unarchive UI; cron uses batch processing with `self.env.cr.commit()` per batch; wizard provides manual archival action |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | >=3.1 | Template rendering for model/wizard/cron code | Already used throughout the project |
| pytest | >=8.0 | Test framework | Already configured in pyproject.toml |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| odoo.tools | N/A (Odoo built-in) | `ormcache` decorator | Generated code imports `from odoo import tools` |
| odoo.api | N/A (Odoo built-in) | `model_create_multi` decorator | Generated code uses `@api.model_create_multi` |

No new dependencies needed -- all changes are to generated code templates and the renderer preprocessor.

## Architecture Patterns

### Recommended Changes
```
python/src/odoo_gen_utils/
  renderer.py                    # Add _process_production_patterns(), extend _build_model_context()
  templates/
    17.0/model.py.j2             # Extend for bulk/cache/archival patterns
    18.0/model.py.j2             # Same extensions (both templates are nearly identical)
    shared/
      archival_wizard.py.j2      # NEW: archival wizard TransientModel
      archival_wizard_form.xml.j2 # NEW: archival wizard form view
python/tests/
  test_renderer.py               # Add tests for production patterns
```

### Pattern 1: Preprocessor Chain Extension
**What:** Add `_process_production_patterns()` as a new preprocessor in the `render_module()` pipeline, called after `_process_performance()`.
**When to use:** When spec contains `bulk: true`, `cacheable: true`, or `archival: true` on any model.
**Integration point in render_module():**
```python
spec = _process_performance(spec)
spec = _process_production_patterns(spec)  # NEW -- Phase 34
```

### Pattern 2: Merged Create/Write Overrides
**What:** The model template currently renders create/write overrides only for Phase 29 constraints. Phase 34 needs to extend these overrides for bulk post-processing and cache invalidation.
**Critical insight:** The template must handle all combinations:
- Constraints only (existing): `@api.model_create_multi def create() -> super() -> _check_*()`
- Bulk only: `@api.model_create_multi def create() -> super() -> batch post-processing`
- Cache only: `create() -> super() -> clear_caches()` and `write() -> super() -> clear_caches()`
- Combined: All of the above in one create/write method

**Implementation approach:** Extend `has_create_override` and `has_write_override` to also be True when `bulk` or `cacheable` is set. Add template blocks for bulk post-processing and cache invalidation that render alongside constraint checks.

### Pattern 3: Archival as Spec Enrichment
**What:** When `archival: true` is set on a model, the preprocessor:
1. Injects an `active` field (Boolean, default=True) into the model's fields list
2. Adds an archival wizard to `spec["wizards"]` (reuses existing wizard rendering infrastructure)
3. Adds an archival cron job to `spec["cron_jobs"]` (reuses existing cron rendering infrastructure)
**Why this approach:** No new render stages needed -- archival leverages existing wizard + cron pipelines.

### Anti-Patterns to Avoid
- **Separate create/write methods per feature:** Do NOT generate multiple `create()` overrides. Odoo allows only one `create()` per class. All logic must merge into a single override.
- **Forgetting to handle bulk=true without constraints:** The existing `has_create_override` is currently only triggered by constraints. Must extend it to also trigger for `bulk: true`.
- **Using self.env.cr.commit() in regular model methods:** Commit-per-batch is ONLY safe in cron-executed methods (separate transaction). Regular model methods must never commit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Archival wizard rendering | Custom archival wizard render stage | Existing `render_wizards()` pipeline | Archival wizard is just a TransientModel -- inject into `spec["wizards"]` during preprocessing |
| Archival cron rendering | Custom archival cron render stage | Existing `render_cron()` pipeline | Archival cron is just an ir.cron entry -- inject into `spec["cron_jobs"]` during preprocessing |
| Cache invalidation | Custom cache clear mechanism | `self.clear_caches()` (Odoo built-in) | Odoo's Registry.clear_caches() handles all ormcache-decorated methods |
| Batch processing in cron | Custom batch iterator | `search(limit=BATCH_SIZE)` + `cr.commit()` loop | Standard Odoo pattern; well-tested in production |

## Common Pitfalls

### Pitfall 1: Conflicting Create Override Decorators
**What goes wrong:** If both `has_create_override` (constraints) and `bulk` are True, the template might try to render two `create()` methods.
**Why it happens:** Phase 29 introduced `@api.model_create_multi def create()` for constraints. Phase 34 also needs it for bulk.
**How to avoid:** Merge all create-override logic into a single template block. Use separate conditional sections within one `create()` method: constraint checks, bulk post-processing, cache invalidation.
**Warning signs:** `SyntaxError: duplicate method` in generated Python.

### Pitfall 2: Cache Invalidation in write() Missing Trigger Fields
**What goes wrong:** `clear_caches()` is called on every `write()`, even when non-cached fields are modified, causing unnecessary cache invalidation.
**Why it happens:** Unlike constraints (which check trigger fields), cache invalidation is unconditional.
**How to avoid:** For this phase, unconditional `clear_caches()` in write/create is acceptable for near-static reference models (they rarely write). Optimization with field-level checks is a future enhancement.

### Pitfall 3: Archival Cron Without Batch Commit
**What goes wrong:** Archiving thousands of records in a single transaction causes long locks and potential OOM.
**Why it happens:** Default cron method uses a single `search().write()` call.
**How to avoid:** Generate cron method with `search(limit=BATCH_SIZE)` loop and `self.env.cr.commit()` after each batch. Include proper exception handling with `try/except` per batch.

### Pitfall 4: Missing `active` Field Index
**What goes wrong:** Odoo implicitly filters `active=True` on every search. Without an index, this is slow on large tables.
**Why it happens:** The `active` field is injected but `index=True` is forgotten.
**How to avoid:** Always inject `active` with `index=True` (Odoo convention).

### Pitfall 5: tools Import Not Added
**What goes wrong:** Generated model uses `@tools.ormcache` but the import line `from odoo import tools` is missing.
**Why it happens:** The template import line only conditionally adds `api` -- `tools` is a new conditional import.
**How to avoid:** Add `needs_tools` context key and conditionally render `from odoo import tools` in the template.

## Code Examples

### Bulk Create Pattern (Generated Code)
```python
# Source: Odoo ORM API + odoomastery.com verified pattern
from odoo import api, fields, models

class CourseEnrollment(models.Model):
    _name = "academy.enrollment"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Batched post-processing: compute once, apply to all
        for record in records:
            record._post_create_processing()
        return records

    def _post_create_processing(self):
        """Post-creation logic executed for each record in batch."""
        # TODO: implement post-create processing
        pass
```

### ORM Cache Pattern (Generated Code)
```python
# Source: Odoo tools.ormcache documentation + Cybrosys verified pattern
from odoo import api, fields, models, tools

class AcademicDepartment(models.Model):
    _name = "academy.department"

    @tools.ormcache('self.env.uid', 'code')
    def _get_by_code(self, code):
        """Cached lookup by code for near-static reference data."""
        return self.search([('code', '=', code)], limit=1).id

    @api.model_create_multi
    def create(self, vals_list):
        self.clear_caches()
        return super().create(vals_list)

    def write(self, vals):
        self.clear_caches()
        return super().write(vals)
```

### Archival Cron Pattern (Generated Code)
```python
# Source: Odoo coding guidelines + Numla resilient crons pattern
@api.model
def _cron_archive_old_records(self):
    """Scheduled action: archive records older than threshold.

    Uses batch processing with commit-per-batch to avoid long transactions.
    """
    BATCH_SIZE = 100
    cutoff = fields.Date.today() - relativedelta(days=self.env['ir.config_parameter'].sudo().get_param(
        'module_name.archival_days', default=365
    ))
    while True:
        records = self.search([
            ('active', '=', True),
            ('create_date', '<', cutoff),
        ], limit=BATCH_SIZE)
        if not records:
            break
        records.write({'active': False})
        self.env.cr.commit()
```

### Archival Wizard Pattern (Generated Code)
```python
# Source: Existing import_wizard.py.j2 pattern adapted for archival
from odoo import api, fields, models

class ArchiveEnrollmentWizard(models.TransientModel):
    _name = "academy.enrollment.archive.wizard"
    _description = "Archive Enrollments"
    _transient_max_hours = 1.0

    days_threshold = fields.Integer(
        string="Archive records older than (days)",
        default=365,
        required=True,
    )

    def action_archive(self):
        self.ensure_one()
        cutoff = fields.Date.today() - relativedelta(days=self.days_threshold)
        records = self.env['academy.enrollment'].search([
            ('active', '=', True),
            ('create_date', '<', cutoff),
        ])
        records.write({'active': False})
        return {'type': 'ir.actions.act_window_close'}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@api.model def create(self, vals)` | `@api.model_create_multi def create(self, vals_list)` | Odoo 12.0+ | All modern Odoo create overrides should use model_create_multi |
| Manual LRU dict caching | `@tools.ormcache()` decorator | Odoo 8.0+ (stable API) | Built-in LRU with automatic Registry-level management |
| Manual `active` field + domain filter | Built-in active field behavior (auto-filter) | Odoo core feature | Odoo automatically adds `('active', '=', True)` to search domains |

**Important:** The `@api.model_create_multi` decorator is already used in the existing 17.0 and 18.0 model templates for Phase 29 constraint create overrides. Phase 34 extends this, not replaces it.

## Template Integration Analysis

### Current Template State (Critical for Planning)

Both `17.0/model.py.j2` and `18.0/model.py.j2` currently have:
1. **Import line:** `from odoo import {{ 'api, ' if needs_api }}fields, models` -- needs `tools` conditional
2. **Create override block (lines 203-212 in 17.0):** Triggered by `has_create_override` from Phase 29 constraints
3. **Write override block (lines 213-224 in 17.0):** Triggered by `has_write_override` from Phase 29 constraints
4. **Cron methods block (lines 225-234 in 17.0):** Renders `@api.model` stub methods

### Required Template Changes

1. **Import line:** Add `{{ ', tools' if needs_tools }}` to conditional imports
2. **New `@tools.ormcache` lookup method block:** Before create/write overrides
3. **Extend create override logic:** Add bulk post-processing + cache invalidation conditionals
4. **Extend write override logic:** Add cache invalidation conditional
5. **Extend cron methods block:** Add archival cron with batch commit pattern

### Context Keys to Add (_build_model_context)

| Key | Type | When Set | Template Use |
|-----|------|----------|-------------|
| `is_bulk` | bool | `model.get("bulk", False)` | Render post-processing in create |
| `is_cacheable` | bool | `model.get("cacheable", False)` | Render ormcache lookup + clear_caches |
| `cache_lookup_field` | str | From cacheable config (e.g., "code") | ormcache key parameter |
| `is_archival` | bool | `model.get("archival", False)` | Inject active field, render archival cron |
| `needs_tools` | bool | `is_cacheable` | Conditional `tools` import |
| `archival_batch_size` | int | Default 100 | Cron batch size |
| `archival_days` | int | Default 365 | Default cutoff threshold |

## Open Questions

1. **Cache lookup method name convention**
   - What we know: Odoo uses `@tools.ormcache` on arbitrary methods; common patterns are `_get_by_code()`, `_get_by_name()`
   - What's unclear: Should the spec define the lookup field explicitly (`cacheable: {field: "code"}`) or auto-detect from unique Char fields?
   - Recommendation: Use explicit spec config `cacheable: true` with optional `cache_key: "code"` field. Default to first unique Char field if not specified.

2. **Archival wizard vs. just cron**
   - What we know: Success criteria require both wizard + cron
   - What's unclear: Whether wizard should have a preview step showing count of records to archive
   - Recommendation: Simple single-step wizard (threshold input + confirm button). No preview -- keeps it simple and consistent with existing wizard patterns.

3. **Merging create/write overrides across features**
   - What we know: Template currently has separate `has_create_override`/`has_write_override` blocks for constraints
   - What's unclear: Best Jinja2 structure for combining constraints + bulk + cache in one method
   - Recommendation: Extend `has_create_override` to be True whenever ANY feature needs create override (constraints OR bulk OR cacheable). Within the create method body, use conditional blocks: `{% if create_constraints %}`, `{% if is_bulk %}`, `{% if is_cacheable %}`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | python/pyproject.toml |
| Quick run command | `cd /home/inshal-rauf/Odoo_module_automation && python -m pytest python/tests/test_renderer.py -x -q --tb=short` |
| Full suite command | `cd /home/inshal-rauf/Odoo_module_automation && python -m pytest python/tests/ -x -q --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-02 | bulk:true generates @api.model_create_multi with batch post-processing | unit | `python -m pytest python/tests/test_renderer.py -x -k "test_bulk"` | Wave 0 |
| PERF-02 | bulk:true create override merges with constraint overrides | unit | `python -m pytest python/tests/test_renderer.py -x -k "test_bulk_with_constraints"` | Wave 0 |
| PERF-03 | cacheable:true generates @tools.ormcache lookup method | unit | `python -m pytest python/tests/test_renderer.py -x -k "test_ormcache"` | Wave 0 |
| PERF-03 | cacheable:true adds clear_caches() in create/write | unit | `python -m pytest python/tests/test_renderer.py -x -k "test_cache_invalidation"` | Wave 0 |
| PERF-03 | cacheable:true adds `from odoo import tools` import | unit | `python -m pytest python/tests/test_renderer.py -x -k "test_tools_import"` | Wave 0 |
| PERF-04 | archival:true injects active field with index=True | unit | `python -m pytest python/tests/test_renderer.py -x -k "test_archival_active"` | Wave 0 |
| PERF-04 | archival:true generates archival wizard TransientModel | unit | `python -m pytest python/tests/test_renderer.py -x -k "test_archival_wizard"` | Wave 0 |
| PERF-04 | archival:true generates ir.cron with batch commit pattern | unit | `python -m pytest python/tests/test_renderer.py -x -k "test_archival_cron"` | Wave 0 |
| PERF-04 | archival cron method uses batch processing with cr.commit() | unit | `python -m pytest python/tests/test_renderer.py -x -k "test_archival_batch"` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest python/tests/test_renderer.py -x -q --tb=short`
- **Per wave merge:** `python -m pytest python/tests/ -x -q --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `python/tests/test_renderer.py` -- add test_bulk_*, test_ormcache_*, test_archival_* test methods (file exists, tests do not)
- [ ] No new test files needed -- all tests go in existing test_renderer.py following Phase 33 pattern

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `renderer.py` (preprocessor chain, _build_model_context, render_module pipeline)
- Codebase analysis: `17.0/model.py.j2` and `18.0/model.py.j2` (current template structure, existing create/write overrides)
- Codebase analysis: `cron_data.xml.j2` (existing cron template)
- Codebase analysis: `wizard.py.j2` and `import_wizard.py.j2` (existing wizard templates)

### Secondary (MEDIUM confidence)
- [Odoo ORM API Documentation](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html) - model_create_multi, ormcache
- [ORM Cache - Cybrosys Odoo 17 Book](https://www.cybrosys.com/odoo/odoo-books/odoo-17-development/performance-optimisation/orm-cache/) - ormcache usage patterns
- [Optimize create overrides - Odoo Mastery](https://odoomastery.com/blog/tips-4/optimize-create-overrides-by-using-the-decorator-model-create-multi-54) - model_create_multi pattern
- [Resilient Odoo Crons - Numla](https://numla.com/blog/odoo-development-18/how-to-design-resilient-odoo-crons-17) - batch commit pattern
- [Odoo Coding Guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html) - cr.commit() rules

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, purely template/preprocessor work
- Architecture: HIGH - follows established patterns from Phases 28-33 (preprocessor + template extension)
- Pitfalls: HIGH - create/write override merging is the main risk, well-understood from codebase analysis
- Template integration: HIGH - both 17.0 and 18.0 templates analyzed line-by-line

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable -- Odoo ORM API is mature)
