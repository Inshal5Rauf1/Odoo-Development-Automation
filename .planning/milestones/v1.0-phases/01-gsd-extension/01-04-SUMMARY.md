---
phase: 01-gsd-extension
plan: 04
subsystem: infra
tags: [workflows, scaffold, integration-test, odoo-17, jinja2, end-to-end, gsd-extension]

# Dependency graph
requires:
  - phase: 01-gsd-extension (01-01)
    provides: install.sh, config defaults, agent definitions
  - phase: 01-gsd-extension (01-02)
    provides: 12 /odoo-gen:* command registrations
  - phase: 01-gsd-extension (01-03)
    provides: Python utility package with CLI, renderer, and 15 Jinja2 templates
provides:
  - Scaffold workflow (workflows/scaffold.md) defining 4-phase end-to-end module generation flow
  - Help workflow (workflows/help.md) listing all 12 commands with Active/Planned status
  - Verified end-to-end integration: install.sh -> commands -> agents -> workflows -> Python utilities -> rendered Odoo module
  - Human-verified OCA compliance and Odoo 17.0 correctness of generated output
affects: [02-knowledge-base, 03-validation, 04-input-specification, 05-code-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [4-phase-scaffold-workflow, command-status-tracking]

key-files:
  created:
    - workflows/scaffold.md
    - workflows/help.md
  modified:
    - python/src/odoo_gen_utils/templates/demo_data.xml.j2
    - python/src/odoo_gen_utils/templates/view_form.xml.j2

key-decisions:
  - "Scaffold workflow defines 4 phases: input parsing, spec confirmation, generation (via odoo-gen-utils render-module), post-generation summary"
  - "Help workflow uses inline table with Active/Planned status labels for all 12 commands"
  - "Conditional chatter section in form views: only render mail.thread fields when 'mail' is in module depends"

patterns-established:
  - "Workflow-as-markdown: workflows/*.md files are referenced by commands and agents as execution guides"
  - "Command status tracking: Active for implemented commands, Planned for future-phase commands"

requirements-completed: [EXT-01, EXT-02, EXT-05]

# Metrics
duration: 4min
completed: 2026-03-01
---

# Phase 1 Plan 4: Scaffold & Help Workflows + End-to-End Integration Summary

**Scaffold and help workflows with verified end-to-end pipeline: install.sh through odoo-gen-utils producing a complete Odoo 17.0 module with OCA directory structure**

## Performance

- **Duration:** 4 min (includes checkpoint wait time)
- **Started:** 2026-03-01T18:20:00Z
- **Completed:** 2026-03-01T18:36:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created scaffold workflow defining the complete 4-phase module generation flow (input parsing -> spec confirmation -> generation via odoo-gen-utils -> post-generation summary)
- Created help workflow listing all 12 /odoo-gen:* commands with Active/Planned status labels
- Verified full integration pipeline end-to-end: Python package installs, CLI works, 15 templates list correctly, render-module produces a complete Odoo 17.0 module with correct syntax
- Human-approved: generated module meets Odoo 17.0 and OCA quality standards

## Task Commits

Each task was committed atomically:

1. **Task 1: Create scaffold and help workflow files** - `705041a` (feat)
2. **[Auto-fix] Template bugs found during integration testing** - `09cf440` (fix)
3. **Task 2: End-to-end integration verification** - checkpoint:human-verify (approved, no file changes)

## Files Created/Modified
- `workflows/scaffold.md` - 4-phase scaffold workflow referenced by /odoo-gen:new and odoo-scaffold agent
- `workflows/help.md` - Help content listing all 12 commands with status and usage examples
- `python/src/odoo_gen_utils/templates/demo_data.xml.j2` - Fixed loop.parent.loop.index (unavailable in Jinja2) with set variable pattern
- `python/src/odoo_gen_utils/templates/view_form.xml.j2` - Made chatter section conditional on 'mail' in depends

## Decisions Made
- Scaffold workflow uses `$HOME/.claude/odoo-gen/bin/odoo-gen-utils render-module` as the generation command (not direct Python import)
- Help workflow is self-contained with inline command table (no external workflow reference needed)
- Chatter/mail fields in form views are conditional on 'mail' being in module dependencies to prevent field errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed demo_data.xml.j2 loop.parent.loop.index**
- **Found during:** Task 2 (integration testing)
- **Issue:** Template used `loop.parent.loop.index` which is not available in Jinja2 (unlike Django templates)
- **Fix:** Replaced with `set outer_loop_index` variable pattern before inner loop
- **Files modified:** python/src/odoo_gen_utils/templates/demo_data.xml.j2
- **Verification:** render-module produces valid demo data XML
- **Committed in:** 09cf440

**2. [Rule 1 - Bug] Fixed view_form.xml.j2 unconditional chatter section**
- **Found during:** Task 2 (integration testing)
- **Issue:** Form view template always rendered mail.thread chatter fields (message_ids, activity_ids) even when module didn't depend on 'mail', causing field-not-found errors
- **Fix:** Wrapped chatter section in `{% if 'mail' in module.depends %}` conditional
- **Files modified:** python/src/odoo_gen_utils/templates/view_form.xml.j2
- **Verification:** Module renders correctly both with and without 'mail' dependency
- **Committed in:** 09cf440

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both auto-fixes necessary for correctness. Template bugs would have caused runtime failures in generated modules. No scope creep.

## Issues Encountered

None beyond the auto-fixed template bugs.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 1 is complete: all 5 EXT requirements satisfied
- Extension is ready for use: `/odoo-gen:new` triggers scaffold workflow, agents are discoverable, Python utilities work end-to-end
- Phase 2 (Knowledge Base) and Phase 3 (Validation Infrastructure) can begin in parallel
- The scaffold workflow currently generates from templates; Phase 4 (Input & Specification) will add the NL parsing front-end
- The generated module quality is baseline; Phase 5 (Core Code Generation) will enhance with knowledge-base-aware generation

## Self-Check: PASSED

All 4 files verified present on disk. Both task commits (705041a, 09cf440) verified in git log. All test artifacts (/tmp/test_odoo_module/, .venv-test/, /tmp/test_spec.json) cleaned up.

---
*Phase: 01-gsd-extension*
*Completed: 2026-03-01*
