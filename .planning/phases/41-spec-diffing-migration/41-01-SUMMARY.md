---
phase: 41-spec-diffing-migration
plan: 01
subsystem: tooling
tags: [deepdiff, cli, spec-diffing, migration, click]

# Dependency graph
requires:
  - phase: 36-renderer-extraction
    provides: stable preprocessors module and spec format
provides:
  - spec_differ.py module with diff_specs(), format_human_summary(), SpecDiff
  - diff-spec CLI command with human and JSON output modes
  - destructiveness classification (always/possibly/non-destructive)
  - test fixtures spec_v1.json and spec_v2.json
affects: [41-02-migration-generator, 43-integration-testing]

# Tech tracking
tech-stack:
  added: [deepdiff>=8.0]
  patterns: [list-to-dict spec conversion for stable diffing, hierarchical change structure]

key-files:
  created:
    - python/src/odoo_gen_utils/spec_differ.py
    - python/tests/test_spec_differ.py
    - python/tests/fixtures/spec_v1.json
    - python/tests/fixtures/spec_v2.json
  modified:
    - python/pyproject.toml
    - python/src/odoo_gen_utils/cli.py

key-decisions:
  - "Direct dict comparison instead of DeepDiff for main diff: converted specs to dict-indexed form and compared directly for cleaner hierarchical output"
  - "Selection change detection uses key-based set difference for precise added/removed options"
  - "Float->Monetary classified as possibly_destructive (precision change) not always_destructive"

patterns-established:
  - "List-to-dict conversion: _spec_to_diffable() converts all list-indexed spec elements (models, fields, constraints, approval levels, cron, reports) to dict-indexed for stable comparison"
  - "Three-tier destructiveness classification: always_destructive (data loss certain), possibly_destructive (data loss possible), non_destructive (safe)"
  - "Excluded attribute pattern: presentation-only attributes (string, help, placeholder) filtered from schema comparison"

requirements-completed: [TOOL-01]

# Metrics
duration: 6min
completed: 2026-03-07
---

# Phase 41 Plan 01: Spec Differ Summary

**Spec differ module with deepdiff, hierarchical change structure, destructiveness classification, and diff-spec CLI command**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-07T01:00:18Z
- **Completed:** 2026-03-07T01:06:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- spec_differ.py with diff_specs(), format_human_summary(), _spec_to_diffable(), _classify_destructiveness()
- Hierarchical change structure: models.modified.{name}.fields.{added|removed|modified} with security, approval, webhook, constraint, cron, report support
- Three-tier destructiveness classification with exhaustive type change matrix
- diff-spec CLI command with human summary + JSON default output and --json flag for JSON only
- 63 unit tests covering all diff logic, destructiveness, formatting, and pure function guarantee

## Task Commits

Each task was committed atomically:

1. **Task 1: Create spec_differ.py with diff logic** - `3497952` (test: RED) + `f4b37e1` (feat: GREEN)
2. **Task 2: Wire diff-spec CLI command** - `0b79fe1` (feat)

_Note: Task 1 used TDD with separate RED and GREEN commits_

## Files Created/Modified
- `python/src/odoo_gen_utils/spec_differ.py` - Spec diffing logic: deepdiff-to-hierarchical translator, destructiveness classification, human formatting
- `python/src/odoo_gen_utils/cli.py` - diff-spec CLI command registration
- `python/pyproject.toml` - deepdiff>=8.0 dependency added
- `python/tests/test_spec_differ.py` - 63 unit tests for diff logic, destructiveness, human format, pure function
- `python/tests/fixtures/spec_v1.json` - Old spec fixture with 2 models, security, approval, webhooks, constraints, cron, reports
- `python/tests/fixtures/spec_v2.json` - New spec fixture with added/removed/modified elements across all categories

## Decisions Made
- Used direct dict comparison after _spec_to_diffable() conversion instead of relying on DeepDiff's raw path parsing -- produces cleaner hierarchical output without brittle path string parsing
- Float->Monetary classified as possibly_destructive (precision change may affect values) rather than always_destructive
- Selection change detection uses key-based set difference for precise tracking of which options were added vs removed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- spec_differ.py provides complete diff output for Plan 02 (migration generator) to consume
- diff_specs() returns structured dict with changes, destructive_count, and warnings
- Test fixtures spec_v1.json and spec_v2.json available for migration generator tests

## Self-Check: PASSED

All 6 created/modified files verified present. All 3 commit hashes verified in git log.

---
*Phase: 41-spec-diffing-migration*
*Completed: 2026-03-07*
