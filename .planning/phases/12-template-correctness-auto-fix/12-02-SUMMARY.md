---
phase: 12-template-correctness-auto-fix
plan: 02
subsystem: validation
tags: [auto-fix, mail.thread, unused-imports, ast, knowledge-base, odoo]

# Dependency graph
requires:
  - phase: 11-docker-validation
    provides: auto_fix.py with FIXABLE_DOCKER_PATTERNS and identify_docker_fix
provides:
  - fix_missing_mail_thread function for chatter/model consistency auto-repair
  - fix_unused_imports function for AST-based unused import removal
  - FIXABLE_DOCKER_PATTERNS expanded to 5 patterns (missing_mail_thread)
  - Knowledge base documentation of mail.thread inheritance rules
affects: [13-deploy-polish, validation-pipeline, template-rendering]

# Tech tracking
tech-stack:
  added: []
  patterns: [ast-based-import-analysis, xml-content-scanning, immutable-read-transform-write]

key-files:
  created: []
  modified:
    - python/src/odoo_gen_utils/auto_fix.py
    - python/tests/test_auto_fix.py
    - knowledge/models.md

key-decisions:
  - "Used AST parsing for import analysis rather than pure regex -- more reliable for complex import statements"
  - "Targeted unused import detection at known template patterns (api, ValidationError, AccessError, _) rather than building a full Python import analyzer"
  - "Inserted _inherit line after _description to match OCA convention ordering (_name, _inherit, _description)"

patterns-established:
  - "Module-level auto-fix: scan views/ XML for indicators, then fix models/ Python files"
  - "Targeted import analysis: focus on known patterns rather than general-purpose unused import detection"

requirements-completed: [AFIX-01, AFIX-02, KNOW-01, KNOW-02]

# Metrics
duration: 4min
completed: 2026-03-03
---

# Phase 12 Plan 02: Auto-Fix & Knowledge Base Summary

**Two new auto-fix functions (mail.thread inheritance + unused imports) with AST-based detection, 15 new tests, and knowledge base documentation of the mail.thread triple dependency**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-03T17:08:05Z
- **Completed:** 2026-03-03T17:12:22Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- fix_missing_mail_thread detects chatter XML references (oe_chatter, chatter tag, message_ids) and adds _inherit = ['mail.thread', 'mail.activity.mixin'] to model.py
- fix_unused_imports uses AST parsing to detect and remove unused ValidationError, api, and other template-pattern imports
- FIXABLE_DOCKER_PATTERNS expanded from 4 to 5 patterns with missing_mail_thread and keyword detection
- Knowledge base documents the triple dependency (mail depends + model inherit + chatter view) with Rule/WRONG/CORRECT/Why format

## Task Commits

Each task was committed atomically:

1. **Task 1: Add missing mail.thread and unused import auto-fix functions** - `7698374` (test: RED), `4d86866` (feat: GREEN)
2. **Task 2: Update knowledge base with mail.thread inheritance rules** - `4a0710d` (docs)

_Note: Task 1 used TDD with separate RED and GREEN commits_

## Files Created/Modified
- `python/src/odoo_gen_utils/auto_fix.py` - Two new auto-fix functions (fix_missing_mail_thread, fix_unused_imports), updated constants and keywords
- `python/tests/test_auto_fix.py` - 15 new tests across 3 test classes (TestFixMissingMailThread, TestFixUnusedImports, TestUpdatedConstants)
- `knowledge/models.md` - New "mail.thread and mail.activity.mixin" section with 3 subsections

## Decisions Made
- Used AST parsing for import analysis rather than pure regex -- more reliable for multi-name import statements and avoids false matches in strings/comments
- Targeted unused import detection at known template patterns (api, ValidationError, AccessError, _) rather than building a general-purpose analyzer -- keeps scope focused per CONTEXT.md
- Inserted _inherit after _description line (not after _name) to match OCA convention ordering

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Auto-fix pipeline now handles 5 Docker patterns and 5 pylint codes
- Knowledge base ready for agent consumption with mail.thread rules
- Plan 01 (template fixes) can be executed independently

## Self-Check: PASSED

All files verified present, all commits verified in git log.

---
*Phase: 12-template-correctness-auto-fix*
*Completed: 2026-03-03*
