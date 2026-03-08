---
phase: 60-iterative-refinement
plan: 01
subsystem: iterative-refinement
tags: [deepdiff, spec-diff, conflict-detection, stub-merge, frozen-dataclass]

# Dependency graph
requires:
  - phase: 56-logic-writer-core
    provides: stub_detector._find_stub_zones() for zone detection
  - phase: 54-manifest
    provides: GenerationManifest, compute_file_sha256, compute_spec_sha256
provides:
  - Spec stash management (save/load .odoo-gen-spec.json)
  - Spec diff orchestration with SHA256 gate
  - Diff-to-stage mapping for 10 change categories
  - Three-way conflict detection (manifest vs current vs skeleton)
  - Stub-zone-aware merge with position-independent method matching
affects: [60-02-iterative-cli, renderer-iterative-mode]

# Tech tracking
tech-stack:
  added: []
  patterns: [outside-zone-comparison, method-name-matching-merge]

key-files:
  created:
    - python/src/odoo_gen_utils/iterative/__init__.py
    - python/src/odoo_gen_utils/iterative/diff.py
    - python/src/odoo_gen_utils/iterative/affected.py
    - python/src/odoo_gen_utils/iterative/conflict.py
    - python/src/odoo_gen_utils/iterative/merge.py
    - python/tests/test_iterative_diff.py
    - python/tests/test_iterative_affected.py
    - python/tests/test_iterative_conflict.py
    - python/tests/test_iterative_merge.py
    - python/tests/fixtures/spec_v1_iterative.json
    - python/tests/fixtures/spec_v2_field_added.json
    - python/tests/fixtures/spec_v2_model_added.json
  modified: []

key-decisions:
  - "FIELD_ADDED includes security stage unconditionally (false positives safe, false negatives not)"
  - "determine_affected_stages accepts optional old/new specs for detecting view_hints changes not tracked by spec_differ"
  - "Outside-zone line comparison for stub-zone detection (handles line count changes within zones)"
  - "extract_filled_stubs skips zones with only pass or TODO comments"
  - "inject_stubs_into matches by method name, not position, for resilience to structural changes"

patterns-established:
  - "Outside-zone comparison: extract lines outside BUSINESS LOGIC zones, compare sequences (avoids line-shift false positives)"
  - "Method-name matching for stub transplant: scan backward from zone to find def line, match by name across files"

requirements-completed: [ITER-01, ITER-03]

# Metrics
duration: 12min
completed: 2026-03-09
---

# Phase 60 Plan 01: Iterative Refinement Core Logic Summary

**Spec stash, diff-to-stage mapping, three-way conflict detection, and stub-zone-aware merge as pure-function iterative subpackage**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-08T23:42:28Z
- **Completed:** 2026-03-08T23:55:08Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Created iterative/ subpackage with 5 modules: diff.py, affected.py, conflict.py, merge.py, __init__.py
- Mapped all 10 diff categories to correct pipeline stage sets with union semantics
- Three-way conflict detection using outside-zone comparison pattern for accurate stub-only edit detection
- Position-independent method-name matching for stub-zone merge survives file restructuring
- 45 tests covering all categories, edge cases, and round-trip scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1: Spec stash + diff-to-stage mapping** (TDD)
   - `0553ce1` (test: add failing tests for spec stash, diff, affected stages)
   - `163b84a` (feat: implement spec stash, diff orchestration, affected-stage mapping)

2. **Task 2: Conflict detection + stub-zone merge** (TDD)
   - `a52412d` (test: add failing tests for conflict detection and stub-zone merge)
   - `c25999a` (feat: implement conflict detection and stub-zone merge)

## Files Created/Modified
- `python/src/odoo_gen_utils/iterative/__init__.py` - Public API re-exports (9 symbols)
- `python/src/odoo_gen_utils/iterative/diff.py` - Spec stash save/load + SHA256-gated diff orchestration
- `python/src/odoo_gen_utils/iterative/affected.py` - AffectedStages frozen dataclass + 10 diff category-to-stage mapping
- `python/src/odoo_gen_utils/iterative/conflict.py` - ConflictResult frozen dataclass + three-way conflict detection
- `python/src/odoo_gen_utils/iterative/merge.py` - extract_filled_stubs + inject_stubs_into with method-name matching
- `python/tests/test_iterative_diff.py` - 10 tests for stash and diff
- `python/tests/test_iterative_affected.py` - 15 tests for all diff categories + union + empty + summary
- `python/tests/test_iterative_conflict.py` - 9 tests for safe/conflict/mergeable classification
- `python/tests/test_iterative_merge.py` - 11 tests for extract, inject, round-trip
- `python/tests/fixtures/spec_v1_iterative.json` - Minimal spec with 1 model + 3 fields
- `python/tests/fixtures/spec_v2_field_added.json` - v1 + discount Float field added
- `python/tests/fixtures/spec_v2_model_added.json` - v1 + fee.scholarship model added

## Decisions Made
- FIELD_ADDED always includes security stage (false positives safe; per CONTEXT.md note about conditional groups= check simplified)
- determine_affected_stages accepts optional old_spec/new_spec for detecting view_hints changes that spec_differ does not track
- Outside-zone comparison pattern for stub-zone detection (same approach as E16 validation, handles line count changes)
- Unfilled detection: zones with only pass or TODO/FIXME/XXX comments are skipped by extract_filled_stubs
- Method-name matching scans backward up to 10 lines from START marker to find the def line

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stub-zone comparison for variable-length edits**
- **Found during:** Task 2 (conflict detection)
- **Issue:** Initial line-by-line comparison broke when user added lines inside a zone (line indices shift)
- **Fix:** Switched to outside-zone extraction pattern: extract lines outside zones, compare sequences
- **Files modified:** python/src/odoo_gen_utils/iterative/conflict.py
- **Verification:** test_file_edited_only_in_stubs passes
- **Committed in:** c25999a (part of Task 2 commit)

**2. [Rule 2 - Missing Critical] Added view_hints detection via raw spec comparison**
- **Found during:** Task 1 (affected stages)
- **Issue:** spec_differ.diff_specs() does not track model-level attributes like view_hints
- **Fix:** determine_affected_stages accepts optional old_spec/new_spec and compares view_hints/view_extensions directly
- **Files modified:** python/src/odoo_gen_utils/iterative/affected.py
- **Verification:** test_view_hint_changed_stages passes with old/new spec parameters
- **Committed in:** 163b84a (part of Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both fixes necessary for correctness. No scope creep. API slightly extended with optional parameters.

## Issues Encountered
None -- plan executed with two minor deviations handled inline.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Iterative subpackage complete with clean public API via __init__.py
- Ready for Plan 02: CLI integration (--force, --dry-run, resolve command) and renderer integration
- All pure-logic modules decoupled from renderer/CLI as specified

---
*Phase: 60-iterative-refinement*
*Completed: 2026-03-09*
