---
phase: 07-human-review-quality-loops
plan: 02
subsystem: workflows
tags: [checkpoints, human-review, i18n, regeneration, generate-workflow]
dependency_graph:
  requires: []
  provides:
    - "generate.md with 3 human review checkpoints (CP-1, CP-2, CP-3)"
    - "i18n extraction step (Step 3.5) in generation pipeline"
    - "Regeneration logic with max 3 retries per checkpoint"
    - "Diff-based review via difflib.unified_diff on regeneration"
  affects:
    - "workflows/generate.md"
tech_stack:
  added: []
  patterns:
    - "Prose markdown checkpoints (not PLAN.md XML) for agent-readable workflow"
    - "Stage+downstream regeneration scope (CP-1=full, CP-2=Wave1+2, CP-3=Wave2)"
    - "Structured summary on first review pass, unified diff on regeneration"
key_files:
  modified:
    - "workflows/generate.md"
decisions:
  - "REVW-05 handled by existing GSD auto_advance config -- no new code, noted in workflow"
  - "Checkpoints written as prose markdown sections for agent consumption"
  - "Max 3 retry limit per checkpoint with graceful escalation message"
  - "i18n extraction is non-blocking -- failure does not prevent commit"
metrics:
  duration: "4 min"
  completed: "2026-03-02T20:25:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 7 Plan 2: Wire Human Review Checkpoints into generate.md Summary

Three human review checkpoints (CP-1: models/security after Jinja2, CP-2: business logic after Wave 1, CP-3: views/tests after Wave 2) with per-checkpoint retry limits, diff-based regeneration review, and i18n extraction step.

## What Was Done

### Task 1: Rewrite generate.md with checkpoints and i18n step

Rewrote the entire `workflows/generate.md` to add:

- **CP-1 (after Step 1):** Reviews generated models, security files, and structural output. Presents structured summary with file list, key decisions (state fields, computed fields, sequence fields, multi-company, security groups, ACLs). Rejection triggers full restart (Step 1 + Wave 1 + Wave 2).

- **CP-2 (after Step 2):** Reviews business logic from `odoo-model-gen`. Presents computed field methods, onchange handlers, constraint methods, TODO stub counts. Rejection re-runs Wave 1 for affected models + all of Wave 2.

- **CP-3 (after Step 3):** Reviews view enrichments and test generation. Presents workflow buttons added and test categories present. Rejection re-runs Wave 2 only.

- **Step 3.5 (i18n extraction):** Calls `odoo-gen-utils extract-i18n "$OUTPUT_DIR/$MODULE_NAME" "$MODULE_NAME"` after all checkpoints pass and before git commit. Non-blocking on failure.

- **Regeneration logic:** Each checkpoint tracks `$RETRY_COUNT` (initialized to 0, max 3). On first pass, user sees structured summary. On regeneration, user sees `difflib.unified_diff` of changed files only. After 3 retries, escalation message printed and pipeline continues.

- **REVW-05 note:** Documented that skippable checkpoints are handled by GSD's existing `workflow.auto_advance = true` config. No new skip logic added.

### Task 2: Verify workflow structure and cross-references

Verified all 6 plan verification criteria:
1. 3 checkpoint sections present (Checkpoint 1, 2, 3) at correct positions
2. `extract-i18n` CLI invocation in Step 3.5
3. `difflib.unified_diff` referenced in all 3 checkpoint regeneration handlers
4. `$RETRY_COUNT` tracking with max 3 in all checkpoints
5. Escalation messages present for all 3 checkpoints
6. Top-to-bottom order: Step 1 -> CP-1 -> Step 2 -> CP-2 -> Step 3 -> CP-3 -> Step 3.5 -> Step 4 -> Step 5

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | ff6d3a2 | feat(07-02): rewrite generate.md with 3 human review checkpoints and i18n step |
| 2 | (no changes) | Verification only -- all checks passed |

## Requirements Satisfied

| Requirement | How |
|-------------|-----|
| REVW-01 | CP-1 pauses after model generation for human review |
| REVW-02 | CP-3 pauses after view generation for human review |
| REVW-03 | CP-1 includes security review (security files generated in same Jinja2 pass) |
| REVW-04 | CP-2 pauses after business logic generation for human review |
| REVW-05 | Noted in workflow -- GSD auto_advance handles skip; no new code needed |
| REVW-06 | Regeneration with feedback: agent re-invoked with spec + file + feedback; difflib.unified_diff shows changes |

## Deviations from Plan

None -- plan executed exactly as written.

## Key Files

- `/home/inshal-rauf/Odoo_module_automation/workflows/generate.md` -- complete generation workflow with 3 checkpoints, i18n step, and regeneration logic

## Self-Check: PASSED

- workflows/generate.md: FOUND
- 07-02-SUMMARY.md: FOUND
- Commit ff6d3a2: FOUND
