# Phase 14: Cleanup/Debug the Tech Debt - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the two auto-fix functions (`fix_missing_mail_thread` and `fix_unused_imports`) from Phase 12 into the CLI runtime so they execute during `validate --auto-fix`. Currently these functions are implemented and tested (15 tests) but have no caller outside tests.

Source: v1.2 Milestone Audit tech debt findings.

</domain>

<decisions>
## Implementation Decisions

### Docker Fix Dispatch
- Create a `run_docker_fix_loop()` function in `auto_fix.py` that mirrors the existing `run_pylint_fix_loop()` pattern
- The function takes a module path and Docker error output, calls `identify_docker_fix()` to detect the pattern, then dispatches to the appropriate fix function (`fix_missing_mail_thread` or `fix_unused_imports`)
- Follow the existing immutable read-transform-write pattern established in auto_fix.py

### CLI Integration
- Extend the `validate` command in `cli.py` to call the new Docker fix dispatch after Docker validation fails
- The `--auto-fix` flag should trigger both pylint fix loop AND Docker fix dispatch (not a separate flag)
- Import `run_docker_fix_loop` (or equivalent) alongside existing `run_pylint_fix_loop` import in cli.py

### Fix Scope
- `fix_missing_mail_thread`: called when Docker install fails with mail.thread-related errors — scans module XML for chatter indicators, adds `_inherit` line
- `fix_unused_imports`: called as a post-render cleanup step — scan all .py files in the module for unused imports (api, ValidationError, _)
- `fix_unused_imports` should also run during pylint fix loop when unused-import pylint violations are detected (not just Docker errors)

### Claude's Discretion
- Exact function signature for `run_docker_fix_loop` (whether it returns bool, count, or a result object)
- Whether to add a `--docker-fix` flag separate from `--auto-fix` or keep them combined
- Error handling and logging verbosity during fix dispatch
- Whether `fix_unused_imports` runs on all .py files or only models/*.py

</decisions>

<specifics>
## Specific Ideas

- The milestone audit identified exactly 2 orphaned exports: `fix_missing_mail_thread()` at line 447 and `fix_unused_imports()` at line 517 of auto_fix.py
- `identify_docker_fix()` at line 342 already recognizes "missing_mail_thread" pattern via `_DOCKER_PATTERN_KEYWORDS` — just needs a caller
- `FIXABLE_DOCKER_PATTERNS` already has 5 patterns including "missing_mail_thread" — the constant is ready, the dispatch is missing
- The validate command in cli.py (line 376+) already has `--auto-fix` flag that calls `run_pylint_fix_loop` — extend this path

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_pylint_fix_loop()` (auto_fix.py:297): Existing fix loop pattern — read violations, dispatch fixes, retry. Model for Docker fix loop.
- `identify_docker_fix()` (auto_fix.py:342): Already implemented, maps error text to fix pattern names. Just needs a caller.
- `fix_missing_mail_thread()` (auto_fix.py:447): Fully implemented and tested (6 tests). Scans XML views for chatter, adds _inherit line.
- `fix_unused_imports()` (auto_fix.py:517): Fully implemented and tested (5 tests). AST-based import analysis.
- `FIXABLE_DOCKER_PATTERNS` (auto_fix.py:37-43): frozenset with 5 patterns including "missing_mail_thread"

### Established Patterns
- Immutable read-transform-write: read file → create new content → compare → write if changed → return bool
- Fix loop with max iterations: `run_pylint_fix_loop` runs up to `max_cycles` (default 2), re-validates after each fix
- CLI imports from auto_fix: `from odoo_gen_utils.auto_fix import format_escalation, run_pylint_fix_loop`

### Integration Points
- `cli.py` line 12: import statement — add new function(s) here
- `cli.py` line 413: `if auto_fix:` block — extend to include Docker fix dispatch
- `auto_fix.py` line 297-340: `run_pylint_fix_loop` — pattern to follow for Docker fix loop

</code_context>

<deferred>
## Deferred Ideas

- General-purpose unused import analyzer (beyond template patterns) — v1.3+
- Auto-fix for computed field `@api.depends` missing dependencies — v1.3+
- Docker fix loop for all 5 FIXABLE_DOCKER_PATTERNS (not just missing_mail_thread) — future milestone

</deferred>

---

*Phase: 14-cleanup-debug-the-tech-debt*
*Context gathered: 2026-03-03*
