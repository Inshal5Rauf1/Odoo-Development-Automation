---
phase: 52-document-management
plan: 01
subsystem: domain
tags: [preprocessor, document-management, binary-attachment, verification-workflow, version-tracking, security-roles]

requires:
  - phase: 50-academic-calendar
    provides: "GENERATION preprocessor pattern (model dict building + spec append)"
  - phase: 45-preprocessor-split
    provides: "Decorator-based preprocessor registry with auto-discovery"
provides:
  - "document_management.py preprocessor generating document.type + document.document models"
  - "Verification workflow (pending/verified/rejected) with action methods"
  - "Linked-list version tracking on document.document"
  - "File validation constraint (max_file_size + allowed_mime_types)"
  - "Security role injection (viewer/uploader/verifier/manager hierarchy)"
  - "Configurable via document_config (enable_versioning, enable_verification, default_types)"
affects: [52-document-management, templates, renderer]

tech-stack:
  added: []
  patterns: ["doc_* constraint type prefix for document management actions", "conditional model field generation via config flags"]

key-files:
  created:
    - "python/src/odoo_gen_utils/preprocessors/document_management.py"
    - "python/tests/test_document_management.py"
  modified:
    - "python/tests/test_preprocessor_registry.py"

key-decisions:
  - "doc_action_* types for action methods (verify/reject/reset/upload_new_version) -- same prefix pattern as ac_action_*"
  - "doc_file_validation type for @api.constrains file validation -- checks max_file_size and allowed_mime_types"
  - "Conditional field generation via enable_versioning/enable_verification config flags"
  - "Security role xml_ids use module_name prefix: group_{module_name}_viewer etc."
  - "implied_ids stored as xml_id strings (not role names) for consistency with audit.py pattern"

patterns-established:
  - "doc_* constraint type prefix: doc_file_validation, doc_action_verify, doc_action_reject, doc_action_reset, doc_action_upload_new_version"
  - "Conditional model features via config dict flags (enable_versioning, enable_verification)"
  - "has_document_verification / has_document_versioning context keys on model dict for template rendering"

requirements-completed: [DOMN-01]

duration: 10min
completed: 2026-03-08
---

# Phase 52 Plan 01: Document Management Preprocessor Summary

**TDD document.type + document.document preprocessor with verification workflow, linked-list versioning, file validation constraint, and configurable security roles at order=28**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-08T10:26:28Z
- **Completed:** 2026-03-08T10:36:44Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments
- Document management preprocessor generating document.type (classification lookup) and document.document (files with attachment=True) when `document_management: true`
- Verification workflow with 3 states (pending/verified/rejected) and action methods (verify, reject, reset_to_pending)
- Linked-list version tracking (version, previous_version_id, is_latest) with action_upload_new_version
- File validation constraint checking max_file_size and allowed_mime_types from document_type_id
- Security role injection: viewer/uploader/verifier/manager with implied_ids hierarchy
- Configurable via document_config: enable_versioning, enable_verification, default_types
- 84 unit tests covering all features, config options, immutability, and edge cases

## Task Commits

Each task was committed atomically:

1. **TDD RED: Failing tests** - `fdc77e4` (test)
2. **TDD GREEN: Implementation** - `5ae5380` (feat)

_TDD cycle: RED (84 tests fail) -> GREEN (84 tests pass). No REFACTOR needed -- code clean on first pass._

## Files Created/Modified
- `python/src/odoo_gen_utils/preprocessors/document_management.py` - Preprocessor (475 lines): builds document.type + document.document model dicts, injects security roles, mail dependency
- `python/tests/test_document_management.py` - Tests (900 lines): 84 unit tests covering registration, models, fields, constraints, actions, roles, config, immutability
- `python/tests/test_preprocessor_registry.py` - Updated registry count from 13 to 14, added order=28 to pipeline sequence

## Decisions Made
- doc_action_* types for action methods -- consistent with ac_action_* prefix from Phase 50
- doc_file_validation type for @api.constrains file validation
- Conditional field generation via enable_versioning/enable_verification config flags
- Security role xml_ids use module_name prefix (group_{module_name}_viewer)
- implied_ids stored as xml_id strings for consistency with audit.py pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated preprocessor registry tests for 14th preprocessor**
- **Found during:** GREEN phase verification
- **Issue:** test_preprocessor_registry.py expected 13 preprocessors and order sequence without 28
- **Fix:** Updated count to 14, added order=28 to expected pipeline, updated auto-discovery count
- **Files modified:** python/tests/test_preprocessor_registry.py
- **Verification:** All 1484 non-Docker tests pass
- **Committed in:** 5ae5380 (GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking)
**Impact on plan:** Necessary registry test update. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Preprocessor generates complete model dicts for document.type and document.document
- Template rendering (52-02) can use has_document_verification and has_document_versioning context keys
- doc_* constraint types need template branches in model.py.j2 for rendering
- VERSION_GATES for discuss.channel rename is template-scope work (52-02)

---
*Phase: 52-document-management*
*Completed: 2026-03-08*
