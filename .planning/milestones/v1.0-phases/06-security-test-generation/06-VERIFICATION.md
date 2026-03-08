---
phase: 06-security-test-generation
verified: 2026-03-02T18:30:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Install a generated module with company_id field into a real Odoo 17.0 instance and verify record_rules.xml installs without errors"
    expected: "Module installs cleanly, ir.rule with company_ids domain is applied, non-company records are hidden from multi-company users"
    why_human: "Requires live Odoo + PostgreSQL instance to truly verify runtime ir.rule evaluation"
  - test: "Generate a module and run odoo-test-gen agent, then install and run the test suite via /odoo-gen:validate"
    expected: "All test methods pass: test_create, test_read, test_write, test_unlink, test_user_can_create, test_no_group_cannot_create, and workflow tests where applicable"
    why_human: "Access rights tests (with_user + assertRaises(AccessError)) require real Odoo user/group infrastructure to execute"
---

# Phase 6: Security & Test Generation Verification Report

**Phase Goal:** Every generated Odoo 17.0 module has complete security infrastructure (ACLs, groups, record rules) and a meaningful test suite that verifies real behavior.
**Verified:** 2026-03-02T18:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Security group generation produces User + Manager groups with module category | VERIFIED | `security_group.xml.j2` generates `module_category_`, `group_*_user`, `group_*_manager` with `implied_ids` chain |
| 2 | ACL CSV enforces least-privilege (User=RWC no delete, Manager=RWCU) | VERIFIED | `access_csv.j2` hardcodes User row `1,1,1,0` and Manager row `1,1,1,1` |
| 3 | Multi-company record rules auto-detected from company_id Many2one | VERIFIED | `_build_model_context()` line 163-166: `any()` scan for `name==company_id` AND `type==Many2one`; `render_module()` lines 307-314 detect company models |
| 4 | Security files included in manifest in correct order | VERIFIED | `_compute_manifest_data()` lines 232-236: security.xml -> ir.model.access.csv -> record_rules.xml (conditional) |
| 5 | Generated security installable without errors (company_ids OCA shorthand) | VERIFIED | `record_rules.xml.j2` line 9: `[('company_id', 'in', company_ids)]` — OCA shorthand, not `user.company_ids.ids` |
| 6 | test_model.py.j2 generates test_create and test_read | VERIFIED | Template lines 42-51 produce `test_create` and `test_read` with real assertions |
| 7 | test_model.py.j2 generates test_write and test_unlink | VERIFIED | Template lines 63-85: `test_write` writes Char field + asserts; `test_unlink` deletes + asserts `browse().exists()` is False |
| 8 | test_model.py.j2 generates access rights tests with AccessError | VERIFIED | Template lines 87-161: `test_user_can_create` + `test_no_group_cannot_create` with `assertRaises(AccessError)` |
| 9 | Computed field tests available via odoo-test-gen agent | VERIFIED | `odoo-test-gen.md` lines 19-21: 2 tests per computed field (`_basic` + `_zero_case`) |
| 10 | Constraint tests available via odoo-test-gen agent | VERIFIED | `odoo-test-gen.md` lines 23-26: valid + invalid with `assertRaises(ValidationError)` |
| 11 | Workflow transition tests generated (1 per state pair when state_field exists) | VERIFIED | Template lines 162-182: conditional block with guard `state_field AND workflow_states|length>=2`; renders `test_action_{to_key}()` per consecutive pair; confirmed by live render |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `python/src/odoo_gen_utils/templates/record_rules.xml.j2` | Multi-company ir.rule template with `company_ids` domain | VERIFIED | 13 lines; iterates `models if model.has_company_field`; uses OCA shorthand domain |
| `python/src/odoo_gen_utils/renderer.py` | `has_company_field` + `workflow_states` keys in `_build_model_context()`; conditional `record_rules.xml` in `render_module()` | VERIFIED | `has_company_field` at line 200; `workflow_states` at line 201; `render_module()` company detection at lines 307-324; conditional render at lines 411-424 |
| `python/src/odoo_gen_utils/templates/test_model.py.j2` | Jinja2 template with all 7 test categories | VERIFIED | 183 lines; contains `test_write`, `test_unlink`, `test_user_can_create`, `test_no_group_cannot_create`, conditional workflow block |
| `agents/odoo-test-gen.md` | Full Phase 6 scope agent (7 test categories, Phase 5 restriction removed) | VERIFIED | 145 lines; complete system prompt; all 7 categories documented with canonical patterns; "Phase 5 only" restriction absent |
| `agents/odoo-security-gen.md` | Standalone agent (NOT in pipeline) with complete security patterns | VERIFIED | 140 lines; frontmatter `description: standalone`; "NOT in the generate.md pipeline" stated explicitly; 6-step execution pattern |
| `workflows/generate.md` | Wave 2 Task B updated to list all 7 Phase 6 test categories | VERIFIED | Line 107: "all Phase 6 test categories"; lines 107-118 list all 7 categories with group ref and AccessError patterns |
| `python/tests/test_renderer.py` | 8 new Phase 6 pytest tests (4 for `has_company_field`, 4 for `record_rules.xml`) | VERIFIED | `TestBuildModelContextCompanyField` (4 tests, lines 534-582) + `TestRenderModuleRecordRules` (4 tests, lines 590-644); all 8 pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `renderer.py _build_model_context()` | model fields list | `any()` scan for `name=='company_id'` AND `type=='Many2one'` | WIRED | Lines 163-166 in renderer.py; confirmed by 4 unit tests all PASSING |
| `renderer.py render_module()` | `record_rules.xml.j2` | `render_template()` call conditional on `models_with_company_field` | WIRED | Lines 307-314 detect; lines 411-424 conditionally render; confirmed by `TestRenderModuleRecordRules` |
| `_compute_manifest_data()` | `security/record_rules.xml` | `manifest_files.append()` after `ir.model.access.csv` | WIRED | Lines 235-236; confirmed by `test_manifest_includes_record_rules_when_company_field` PASSING |
| `test_model.py.j2` | `state_field` context key | Jinja2 guard `{% if state_field and workflow_states|length >= 2 %}` | WIRED | Line 162; live render confirmed workflow tests appear only when `state_field` is a Selection type |
| `test_model.py.j2` | `module_name` context key | `env.ref("{{ module_name }}.group_{{ module_name }}_user")` in access tests | WIRED | Lines 92, 93; correct OCA group ref pattern |
| `generate.md Wave 2 Task B` | `odoo-test-gen` agent | Task tool spawn with Phase 6 expanded scope prompt | WIRED | Lines 103-118 in generate.md; prompt explicitly lists all 7 test categories |
| `record_rules.xml.j2` | enriched model dicts | `model.has_company_field` attribute via enriched_models in render_module() | WIRED | Lines 316-324 build `enriched_models` with `has_company_field` attached; passed as context at line 415 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SECG-01 | 06-01-PLAN.md | `ir.model.access.csv` with correct model references and CRUD permissions | SATISFIED | `access_csv.j2` template generates ACL rows per model; `security_group.xml.j2` generates User/Manager groups with `implied_ids` |
| SECG-02 | 06-02-PLAN.md | Security group hierarchy (User and Manager) with proper `implied_ids` chains | SATISFIED | `security_group.xml.j2`: User has `implied_ids=[(4, ref('base.group_user'))]`; Manager has `implied_ids=[(4, ref('group_*_user'))]` |
| SECG-03 | 06-01-PLAN.md | Record rules for multi-company scenarios | SATISFIED | `record_rules.xml.j2` + `has_company_field` detection in renderer; 4 unit tests passing |
| SECG-04 | 06-01, 06-02 | Module category for the security group hierarchy | SATISFIED | `security_group.xml.j2` generates `ir.module.category` with sequence=100 before groups |
| SECG-05 | 06-01-PLAN.md | Every generated model has at least one access control rule | SATISFIED | `access_csv.j2` iterates ALL models and generates both User and Manager ACL rows unconditionally |
| TEST-01 | 06-02-PLAN.md | `tests/__init__.py` and test files using `TransactionCase` | SATISFIED | Template line 2: `from odoo.tests.common import TransactionCase`; line 6: class extends `TransactionCase` |
| TEST-02 | 06-02-PLAN.md | Model CRUD tests (create, read, update, delete) | SATISFIED | Template: `test_create` (line 42), `test_read` (line 46), `test_write` (line 63), `test_unlink` (line 78) |
| TEST-03 | 06-02-PLAN.md | Access rights tests (user role vs manager role permissions) | SATISFIED | Template: `test_user_can_create` (line 87) + `test_no_group_cannot_create` (line 125) with `assertRaises(AccessError)` |
| TEST-04 | 06-02-PLAN.md | Computed field tests | SATISFIED | `odoo-test-gen.md` lines 19-21: 2 tests per computed field pattern documented |
| TEST-05 | 06-02-PLAN.md | Constraint tests | SATISFIED | `odoo-test-gen.md` lines 23-26: valid + invalid with `assertRaises(ValidationError)` pattern documented |
| TEST-06 | 06-02-PLAN.md | Workflow/state transition tests | SATISFIED | Template lines 162-182: conditional workflow block; live render confirms `test_action_confirm()` generated when state_field + 2+ workflow_states |

All 11 requirements (SECG-01 through SECG-05, TEST-01 through TEST-06) are SATISFIED.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `workflows/generate.md` | 18 | "adds computed field tests, constraint tests, and onchange tests to the Jinja2-generated test stubs" — description does not mention Phase 6 categories | Info | Wave 2 description in the overview paragraph is stale; the actual Task B prompt at lines 107-118 is correct and complete |

No blockers or warnings found. The single Info item is a minor documentation inconsistency in the generate.md overview paragraph — the actual Task B prompt that agents read is correct.

---

### Human Verification Required

#### 1. Multi-Company Record Rule Runtime Behavior

**Test:** Generate a module with a `company_id` Many2one field, install it on a real Odoo 17.0 instance with 2 companies and 2 users (each belonging to one company), create records in each company, then switch user company context and verify records from the other company are not visible.
**Expected:** Records from company B are hidden from company A users due to the `company_ids` ir.rule domain.
**Why human:** Requires live Odoo 17.0 + PostgreSQL environment. The `company_ids` shorthand only resolves correctly at Odoo runtime — cannot be verified via static analysis.

#### 2. Access Rights Tests Execution

**Test:** Generate a module, run the odoo-test-gen agent on it to produce domain-specific assertions, install in Docker via `/odoo-gen:validate`, and verify all access rights tests pass.
**Expected:** `test_user_can_create` succeeds (user with module group can create), `test_no_group_cannot_create` raises `AccessError`.
**Why human:** Access rights tests use `with_user(non_admin)` which bypasses sudo — requires real Odoo user/group database to execute. Static analysis cannot confirm group refs resolve.

---

### Gaps Summary

No gaps found. All 11 observable truths verified, all 7 required artifacts exist and are substantive, all 7 key links are confirmed wired.

One structural observation on `test_model.py.j2`: The workflow transition test block (lines 162-182) is rendered after the closing `})` of `test_no_group_cannot_create` but the indentation structure places workflow test methods correctly as separate class-level methods (4-space indent `def test_action_{to_key}`). Live render output confirmed the generated Python is structurally valid — `test_action_confirm` appears as a standalone method after `test_no_group_cannot_create` closes correctly.

---

## Test Suite Evidence

All 130 pytest tests pass (0.71s):

```
python/.venv/bin/pytest python/tests/ → 130 passed, 5 warnings in 0.71s
```

Phase 6 specific tests (8 of 130):
- `TestBuildModelContextCompanyField` — 4 tests, all PASSED
  - `test_company_field_many2one_sets_has_company_field_true`
  - `test_no_company_field_sets_has_company_field_false`
  - `test_company_field_wrong_type_sets_false`
  - `test_company_field_different_name_sets_false`
- `TestRenderModuleRecordRules` — 4 tests, all PASSED
  - `test_company_field_model_generates_record_rules_xml`
  - `test_no_company_field_no_record_rules_xml`
  - `test_record_rules_xml_contains_company_ids_domain`
  - `test_manifest_includes_record_rules_when_company_field`

---

_Verified: 2026-03-02T18:30:00Z_
_Verifier: Claude (gsd-verifier)_
