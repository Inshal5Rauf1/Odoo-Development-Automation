---
phase: 35-template-bug-fixes-tech-debt
verified: 2026-03-06T12:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 35: Template Bug Fixes & Tech Debt Verification Report

**Phase Goal:** Fix critical template bugs and tech debt discovered during v3.1 milestone audit
**Verified:** 2026-03-06
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A spec with archival:true AND a state Selection field renders without StrictUndefined error | VERIFIED | `wizard.get('trigger_state')` guard at line 20 of both 17.0 and 18.0 `view_form.xml.j2`; test `test_archival_with_state_field_no_crash` passes |
| 2 | A spec with cron_jobs containing doall:true generates doall eval=True in cron XML | VERIFIED | `cron.get('doall', false)` ternary at line 13 of `cron_data.xml.j2`; test `test_cron_doall_from_spec_true` passes |
| 3 | Existing wizard+state combos (with trigger_state) still render the invisible attribute correctly | VERIFIED | Test `test_archival_with_state_and_regular_wizard` asserts `invisible="state != 'draft'"` present for regular wizard button; passes |
| 4 | Existing cron specs without explicit doall still default to False | VERIFIED | Test `test_cron_doall_default_false` asserts `eval="False"` on doall field line; passes |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2` | Guarded wizard.trigger_state access | VERIFIED | Line 20: `{% if wizard.get('trigger_state') %}` guard with else branch for no-trigger-state wizards |
| `python/src/odoo_gen_utils/templates/18.0/view_form.xml.j2` | Guarded wizard.trigger_state access | VERIFIED | Line 20: identical guard as 17.0 version |
| `python/src/odoo_gen_utils/templates/shared/cron_data.xml.j2` | Dynamic doall rendering from spec | VERIFIED | Line 13: `eval="{{ 'True' if cron.get('doall', false) else 'False' }}"` |
| `python/tests/test_render_stages.py` | Regression tests for archival+state and cron doall | VERIFIED | 4 new tests in `TestRenderModelsArchival` class (lines 1963-2081): `test_archival_with_state_field_no_crash`, `test_archival_with_state_and_regular_wizard`, `test_cron_doall_from_spec_true`, `test_cron_doall_default_false` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `17.0/view_form.xml.j2` | wizard dict from _process_production_patterns() | `wizard.get('trigger_state')` guard | WIRED | Line 20 uses `wizard.get('trigger_state')` -- safely handles both archival wizards (no trigger_state) and regular wizards (with trigger_state) |
| `18.0/view_form.xml.j2` | wizard dict from _process_production_patterns() | `wizard.get('trigger_state')` guard | WIRED | Identical implementation to 17.0 |
| `shared/cron_data.xml.j2` | cron dict from spec | `cron.get('doall', false)` with ternary | WIRED | Line 13 reads doall from cron dict with False default, renders Python-eval-compatible True/False string |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PERF-04 | 35-01-PLAN | Models with archival:true generate active field, archival wizard, and ir.cron for periodic archival | SATISFIED | The template crash that prevented archival+state combos from rendering is fixed; 2 regression tests confirm |
| TMPL-05 | 35-01-PLAN | Generator produces ir.cron XML records with interval, model reference, and method stub | SATISFIED | doall field now renders dynamically from spec instead of hardcoded False; 2 regression tests confirm |

Note: PERF-04 and TMPL-05 are mapped to Phases 34 and 30 respectively in REQUIREMENTS.md (where the core implementation was done). Phase 35 closes specific bugs found during v3.1 audit that affected these requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | -- | -- | -- | No anti-patterns found in modified files |

No TODO, FIXME, PLACEHOLDER, or HACK comments found in any modified template or test file. No empty implementations or stub patterns detected.

### Test Results

- **Targeted tests:** 10 passed in TestRenderModelsArchival (including 4 new regression tests) -- 0.70s
- **Full suite (excl. Docker/external):** 777 passed, 9 skipped, 5 warnings -- 77s
- **Docker-dependent failures:** 2 pre-existing failures in `test_docker_integration.py` and `test_golden_path.py` (require running Docker daemon; unrelated to this phase)

### Human Verification Required

None. All phase behaviors have automated test coverage. The template fixes are purely logic-level (Jinja2 guard patterns) with no visual or runtime dependencies.

### Gaps Summary

No gaps found. All 4 observable truths are verified with passing tests and correct template implementations. Both requirement IDs (PERF-04, TMPL-05) are satisfied for the bug-fix scope of this phase.

---

_Verified: 2026-03-06_
_Verifier: Claude (gsd-verifier)_
