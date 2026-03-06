---
phase: 39-approval-workflows
plan: 02
subsystem: codegen
tags: [approval-workflow, jinja2-templates, action-methods, write-guard, header-buttons, record-rules]

# Dependency graph
requires:
  - phase: 39-approval-workflows
    provides: "approval preprocessor context keys (has_approval, approval_action_methods, etc.) from Plan 01"
  - phase: 38-audit-trail
    provides: "write() stacking order (audit outermost), model.py.j2 audit blocks"
  - phase: 37-security-patterns
    provides: "security_roles for group XML ID resolution, record_rule_scopes"
provides:
  - "Approval action methods rendered in model.py.j2 (submit, approve per level, reject, reset)"
  - "Write() state guard blocking direct state modification in model.py.j2"
  - "Header buttons with invisible= and groups= in view_form.xml.j2"
  - "Approval record rules in record_rules.xml.j2"
  - "UserError import conditionally added when has_approval"
  - "Both 17.0 and 18.0 template variants updated"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: ["Jinja2 approval action method rendering loop", "Write guard stacking after audit capture"]

key-files:
  created: []
  modified:
    - "python/src/odoo_gen_utils/templates/17.0/model.py.j2"
    - "python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2"
    - "python/src/odoo_gen_utils/templates/18.0/model.py.j2"
    - "python/src/odoo_gen_utils/templates/18.0/view_form.xml.j2"
    - "python/src/odoo_gen_utils/templates/shared/record_rules.xml.j2"
    - "python/tests/test_renderer.py"
    - "python/tests/test_render_stages.py"

key-decisions:
  - "UserError import added as separate conditional block (not merged with ValidationError)"
  - "Record rules template uses conditional global/group-scoped rendering based on rule dict"
  - "Approval state guard placed after audit old_values capture, before cache clear in 17.0"
  - "18.0 approval guard placed directly in write() since audit not yet ported to 18.0"

patterns-established:
  - "Approval action methods: ensure_one -> has_group check -> state check -> with_context write"
  - "Header buttons: invisible= for state-based visibility, groups= for RBAC"
  - "Write guard stacking: audit skip -> audit capture -> approval guard -> cache -> super()"

requirements-completed: [BIZL-01]

# Metrics
duration: 16min
completed: 2026-03-06
---

# Phase 39 Plan 02: Approval Template Rendering Summary

**Jinja2 template blocks rendering group-gated action methods, write() state guard, header buttons with invisible= and groups=, and two-tier record rules for approval workflows in both 17.0 and 18.0 templates**

## Performance

- **Duration:** 16 min
- **Started:** 2026-03-06T19:36:36Z
- **Completed:** 2026-03-06T19:52:36Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added complete approval action method rendering to model.py.j2 (submit, approve per level, reject, reset_to_draft) with has_group() checks and UserError enforcement
- Added write() state guard in correct stacking position (after audit capture, before cache clear) for 17.0; directly in write() for 18.0
- Added approval header buttons with invisible= and groups= attributes (no deprecated states=) to view_form.xml.j2
- Added approval record rules rendering to record_rules.xml.j2 with conditional global/group-scoped entries
- 35 new tests (23 template rendering + 12 full-pipeline smoke) all passing, 950 total tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: Add approval template blocks to model.py.j2 and view_form.xml.j2 (both 17.0 and 18.0)** - `1c56185` (feat)
2. **Task 2: Full-pipeline smoke tests and regression verification** - `c084f08` (test)

## Files Created/Modified
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Approval state guard in write(), action methods, UserError import
- `python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2` - Header buttons with invisible= and groups=, updated header condition
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Same approval blocks adapted for 18.0 (no audit wrapper)
- `python/src/odoo_gen_utils/templates/18.0/view_form.xml.j2` - Same header buttons adapted for 18.0
- `python/src/odoo_gen_utils/templates/shared/record_rules.xml.j2` - Approval record rules with conditional global/group scope
- `python/tests/test_renderer.py` - TestApprovalTemplateRendering class with 23 tests
- `python/tests/test_render_stages.py` - TestApprovalSmokeFullPipeline class with 12 smoke tests

## Decisions Made
- UserError import is a separate conditional block in the template header, not merged with ValidationError, since they serve different purposes
- Record rules template conditionally uses `global` (for rules without group_xml_id) or `groups` (when group_xml_id present in rule dict), avoiding StrictUndefined errors
- Stacking order verified: audit skip -> audit capture -> approval guard -> cache clear -> super().write() -> constraints -> audit log
- 18.0 template gets approval guard directly in write() since audit blocks are not yet ported to 18.0

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed record rules template accessing non-existent group_xml_id**
- **Found during:** Task 1 (record_rules.xml.j2 template)
- **Issue:** Plan template example used `rule.group_xml_id` but the preprocessor from Plan 01 does not include `group_xml_id` in approval_record_rules dicts (they have xml_id, name, domain_force, scope)
- **Fix:** Made template conditional: render `groups` when `group_xml_id` exists, otherwise render `global` attribute
- **Files modified:** `python/src/odoo_gen_utils/templates/shared/record_rules.xml.j2`
- **Verification:** Record rules render correctly with global scope; tests pass
- **Committed in:** `1c56185` (Task 1 commit)

**2. [Rule 1 - Bug] Fixed stacking order test accounting for audit_skip fast path**
- **Found during:** Task 2 (smoke tests)
- **Issue:** Write guard stacking test found `super().write()` before approval guard because the first occurrence was inside the audit `_audit_skip` fast path (not the main code path)
- **Fix:** Updated test to find main-path super() call after the approval guard position
- **Files modified:** `python/tests/test_renderer.py`, `python/tests/test_render_stages.py`
- **Verification:** All stacking order tests pass correctly
- **Committed in:** `c084f08` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 39 (Approval Workflows) is now complete: preprocessor + context (Plan 01) and templates (Plan 02)
- Models with `approval` in spec now generate complete multi-level approval workflows
- Both 17.0 and 18.0 templates fully support approval rendering
- 950+ tests passing with zero regressions

## Self-Check: PASSED

- SUMMARY.md: FOUND
- Commit 1c56185: FOUND
- Commit c084f08: FOUND
- All 7 key files: FOUND
- Tests: 950 passed (23 template rendering + 12 smoke + 915 existing)

---
*Phase: 39-approval-workflows*
*Completed: 2026-03-06*
