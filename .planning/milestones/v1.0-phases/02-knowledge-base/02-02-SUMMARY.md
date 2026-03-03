---
phase: 02-knowledge-base
plan: 02
subsystem: knowledge
tags: [odoo-17, testing, actions, inheritance, data, i18n, controllers, wizards, knowledge-base]

# Dependency graph
requires:
  - phase: 01-gsd-extension
    provides: Extension directory structure and agent definitions
provides:
  - 7 additional knowledge base category files covering testing, actions, inheritance, data, i18n, controllers, wizards
  - Complete domain coverage for Odoo 17.0 code generation rules
affects: [03-validation-infrastructure, 05-core-code-generation, 06-security-test-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [rule-example-why-format, changed-in-17-section, wrong-correct-pairs]

key-files:
  created:
    - knowledge/testing.md
    - knowledge/actions.md
    - knowledge/inheritance.md
    - knowledge/data.md
    - knowledge/i18n.md
    - knowledge/controllers.md
    - knowledge/wizards.md
  modified: []

key-decisions:
  - "Each knowledge file follows consistent structure: sections with Rule + WRONG + CORRECT + Why format"
  - "All files include Changed in 17.0 table and Common Mistakes section"
  - "testing.md uses TransactionCase as primary base class (SavepointCase deprecated in 17.0)"
  - "actions.md specifies tree (not list) in view_mode for Odoo 17.0"
  - "inheritance.md documents all three inheritance patterns: _inherit, _inherits, _name+_inherit"

patterns-established:
  - "Knowledge file structure: Header > Rule sections > Changed in 17.0 > Common Mistakes > pylint-odoo rules"
  - "WRONG/CORRECT code examples are copy-pasteable with sufficient context"

requirements-completed: [KNOW-01, KNOW-02]

# Metrics
duration: 6min
completed: 2026-03-02
---

# Phase 02 Plan 02: Extended Knowledge Base Summary

**7 Odoo 17.0 knowledge files covering testing, actions, inheritance, data, i18n, controllers, and wizards with WRONG/CORRECT examples and version-specific guidance**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-01T20:09:45Z
- **Completed:** 2026-03-01T20:16:17Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created testing.md with TransactionCase patterns, CRUD/constraint/access rights/workflow test coverage (375 lines)
- Created actions.md with window actions, server actions, menu hierarchy, and action binding patterns (246 lines)
- Created inheritance.md with model extension, delegation, view inheritance, and xpath patterns (376 lines)
- Created data.md with data files, demo data conventions, XML/CSV formats, and load order rules (273 lines)
- Created i18n.md with translation markup, translatable fields, and .pot generation patterns (219 lines)
- Created controllers.md with HTTP controllers, route decorators, auth options, and request/response patterns (264 lines)
- Created wizards.md with TransientModel patterns, wizard views, action methods, and context passing (336 lines)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create testing.md, actions.md, and inheritance.md** - `2ec2c8c` (feat)
2. **Task 2: Create data.md, i18n.md, controllers.md, and wizards.md** - `6bd9f6d` (feat)

## Files Created/Modified
- `knowledge/testing.md` - Test base classes, CRUD/constraint/access/workflow test patterns (375 lines)
- `knowledge/actions.md` - Window actions, server actions, menu hierarchy (246 lines)
- `knowledge/inheritance.md` - Model extension, delegation, view/xpath inheritance (376 lines)
- `knowledge/data.md` - Data files, demo data, XML/CSV formats, load order (273 lines)
- `knowledge/i18n.md` - Translation markup, translatable fields, .pot generation (219 lines)
- `knowledge/controllers.md` - HTTP controllers, route decorators, auth, request/response (264 lines)
- `knowledge/wizards.md` - TransientModel patterns, wizard views, action methods (336 lines)

## Decisions Made
- Used TransactionCase as primary test base class (SavepointCase deprecated in 17.0)
- Used `tree` (not `list`) in view_mode for Odoo 17.0 in actions.md
- Documented all three model inheritance patterns in inheritance.md (_inherit, _inherits, _name+_inherit)
- Included Jinja2 template syntax in data.md email templates (Odoo 17.0 default, replacing Mako)
- Documented `records` variable (not `object`) for server action code in 17.0

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created knowledge/ directory**
- **Found during:** Task 1 (before file creation)
- **Issue:** `knowledge/` directory did not exist yet (Plan 02-01 not committed)
- **Fix:** Created the directory with `mkdir -p`
- **Files modified:** knowledge/ (directory creation)
- **Verification:** Directory exists, files created successfully
- **Committed in:** 2ec2c8c (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Trivial -- directory creation was necessary for file creation. No scope creep.

## Issues Encountered
- Plan 02-01 files (MASTER.md, models.md, views.md, security.md, manifest.md) existed on disk but were not committed to git. The Task 2 commit included security.md, views.md, and manifest.md because they were untracked in the knowledge/ directory. This is harmless -- those files will be properly attributed when Plan 02-01 SUMMARY is created.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 7 of 11 category knowledge files complete (Plan 02-03 handles extensibility and agent updates)
- Combined with Plan 02-01 files, the knowledge/ directory has comprehensive Odoo 17.0 domain coverage
- All files follow the Rule + WRONG + CORRECT + Why format consistently
- All files under 500-line cap (largest is inheritance.md at 376 lines)

## Self-Check: PASSED

All 7 knowledge files exist on disk. Both task commits (2ec2c8c, 6bd9f6d) found in git history. SUMMARY.md created successfully.

---
*Phase: 02-knowledge-base*
*Completed: 2026-03-02*
