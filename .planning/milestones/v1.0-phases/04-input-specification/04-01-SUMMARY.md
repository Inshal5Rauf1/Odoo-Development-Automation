---
phase: 04-input-specification
plan: 01
subsystem: input-pipeline
tags: [natural-language, specification, follow-up-questions, json-spec, odoo-scaffold]

# Dependency graph
requires:
  - phase: 01-gsd-extension
    provides: "GSD command/agent/workflow pattern, odoo-scaffold agent, commands/new.md and plan.md stubs"
  - phase: 02-knowledge-base
    provides: "12 knowledge base files for Odoo-domain-informed follow-up questions"
provides:
  - "workflows/spec.md -- 4-phase specification pipeline (parse, questions, spec, approve)"
  - "Active /odoo-gen:plan command routing to odoo-scaffold with spec workflow"
  - "Dual-mode odoo-scaffold agent (quick mode via new, spec mode via plan)"
  - "Extended JSON spec schema backward-compatible with render-module"
  - "Tiered follow-up question strategy with complexity detection"
  - "Keyword-to-type mapping table with 25+ field inference patterns"
affects: [04-input-specification, 05-core-code-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [tiered-follow-up-questions, complexity-detection-triggers, extended-spec-schema, dual-mode-agent]

key-files:
  created:
    - "workflows/spec.md"
  modified:
    - "commands/plan.md"
    - "agents/odoo-scaffold.md"

key-decisions:
  - "Tiered question strategy: 3-5 Tier 1 always, 0-3 Tier 2 on complexity triggers, max 8 total"
  - "7 complexity triggers: workflow, multi-company, inheritance, portal, reporting, integration, automation"
  - "Spec JSON extends render-module format with optional fields (backward-compatible)"
  - "Agent KB expanded from 5 to 12 files for domain-specific question generation"
  - "Mode Selection section added to agent for explicit Quick vs Specification mode"

patterns-established:
  - "Tiered follow-up: Always ask high-level, conditionally ask deep questions based on keyword triggers"
  - "Extended spec schema: New optional fields with null defaults preserve backward compatibility"
  - "Dual-mode agent: Single agent, two workflows, mode determined by invoking command"
  - "Keyword-to-type mapping: Deterministic field inference from description keywords"

requirements-completed: [INPT-01, INPT-02, INPT-03]

# Metrics
duration: 5min
completed: 2026-03-02
---

# Phase 4 Plan 1: Input Specification Pipeline Summary

**4-phase specification workflow with tiered Odoo-specific follow-up questions, keyword-to-type field inference, and extended JSON spec schema backward-compatible with render-module**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-01T21:04:50Z
- **Completed:** 2026-03-01T21:10:02Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created complete 445-line specification workflow (`workflows/spec.md`) with 4 phases: NL parsing, tiered follow-up questions, structured spec generation, and approval presentation
- Activated `/odoo-gen:plan` command replacing the stub with a fully wired command routing to odoo-scaffold agent
- Updated odoo-scaffold agent with dual-mode operation (Quick via `/odoo-gen:new`, Specification via `/odoo-gen:plan`) and expanded KB from 5 to 12 files

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the specification workflow** - `46c9ca7` (feat)
2. **Task 2: Activate /odoo-gen:plan command and update odoo-scaffold agent** - `1f3080f` (feat)

## Files Created/Modified
- `workflows/spec.md` - Complete 4-phase specification pipeline workflow (445 lines)
- `commands/plan.md` - Active command routing to odoo-scaffold agent with spec.md workflow reference
- `agents/odoo-scaffold.md` - Dual-mode agent with Mode Selection section and 12 KB file references

## Decisions Made
- Tiered question strategy: 3-5 Tier 1 questions always asked, 0-3 Tier 2 questions conditional on complexity triggers, maximum 8 total to avoid interrogation fatigue
- 7 complexity triggers identified: workflow, multi-company, inheritance, portal, reporting, integration, automation
- Spec JSON schema extends render-module format -- all new fields are optional with null/empty defaults for backward compatibility
- Agent KB expanded from 5 to 12 files to enable domain-informed follow-up question generation
- Mode Selection section added before Workflow section for clarity on quick vs specification mode
- Workflow renamed from "## Workflow" to "## Workflow (Quick Mode)" in agent for disambiguation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Specification workflow is complete and ready for use via `/odoo-gen:plan`
- Plan 04-02 (approval UX and spec rendering) can proceed -- Phase 4 placeholder in spec.md is ready for detailed implementation
- The extended spec schema is defined and documented for Phase 5 (code generation) to consume

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 04-input-specification*
*Completed: 2026-03-02*
