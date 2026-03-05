---
phase: 32-controllers-import-export
plan: 01
subsystem: codegen
tags: [jinja2, controllers, http-route, odoo, tdd]

requires:
  - phase: 30-scheduled-actions-render-pipeline
    provides: render pipeline with stage functions and Result pattern
  - phase: 31-reports-analytics
    provides: report/dashboard templates and render_reports implementation
provides:
  - render_controllers() stage producing controllers/main.py with @http.route
  - controller.py.j2 template with secure defaults (auth='user', csrf=True)
  - init_controllers.py.j2 and init_root.py.j2 conditional import
  - has_controllers flag in _build_module_context()
affects: [32-02, manifest generation, render_module pipeline]

tech-stack:
  added: []
  patterns: [controller class inheriting http.Controller, JSON try/except error handling]

key-files:
  created:
    - python/src/odoo_gen_utils/templates/shared/controller.py.j2
    - python/src/odoo_gen_utils/templates/shared/init_controllers.py.j2
  modified:
    - python/src/odoo_gen_utils/templates/shared/init_root.py.j2
    - python/src/odoo_gen_utils/renderer.py
    - python/tests/test_render_stages.py
    - python/tests/test_renderer.py

key-decisions:
  - "JSON routes get try/except with structured {'status':'error','message':str(e)} response"
  - "Controller class_name auto-derived as _to_class(module_name) + 'Controller' when not specified"

patterns-established:
  - "Controller generation follows same render_template pattern as all other stages"
  - "Secure defaults: auth='user' and csrf=True applied via Jinja2 dict.get() defaults"

requirements-completed: [TMPL-03]

duration: 5min
completed: 2026-03-06
---

# Phase 32 Plan 01: Controller Templates + render_controllers Summary

**HTTP controller generation with @http.route, secure defaults (auth='user', csrf=True), and JSON error handling via controller.py.j2 template**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T20:00:06Z
- **Completed:** 2026-03-05T20:05:12Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- controller.py.j2 renders @http.route with secure defaults and JSON try/except error handling
- init_controllers.py.j2 produces `from . import main` for controllers package
- init_root.py.j2 conditionally imports controllers when has_controllers=True
- render_controllers() replaces placeholder with full implementation producing controllers/main.py and __init__.py
- _build_module_context() includes has_controllers flag
- 11 new tests, 711 total passing with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `c1098e6` (test)
2. **Task 1 GREEN: Controller implementation** - `873d8d1` (feat)
3. **Task 2: Regression fix + full suite** - `d832646` (fix)

_Note: TDD task has RED and GREEN commits._

## Files Created/Modified
- `python/src/odoo_gen_utils/templates/shared/controller.py.j2` - HTTP controller class template with @http.route loops
- `python/src/odoo_gen_utils/templates/shared/init_controllers.py.j2` - controllers/__init__.py importing main
- `python/src/odoo_gen_utils/templates/shared/init_root.py.j2` - Added conditional controllers import
- `python/src/odoo_gen_utils/renderer.py` - render_controllers() implementation + has_controllers in context
- `python/tests/test_render_stages.py` - TestRenderControllers class (8 tests) + context helper fix
- `python/tests/test_renderer.py` - TestBuildModuleContextControllers class (3 tests)

## Decisions Made
- JSON routes get try/except with structured `{'status':'error','message':str(e)}` response
- Controller class_name auto-derived as `_to_class(module_name) + "Controller"` when not specified in spec
- Secure defaults applied via Jinja2 `dict.get()` with fallback values in template

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added has_controllers to test helper _make_module_context()**
- **Found during:** Task 2 (full suite regression)
- **Issue:** init_root.py.j2 now references has_controllers but the test helper didn't include it, causing StrictUndefined error in all render_manifest tests
- **Fix:** Added `"has_controllers": bool(spec.get("controllers"))` to _make_module_context() in test_render_stages.py
- **Files modified:** python/tests/test_render_stages.py
- **Verification:** Full suite passes (711 tests)
- **Committed in:** d832646

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix for test helper consistency. No scope creep.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Controller generation complete, ready for Plan 02 (import/export)
- render_controllers() follows the same stage pattern as all other render_* functions
- has_controllers flag available in module context for manifest and other templates

## Self-Check: PASSED

All 7 files verified on disk. All 3 commit hashes verified in git log.

---
*Phase: 32-controllers-import-export*
*Completed: 2026-03-06*
