---
phase: 07-human-review-quality-loops
created: 2026-03-03T00:00:00Z
status: context-captured
---

# Phase 7: Human Review & Quality Loops - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire GSD checkpoints into each Odoo generation stage so that users can review, approve, request changes, or reject at three natural pause points. When sections are rejected, the system regenerates only the affected stage and its downstream. After full generation, a static i18n `.pot` file is extracted. When validation (pylint-odoo or Docker) finds issues, auto-fix is attempted before escalating remaining violations to the user.

**Depends on:** Phase 5 (generate.md pipeline), Phase 6 (security + test generation)
**Requirements in scope:** REVW-01, REVW-02, REVW-03, REVW-04, REVW-05, REVW-06, QUAL-06, QUAL-09, QUAL-10

</domain>

<decisions>
## Implementation Decisions

### A — Checkpoint Placement (REVW-01, REVW-02, REVW-03, REVW-04)

**Three checkpoints added to generate.md:**

| # | When | What is reviewed | Requirement |
|---|------|-----------------|-------------|
| CP-1 | After Step 1 (Jinja2 render) | Models + security + test stubs | REVW-01, REVW-03 |
| CP-2 | After Step 2 (Wave 1 model-gen) | Business logic (computed, onchange, constraints) | REVW-04 |
| CP-3 | After Step 3 (Wave 2 view+test-gen) | Views (form/tree/search) + enriched tests | REVW-02 |

Security review is merged into CP-1 because security files are generated in the same Jinja2 pass. No fourth checkpoint for security alone.

**Checkpoint mechanism:** Prose instruction sections in generate.md (not PLAN.md XML). The orchestrating agent (which reads generate.md) presents the review box and waits for explicit user response. GSD `type="checkpoint:human-verify"` XML syntax is for PLAN.md only — generate.md uses agent-readable markdown.

**REVW-05 (skippable checkpoints):** Already built into GSD — `workflow.auto_advance = true` in `.planning/config.json` causes all checkpoint:human-verify to auto-approve. No new code needed. Checkpoints are inserted normally; the skip behavior is GSD's existing mechanism.

---

### B — Review Presentation (REVW-01, REVW-02, REVW-06)

**First review at a checkpoint (no prior version):**
Show a structured summary:
- What was generated (file list by category: models, views, security, tests)
- Key detected decisions: state fields, computed fields, sequence fields, company_id models
- Generated security groups and ACL summary
- Prompt: "Review the generated files above. Type 'approved' to continue, or describe what to change."

**After regeneration (diff view — REVW-06):**
Show a unified diff of changed files only using Python `difflib.unified_diff`.
- Do NOT show unchanged files
- Limit diff output to changed files only (not the entire module)
- Prompt: "Here's what changed. Type 'approved' to continue, or describe further changes."

**Rationale:** No diff on first pass (nothing to compare against). Diff only when there's a prior version to compare. This naturally satisfies REVW-06 without noise.

---

### C — Regeneration Granularity (REVW-03, REVW-04)

**Stage + downstream rule:**

| Rejected at | What reruns |
|-------------|-------------|
| CP-1 (Jinja2 render) | Full restart — re-run render-module + Wave 1 + Wave 2 (everything depends on structural files) |
| CP-2 (Wave 1 model-gen) | Wave 1 only + Wave 2 (views read completed model files) |
| CP-3 (Wave 2 view+test-gen) | Wave 2 only (view-gen and test-gen are independent of each other; re-run both) |

**Feedback injection:** On rejection, the orchestrating agent re-invokes the relevant stage agent(s) with: original spec + original generated file content + user's feedback text. Agent rewrites the ENTIRE file (not patches).

**Max retry limit (REVW-04):** 3 regeneration attempts per stage. After 3 rejections at the same checkpoint, escalate with message: "Maximum regeneration attempts reached. Proceeding to next stage. You can manually edit the files or run the relevant agent again."

---

### D — i18n .pot Generation (QUAL-06)

**Timing:** End of pipeline — after Wave 2 completes, before the git commit (new Step 3.5 in generate.md).

**Method:** Static extraction only. No live Odoo server required.
- Python files: `ast.parse()` scan for `_("...")` calls
- XML files: `xml.etree.ElementTree` scan for `string=` attributes and label text
- Known limitation: field `string=` auto-translations (e.g., `fields.Char(string="My Field")`) are NOT extracted by static analysis — documented as a known gap, acceptable for v1

**Output location:** `$MODULE_NAME/i18n/$MODULE_NAME.pot`

**If no translatable strings found:** Generate the standard POT header anyway (Odoo expects this file to exist). Never skip generation.

**POT header format:**
```
# Translation of $MODULE_NAME.pot in English
# This file contains the translation of the following modules:
# * $MODULE_NAME
msgid ""
msgstr ""
"Project-Id-Version: Odoo Server 17.0\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: $TIMESTAMP\n"
"PO-Revision-Date: \n"
"Last-Translator: \n"
"Language-Team: \n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: \n"
"Plural-Forms: \n"
```

---

### E — Auto-fix Escalation (QUAL-09, QUAL-10)

**pylint-odoo auto-fix (QUAL-09):**

Mechanically auto-fixable violation codes (verified from OCA/pylint-odoo README):
- `W8113` — redundant `string=` parameter on field
- `W8111` — renamed field parameter
- `C8116` — superfluous manifest key
- `W8150` — absolute import should be relative
- `C8107` — missing `required` in manifest key

All other violations → NOT auto-fixable, escalate immediately.

**Max attempts:** 2 auto-fix + re-validate cycles. If violations remain after 2 attempts, escalate.

**Escalation presentation:**
```
Auto-fix exhausted. Remaining violations:

[manifest.py] C8101: Missing key `author` in manifest
  → Add `"author": "Your Name"` to __manifest__.py

[models/sale_order.py:42] E8103: Model _description missing
  → Add `_description = "Sales Order"` to the model class

Run /odoo-gen:validate to re-check after manual fixes.
```
Grouped by file, one fix suggestion per violation, file:line reference. No agent auto-spawned — user decides whether to call odoo-validator/odoo-security-gen manually.

**Docker failure auto-fix (QUAL-10):**

Auto-fixable patterns (from existing `error_patterns.json` infrastructure):
- `xml_parse_error` → check for unclosed tags, fix XML syntax
- `missing_acl` → regenerate `ir.model.access.csv` via access_csv.j2 template
- `missing_import` → add missing Python import to the relevant model file
- `manifest_load_order` → reorder `data` list in `__manifest__.py`

All other Docker failures (logic errors, test assertion failures, missing business logic) → NOT auto-fixable, escalate immediately.

**Max attempts:** 2 Docker auto-fix cycles (Docker runs take 2-5 min each; 3+ would be too slow).

**Escalation presentation:**
```
Docker validation failed after 2 fix attempts. Remaining issues:

INSTALL FAILED:
  Module test_order failed to install.
  Error: ir.model.access.csv: model test.order not found
  → Check that model _name matches access CSV model column

TEST FAILURES:
  tests/test_order.py::TestOrder::test_create: FAIL
  AssertionError: False is not true
  → Review test_create in tests/test_order.py — may need spec adjustment

Run /odoo-gen:validate for full details.
```

</decisions>

<specifics>
## Specific Ideas

- User approved all recommendations without modification — no specific "I want it like X" preferences
- Keep checkpoint messages concise — users are reviewing generated code, not reading documentation

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `odoo-gen-utils validate` CLI: already parses pylint-odoo output into structured `ValidationResult` objects — reuse for auto-fix input
- `error_patterns.json`: Docker failure pattern taxonomy already exists in Phase 3 — use as auto-fix trigger map
- `difflib` (Python stdlib): use `unified_diff()` for REVW-06 diff generation — no new dependency
- `ast` + `xml.etree.ElementTree` (Python stdlib): use for i18n static extraction — no new dependency
- `access_csv.j2` template: reusable for ACL regeneration on `missing_acl` Docker failure

### Established Patterns
- generate.md workflow: prose instruction sections (not PLAN.md XML) — checkpoints must be written as markdown prose, not `<task type="checkpoint:human-verify">`
- Agent full-file rewrite: all existing agents (odoo-model-gen, odoo-view-gen, odoo-test-gen) rewrite entire files — use same pattern for regeneration
- `workflow.auto_advance` in config.json: already handles REVW-05 skip — no new code

### Integration Points
- `workflows/generate.md`: 3 checkpoint sections added (after Step 1, after Step 2, after Step 3)
- `python/src/odoo_gen_utils/`: new `i18n_extractor.py` module for static .pot generation
- `python/src/odoo_gen_utils/renderer.py`: `render_module()` extended to call i18n extractor
- `odoo-gen-utils` CLI: new `extract-i18n` command (or add to `render-module` output)

</code_context>

<deferred>
## Deferred Ideas

- `click-odoo-makepot` integration (requires live Odoo DB) — Phase 9 or post-v1
- Field `string=` auto-translation extraction — requires running Odoo; Phase 9
- Manager-specific access rights tests — Phase 8 (per Phase 6 scope boundary)
- Kanban view generation — Phase 7 per generate.md Decision F note, but actually deferred to Phase 8
- Per-model regeneration granularity (user picks which model files to redo) — Phase 8
- Portal user access tests — Phase 8

</deferred>

---

*Phase: 07-human-review-quality-loops*
*Context gathered: 2026-03-03*
