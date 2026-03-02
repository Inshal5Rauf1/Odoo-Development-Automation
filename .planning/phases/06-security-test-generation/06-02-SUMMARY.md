---
phase: 06-security-test-generation
plan: 02
subsystem: testing
tags: [jinja2, odoo-tests, TransactionCase, AccessError, workflow-transitions, odoo-17]

# Dependency graph
requires:
  - phase: 06-01-security-test-generation
    provides: renderer.py workflow_states key and record_rules.xml template
  - phase: 05-core-code-generation
    provides: generate.md wave pipeline structure and odoo-test-gen agent stub
provides:
  - test_model.py.j2 with all 7 test categories (CRUD write/unlink, access rights, workflow)
  - odoo-test-gen.md full Phase 6 system prompt (all 7 test types, Phase 5 restriction removed)
  - odoo-security-gen.md complete standalone agent with OCA patterns and execution steps
  - generate.md Wave 2 Task B prompt expanded to Phase 6 scope
affects: [phase-07-human-review, any plan using generate.md workflow]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TransactionCase with groups_id [(6, 0, [...])] for test user creation in access rights tests"
    - "with_user(non_admin) + assertRaises(AccessError) for ACL testing pattern"
    - "workflow transition tests via action_{state_key}() method calls"
    - "browse(record_id).exists() assertion pattern for unlink verification"

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/templates/test_model.py.j2
    - agents/odoo-test-gen.md
    - agents/odoo-security-gen.md
    - workflows/generate.md

key-decisions:
  - "test_model.py.j2 Jinja2 template handles all 7 test categories in the static scaffold; odoo-test-gen agent rewrites with domain-specific assertions"
  - "odoo-security-gen is NOT added to generate.md pipeline — security is deterministic via Jinja2, agent is standalone only for post-validation remediation"
  - "Workflow transition tests guarded by: state_field not None AND workflow_states|length >= 2"
  - "Access rights tests use groups_id [(6, 0, [...])] to SET group list (not additive (4, id) form)"
  - "standalone lowercase in frontmatter description for grep verification compatibility"

patterns-established:
  - "Phase 6 test pattern: write test finds first required Char field; falls back to id assertion if none"
  - "Phase 6 unlink pattern: store record_id before unlink, assertFalse browse().exists()"
  - "Phase 6 access pattern: 2-user setup (module_user + base.group_user only), with_user() on each"
  - "Phase 6 workflow pattern: consecutive state pairs from workflow_states list, action_{to_key}() call"

requirements-completed:
  - SECG-02
  - SECG-04
  - TEST-01
  - TEST-02
  - TEST-03
  - TEST-04
  - TEST-05
  - TEST-06

# Metrics
duration: 3min
completed: 2026-03-02
---

# Phase 6 Plan 02: Test Template Expansion and Agent Activation Summary

**test_model.py.j2 extended to generate CRUD write/unlink, access rights (with_user + AccessError), and workflow transition tests; odoo-test-gen and odoo-security-gen fully activated as standalone agents**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T18:02:54Z
- **Completed:** 2026-03-02T18:06:20Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Expanded `test_model.py.j2` to generate all 7 test categories: create, read, name_get (Phase 5), plus write, unlink, test_user_can_create, test_no_group_cannot_create, and workflow transitions (Phase 6)
- Rewrote `odoo-test-gen.md` with full Phase 6 scope — removed "Phase 5 only" restriction, added patterns for all 7 test categories including access rights group ref pattern
- Replaced stub `odoo-security-gen.md` with complete standalone agent system prompt including canonical OCA security patterns (group IDs, ACL CSV format, implied_ids, record rules) and anti-patterns table
- Updated `generate.md` Wave 2 Task B prompt to trigger Phase 6 expanded test generation scope
- All 130 renderer tests pass (no regressions from template changes)

## Task Commits

Each task was committed atomically:

1. **Task 1: Expand test_model.py.j2 with new test categories** - `80e00f4` (feat)
2. **Task 2: Activate odoo-test-gen.md, odoo-security-gen.md, update generate.md** - `f421c76` (feat)

**Plan metadata:** (committed below)

## Files Created/Modified

- `python/src/odoo_gen_utils/templates/test_model.py.j2` - Added test_write, test_unlink, test_user_can_create, test_no_group_cannot_create, and conditional workflow transition tests; includes AccessError import
- `agents/odoo-test-gen.md` - Full Phase 6 scope (7 test categories), Phase 5 restriction removed, execution steps updated to rewrite entire file
- `agents/odoo-security-gen.md` - Complete standalone agent with 6-step execution pattern, canonical patterns for all Odoo 17.0 security constructs, anti-patterns table
- `workflows/generate.md` - Wave 2 Task B prompt expanded to list all 7 Phase 6 test categories with AccessError import instruction and group ref pattern

## Decisions Made

- odoo-security-gen is NOT added to the generate.md wave pipeline — security generation is fully deterministic via Jinja2 templates (no AI reasoning needed), so the agent's role is post-validation remediation only
- Workflow tests use a hard guard (state_field AND workflow_states|length >= 2) to prevent degenerate single-state cases
- Access rights tests in the Jinja2 template create users inline per test method (not in setUpClass) to avoid inter-test state contamination in the static scaffold
- The "standalone" keyword in odoo-security-gen frontmatter uses lowercase for grep verification compatibility

## Deviations from Plan

None - plan executed exactly as written.

The template already contained the new test methods from a prior partial write (git tracked as M). Verification confirmed all assertions pass and 130/130 tests pass.

## Issues Encountered

- Template file showed as already modified (M in git status) when the session started — the template already had the test methods in it. Ran the Jinja2 render test which confirmed all required test methods were present and functional. Committed cleanly.
- Initial Jinja2 render test used a plain Environment without registering `to_class` filter — switched to `create_renderer()` from renderer.py which registers all custom filters.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 Plan 02 complete. Phase 6 now has both plans (06-01 record rules, 06-02 test expansion) done.
- Phase 6 SECG and TEST requirements: SECG-01 through SECG-05 and TEST-01 through TEST-06 are satisfied across both plans.
- Ready for Phase 7: Human Review & Quality Loops (REVW-01..06, QUAL-06, 09, 10).

---
*Phase: 06-security-test-generation*
*Completed: 2026-03-02*

## Self-Check: PASSED
