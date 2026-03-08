---
phase: 52-document-management
plan: 02
subsystem: domain
tags: [templates, document-management, version-gates, jinja2, binary-attachment, verification-buttons, discuss-channel]

requires:
  - phase: 52-document-management
    provides: "Document management preprocessor generating model dicts with doc_* constraints"
  - phase: 50-academic-calendar
    provides: "ac_action_* plain method dispatch pattern in model.py.j2"
provides:
  - "Template rendering for all doc_* constraint types (file_validation with @api.constrains, actions as plain methods)"
  - "Generic field branch renders attachment, readonly, tracking, copy, size, model_field kwargs"
  - "Form view verification buttons + statusbar + version history smart button"
  - "VERSION_GATES dict in module context for Odoo 18 discuss.channel gate (DOMN-04)"
  - "Document type seed data XML generation via _render_document_type_xml()"
  - "Security role merge preserving domain preprocessor roles through security preprocessor"
affects: [templates, renderer, security-preprocessor]

tech-stack:
  added: []
  patterns: ["VERSION_GATES dict for cross-version template rendering", "bracket notation for dict.copy() Jinja2 conflict", "security role merge in security preprocessor"]

key-files:
  created: []
  modified:
    - "python/src/odoo_gen_utils/renderer_context.py"
    - "python/src/odoo_gen_utils/renderer.py"
    - "python/src/odoo_gen_utils/templates/17.0/model.py.j2"
    - "python/src/odoo_gen_utils/templates/18.0/model.py.j2"
    - "python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2"
    - "python/src/odoo_gen_utils/templates/18.0/view_form.xml.j2"
    - "python/src/odoo_gen_utils/preprocessors/security.py"
    - "python/tests/test_document_management.py"

key-decisions:
  - "Bracket notation field['copy'] to avoid Jinja2 resolving dict.copy() method instead of key"
  - "document_verification_actions auto-built from doc_action_* complex_constraints in renderer_context"
  - "Security preprocessor merges existing roles instead of overwriting (preserves domain preprocessor roles)"
  - "VERSION_GATES is a static dict in _build_module_context, not preprocessor-level (render-time concern)"
  - "inherit list handling supports both string and list types from preprocessors"

patterns-established:
  - "VERSION_GATES dict: centralized version-conditional mappings for template rendering"
  - "Security role merge: domain preprocessors inject roles, security preprocessor preserves them"
  - "Generic field kwargs: attachment, readonly, tracking, copy, size, model_field in generic branch"

requirements-completed: [DOMN-01, DOMN-04]

duration: 15min
completed: 2026-03-08
---

# Phase 52 Plan 02: Template Rendering + VERSION_GATES Summary

**Extended Jinja2 templates for document management field kwargs, doc_* constraint dispatch, verification view buttons, and VERSION_GATES dict for Odoo 18 discuss.channel compatibility**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-08T10:39:47Z
- **Completed:** 2026-03-08T10:55:04Z
- **Tasks:** 2 (both TDD: RED + GREEN)
- **Files modified:** 8

## Accomplishments
- Templates render all document management field kwargs correctly (attachment=True, readonly=True, tracking=True, copy=False, size=N, model_field="...")
- doc_file_validation constraint dispatches with @api.constrains decorator + _check_ prefix
- doc_action_* constraints dispatch as plain methods (like ac_action_* from Phase 50)
- Form view header renders verification buttons (Verify, Reject, Reset) with visibility conditions and group restrictions
- verification_state statusbar widget and version history smart button rendered for document models
- VERSION_GATES dict injected into module context with 18.0 discuss.channel mappings (DOMN-04)
- Document type seed data XML generated when default_types configured
- 41 new tests (21 template + 20 E2E) all passing, total suite at 1495 tests

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing template tests** - `b1cc014` (test)
2. **Task 1 GREEN: Template + context implementation** - `34ac943` (feat)
3. **Task 2: E2E tests + security role merge** - `f0623c6` (feat)

_TDD cycle: RED (21 tests fail) -> GREEN (1495 tests pass). Task 2 bundled RED+GREEN since E2E tests passed immediately after Task 1._

## Files Created/Modified
- `python/src/odoo_gen_utils/renderer_context.py` - Phase 52 context keys (has_document_verification/versioning, document_verification_actions, VERSION_GATES), inherit list handling fix
- `python/src/odoo_gen_utils/renderer.py` - _render_document_type_xml helper, document_type_data.xml handler in _render_extra_data_files
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Generic field kwargs, doc_file_/doc_action dispatch, UserError import guard
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Same changes as 17.0 template
- `python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2` - Verification buttons, statusbar, version history smart button
- `python/src/odoo_gen_utils/templates/18.0/view_form.xml.j2` - Same changes as 17.0 template
- `python/src/odoo_gen_utils/preprocessors/security.py` - Role merge preserving domain preprocessor roles
- `python/tests/test_document_management.py` - 41 new tests (template rendering + E2E integration)

## Decisions Made
- Used bracket notation `field['copy']` in Jinja2 to avoid dict.copy() method resolution conflict
- Auto-built document_verification_actions from doc_action_* complex_constraints in renderer_context (not preprocessor)
- Fixed security preprocessor to merge existing roles instead of overwriting
- VERSION_GATES is a static dict injected at module context build time (render-time, not preprocessing)
- Handled inherit as both string and list types for models with explicit inherit lists

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] dict.copy() Jinja2 conflict for copy=False field rendering**
- **Found during:** Task 1 (generic field branch)
- **Issue:** `field.copy` in Jinja2 resolves to Python dict's built-in `.copy()` method, not the `copy` key value
- **Fix:** Used `'copy' in field and not field['copy']` bracket notation
- **Files modified:** templates/17.0/model.py.j2, templates/18.0/model.py.j2
- **Verification:** test_copy_false passes
- **Committed in:** 34ac943

**2. [Rule 3 - Blocking] inherit list type not handled in renderer_context**
- **Found during:** Task 1 (view rendering for document.document)
- **Issue:** `model.get("inherit")` returns a list for document.document (`["mail.thread"]`), but code assumed string
- **Fix:** Added isinstance check for list type in explicit_inherit handling and parent_is_in_module check
- **Files modified:** renderer_context.py
- **Verification:** E2E tests render document.document view without TypeError
- **Committed in:** 34ac943

**3. [Rule 1 - Bug] Security preprocessor overwrites domain preprocessor roles**
- **Found during:** Task 2 (E2E security groups test)
- **Issue:** Security preprocessor at order=60 replaces security_roles dict, losing viewer/uploader/verifier/manager from document_management at order=28
- **Fix:** Both _inject_legacy_security and _process_security_patterns now merge existing roles by name
- **Files modified:** preprocessors/security.py
- **Verification:** test_security_groups_include_all_roles passes, all 1495 tests green
- **Committed in:** f0623c6

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All fixes necessary for correct rendering. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Document management generation is now end-to-end complete
- Templates correctly render all field kwargs, constraint types, and view elements
- VERSION_GATES dict available for future version-conditional template logic
- Security role merge ensures domain preprocessor roles survive through security preprocessing
- Ready for Phase 53+ (further domain patterns or pipeline QoL)

---
*Phase: 52-document-management*
*Completed: 2026-03-08*
