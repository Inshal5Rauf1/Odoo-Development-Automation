# Phase 9: Edition & Version Support - Research

**Researched:** 2026-03-03
**Domain:** Odoo CE/EE edition detection, multi-version module generation (17.0 + 18.0)
**Confidence:** MEDIUM-HIGH

## Summary

Phase 9 adds two capabilities to odoo-gen: (1) Enterprise/Community edition awareness -- detecting when a user's spec requires Enterprise-only modules and suggesting Community alternatives, and (2) Odoo 18.0 support alongside the existing 17.0 target -- generating syntactically correct modules for either version.

The Enterprise vs Community distinction is well-documented: approximately 30+ modules are Enterprise-only, and the OCA ecosystem provides Community alternatives for most of them. The key implementation challenge is maintaining a curated registry of Enterprise module technical names and their OCA replacements, plus wiring edition checks into the spec validation flow.

The 17.0-to-18.0 gap is more significant than typical minor version changes. Odoo 18.0 introduces breaking changes: `<tree>` becomes `<list>`, `view_mode` values change from `tree,form` to `list,form`, the Python `states` parameter on field definitions is removed, `group_operator` is renamed to `aggregator`, `_name_search` is replaced by `_search_display_name`, the `numbercall` field on `ir.cron` is removed, and access control methods are consolidated. These differences require version-conditional templates and version-aware knowledge base content.

**Primary recommendation:** Use a version-specific template directory strategy (`templates/17.0/` and `templates/18.0/`) for templates that differ between versions, with shared templates for identical content. Maintain the Enterprise module registry as a JSON data file loaded by the renderer and spec validator.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VERS-01 | System knows which Odoo modules are Enterprise-only | Enterprise module registry JSON with ~35 entries, sourced from official Odoo editions comparison + OCA ecosystem research |
| VERS-02 | System flags when user's description requires Enterprise-only dependencies | Spec validation step that checks `depends` list against Enterprise registry |
| VERS-03 | System offers Community-compatible alternatives when Enterprise dependencies detected | OCA alternative mapping in the same registry JSON (Enterprise technical name -> OCA replacement + notes) |
| VERS-04 | System supports generating modules for Odoo 18.0 in addition to 17.0 | Version-specific templates for views (tree->list), models (states removal), manifest (version prefix), actions (view_mode) |
| VERS-05 | System uses version-specific templates and syntax rules per target version | Template directory strategy with version selection in renderer.py based on `odoo_version` from spec/config |
| VERS-06 | User can specify target Odoo version via config or command parameter | Config already has `odoo_version` field in defaults.json; needs wiring through renderer and agent workflows |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | >=3.1 | Template rendering with version selection | Already in use; template inheritance supports version branching |
| click | >=8.0 | CLI parameter for version override | Already in use for odoo-gen-utils CLI |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | - | Enterprise module registry data | Load/parse the edition registry file |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate template dirs per version | Jinja2 template inheritance (base + override) | Template inheritance is harder to reason about for XML; separate dirs are explicit and debuggable |
| Hardcoded Enterprise list in Python | JSON data file | JSON is editable by non-developers, extensible, and separates data from logic |
| Full Odoo 18 Docker validation | Odoo 18 Docker image alongside 17 | Worth adding but can be deferred -- template correctness is the priority |

**Installation:**
No new dependencies. All work uses existing Jinja2 + click + json stdlib.

## Architecture Patterns

### Recommended Project Structure

```
python/src/odoo_gen_utils/
  templates/
    17.0/                    # Version-specific templates for 17.0
      view_form.xml.j2       # Uses <tree> tag
      view_tree.xml.j2       # Uses <tree> tag
      action.xml.j2          # view_mode="tree,form"
      manifest.py.j2         # version="17.0.X.Y.Z"
      model.py.j2            # Supports states= param (existing)
    18.0/                    # Version-specific templates for 18.0
      view_form.xml.j2       # Uses <list> tag
      view_tree.xml.j2       # Uses <list> tag (standalone)
      action.xml.j2          # view_mode="list,form"
      manifest.py.j2         # version="18.0.X.Y.Z"
      model.py.j2            # No states= param, aggregator not group_operator
    shared/                  # Version-independent templates
      access_csv.j2          # Same across versions
      init_models.py.j2      # Same across versions
      init_root.py.j2        # Same across versions
      init_tests.py.j2       # Same across versions
      init_wizards.py.j2     # Same across versions
      menu.xml.j2            # Same across versions
      readme.rst.j2          # Same across versions
      security_group.xml.j2  # Same across versions
      record_rules.xml.j2    # Same across versions
      sequences.xml.j2       # Same across versions
      demo_data.xml.j2       # Same across versions
      wizard.py.j2           # Same across versions
      wizard_form.xml.j2     # Same across versions
      test_model.py.j2       # Same across versions
  data/
    enterprise_modules.json  # Enterprise module registry + OCA alternatives

knowledge/
  models.md                  # Add "Changed in 18.0" section
  views.md                   # Add "Changed in 18.0" section
  manifest.md                # Add "Changed in 18.0" section
  MASTER.md                  # Update to mention 18.0 support
```

### Pattern 1: Version-Aware Template Resolution

**What:** The renderer selects templates from the correct version directory, falling back to shared/ for templates that are identical across versions.

**When to use:** Every call to `render_module()` and `render_template()`.

**Example:**
```python
# In renderer.py
def get_versioned_template_dir(version: str) -> Path:
    """Return the template directory for the given Odoo version.

    Resolution order:
    1. templates/{version}/ -- version-specific template
    2. templates/shared/    -- shared template
    """
    base = Path(__file__).parent / "templates"
    return base / version


def create_versioned_renderer(version: str) -> Environment:
    """Create Jinja2 Environment that searches version-specific then shared templates."""
    base = Path(__file__).parent / "templates"
    version_dir = base / version
    shared_dir = base / "shared"

    loader = FileSystemLoader([str(version_dir), str(shared_dir)])
    env = Environment(
        loader=loader,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # Register filters
    env.filters["model_ref"] = _model_ref
    env.filters["to_class"] = _to_class
    env.filters["to_python_var"] = _to_python_var
    env.filters["to_xml_id"] = _to_xml_id
    return env
```

### Pattern 2: Enterprise Module Registry

**What:** A JSON data file mapping Enterprise module technical names to metadata and Community alternatives.

**When to use:** During spec validation (VERS-01, VERS-02, VERS-03) and spec follow-up questions.

**Example:**
```json
{
  "enterprise_modules": {
    "helpdesk": {
      "display_name": "Helpdesk",
      "category": "Services",
      "description": "Ticket tracking and resolution",
      "community_alternative": {
        "oca_module": "helpdesk_mgmt",
        "oca_repo": "OCA/helpdesk",
        "notes": "OCA helpdesk_mgmt provides ticket CRUD, stages, and assignment. Missing: SLA tracking, customer portal."
      }
    },
    "account_asset": {
      "display_name": "Assets Management",
      "category": "Accounting",
      "description": "Fixed asset tracking and depreciation",
      "community_alternative": {
        "oca_module": "account_asset_management",
        "oca_repo": "OCA/account-financial-tools",
        "notes": "Full-featured asset management with enhanced depreciation methods."
      }
    }
  }
}
```

### Pattern 3: Version-Conditional Spec Context

**What:** The `_build_model_context()` and `render_module()` functions read `odoo_version` from the spec and pass it to templates as context.

**When to use:** All template rendering.

**Example:**
```python
def render_module(spec: dict, template_dir: Path, output_dir: Path) -> list[Path]:
    version = spec.get("odoo_version", "17.0")
    env = create_versioned_renderer(version)
    # ... rest of rendering with version-aware templates
```

### Anti-Patterns to Avoid

- **Inline version conditionals in templates:** Do NOT use `{% if odoo_version == '18.0' %}` inside a single template to handle both versions. This creates unreadable, unmaintainable templates. Use separate template files per version instead.
- **Hardcoding Enterprise module list in Python code:** Keep the registry as data (JSON), not code. The list changes with each Odoo release.
- **Assuming 18.0 is just "tree -> list":** There are at least 10 distinct breaking changes between 17.0 and 18.0. Each needs its own handling.
- **Mutating the existing 17.0 templates:** The current templates work correctly for 17.0. Copy them to `templates/17.0/` and create separate 18.0 variants. Never modify the originals in a way that breaks existing 17.0 generation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Enterprise module list | Manual research every time | Curated JSON registry file | Enterprise modules change per Odoo release; a data file is maintainable and versionable |
| 17-to-18 migration transformations | Custom regex-based migration script | Separate template sets per version | The Odoo upgrade_code tool has known bugs with regex-based tree->list. Template separation is deterministic |
| Version validation for generated code | Custom syntax checker | pylint-odoo (already integrated) + version-specific Docker images | pylint-odoo already catches version-specific issues |
| OCA alternative discovery | Live GitHub search per request | Static mapping in enterprise_modules.json | OCA alternatives are stable and well-known; live search is slow and fragile |

**Key insight:** The version differences are finite and well-documented. A data-driven approach (JSON registry for Enterprise modules, separate template directories for versions) is far more reliable than trying to dynamically transform code between versions.

## Common Pitfalls

### Pitfall 1: tree vs list Tag -- Odoo 18 Hard Error
**What goes wrong:** Using `<tree>` in Odoo 18.0 views causes `ValueError: Wrong value for ir.ui.view.type: 'tree'`. This is a hard error, not a warning.
**Why it happens:** Odoo 18 completely removed the `tree` view type from the registry. The `<tree>` tag is not accepted at all.
**How to avoid:** 18.0 templates MUST use `<list>` everywhere: in XML arch, in `view_mode` fields of actions, and in `ir.ui.view` type fields.
**Warning signs:** Any template or generated file containing `<tree` or `view_mode.*tree` when targeting 18.0.

### Pitfall 2: view_mode in Actions Must Also Change
**What goes wrong:** Changing `<tree>` to `<list>` in XML views but leaving `view_mode="tree,form"` in action definitions.
**Why it happens:** Developers focus on view arch XML and forget action definitions also reference view types.
**How to avoid:** The action.xml.j2 template for 18.0 must use `view_mode="list,form"` (not `tree,form`).
**Warning signs:** Module installs but the action window shows no list view.

### Pitfall 3: Python `states` Parameter Removed in 18.0
**What goes wrong:** Field definitions using `states={'posted': [('readonly', True)]}` cause errors in Odoo 18.
**Why it happens:** Odoo 18 removed the `states` parameter from Python field definitions entirely. Conditional field behavior must be handled in XML views using `readonly="state == 'posted'"`.
**How to avoid:** 18.0 model.py.j2 template must not emit `states=` on any field. Current 17.0 templates don't use `states` either (they use inline XML modifiers), so this is mostly about preventing future additions from breaking 18.0.
**Warning signs:** `AttributeError` or `TypeError` on field definitions with `states=` parameter.

### Pitfall 4: group_operator Renamed to aggregator in 18.0
**What goes wrong:** Fields using `group_operator="avg"` silently ignore the parameter in Odoo 18.
**Why it happens:** Renamed to `aggregator` for clarity.
**How to avoid:** 18.0 templates should use `aggregator=` instead of `group_operator=`. Current templates don't use either, but knowledge base should document this for agent-generated code.
**Warning signs:** Aggregation in tree/list views not working as expected.

### Pitfall 5: _name_search Replaced by _search_display_name in 18.0
**What goes wrong:** Custom `_name_search()` overrides are ignored in Odoo 18.
**Why it happens:** Method was replaced with `_search_display_name()` for broader search capability.
**How to avoid:** Knowledge base must document this for agents that generate custom search behavior.
**Warning signs:** Many2one dropdown search not finding expected records.

### Pitfall 6: Chatter Syntax Difference
**What goes wrong:** Using `<div class="oe_chatter">...</div>` in Odoo 17 when `<chatter/>` shorthand is available, or vice versa.
**Why it happens:** Both syntaxes work in 17.0, but `<chatter/>` is the preferred/only form in 18.0.
**How to avoid:** Current 17.0 templates already use the verbose `<div class="oe_chatter">` form. This still works in 18.0 but is unnecessary. For 18.0 templates, use `<chatter/>` exclusively.
**Warning signs:** Extra verbose XML in 18.0 modules.

### Pitfall 7: Enterprise Module Names are NOT Obvious
**What goes wrong:** Assuming "helpdesk" is available on Community and generating a module with `"depends": ["helpdesk"]`.
**Why it happens:** Enterprise module names look like regular module names. There's no runtime check until install fails.
**How to avoid:** Check spec `depends` against enterprise_modules.json registry BEFORE generation.
**Warning signs:** Module install failure with "Module not found: helpdesk" on Community instances.

### Pitfall 8: numbercall Field Removed in ir.cron (18.0)
**What goes wrong:** Data files defining scheduled actions with `<field name='numbercall'>-1</field>` cause errors in 18.0.
**Why it happens:** The `numbercall` field was removed from `ir.cron` in Odoo 18.
**How to avoid:** 18.0 data templates must not include `numbercall` in cron record definitions.
**Warning signs:** XML parsing errors when loading scheduled action data files.

### Pitfall 9: Access Control API Changes (18.0)
**What goes wrong:** Using `check_access_rights('read')` + `check_access_rule('read')` separately in 18.0.
**Why it happens:** 18.0 consolidated these into `record.check_access("read")`.
**How to avoid:** Knowledge base must document the new unified API for generated business logic.
**Warning signs:** `AttributeError` on `check_access_rights` in Odoo 18 custom code.

## Code Examples

### Example 1: Version-Specific Tree/List View (18.0)

```xml
{# view_form.xml.j2 for Odoo 18.0 -- Uses <list> instead of <tree> #}
    <!-- Tree View (Odoo 18.0: <list> tag) -->
    <record id="view_{{ model_name | to_xml_id }}_list" model="ir.ui.view">
        <field name="name">{{ model_name }}.view.list</field>
        <field name="model">{{ model_name }}</field>
        <field name="arch" type="xml">
            <list string="{{ model_description }}">
{% for field in fields %}
{% if field.type not in ('One2many', 'Html', 'Text') %}
{% if loop.index0 < 6 %}
                <field name="{{ field.name }}"{% if loop.index0 >= 4 %} optional="hide"{% endif %}/>
{% endif %}
{% endif %}
{% endfor %}
            </list>
        </field>
    </record>
```

### Example 2: Version-Specific Action (18.0)

```xml
{# action.xml.j2 for Odoo 18.0 -- view_mode uses "list" not "tree" #}
<record id="{{ model_name | to_xml_id }}_action" model="ir.actions.act_window">
    <field name="name">{{ model_description }}</field>
    <field name="res_model">{{ model_name }}</field>
    <field name="view_mode">list,form</field>
</record>
```

### Example 3: Version-Specific Manifest (18.0)

```python
{# manifest.py.j2 for Odoo 18.0 -- version prefix is 18.0 #}
{
    "name": "{{ module_title }}",
    "version": "{{ odoo_version }}.1.0.0",
    ...
}
```
Note: The manifest template already uses `{{ odoo_version }}` so the version prefix is dynamic. This template can remain shared if we ensure `odoo_version` is correctly set in the spec context.

### Example 4: Enterprise Module Check

```python
def check_enterprise_dependencies(
    depends: list[str],
    registry_path: Path,
) -> list[dict]:
    """Check if any dependencies are Enterprise-only modules.

    Returns list of dicts with keys: module, display_name, alternative.
    Empty list means all dependencies are Community-safe.
    """
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    enterprise_modules = registry.get("enterprise_modules", {})

    warnings = []
    for dep in depends:
        if dep in enterprise_modules:
            entry = enterprise_modules[dep]
            alt = entry.get("community_alternative", {})
            warnings.append({
                "module": dep,
                "display_name": entry.get("display_name", dep),
                "alternative": alt.get("oca_module"),
                "alternative_repo": alt.get("oca_repo"),
                "notes": alt.get("notes", ""),
            })
    return warnings
```

### Example 5: Chatter Template Difference

```xml
{# 17.0 chatter (existing) -- verbose form #}
{% if 'mail' in depends %}
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="message_ids"/>
                </div>
{% endif %}

{# 18.0 chatter -- shorthand form #}
{% if 'mail' in depends %}
                <chatter/>
{% endif %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `<tree>` tag for list views | `<list>` tag | Odoo 18.0 (Oct 2024) | Breaking -- `<tree>` causes ValueError in 18.0 |
| `view_mode="tree,form"` | `view_mode="list,form"` | Odoo 18.0 | Breaking -- action views broken if not updated |
| `states=` param on Python fields | Removed; use XML `readonly`/`invisible` | Odoo 18.0 | Breaking -- parameter not recognized |
| `group_operator=` on fields | `aggregator=` | Odoo 18.0 | Silent failure -- aggregation stops working |
| `_name_search()` method | `_search_display_name()` | Odoo 18.0 | Custom name search overrides ignored |
| `check_access_rights()` + `check_access_rule()` | `record.check_access()` | Odoo 18.0 | Old methods deprecated |
| `numbercall` field on ir.cron | Removed | Odoo 18.0 | Data files with numbercall cause errors |
| `<div class="oe_chatter">...` | `<chatter/>` shorthand | Odoo 17.0+ (preferred in 18.0) | Both work in 17; shorthand preferred in 18 |
| `attrs` dict in XML views | Inline expressions | Odoo 17.0 | Already handled by current 17.0 templates |
| `name_get()` method | `display_name` field read | Odoo 18.0 | `name_get()` deprecated |

**Deprecated/outdated:**
- `<tree>` XML tag: Removed in 18.0, use `<list>`
- `states` field parameter: Removed in 18.0
- `group_operator` field attribute: Renamed to `aggregator` in 18.0
- `_name_search()`: Replaced by `_search_display_name()` in 18.0
- `numbercall` on ir.cron: Removed in 18.0

## Enterprise Module Registry

### Enterprise-Only Modules (Verified)

The following modules are available ONLY in Odoo Enterprise Edition. This registry should be stored as `data/enterprise_modules.json`:

**Accounting & Finance:**
- `account_asset` -- Asset Management and Depreciation
- `account_accountant` -- Full Accounting (Invoicing is CE, full accounting is EE)

**Services:**
- `helpdesk` -- Ticket Management
- `planning` -- Team Scheduling and Resource Planning
- `field_service` -- On-site Service Management
- `appointment` -- Online Appointment Booking
- `timesheet_grid` -- Timesheet Grid View (base timesheets is CE)

**HR:**
- `payroll` -- Payroll Management
- `appraisals` -- Employee Appraisals (with advanced features)

**Manufacturing & Supply Chain:**
- `quality_control` / `quality` -- Quality Management
- `mrp_workorder` -- Work Orders (MRP Shop Floor)
- `stock_barcode` -- Barcode Scanner for Inventory
- `mrp_plm` -- Product Lifecycle Management
- `mrp_mps` -- Master Production Schedule

**Marketing:**
- `marketing_automation` -- Marketing Automation Workflows
- `social_marketing` -- Social Media Management

**Websites:**
- `website_studio` -- Studio for Website Customization

**Productivity:**
- `documents` -- Document Management System
- `sign` -- Electronic Signatures
- `knowledge` -- Knowledge Base / Wiki
- `voip` -- VoIP Phone Integration
- `data_cleaning` -- Data Deduplication and Cleaning

**Customization:**
- `web_studio` -- Odoo Studio (visual customizer)

**Views (EE-only view types):**
- `web_dashboard` -- Dashboard View
- `web_map` -- Map View
- `web_cohort` -- Cohort Analysis View
- `web_gantt` -- Gantt View (basic) is CE, advanced features EE

**Other:**
- `iot` -- IoT Box Integration
- `rental` -- Rental Management
- `subscriptions` / `sale_subscription` -- Subscription Management

### OCA Community Alternatives

| Enterprise Module | OCA Alternative | OCA Repository | Coverage |
|-------------------|----------------|----------------|----------|
| `helpdesk` | `helpdesk_mgmt` | OCA/helpdesk | Tickets, stages, assignment. Missing: SLA, portal |
| `account_asset` | `account_asset_management` | OCA/account-financial-tools | Full-featured, often exceeds EE version |
| `quality_control` | `quality_control_oca` | OCA/manufacture | Basic quality checks |
| `documents` | `dms` | OCA/dms | Document management system |
| `sign` | No direct OCA equivalent | - | Use third-party (signrequest, etc.) |
| `planning` | `project_forecast` | OCA/project | Resource scheduling |
| `rental` | `rental` | OCA/rental | Basic rental flows |
| `voip` | No direct OCA equivalent | - | Use third-party SIP integration |
| `web_studio` | No alternative | - | Manual customization required |
| `payroll` | `payroll_account` (partial) | OCA/payroll | Country-specific localizations needed |

**Confidence:** MEDIUM -- Enterprise module list is based on multiple sources (Syncoria, Cybrosys, Odoo editions page, OCA repos). Some module technical names may have been renamed across Odoo versions. The OCA alternative list is from OCA GitHub repos.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `python/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd python && uv run pytest tests/ -x -q` |
| Full suite command | `cd python && uv run pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VERS-01 | Enterprise module registry loads and contains known EE modules | unit | `cd python && uv run pytest tests/test_edition.py::test_registry_loads -x` | Wave 0 |
| VERS-02 | Spec with EE dependency flagged | unit | `cd python && uv run pytest tests/test_edition.py::test_enterprise_dep_flagged -x` | Wave 0 |
| VERS-03 | Community alternative returned for flagged EE module | unit | `cd python && uv run pytest tests/test_edition.py::test_community_alternative -x` | Wave 0 |
| VERS-04 | render_module produces valid 18.0 output (list tag, view_mode) | unit | `cd python && uv run pytest tests/test_renderer.py::TestRenderModule18 -x` | Wave 0 |
| VERS-05 | Version-specific template selection works (17 gets tree, 18 gets list) | unit | `cd python && uv run pytest tests/test_renderer.py::TestVersionedTemplates -x` | Wave 0 |
| VERS-06 | odoo_version from config/spec flows through to renderer | integration | `cd python && uv run pytest tests/test_renderer.py::TestVersionConfig -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && uv run pytest tests/ -x -q`
- **Per wave merge:** `cd python && uv run pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `python/tests/test_edition.py` -- covers VERS-01, VERS-02, VERS-03 (Enterprise registry and dependency checking)
- [ ] `python/tests/test_renderer.py::TestRenderModule18` -- covers VERS-04 (18.0 output validation)
- [ ] `python/tests/test_renderer.py::TestVersionedTemplates` -- covers VERS-05 (template selection)
- [ ] `python/tests/test_renderer.py::TestVersionConfig` -- covers VERS-06 (config flow)
- [ ] `python/src/odoo_gen_utils/data/enterprise_modules.json` -- registry data file
- [ ] `python/src/odoo_gen_utils/templates/18.0/` -- version-specific template directory
- [ ] `python/src/odoo_gen_utils/templates/shared/` -- shared template directory
- [ ] `python/src/odoo_gen_utils/templates/17.0/` -- current templates moved here

## Open Questions

1. **Docker validation for 18.0**
   - What we know: Phase 3 built Docker validation targeting Odoo 17.0 (`odoo:17.0` image). Odoo 18.0 has a corresponding `odoo:18.0` Docker image.
   - What's unclear: Should Phase 9 also add 18.0 Docker validation, or defer to a future phase? Adding it requires a second Docker image and potentially longer validation times.
   - Recommendation: Defer 18.0 Docker validation. Focus Phase 9 on template correctness. Document as known limitation. The pylint-odoo checks + template correctness cover the immediate need.

2. **Knowledge base 18.0 sections**
   - What we know: Each KB file has a "Changed in 17.0" section. Agents reference these during generation.
   - What's unclear: How much 18.0 content should KB files contain? Full 18.0 coverage or just "Changed in 18.0" deltas?
   - Recommendation: Add "Changed in 18.0" delta sections to each KB file (same pattern as "Changed in 17.0"). Keep 17.0 as the base. This is consistent with the existing pattern and keeps KB files focused.

3. **OCA alternative accuracy**
   - What we know: OCA repos exist for helpdesk, account_asset, documents, etc.
   - What's unclear: Whether specific OCA alternatives are available for ALL Odoo versions (some only have 16.0 branches, not 17.0 or 18.0).
   - Recommendation: Mark each OCA alternative with "verified_versions" in the JSON registry. Start with known-good entries and mark uncertain ones as LOW confidence.

## Sources

### Primary (HIGH confidence)
- Odoo 18.0 official documentation -- View architectures (confirmed `<list>` tag)
- Odoo 18.0 ORM Changelog -- `group_operator` renamed to `aggregator`, `_name_search` -> `_search_display_name`
- Odoo GitHub issue #192829 -- tree-to-list upgrade script details and fix
- Odoo forum: "How did I migrate custom module from odoo 17 to odoo 18" -- `view_mode` change confirmation
- Odoo forum: "odoo18 ValueError: Wrong value for ir.ui.view.type: 'tree'" -- hard error confirmation

### Secondary (MEDIUM confidence)
- Cybrosys blog: "Odoo 18 vs Odoo 17" -- Comprehensive technical diff (multiple breaking changes)
- SurekhaTech blog: "Odoo 18 Technical Improvements" -- API changes (`_search_display_name`, `check_access`)
- ibeltechnology/odoo18-migration-cli GitHub -- Migration transformation list (tree->list, attrs, states, chatter, settings views)
- Syncoria: "Odoo Enterprise and Community True Facts" -- Enterprise module categories
- Odoo 18 release notes -- Product model restructuring, removed payment providers

### Tertiary (LOW confidence)
- Medium (Delvito): "Code Changes in Odoo 18" -- `@api.readonly` decorator (unverified in official docs)
- Various forum posts about Enterprise module names -- Technical names inferred from app store and documentation, not from direct Enterprise repo access

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies needed, extends existing Jinja2 + JSON approach
- Architecture (template separation): HIGH -- well-established pattern, explicit and debuggable
- Enterprise module list: MEDIUM -- compiled from multiple sources but no direct Enterprise repo access
- OCA alternatives: MEDIUM -- OCA repos confirmed on GitHub but version-specific availability not verified
- Odoo 18.0 breaking changes: HIGH -- confirmed via official docs, GitHub issues, and multiple community sources
- Pitfalls: HIGH -- each pitfall verified with at least 2 sources (forum error reports + documentation)

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable -- Odoo version differences are well-established)
