---
phase: 62-portal-controllers
verified: 2026-03-09T14:50:00Z
status: passed
score: 11/11 must-haves verified
must_haves:
  truths:
    - "Portal spec with pages array validates through Pydantic schema (PortalSpec, PortalPageSpec, PortalActionSpec)"
    - "Portal preprocessor enriches spec with has_portal, portal_pages, portal_auth and auto-adds 'portal' to depends"
    - "E23 validation detects ownership paths that do not terminate at res.users"
    - "E23 validation accepts valid direct and multi-hop ownership paths"
    - "Preprocessor runs at order=95 (after notifications@90, before webhooks@100)"
    - "Portal spec generates a controller.py inheriting CustomerPortal with _prepare_home_portal_values, domain helpers, list/detail routes, and stub zones"
    - "Portal spec generates QWeb templates: home counter entries via portal_docs_entry, list pages with portal_table and pagination, detail pages with card layout"
    - "Portal spec generates record rules with base.group_portal, noupdate=1, correct ownership domains, explicit perm_read/write/create/unlink"
    - "Editable detail pages generate POST handler with allowed_fields whitelist, CSRF form template, and separate write record rule"
    - "Report download actions generate controller routes calling _show_report() with _document_check_access()"
    - "render_portal() stage produces controller file + QWeb XML files + portal rule XML in a single render pass"
  artifacts:
    - path: "python/src/odoo_gen_utils/spec_schema.py"
      provides: "PortalActionSpec, PortalFilterSpec, PortalPageSpec, PortalSpec Pydantic models; portal field on ModuleSpec"
    - path: "python/src/odoo_gen_utils/preprocessors/portal.py"
      provides: "Portal preprocessor at order=95"
    - path: "python/src/odoo_gen_utils/validation/semantic.py"
      provides: "E23 ownership path validation check and _resolve_model_fields helper"
    - path: "python/tests/fixtures/portal_spec.json"
      provides: "Test fixture with uni_student_portal 4-page spec"
    - path: "python/src/odoo_gen_utils/templates/shared/portal_controller.py.j2"
      provides: "Controller class template inheriting CustomerPortal"
    - path: "python/src/odoo_gen_utils/templates/shared/portal_home_counter.xml.j2"
      provides: "QWeb home counter entry template"
    - path: "python/src/odoo_gen_utils/templates/shared/portal_list.xml.j2"
      provides: "QWeb list page template with pagination"
    - path: "python/src/odoo_gen_utils/templates/shared/portal_detail.xml.j2"
      provides: "QWeb detail page template with card layout"
    - path: "python/src/odoo_gen_utils/templates/shared/portal_detail_editable.xml.j2"
      provides: "QWeb editable detail page with form and CSRF"
    - path: "python/src/odoo_gen_utils/templates/shared/portal_rules.xml.j2"
      provides: "Portal record rules template"
    - path: "python/src/odoo_gen_utils/renderer.py"
      provides: "render_portal() function and 'portal' stage in pipeline"
  key_links:
    - from: "python/src/odoo_gen_utils/preprocessors/portal.py"
      to: "python/src/odoo_gen_utils/preprocessors/_registry.py"
      via: "@register_preprocessor(order=95, name='portal')"
    - from: "python/src/odoo_gen_utils/renderer.py"
      to: "templates/shared/portal_controller.py.j2"
      via: "render_template('portal_controller.py.j2', ...) at line 886"
    - from: "python/src/odoo_gen_utils/renderer.py"
      to: "STAGE_NAMES and all_stages pipeline"
      via: "('portal', lambda: render_portal(...)) at line 1139"
    - from: "python/src/odoo_gen_utils/validation/semantic.py"
      to: "_check_e23 called from semantic_validate()"
      via: "e23_issues = _check_e23(output_dir, spec, registry) at line 2025"
---

# Phase 62: Portal Controllers Verification Report

**Phase Goal:** Users can generate portal-facing features with controllers, QWeb templates, and security rules that restrict data to the portal user's linked records
**Verified:** 2026-03-09T14:50:00Z
**Status:** PASSED
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Portal spec with pages array validates through Pydantic schema (PortalSpec, PortalPageSpec, PortalActionSpec) | VERIFIED | `spec_schema.py` lines 55-118: PortalActionSpec, PortalFilterSpec, PortalPageSpec (with type validator restricting to detail/list), PortalSpec all defined. ModuleSpec.portal field at line 449. 19 schema tests pass. |
| 2 | Portal preprocessor enriches spec with has_portal, portal_pages, portal_auth and auto-adds 'portal' to depends | VERIFIED | `preprocessors/portal.py` lines 63-109: @register_preprocessor(order=95), sets has_portal=True, portal_pages (enriched with model_var/model_class/singular_name/plural_name), portal_auth, portal_page_models, auto-adds "portal" to depends immutably. 16 preprocessor tests pass. |
| 3 | E23 validation detects ownership paths that do not terminate at res.users | VERIFIED | `validation/semantic.py` lines 1760-1897: _check_e23 traverses ownership path hops, checks terminal model == "res.users", emits E23 error when it does not. Wired into semantic_validate() at line 2025. 10 validation tests pass. |
| 4 | E23 validation accepts valid direct and multi-hop ownership paths | VERIFIED | _check_e23 splits on "." (line 1799), traverses model chain via _resolve_model_fields helper (line 1740), follows relational comodel_name through intermediates. Direct "user_id" and multi-hop "student_id.user_id" both work. Tests confirm. |
| 5 | Preprocessor runs at order=95 (after notifications@90, before webhooks@100) | VERIFIED | `portal.py` line 63: `@register_preprocessor(order=95, name="portal")`. Registry count test confirms 16 preprocessors with 95 in order sequence. |
| 6 | Portal spec generates controller.py inheriting CustomerPortal with counters, domain helpers, list/detail routes, and stub zones | VERIFIED | `portal_controller.py.j2`: Class inherits CustomerPortal (line 10), _prepare_home_portal_values with check_access_rights guard (lines 14-28), _get_{model_var}_domain helpers (lines 33-37), list routes with portal_pager (lines 45-85), detail routes with _document_check_access (lines 88-106), BUSINESS LOGIC START/END markers (lines 52-54, 152-154). |
| 7 | Portal spec generates QWeb templates: home counter entries via portal_docs_entry, list pages with portal_table and pagination, detail pages with card layout | VERIFIED | `portal_home_counter.xml.j2`: inherits portal.portal_my_home, calls portal.portal_docs_entry. `portal_list.xml.j2`: uses portal.portal_layout, portal.portal_searchbar, portal.portal_table, portal.pager. `portal_detail.xml.j2`: 2-column layout (col-lg-8/col-lg-4), card body, back button. |
| 8 | Portal spec generates record rules with base.group_portal, noupdate=1, correct ownership domains, explicit perm_read/write/create/unlink | VERIFIED | `portal_rules.xml.j2`: `<data noupdate="1">`, ir.rule records with `base.group_portal`, domain_force uses ownership, read rule has perm_read=True/perm_write=False/perm_create=False/perm_unlink=False. |
| 9 | Editable detail pages generate POST handler with allowed_fields whitelist, CSRF form template, and separate write record rule | VERIFIED | Controller template lines 136-163: detail type with fields_editable gets methods=['GET', 'POST'], allowed_fields set, sudo().write(vals). `portal_detail_editable.xml.j2`: form with method="POST", csrf_token hidden input, editable field inputs, save button. Rules template lines 17-28: separate write rule for editable models with perm_write=True. |
| 10 | Report download actions generate controller routes calling _show_report() with _document_check_access() | VERIFIED | Controller template lines 107-134: report action routes with _document_check_access, state check gating, _show_report() call with report_ref and download=True. |
| 11 | render_portal() stage produces controller + QWeb XML + portal rules in a single render pass | VERIFIED | `renderer.py` lines 832-954: render_portal() renders portal_controller.py.j2, updates controllers/__init__.py, renders portal_home_counter.xml.j2 and per-page list/detail/editable templates, renders portal_rules.xml.j2. Wired into pipeline at line 1139. STAGE_NAMES has 13 entries including "portal". |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `python/src/odoo_gen_utils/spec_schema.py` | VERIFIED | 540 lines. PortalActionSpec(55), PortalFilterSpec(67), PortalPageSpec(76), PortalSpec(111), ModuleSpec.portal(449). |
| `python/src/odoo_gen_utils/preprocessors/portal.py` | VERIFIED | 109 lines. @register_preprocessor(order=95). Enriches spec immutably. |
| `python/src/odoo_gen_utils/validation/semantic.py` | VERIFIED | _check_e23 at line 1760, _resolve_model_fields at line 1740, wired into semantic_validate at line 2025. |
| `python/tests/fixtures/portal_spec.json` | VERIFIED | 111 lines. uni_student_portal with 4 pages, 2 models, detail actions, filters. |
| `python/src/odoo_gen_utils/templates/shared/portal_controller.py.j2` | VERIFIED | 186 lines. CustomerPortal inheritance, counters, domain helpers, list/detail/editable/report routes. |
| `python/src/odoo_gen_utils/templates/shared/portal_home_counter.xml.j2` | VERIFIED | 29 lines. Inherits portal.portal_my_home, portal_docs_entry calls. |
| `python/src/odoo_gen_utils/templates/shared/portal_list.xml.j2` | VERIFIED | 44 lines. portal.portal_table, portal.portal_searchbar, pagination. |
| `python/src/odoo_gen_utils/templates/shared/portal_detail.xml.j2` | VERIFIED | 55 lines. 2-column card layout, back button, action buttons. |
| `python/src/odoo_gen_utils/templates/shared/portal_detail_editable.xml.j2` | VERIFIED | 49 lines. CSRF form, read-only + editable fields, save button. |
| `python/src/odoo_gen_utils/templates/shared/portal_rules.xml.j2` | VERIFIED | 30 lines. base.group_portal, noupdate=1, read + write rules. |
| `python/src/odoo_gen_utils/renderer.py` | VERIFIED | render_portal() at line 832, STAGE_NAMES has 13 entries (line 74-77), pipeline wiring at line 1139. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `preprocessors/portal.py` | `preprocessors/_registry.py` | `@register_preprocessor(order=95)` | WIRED | Decorator at line 63, confirmed by registry count test (16 preprocessors). |
| `spec_schema.py` | `preprocessors/portal.py` | Pydantic models validate portal spec before preprocessor enriches it | WIRED | PortalSpec class at line 111; preprocessor handles both Pydantic model and dict (lines 80-85). |
| `validation/semantic.py` | `registry.py` | E23 uses ModelRegistry for cross-module ownership path traversal | WIRED | _resolve_model_fields checks registry at lines 1753-1756; _check_e23 receives registry param. |
| `renderer.py` | `portal_controller.py.j2` | render_template() call | WIRED | Line 886: render_template(env, "portal_controller.py.j2", ...) |
| `renderer.py` | STAGE_NAMES/all_stages | portal stage added after controllers | WIRED | STAGE_NAMES line 77 includes "portal"; all_stages line 1139: ("portal", lambda: render_portal(...)). |
| `portal_controller.py.j2` | portal spec enriched by preprocessor | Jinja context variables: portal_pages, portal_auth | WIRED | Template uses `portal_pages` at lines 11, 42; `portal_models` at line 33; `controller_class` at line 10. All provided by render_portal() context at lines 875-882. |
| `preprocessors/__init__.py` | `preprocessors/portal.py` | Re-export import | WIRED | Line 107: `from odoo_gen_utils.preprocessors.portal import ...` |
| `renderer_context.py` | preprocessor output | has_portal, has_controllers, portal manifest files | WIRED | Lines 649-697: has_portal from spec, portal view files added to manifest_files. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PRTL-01 | 62-01, 62-02 | Generate portal controllers inheriting portal.CustomerPortal with ir.http routes, authentication, and JSON serialization | SATISFIED | Controller template inherits CustomerPortal with @http.route decorators, auth='user', list/detail/report routes. render_portal() generates controllers/portal.py. |
| PRTL-02 | 62-02 | Generate QWeb portal templates inheriting portal.portal_my_home with portal menu items and page templates | SATISFIED | portal_home_counter.xml.j2 inherits portal.portal_my_home with portal_docs_entry. portal_list.xml.j2 uses portal.portal_table. portal_detail.xml.j2 and portal_detail_editable.xml.j2 use portal.portal_layout. |
| PRTL-03 | 62-01, 62-02 | Generate portal-specific record rules restricting data to the portal user's linked records | SATISFIED | portal_rules.xml.j2 generates ir.rule records with base.group_portal, domain_force using ownership path, noupdate=1, explicit perm flags. E23 validates ownership paths terminate at res.users. |

No orphaned requirements found. REQUIREMENTS.md maps PRTL-01, PRTL-02, PRTL-03 to Phase 62, all claimed by plans and all verified.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `portal_controller.py.j2` | 53 | `# TODO: implement portal_my_{{ page.id }} logic` | Info | Intentional BUSINESS LOGIC stub zone for Logic Writer integration. Not a missing implementation -- this is the designed pattern. |
| `portal_controller.py.j2` | 153 | `# TODO: validate and write editable fields` | Info | Intentional BUSINESS LOGIC stub zone in editable POST handler. Logic Writer fills these. |

Both TODOs are intentional stub markers between `--- BUSINESS LOGIC START ---` and `--- BUSINESS LOGIC END ---` delimiters. These are the designed hook points for the Logic Writer (Phase 56) to inject business logic. They do NOT represent missing functionality -- the generated controllers work as-is with default behavior.

### Human Verification Required

### 1. Generated Portal Module Installability

**Test:** Generate a module with portal spec (e.g., uni_student_portal fixture), install it in a Docker Odoo 17 instance, and verify the portal pages are accessible.
**Expected:** Module installs without errors, /my/profile route responds, portal home shows menu entries.
**Why human:** Docker integration tests are pre-existing failures (bind mount path issue). Cannot verify real Odoo installation programmatically in this environment.

### 2. QWeb Template Rendering in Browser

**Test:** Navigate to /my/enrollments as a portal user, verify table renders with pagination, click detail link.
**Expected:** Portal table shows enrollment records, pager works, detail page shows 2-column card layout.
**Why human:** Visual rendering and browser interaction cannot be verified programmatically.

### Gaps Summary

No gaps found. All 11 observable truths verified. All 11 artifacts exist, are substantive (not stubs), and are wired into the codebase. All 4 key links from Plan 01 and 3 key links from Plan 02 are confirmed. All 3 requirements (PRTL-01, PRTL-02, PRTL-03) are satisfied. 2125 non-Docker tests pass including 157 portal-specific tests. The 2 TODO patterns found are intentional Logic Writer stub zones, not missing implementation.

---

_Verified: 2026-03-09T14:50:00Z_
_Verifier: Claude (gsd-verifier)_
