---
phase: 53-mermaid-graphs
plan: 02
subsystem: tooling
tags: [mermaid, cli, diagrams, auto-generation, click]

# Dependency graph
requires:
  - phase: 53-mermaid-graphs
    plan: 01
    provides: "mermaid.py module with generate_dependency_dag, generate_er_diagram, generate_module_diagrams, generate_project_diagrams"
  - phase: 48-model-registry
    provides: "ModelRegistry with _models, _dependency_graph, list_modules()"
provides:
  - "CLI mermaid command with --module/--project/--type/--stdout flags"
  - "Auto-generation hook in render_module_cmd firing after successful render + validation"
  - "12 new integration tests (7 CLI + 2 edge cases + 3 auto-generation)"
affects: [render-module pipeline, module docs/ output]

# Tech tracking
tech-stack:
  added: []  # No new dependencies -- uses existing click + mermaid.py
  patterns: [cli-mermaid-command, post-render-auto-generation-hook]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/cli.py
    - python/tests/test_mermaid.py
    - python/tests/test_cli_lazy_imports.py

key-decisions:
  - "Mermaid command writes to <cwd>/<module>/docs/ for module-level, .planning/diagrams/ for project-level"
  - "Auto-generation hook placed inside registry try/except after reg.save(), with own inner try/except for best-effort"
  - "Auto-generation gated on not skip_validation since mermaid relies on post-validation state"

patterns-established:
  - "CLI mermaid command: --module XOR --project validation, --type defaults to all, --stdout for console output"
  - "Best-effort post-render hooks: inner try/except inside registry block, silent failure"

requirements-completed: [TOOL-01]

# Metrics
duration: 10min
completed: 2026-03-08
---

# Phase 53 Plan 02: CLI Mermaid Command + Auto-Generation Hook Summary

**CLI `odoo-gen mermaid` command with --module/--project/--type/--stdout flags and best-effort auto-generation hook in render_module_cmd after successful render + validation**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-08T12:07:10Z
- **Completed:** 2026-03-08T12:17:17Z
- **Tasks:** 2 (both TDD with RED + GREEN commits)
- **Files modified:** 3

## Accomplishments
- Added `odoo-gen mermaid` CLI command supporting --module, --project, --type (deps/er/all), --stdout flags
- Wired auto-generation hook into render_module_cmd that creates docs/*.mmd after successful render + validation + registry update
- Auto-generation is best-effort (does not block render on mermaid failure) and skips when --skip-validation is set
- 12 new integration tests covering all flag combinations, edge cases, and auto-generation behavior
- Updated lazy import tests to verify mermaid module is not imported at top level

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for CLI mermaid command** - `bbab5e1` (test)
2. **Task 1 GREEN: CLI mermaid command implementation** - `13c8be6` (feat)
3. **Task 2 GREEN: Auto-generation hook in render_module_cmd** - `1eafcd4` (feat)

_TDD flow: Task 1 RED (failing CLI tests) -> Task 1 GREEN (mermaid command) -> Task 2 GREEN (auto-gen hook, tests from Task 1 RED)_

## Files Created/Modified
- `python/src/odoo_gen_utils/cli.py` - Added @main.command("mermaid") with 4 options + auto-generation hook in render_module_cmd (~173 new lines)
- `python/tests/test_mermaid.py` - Added TestMermaidCli (7 tests), TestMermaidCliEdgeCases (2 tests), TestAutoGeneration (3 tests)
- `python/tests/test_cli_lazy_imports.py` - Added "mermaid" to expected commands and "odoo_gen_utils.mermaid" to forbidden top-level imports

## Decisions Made
- Module-level diagrams write to `<cwd>/<module>/docs/` (consistent with render-module output structure)
- Project-level diagrams write to `.planning/diagrams/` (GSD convention for planning artifacts)
- Auto-generation hook gated on `not skip_validation` since mermaid relies on registry state from post-validation
- Auto-generation placed inside registry try/except (after reg.save()) with its own inner try/except so registry failure doesn't prevent mermaid, and mermaid failure doesn't affect registry
- For --stdout with --project, diagram content is generated inline rather than via generate_project_diagrams (which writes files)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 53 (Mermaid Graphs) is fully complete -- both Plan 01 (mermaid.py core) and Plan 02 (CLI + auto-gen) delivered
- TOOL-01 requirement complete end-to-end: CLI command + auto-generation after render
- Ready for Phase 54 (pipeline QoL)

## Self-Check: PASSED

- [x] cli.py contains @main.command("mermaid")
- [x] cli.py contains generate_module_diagrams auto-generation hook in render_module_cmd
- [x] test_mermaid.py contains TestMermaidCli, TestMermaidCliEdgeCases, TestAutoGeneration
- [x] test_cli_lazy_imports.py includes "mermaid" in expected commands
- [x] Commit bbab5e1 exists (RED)
- [x] Commit 13c8be6 exists (GREEN Task 1)
- [x] Commit 1eafcd4 exists (GREEN Task 2)
- [x] 70 tests passing in test_mermaid.py, 4 in test_cli_lazy_imports.py

---
*Phase: 53-mermaid-graphs*
*Completed: 2026-03-08*
