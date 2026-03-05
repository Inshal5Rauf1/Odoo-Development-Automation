---
phase: 34-production-patterns
plan: 02
subsystem: code-generation
tags: [archival, active-field, transient-model, ir-cron, batch-processing, jinja2]

requires:
  - phase: 34-production-patterns-01
    provides: "_process_production_patterns() preprocessor with bulk/cache logic"
provides:
  - "Archival production pattern: active field injection, archival wizard, batch cron"
  - "Custom template support in render_wizards() via template/form_template keys"
  - "archival_wizard.py.j2 and archival_wizard_form.xml.j2 shared templates"
  - "Batch archival cron method in model.py.j2 with cr.commit() per batch"
affects: []

tech-stack:
  added: []
  patterns: ["archival wizard TransientModel pattern", "batch cron with commit-per-batch", "custom wizard template dispatch"]

key-files:
  created:
    - python/src/odoo_gen_utils/templates/shared/archival_wizard.py.j2
    - python/src/odoo_gen_utils/templates/shared/archival_wizard_form.xml.j2
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/templates/17.0/model.py.j2
    - python/src/odoo_gen_utils/templates/18.0/model.py.j2
    - python/tests/test_renderer.py
    - python/tests/test_render_stages.py

key-decisions:
  - "Used model_name (not model) key in injected cron dict to match existing cron_data.xml.j2 template"
  - "Archival cron filtered from generic cron_methods to avoid duplicate stub methods in model template"

patterns-established:
  - "Custom wizard template dispatch: wizard.get('template', 'wizard.py.j2') enables specialized wizard rendering"
  - "Batch cron with cr.commit(): long-running archival uses while-loop with BATCH_SIZE and commit per batch"

requirements-completed: [PERF-04]

duration: 17min
completed: 2026-03-06
---

# Phase 34 Plan 02: Archival Production Pattern Summary

**Archival strategy with active field injection, TransientModel wizard (days_threshold + action_archive), and batch ir.cron with cr.commit() per batch**

## Performance

- **Duration:** 17 min
- **Started:** 2026-03-05T21:28:48Z
- **Completed:** 2026-03-05T21:45:21Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Models with archival:true automatically get active Boolean field with index=True (Odoo's built-in archive/unarchive behavior)
- Archival wizard TransientModel generated with days_threshold field and action_archive button
- Batch archival cron method injected into model template with cr.commit() per batch to avoid long transactions
- Combined bulk+cache+archival scenario works without conflicts (all three patterns coexist)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend preprocessor for archival + create archival templates (TDD)**
   - `7952692` (test: add failing tests for archival production pattern)
   - `b33ee91` (feat: implement archival production pattern)
2. **Task 2: Integration tests and full suite verification** - `aede708` (test)

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Extended _process_production_patterns() with archival logic, _build_model_context() with archival keys, render_wizards() with custom template dispatch
- `python/src/odoo_gen_utils/templates/shared/archival_wizard.py.j2` - Archival wizard TransientModel template with days_threshold and action_archive
- `python/src/odoo_gen_utils/templates/shared/archival_wizard_form.xml.j2` - Archival wizard form view with action_archive button and act_window action
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Added archival cron method block with batch processing and cr.commit()
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Same archival cron method block for 18.0
- `python/tests/test_renderer.py` - 7 unit tests for archival preprocessor logic
- `python/tests/test_render_stages.py` - 6 integration tests for archival template rendering

## Decisions Made
- Used `model_name` key (not `model`) in injected cron dict to match existing `cron_data.xml.j2` template expectations (plan used `model` key which would have broken cron XML rendering)
- Archival cron filtered from generic `cron_methods` list in `_build_model_context()` to prevent duplicate method stubs in generated model code

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used model_name instead of model key in archival cron dict**
- **Found during:** Task 1 (preprocessor implementation)
- **Issue:** Plan specified `"model": model["name"]` but existing `cron_data.xml.j2` template uses `cron.model_name` and `_build_model_context` filters by `c.get("model_name")`
- **Fix:** Used `"model_name": model["name"]` to match existing convention
- **Files modified:** python/src/odoo_gen_utils/renderer.py
- **Verification:** Integration test test_archival_generates_cron_xml passes
- **Committed in:** b33ee91

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for correctness -- using the wrong key would have broken cron XML generation and cron method filtering.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 34 (Production Patterns) is now complete with all three patterns: bulk create, ORM cache, and archival
- All 353 renderer/render-stages tests pass with zero regressions
- Pre-existing failures in Docker, chromadb, search_index, and verifier_integration tests are unrelated

---
*Phase: 34-production-patterns*
*Completed: 2026-03-06*
