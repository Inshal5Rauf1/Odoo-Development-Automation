---
phase: 41-spec-diffing-migration
plan: 02
subsystem: tooling
tags: [migration, cli, raw-sql, backup-restore, code-generation, click]

# Dependency graph
requires:
  - phase: 41-spec-diffing-migration plan 01
    provides: spec_differ.py with diff_specs(), hierarchical change structure, destructiveness classification
provides:
  - migration_generator.py module with generate_migration(), MigrationResult, per-change helper generation
  - gen-migration CLI command with pre-migrate.py and post-migrate.py output
  - Backup/restore column pattern for destructive changes
  - Validation query pattern for possibly-destructive changes
affects: [43-integration-testing]

# Tech tracking
tech-stack:
  added: []
  patterns: [per-change helper generation, backup/restore column pattern, validation query pattern for possibly-destructive, raw SQL only migration scripts]

key-files:
  created:
    - python/src/odoo_gen_utils/migration_generator.py
  modified:
    - python/src/odoo_gen_utils/cli.py
    - python/tests/test_migration_generator.py

key-decisions:
  - "String formatting (f-strings) for migration script generation instead of Jinja2 templates -- scripts are simple enough that string formatting is cleaner"
  - "PostgreSQL type mapping (_FIELD_TYPE_TO_PG) for backup columns using proper PG types based on Odoo field type"
  - "generate_migration returns dict (not writes files) when output_dir not provided -- enables testing without filesystem side effects"

patterns-established:
  - "Backup/restore pattern: _backup_{field}(cr) in pre-migrate creates {field}_backup column and copies data; _restore_{field}(cr) in post-migrate restores and drops backup"
  - "Validation pattern: _validate_{field}(cr) in pre-migrate runs SELECT COUNT(*) to check for NULLs or invalid values, logs warning, and backfills with safe defaults"
  - "Per-change helpers: each field change maps to an independent helper function taking only cr, called sequentially from migrate(cr, version)"
  - "Docstring prefix convention: DESTRUCTIVE: for always_destructive, POSSIBLY DESTRUCTIVE: for possibly_destructive"

requirements-completed: [TOOL-04]

# Metrics
duration: 10min
completed: 2026-03-07
---

# Phase 41 Plan 02: Migration Generator Summary

**Migration script generator with per-change helpers, backup/restore column pattern for destructive changes, validation queries for possibly-destructive, and gen-migration CLI command**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-07T01:10:12Z
- **Completed:** 2026-03-07T01:20:11Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- migration_generator.py with generate_migration(), MigrationResult, _model_to_table(), _generate_pre_helpers(), _generate_post_helpers(), _render_script()
- Per-change helper functions: backup/restore for destructive type changes and field removal, validation queries for required changes and selection option removal
- gen-migration CLI command creating migrations/{version}/pre-migrate.py and post-migrate.py
- 50 unit tests covering all migration patterns, script structure, syntax validity, and multiple changes
- End-to-end pipeline verified: diff-spec + gen-migration with test fixtures produces valid Python scripts

## Task Commits

Each task was committed atomically:

1. **Task 1: Create migration_generator.py with per-change helper generation** - `a8d16c8` (test: RED) + `1cffc24` (feat: GREEN)
2. **Task 2: Wire gen-migration CLI command** - `de93a75` (feat)

_Note: Task 1 used TDD with separate RED and GREEN commits_

## Files Created/Modified
- `python/src/odoo_gen_utils/migration_generator.py` - Migration script generation: per-change helpers, backup/restore patterns, validation queries, raw SQL
- `python/src/odoo_gen_utils/cli.py` - gen-migration CLI command registration
- `python/tests/test_migration_generator.py` - 50 unit tests for migration generation across all change types

## Decisions Made
- Used f-string formatting for script generation instead of Jinja2 templates (simpler, no template file overhead)
- Added _FIELD_TYPE_TO_PG mapping dict for proper PostgreSQL type selection in backup columns
- generate_migration() returns code strings without writing files when output_dir is None (better testability)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full diff-spec -> gen-migration pipeline operational
- Test fixtures (spec_v1.json, spec_v2.json) available for integration testing
- Phase 41 complete: both spec differ and migration generator shipped
- Ready for Phase 43 integration testing

## Self-Check: PASSED

All 3 created/modified files verified present. All 3 commit hashes verified in git log.
