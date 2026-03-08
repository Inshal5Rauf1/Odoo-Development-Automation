# Phase 2: Knowledge Base - Research

**Researched:** 2026-03-02
**Domain:** Odoo 17.0 coding patterns, OCA standards, pylint-odoo rules, knowledge base organization
**Confidence:** HIGH

## Summary

Phase 2 builds a comprehensive Odoo 17.0 knowledge base that agents load during code generation to prevent common mistakes. The knowledge base follows the UI UX Pro Max Skill pattern: a `MASTER.md` defining global conventions, plus category-specific files (`models.md`, `views.md`, `security.md`, etc.) that agents load via `@include` references. Each file is capped at 500 lines and follows a consistent Rule + Example + Why format.

The Odoo 17.0 domain is well-documented. Key sources are the official Odoo developer documentation, OCA coding standards, and pylint-odoo rule definitions. The critical challenge is curating the RIGHT rules -- the ones LLMs most commonly violate when generating Odoo code. The top violators are: mixing version-specific syntax (attrs vs inline expressions), wrong import patterns (openerp vs odoo), deprecated decorators (@api.multi, @api.one), incorrect manifest keys, and missing security declarations.

The extensibility mechanism uses a `custom/` subdirectory where teams add their own rule files that agents load alongside shipped defaults. Format validation ensures custom files follow the expected markdown structure without semantic validation.

**Primary recommendation:** Create 10-12 category files plus MASTER.md, populate with Odoo 17.0-specific rules sourced from official docs and pylint-odoo, then update Phase 1 agent definitions to reference the knowledge base via `@include` paths.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Category-based files**: One `.md` file per category -- `models.md`, `views.md`, `security.md`, `testing.md`, `manifest.md`, `actions.md`, `data.md`, `i18n.md`, etc. (~10-15 files, each focused on one domain)
- **Hierarchical structure** following UI UX Pro Max Skill pattern: `MASTER.md` defines global Odoo conventions, category files add/override for their domain. Agents load MASTER + relevant category files.
- **Location**: `~/.claude/odoo-gen/knowledge/` -- inside the extension directory, shipped and versioned with it. Agents reference via `@~/.claude/odoo-gen/knowledge/`
- **Rule + example + why** format for each rule: one-line rule statement, a WRONG code example, a CORRECT code example, and a brief explanation of why. ~10-20 lines per rule. Enough for an LLM to apply correctly without wasting context.
- **Explicit Odoo 17-specific migration notes**: Dedicated "Changed in 17.0" section per category with what-was/what-is pairs.
- **@include in agent .md files**: Agent definitions use `@~/.claude/odoo-gen/knowledge/MASTER.md` and relevant category files in their `execution_context`.
- **500-line limit per category file**: Hard cap. If a category grows beyond 500 lines, split into subcategories.
- **custom/ subdirectory**: Users add files to `~/.claude/odoo-gen/knowledge/custom/`. Agents load MASTER + category + matching custom/ file.
- **Format check only** for custom rules: Verify files follow expected markdown structure (headers, code blocks). No semantic validation.

### Claude's Discretion
- Exact rule content and phrasing within each category file
- Number of rules per category (aim for comprehensive but within 500-line limit)
- Internal heading structure within each .md file
- Which pylint-odoo rules to explain (prioritize commonly violated ones)
- MASTER.md structure and global conventions selection

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| KNOW-01 | System loads Odoo-specific knowledge base before generation (coding patterns, ORM conventions, version-specific syntax) | MASTER.md + category files provide comprehensive Odoo 17.0 patterns. Agent @include mechanism loads them before generation. Category files cover ORM (models.md), view syntax (views.md), and all other domains. |
| KNOW-02 | Knowledge base includes OCA coding standards, pylint-odoo rules, and common pitfall avoidance patterns | Each category file includes OCA standards for its domain. pylint-odoo rules are mapped to categories (W8120 -> models.md, W8140 -> views.md). Common pitfalls have dedicated sections per category. |
| KNOW-03 | Knowledge base includes version-specific references (Odoo 17.0 API, field types, view syntax changes) | Each category file has a "Changed in 17.0" section with what-was/what-is pairs. MASTER.md has global version info. Prevents LLMs from using outdated training data. |
| KNOW-04 | Knowledge base is extensible -- team can add custom skills/patterns via GSD skills system | `custom/` subdirectory with format validation. Custom files extend defaults. Agents load MASTER + category + matching custom/ file. Validation script checks markdown structure. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Markdown (.md) | N/A | Knowledge base file format | Agents load .md files natively via @include. No processing pipeline needed. Human-readable, version-controllable, LLM-friendly. |
| Python 3.12 | 3.12.x | Custom rule validation script | Existing odoo-gen-utils package. Validates custom rule file format. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | File path handling in validation | Custom rule format checker |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Markdown files | YAML/JSON structured rules | Markdown is directly loadable by AI assistants without parsing. YAML/JSON would need a rendering step. |
| @include references | Dynamic loading script | @include is GSD-native, deterministic, zero overhead. Dynamic loading adds complexity for no benefit. |
| Format-only validation | Semantic validation (parse rules, check code blocks) | Format check catches 90% of issues (missing headers, broken markdown) without complexity of understanding rule content. |

## Architecture Patterns

### Recommended Knowledge Base Structure
```
~/.claude/odoo-gen/knowledge/
  MASTER.md                    # Global Odoo 17.0 conventions (~200 lines)
  models.md                    # ORM, fields, decorators, constraints (~400 lines)
  views.md                     # XML views, forms, lists, search (~400 lines)
  security.md                  # ACLs, groups, record rules (~300 lines)
  testing.md                   # TransactionCase, test patterns (~300 lines)
  manifest.md                  # __manifest__.py requirements (~200 lines)
  actions.md                   # Actions, menus, server actions (~250 lines)
  data.md                      # Data files, sequences, defaults (~200 lines)
  i18n.md                      # Translations, .pot files (~150 lines)
  controllers.md               # HTTP controllers, routes (~200 lines)
  wizards.md                   # TransientModel, wizard patterns (~250 lines)
  inheritance.md               # _inherit, _inherits, xpath (~300 lines)
  custom/                      # User-added custom rules
    README.md                  # Instructions for adding custom rules
```

### Pattern 1: MASTER + Category Hierarchy (from UI UX Pro Max Skill)
**What:** MASTER.md defines global conventions that apply to ALL generated code. Category files define domain-specific rules. Agents load MASTER + relevant categories.
**When to use:** Always -- this is the core loading pattern.
**Example:**
```
# Agent loads for model generation:
@~/.claude/odoo-gen/knowledge/MASTER.md
@~/.claude/odoo-gen/knowledge/models.md

# Agent loads for view generation:
@~/.claude/odoo-gen/knowledge/MASTER.md
@~/.claude/odoo-gen/knowledge/views.md

# Agent loads for full scaffold:
@~/.claude/odoo-gen/knowledge/MASTER.md
@~/.claude/odoo-gen/knowledge/models.md
@~/.claude/odoo-gen/knowledge/views.md
@~/.claude/odoo-gen/knowledge/security.md
```

### Pattern 2: Rule Format (Rule + Example + Why)
**What:** Each rule follows a consistent format: one-line rule, WRONG example, CORRECT example, brief explanation.
**When to use:** Every rule in every category file.
**Example:**
```markdown
### Use `fields.Boolean` not `fields.Integer` for flags

**WRONG:**
\`\`\`python
is_active = fields.Integer(string="Active", default=1)
\`\`\`

**CORRECT:**
\`\`\`python
is_active = fields.Boolean(string="Active", default=True)
\`\`\`

**Why:** Boolean fields render as checkboxes in views and support proper truthiness. Integer flags require manual 0/1 handling and confuse search filters.
```

### Pattern 3: Changed in 17.0 Section
**What:** Each category file has a dedicated section documenting what changed from Odoo 16 to 17.
**When to use:** End of each category file, after the rules section.
**Example:**
```markdown
## Changed in 17.0

| What Changed | Before (16.0) | Now (17.0) | Notes |
|-------------|---------------|------------|-------|
| View modifiers | `attrs="{'invisible': [('state', '!=', 'draft')]}"` | `invisible="state != 'draft'"` | attrs dict completely removed |
| Column hiding | `attrs="{'column_invisible': ...}"` | `column_invisible="parent.show_col"` | New dedicated attribute |
```

### Anti-Patterns to Avoid
- **Monolithic knowledge file:** A single 3000-line file would blow the context budget. Category files stay under 500 lines.
- **Rules without examples:** LLMs need code examples, not just prose descriptions. Every rule MUST have WRONG and CORRECT code.
- **Version-ambiguous rules:** Rules must explicitly state they are for Odoo 17.0. Never write rules that could apply to any version.
- **Duplicate rules across files:** MASTER.md handles cross-cutting concerns. Category files handle domain-specific rules. No duplication.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Odoo 17 ORM reference | Custom ORM documentation | Official Odoo 17 developer docs + distilled rules | Official docs are authoritative; we distill into actionable rules |
| pylint-odoo rule mapping | Custom linting rules | pylint-odoo rule IDs (W8xxx, C8xxx, E8xxx) with explanations | pylint-odoo is the OCA standard; we explain rules, not reinvent them |
| Knowledge loading | Custom loader/parser | GSD @include mechanism | Native to the platform, zero overhead, deterministic |
| Custom rule validation | Full markdown AST parser | Simple regex-based structure check | Format validation only -- headers, code blocks, basic structure |

**Key insight:** The knowledge base is curated content, not a software system. The "stack" is markdown files loaded via @include. The only code is a small validation script for custom rules.

## Common Pitfalls

### Pitfall 1: LLM Version Confusion
**What goes wrong:** LLMs trained on Odoo 8-18 data mix version-specific patterns. Generated code uses `@api.multi` (removed in 13+), `openerp` imports (removed in 10+), or `attrs` dict (deprecated in 17).
**Why it happens:** Training data contains all versions. Without explicit version context, LLMs default to the most common patterns in training data.
**How to avoid:** Every rule explicitly states "Odoo 17.0". "Changed in 17.0" sections highlight version-specific differences. MASTER.md declares the target version prominently.
**Warning signs:** Any mention of `openerp`, `@api.multi`, `@api.one`, `_columns`, `_defaults`, `attrs=`, `states=` attribute.

### Pitfall 2: Rules Too Abstract for LLMs
**What goes wrong:** Rules described in prose without code examples are ignored or misapplied by LLMs.
**Why it happens:** LLMs pattern-match on code examples more reliably than prose instructions.
**How to avoid:** Every rule includes WRONG and CORRECT code examples. The examples are copy-pasteable and complete (not fragments).
**Warning signs:** Rules that say "use X instead of Y" without showing X and Y in code.

### Pitfall 3: Context Budget Overflow
**What goes wrong:** Loading too many knowledge files consumes the agent's context window, leaving insufficient room for the actual generation task.
**Why it happens:** Comprehensive knowledge base grows to thousands of lines. Agent tries to load all files.
**How to avoid:** 500-line cap per file. Agents load only MASTER + relevant category files (not all). MASTER.md is kept lean (~200 lines).
**Warning signs:** Agent performance degrades on complex modules. Generated code quality drops in later files.

### Pitfall 4: Custom Rules Overriding Shipped Rules
**What goes wrong:** Custom rule files contradict shipped defaults, causing inconsistent generated code.
**Why it happens:** No mechanism to prevent custom rules from stating the opposite of shipped rules.
**How to avoid:** Document that custom rules EXTEND defaults, never override. Custom files are loaded AFTER category files -- if an LLM sees contradictory rules, the last one (custom) would win, so the README must be clear about this.
**Warning signs:** Generated code follows different conventions than expected.

## Code Examples

### Odoo 17.0 Model Definition (Correct Pattern)
```python
# Source: Odoo 17.0 Developer Documentation
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryBook(models.Model):
    _name = "library.book"
    _description = "Library Book"
    _order = "name, date_published desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Title", required=True, tracking=True)
    isbn = fields.Char(string="ISBN")
    active = fields.Boolean(default=True)
    date_published = fields.Date(string="Publication Date")
    publisher_id = fields.Many2one(
        comodel_name="res.partner",
        string="Publisher",
    )
    author_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Authors",
    )
    page_count = fields.Integer(string="Pages")
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("available", "Available"),
            ("borrowed", "Borrowed"),
            ("lost", "Lost"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )
    borrower_id = fields.Many2one(
        comodel_name="res.partner",
        string="Borrower",
    )

    @api.constrains("isbn")
    def _check_isbn(self):
        for record in self:
            if record.isbn and len(record.isbn) not in (10, 13):
                raise ValidationError("ISBN must be 10 or 13 characters.")

    @api.depends("page_count")
    def _compute_is_long_book(self):
        for record in self:
            record.is_long_book = record.page_count > 500

    is_long_book = fields.Boolean(
        string="Long Book",
        compute="_compute_is_long_book",
        store=True,
    )
```

### Odoo 17.0 Form View (Correct Pattern)
```xml
<!-- Source: Odoo 17.0 Developer Documentation -->
<odoo>
    <record id="library_book_view_form" model="ir.ui.view">
        <field name="name">library.book.form</field>
        <field name="model">library.book</field>
        <field name="arch" type="xml">
            <form string="Library Book">
                <header>
                    <button name="action_make_available"
                            string="Make Available"
                            type="object"
                            class="btn-primary"
                            invisible="state != 'draft'"/>
                    <field name="state" widget="statusbar"
                           statusbar_visible="draft,available,borrowed"/>
                </header>
                <sheet>
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="isbn"/>
                            <field name="publisher_id"/>
                        </group>
                        <group>
                            <field name="date_published"/>
                            <field name="page_count"/>
                            <field name="state"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="Authors">
                            <field name="author_ids"/>
                        </page>
                    </notebook>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>
</odoo>
```

### Odoo 17.0 Security (ACL + Groups Pattern)
```xml
<!-- security/security.xml -->
<odoo>
    <record id="module_category_library" model="ir.module.category">
        <field name="name">Library</field>
        <field name="sequence">100</field>
    </record>

    <record id="group_library_user" model="res.groups">
        <field name="name">User</field>
        <field name="category_id" ref="module_category_library"/>
        <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
    </record>

    <record id="group_library_manager" model="res.groups">
        <field name="name">Manager</field>
        <field name="category_id" ref="module_category_library"/>
        <field name="implied_ids" eval="[(4, ref('group_library_user'))]"/>
    </record>
</odoo>
```

```csv
# security/ir.model.access.csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_library_book_user,library.book.user,model_library_book,group_library_user,1,1,1,0
access_library_book_manager,library.book.manager,model_library_book,group_library_manager,1,1,1,1
```

### Odoo 17.0 Test Pattern
```python
# tests/test_library_book.py
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestLibraryBook(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Book = cls.env["library.book"]
        cls.partner = cls.env["res.partner"].create({"name": "Test Publisher"})

    def test_create_book(self):
        book = self.Book.create({
            "name": "Test Book",
            "isbn": "1234567890",
            "publisher_id": self.partner.id,
        })
        self.assertEqual(book.name, "Test Book")
        self.assertEqual(book.state, "draft")

    def test_isbn_constraint(self):
        with self.assertRaises(ValidationError):
            self.Book.create({
                "name": "Bad ISBN",
                "isbn": "123",  # Neither 10 nor 13 chars
            })

    def test_computed_field(self):
        book = self.Book.create({
            "name": "Long Book",
            "page_count": 600,
        })
        self.assertTrue(book.is_long_book)
```

## Odoo 17.0 Key Rules Reference

### Models Domain
- `_name` uses dot notation: `library.book` (not `LibraryBook` or `library_book`)
- `_description` is REQUIRED (pylint-odoo W8150)
- Only use `from odoo import api, fields, models` (never `from openerp`)
- No `@api.multi`, `@api.one`, `@api.returns` (removed since Odoo 13)
- No `_columns`, `_defaults` (old API, removed since Odoo 10)
- Computed fields: define the field first, then the compute method (or use `compute="_compute_xxx"` string reference)
- `@api.depends` is required for stored computed fields
- `@api.constrains` for validation, not `_constraints` list
- One model per Python file (OCA convention)
- `_order` for default sort order (not relying on database order)

### Views Domain
- Use `<tree>` tag for list views in Odoo 17.0 (NOT `<list>` -- that is Odoo 18+ only)
- Use inline `invisible="expression"` and `readonly="expression"` (NOT `attrs={"invisible": [...]}`)
- Use `column_invisible="expression"` for tree column visibility (new in 17.0)
- No `states` attribute on buttons -- use `invisible="state != 'draft'"` instead
- XML root tag is `<odoo>` (never `<openerp>`)
- External IDs follow pattern: `{model_underscore}_view_{type}` (e.g., `library_book_view_form`)
- Use `<chatter/>` shorthand (Odoo 17) instead of explicit message/activity fields

### Security Domain
- Module category record for group hierarchy
- Two groups minimum: User (read/write/create) and Manager (+unlink)
- Manager group uses `implied_ids` to inherit from User group
- User group uses `implied_ids` to inherit from `base.group_user`
- ACL CSV columns: `id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink`
- Model reference in ACL: `model_{name_with_underscores}` (dots become underscores)
- Every model MUST have at least one ACL entry
- Record rules for multi-company: `['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]`

### Manifest Domain
- `license` is REQUIRED (pylint-odoo E8501) -- typically `"LGPL-3"` for OCA
- Version format: `17.0.1.0.0` (5 parts: odoo_version.major.minor.patch)
- No `description` key -- use `README.rst` instead (pylint-odoo C8101)
- `category` should match one of Odoo's standard categories
- `data` list must reference files in correct load order: security groups before ACLs, ACLs before views
- `demo` list for demo data (separate from `data`)
- `installable: True` is required for the module to appear in Apps
- `application: True` only for top-level application modules (creates menu entry)
- `depends` list must include all modules whose models/views/data you reference

### pylint-odoo Key Rules (Commonly Violated)

| Rule | Category | Description |
|------|----------|-------------|
| W8120 | models | `_description` missing on model |
| W8150 | models | Use of old API (`_columns`, `_defaults`) |
| C8101 | manifest | `description` key used in manifest (use README) |
| E8501 | manifest | Missing `license` in manifest |
| W8140 | views | Deprecated `attrs` attribute in XML view |
| W8105 | models | Missing `_inherit` or `_name` in model class |
| C8104 | manifest | Empty `depends` list |
| W8180 | security | Missing access rights for model |
| R8110 | models | Redundant `@api.returns` decorator |
| W8160 | i18n | Missing translation markup (`_()`) on user-facing strings |
| C8108 | manifest | Invalid version format |

## State of the Art

| Old Approach | Current Approach (17.0) | When Changed | Impact |
|--------------|--------------------------|--------------|--------|
| `attrs={"invisible": [...]}` | `invisible="expression"` | Odoo 17.0 | All view modifiers are now inline Python expressions |
| `states` attribute on buttons | `invisible="state != 'x'"` | Odoo 17.0 | `states` attribute removed |
| `<tree>` tag | `<tree>` still valid in 17, `<list>` in 18+ | Odoo 18.0 | Use `<tree>` for 17.0 compatibility |
| `attrs={"column_invisible": ...}` | `column_invisible="expression"` | Odoo 17.0 | Dedicated attribute for tree column hiding |
| Explicit chatter fields | `<chatter/>` shorthand | Odoo 16.0+ | Simpler XML, still works in 17.0 |
| `@api.multi` / `@api.one` | Removed (methods work on recordsets by default) | Odoo 13.0 | LLMs still frequently generate these |
| `from openerp import ...` | `from odoo import ...` | Odoo 10.0 | LLMs trained on old code still use `openerp` |
| `_columns = {...}` | `name = fields.Char(...)` | Odoo 10.0 | New ORM API since Odoo 8, old API removed in 10 |

## Open Questions

1. **Exact pylint-odoo rule count for Odoo 17.0**
   - What we know: pylint-odoo has ~50+ rules. We need to prioritize the top 15-20 most commonly violated.
   - What's unclear: Which rules fire most often on LLM-generated code specifically (vs human-written code).
   - Recommendation: Start with the rules listed above (mapped from Odoo 17 breaking changes + OCA requirements). Expand based on Phase 3 validation feedback.

2. **Optimal number of rules per category**
   - What we know: 500-line cap per file, ~10-20 lines per rule, so ~25-50 rules max per file.
   - What's unclear: Whether LLMs benefit more from fewer high-impact rules or comprehensive coverage.
   - Recommendation: Start with 15-25 rules per category (the most impactful ones). Add more in later phases based on validation failure patterns.

## Sources

### Primary (HIGH confidence)
- Odoo 17.0 Developer Documentation (https://www.odoo.com/documentation/17.0/developer/) -- ORM API, view syntax, security model, testing
- OCA Coding Standards (https://odoo-community.org/resources/code) -- Python style, XML conventions, manifest requirements
- pylint-odoo GitHub (https://github.com/OCA/pylint-odoo) -- Rule definitions, codes, descriptions
- Odoo 17.0 Release Notes (https://www.odoo.com/odoo-17-release-notes) -- attrs deprecation, inline expressions, view changes

### Secondary (MEDIUM confidence)
- UI UX Pro Max Skill (GitHub) -- Skill architecture pattern: MASTER + category hierarchy, rule library structure
- erp_claude (GitHub) -- Odoo 17 model/view skills used as reference for rule content
- Phase 1 odoo-scaffold agent -- Existing inline Odoo 17.0 rules to extract and expand

### Tertiary (LOW confidence)
- Community forum posts about Odoo 17 migration gotchas -- Anecdotal but useful for pitfall identification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Markdown + @include is a proven pattern in this project (Phase 1 already uses it)
- Architecture: HIGH -- UI UX Pro Max Skill pattern is documented and adopted as project decision
- Pitfalls: HIGH -- Odoo version confusion is extensively documented in prior research
- Rule content: MEDIUM -- Rules are sourced from official docs but the optimal selection for LLM code generation is empirical

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable domain, Odoo 17.0 API is frozen)
