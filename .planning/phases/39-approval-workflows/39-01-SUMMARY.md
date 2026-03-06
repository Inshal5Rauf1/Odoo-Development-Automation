---
phase: 39-approval-workflows
plan: 01
subsystem: codegen
tags: [approval-workflow, preprocessor, state-machine, context-builder, jinja2]

# Dependency graph
requires:
  - phase: 38-audit-trail
    provides: "audit preprocessor pattern, override_sources write stacking, _build_model_context structure"
  - phase: 37-security-patterns
    provides: "security_roles structure, group XML ID resolution, record_rule_scopes"
provides:
  - "_process_approval_patterns preprocessor for spec enrichment"
  - "12 approval context keys with defaults in _build_model_context"
  - "has_approval_models key in _build_module_context"
  - "approval wired into render_module() chain after audit"
affects: [39-02-PLAN, model.py.j2, view_form.xml.j2, record_rules.xml.j2]

# Tech tracking
tech-stack:
  added: []
  patterns: ["approval preprocessor follows audit/security preprocessor pure-function pattern"]

key-files:
  created: []
  modified:
    - "python/src/odoo_gen_utils/preprocessors.py"
    - "python/src/odoo_gen_utils/renderer.py"
    - "python/src/odoo_gen_utils/renderer_context.py"
    - "python/tests/test_preprocessors.py"
    - "python/tests/test_renderer.py"

key-decisions:
  - "Action methods transition FROM previous state TO current level state (not from current to next)"
  - "Submit action is a separate entry, not part of approval_action_methods list"
  - "Record rules are two-tier (draft-owner + manager-full), not per-stage"
  - "needs_translate set True for approval models (action methods use _() for UserError)"

patterns-established:
  - "Approval preprocessor: pure function _process_approval_patterns following audit/security pattern"
  - "Context defaults pattern: all 12 approval keys have safe defaults to prevent StrictUndefined"

requirements-completed: [BIZL-01]

# Metrics
duration: 9min
completed: 2026-03-06
---

# Phase 39 Plan 01: Approval Workflow Preprocessor Summary

**Pure-function approval preprocessor enriching model specs with state Selection, action method metadata, group resolution, and two-tier record rules, with 12 context keys defaulted for safe template rendering**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-06T19:24:19Z
- **Completed:** 2026-03-06T19:33:19Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Implemented _process_approval_patterns as a pure function that synthesizes state Selection field, action method specs, submit/reject/reset actions, and two-tier record rules from approval spec blocks
- All approval context keys have safe defaults in _build_model_context preventing StrictUndefined crashes on non-approval models
- 47 new tests (30 preprocessor + 17 context) all passing with zero regressions on the 368-test suite

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _process_approval_patterns preprocessor and wire into pipeline** - `0b7c042` (feat)
2. **Task 2: Add approval context keys to _build_model_context and _build_module_context** - `66d7a27` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/preprocessors.py` - Added _process_approval_patterns pure function (state synthesis, action methods, record rules, override_sources)
- `python/src/odoo_gen_utils/renderer.py` - Wired _process_approval_patterns into render_module() chain after _process_audit_patterns
- `python/src/odoo_gen_utils/renderer_context.py` - Added 12 approval context keys with defaults in _build_model_context, has_approval_models in _build_module_context
- `python/tests/test_preprocessors.py` - Added TestApprovalPreprocessor class with 30 unit tests
- `python/tests/test_renderer.py` - Added TestApprovalIntegration class with 17 integration tests

## Decisions Made
- Action methods transition FROM the previous state TO the current level's state (first level from "draft" to level[0].state), matching the plan's specification exactly
- Submit action is a separate metadata dict (approval_submit_action), not mixed into approval_action_methods list
- Two-tier record rules: draft-owner rule uses OR domain (non-draft OR creator), manager rule uses global [(1,'=',1)]
- needs_translate is set True via both the preprocessor (on model dict) and the context builder (via conditional override)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All approval metadata is available in template context, ready for Plan 02 to render Jinja2 templates
- Template blocks for action methods, header buttons, write() state guard, and record rules can consume the enriched context keys
- Existing tests validate all edge cases (missing approval, rejected state, role validation, explicit group override)

## Self-Check: PASSED

- SUMMARY.md: FOUND
- Commit 0b7c042: FOUND
- Commit 66d7a27: FOUND
- All 5 key files: FOUND
- Tests: 368 passed (30 preprocessor + 17 context + 321 existing)

---
*Phase: 39-approval-workflows*
*Completed: 2026-03-06*
