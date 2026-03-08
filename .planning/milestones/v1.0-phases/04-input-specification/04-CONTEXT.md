# Phase 4: Input & Specification - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the input parsing and specification pipeline: accept natural language module descriptions, ask Odoo-specific follow-up questions informed by the knowledge base, produce a structured JSON module spec, and get user approval before generation.

Requirements: INPT-01, INPT-02, INPT-03, INPT-04

</domain>

<decisions>
## Implementation Decisions

### Follow-up Question Strategy
- **Tiered approach**: Start with 3-5 high-level questions (models, core fields, who uses it, any inheritance/existing module extension). If answers reveal complexity (workflows, multi-company, approval chains), ask 2-3 deeper follow-ups.
- **Maximum 8 questions total** — avoid interrogation fatigue. Better to infer and show for review than to over-ask.
- **Knowledge-base-informed questions**: Use Phase 2 KB patterns to inform what to ask. E.g., if user mentions "approval", ask about workflow states and groups. If they mention "portal", ask about controller routes.
- **Questions are Odoo-specific**: Not generic ("what fields?") but domain-aware ("Should inventory items track serial numbers or lot numbers?", "Which existing Odoo models should this extend?")

### Structured Spec Format
- **JSON spec file** — same format as Phase 1's `odoo-gen-utils render-module` input, extended with richer fields
- Spec contains: `module_name`, `module_title`, `summary`, `category`, `depends`, `models[]` (each with `name`, `_inherit`, `fields[]`, `constraints[]`, `workflow_states[]`), `views[]`, `security_groups[]`, `menu_structure`, `demo_data_hints`
- Machine-readable for Phase 5 code generation, human-reviewable when rendered as markdown
- Spec file written to `./module_name/spec.json` alongside the generated module

### Approval UX
- **Human-readable markdown summary** shown to user — NOT raw JSON. Sections: Module Overview, Models & Fields (table), Relationships, Views, Security Groups, Workflow States.
- User options: **Approve** (proceed to generation), **Request changes** (system re-asks targeted questions), **Edit directly** (user modifies the spec summary, system updates JSON)
- Approval is a **GSD checkpoint** — generation does not begin until user explicitly approves
- After approval, spec.json is committed to git as the generation contract

### Handling Ambiguity & Defaults
- **Smart defaults from knowledge base**: `name` → `Char(required=True)`, `description` → `Text`, `email` → `Char` with email widget, `amount`/`price` → `Float` or `Monetary`, `date` → `Date`, `partner` → `Many2one(res.partner)`
- **Always show inferred defaults** in the spec summary — never silently assume. User catches mistakes during review.
- **For vague descriptions**: Infer a reasonable minimal spec, show it, and ask "I inferred X, Y, Z — is this what you meant?" rather than asking 20 clarifying questions.

### Claude's Discretion
- Exact follow-up question wording and sequencing
- JSON spec schema field names and nesting structure
- Markdown summary formatting and section order
- Which defaults to infer for which keyword patterns
- How to detect complexity triggers (workflow mentions, multi-company hints, etc.)

</decisions>

<specifics>
## Specific Ideas

- Phase 1's `/odoo-gen:new "description"` already accepts inline text — Phase 4 upgrades this from "direct scaffold" to "description → questions → spec → approve → scaffold"
- The spec.json format should be backward-compatible with Phase 1's render-module input (extend, don't replace)
- Follow-up questions should reference Odoo concepts the user may not know — e.g., "Odoo has a built-in approval mechanism using workflow states (Draft → Confirmed → Done). Would you like that for your orders?"
- The approval checkpoint integrates with GSD's checkpoint system — same approve/reject/feedback pattern used in Phase 1's integration verification

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-input-specification*
*Context gathered: 2026-03-02*
