---
phase: 07-human-review-quality-loops
plan: 01
subsystem: i18n
tags: [i18n, pot, ast, xml, static-analysis, tdd, cli, odoo-17]

# Dependency graph
requires:
  - phase: 05-core-code-generation
    provides: render_module() produces .py and .xml files with _() calls and string= attributes

provides:
  - extract_python_strings() via ast.parse() for _() call extraction
  - extract_xml_strings() via xml.etree.ElementTree for string= attribute and label text extraction
  - extract_translatable_strings() recursive directory scanner combining .py and .xml
  - generate_pot() POT file generation with Odoo 17.0 header, deduplication, source references
  - extract-i18n CLI command writing MODULE_NAME.pot to i18n/ directory

affects:
  - 07-02-PLAN (generate.md will call extract-i18n as Step 3.5 after Wave 2)
  - 07-03-PLAN (auto-fix may reference i18n extraction for validation loops)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ast.parse() walker pattern: walk AST for Call nodes with Name(id='_') func"
    - "ElementTree scan pattern: iter() all elements for string attribute + label tag text"
    - "POT deduplication: dict-based msgid merging of source references"
    - "Immutable list building: [*existing, *new] spread instead of .extend() mutation"

key-files:
  created:
    - python/src/odoo_gen_utils/i18n_extractor.py
    - python/tests/test_i18n_extractor.py
  modified:
    - python/src/odoo_gen_utils/cli.py

key-decisions:
  - "Static extraction only (no live Odoo server) using ast + xml.etree.ElementTree stdlib modules"
  - "ElementTree line numbers unreliable -- use 0 for all XML entries"
  - "Always generate POT header even when no strings found (per CONTEXT.md Decision D)"
  - "Known gap: field string= auto-translations from Python field declarations not extracted (v1 acceptable)"

requirements-completed:
  - QUAL-06

# Metrics
duration: 5min
completed: 2026-03-02
---

# Phase 7 Plan 01: i18n Static Extractor and extract-i18n CLI Command Summary

**Static i18n .pot extraction via ast.parse() for Python _() calls and xml.etree.ElementTree for XML string= attributes, with extract-i18n CLI command writing Odoo 17.0-format POT files**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-02T20:20:33Z
- **Completed:** 2026-03-02T20:25:54Z
- **Tasks:** 2/2 (Task 1 TDD: RED+GREEN, Task 2 CLI wiring)
- **Files created:** 2 (i18n_extractor.py, test_i18n_extractor.py)
- **Files modified:** 1 (cli.py)

## Accomplishments

- Created `i18n_extractor.py` with 4 exported functions: `extract_python_strings`, `extract_xml_strings`, `extract_translatable_strings`, `generate_pot`
- `extract_python_strings()` uses `ast.parse()` to walk AST for `ast.Call` nodes where `func` is `ast.Name(id='_')` and extracts the first string `ast.Constant` argument
- `extract_xml_strings()` uses `xml.etree.ElementTree.parse()` to scan all elements for `string` attributes and `<label>` elements for text content; handles malformed XML gracefully
- `extract_translatable_strings()` recursively walks a module directory, calling the appropriate extractor for each `.py` and `.xml` file, returning a sorted combined list
- `generate_pot()` produces a valid POT file with standard Odoo 17.0 header (`Project-Id-Version: Odoo Server 17.0`), deduplicates identical msgids by merging source references, and always generates the header even when no strings found
- Wired `extract-i18n` CLI command to the `main` Click group: takes `MODULE_PATH`, writes `MODULE_NAME.pot` to `MODULE_PATH/i18n/`
- 17 new tests in `test_i18n_extractor.py` covering Python extraction (5 tests), XML extraction (5 tests), directory scanning (1 test), and POT generation (6 tests)
- All 147 tests pass (130 existing + 17 new), zero regressions

## Task Commits

1. **Task 1 RED: Write failing tests** - `6d7a331` (test)
2. **Task 1 GREEN: Implement i18n extractor module** - `8fb198f` (feat)
3. **Task 2: Wire extract-i18n CLI command** - `f90489a` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `python/src/odoo_gen_utils/i18n_extractor.py` - New module with 4 functions: `extract_python_strings` (ast-based _() extraction), `extract_xml_strings` (ElementTree-based string= and label extraction), `extract_translatable_strings` (recursive directory scanner), `generate_pot` (POT file generation with Odoo 17.0 header and deduplication)
- `python/tests/test_i18n_extractor.py` - 17 test cases organized in 5 test classes: `TestExtractPythonStrings` (5), `TestExtractXmlStrings` (5), `TestExtractTranslatableStrings` (1), `TestGeneratePot` (6)
- `python/src/odoo_gen_utils/cli.py` - Added `extract-i18n` Click command and `from odoo_gen_utils.i18n_extractor import` statement

## Decisions Made

- **Static extraction only**: Using Python stdlib `ast` and `xml.etree.ElementTree` -- no new dependencies, no live Odoo server required
- **Line number 0 for XML**: ElementTree does not reliably track line numbers, so all XML entries use line 0 in source references
- **Always generate POT header**: Even when no translatable strings are found, the POT file is generated with the standard Odoo 17.0 header (Odoo expects this file to exist)
- **Known gap accepted**: Python field declarations like `fields.Char(string="My Field")` are NOT extracted -- this requires runtime Odoo introspection, deferred to Phase 9

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

- Phase 07-01 complete: i18n extractor module and CLI command working
- Phase 07-02 can proceed: generate.md checkpoint wiring will call extract-i18n as Step 3.5
- Phase 07-03 can proceed: auto-fix loops are independent of i18n extraction
- 147/147 tests passing, zero regressions

---
*Phase: 07-human-review-quality-loops*
*Completed: 2026-03-02*
