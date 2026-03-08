---
phase: 56-logic-writer-core
plan: 02
subsystem: code-generation
tags: [classifier, stub-report, json, cli-integration, agent-prompt, logic-writer]

# Dependency graph
requires:
  - phase: 56-logic-writer-core-01
    provides: StubDetector (detect_stubs) and ContextBuilder (build_stub_context) with StubInfo/StubContext dataclasses
provides:
  - Deterministic complexity classifier (classify_complexity) routing stubs to budget/quality
  - JSON stub report generator (.odoo-gen-stubs.json) matching locked schema
  - CLI generate command integration printing stub summary after Jinja render
  - Agent prompt (agents/odoo-logic-writer.md) for Claude Code to fill stubs
affects: [57-logic-writer-computed, 58-logic-writer-overrides, odoo-gsd-orchestrator]

# Tech tracking
tech-stack:
  added: []
  patterns: [deterministic-classification, json-sidecar-report, non-blocking-cli-hook, agent-prompt-contract]

key-files:
  created:
    - python/src/odoo_gen_utils/logic_writer/classifier.py
    - python/src/odoo_gen_utils/logic_writer/report.py
    - python/tests/test_classifier.py
    - python/tests/test_stub_report.py
    - agents/odoo-logic-writer.md
  modified:
    - python/src/odoo_gen_utils/logic_writer/__init__.py
    - python/src/odoo_gen_utils/cli.py

key-decisions:
  - "Cross-model depends detection checks for dots only INSIDE @api.depends argument strings, not in api.depends itself"
  - "CLI uses separate ModelRegistry instance for stub report (option b) -- self-contained, no dependency on registry block further down"
  - "Agent prompt is pure markdown (141 lines) covering ORM rules, method patterns, complexity routing, and validation workflow"

patterns-established:
  - "Deterministic classification: priority-ordered rules with early return, no ML/LLM involvement"
  - "Non-blocking CLI hook: try/except wrapper ensures stub report failure never blocks module generation"
  - "Agent prompt contract: .odoo-gen-stubs.json is the machine-readable interface between belt and LLM layer"

requirements-completed: [LGEN-02]

# Metrics
duration: 9min
completed: 2026-03-08
---

# Phase 56 Plan 02: Classifier + Report + CLI + Agent Prompt Summary

**Deterministic budget/quality classifier with 6 rules, JSON stub report matching locked schema, CLI integration after Jinja render, and 141-line agent prompt for Claude Code stub implementation**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-08T16:14:32Z
- **Completed:** 2026-03-08T16:23:54Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Classifier implements all 6 deterministic complexity rules from CONTEXT.md (cross-model depends, multiple targets, conditional rules, create/write, action_/cron_, default budget)
- Report writer orchestrates detect_stubs -> build_stub_context -> classify_complexity pipeline and writes .odoo-gen-stubs.json with _meta header and per-stub entries
- CLI generate command prints stub summary after Jinja render (non-blocking try/except)
- Agent prompt covers workflow, ORM rules, 5 method patterns, complexity routing, validation instructions
- 38 new tests (20 classifier + 18 report) all passing, 74 total Phase 56 tests passing

## Task Commits

Each task was committed atomically (TDD RED then GREEN for Task 1):

1. **Task 1: Classifier + Report modules** - `bd820eb` (test: failing tests) then `b82dd53` (feat: implementation)
2. **Task 2: CLI integration + Agent prompt** - `2ef8805` (feat: CLI hook + agent prompt)

_TDD Task 1 has two commits (RED test then GREEN implementation)_

## Files Created/Modified
- `python/src/odoo_gen_utils/logic_writer/classifier.py` - Deterministic complexity routing with 6 priority-ordered rules (90 lines)
- `python/src/odoo_gen_utils/logic_writer/report.py` - JSON stub report generator orchestrating full pipeline (146 lines)
- `python/src/odoo_gen_utils/logic_writer/__init__.py` - Updated to export classify_complexity, generate_stub_report, StubReport
- `python/src/odoo_gen_utils/cli.py` - Stub report generation after Jinja render, non-blocking
- `python/tests/test_classifier.py` - 20 tests covering all 6 rules + priority/edge cases (213 lines)
- `python/tests/test_stub_report.py` - 18 tests covering schema, id format, empty module, integration (436 lines)
- `agents/odoo-logic-writer.md` - Agent prompt for Claude Code (141 lines)

## Decisions Made
- Cross-model depends detection parses the argument portion after `(` in the decorator to avoid false positives from `api.depends` itself containing a dot
- CLI uses a separate ModelRegistry instance (option b from plan) for stub report, keeping it self-contained without depending on the registry init block further down in the generate command
- Agent prompt written as pure markdown (not Python) -- editable, versionable, no redeployment needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed cross-model depends detection false positive**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** Initial implementation checked for "." anywhere in decorator string, but `@api.depends("amount")` contains a dot in `api.depends` itself, causing all depends decorators to match
- **Fix:** Changed to extract argument portion after opening paren, then check for dots only in the argument strings
- **Files modified:** `python/src/odoo_gen_utils/logic_writer/classifier.py`
- **Verification:** All 20 classifier tests pass including the edge case test
- **Committed in:** `b82dd53` (part of GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential correctness fix caught by TDD. No scope creep.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Full logic_writer pipeline complete: detect -> context -> classify -> report -> CLI output
- Running `odoo-gen generate` now produces `.odoo-gen-stubs.json` alongside module files
- Agent prompt at `agents/odoo-logic-writer.md` ready for Claude Code / odoo-gsd to consume
- Phase 57 (computed chains) and Phase 58 (overrides) can build on this foundation
- No blockers or concerns

---
*Phase: 56-logic-writer-core*
*Completed: 2026-03-08*

## Self-Check: PASSED

- All 7 created/modified files exist on disk
- All 3 commits (bd820eb, b82dd53, 2ef8805) verified in git log
- 74 Phase 56 tests pass (36 Plan 01 + 38 Plan 02)
- 1686 non-Docker tests pass across full test suite
