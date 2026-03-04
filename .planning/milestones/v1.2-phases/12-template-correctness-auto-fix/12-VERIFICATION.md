---
phase: 12-template-correctness-auto-fix
status: passed
score: 9/9
verified: 2026-03-03
---

# Phase 12: Template Correctness & Auto-Fix - Verification

## Phase Goal
Generated modules produce correct Python code out of the box -- proper inheritance, minimal imports, clean manifests -- and auto-fix catches any remaining structural issues.

## Must-Haves Verification

### Plan 12-01: Template Bug Fixes

| # | Must-Have | Status | Evidence |
|---|----------|--------|----------|
| 1 | A spec with 'mail' in depends renders model.py containing _inherit = ['mail.thread', 'mail.activity.mixin'] | VERIFIED | renderer.py:212-221 computes inherit_list; both 17.0/18.0 model.py.j2 use inherit_list loop |
| 2 | A spec with no @api.* decorators renders model.py that does NOT import api from odoo | VERIFIED | renderer.py adds needs_api flag; templates use conditional api import |
| 3 | A spec with @api.depends renders model.py that DOES import api from odoo | VERIFIED | needs_api = bool(computed_fields or onchange_fields or constrained_fields or sequence_fields) |
| 4 | Rendered __manifest__.py contains no installable or auto_install keys | VERIFIED | manifest.py.j2 has no installable or auto_install lines |
| 5 | Rendered test files do not import ValidationError unless the test actually uses it | VERIFIED | test_model.py.j2 imports only AccessError |

### Plan 12-02: Auto-Fix + Knowledge Base

| # | Must-Have | Status | Evidence |
|---|----------|--------|----------|
| 6 | Auto-fix detects missing mail.thread when chatter XML exists and adds _inherit line | VERIFIED | auto_fix.py fix_missing_mail_thread() scans XML for oe_chatter/chatter/message_ids |
| 7 | Auto-fix detects and removes unused imports (ValidationError, api) | VERIFIED | auto_fix.py fix_unused_imports() uses ast.parse |
| 8 | Knowledge base documents when _inherit mail.thread is required | VERIFIED | knowledge/models.md new section |
| 9 | Knowledge base documents the triple dependency | VERIFIED | knowledge/models.md Triple Dependency subsection |

## Requirement Coverage

| Requirement | Plan | Status |
|-------------|------|--------|
| TMPL-01 | 12-01 | Verified |
| TMPL-02 | 12-01 | Verified |
| TMPL-03 | 12-01 | Verified |
| TMPL-04 | 12-01 | Verified |
| AFIX-01 | 12-02 | Verified |
| AFIX-02 | 12-02 | Verified |
| KNOW-01 | 12-02 | Verified |
| KNOW-02 | 12-02 | Verified |

All 8 requirements verified.

## Test Results

- test_renderer.py: 76 tests (25 new Phase 12)
- test_auto_fix.py: 37 tests (15 new Phase 12)
- Full suite: 303 passed, 0 failures

---
*Verified: 2026-03-03*
