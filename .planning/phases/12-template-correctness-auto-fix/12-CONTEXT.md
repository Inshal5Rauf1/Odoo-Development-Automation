# Phase 12: Template Correctness & Auto-Fix - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 4 Jinja2 template bugs that prevent generated modules from installing in Odoo, expand auto-fix to handle structural issues (missing mail.thread inheritance, unused imports), and update knowledge base with mail.thread/mixin inheritance rules.

Requirements: TMPL-01..04, AFIX-01..02, KNOW-01..02 (8 of 10 v1.2 requirements).

</domain>

<decisions>
## Implementation Decisions

### mail.thread Inheritance (TMPL-01)
- Fix in BOTH renderer context building AND template logic
- `_build_model_context()` in renderer.py builds an `inherit_list` from:
  1. Explicit `model.get("inherit")` (existing behavior)
  2. Auto-detection: if `'mail' in spec.get("depends", [])`, add `mail.thread` and `mail.activity.mixin`
- Template receives `inherit_list` (list of strings) instead of single `inherit` (string or None)
- Template renders `_inherit = [...]` from the list
- Both 17.0 and 18.0 model.py.j2 get this fix (currently identical)

### Conditional api Import (TMPL-02)
- Template checks whether `@api.*` decorators are used before importing `api`
- Context already has `computed_fields`, `onchange_fields`, `constrained_fields`, `sequence_fields`
- Add a convenience flag `needs_api` to model context: `bool(computed_fields or onchange_fields or constrained_fields)`
- Template: `from odoo import {{ 'api, ' if needs_api }}fields, models`
- Both 17.0 and 18.0 templates

### Superfluous Manifest Keys (TMPL-03)
- Remove `"installable": True` and `"auto_install": False` from manifest.py.j2
- These are Odoo defaults — emitting them triggers pylint-odoo C8116
- Simple template deletion — no context changes needed

### Unused Test Import (TMPL-04)
- Remove `ValidationError` from the import line in test_model.py.j2
- Keep `AccessError` (used in `test_no_group_cannot_create`)
- Change: `from odoo.exceptions import AccessError, ValidationError` → `from odoo.exceptions import AccessError`
- If future templates need ValidationError, add it conditionally (not in Phase 12 scope)

### Auto-Fix: Missing mail.thread (AFIX-01)
- New auto-fix function detects when chatter XML references exist but model lacks `_inherit = ['mail.thread', ...]`
- Detection: scan rendered XML files for `oe_chatter` div (17.0) or `<chatter/>` (18.0) or `message_follower_ids`/`message_ids` field references
- Fix: parse model.py, add `_inherit = ['mail.thread', 'mail.activity.mixin']` line after `_description`
- Add to FIXABLE_DOCKER_PATTERNS as `missing_mail_thread`
- Hook into validation pipeline alongside existing docker auto-fix

### Auto-Fix: Unused Imports (AFIX-02)
- New auto-fix function detects and removes unused imports in generated Python files
- Detection: parse file with `ast` module, collect import names, scan for usage in function/class bodies
- Focus on common cases: unused `ValidationError`, unused `api`, unused `_`
- Not a full unused-import analyzer — targeted at known template patterns
- Add to auto-fix pipeline as a post-render cleanup step

### Knowledge Base Updates (KNOW-01, KNOW-02)
- Update `knowledge/models.md` with a new section: "mail.thread and mail.activity.mixin"
- Document: when to add (mail in depends), what to inherit, relationship to chatter XML
- Document: the triple dependency (mail in depends → model inherits mail.thread → view has chatter)
- Human-readable for agents — agents read knowledge files to generate correct code

### Claude's Discretion
- Exact regex/AST patterns for auto-fix detection
- Whether to add `needs_api` as a renderer context key or compute inline in template
- Test file organization (new test class vs extending existing)
- Order of operations within auto-fix pipeline
- Knowledge base section placement and length

</decisions>

<specifics>
## Specific Ideas

- The triple dependency is the key insight: `mail` in depends + `mail.thread` inheritance + chatter XML must all be consistent. Templates currently handle view side (chatter XML) but not model side (inheritance).
- Auto-fix should work on generated modules AND existing modules passed to `validate` command — not limited to just-generated code.
- Keep auto-fix focused on known template patterns — a full Python linter is out of scope.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_build_model_context()` (renderer.py:157-246): Already builds per-model context with fields, computed/onchange/constrained lists — extend with `inherit_list` and `needs_api`
- `auto_fix.py` (392 lines): Has `FIXABLE_PYLINT_CODES`, `FIXABLE_DOCKER_PATTERNS`, dispatch functions, fix loop — extend with new patterns
- `validation/error_patterns.json` (60+ patterns): Error diagnosis library — add `missing_mail_thread` pattern
- `knowledge/models.md` (545 lines): Has inheritance section at lines 379-414 — extend with mail.thread specifics

### Established Patterns
- Frozen dataclasses for all types (Violation, InstallResult, TestResult)
- Immutable auto-fix pattern: read file → create new content → write back
- Template context vars passed as dict to Jinja2 render
- Version-aware template loader: `templates/{version}/` falls back to `templates/shared/`
- Per-model context building in renderer (called once per model in spec)

### Integration Points
- `render_module()` (renderer.py:313-597) calls `_build_model_context()` at line 428 — context changes flow through automatically
- `run_pylint_fix_loop()` (auto_fix.py:293-330) orchestrates fix cycles — new fixes plug into `fix_pylint_violation()` dispatch
- `identify_docker_fix()` (auto_fix.py:338-356) matches error patterns — add `missing_mail_thread` to keyword dict
- Template files loaded via Jinja2 `FileSystemLoader` with `StrictUndefined` — new context vars must always be provided

</code_context>

<deferred>
## Deferred Ideas

- Odoo 18.0 Docker validation — Phase 13 or later (17.0 first)
- Full unused-import analyzer (not just template patterns) — v1.3+
- Template linting tool that validates output against Odoo schema — v1.3+
- Auto-fix for computed field `@api.depends` missing dependencies — v1.3+

</deferred>

---

*Phase: 12-template-correctness-auto-fix*
*Context gathered: 2026-03-03*
