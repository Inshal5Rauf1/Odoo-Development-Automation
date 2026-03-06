---
phase: 38-audit-trail
plan: 01
subsystem: security
tags: [audit-trail, preprocessor, rbac, acl, override-sources]

# Dependency graph
requires:
  - phase: 37-security-foundation
    provides: security_roles, security_acl, override_sources pattern
  - phase: 36-renderer-extraction
    provides: preprocessor chain in render_module, override_sources defaultdict(set)
provides:
  - _process_audit_patterns preprocessor function
  - audit.trail.log companion model synthesis
  - Auditor role injection into security_roles
  - Read-only ACL for audit log model
  - Context builder defaults for has_audit, audit_fields, audit_field_names, audit_exclude, has_audit_log
affects: [38-02-audit-trail-templates, 39-approval-workflow, 40-webhooks]

# Tech tracking
tech-stack:
  added: []
  patterns: [audit-preprocessor-chain, audit-model-synthesis, auditor-role-injection]

key-files:
  created:
    - python/tests/test_preprocessors.py
  modified:
    - python/src/odoo_gen_utils/preprocessors.py
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/renderer_context.py
    - python/tests/test_renderer.py

key-decisions:
  - "Auditor role injected as sibling of lowest role implying base.group_user (not in hierarchy chain)"
  - "Audit log ACL: read-only for auditor + highest role, no access for all others"
  - "Auto-exclude set: One2many, Many2many, Binary, message_ids, activity_ids, write_date, write_uid"

patterns-established:
  - "Audit preprocessor follows pure function pattern: _process_audit_patterns(spec) -> spec"
  - "Synthesized models use _synthesized=True, _is_audit_log=True flags for downstream identification"
  - "Context builder defaults prevent StrictUndefined crashes on new optional keys"

requirements-completed: [SECR-03]

# Metrics
duration: 14min
completed: 2026-03-06
---

# Phase 38 Plan 01: Audit Trail Preprocessor Summary

**Audit trail preprocessor with model synthesis, auditor role injection, ACL enforcement, and context builder defaults for safe template rendering**

## Performance

- **Duration:** 14 min
- **Started:** 2026-03-06T15:00:25Z
- **Completed:** 2026-03-06T15:14:25Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Implemented _process_audit_patterns preprocessor that enriches audited models with has_audit, audit_fields, override_sources["write"]="audit"
- Synthesizes audit.trail.log companion model with res_model, res_id, changes, user_id, operation fields
- Injects auditor role (implies base.group_user) when missing, sets read-only ACL on audit log for auditor + highest role
- Added context builder defaults (has_audit, audit_fields, audit_field_names, audit_exclude, has_audit_log) preventing StrictUndefined crashes
- 23 new tests (14 unit + 9 integration), full suite at 851 passed

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _process_audit_patterns preprocessor** - `6de9ea4` (feat)
2. **Task 2: Wire audit preprocessor into renderer and add context defaults** - `9fc54b8` (feat)

_Note: Task 1 followed TDD (tests written first, then implementation)_

## Files Created/Modified
- `python/src/odoo_gen_utils/preprocessors.py` - Added _build_audit_log_model helper and _process_audit_patterns preprocessor
- `python/src/odoo_gen_utils/renderer.py` - Imported and wired _process_audit_patterns after security preprocessor
- `python/src/odoo_gen_utils/renderer_context.py` - Added has_audit, audit_fields, audit_field_names, audit_exclude to _build_model_context; has_audit_log to _build_module_context
- `python/tests/test_preprocessors.py` - New file: 14 unit tests for audit preprocessor behaviors
- `python/tests/test_renderer.py` - Added 9 integration tests for audit context defaults, rendering, ACL generation

## Decisions Made
- Auditor role is a sibling of the lowest role (implies base.group_user directly), not inserted into the hierarchy chain. This keeps auditors separate from business roles.
- Audit log ACL grants read-only access to auditor and highest role (manager), zero access for all other roles. This matches CONTEXT.md requirement that nobody updates/deletes audit rows.
- Auto-exclude set is computed per model: ALWAYS_EXCLUDE union type-based excludes union spec audit_exclude. Sorted for deterministic output.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Preprocessor chain complete: audit metadata flows through to template context
- Context defaults in place: templates can safely reference has_audit, audit_fields, etc.
- Ready for Plan 02: Jinja2 template blocks for write() override wrapper, audit helper methods, and audit model views

## Self-Check: PASSED

All 5 source/test files verified on disk. Both task commits (6de9ea4, 9fc54b8) verified in git log.

---
*Phase: 38-audit-trail*
*Completed: 2026-03-06*
