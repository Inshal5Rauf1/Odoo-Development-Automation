---
phase: 09-edition-version-support
plan: 02
subsystem: templates
tags: [jinja2, odoo-17, odoo-18, versioned-templates, filesystemloader]

# Dependency graph
requires:
  - phase: 05-core-code-generation
    provides: "Jinja2 renderer with create_renderer() and render_module()"
provides:
  - "Versioned template directories (17.0/, 18.0/, shared/)"
  - "create_versioned_renderer() with FileSystemLoader fallback chain"
  - "Version-aware render_module() reading odoo_version from spec"
affects: [09-edition-version-support]

# Tech tracking
tech-stack:
  added: []
  patterns: ["FileSystemLoader fallback chain [version_dir, shared_dir]", "Version-specific template directories"]

key-files:
  created:
    - "python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2"
    - "python/src/odoo_gen_utils/templates/17.0/view_tree.xml.j2"
    - "python/src/odoo_gen_utils/templates/17.0/action.xml.j2"
    - "python/src/odoo_gen_utils/templates/17.0/model.py.j2"
    - "python/src/odoo_gen_utils/templates/18.0/view_form.xml.j2"
    - "python/src/odoo_gen_utils/templates/18.0/view_tree.xml.j2"
    - "python/src/odoo_gen_utils/templates/18.0/action.xml.j2"
    - "python/src/odoo_gen_utils/templates/18.0/model.py.j2"
    - "python/src/odoo_gen_utils/templates/shared/ (16 templates)"
  modified:
    - "python/src/odoo_gen_utils/renderer.py"
    - "python/tests/test_renderer.py"

key-decisions:
  - "FileSystemLoader([version_dir, shared_dir]) for template fallback -- version-specific overrides shared"
  - "create_renderer() auto-detects base templates dir and falls back to create_versioned_renderer('17.0')"
  - "Separate template files per version (no if/else in templates) -- anti-pattern prevention"

patterns-established:
  - "Version-specific templates in templates/{version}/, shared in templates/shared/"
  - "FileSystemLoader fallback chain for version resolution"

requirements-completed: [VERS-04, VERS-05, VERS-06]

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 9 Plan 02: Versioned Templates & Renderer Summary

**Reorganized templates into 17.0/18.0/shared directories with FileSystemLoader fallback chain for version-aware module generation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T04:24:25Z
- **Completed:** 2026-03-03T04:27:53Z
- **Tasks:** 2
- **Files modified:** 24 (reorganized) + 2 (renderer + tests)

## Accomplishments
- Templates reorganized into 17.0/ (4 files), 18.0/ (4 files), shared/ (16 files) directories
- 18.0 templates use `<list>` tag (not `<tree>`), `<chatter/>` shorthand, and `list,form` view_mode
- Version-aware renderer with create_versioned_renderer() using FileSystemLoader fallback chain
- Full backward compatibility: existing tests pass, default version is 17.0
- 9 new tests added (51 total renderer tests, 243 total project tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Reorganize templates into 17.0/, 18.0/, shared/ directories** - `80af540` (feat)
2. **Task 2 RED: Failing tests for versioned rendering** - `fddb1b2` (test)
3. **Task 2 GREEN: Version-aware renderer implementation** - `e80b53c` (feat)

## Files Created/Modified
- `python/src/odoo_gen_utils/templates/17.0/` - 4 version-specific templates for Odoo 17.0 (tree tag, verbose chatter)
- `python/src/odoo_gen_utils/templates/18.0/` - 4 version-specific templates for Odoo 18.0 (list tag, chatter shorthand)
- `python/src/odoo_gen_utils/templates/shared/` - 16 version-independent templates
- `python/src/odoo_gen_utils/renderer.py` - Added create_versioned_renderer(), updated render_module()
- `python/tests/test_renderer.py` - Added 9 tests across 3 new test classes

## Decisions Made
- FileSystemLoader([version_dir, shared_dir]) for fallback -- version-specific templates override shared ones
- create_renderer() backward compatibility: detects base templates dir, falls back to versioned 17.0 loading
- Separate template files per version -- no conditional version logic inside templates (anti-pattern prevention)
- _register_filters() extracted as helper to avoid duplication between create_renderer and create_versioned_renderer

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Versioned templates and renderer ready for CLI wiring in Plan 03
- create_versioned_renderer() exported and ready for CLI integration
- All 243 tests pass with no regressions

---
*Phase: 09-edition-version-support*
*Completed: 2026-03-03*
