---
phase: 56-logic-writer-core
plan: 01
subsystem: code-generation
tags: [ast, stub-detection, context-assembly, dataclass, logic-writer]

# Dependency graph
requires:
  - phase: 55-cleanup
    provides: Clean codebase with no deprecated modules
provides:
  - StubDetector module with AST-based stub pattern detection
  - ContextBuilder module with spec + registry context assembly
  - StubInfo and StubContext frozen dataclasses
  - logic_writer package with public API (detect_stubs, build_stub_context)
affects: [56-02-classifier-report, 57-logic-writer-computed, 58-logic-writer-overrides]

# Tech tracking
tech-stack:
  added: []
  patterns: [ast-based-stub-detection, spec-context-aggregation, leaf-module-pattern]

key-files:
  created:
    - python/src/odoo_gen_utils/logic_writer/__init__.py
    - python/src/odoo_gen_utils/logic_writer/stub_detector.py
    - python/src/odoo_gen_utils/logic_writer/context_builder.py
    - python/tests/test_stub_detector.py
    - python/tests/test_context_builder.py
  modified: []

key-decisions:
  - "Frozen dataclasses for StubInfo and StubContext (matches project convention, zero new deps)"
  - "Leaf module pattern: logic_writer imports only from stdlib + registry, never from renderer or validation"
  - "Multi-field compute stubs detected via for-loop body analysis (all Assign nodes must be constant attr assigns)"
  - "Business rules aggregated from 6 spec locations: description, help, complex_constraints, workflow_states, approval_levels, depends"
  - "Registry source tracking: 'registry' for registered modules, 'known_models' for standard Odoo models, None when not found"

patterns-established:
  - "AST stub detection: _is_stub_body() filters docstrings, then checks for pass/for-pass/for-constant-assign patterns"
  - "Context aggregation: build_stub_context() assembles model_fields, related_fields, business_rules from spec + registry"
  - "Graceful degradation: registry=None returns empty related_fields, model not in spec returns empty context"

requirements-completed: [LGEN-01]

# Metrics
duration: 12min
completed: 2026-03-08
---

# Phase 56 Plan 01: StubDetector + ContextBuilder Summary

**AST-based stub detection identifying compute/constraint/action patterns, and per-stub context assembly from spec + ModelRegistry with business rule aggregation**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-08T15:58:21Z
- **Completed:** 2026-03-08T16:10:59Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- StubDetector scans .py files recursively, identifies 3 stub patterns (compute, constraint, action/cron), handles SyntaxError gracefully, and ignores real implementations
- ContextBuilder assembles model_fields, related_fields (from registry or known_models), and business_rules aggregated from 6 spec locations
- 36 tests covering all behaviors: stub patterns, docstrings, decorator extraction, target field extraction, recursive scanning, context assembly, registry lookups, wizard stubs, graceful degradation
- Zero new dependencies -- all stdlib + existing project code

## Task Commits

Each task was committed atomically (TDD RED then GREEN):

1. **Task 1: StubDetector module** - `b6c31b7` (test: failing tests) then `644b4c2` (feat: implementation)
2. **Task 2: ContextBuilder module** - `5e0efae` (test: failing tests) then `9ef00d6` (feat: implementation)

_TDD tasks have two commits each (RED test then GREEN implementation)_

## Files Created/Modified
- `python/src/odoo_gen_utils/logic_writer/__init__.py` - Package public API exporting detect_stubs, StubInfo, build_stub_context, StubContext
- `python/src/odoo_gen_utils/logic_writer/stub_detector.py` - AST-based stub detection (234 lines): StubInfo dataclass, detect_stubs(), _is_stub_body(), helpers
- `python/src/odoo_gen_utils/logic_writer/context_builder.py` - Per-stub context assembly (248 lines): StubContext dataclass, build_stub_context(), field/rule helpers
- `python/tests/test_stub_detector.py` - 19 tests for stub detection (505 lines)
- `python/tests/test_context_builder.py` - 17 tests for context assembly (457 lines)

## Decisions Made
- Used frozen dataclasses (not Pydantic) for StubInfo and StubContext -- matches project convention, zero new imports
- Made logic_writer a leaf module: imports only from stdlib + registry module, avoiding circular deps with renderer/validation
- Multi-field compute stubs (for rec in self: rec.x = 0; rec.y = 0) detected by checking all for-body statements are constant attr assigns
- Business rules aggregated from 6 spec locations (description, help, complex_constraints, workflow_states, approval_levels, depends)
- Registry source tracked as "registry" / "known_models" / None to inform LLM about data provenance

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- StubDetector and ContextBuilder ready for Plan 02 consumption (classifier + report + CLI integration)
- Plan 02 will import detect_stubs() and build_stub_context() to build the full stub report pipeline
- No blockers or concerns

---
*Phase: 56-logic-writer-core*
*Completed: 2026-03-08*

## Self-Check: PASSED

- All 5 created files exist on disk
- All 4 commits (b6c31b7, 644b4c2, 5e0efae, 9ef00d6) verified in git log
- 36 tests pass (19 stub_detector + 17 context_builder)
