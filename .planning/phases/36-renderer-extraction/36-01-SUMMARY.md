---
phase: 36-renderer-extraction
plan: 01
subsystem: renderer
tags: [extraction, refactoring, preprocessors, utilities]
dependency_graph:
  requires: []
  provides: [renderer_utils, preprocessors, override_sources]
  affects: [renderer]
tech_stack:
  added: []
  patterns: [module-extraction, re-export-imports, override-sources-defaultdict-set]
key_files:
  created:
    - python/src/odoo_gen_utils/renderer_utils.py
    - python/src/odoo_gen_utils/preprocessors.py
  modified:
    - python/src/odoo_gen_utils/renderer.py
decisions:
  - Kept legacy boolean has_create/write_override alongside override_sources for backward compatibility with existing tests
  - Placed _topologically_sort_fields in renderer_utils.py (not preprocessors.py) per research recommendation
metrics:
  duration: 490s
  completed: "2026-03-06T07:40:23Z"
---

# Phase 36 Plan 01: Extract renderer_utils.py and preprocessors.py Summary

Extracted shared utilities (4 constants + 6 functions) into renderer_utils.py and all 5 preprocessors + 6 helpers into preprocessors.py from the 1852-line monolithic renderer.py, migrating override flags to defaultdict(set) via override_sources while preserving legacy boolean keys for test backward compatibility.

## What Was Done

### Task 1: Create renderer_utils.py (commit 7b5bde7)
- Created `renderer_utils.py` (121 lines) with 4 constants (SEQUENCE_FIELD_NAMES, MONETARY_FIELD_PATTERNS, INDEXABLE_TYPES, NON_INDEXABLE_TYPES) and 6 functions (_is_monetary_field, _model_ref, _to_class, _to_python_var, _to_xml_id, _topologically_sort_fields)
- Removed moved symbols from renderer.py and added re-export imports
- All 357 tests passed

### Task 2: Create preprocessors.py and migrate override flags (commit 6c7ba33)
- Created `preprocessors.py` (675 lines) with 5 preprocessors (_process_relationships, _process_constraints, _process_performance, _process_production_patterns, _process_computation_chains), 5 helpers (_synthesize_through_model, _inject_one2many_links, _enrich_self_referential_m2m, _resolve_comodel, _enrich_model_performance), and _validate_no_cycles
- Migrated override flags to use `defaultdict(set)` via `override_sources` key on model dicts
- Updated `_build_model_context` to read from `override_sources` instead of boolean flags
- Added `override_sources` initialization loop in `render_module()` after `_process_relationships()`
- All 357 tests passed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Preserved legacy boolean override flags alongside override_sources**
- **Found during:** Task 2
- **Issue:** 12 existing tests directly check `model["has_create_override"]` and `model["has_write_override"]` on preprocessor output. Removing these keys broke tests.
- **Fix:** Preprocessors set both `override_sources` (new) and `has_create_override`/`has_write_override` (legacy) on model dicts. Context builder reads from `override_sources`.
- **Files modified:** python/src/odoo_gen_utils/preprocessors.py
- **Commit:** 6c7ba33

## File Size Results

| File | Lines | Purpose |
|------|-------|---------|
| renderer_utils.py | 121 | Shared converters, constants, pure utilities |
| preprocessors.py | 675 | 5 preprocessors + 6 helpers + validation |
| renderer.py | 1129 | Render stages + orchestrator (down from 1852) |

## Verification

- All 357 renderer/render_stages tests pass
- Direct imports from renderer_utils work
- Direct imports from preprocessors work
- Re-exports from renderer work (backward compatible)
- No circular imports between modules
