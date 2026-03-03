# Phase 2: Knowledge Base - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a comprehensive Odoo 17.0 knowledge base that agents load during code generation to prevent common mistakes. Delivers: categorized rule files with MASTER + category hierarchy, OCA standards, pylint-odoo rules, version-specific references, and an extensibility mechanism for custom rules.

Requirements: KNOW-01, KNOW-02, KNOW-03, KNOW-04

</domain>

<decisions>
## Implementation Decisions

### Knowledge Organization
- **Category-based files**: One `.md` file per category — `models.md`, `views.md`, `security.md`, `testing.md`, `manifest.md`, `actions.md`, `data.md`, `i18n.md`, etc. (~10-15 files, each focused on one domain)
- **Hierarchical structure** following UI UX Pro Max Skill pattern: `MASTER.md` defines global Odoo conventions, category files add/override for their domain. Agents load MASTER + relevant category files.
- **Location**: `~/.claude/odoo-gen/knowledge/` — inside the extension directory, shipped and versioned with it. Agents reference via `@~/.claude/odoo-gen/knowledge/`

### Content Scope & Depth
- **Rule + example + why** format for each rule: one-line rule statement, a WRONG code example, a CORRECT code example, and a brief explanation of why. ~10-20 lines per rule. Enough for an LLM to apply correctly without wasting context.
- **Explicit Odoo 17-specific migration notes**: Dedicated "Changed in 17.0" section per category with what-was/what-is pairs. This prevents LLMs from using outdated training data (e.g., `attrs` → inline expressions, `<tree>` still valid in 17 but `<list>` in 18).

### Agent Loading Mechanism
- **@include in agent .md files**: Agent definitions use `@~/.claude/odoo-gen/knowledge/MASTER.md` and relevant category files (e.g., `@~/.claude/odoo-gen/knowledge/models.md`) in their `execution_context`. The AI assistant loads them as context automatically. Simple, deterministic, GSD-native.
- **500-line limit per category file**: Hard cap. If a category grows beyond 500 lines, split into subcategories (e.g., `views.md` → `views-form.md`, `views-list.md`). Keeps context window affordable.

### Extensibility & Custom Rules
- **custom/ subdirectory**: Users add files to `~/.claude/odoo-gen/knowledge/custom/`. Agents load MASTER + category + matching custom/ file. Custom rules extend defaults, never override shipped rules.
- **Format check only** for custom rules: Verify files follow expected markdown structure (headers, code blocks). No semantic validation. Quick, catches formatting errors.

### Claude's Discretion
- Exact rule content and phrasing within each category file
- Number of rules per category (aim for comprehensive but within 500-line limit)
- Internal heading structure within each .md file
- Which pylint-odoo rules to explain (prioritize commonly violated ones)
- MASTER.md structure and global conventions selection

</decisions>

<specifics>
## Specific Ideas

- MASTER.md should cover: naming conventions (_name format, field naming, method naming), manifest requirements (license, version format), Python style (OCA deviations from PEP 8), and universal Odoo 17 patterns
- Each category file should have a consistent structure: Overview → Rules → Changed in 17.0 → Common Mistakes
- pylint-odoo rules should map to specific knowledge categories (e.g., W8120 → models.md, W8140 → views.md)
- The knowledge base is the single source of truth agents reference — if a rule isn't here, agents may hallucinate
- Phase 1's odoo-scaffold agent already has inline Odoo 17 rules — Phase 2 should extract and expand those into the KB, then update agent references

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-knowledge-base*
*Context gathered: 2026-03-02*
