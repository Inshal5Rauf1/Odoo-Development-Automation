---
phase: 02-knowledge-base
plan: 01
subsystem: knowledge
tags: [odoo-17, orm, views, security, manifest, oca-standards, pylint-odoo]

# Dependency graph
requires:
  - phase: 01-gsd-extension
    provides: Extension directory structure and agent definitions
provides:
  - MASTER.md with global Odoo 17.0 conventions (naming, imports, style, directory structure)
  - models.md with ORM rules, field types, decorators, constraints, CRUD overrides
  - views.md with form/tree/search view rules, inline modifiers, statusbar patterns
  - security.md with ACL CSV format, group hierarchy, record rules
  - manifest.md with required/forbidden keys, version format, data load order
affects: [02-knowledge-base, 05-core-code-generation, 06-security-test-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [rule-example-why-format, master-plus-category-hierarchy, 500-line-cap]

key-files:
  created:
    - knowledge/MASTER.md
    - knowledge/models.md
    - knowledge/views.md
    - knowledge/security.md
    - knowledge/manifest.md
  modified: []

key-decisions:
  - "Rule format: Rule statement + WRONG code + CORRECT code + Why explanation for every rule"
  - "Changed in 17.0 section as table with what-was/what-is pairs in every category file"
  - "pylint-odoo rules presented as compact tables mapping rule ID to trigger and fix"

patterns-established:
  - "Rule + WRONG + CORRECT + Why: every knowledge rule follows this 4-part format"
  - "Changed in 17.0: dedicated table section at end of each category file"
  - "MASTER.md: lean global conventions (~161 lines) all agents load"

requirements-completed: [KNOW-01, KNOW-02, KNOW-03]

# Metrics
duration: 7min
completed: 2026-03-02
---

# Phase 2 Plan 01: Core Knowledge Base Summary

**MASTER.md global conventions plus 4 category files (models, views, security, manifest) with 40 WRONG/CORRECT example pairs covering Odoo 17.0 ORM, XML views, ACLs, and manifest rules**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-01T20:09:24Z
- **Completed:** 2026-03-01T20:16:52Z
- **Tasks:** 2
- **Files created:** 5

## Accomplishments
- MASTER.md created with global Odoo 17.0 conventions: naming, imports, Python style, directory structure, version format, and top version pitfalls table (161 lines)
- models.md created with 15 WRONG/CORRECT pairs covering field types, relational fields, computed fields, constraints, CRUD overrides, decorators, inheritance, and OCA conventions (482 lines)
- views.md created with 9 WRONG/CORRECT pairs covering form/tree/search views, inline modifiers (attrs removed), statusbar, actions/menus, and external ID naming (382 lines)
- security.md created with 6 WRONG/CORRECT pairs covering module categories, group hierarchy with implied_ids, ACL CSV format, record rules, and data load order (244 lines)
- manifest.md created with 8 WRONG/CORRECT pairs covering required keys, version format (17.0.X.Y.Z), license, forbidden keys, dependencies, and application flag (280 lines)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MASTER.md and models.md** - `1331979` (feat)
2. **Task 2: Create views.md, security.md, and manifest.md** - `6bd9f6d` (feat)

## Files Created/Modified
- `knowledge/MASTER.md` - Global Odoo 17.0 conventions loaded by all agents (161 lines)
- `knowledge/models.md` - ORM, fields, decorators, constraints, CRUD, inheritance rules (482 lines)
- `knowledge/views.md` - Form, tree, search views, inline modifiers, actions/menus (382 lines)
- `knowledge/security.md` - ACLs, groups, record rules, multi-company patterns (244 lines)
- `knowledge/manifest.md` - Required keys, version format, license, data load order (280 lines)

## Decisions Made
- Rule format standardized as Rule statement + WRONG code + CORRECT code + Why explanation
- Changed in 17.0 sections use table format with what-was/what-is columns
- pylint-odoo rules presented as compact tables (Rule | Trigger | Fix) rather than full code examples to save space
- models.md trimmed from initial 646 lines to 482 by consolidating inverse pattern, SQL constraints, write/unlink examples, inheritance delegation, and OCA rec_name/order sections

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] models.md exceeded 500-line limit**
- **Found during:** Task 1
- **Issue:** Initial models.md was 646 lines, exceeding the 500-line hard cap
- **Fix:** Consolidated compute inverse example, SQL constraints, write/unlink overrides, Many2many relation table, inheritance delegation, OCA order/rec_name sections, and pylint-odoo rules into compact format
- **Files modified:** knowledge/models.md
- **Verification:** Final line count 482 (under 500)
- **Committed in:** 1331979 (Task 1 commit, after trimming)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary trimming to meet 500-line requirement. All rules preserved, just more compact.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 5 core knowledge files ready for agent @include references
- Remaining category files (testing, actions, data, i18n, controllers, wizards, inheritance) are covered in 02-02-PLAN.md
- Custom rules extensibility and agent KB wiring covered in 02-03-PLAN.md

## Self-Check: PASSED

- All 5 knowledge files exist on disk
- Commit 1331979 (Task 1) found in git log
- Commit 6bd9f6d (Task 2) found in git log
- 02-01-SUMMARY.md created successfully

---
*Phase: 02-knowledge-base*
*Completed: 2026-03-02*
