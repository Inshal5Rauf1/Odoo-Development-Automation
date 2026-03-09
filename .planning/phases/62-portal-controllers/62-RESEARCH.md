# Phase 62: Portal Controllers - Research

**Researched:** 2026-03-09
**Domain:** Odoo 17 portal controller generation, QWeb templates, portal record rules
**Confidence:** HIGH

## Summary

Phase 62 generates portal-facing features for Odoo modules: controllers inheriting `portal.CustomerPortal`, QWeb templates inheriting `portal.portal_my_home`, and ownership-based record rules scoped to `base.group_portal`. The implementation extends the existing code generation pipeline with a new preprocessor (order=90), 6 new Jinja templates, a new `render_portal()` stage in the renderer pipeline, new Pydantic schema models, and E23 semantic validation.

The Odoo 17 portal controller pattern is well-established and stable. Every standard Odoo module (sale, account, project, helpdesk) follows an identical structure: a controller class inheriting `CustomerPortal` with `_prepare_home_portal_values()` for counters, list routes with `pager()` pagination, detail routes with `_document_check_access()` for security, and `_show_report()` for PDF downloads. QWeb templates follow a three-layer pattern: home counter entry via `portal.portal_docs_entry`, list page via `portal.portal_table`, and detail page via `portal.portal_sidebar`. Record rules use `base.group_portal` group with `domain_force` expressions using dotted ownership paths.

**Primary recommendation:** Implement the portal generation as 6 Jinja templates + 1 preprocessor + 1 render stage + Pydantic schema + E23 validation, following the exact Odoo 17 portal patterns from sale/account modules. The preprocessor validates ownership paths and enriches the spec; the render stage generates controller, templates, and rules from the enriched spec.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Spec format:** Top-level `"portal"` key on module spec with `pages` array. Three page types: `"detail"`, `"list"`, `"form"` (form deferred).
- **Ownership field:** `"ownership"` field path from model to `res.users`, used for both record rules AND controller queryset filtering. Direct (`"user_id"`) or multi-hop (`"student_id.user_id"`).
- **Route conventions:** Follow Odoo portal conventions exactly. List: `/my/{plural}`, detail: `/my/{singular}/<id>`, profile: `/my/profile` (no ID). Spec `"route"` field is canonical.
- **Auth strategy:** `"auth": "portal"` maps to `auth='user'`. Default is portal. Belt generates BOTH route auth AND record rule (double security).
- **Controller inherits CustomerPortal:** `_prepare_home_portal_values(counters)` for counters, per-page methods with stub zones, `_get_{model}_domain()` helpers.
- **Record rules read-only by default:** `perm_read=True`, rest False. Separate write rule for models with `fields_editable`.
- **Six new Jinja templates:** `portal_controller.py.j2`, `portal_home_counter.xml.j2`, `portal_list.xml.j2`, `portal_detail.xml.j2`, `portal_detail_editable.xml.j2`, `portal_rules.xml.j2`
- **Preprocessor at order=90:** After all model processing, before tests/webhooks.
- **E23 validation:** Portal ownership path validation -- verifies field path terminates at `res.users`.
- **Pagination:** 20 records per page using Odoo's `portal.pager` utility.
- **Badge auto-styling:** Selection fields get badge colors: draft=secondary, confirmed/active=info, done/approved=success, cancelled/rejected=danger, overdue=warning.
- **Three QWeb templates per list page:** Home counter, list page, detail page.
- **Full page structure:** Breadcrumbs, pagination, responsive layout, not minimal content-only.

### Claude's Discretion
- Exact Jinja template implementation for the 6 portal templates
- Pydantic schema for PortalSpec, PortalPageSpec, PortalActionSpec
- How to implement E23 ownership path validation (AST walk vs string split)
- Controller access check pattern (browse + exists + check_access_rights)
- How to handle the editable form POST -> write flow (CSRF, validation)
- Test fixture design for portal scenarios
- How to extend render_controllers() vs add a separate render_portal()
- Whether portal templates go in views/ or a portal/ subdirectory

### Deferred Ideas (OUT OF SCOPE)
- `"form"` page type (submission forms creating new records) -- own phase
- `"action"` type detail_actions (triggering server actions from portal) -- future
- Portal user creation/invitation flow -- separate from generation
- Multi-portal support (student + parent + alumni as separate modules) -- composition
- Portal search/full-text filtering -- add when needed
- Mobile-specific portal templates (PWA) -- future
- Portal notification preferences page -- separate feature
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRTL-01 | Generate portal controllers inheriting portal.CustomerPortal with ir.http routes, authentication, and JSON serialization | Odoo 17 CustomerPortal pattern verified: `_prepare_home_portal_values(counters)`, `_document_check_access()`, `pager()`, `_show_report()`. Jinja template `portal_controller.py.j2` generates the controller class. |
| PRTL-02 | Generate QWeb portal templates inheriting portal.portal_my_home with portal menu items and page templates | Odoo 17 template inheritance verified: `portal.portal_docs_entry` for home counters, `portal.portal_table` for list pages, `portal.portal_sidebar` for detail pages. Three Jinja templates generate corresponding QWeb XML. |
| PRTL-03 | Generate portal-specific record rules restricting data to the portal user's linked records | Record rule pattern verified: `base.group_portal` group, `domain_force` with dotted ownership paths, `<data noupdate="1">` wrapper. Separate read-only and write rules. Jinja template `portal_rules.xml.j2` generates the rules. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | 2.10+ | PortalSpec/PortalPageSpec schema validation | Project convention -- all spec schemas are Pydantic v2 models |
| Jinja2 | 3.1+ | Template rendering for portal controller/QWeb/rules | Project convention -- entire generation pipeline uses Jinja2 |
| pytest | 8.0+ | Test framework for portal generation tests | Project convention -- all tests use pytest |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (no new deps) | - | All portal functionality uses existing dependencies | Phase adds templates/code, no new packages |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate render_portal() | Extend render_controllers() | Separate function is cleaner -- portal generation is structurally different from generic controllers (inherits CustomerPortal, generates QWeb, generates rules). Add as new pipeline stage. |
| Portal templates in views/ | Portal templates in portal/ subdir | Use views/ -- Odoo convention puts all QWeb XML in views/. No separate portal/ directory. |

**Installation:**
```bash
# No new packages needed -- uses existing project dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
python/src/odoo_gen_utils/
├── preprocessors/
│   └── portal.py                    # Portal preprocessor (order=90)
├── templates/shared/
│   ├── portal_controller.py.j2      # Controller class inheriting CustomerPortal
│   ├── portal_home_counter.xml.j2   # /my home entry (inherits portal.portal_my_home)
│   ├── portal_list.xml.j2           # List page template (table + pagination)
│   ├── portal_detail.xml.j2         # Detail page template (card layout)
│   ├── portal_detail_editable.xml.j2 # Detail with form inputs + save
│   └── portal_rules.xml.j2          # Portal record rules
├── spec_schema.py                   # + PortalSpec, PortalPageSpec, PortalActionSpec
├── renderer.py                      # + render_portal() stage, added to pipeline
├── renderer_context.py              # + portal context building
└── validation/
    └── semantic.py                  # + E23 portal ownership path check
python/tests/
├── test_portal_preprocessor.py      # Preprocessor tests
├── test_portal_renderer.py          # Render stage tests
├── test_portal_schema.py            # Pydantic schema tests
└── test_portal_validation.py        # E23 validation tests
```

### Pattern 1: Portal Preprocessor (order=90)
**What:** Validates ownership paths, enriches spec with portal context, auto-adds `"portal"` to depends.
**When to use:** Always runs; no-ops when spec has no `"portal"` key.
**Example:**
```python
# Source: Established project pattern (preprocessors/_registry.py)
@register_preprocessor(order=90, name="portal")
def _process_portal(spec: dict[str, Any]) -> dict[str, Any]:
    portal = spec.get("portal")
    if not portal:
        return spec
    # Validate ownership paths
    models_by_name = {m["name"]: m for m in spec.get("models", [])}
    for page in portal.get("pages", []):
        _validate_ownership_path(page, models_by_name)
    # Enrich spec
    spec = {**spec, "has_portal": True}
    spec["portal_pages"] = portal["pages"]
    spec["portal_auth"] = portal.get("auth", "portal")
    # Auto-add portal dependency
    depends = list(spec.get("depends", ["base"]))
    if "portal" not in depends:
        depends.append("portal")
    spec = {**spec, "depends": depends}
    return spec
```

### Pattern 2: Odoo 17 CustomerPortal Controller (Generated Output)
**What:** The actual Python file generated by `portal_controller.py.j2`.
**When to use:** Every portal module generates exactly one controller file.
**Example:**
```python
# Source: Odoo 17 sale/account portal controller patterns
# (github.com/odoo/odoo/blob/17.0/addons/sale/controllers/portal.py)
from collections import OrderedDict

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class UniStudentPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'enrollment_count' in counters:
            Enrollment = request.env['uni.enrollment']
            enrollment_count = Enrollment.search_count(
                self._get_enrollment_domain()
            ) if Enrollment.check_access_rights('read', raise_exception=False) else 0
            values['enrollment_count'] = enrollment_count
        return values

    def _get_enrollment_domain(self):
        return [('student_id.user_id', '=', request.env.user.id)]

    @http.route(
        ['/my/enrollments', '/my/enrollments/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def portal_my_enrollments(self, page=1, sortby=None, **kw):
        Enrollment = request.env['uni.enrollment']
        domain = self._get_enrollment_domain()
        # --- BUSINESS LOGIC START ---
        # TODO: implement portal_my_enrollments logic
        pass
        # --- BUSINESS LOGIC END ---
        searchbar_sortings = {
            'term_id desc': {'label': 'Term', 'order': 'term_id desc'},
        }
        sort_order = searchbar_sortings.get(sortby, {}).get(
            'order', 'term_id desc'
        )
        enrollment_count = Enrollment.search_count(domain)
        pager = portal_pager(
            url='/my/enrollments',
            total=enrollment_count,
            page=page,
            step=20,
            url_args={'sortby': sortby},
        )
        enrollments = Enrollment.search(
            domain, order=sort_order, limit=20, offset=pager['offset'],
        )
        values = {
            'enrollments': enrollments.sudo(),
            'page_name': 'enrollments',
            'pager': pager,
            'default_url': '/my/enrollments',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        }
        return request.render(
            'uni_student_portal.portal_my_enrollments', values
        )
```

### Pattern 3: QWeb Home Counter Template (Generated Output)
**What:** XPath-based inheritance of `portal.portal_my_home` to add dashboard entries.
**When to use:** For every page with `show_in_home: true`.
**Example:**
```xml
<!-- Source: Odoo 17 sale/views/sale_portal_templates.xml pattern -->
<template id="portal_my_home_enrollments"
          name="Portal: Enrollments"
          inherit_id="portal.portal_my_home"
          customize_show="True" priority="60">
    <xpath expr="//div[hasclass('o_portal_docs')]" position="before">
        <t t-set="portal_client_category_enable" t-value="True"/>
    </xpath>
    <div id="portal_client_category" position="inside">
        <t t-call="portal.portal_docs_entry">
            <t t-set="title">My Enrollments</t>
            <t t-set="url" t-value="'/my/enrollments'"/>
            <t t-set="placeholder_count" t-value="enrollment_count"/>
            <t t-set="icon" t-value="False"/>
            <t t-set="config_card" t-value="True"/>
        </t>
    </div>
</template>
```

### Pattern 4: Portal Record Rules (Generated Output)
**What:** `ir.rule` records for `base.group_portal` with ownership-based domain.
**When to use:** Every portal page generates at least one read-only rule; editable pages add a write rule.
**Example:**
```xml
<!-- Source: Odoo 17 record rule patterns -->
<data noupdate="1">
    <record id="rule_portal_uni_enrollment_read" model="ir.rule">
        <field name="name">Portal: Read Own Enrollments</field>
        <field name="model_id" ref="model_uni_enrollment"/>
        <field name="domain_force">[('student_id.user_id', '=', user.id)]</field>
        <field name="groups" eval="[(4, ref('base.group_portal'))]"/>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="False"/>
        <field name="perm_create" eval="False"/>
        <field name="perm_unlink" eval="False"/>
    </record>
</data>
```

### Pattern 5: Editable Form POST Handler
**What:** Controller route that handles form POST with CSRF protection for editable fields.
**When to use:** Detail pages with `fields_editable`.
**Example:**
```python
# Source: Odoo 17 portal controller pattern for form submission
@http.route('/my/profile', type='http', auth='user', website=True,
            methods=['GET', 'POST'])
def portal_my_profile(self, **post):
    student = request.env['uni.student'].search(
        self._get_student_domain(), limit=1
    )
    if not student:
        return request.redirect('/my')
    if request.httprequest.method == 'POST':
        # CSRF is auto-validated by Odoo for type='http' routes
        allowed_fields = {'phone', 'email', 'address'}
        vals = {k: v for k, v in post.items() if k in allowed_fields}
        # --- BUSINESS LOGIC START ---
        # TODO: validate and write editable fields
        pass
        # --- BUSINESS LOGIC END ---
        student.sudo().write(vals)
        return request.redirect('/my/profile')
    values = {
        'student': student.sudo(),
        'page_name': 'profile',
    }
    return request.render('uni_student_portal.portal_my_profile', values)
```

### Anti-Patterns to Avoid
- **Using `http.Controller` instead of `CustomerPortal`:** Portal controllers MUST inherit `CustomerPortal` to integrate with the portal home, pager, and access control patterns.
- **Skipping `check_access_rights()` in counters:** Always wrap `search_count()` with `check_access_rights('read', raise_exception=False)` to avoid crashing the portal home for users without model access.
- **Hardcoding domains instead of helper methods:** Always use `_get_{model}_domain()` helper methods so domains are reusable and testable. The same domain is used in counters, list pages, and record rules.
- **Using `sudo()` without ownership check:** Never `sudo().browse(id)` without first verifying the record belongs to the current user via domain check or `_document_check_access()`.
- **Putting portal XML in `data/` instead of `views/`:** Portal QWeb templates go in `views/` directory. Record rules go in `security/` directory.
- **Missing `noupdate="1"` on record rules:** Portal record rules MUST be in `<data noupdate="1">` to prevent user customizations from being overwritten on module update.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pagination | Custom page calculation | `pager()` from `odoo.addons.portal.controllers.portal` | Handles edge cases (empty results, out-of-range pages, URL args) |
| Access check | Custom `browse + if` | `_document_check_access(model, id, token)` | Handles access tokens, sudo, MissingError, AccessError consistently |
| PDF download | Custom `_render_qweb_pdf()` call | `_show_report(model, report_type, report_ref, download)` | Handles HTML/PDF/text formats, headers, content-disposition correctly |
| Portal home entry | Custom HTML counter card | `portal.portal_docs_entry` QWeb call template | Consistent styling, responsive, supports icons/counts/labels |
| List table | Custom HTML table | `portal.portal_table` QWeb call template | Responsive, consistent column headers, empty state handling |
| CSRF in forms | Manual token insertion | Odoo auto-validates CSRF for `type='http'` routes; include `<input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>` in QWeb form | Auto-validation by framework, just need hidden field in template |
| Searchbar | Custom filter UI | `portal.portal_searchbar` QWeb call template with searchbar_sortings/searchbar_filters dicts | Standard Odoo portal searchbar with sort/filter/group dropdowns |

**Key insight:** Odoo 17's portal module provides a complete set of controller base methods and QWeb sub-templates. The generated controller should use these building blocks, not replicate their functionality.

## Common Pitfalls

### Pitfall 1: Ownership Path Does Not Terminate at res.users
**What goes wrong:** The spec defines `"ownership": "student_id"` but `student_id` points to `uni.student`, not `res.users`. The record rule domain `[('student_id', '=', user.id)]` compares a `uni.student` ID with a `res.users` ID, silently returning zero records.
**Why it happens:** Spec author confuses the field path from model to the model that has the user field with the field path to the user itself.
**How to avoid:** E23 validation traverses the ownership path through the model registry and verifies the terminal field is of type `Many2one` with `comodel_name='res.users'`.
**Warning signs:** Portal pages show zero records even though the user has data.

### Pitfall 2: Counter Method Crashes Portal Home
**What goes wrong:** `_prepare_home_portal_values()` calls `search_count()` without checking `check_access_rights()`. If the portal user lacks ACL access to the model, the entire `/my` page crashes with AccessError.
**Why it happens:** Developer tests only with admin/internal users, not actual portal users.
**How to avoid:** Always wrap counter search_count in `if Model.check_access_rights('read', raise_exception=False)` with `else 0` fallback. The Jinja template must generate this pattern.
**Warning signs:** `/my` returns 500 error for portal users but works for internal users.

### Pitfall 3: Missing perm_write=False on Read-Only Rules
**What goes wrong:** Record rule defaults to `perm_write=True` in Odoo if not explicitly set. Portal users can modify records they should only be able to read.
**Why it happens:** Omitting `<field name="perm_write" eval="False"/>` relies on Odoo defaults, which default all perms to True.
**How to avoid:** The `portal_rules.xml.j2` template must ALWAYS explicitly set all four permission fields. Read-only rule: read=True, write/create/unlink=False.
**Warning signs:** No visible error, but portal users can write to records via API calls.

### Pitfall 4: Missing model_id ref Format for ir.rule
**What goes wrong:** Using `ref="uni.enrollment"` (Odoo model name) instead of `ref="model_uni_enrollment"` (XML ID format for model references). The record rule fails to install.
**Why it happens:** Confusion between Odoo model names (`uni.enrollment`) and ir.model XML IDs (`model_uni_enrollment`).
**How to avoid:** The template must use the `model_ref` Jinja filter (already exists in the project) to convert `uni.enrollment` to the correct `model_uni_enrollment` XML ID format. For cross-module models, use `module.model_model_name` format.
**Warning signs:** Module install fails with "ValueError: External ID not found" for record rules.

### Pitfall 5: portal_docs_entry Not Showing on /my Home
**What goes wrong:** Counter entry does not appear on the portal home page even though the template is installed.
**Why it happens:** The `portal_client_category_enable` (or other category enable) context variable is not set to True in the inheriting template. Since Odoo 17, the home page uses category divs that are hidden by default.
**How to avoid:** The home counter template must include `<t t-set="portal_client_category_enable" t-value="True"/>` before the category div insertion via xpath. This enables the category container div.
**Warning signs:** No error, but the portal home shows no entries for the module.

### Pitfall 6: Editable Fields Allow Writing Arbitrary Data
**What goes wrong:** The POST handler writes all form fields to the model without validating which fields are allowed to be edited.
**Why it happens:** Using `record.write(post)` without filtering to only the `fields_editable` whitelist.
**How to avoid:** The controller template must generate an explicit `allowed_fields` set from the spec's `fields_editable` list and filter POST data against it before writing.
**Warning signs:** Security vulnerability -- portal users can modify any field by crafting POST parameters.

## Code Examples

### Odoo 17 Portal pager() Usage
```python
# Source: Odoo 17 addons/portal/controllers/portal.py
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

# In list page method:
pager_values = portal_pager(
    url='/my/enrollments',
    total=enrollment_count,       # from search_count(domain)
    page=page,                    # from route parameter
    step=20,                      # items per page
    url_args={'sortby': sortby},  # preserved in pagination links
)
enrollments = Model.search(
    domain,
    order=sort_order,
    limit=20,
    offset=pager_values['offset'],  # computed by pager
)
```

### Odoo 17 _document_check_access() for Detail Pages
```python
# Source: Odoo 17 addons/account/controllers/portal.py
@http.route('/my/enrollment/<int:enrollment_id>', type='http',
            auth='user', website=True)
def portal_enrollment_detail(self, enrollment_id, **kw):
    try:
        enrollment_sudo = self._document_check_access(
            'uni.enrollment', enrollment_id
        )
    except (AccessError, MissingError):
        return request.redirect('/my')
    values = self._get_page_view_values(
        enrollment_sudo, None,
        {'enrollment': enrollment_sudo, 'page_name': 'enrollment'},
        'my_enrollments_history', False,
    )
    return request.render(
        'uni_student_portal.portal_enrollment_detail', values
    )
```

### Odoo 17 PDF Report Download via _show_report()
```python
# Source: Odoo 17 addons/sale/controllers/portal.py
@http.route('/my/fee/<int:invoice_id>/download_challan', type='http',
            auth='user', website=True)
def portal_fee_download_challan(self, invoice_id, **kw):
    try:
        invoice_sudo = self._document_check_access(
            'fee.invoice', invoice_id
        )
    except (AccessError, MissingError):
        return request.redirect('/my')
    return self._show_report(
        model=invoice_sudo,
        report_type='pdf',
        report_ref='uni_fee.report_fee_challan',
        download=True,
    )
```

### QWeb List Page with portal_table
```xml
<!-- Source: Odoo 17 sale/views/sale_portal_templates.xml pattern -->
<template id="portal_my_enrollments" name="My Enrollments">
    <t t-call="portal.portal_layout">
        <t t-set="breadcrumbs_searchbar" t-value="True"/>
        <t t-call="portal.portal_searchbar">
            <t t-set="title">My Enrollments</t>
        </t>
        <t t-if="not enrollments">
            <div class="alert alert-info">No enrollments found.</div>
        </t>
        <t t-if="enrollments" t-call="portal.portal_table">
            <thead>
                <tr>
                    <th>Course</th>
                    <th>Term</th>
                    <th>Status</th>
                    <th>Grade</th>
                </tr>
            </thead>
            <tbody>
                <t t-foreach="enrollments" t-as="enrollment">
                    <tr>
                        <td>
                            <a t-attf-href="/my/enrollment/#{enrollment.id}">
                                <t t-out="enrollment.course_id.display_name"/>
                            </a>
                        </td>
                        <td><t t-out="enrollment.term_id.display_name"/></td>
                        <td>
                            <span t-attf-class="badge #{
                                'bg-info' if enrollment.state == 'confirmed'
                                else 'bg-success' if enrollment.state == 'done'
                                else 'bg-secondary'
                            }">
                                <t t-out="enrollment.state"/>
                            </span>
                        </td>
                        <td><t t-out="enrollment.grade"/></td>
                    </tr>
                </t>
            </tbody>
        </t>
    </t>
</template>
```

### QWeb Editable Detail with CSRF Form
```xml
<!-- Source: Odoo portal form pattern -->
<template id="portal_my_profile" name="My Profile">
    <t t-call="portal.portal_layout">
        <t t-set="breadcrumbs_searchbar" t-value="True"/>
        <t t-call="portal.portal_searchbar">
            <t t-set="title">My Profile</t>
        </t>
        <div class="card">
            <div class="card-body">
                <!-- Read-only fields -->
                <div class="row mb-2">
                    <div class="col-4 fw-bold">Name</div>
                    <div class="col-8" t-field="student.name"/>
                </div>
                <!-- Editable fields via form -->
                <form method="POST" t-attf-action="/my/profile">
                    <input type="hidden" name="csrf_token"
                           t-att-value="request.csrf_token()"/>
                    <div class="row mb-2">
                        <label class="col-4 fw-bold" for="phone">Phone</label>
                        <div class="col-8">
                            <input type="text" name="phone" class="form-control"
                                   t-att-value="student.phone"/>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">Save</button>
                </form>
            </div>
        </div>
    </t>
</template>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `http.Controller` for portal | `CustomerPortal` inheritance | Odoo 12+ (stable through 17) | All portal modules inherit CustomerPortal for consistent home/pager/access |
| Manual pagination HTML | `pager()` + `portal.portal_table` template | Odoo 13+ | Consistent responsive pagination across all portal pages |
| Global record rules | Group-scoped `base.group_portal` rules | Odoo 10+ | Portal rules only apply to portal users, not internal users |
| `render_qweb_pdf()` directly | `_show_report()` method on CustomerPortal | Odoo 14+ | Handles HTML/PDF/text, content headers, download flag automatically |
| Flat `/my` home page | Category-based portal_my_home (alert, client, service, vendor, common) | Odoo 17 | Must set category_enable flag to show entries in correct category |

**Deprecated/outdated:**
- `website_portal` module: Merged into `portal` in Odoo 12+. Import from `odoo.addons.portal.controllers.portal`, not website_portal.
- Direct `request.website.pager()`: Use `pager` imported from portal controller module, aliased as `portal_pager`.

## Open Questions

1. **Which portal_my_home category div to use**
   - What we know: Odoo 17 has 5 category divs: `portal_alert_category`, `portal_client_category`, `portal_service_category`, `portal_vendor_category`, `portal_common_category`
   - What's unclear: Which category is most appropriate for arbitrary generated modules
   - Recommendation: Use `portal_client_category` as default (matches sale/account pattern). Could make configurable in spec later but unnecessary complexity for Phase 62.

2. **E23 validation: use model registry or spec models**
   - What we know: Ownership paths may traverse models defined in the SAME module (in spec) or in external modules (in registry). Need both sources.
   - What's unclear: Registry may not be loaded during validation if running standalone.
   - Recommendation: E23 should try registry first (for cross-module resolution), fall back to spec models for same-module resolution. Accept LOW confidence validation when neither source can resolve a hop. This matches the E19 dot-path pattern from computation chains.

3. **Portal template output location within generated module**
   - What we know: Odoo convention puts QWeb templates in `views/` directory. Portal rules go in `security/`.
   - What's unclear: Whether to use a subdirectory like `views/portal/` or flat `views/`.
   - Recommendation: Use flat `views/` directory with prefixed filenames: `views/portal_home.xml`, `views/portal_enrollments.xml`, `views/portal_enrollment_detail.xml`. This follows Odoo's standard module layout.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | python/pyproject.toml (`[tool.pytest.ini_options]`) |
| Quick run command | `cd python && python -m pytest tests/test_portal_preprocessor.py tests/test_portal_renderer.py tests/test_portal_schema.py tests/test_portal_validation.py -x -q` |
| Full suite command | `cd python && python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRTL-01 | Controller inherits CustomerPortal, has routes, auth decorators, domain helpers, stub zones | unit | `cd python && python -m pytest tests/test_portal_renderer.py -x -q` | -- Wave 0 |
| PRTL-01 | Counter method uses check_access_rights pattern | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_counter_method_pattern -x -q` | -- Wave 0 |
| PRTL-02 | QWeb templates inherit portal.portal_my_home, use portal_docs_entry, portal_table, portal_searchbar | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_qweb_home_counter -x -q` | -- Wave 0 |
| PRTL-02 | List page has pagination, empty state, column headers from list_fields | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_qweb_list_page -x -q` | -- Wave 0 |
| PRTL-02 | Detail page has card layout, sidebar, back button, badge styling | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_qweb_detail_page -x -q` | -- Wave 0 |
| PRTL-02 | Editable detail page has CSRF form, input fields, save button | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_qweb_editable_detail -x -q` | -- Wave 0 |
| PRTL-03 | Record rules use base.group_portal, correct domain_force, noupdate="1" | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_portal_record_rules -x -q` | -- Wave 0 |
| PRTL-03 | Read-only rules: perm_read=True, others False; write rules for editable models | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_portal_rule_permissions -x -q` | -- Wave 0 |
| PRTL-03 | Multi-hop ownership paths generate correct domain expressions | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_multihop_ownership -x -q` | -- Wave 0 |
| E23 | Ownership path validation traverses model chain, terminates at res.users | unit | `cd python && python -m pytest tests/test_portal_validation.py -x -q` | -- Wave 0 |
| Schema | PortalSpec/PortalPageSpec/PortalActionSpec Pydantic models validate correctly | unit | `cd python && python -m pytest tests/test_portal_schema.py -x -q` | -- Wave 0 |
| Preprocessor | Portal preprocessor at order=90, enriches spec, adds portal dependency | unit | `cd python && python -m pytest tests/test_portal_preprocessor.py -x -q` | -- Wave 0 |
| Integration | Full portal spec renders complete module with controller+templates+rules | integration | `cd python && python -m pytest tests/test_portal_renderer.py::test_full_portal_render -x -q` | -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && python -m pytest tests/test_portal_preprocessor.py tests/test_portal_renderer.py tests/test_portal_schema.py tests/test_portal_validation.py -x -q`
- **Per wave merge:** `cd python && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_portal_preprocessor.py` -- covers preprocessor order=90, spec enrichment, dependency injection
- [ ] `tests/test_portal_renderer.py` -- covers render_portal() output, controller content, QWeb content, rule content
- [ ] `tests/test_portal_schema.py` -- covers PortalSpec, PortalPageSpec, PortalActionSpec Pydantic models
- [ ] `tests/test_portal_validation.py` -- covers E23 ownership path validation
- [ ] Test fixtures: portal spec fixture (uni_student_portal with 4 pages from CONTEXT.md)

## Sources

### Primary (HIGH confidence)
- Odoo 17 portal controller source: `github.com/odoo/odoo/blob/17.0/addons/portal/controllers/portal.py` -- CustomerPortal class, pager(), _document_check_access(), _prepare_home_portal_values()
- Odoo 17 sale portal controller: `github.com/odoo/odoo/blob/17.0/addons/sale/controllers/portal.py` -- Complete list/detail/counter/report pattern
- Odoo 17 account portal controller: `github.com/odoo/odoo/blob/17.0/addons/account/controllers/portal.py` -- Counter domain helpers, filter patterns
- Odoo 17 portal templates: `github.com/odoo/odoo/blob/17.0/addons/portal/views/portal_templates.xml` -- portal_my_home, portal_docs_entry, portal_table, portal_searchbar, portal_sidebar
- Odoo 17 official docs: `odoo.com/documentation/17.0/developer/tutorials/restrict_data_access.html` -- Record rules XML format

### Secondary (MEDIUM confidence)
- [Odoo Portal Customization Guide - teguhteja.id](https://teguhteja.id/odoo-portal-customization-guide/) -- QWeb template inheritance patterns
- [PDF Report Download on Portal - Cybrosys](https://www.cybrosys.com/blog/how-to-add-a-pdf-report-download-button-to-the-odoo-17-customer-portal) -- _render_qweb_pdf / _show_report pattern
- [Pagination in Portal - Cybrosys](https://www.cybrosys.com/blog/how-to-add-pagination-in-website-portal-in-odoo-17) -- pager() usage
- [Record Rules in Odoo 17 - Cybrosys](https://www.cybrosys.com/blog/how-to-create-record-rules-in-odoo-17) -- ir.rule XML format

### Tertiary (LOW confidence)
- None -- all findings verified with official Odoo source code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Odoo 17 portal patterns are stable and well-documented. No new dependencies needed.
- Architecture: HIGH -- The project's preprocessor + Jinja template + render stage pattern is proven across 7+ prior phases. Portal follows the same architecture.
- Pitfalls: HIGH -- All pitfalls verified against actual Odoo 17 source code behavior (search_count access check, perm defaults, model_ref format, category_enable flags).

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (Odoo 17 portal API is stable, no breaking changes expected)
