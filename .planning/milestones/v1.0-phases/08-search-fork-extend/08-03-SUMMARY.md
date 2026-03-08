---
phase: 08-search-fork-extend
plan: 03
subsystem: search
tags: [git-sparse-checkout, ast-parse, xml-etree, fork-extend, odoo-inherit, xpath, click-cli, companion-module]

# Dependency graph
requires:
  - phase: 08-search-fork-extend
    provides: ChromaDB vector index, SearchResult, search_modules(), _parse_manifest_safe
provides:
  - clone_oca_module() for git sparse checkout of individual OCA modules
  - analyze_module() for AST-based model/field extraction and XML view parsing
  - setup_companion_dir() for {module}_ext directory structure creation
  - ModuleAnalysis frozen dataclass with 10 structural fields
  - extend-module CLI command with --repo, --spec-file, --branch options
  - odoo-extend agent with 5-phase delta code generation workflow
  - Activated /odoo-gen:extend command wired to odoo-extend agent
affects: [09-edition-version]

# Tech tracking
tech-stack:
  added: []
  patterns: [git sparse-checkout for efficient partial clone, AST-based model extraction, XML ElementTree view parsing, companion _ext module pattern]

key-files:
  created:
    - python/src/odoo_gen_utils/search/fork.py
    - python/src/odoo_gen_utils/search/analyzer.py
    - python/tests/test_search_fork.py
    - agents/odoo-extend.md
  modified:
    - python/src/odoo_gen_utils/search/__init__.py
    - python/src/odoo_gen_utils/cli.py
    - commands/extend.md

key-decisions:
  - "subprocess.run(check=True) for git commands -- CalledProcessError propagates naturally (not wrapped in RuntimeError)"
  - "AST-based field extraction scans for fields.X() call pattern with _ODOO_FIELD_TYPES frozenset"
  - "XML ElementTree for view type detection -- looks for form/tree/search/kanban tags in arch content"
  - "Security group extraction from res.groups records AND ir.module.category records with 'group' in ID"
  - "Companion module naming: {original}_ext suffix per Decision C"
  - "Refined spec saved to both {module}_ext/spec.json AND overwrites original (REFN-03)"

patterns-established:
  - "Git sparse checkout pattern: --no-checkout --filter=blob:none --sparse for efficient OCA cloning"
  - "Module analysis pipeline: manifest -> AST models -> XML views -> security groups -> structural flags"
  - "Companion _ext module: models/views/security/tests subdirs created by setup_companion_dir"
  - "odoo-extend agent 5-phase workflow: clone, gap analysis, delta code gen, spec save, verify"

requirements-completed: [FORK-01, FORK-02, FORK-03]

# Metrics
duration: 5min
completed: 2026-03-03
---

# Phase 8 Plan 3: Fork-and-Extend Workflow Summary

**Git sparse checkout clone, AST-based module analysis, companion _ext directory setup, odoo-extend delta generation agent, and activated /odoo-gen:extend command**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-03T01:01:58Z
- **Completed:** 2026-03-03T01:07:21Z
- **Tasks:** 2 (Task 1 TDD with RED/GREEN phases, Task 2 auto)
- **Files modified:** 7

## Accomplishments
- Complete fork.py with clone_oca_module() using git sparse checkout (--no-checkout --filter=blob:none --sparse) and setup_companion_dir() for {module}_ext structure
- Complete analyzer.py with AST-based model/field extraction, XML view type detection, security group parsing, and frozen ModuleAnalysis dataclass
- extend-module CLI command that clones, analyzes, creates companion dir, and handles spec file (REFN-03)
- odoo-extend agent with comprehensive 5-phase workflow: clone, gap analysis, delta code generation using _inherit and xpath, spec replacement, verification
- 21 new tests (all passing) covering clone args, branch support, error propagation, model extraction, field types, view detection, security groups, companion dir

## Task Commits

Each task was committed atomically:

1. **Task 1: Fork clone + module analyzer with TDD tests**
   - `9e613bd` (test: RED phase - failing tests for fork clone, module analyzer, companion dir)
   - `d32d6dd` (feat: GREEN phase - implement fork clone, module analyzer, companion dir setup)
2. **Task 2: extend-module CLI command, odoo-extend agent, activated extend.md**
   - `1537390` (feat: CLI command + agent + activated command)

_TDD Task 1 has RED (test) and GREEN (feat) commits_

## Files Created/Modified
- `python/src/odoo_gen_utils/search/fork.py` - Git sparse checkout clone and companion dir setup (88 lines)
- `python/src/odoo_gen_utils/search/analyzer.py` - AST model/field extraction, XML view parsing, security groups (273 lines)
- `python/tests/test_search_fork.py` - 21 tests for clone, analyze, companion dir, frozen dataclass (276 lines)
- `python/src/odoo_gen_utils/search/__init__.py` - Added exports: clone_oca_module, setup_companion_dir, analyze_module, ModuleAnalysis, format_analysis_text
- `python/src/odoo_gen_utils/cli.py` - Added extend-module Click command with --repo, --spec-file, --branch, --json
- `agents/odoo-extend.md` - 5-phase delta code generation agent (235 lines)
- `commands/extend.md` - Activated command wired to odoo-extend agent (replaced stub)

## Decisions Made
- `subprocess.run(check=True)` for all git commands -- CalledProcessError propagates naturally without re-wrapping
- AST-based field extraction uses `_ODOO_FIELD_TYPES` frozenset matching `fields.X()` call pattern
- XML ElementTree for view type detection -- parses arch content for known view tags (form, tree, search, kanban, etc.)
- Security group extraction scans both `res.groups` and `ir.module.category` records with "group" in ID
- Companion module naming uses `{original}_ext` suffix per Decision C
- Refined spec saved to both `{module}_ext/spec.json` AND overwrites original spec.json (REFN-03)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. The extend-module command requires git to be installed (standard system tool).

## Next Phase Readiness
- Phase 8 is now complete (all 3 plans: index, query, fork-extend)
- Full search + fork-extend pipeline available: build-index -> search-modules -> extend-module
- All agents operational: odoo-search (gap analysis), odoo-extend (delta code gen)
- All commands activated: /odoo-gen:index, /odoo-gen:search, /odoo-gen:extend
- Ready for Phase 9 (Edition & Version Support)
- No blockers for next phase

## Self-Check: PASSED

All 7 files verified present. All 3 commits verified in git log.

---
*Phase: 08-search-fork-extend*
*Completed: 2026-03-03*
