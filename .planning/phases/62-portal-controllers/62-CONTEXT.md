# Phase 62: Portal Controllers - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate portal-facing features with controllers inheriting `portal.CustomerPortal`, QWeb templates inheriting `portal.portal_my_home`, and portal-specific record rules restricting data to the portal user's linked records. Covers list pages, detail pages, home counters, report download actions, editable profile fields, and ownership-based security.

Pipeline: Spec with `portal` section → Portal preprocessor (order=90) validates ownership paths + adds portal depend → Jinja renders controller + QWeb templates + record rules → Stub zones for Logic Writer → Semantic validate (E23 ownership path) → Pass/fail

</domain>

<decisions>
## Implementation Decisions

### Portal spec format

**Top-level "portal" key** on the module spec. Refined from NEW-01 (which predates Phase 37-60 infrastructure).

```json
{
  "module_name": "uni_student_portal",
  "depends": ["portal", "uni_student", "uni_fee", "uni_enrollment"],
  "portal": {
    "pages": [
      {
        "id": "student_profile",
        "type": "detail",
        "model": "uni.student",
        "route": "/my/profile",
        "title": "My Profile",
        "ownership": "user_id",
        "fields_visible": ["name", "cnic", "program_id", "department_id", "cgpa", "enrollment_status", "semester"],
        "fields_editable": ["phone", "email", "address"],
        "show_in_home": true,
        "home_icon": "fa fa-user",
        "home_counter": false
      },
      {
        "id": "student_enrollments",
        "type": "list",
        "model": "uni.enrollment",
        "route": "/my/enrollments",
        "title": "My Enrollments",
        "ownership": "student_id.user_id",
        "list_fields": ["course_id", "term_id", "state", "grade"],
        "detail_route": "/my/enrollment/<int:enrollment_id>",
        "detail_fields": ["course_id", "term_id", "section", "state", "grade", "grade_point", "attendance_percentage"],
        "filters": [
          {"field": "term_id", "label": "Term"},
          {"field": "state", "label": "Status"}
        ],
        "default_sort": "term_id desc",
        "show_in_home": true,
        "home_icon": "fa fa-book",
        "home_counter": true
      },
      {
        "id": "student_fees",
        "type": "list",
        "model": "fee.invoice",
        "route": "/my/fees",
        "title": "My Fees",
        "ownership": "student_id.user_id",
        "list_fields": ["name", "amount", "due_date", "state", "amount_paid"],
        "detail_route": "/my/fee/<int:invoice_id>",
        "detail_fields": ["name", "amount", "penalty_amount", "total_amount", "due_date", "state", "amount_paid", "balance"],
        "detail_actions": [
          {
            "name": "download_challan",
            "label": "Download Challan",
            "type": "report",
            "report_ref": "uni_fee.report_fee_challan",
            "states": ["confirmed", "overdue"]
          }
        ],
        "show_in_home": true,
        "home_icon": "fa fa-money",
        "home_counter": true,
        "counter_domain": [["state", "in", ["confirmed", "overdue"]]]
      },
      {
        "id": "student_results",
        "type": "list",
        "model": "exam.result",
        "route": "/my/results",
        "title": "My Results",
        "ownership": "student_id.user_id",
        "list_fields": ["course_id", "exam_type", "marks", "grade", "term_id"],
        "show_in_home": true,
        "home_icon": "fa fa-graduation-cap",
        "home_counter": false
      }
    ],
    "auth": "portal",
    "menu_label": "Student Portal"
  }
}
```

**Three page types:**
- `"detail"` — Single record view (profile page). One record belonging to the user. Optional editable fields (renders as form with save). Route: `/my/profile` (no ID in URL).
- `"list"` — Paginated list with optional detail drilldown. Multiple records belonging to the user. Route: `/my/enrollments` (list), `/my/enrollment/<id>` (detail). Optional filters, sorting, pagination.
- `"form"` — Submission form (applications, requests). Creates a new record. **Deferred to later phase — not building in Phase 62.**

**Key spec fields:**
- `"ownership"` — Field path from model to `res.users`. Critical for both record rules AND controller queryset filtering. Direct (`"user_id"`) or multi-hop (`"student_id.user_id"`).
- `"fields_visible"` vs `"fields_editable"` — Visible are read-only display, editable render as form inputs with save button. Belt generates both QWeb template and controller write logic for editable fields.
- `"show_in_home"` + `"home_icon"` + `"home_counter"` — Controls entry on `/my` portal home. `home_counter=true` generates counter method on portal controller.
- `"counter_domain"` — Optional domain filter for counter (e.g., only count unpaid fees).
- `"detail_actions"` — Buttons on detail page. Type `"report"` generates download link. Type `"action"` deferred to future.

### Route & URL patterns

**Follow Odoo portal conventions exactly. No custom prefixes.**

URL structure:
- `/my` — portal home (inherited, add counters)
- `/my/enrollments` — list page (paginated)
- `/my/enrollments?page=2` — pagination
- `/my/enrollments?term=5` — filtered
- `/my/enrollment/42` — detail page
- `/my/profile` — single-record detail (no ID)
- `/my/fee/17/download_challan` — report download action

Conventions:
- List route: `/my/{plural_name}` (enrollments, fees, results)
- Detail route: `/my/{singular_name}/<id>` (enrollment, fee, result)
- Profile: `/my/profile` (no ID, one record per user)
- Actions: `/my/{singular}/<id>/{action_name}`

The spec's `"route"` field is canonical — belt uses it directly. No magic URL generation.

**Pagination:** 20 records per page (Odoo default). Belt generates pager helper using Odoo's `portal.pager` utility.

**Auth strategy:**
- `"auth": "portal"` → `@http.route(..., auth='user', type='http')` — only logged-in portal/internal users
- `"auth": "public"` → `@http.route(..., auth='public', type='http')` — anyone (rare for student data)
- Default is `"portal"`. Belt always generates BOTH route auth AND record rule — double security.

**Generated controller inherits `CustomerPortal`:**
- `_prepare_home_portal_values(counters)` for home counters
- Per-page list/detail methods with stub zones for Logic Writer
- `_get_{model}_domain()` helper methods using ownership path
- `website=True` on all routes for portal layout integration

### Record rule domains

Generated from `"ownership"` field path. Supports direct and multi-hop.

**Direct:** `"ownership": "user_id"` → `[('user_id', '=', user.id)]`
**Multi-hop:** `"ownership": "student_id.user_id"` → `[('student_id.user_id', '=', user.id)]`
**Complex (x2many):** `"ownership": "student_id.guardian_ids.user_id"` → `[('student_id.guardian_ids.user_id', '=', user.id)]`

Odoo supports dotted paths in `ir.rule` domains natively for Many2one and x2many traversal.

**Portal record rules are ALWAYS read-only by default** (perm_read=True, perm_write/create/unlink=False). If spec has `"fields_editable"`, belt generates a **separate** rule with perm_write=True for that model, scoped to same ownership domain.

**Controller domain helper AND record rule use the SAME ownership path.** Belt generates both from the single `"ownership"` spec field.

**New validation check E23: Portal ownership path invalid**
- Validates field path resolves through the model chain
- Verifies path terminates at `res.users` (or has path to `res.users`)
- Uses model registry for cross-module resolution
- ERROR if path doesn't terminate at `res.users`

### QWeb template depth

**Full page structure** — breadcrumbs, pagination, responsive layout, inheriting `portal.portal_my_home`. Not minimal content-only.

**Three QWeb templates per list page:**
1. **Home counter** — inherits `portal.portal_my_home`, adds entry with icon/counter via `portal.portal_docs_entry`
2. **List page** — `portal.portal_layout` + `portal.portal_searchbar`, responsive table with column headers from `list_fields`, pagination via `portal.pager`, empty state alert
3. **Detail page** — card layout with field rows from `detail_fields`, sidebar for status/actions, back button

**For editable detail pages** (profile with `fields_editable`): Generate form with input fields + save button + controller POST handler that validates and writes.

**Badge auto-styling:** Belt checks if field is Selection type → generates `t-attf-class` with badge colors based on Odoo state patterns (draft=secondary, confirmed=info, done=success, cancelled=danger).

**Report download actions:** Button on detail page + controller route that calls `_render_qweb_pdf()` and returns file response. Gated by `states` condition.

**Six new Jinja templates:**
```
templates/shared/
├── portal_controller.py.j2       # Controller class inheriting CustomerPortal
├── portal_home_counter.xml.j2    # /my home entry (inherits portal.portal_my_home)
├── portal_list.xml.j2            # List page template (table + pagination)
├── portal_detail.xml.j2          # Detail page template (card layout)
├── portal_detail_editable.xml.j2 # Detail with form inputs + save
└── portal_rules.xml.j2           # Portal record rules
```

### Preprocessor

```python
@register_preprocessor(order=90)
def process_portal(spec, models, context):
    portal = spec.get('portal')
    if not portal:
        return
    context['has_portal'] = True
    context['portal_pages'] = portal['pages']
    context['portal_auth'] = portal.get('auth', 'portal')
    context.setdefault('extra_depends', []).append('portal')
    _validate_ownership_path(page, models, context['registry'])
```

**Order 90:** After all model processing (extensions, chains, security, approval) because portal needs to reference finalized models and fields. Before tests (which may need portal test fixtures).

### Claude's Discretion
- Exact Jinja template implementation for the 6 portal templates
- Pydantic schema for PortalSpec, PortalPageSpec, PortalActionSpec
- How to implement E23 ownership path validation (AST walk vs string split)
- Controller access check pattern (browse + exists + check_access_rights)
- How to handle the editable form POST → write flow (CSRF, validation)
- Test fixture design for portal scenarios
- How to extend render_controllers() vs add a separate render_portal()
- Whether portal templates go in views/ or a portal/ subdirectory

</decisions>

<specifics>
## Specific Ideas

- Complete portal spec example (uni_student_portal with 4 pages) provided above — use as test fixture
- Controller class named `{ModuleName}Portal` (e.g., `UniStudentPortal`) inheriting `CustomerPortal`
- Domain helpers named `_get_{model_short}_domain()` (e.g., `_get_enrollment_domain()`)
- Counter method uses Odoo's standard `_prepare_home_portal_values(counters)` pattern
- Badge colors for Selection fields: draft=secondary, confirmed/active=info, done/approved=success, cancelled/rejected=danger, overdue=warning
- List page empty state: `<div class="alert alert-info">No {title} found.</div>`
- Detail page layout: 2-column (8+4) with main content card left, status/actions sidebar right
- Back button on every detail page linking to the list route

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `controller.py.j2` — existing generic controller template. Portal template is different (inherits CustomerPortal, not http.Controller) but shares route decorator pattern.
- `init_controllers.py.j2` — reuse for `controllers/__init__.py`
- `record_rules.xml.j2` — existing record rule template. Portal rules need `groups` set to `base.group_portal` specifically.
- `renderer.py:render_controllers()` — existing stage in pipeline. Portal rendering integrates here or as a new `render_portal()` function.
- `registry.py:ModelRegistry` — needed for E23 ownership path validation (traverse field chain across models).
- `validation/semantic.py` — E1-E22 checks. E23 extends this for portal ownership validation.
- `preprocessors/` — decorator-based registry. Portal preprocessor at order=90.
- `spec_schema.py` — Pydantic models. Needs new PortalSpec, PortalPageSpec.

### Established Patterns
- Frozen dataclasses for immutable data
- Preprocessor decorator registry with ordering
- Jinja template rendering through renderer.py with context dict
- BUSINESS LOGIC START/END markers for Logic Writer stub zones (Phase 58)
- Pydantic schema for spec validation with cross-field validators
- Semantic validation checks (E-series for errors, W-series for warnings)

### Integration Points
- `renderer.py` — add portal rendering stage (after controllers, before tests)
- `spec_schema.py` — add PortalSpec Pydantic model, portal field on ModuleSpec
- `preprocessors/` — add portal preprocessor at order=90
- `validation/semantic.py` — add E23 check
- `templates/shared/` — 6 new portal templates
- `manifest.py.j2` — portal depends auto-added by preprocessor
- `logic_writer/context_builder.py` — portal controller stubs need method context

</code_context>

<deferred>
## Deferred Ideas

- `"form"` page type (submission forms creating new records) — own phase when needed
- `"action"` type detail_actions (triggering server actions from portal) — future
- Portal user creation/invitation flow — separate from generation
- Multi-portal support (student portal + parent portal + alumni portal as separate modules) — composition pattern, not a generator feature
- Portal search/full-text filtering — add when needed
- Mobile-specific portal templates (PWA) — future enhancement
- Portal notification preferences page — separate feature

</deferred>

---

*Phase: 62-portal-controllers*
*Context gathered: 2026-03-09*
