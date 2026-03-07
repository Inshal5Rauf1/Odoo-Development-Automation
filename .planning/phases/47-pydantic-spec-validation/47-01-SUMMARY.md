---
phase: 47-pydantic-spec-validation
plan: 01
subsystem: architecture
tags: [pydantic, validation, schema, odoo-spec, tdd]

requires:
  - phase: 46-test-infrastructure
    provides: test infrastructure with import guards and conftest fixtures
provides:
  - ModuleSpec Pydantic v2 model hierarchy for spec validation
  - validate_spec() entry point that returns validated ModuleSpec or raises
  - format_validation_errors() for human-readable validation output
  - VALID_FIELD_TYPES frozenset of 16 Odoo field types
  - Cross-reference validators for approval roles and audit_exclude
affects: [47-02 renderer-integration, preprocessors, cli]

tech-stack:
  added: [pydantic>=2.10,<3.0]
  patterns: [ConfigDict(extra='allow', protected_namespaces=()), model_validator cross-ref checks, field_validator type whitelist]

key-files:
  created:
    - python/src/odoo_gen_utils/spec_schema.py
    - python/tests/test_spec_schema.py
  modified:
    - python/pyproject.toml

key-decisions:
  - "Used 16 valid field types (excluding Reference which is rare in Odoo 17)"
  - "Cross-reference validators check per-model security.roles (not module-level) for approval role validation"
  - "validate_spec() prints formatted errors then re-raises ValidationError (hard fail)"

patterns-established:
  - "All Pydantic models use ConfigDict(extra='allow', protected_namespaces=()) for backward compatibility"
  - "validate_spec() -> ModuleSpec is the single validation entry point"
  - "format_validation_errors() produces indented output with field paths, messages, and input values"

requirements-completed: [ARCH-01]

duration: 4min
completed: 2026-03-08
---

# Phase 47 Plan 01: Pydantic Spec Schema Summary

**Pydantic v2 spec schema with 10 typed models, field type validator, cross-reference checks, and 22 TDD tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-07T23:33:19Z
- **Completed:** 2026-03-07T23:37:20Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments
- Created spec_schema.py (~318 lines) with complete Pydantic v2 model hierarchy: ModuleSpec > ModelSpec > FieldSpec + 7 supporting specs
- All models use ConfigDict(extra='allow', protected_namespaces=()) for backward compatibility with unknown keys and Odoo's model_ prefixed fields
- validate_spec() entry point with hard fail behavior (prints formatted errors, re-raises ValidationError)
- Cross-reference validators catch approval roles not in security.roles and audit_exclude fields not in model fields
- Both spec_v1.json and spec_v2.json fixtures validate without modification
- 22 unit tests across 7 test classes, all passing

## Task Commits

Each task was committed atomically (TDD):

1. **Task 1 RED: Failing tests** - `01ab22f` (test)
2. **Task 1 GREEN: Implementation** - `d73d51a` (feat)

_TDD task with RED (failing tests) and GREEN (passing implementation) commits._

## Files Created/Modified
- `python/src/odoo_gen_utils/spec_schema.py` - All Pydantic v2 models, validate_spec(), format_validation_errors(), VALID_FIELD_TYPES
- `python/tests/test_spec_schema.py` - 22 unit tests across 7 test classes (TestValidateSpec, TestFieldTypeValidation, TestExtraAllow, TestCrossRefValidators, TestFormatErrors, TestFixtureCompat, TestSubModels)
- `python/pyproject.toml` - Added pydantic>=2.10,<3.0 to core dependencies

## Decisions Made
- Used 16 valid field types (Char, Text, Html, Integer, Float, Monetary, Boolean, Date, Datetime, Binary, Selection, Many2one, One2many, Many2many, Many2oneReference, Json) -- excluded Reference which is rare in Odoo 17
- Cross-reference validators check per-model security.roles (not module-level security) for approval role validation, matching the fixture data structure where security is per-model
- validate_spec() prints formatted errors then re-raises the original ValidationError for caller handling

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- spec_schema.py is ready for Plan 02 (renderer integration and CLI export-schema)
- validate_spec() can be wired into render_module() before preprocessors
- ModuleSpec.model_json_schema() ready for export-schema CLI command

## Self-Check: PASSED

- All 3 files exist on disk
- Both commits (01ab22f, d73d51a) verified in git log
- 22 tests passing in test_spec_schema.py
- 1147 existing tests still passing (30 skipped, Docker-only failures pre-existing)

---
*Phase: 47-pydantic-spec-validation*
*Completed: 2026-03-08*
