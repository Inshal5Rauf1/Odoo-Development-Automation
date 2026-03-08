---
phase: 51-semantic-validation
plan: 01
subsystem: validation
tags: [ast, xml-etree, semantic-analysis, difflib, csv, dataclasses]

requires:
  - phase: 48-model-registry
    provides: ModelRegistry for comodel lookups, known_odoo_models.json
provides:
  - semantic_validate() entry point with 10 checks (E1-E6, W1-W4)
  - ValidationIssue and SemanticValidationResult dataclasses
  - print_validation_report() for CLI output
  - Short-circuit logic skipping cross-ref on parse failures
affects: [52-document-templates, 54-pipeline-qol, auto-fix-integration, cli-validate-command]

tech-stack:
  added: []
  patterns: [single-pass-parsing, in-memory-index, short-circuit-validation, frozen-dataclass-issues]

key-files:
  created:
    - python/src/odoo_gen_utils/validation/semantic.py
    - python/tests/test_semantic_validation.py
  modified:
    - python/src/odoo_gen_utils/validation/__init__.py

key-decisions:
  - "ValidationIssue frozen dataclass with code/severity/file/line/message/fixable/suggestion fields"
  - "SemanticValidationResult mutable dataclass with has_errors and has_fixable_errors properties"
  - "Short-circuit: E1/E2 failures prevent cross-ref checks on failed files"
  - "difflib.get_close_matches(cutoff=0.6) for E3 field name suggestions"
  - "View metadata fields (name, model, arch, priority, inherit_id) excluded from E3 field checks"
  - "Inherited fields resolved via known_odoo_models.json for E3 validation"

patterns-established:
  - "Post-render semantic validation pattern: parse once, index, cross-reference"
  - "ValidationIssue with fixable flag + suggestion for auto-fix pipeline"

requirements-completed: [ARCH-03]

duration: 8min
completed: 2026-03-08
---

# Phase 51 Plan 01: Semantic Validation Summary

**10-check semantic validator (E1-E6 errors, W1-W4 warnings) with AST-based Python parsing, xml.etree XML parsing, difflib fuzzy suggestions, and short-circuit logic -- all stdlib, <100ms for typical modules**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-08T08:57:29Z
- **Completed:** 2026-03-08T09:05:29Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments
- All 10 semantic checks implemented: E1 Python syntax, E2 XML well-formedness, E3 field references with fuzzy suggestions, E4 ACL references, E5 XML ID uniqueness, E6 manifest depends completeness, W1 comodel refs, W2 computed depends, W3 group refs, W4 rule domain fields
- Short-circuit logic prevents cascading false positives when E1/E2 fails
- 32 tests covering all checks, inherited fields, dot-notation depends, view metadata exclusion, performance budget
- Validation under 100ms for typical modules (budget was 2s)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for semantic validation** - `5619c26` (test)
2. **Task 1 GREEN: Implement semantic validation with all 10 checks** - `167b0f4` (feat)

_TDD task with RED and GREEN commits._

## Files Created/Modified
- `python/src/odoo_gen_utils/validation/semantic.py` - All 10 checks, ValidationIssue, SemanticValidationResult, semantic_validate(), print_validation_report()
- `python/tests/test_semantic_validation.py` - 32 tests across 12 test classes
- `python/src/odoo_gen_utils/validation/__init__.py` - Added semantic validation exports

## Decisions Made
- ValidationIssue as frozen dataclass (immutable) with fixable flag and suggestion for future auto-fix integration
- SemanticValidationResult as mutable dataclass (accumulated during validation) with @property helpers
- View metadata fields (name, model, arch, priority, inherit_id) explicitly excluded from E3 field reference checking
- Inherited fields from _inherit resolved via known_odoo_models.json lookup (e.g., mail.thread -> message_ids)
- _KNOWN_GROUPS frozenset for W3 common Odoo security groups
- Regex-based domain field extraction for W4 rule domain validation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- semantic_validate() ready for CLI integration (--skip-validation flag in future plan)
- ValidationIssue.fixable flag ready for auto_fix.py integration
- print_validation_report() ready for CLI output
- Full regression suite passes (1426 existing + 32 new tests)

---
*Phase: 51-semantic-validation*
*Completed: 2026-03-08*
