---
phase: 40-notifications-webhooks
plan: 02
subsystem: codegen
tags: [jinja2, mail-template, notifications, webhooks, send-mail, model-template, odoo]

# Dependency graph
requires:
  - phase: 40-notifications-webhooks
    plan: 01
    provides: notification/webhook preprocessors, enriched approval action methods with notification key, webhook context keys, render_mail_templates stage
  - phase: 39-approval-workflows
    provides: approval_action_methods, approval_submit_action, approval_reject_action dicts on model
  - phase: 38-audit-trail
    provides: audit write stacking (old_values capture, _audit_log_changes), _audit_skip fast path
provides:
  - Notification send_mail blocks in action methods with try/except + _logger.warning
  - Logger import conditional on has_notifications
  - Webhook stub methods (_webhook_post_create, _webhook_post_write, _webhook_pre_unlink)
  - Webhook create() override guard with _skip_webhooks context flag
  - Webhook write() old_vals capture (reuses audit old_values or standalone)
  - Webhook dispatch as last block in write() before return
  - auto_delete field in mail_template_data.xml.j2
  - 18.0 template parity for all notification and webhook blocks
affects: [model.py.j2 rendering, manifest generation, full-pipeline rendering]

# Tech tracking
tech-stack:
  added: []
  patterns: [send-mail-try-except-in-action-method, webhook-stub-extension-point, webhook-skip-context-flag, webhook-old-vals-reuse-audit, dict-get-for-optional-jinja2-keys]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/templates/17.0/model.py.j2
    - python/src/odoo_gen_utils/templates/18.0/model.py.j2
    - python/src/odoo_gen_utils/templates/shared/mail_template_data.xml.j2
    - python/tests/test_renderer.py
    - python/tests/test_render_stages.py

key-decisions:
  - "Use dict.get('notification') in Jinja2 templates for StrictUndefined safety when checking optional notification key on action methods"
  - "Webhook old_vals in 18.0 always uses standalone capture (audit not ported to 18.0)"
  - "auto_delete eval='True' added to mail.template XML for email cleanup"

patterns-established:
  - "send_mail pattern: try/except with _logger.warning after state write, force_send=False for queue"
  - "Webhook stub pattern: empty pass methods with docstrings, designed for _inherit override"
  - "Webhook write stacking: old_vals capture BEFORE super(), dispatch AFTER audit log, LAST before return"
  - "dict.get() pattern for optional keys in Jinja2 StrictUndefined environment"

requirements-completed: [BIZL-02, BIZL-03]

# Metrics
duration: 16min
completed: 2026-03-07
---

# Phase 40 Plan 02: Notification & Webhook Template Rendering Summary

**Notification send_mail blocks in action methods with try/except logging, webhook stub methods with create/write guards, and full write() stacking order with audit old_vals reuse**

## Performance

- **Duration:** 16 min
- **Started:** 2026-03-06T20:55:54Z
- **Completed:** 2026-03-06T21:12:46Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added logger import conditional on has_notifications to both 17.0 and 18.0 model.py.j2 templates
- Injected send_mail blocks with try/except + _logger.warning in submit, approve, and reject action methods (only when action has notification key)
- Implemented webhook stub methods (_webhook_post_create, _webhook_post_write, _webhook_pre_unlink) with descriptive docstrings
- Added webhook create() guard with _skip_webhooks context flag and per-record dispatch
- Implemented webhook write() old_vals capture that reuses audit old_values when audit is present, standalone capture otherwise
- Webhook dispatch is the LAST block in write() before return (after audit log)
- Added auto_delete field to mail_template_data.xml.j2
- 18.0 template has full parity with notification and webhook blocks
- 36 new tests (21 unit + 15 smoke), full suite green at 1022 tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Create mail_template_data.xml.j2 and add notification/webhook blocks to model.py.j2 (17.0 and 18.0)** - `4d6a297` (feat)
2. **Task 2: Full-pipeline smoke tests and regression verification** - `b57c2d9` (test)

## Files Created/Modified
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` - Added logger import, send_mail in action methods, webhook stubs, webhook create/write guards
- `python/src/odoo_gen_utils/templates/18.0/model.py.j2` - Same notification and webhook blocks adapted for 18.0 (no audit, standalone old_vals)
- `python/src/odoo_gen_utils/templates/shared/mail_template_data.xml.j2` - Added auto_delete eval="True" field
- `python/tests/test_renderer.py` - Added TestNotificationTemplateRendering (11 tests) and TestWebhookTemplateRendering (10 tests)
- `python/tests/test_render_stages.py` - Added TestNotificationWebhookSmokeFullPipeline (15 tests)

## Decisions Made
- Used `dict.get('notification')` instead of `dict.notification` in Jinja2 templates to prevent StrictUndefined crashes when action methods don't have notification key -- essential for compatibility with non-notifying levels
- 18.0 webhook old_vals always uses standalone capture block (audit not yet ported to 18.0 per Phase 39 decisions)
- Added auto_delete eval="True" to mail.template XML records per plan specification

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] StrictUndefined crash on action.notification**
- **Found during:** Task 1
- **Issue:** `{% if action.notification %}` in Jinja2 with StrictUndefined throws UndefinedError when action dict doesn't have 'notification' key
- **Fix:** Changed to `{% if action.get('notification') %}` for safe key access on all notification conditionals
- **Files modified:** python/src/odoo_gen_utils/templates/17.0/model.py.j2, python/src/odoo_gen_utils/templates/18.0/model.py.j2
- **Verification:** All tests pass including non-notifying action methods
- **Committed in:** 4d6a297 (Task 1 commit)

**2. [Rule 1 - Bug] Security spec format in smoke test fixture**
- **Found during:** Task 2
- **Issue:** Plan's spec used dict-format roles `[{"name": "user", "label": "User"}]` but security preprocessor expects string array `["user", "manager"]`
- **Fix:** Changed smoke test fixture to use string array format consistent with all other tests
- **Files modified:** python/tests/test_render_stages.py
- **Verification:** All 15 smoke tests pass
- **Committed in:** b57c2d9 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 40 (Notifications & Webhooks) is fully complete
- All preprocessors (Plan 01) and template rendering (Plan 02) working end-to-end
- 1022 tests passing (36 new in this plan)
- Ready for next phase in the roadmap

---
## Self-Check: PASSED

- All 5 files verified present
- Both task commits (4d6a297, b57c2d9) verified in git log
- 1022 tests passing (excluding pre-existing Docker/verifier env failures)

---
*Phase: 40-notifications-webhooks*
*Completed: 2026-03-07*
