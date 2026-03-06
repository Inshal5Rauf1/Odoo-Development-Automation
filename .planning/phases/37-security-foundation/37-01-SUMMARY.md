---
phase: 37-security-foundation
plan: 01
subsystem: security
tags: [rbac, acl, record-rules, security-groups, jinja2, preprocessor]

# Dependency graph
requires:
  - phase: 36-renderer-extraction
    provides: preprocessor pipeline, renderer_context.py, renderer_utils.py
provides:
  - _process_security_patterns preprocessor with RBAC infrastructure
  - security_roles context key for templates
  - Per-model security_acl with per-role CRUD matrix
  - Multi-scope record rules (ownership, department, company)
  - Legacy User/Manager fallback for specs without security block
affects: [37-security-foundation, field-level-security, view-security-auto-fix]

# Tech tracking
tech-stack:
  added: []
  patterns: [spec-driven RBAC, implied_ids group chain, multi-scope record rules]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/preprocessors.py
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/renderer_context.py
    - python/src/odoo_gen_utils/templates/shared/security_group.xml.j2
    - python/src/odoo_gen_utils/templates/shared/access_csv.j2
    - python/src/odoo_gen_utils/templates/shared/record_rules.xml.j2
    - python/tests/test_renderer.py
    - python/tests/test_render_stages.py

key-decisions:
  - "Wizards get full CRUD for all roles (not just user) since they are transient and gated by parent model access"
  - "Record rule ownership scope uses create_uid domain (not user_id) for consistency with Odoo patterns"
  - "Legacy security preprocessor normalizes to same data structure as spec-driven, eliminating template branching"

patterns-established:
  - "Security preprocessor pattern: _process_security_patterns normalizes both legacy and spec-driven to unified security_roles + security_acl structure"
  - "CRUD string parsing: lowercase 'crud' chars to perm_create/read/write/unlink dict"

requirements-completed: [SECR-01]

# Metrics
duration: 11min
completed: 2026-03-06
---

# Phase 37 Plan 01: Security Foundation Summary

**Spec-driven RBAC preprocessor with N-role group hierarchy, per-model ACL matrix, and multi-scope record rules (ownership/department/company)**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-06T09:36:26Z
- **Completed:** 2026-03-06T09:47:34Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Added _process_security_patterns preprocessor supporting arbitrary role hierarchies from spec security.roles
- Per-model ACL matrix with defaults + per-model overrides, generating correct ir.model.access CSV rows
- Multi-scope record rules auto-detecting ownership (user_id), department (department_id), and company (company_id) from model fields
- Full backward compatibility: specs without security block get legacy User/Manager two-tier system
- 25 new tests (20 preprocessor unit tests + 5 render stage integration tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _process_security_patterns preprocessor and wire into pipeline** - `2b3a883` (feat, TDD)
2. **Task 2: Update security templates for conditional spec-driven vs legacy rendering** - `f4e8c55` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/preprocessors.py` - Added _process_security_patterns, _parse_crud, _security_validate_spec, _security_build_roles, _security_build_acl_matrix, _security_detect_record_rule_scopes, _inject_legacy_security
- `python/src/odoo_gen_utils/renderer.py` - Wired preprocessor into pipeline, updated render_security() to use has_record_rules
- `python/src/odoo_gen_utils/renderer_context.py` - Added security_roles and has_record_rules to module context
- `python/src/odoo_gen_utils/templates/shared/security_group.xml.j2` - Rewritten to iterate security_roles (N roles)
- `python/src/odoo_gen_utils/templates/shared/access_csv.j2` - Rewritten to use security_acl per model with per-role wizard CRUD
- `python/src/odoo_gen_utils/templates/shared/record_rules.xml.j2` - Rewritten for multi-scope rules
- `python/tests/test_renderer.py` - 20 new security preprocessor tests + updated wizard ACL expectations
- `python/tests/test_render_stages.py` - 5 new spec-driven security render tests

## Decisions Made
- Wizards get full CRUD for all roles (transient models gated by parent access)
- Record rule ownership scope uses create_uid domain for Odoo convention alignment
- Legacy preprocessor normalizes to same structure as spec-driven, so templates have zero branching
- Updated _make_module_context test helper to run security preprocessor (mirrors render_module behavior)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing wizard ACL tests for new per-role behavior**
- **Found during:** Task 2
- **Issue:** Existing test_wizard_acl_no_manager_line expected 1 wizard ACL line (old: only _user). New template generates 1 line per role (2 for legacy).
- **Fix:** Updated assertion from 1 line to 2 lines, added manager line assertion to multiple wizards test
- **Files modified:** python/tests/test_renderer.py
- **Verification:** All 388 tests pass
- **Committed in:** f4e8c55

**2. [Rule 3 - Blocking] Added security preprocessor to test helper _make_module_context**
- **Found during:** Task 2
- **Issue:** Test helper _make_module_context didn't run preprocessor, so templates got empty security_roles causing StrictUndefined errors
- **Fix:** Added _process_security_patterns call in _make_module_context
- **Files modified:** python/tests/test_render_stages.py
- **Verification:** All existing + new tests pass
- **Committed in:** f4e8c55

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both auto-fixes necessary for backward compatibility of existing tests. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Security preprocessor complete, ready for field-level security (groups= attribute) in future plans
- Template infrastructure supports arbitrary N-role hierarchies
- Record rule scopes extensible for future scope types

---
*Phase: 37-security-foundation*
*Completed: 2026-03-06*
