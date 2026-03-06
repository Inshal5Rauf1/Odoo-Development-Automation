---
phase: 37-security-foundation
plan: 02
subsystem: security
tags: [field-groups, sensitive-fields, view-auto-fix, jinja2, preprocessor, rbac]

# Dependency graph
requires:
  - phase: 37-security-foundation
    plan: 01
    provides: _process_security_patterns, security_roles, security_acl, record_rule_scopes
provides:
  - _security_enrich_fields helper for field-level groups= attribute
  - _security_auto_fix_views helper for view element groups injection
  - groups= rendering in all 6 field blocks of model.py.j2
affects: [view-template-security, field-visibility, access-control]

# Tech tracking
tech-stack:
  added: []
  patterns: [field-level groups enrichment, view auto-fix with INFO logging]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/preprocessors.py
    - python/src/odoo_gen_utils/templates/17.0/model.py.j2
    - python/tests/test_renderer.py
    - python/tests/test_render_stages.py

key-decisions:
  - "Sensitive fields default to highest role group (not a specific hard-coded role)"
  - "View auto-fix logs at INFO level (not WARNING) since it is expected behavior, not a problem"
  - "Full external IDs (containing dot) are kept as-is without resolution"

patterns-established:
  - "Field enrichment pattern: preprocessor adds groups key, template renders it conditionally"
  - "View auto-fix pattern: restricted fields automatically get view_groups for view template consumption"

requirements-completed: [SECR-02]

# Metrics
duration: 9min
completed: 2026-03-06
---

# Phase 37 Plan 02: Field-Level Groups Summary

**Field-level groups= attribute support for sensitive fields with preprocessor enrichment and view auto-fix, rendered across all model template blocks**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-06T09:52:33Z
- **Completed:** 2026-03-06T10:01:50Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added _security_enrich_fields: sensitive fields default to highest role group, bare role names resolve to full external IDs, full external IDs kept as-is
- Added _security_auto_fix_views: restricted fields get view_groups key with INFO logging for each auto-fixed field
- Added groups= rendering to all 6 field type blocks in model.py.j2 (Selection, Relational, Sequence, Monetary, Computed, Generic)
- 14 new tests: 9 preprocessor unit tests + 5 render stage integration tests
- Full backward compatibility: fields without groups produce no groups= line

## Task Commits

Each task was committed atomically:

1. **Task 1: Add field-level groups enrichment and view auto-fix to preprocessor** - `74f49fe` (feat, TDD)
2. **Task 2: Add groups= rendering to model.py.j2 and integration tests** - `353a554` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/preprocessors.py` - Added _security_enrich_fields, _security_auto_fix_views, wired into both _process_security_patterns and _inject_legacy_security
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Added groups= conditional rendering to all 6 field type blocks
- `python/tests/test_renderer.py` - 9 new tests in TestSecurityFieldGroups and TestSecurityViewAutoFix classes
- `python/tests/test_render_stages.py` - 5 new tests in TestRenderModelsFieldGroups and TestRenderSecurityFullIntegration classes

## Decisions Made
- Sensitive fields default to highest role group (dynamic, not hard-coded to "manager")
- View auto-fix logs at INFO level (expected enrichment behavior, not a warning)
- Full external IDs (containing '.') kept as-is without resolution attempt

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Field-level security complete: sensitive fields render with groups= in generated Python models
- View elements get view_groups key for template consumption
- Ready for next phase in roadmap

---
*Phase: 37-security-foundation*
*Completed: 2026-03-06*
