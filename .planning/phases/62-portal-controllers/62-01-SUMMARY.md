---
phase: 62-portal-controllers
plan: 01
subsystem: codegen
tags: [pydantic, portal, preprocessor, validation, ownership-path, odoo-portal]

# Dependency graph
requires:
  - phase: 61-computed-chain-generator
    provides: "Preprocessor registry with 15 entries, spec_schema Pydantic models"
provides:
  - "PortalSpec, PortalPageSpec, PortalActionSpec, PortalFilterSpec Pydantic models"
  - "Portal preprocessor at order=95 with spec enrichment"
  - "E23 ownership path validation in semantic.py"
  - "W7 warning for unresolvable models"
  - "Portal test fixture (uni_student_portal, 4 pages)"
affects: [62-portal-controllers-plan-02, portal-templates, portal-rendering]

# Tech tracking
tech-stack:
  added: []
  patterns: [portal-preprocessor-enrichment, ownership-path-validation, multi-hop-model-traversal]

key-files:
  created:
    - "python/src/odoo_gen_utils/preprocessors/portal.py"
    - "python/tests/fixtures/portal_spec.json"
    - "python/tests/test_portal_schema.py"
    - "python/tests/test_portal_preprocessor.py"
    - "python/tests/test_portal_validation.py"
  modified:
    - "python/src/odoo_gen_utils/spec_schema.py"
    - "python/src/odoo_gen_utils/preprocessors/__init__.py"
    - "python/src/odoo_gen_utils/renderer_context.py"
    - "python/src/odoo_gen_utils/validation/semantic.py"
    - "python/tests/test_preprocessor_registry.py"

key-decisions:
  - "Preprocessor at order=95 (after notifications@90, before webhooks@100) per plan spec"
  - "E23 uses _resolve_model_fields helper for spec-first then registry-fallback model lookup"
  - "W7 warning (not error) when models unresolvable -- graceful degradation"
  - "Portal page type validator restricts to {detail, list} -- form type deferred"

patterns-established:
  - "Portal page enrichment: model_var, model_class, singular_name, plural_name derived from route"
  - "Ownership path validation: split on dots, traverse model chain, verify res.users terminal"

requirements-completed: [PRTL-01, PRTL-03]

# Metrics
duration: 13min
completed: 2026-03-09
---

# Phase 62 Plan 01: Portal Schema, Preprocessor & E23 Validation Summary

**Pydantic portal schema (PortalSpec/PortalPageSpec/PortalActionSpec/PortalFilterSpec), preprocessor at order=95 with spec enrichment and auto-depends, plus E23 ownership path validation through model chains**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-09T09:08:31Z
- **Completed:** 2026-03-09T09:22:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Portal Pydantic schema: PortalSpec, PortalPageSpec, PortalActionSpec, PortalFilterSpec models with type validation (detail/list only)
- Portal preprocessor at order=95: enriches spec with has_portal, portal_pages (with model_var/model_class/singular/plural), portal_auth, portal_page_models; auto-adds "portal" to depends
- E23 semantic validation: ownership path traversal through model chains, detects paths that don't terminate at res.users
- Test fixture: uni_student_portal with 4 pages (1 detail + 3 list), 2 models, detail actions, filters
- Registry count updated from 15 to 16 preprocessors with correct order sequence

## Task Commits

Each task was committed atomically:

1. **Task 1: Pydantic schema + Test fixture + Portal preprocessor** (TDD)
   - `6ff7de0` (test: failing tests for portal schema and preprocessor)
   - `815d707` (feat: portal schema, preprocessor, and renderer context)
2. **Task 2: E23 ownership path validation** (TDD)
   - `615b8ca` (test: failing tests for E23 ownership path validation)
   - `b50739b` (feat: E23 portal ownership path validation)

## Files Created/Modified
- `python/src/odoo_gen_utils/spec_schema.py` - Added PortalActionSpec, PortalFilterSpec, PortalPageSpec, PortalSpec Pydantic models; portal field on ModuleSpec
- `python/src/odoo_gen_utils/preprocessors/portal.py` - Portal preprocessor at order=95 with spec enrichment
- `python/src/odoo_gen_utils/preprocessors/__init__.py` - Added portal re-export for backward compatibility
- `python/src/odoo_gen_utils/renderer_context.py` - Added has_portal, has_controllers update, portal manifest files
- `python/src/odoo_gen_utils/validation/semantic.py` - Added _check_e23 ownership path validation, spec parameter to semantic_validate
- `python/tests/fixtures/portal_spec.json` - 4-page uni_student_portal test fixture with 2 models
- `python/tests/test_portal_schema.py` - 19 tests for Pydantic schema validation
- `python/tests/test_portal_preprocessor.py` - 16 tests for preprocessor behavior and registry
- `python/tests/test_portal_validation.py` - 10 tests for E23 ownership path validation
- `python/tests/test_preprocessor_registry.py` - Updated count (15->16) and order sequence (added 95)

## Decisions Made
- Preprocessor at order=95 as specified in plan (between notifications@90 and webhooks@100)
- E23 uses _resolve_model_fields helper that checks spec models first, then falls back to registry
- W7 warning (not error) for unresolvable models provides graceful degradation without blocking generation
- Page type validator restricts to {detail, list}; form type explicitly deferred per context decisions
- Naive singularization (_singular helper) for route-derived names -- sufficient for common English plurals

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed preprocessor registry name mismatch in test**
- **Found during:** Task 1 (preprocessor registry tests)
- **Issue:** Test referenced "notifications" and "webhooks" but actual registered names are "notification_patterns" and "webhook_patterns"
- **Fix:** Updated test assertions to use actual registered preprocessor names
- **Files modified:** python/tests/test_portal_preprocessor.py
- **Verification:** All registry tests pass
- **Committed in:** 815d707 (part of Task 1 feat commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test name correction. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Portal Pydantic schema ready for template rendering (plan 02)
- Preprocessor enrichment provides all context keys needed by Jinja templates
- E23 validation will catch ownership path errors before generation runs
- Test fixture available for integration testing in plan 02

---
*Phase: 62-portal-controllers*
*Completed: 2026-03-09*
