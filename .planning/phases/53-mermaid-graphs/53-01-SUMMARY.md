---
phase: 53-mermaid-graphs
plan: 01
subsystem: tooling
tags: [mermaid, diagrams, dag, er-diagram, visualization]

# Dependency graph
requires:
  - phase: 48-model-registry
    provides: "ModelEntry, ModelRegistry, _models, _dependency_graph, list_modules()"
provides:
  - "mermaid.py module with generate_dependency_dag, generate_er_diagram, generate_module_diagrams, generate_project_diagrams"
  - "_mermaid_id() sanitizer, _is_key_field() filter, _is_external_module() detector"
  - "58 tests covering all diagram generation behaviors"
affects: [53-02 CLI integration, render_module_cmd auto-generation hook]

# Tech tracking
tech-stack:
  added: []  # Pure stdlib: re, pathlib, typing
  patterns: [pure-function-module, string-generation, field-filtering-heuristic]

key-files:
  created:
    - python/src/odoo_gen_utils/mermaid.py
    - python/tests/test_mermaid.py
  modified: []

key-decisions:
  - "Access registry private attributes directly (_models, _dependency_graph) -- internal module within same package, follows existing cli.py pattern"
  - "Use graph TD (not flowchart TD) per user specification in CONTEXT.md"
  - "Module is 408 lines (exceeds 300 guidance) due to comprehensive docstrings and type annotations -- well under 800 project max"

patterns-established:
  - "Pure function diagram module: stateless functions accepting registry data, returning strings"
  - "Field filtering heuristic: frozenset exclusion lists + inclusion rules for name/state/Selection/Monetary/stored-computed"
  - "Cross-module detection: compare comodel's module against current module from registry lookup"

requirements-completed: [TOOL-01]

# Metrics
duration: 8min
completed: 2026-03-08
---

# Phase 53 Plan 01: Mermaid Graphs Summary

**Pure-function mermaid.py module generating dependency DAG (graph TD) and ER diagrams (erDiagram) from ModelRegistry data with cross-module dotted-line differentiation and field-filtering heuristics**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-08T11:55:20Z
- **Completed:** 2026-03-08T12:03:20Z
- **Tasks:** 1 (TDD feature with RED + GREEN commits)
- **Files modified:** 2

## Accomplishments
- Created mermaid.py with 4 public functions + 3 helpers for Mermaid diagram generation
- Comprehensive test suite with 58 tests covering all behaviors from the plan
- Field filtering heuristic correctly includes name/state/Selection/Monetary/stored-computed and excludes technical/Binary/Text/Html/non-stored-computed
- Cross-module ER references use dotted lines, same-module use solid lines
- File-writing functions create .mmd files in correct directories with trailing newlines

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `2030060` (test)
2. **Task 1 GREEN: Implementation** - `350c0c1` (feat)

_TDD flow: RED (58 failing tests) -> GREEN (58 passing tests)_

## Files Created/Modified
- `python/src/odoo_gen_utils/mermaid.py` - Pure functions for Mermaid diagram generation (4 public + 3 helpers, 408 lines)
- `python/tests/test_mermaid.py` - Comprehensive test suite (58 tests across 9 test classes, 847 lines)

## Decisions Made
- Access registry private attributes directly (_models, _dependency_graph) -- matches existing cli.py pattern, avoids adding public accessors for a single consumer
- Use `graph TD` (not `flowchart TD`) per user specification in CONTEXT.md examples
- Module at 408 lines exceeds the 300-line guidance due to comprehensive docstrings, type annotations, and inline documentation -- well under the 800-line project maximum

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- mermaid.py ready for CLI wiring in Plan 02 (mermaid command + auto-generation hook)
- All 4 public functions tested and working: generate_dependency_dag, generate_er_diagram, generate_module_diagrams, generate_project_diagrams
- No blockers for Plan 02

## Self-Check: PASSED

- [x] mermaid.py exists at python/src/odoo_gen_utils/mermaid.py
- [x] test_mermaid.py exists at python/tests/test_mermaid.py
- [x] SUMMARY.md exists at .planning/phases/53-mermaid-graphs/53-01-SUMMARY.md
- [x] Commit 2030060 exists (RED)
- [x] Commit 350c0c1 exists (GREEN)
- [x] 58 tests passing, 0 regressions

---
*Phase: 53-mermaid-graphs*
*Completed: 2026-03-08*
