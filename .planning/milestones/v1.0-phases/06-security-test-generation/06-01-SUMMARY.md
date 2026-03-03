---
phase: 06-security-test-generation
plan: 01
subsystem: testing
tags: [jinja2, odoo, multi-company, record-rules, tdd, renderer, security]

# Dependency graph
requires:
  - phase: 05-core-code-generation
    provides: renderer.py with _build_model_context() and render_module() base implementation

provides:
  - has_company_field detection in _build_model_context() (any() scan for company_id Many2one)
  - workflow_states key in _build_model_context() (list from model.get("workflow_states", []))
  - record_rules.xml.j2 template rendering ir.rule with company_ids OCA shorthand
  - Conditional record_rules.xml generation in render_module() when any model has company_id
  - _compute_manifest_data() inserts security/record_rules.xml when has_company_modules=True
  - 8 new pytest tests covering Phase 6 company-field detection and record_rules generation

affects:
  - 06-02-PLAN (workflow state tests — workflow_states key already added here)
  - Any future phase that enriches render_module() file generation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Enriched model dict pattern: attach computed boolean to model copy before passing to template context"
    - "Conditional file generation: same pattern as has_sequences/sequences.xml applied to has_company_modules/record_rules.xml"
    - "Template filter reuse: to_python_var and model_ref filters used in record_rules.xml.j2"

key-files:
  created:
    - python/src/odoo_gen_utils/templates/record_rules.xml.j2
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/tests/test_renderer.py

key-decisions:
  - "Use company_ids OCA shorthand (not user.company_ids.ids) in domain_force for Odoo 17.0 compatibility"
  - "Enrich model dicts with has_company_field before passing enriched_models to record_rules template context"
  - "workflow_states key added here (not 06-02) to consolidate all renderer.py changes into one plan"
  - "_compute_manifest_data() extended with has_company_modules param (default False for backward compatibility)"

requirements-completed:
  - SECG-01
  - SECG-03
  - SECG-04
  - SECG-05

# Metrics
duration: 5min
completed: 2026-03-02
---

# Phase 6 Plan 01: Security Test Generation (has_company_field + record_rules.xml) Summary

**Multi-company record rule generation via has_company_field detection and record_rules.xml.j2 Jinja2 template, enforcing `[('company_id', 'in', company_ids)]` isolation in Odoo 17.0**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-02T18:00:00Z
- **Completed:** 2026-03-02T18:03:11Z
- **Tasks:** 2 (Task 1 RED pre-completed, Task 2 GREEN executed)
- **Files modified:** 3 (renderer.py modified, record_rules.xml.j2 created, test_renderer.py pre-written)

## Accomplishments

- Added `has_company_field` detection in `_build_model_context()` using `any()` scan for `company_id` Many2one field
- Added `workflow_states` key to `_build_model_context()` return dict (forward-consolidation for Phase 06-02)
- Created `record_rules.xml.j2` template that iterates models with `has_company_field=True` and emits `ir.rule` records with `[('company_id', 'in', company_ids)]` OCA shorthand domain
- Extended `render_module()` with `models_with_company_field` detection, `enriched_models` building, and conditional `record_rules.xml` rendering (step 7b)
- Extended `_compute_manifest_data()` with `has_company_modules` parameter that inserts `security/record_rules.xml` after `security/ir.model.access.csv`
- All 130 tests pass: 122 pre-phase + 8 new Phase 6 tests

## Task Commits

1. **Task 1 (RED): Write failing tests** - Pre-completed before this session (tests existed in test_renderer.py)
2. **Task 2 (GREEN): Implement has_company_field, workflow_states, record_rules.xml.j2** - `954f241` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `python/src/odoo_gen_utils/templates/record_rules.xml.j2` - New Jinja2 template for multi-company ir.rule generation; iterates `models` where `model.has_company_field` is True, emits `<record model="ir.rule">` with `company_ids` domain
- `python/src/odoo_gen_utils/renderer.py` - Added `has_company_field` + `workflow_states` keys to `_build_model_context()`; added company field detection, `enriched_models` building, `_compute_manifest_data()` `has_company_modules` param, and step 7b `record_rules.xml` conditional rendering in `render_module()`
- `python/tests/test_renderer.py` - Pre-written (Task 1 RED): `TestBuildModelContextCompanyField` (4 tests) + `TestRenderModuleRecordRules` (4 tests)

## Decisions Made

- **company_ids OCA shorthand**: Used `[('company_id', 'in', company_ids)]` (not `user.company_ids.ids`). OCA standard for Odoo 17.0, confirmed in RESEARCH.md Pattern 2.
- **enriched_models pattern**: A shallow copy of each model dict with `has_company_field` attached is built before rendering — avoids mutating the original spec, consistent with immutability coding style.
- **workflow_states added here**: Consolidated with other `_build_model_context()` changes rather than splitting across 06-02 to reduce renderer.py churn.
- **_compute_manifest_data() backward-compatible**: Default `has_company_modules=False` ensures existing callers remain unaffected.

## Deviations from Plan

None — plan executed exactly as written. Task 1 was pre-completed per `<current_state>` instructions; Task 2 implemented all four changes as specified.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 06-01 complete: has_company_field detection and record_rules.xml generation working
- Phase 06-02 can proceed: workflow_states key already present in _build_model_context() (pre-added here)
- 130/130 tests passing, zero regressions

---
*Phase: 06-security-test-generation*
*Completed: 2026-03-02*
