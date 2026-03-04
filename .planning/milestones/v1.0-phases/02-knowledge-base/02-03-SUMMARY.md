---
phase: 02-knowledge-base
plan: 03
subsystem: knowledge
tags: [odoo-17, knowledge-base, custom-rules, extensibility, agents, cli, validator, install]

# Dependency graph
requires:
  - phase: 02-knowledge-base
    provides: 12 shipped knowledge base files (MASTER + 11 categories) from Plans 01+02
provides:
  - Custom rules extensibility mechanism (custom/ directory with README)
  - kb_validator.py for validating custom rule file format
  - validate-kb CLI subcommand for checking knowledge base files
  - All 6 agents wired to knowledge base via @include references
  - install.sh updated to deploy knowledge/ directory
affects: [03-validation-infrastructure, 05-core-code-generation, 06-security-test-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [custom-extends-defaults, format-only-validation, symlink-based-kb-install]

key-files:
  created:
    - knowledge/custom/README.md
    - python/src/odoo_gen_utils/kb_validator.py
  modified:
    - python/src/odoo_gen_utils/cli.py
    - agents/odoo-scaffold.md
    - agents/odoo-model-gen.md
    - agents/odoo-view-gen.md
    - agents/odoo-security-gen.md
    - agents/odoo-test-gen.md
    - agents/odoo-validator.md
    - install.sh

key-decisions:
  - "Custom rules extend defaults, never override shipped rules"
  - "Format-only validation: checks headings, code blocks, line count, unclosed blocks -- no semantic validation"
  - "Knowledge base installed via symlink (same pattern as agents) to keep files in extension dir"
  - "custom/ directory README.md skipped by validator (documentation, not a rule file)"
  - "validate-kb defaults to custom/ only; --all flag validates shipped + custom"

patterns-established:
  - "@include pattern: agents reference @~/.claude/odoo-gen/knowledge/ for KB loading"
  - "Custom extensibility: custom/ subdirectory extends shipped rules per category"
  - "KB resolution: installed location (~/.claude/odoo-gen/knowledge/) with dev fallback (./knowledge/)"

requirements-completed: [KNOW-01, KNOW-04]

# Metrics
duration: 5min
completed: 2026-03-02
---

# Phase 02 Plan 03: KB Extensibility and Agent Wiring Summary

**Custom rules extensibility with format validator, all 6 agents wired to knowledge base via @include, and install.sh updated to deploy knowledge/ directory**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-01T20:21:07Z
- **Completed:** 2026-03-01T20:26:12Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Created knowledge/custom/ directory with comprehensive README explaining file naming, format requirements, loading order, and validation
- Built kb_validator.py with validate_kb_file() (5 checks: empty, heading, rule sections, code blocks, line count, unclosed blocks) and validate_kb_directory() for batch validation
- Added validate-kb CLI subcommand with --custom (default) and --all flags, automatic KB path resolution, and proper exit codes
- Updated all 6 agent definitions with Knowledge Base sections containing @include references to relevant knowledge files
- Updated install.sh with Step 7 to symlink knowledge/ directory and create custom/ subdirectory

## Task Commits

Each task was committed atomically:

1. **Task 1: Create custom/ directory with README and kb_validator.py** - `3fe4ec4` (feat)
2. **Task 2: Update agent definitions with knowledge base @include references** - `3e4f52c` (feat)

## Files Created/Modified
- `knowledge/custom/README.md` - Instructions for adding custom rules with format examples and validation guide
- `python/src/odoo_gen_utils/kb_validator.py` - Format validator with validate_kb_file() and validate_kb_directory()
- `python/src/odoo_gen_utils/cli.py` - Added validate-kb subcommand with --custom/--all flags
- `agents/odoo-scaffold.md` - Added KB section: MASTER + models + views + security + manifest
- `agents/odoo-model-gen.md` - Added KB section: MASTER + models + inheritance
- `agents/odoo-view-gen.md` - Added KB section: MASTER + views + actions
- `agents/odoo-security-gen.md` - Added KB section: MASTER + security
- `agents/odoo-test-gen.md` - Added KB section: MASTER + testing
- `agents/odoo-validator.md` - Added KB section: MASTER (version-checking context)
- `install.sh` - Added Step 7: symlink knowledge/ to ~/.claude/odoo-gen/knowledge/

## Decisions Made
- Custom rules extend defaults, never override -- enforced by loading order (shipped then custom)
- Format-only validation catches structural issues (missing headings, unclosed code blocks) without attempting semantic rule validation
- Knowledge base installed via symlink (matching agent registration pattern) to avoid file duplication
- README.md in custom/ skipped by validator since it is documentation, not a rule file
- validate-kb defaults to custom/ directory only (most common use case); --all adds shipped file validation

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 2 (Knowledge Base) is now complete: 12 shipped files + custom extensibility + agent wiring + CLI validation
- All agents can load comprehensive Odoo 17.0 rules during code generation
- Custom rules mechanism ready for team-specific conventions
- Phase 5 (Core Code Generation) and Phase 6 (Security & Test Generation) can rely on agent KB loading

## Self-Check: PASSED

- knowledge/custom/README.md exists on disk
- python/src/odoo_gen_utils/kb_validator.py exists on disk
- Commit 3fe4ec4 (Task 1) found in git log
- Commit 3e4f52c (Task 2) found in git log
- 02-03-SUMMARY.md created successfully

---
*Phase: 02-knowledge-base*
*Completed: 2026-03-02*
