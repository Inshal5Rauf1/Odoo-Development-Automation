---
phase: 31-reports-analytics
plan: 01
subsystem: template-generation
tags: [jinja2, qweb, odoo-reports, graph-view, pivot-view, pdf]

# Dependency graph
requires:
  - phase: 30-scheduled-actions
    provides: render_reports() placeholder wired as stage 9 of 10
provides:
  - render_reports() generates PDF report actions, QWeb templates, paper formats
  - render_reports() generates graph and pivot dashboard views
  - _build_module_context() enriched with report/dashboard manifest entries
  - _build_model_context() enriched with model_reports and has_dashboard
  - Form view print buttons for models with reports
  - Action view_mode extended with graph,pivot for dashboard models
affects: [32-controllers-export, 33-performance]

# Tech tracking
tech-stack:
  added: []
  patterns: [report-action-xml, qweb-report-template, graph-pivot-dashboard-views]

key-files:
  created:
    - python/src/odoo_gen_utils/templates/shared/report_action.xml.j2
    - python/src/odoo_gen_utils/templates/shared/report_template.xml.j2
    - python/src/odoo_gen_utils/templates/shared/graph_view.xml.j2
    - python/src/odoo_gen_utils/templates/shared/pivot_view.xml.j2
  modified:
    - python/src/odoo_gen_utils/renderer.py
    - python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2
    - python/src/odoo_gen_utils/templates/17.0/action.xml.j2
    - python/src/odoo_gen_utils/templates/18.0/view_form.xml.j2
    - python/src/odoo_gen_utils/templates/18.0/action.xml.j2

key-decisions:
  - "Used dict.get() in Jinja2 templates for optional fields (paper_format, detail_field, stacked, interval) to work with StrictUndefined"
  - "Report data files placed in data/ directory for consistency with existing cron/sequence patterns"
  - "Dashboard graph/pivot files placed in views/ directory alongside model views"

patterns-established:
  - "Report generation pattern: report_action.xml.j2 + report_template.xml.j2 per report entry"
  - "Dashboard view pattern: graph_view.xml.j2 + pivot_view.xml.j2 per dashboard entry"
  - "Form header conditionally rendered when state_field OR model_reports present"

requirements-completed: [TMPL-01, TMPL-02]

# Metrics
duration: 7min
completed: 2026-03-06
---

# Phase 31 Plan 01: Reports & Analytics Summary

**QWeb PDF report generation with ir.actions.report/paper format/print buttons and graph/pivot dashboard views with configurable measures/dimensions**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-05T19:26:38Z
- **Completed:** 2026-03-05T19:33:37Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 11

## Accomplishments
- 4 new Jinja2 templates for reports and dashboards (report_action, report_template, graph_view, pivot_view)
- render_reports() replaces placeholder with full report + dashboard generation pipeline
- Form views automatically get print buttons when model has reports
- Action view_mode conditionally includes graph,pivot for dashboard models
- Module manifest correctly includes all report data files and dashboard view files
- 21 new tests passing, full suite 651 passed

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests** - `9c86f94` (test)
2. **Task 1 (GREEN): Implementation** - `bd08126` (feat)

## Files Created/Modified
- `templates/shared/report_action.xml.j2` - ir.actions.report + optional paper format XML
- `templates/shared/report_template.xml.j2` - QWeb t-call/t-foreach/t-field report body
- `templates/shared/graph_view.xml.j2` - Graph view with measures and dimensions
- `templates/shared/pivot_view.xml.j2` - Pivot view with row/col/measure fields
- `renderer.py` - render_reports() implementation + context enrichment
- `templates/17.0/view_form.xml.j2` - Print button injection in form header
- `templates/17.0/action.xml.j2` - Conditional graph,pivot in view_mode
- `templates/18.0/view_form.xml.j2` - Print button injection (18.0 variant)
- `templates/18.0/action.xml.j2` - Conditional graph,pivot in view_mode (18.0 variant)
- `tests/test_render_stages.py` - TestRenderReports + TestRenderDashboards + integration test
- `tests/test_renderer.py` - Context enrichment tests for reports/dashboards

## Decisions Made
- Used `dict.get()` in Jinja2 templates instead of direct attribute access for optional fields, since StrictUndefined raises on missing keys
- Report data files go in `data/` directory (consistent with cron_data.xml, sequences.xml patterns)
- Dashboard view files go in `views/` directory alongside model views
- Manifest load order: report data files after cron, dashboard views after model action files

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Jinja2 StrictUndefined errors for optional dict keys**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Templates used `report.paper_format`, `report.detail_field`, `dashboard.stacked`, `dim.interval` which raises UndefinedError when key is absent in dict with StrictUndefined
- **Fix:** Changed all optional key accesses to use `.get()` method (e.g., `report.get('paper_format')`)
- **Files modified:** All 4 new templates
- **Verification:** All 21 tests pass
- **Committed in:** bd08126 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for correctness with the existing Jinja2 StrictUndefined configuration. No scope creep.

## Issues Encountered
None beyond the auto-fixed StrictUndefined issue above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Report and dashboard generation complete, ready for Phase 32 (Controllers & Export)
- render_controllers() placeholder remains for Phase 32 implementation
- All existing functionality preserved (651 tests passing)

---
*Phase: 31-reports-analytics*
*Completed: 2026-03-06*
