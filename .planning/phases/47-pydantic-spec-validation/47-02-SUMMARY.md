---
phase: 47-pydantic-spec-validation
plan: 02
subsystem: architecture
tags: [pydantic, validation, renderer, cli, json-schema, integration]

requires:
  - phase: 47-pydantic-spec-validation
    provides: spec_schema.py with validate_spec(), format_validation_errors(), ModuleSpec
provides:
  - validate_spec() wired into render_module() pipeline before cycle check and preprocessors
  - export-schema CLI command for JSON Schema output (stdout or file)
  - CLI error handling for PydanticValidationError with formatted output
  - Integration tests confirming validation rejects invalid specs in render_module()
affects: [preprocessors, templates, future-spec-tooling]

tech-stack:
  added: []
  patterns: [lazy imports in cli.py for pydantic, model_dump() dict conversion at pipeline boundary]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/cli.py
    - python/src/odoo_gen_utils/spec_schema.py
    - python/src/odoo_gen_utils/preprocessors/security.py
    - python/tests/test_spec_schema.py

key-decisions:
  - "Lazy imports for pydantic in cli.py to preserve the existing import guard test pattern"
  - "ApprovalLevelSpec.name made optional (default='') to support both name-based and state-based approval level specs"
  - "security preprocessor record_rules check updated to handle None values from model_dump()"

patterns-established:
  - "validate_spec() runs first in render_module() pipeline, before _validate_no_cycles() and run_preprocessors()"
  - "model_dump() converts ModuleSpec back to dict at pipeline boundary; preprocessors continue receiving dicts"
  - "CLI catches PydanticValidationError with formatted error output to stderr"

requirements-completed: [ARCH-01]

duration: 11min
completed: 2026-03-08
---

# Phase 47 Plan 02: Renderer Integration and CLI Export-Schema Summary

**Wired Pydantic validation into render_module() pipeline with export-schema CLI command and 5 integration tests**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-07T23:40:37Z
- **Completed:** 2026-03-07T23:52:32Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- validate_spec() runs as the first step in render_module() before _validate_no_cycles() and run_preprocessors(), with model_dump() converting back to dict for the pipeline
- export-schema CLI command outputs valid JSON Schema to stdout or file, enabling IDE autocomplete for spec files
- render-module CLI catches PydanticValidationError with formatted error output to stderr
- 5 new integration tests: export-schema stdout, $defs structure, file output, invalid spec rejection, valid spec pass-through
- Full regression: 1215 passed, 0 new failures (9 pre-existing, 40 skipped)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire validate_spec() into renderer.py render_module()** - `2abd012` (feat)
2. **Task 2: Add export-schema CLI command and integration tests** - `951c8f3` (feat)
3. **Task 3: Full regression test suite** - `0ac3694` (fix)

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer.py` - Added validate_spec() import and call at top of render_module(), model_dump() conversion
- `python/src/odoo_gen_utils/cli.py` - Added export-schema command, PydanticValidationError catch in render_module_cmd (lazy imports)
- `python/src/odoo_gen_utils/spec_schema.py` - Made ApprovalLevelSpec.name optional for backward compatibility
- `python/src/odoo_gen_utils/preprocessors/security.py` - Fixed record_rules None check for model_dump() compatibility
- `python/tests/test_spec_schema.py` - Added 5 integration tests (TestExportSchema, TestExportSchemaFile, TestRendererIntegration)

## Decisions Made
- Used lazy imports for pydantic in cli.py to comply with the existing import guard test that enforces minimal top-level imports
- Made ApprovalLevelSpec.name optional (default='') because existing test specs use state-based approval levels without a name field
- Fixed security preprocessor to use model.get("record_rules") instead of "record_rules" in model, since model_dump() includes keys with None values

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed record_rules None iteration in security preprocessor**
- **Found during:** Task 1 (wire validate_spec into renderer)
- **Issue:** model_dump() includes record_rules=None as an explicit key; security preprocessor's _security_detect_record_rule_scopes did `list(model["record_rules"])` which fails on None
- **Fix:** Changed `if "record_rules" in model` to `if model.get("record_rules") is not None`
- **Files modified:** python/src/odoo_gen_utils/preprocessors/security.py
- **Verification:** All 400 renderer tests pass
- **Committed in:** 2abd012 (Task 1 commit)

**2. [Rule 1 - Bug] Made ApprovalLevelSpec.name optional**
- **Found during:** Task 1 (wire validate_spec into renderer)
- **Issue:** ApprovalLevelSpec required name field, but existing test specs (TestNotificationIntegration) use state-based levels without name
- **Fix:** Changed `name: str` to `name: str = ""` in ApprovalLevelSpec
- **Files modified:** python/src/odoo_gen_utils/spec_schema.py
- **Verification:** All 400 renderer tests pass
- **Committed in:** 2abd012 (Task 1 commit)

**3. [Rule 1 - Bug] Moved pydantic import to lazy (inline) in CLI**
- **Found during:** Task 3 (full regression)
- **Issue:** Top-level `from pydantic import ValidationError` in cli.py violated the lazy import guard test
- **Fix:** Moved pydantic and spec_schema imports inside render_module_cmd function body
- **Files modified:** python/src/odoo_gen_utils/cli.py
- **Verification:** test_cli_lazy_imports passes, full suite 1215 passed
- **Committed in:** 0ac3694 (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (3 bug fixes)
**Impact on plan:** All auto-fixes necessary for correctness and backward compatibility. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 47 (Pydantic Spec Validation) is fully complete
- ARCH-01 requirement satisfied: spec validation integrated into pipeline
- JSON Schema export available for IDE autocomplete workflows
- Ready for Phase 48 and beyond

## Self-Check: PASSED

- All 5 modified files exist on disk
- All 3 commits (2abd012, 951c8f3, 0ac3694) verified in git log
- 27 tests passing in test_spec_schema.py (22 unit + 5 integration)
- 1215 total tests passing (0 new failures, 9 pre-existing)
- export-schema outputs valid JSON Schema

---
*Phase: 47-pydantic-spec-validation*
*Completed: 2026-03-08*
