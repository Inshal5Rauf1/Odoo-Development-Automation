---
phase: 05-core-code-generation
plan: 03
subsystem: workflows
tags: [odoo, generate, orchestration, two-wave, spec, requirements]

# Dependency graph
requires:
  - phase: 05-core-code-generation-01
    provides: render-module CLI and Jinja2 templates
  - phase: 04-input-specification
    provides: spec.md workflow with approval gate
provides:
  - Two-wave generation orchestration workflow (generate.md)
  - generate.md trigger wired into spec.md approval handler (Step 4.3)
  - Corrected REQUIREMENTS.md CODG-09 (tree not list) and CODG-10 (README.rst)
  - CODG-02 annotated with Phase 7 deferral note for CRUD overrides
affects:
  - 05-core-code-generation (generate.md is the orchestrator for all code gen)
  - 06-security-test-generation (odoo-view-gen, odoo-test-gen referenced in Wave 2)
  - 07-human-review (CRUD overrides deferred here per Decision A)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Two-wave generation: Wave 1 (sequential model method bodies) then Wave 2 (parallel view/test enrichment)
    - Workflow chaining: spec.md approval directly triggers generate.md via @-reference
    - Agent spawn per model: one odoo-model-gen Task per model file in Wave 1

key-files:
  created:
    - workflows/generate.md
  modified:
    - workflows/spec.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "generate.md trigger placed in spec.md Step 4.3 AFTER spec commit and BEFORE report step"
  - "Wave 1 sequential guard: all odoo-model-gen tasks must complete before Wave 2 spawns"
  - "Wave 2 parallel: odoo-view-gen and odoo-test-gen run simultaneously using Task tool"
  - "No kanban views in generate.md (Decision F — deferred to Phase 7)"
  - "No CRUD overrides in generate.md (Decision A — deferred to Phase 7)"
  - "CODG-09 corrected: Odoo 17.0 uses <tree>, not <list> (list is Odoo 18+ only)"
  - "CODG-10 corrected: README.rst is OCA standard, not README.md"

patterns-established:
  - "Two-pass hybrid generation: Jinja2 for structure, agents for method bodies"
  - "Sequential Wave 1 before parallel Wave 2 ensures model files are complete when view-gen reads them"
  - "Error handling per wave: model errors continue to next model; Wave 2 errors dont block commit"

requirements-completed:
  - CODG-01
  - CODG-09
  - CODG-10

# Metrics
duration: 3min
completed: 2026-03-02
---

# Phase 5 Plan 03: Generate Workflow + Spec Hook + Requirements Fixes Summary

**Two-wave generation orchestration workflow wired into spec.md approval, with Jinja2 Pass 1 -> sequential Wave 1 model-gen -> parallel Wave 2 view/test enrichment pipeline**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T15:48:55Z
- **Completed:** 2026-03-02T15:51:46Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Created workflows/generate.md with complete two-wave orchestration: Step 1 (render-module CLI), Step 2 (Wave 1 model method bodies, sequential), Step 3 (Wave 2 view enrichment + test generation, parallel), Step 4 (git commit), Step 5 (summary report)
- Added generate.md trigger as Step 3 in spec.md Step 4.3 approval handler, wiring the spec approval gate directly to the generation pipeline
- Fixed REQUIREMENTS.md documentation errors: CODG-09 corrected from `<list>` to `<tree>` with Odoo 18+ note; CODG-10 corrected from README.md to README.rst with OCA standard note; CODG-02 annotated with CRUD deferral to Phase 7

## Task Commits

Each task was committed atomically:

1. **Task 1: Create workflows/generate.md with two-wave orchestration** - `7600f9d` (feat)
2. **Task 2: Add generate.md hook to spec.md and fix REQUIREMENTS.md errors** - `9ba229d` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `workflows/generate.md` — Complete two-wave generation orchestration workflow with 5 steps, Wave 1 sequential guard, Task tool spawn prompts for each agent, git commit step, and summary report format
- `workflows/spec.md` — Added Step 3 in approval handler to trigger generate.md after spec commit; renumbered old Step 3 to Step 4; updated Next steps to reflect Phase 5 active
- `.planning/REQUIREMENTS.md` — Fixed CODG-09 (`<tree>` not `<list>`, added Odoo 18+ clarification), CODG-10 (README.rst not README.md, OCA standard note), CODG-02 (HTML comment deferring CRUD overrides to Phase 7 per Decision A)

## Decisions Made

- Wave 1 must be sequential (all odoo-model-gen tasks finish before Wave 2) because odoo-view-gen reads completed model files to generate correct action button names
- generate.md explicitly documents exclusions: no kanban views (Decision F) and no CRUD overrides (Decision A) with reasons pointing to Phase 7
- spec.md trigger for generate.md placed between git commit step and Report step — the spec commit is the contract, generate.md executes that contract

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Minor: The CODG-02 Edit required checking exact line content because the original line was truncated from the plan's description of "matching the spec". Resolved by grepping the file first to confirm exact content before editing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- generate.md is the orchestrator for Phase 5 generation pipeline — agents (odoo-model-gen, odoo-view-gen, odoo-test-gen) will be created in subsequent plans
- spec.md approval flow now automatically triggers full code generation
- REQUIREMENTS.md documentation is corrected and accurate for implementors in later phases

## Self-Check: PASSED

- FOUND: workflows/generate.md
- FOUND: workflows/spec.md (modified)
- FOUND: .planning/REQUIREMENTS.md (modified)
- FOUND: .planning/phases/05-core-code-generation/05-03-SUMMARY.md
- FOUND commit 7600f9d: feat(05-03): create generate.md two-wave orchestration workflow
- FOUND commit 9ba229d: feat(05-03): add generate.md trigger to spec.md and fix REQUIREMENTS.md docs

---
*Phase: 05-core-code-generation*
*Completed: 2026-03-02*
