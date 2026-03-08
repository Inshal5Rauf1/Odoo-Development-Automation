---
phase: 58-logic-writer-overrides-actions
plan: 01
subsystem: logic-writer
tags: [jinja2, ast, stub-detection, action-context, cron-context, stub-zones]

# Dependency graph
requires:
  - phase: 56-logic-writer-core
    provides: StubInfo/StubContext dataclasses, detect_stubs, build_stub_context, report pipeline
  - phase: 57-logic-writer-computed-constraints
    provides: method_type classification, computation_hint, constraint_type, error_messages enrichment
provides:
  - BUSINESS LOGIC START/END markers in Jinja model template (create/write)
  - _find_stub_zones() for marker-aware zone detection
  - action_context enrichment with full_state_machine, side_effects, preconditions
  - cron_context enrichment with domain_hint, processing_pattern, batch_size_hint
  - stub_zone and exclusion_zones for override method stubs
  - Conditional serialization of new fields in JSON report
affects: [58-02-semantic-validation, logic-writer-agent-prompt]

# Tech tracking
tech-stack:
  added: []
  patterns: [marker-based-zone-detection, keyword-based-pattern-classification, conditional-field-serialization]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/templates/17.0/model.py.j2
    - python/src/odoo_gen_utils/logic_writer/stub_detector.py
    - python/src/odoo_gen_utils/logic_writer/context_builder.py
    - python/src/odoo_gen_utils/logic_writer/report.py
    - python/tests/test_stub_detector.py
    - python/tests/test_context_builder.py
    - python/tests/test_stub_report.py

key-decisions:
  - "Marker detection uses exact string match on stripped lines for reliability"
  - "Cron pattern classification priority: generate_records -> cleanup -> aggregate -> batch_per_record (default)"
  - "Action context returns None when no workflow_states in spec (graceful degradation)"
  - "Override stub_zone detection requires explicit module_dir parameter (not always available)"

patterns-established:
  - "BUSINESS LOGIC START/END markers delimit editable zones in template-generated code"
  - "Keyword-based classification for cron processing patterns (4 types)"
  - "Side effect and precondition extraction from business rules via keyword matching"
  - "Optional module_dir parameter for source-file-aware context building"

requirements-completed: [LGEN-05, LGEN-06]

# Metrics
duration: 11min
completed: 2026-03-08
---

# Phase 58 Plan 01: Stub Zone Markers, Action/Cron Context Enrichment Summary

**Jinja template BUSINESS LOGIC markers for create/write stubs, action_context with full state machine, cron_context with domain hints and processing patterns, marker-aware stub zone detection**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-08T18:36:32Z
- **Completed:** 2026-03-08T18:47:59Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Jinja model template now emits BUSINESS LOGIC START/END markers in create (2 zones: pre-super + post-super) and write (1 zone: post-super)
- StubContext enriched with stub_zone, exclusion_zones, action_context, cron_context fields
- action_context extracts full state machine (states, transitions, side_effects, preconditions) from spec
- cron_context classifies processing pattern into 4 types with domain hints and batch configuration
- JSON report conditionally includes all new fields (omits when None/empty)
- 31 new tests added (8 marker zone + 16 context builder + 7 report serialization)

## Task Commits

Each task was committed atomically:

1. **Task 1: Jinja template markers + marker-aware stub detection** - `ed91c37` (test), `0836da2` (feat)
2. **Task 2: StubContext enrichment + report serialization** - `6d8b2db` (test), `ea07688` (feat)

_Note: TDD tasks have two commits each (test -> feat)_

## Files Created/Modified
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Added BUSINESS LOGIC markers in create/write method blocks
- `python/src/odoo_gen_utils/logic_writer/stub_detector.py` - Added _MARKER_START/_MARKER_END constants and _find_stub_zones() function
- `python/src/odoo_gen_utils/logic_writer/context_builder.py` - Added 4 new StubContext fields, _build_action_context, _build_cron_context, _build_stub_zones_for_override
- `python/src/odoo_gen_utils/logic_writer/report.py` - Added conditional serialization of new context fields, pass module_dir to build_stub_context
- `python/tests/test_stub_detector.py` - TestMarkerZones class with 8 tests
- `python/tests/test_context_builder.py` - TestActionContext (6), TestCronContext (8), TestStubZones (2), TestPhase58FieldsDefaults (2)
- `python/tests/test_stub_report.py` - TestActionContextInReport (2), TestCronContextInReport (2), TestStubZoneInReport (2), test fixtures

## Decisions Made
- Marker detection uses exact stripped-line comparison (not regex) for simplicity and reliability
- Cron pattern classification uses priority ordering: generate > cleanup > aggregate > batch_per_record
- Action context returns None (not empty dict) when no workflow_states exist -- consistent with existing omission pattern
- Override stub zone detection requires explicit module_dir (optional parameter) since not all callers have file access
- Side effect/precondition extraction uses keyword frozensets for consistent, extensible matching

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All enrichment infrastructure in place for Plan 02 (E13-E16 semantic validation)
- _find_stub_zones() available for E16 exclusion zone violation detection
- action_context and cron_context available for E14/E15 validation context
- 123 plan-specific tests + 1786 full suite tests all passing

---
*Phase: 58-logic-writer-overrides-actions*
*Completed: 2026-03-08*
