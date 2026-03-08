# Phase 4: Input & Specification - Research

**Researched:** 2026-03-02
**Domain:** Natural language input parsing, structured specification generation, conversational follow-up, approval flow
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Tiered follow-up questions**: Start with 3-5 high-level questions, expand to 2-3 deeper follow-ups if complexity detected. Maximum 8 questions total.
- **Knowledge-base-informed questions**: Use Phase 2 KB patterns to inform what to ask (e.g., if user mentions "approval", ask about workflow states and groups).
- **Questions are Odoo-specific**: Domain-aware, not generic. Reference Odoo concepts the user may not know.
- **JSON spec file**: Same format as Phase 1's `render-module` input, extended with richer fields (workflow_states, constraints, demo_data_hints, etc.).
- **Spec contains**: `module_name`, `module_title`, `summary`, `category`, `depends`, `models[]` (each with `name`, `_inherit`, `fields[]`, `constraints[]`, `workflow_states[]`), `views[]`, `security_groups[]`, `menu_structure`, `demo_data_hints`.
- **Human-readable markdown summary** shown to user (NOT raw JSON). Sections: Module Overview, Models & Fields (table), Relationships, Views, Security Groups, Workflow States.
- **User options at approval**: Approve (proceed), Request changes (re-ask targeted questions), Edit directly (user modifies spec summary, system updates JSON).
- **Approval is a GSD checkpoint** -- generation does not begin until user explicitly approves.
- **After approval, spec.json is committed to git** as the generation contract.
- **Smart defaults from knowledge base**: `name` -> `Char(required=True)`, `description` -> `Text`, `email` -> `Char` with email widget, `amount`/`price` -> `Float` or `Monetary`, `date` -> `Date`, `partner` -> `Many2one(res.partner)`.
- **Always show inferred defaults** in the spec summary -- never silently assume.
- **For vague descriptions**: Infer reasonable minimal spec, show it, and ask "I inferred X, Y, Z -- is this what you meant?" rather than asking 20 clarifying questions.
- **Spec file written to** `./module_name/spec.json` alongside the generated module.
- **Backward-compatible** with Phase 1's `render-module` input format (extend, don't replace).

### Claude's Discretion
- Exact follow-up question wording and sequencing
- JSON spec schema field names and nesting structure
- Markdown summary formatting and section order
- Which defaults to infer for which keyword patterns
- How to detect complexity triggers (workflow mentions, multi-company hints, etc.)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

## Summary

Phase 4 upgrades the existing `/odoo-gen:new` command from "description -> direct scaffold" to "description -> questions -> spec -> approve -> scaffold". The existing Phase 1 infrastructure provides the foundation: the `new.md` command, the `odoo-scaffold` agent, the `scaffold.md` workflow, and the `render-module` function that accepts a JSON spec. Phase 4 adds three new capabilities on top:

1. **Structured follow-up questions** informed by the Phase 2 knowledge base, using a tiered approach (3-5 high-level questions, then 2-3 deeper questions if complexity is detected).
2. **Extended JSON spec format** that is backward-compatible with the existing `render-module` input but adds richer fields for workflow states, constraints, inheritance, security groups, menu structure, and demo data hints.
3. **Approval flow** where the spec is rendered as a human-readable markdown summary, presented for review, and committed to git as `spec.json` upon approval.

**Primary recommendation:** Implement as a new workflow (`spec.md`) and update the `odoo-scaffold` agent and `/odoo-gen:plan` command to use it. The existing `/odoo-gen:new` command continues to work for quick scaffolding; `/odoo-gen:plan` becomes the full specification pipeline.

## Standard Stack

### Core
| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| GSD commands | `commands/*.md` | Command registration and routing | GSD extension pattern established in Phase 1 |
| GSD workflows | `workflows/*.md` | Multi-step execution flows | Scaffold workflow established in Phase 1 |
| GSD agents | `agents/*.md` | Agent definitions with knowledge base refs | Phase 1 pattern with KB wiring added in Phase 2 |
| Knowledge base | `knowledge/*.md` | Odoo 17.0 patterns and rules | Phase 2 shipped 12 knowledge files |
| odoo-gen-utils | `python/src/odoo_gen_utils/` | JSON spec rendering, validation | Phase 1 Python package with Click CLI |

### Supporting
| Component | Location | Purpose | When to Use |
|-----------|----------|---------|-------------|
| defaults.json | `defaults.json` | Default config (version, license, author) | Read during spec generation for smart defaults |
| Jinja2 templates | `python/src/odoo_gen_utils/templates/*.j2` | Module rendering | Phase 5+ (generation from spec), not this phase |

## Architecture Patterns

### Existing Architecture (Phase 1)

```
User -> /odoo-gen:new "description"
  -> commands/new.md (routes to odoo-scaffold agent)
  -> agents/odoo-scaffold.md (parses description, infers spec, presents for confirmation)
  -> workflows/scaffold.md (4-phase: parse -> confirm -> render-module -> summary)
  -> odoo-gen-utils render-module --spec-file spec.json --output-dir ./
```

The current scaffold.md workflow already has a Phase 1 (Input Parsing) and Phase 2 (Spec Confirmation) that do basic NL parsing and user confirmation. Phase 4 replaces these with a much richer pipeline.

### Phase 4 Target Architecture

```
User -> /odoo-gen:plan "description"
  -> commands/plan.md (routes to odoo-scaffold agent, uses spec workflow)
  -> agents/odoo-scaffold.md (updated: follows spec workflow instead of scaffold)
  -> workflows/spec.md (NEW: 4-phase: parse -> follow-up -> spec -> approve)
    Phase 1: Parse NL description into draft spec (same as current but richer)
    Phase 2: Ask tiered follow-up questions (KB-informed)
    Phase 3: Generate structured spec.json + markdown summary
    Phase 4: Present for approval (GSD checkpoint pattern)
  -> spec.json committed to git as generation contract
```

### Pattern: Spec JSON Schema (Extended)

The existing `render-module` input format from Phase 1:

```json
{
  "module_name": "string",
  "module_title": "string",
  "summary": "string",
  "author": "string",
  "website": "string",
  "license": "string",
  "category": "string",
  "odoo_version": "string",
  "application": true,
  "depends": ["base"],
  "models": [
    {
      "name": "module.model",
      "description": "Model Description",
      "fields": [
        {
          "name": "field_name",
          "type": "Char",
          "string": "Label",
          "required": true,
          "help": "Help text"
        }
      ]
    }
  ]
}
```

Phase 4 extends this (backward-compatible -- new fields are optional):

```json
{
  "module_name": "string",
  "module_title": "string",
  "summary": "string",
  "author": "string",
  "website": "string",
  "license": "string",
  "category": "string",
  "odoo_version": "string",
  "application": true,
  "depends": ["base"],
  "models": [
    {
      "name": "module.model",
      "description": "Model Description",
      "_inherit": null,
      "fields": [
        {
          "name": "field_name",
          "type": "Char",
          "string": "Label",
          "required": true,
          "default": null,
          "help": "Help text",
          "comodel_name": null,
          "inverse_name": null,
          "selection": null,
          "compute": null,
          "widget": null,
          "tracking": false,
          "copy": true,
          "index": false,
          "groups": null
        }
      ],
      "constraints": [
        {
          "type": "sql",
          "name": "unique_name",
          "definition": "UNIQUE(name)",
          "message": "Name must be unique"
        }
      ],
      "workflow_states": [
        {
          "key": "draft",
          "label": "Draft",
          "is_default": true
        }
      ],
      "inherit_mixins": ["mail.thread", "mail.activity.mixin"]
    }
  ],
  "views": [
    {
      "model": "module.model",
      "types": ["form", "tree", "search"],
      "custom_fields_in_tree": ["name", "state"],
      "custom_search_filters": ["state"]
    }
  ],
  "security_groups": [
    {
      "name": "group_module_user",
      "label": "User",
      "permissions": {"read": true, "write": true, "create": true, "unlink": false}
    },
    {
      "name": "group_module_manager",
      "label": "Manager",
      "implied_ids": ["group_module_user"],
      "permissions": {"read": true, "write": true, "create": true, "unlink": true}
    }
  ],
  "menu_structure": {
    "root_menu": "Module Root",
    "sub_menus": ["Model One", "Model Two"]
  },
  "demo_data_hints": [
    "3 sample records per model",
    "Include one record in each workflow state"
  ]
}
```

### Pattern: Tiered Follow-Up Questions

**Tier 1 (Always asked, 3-5 questions):**
1. What are the main data entities/models? (What things does this module manage?)
2. Who will use this module? (Which Odoo user groups need access?)
3. Does this extend or integrate with any existing Odoo modules? (stock, sale, purchase, hr, etc.)
4. Should records have a workflow/approval process? (Draft -> Confirmed -> Done?)
5. Do you need portal/website access for external users?

**Tier 2 (Asked when complexity detected, 2-3 questions):**
- If workflow mentioned: "What are the states and transitions? Who can approve?"
- If multi-company context: "Should records be company-specific? Shared or isolated?"
- If inheritance mentioned: "Which existing models should be extended? What fields added?"
- If portal mentioned: "What data should portal users see? Read-only or editable?"
- If reporting mentioned: "What metrics matter? Grouped by what dimensions?"

**Complexity triggers (keywords/patterns):**
- "approval", "workflow", "status", "stages" -> workflow questions
- "multi-company", "companies", "branches" -> multi-company questions
- "extend", "inherit", "add to", "modify existing" -> inheritance questions
- "portal", "website", "customer access", "public" -> portal questions
- "report", "dashboard", "analytics", "statistics" -> reporting questions

### Pattern: Smart Defaults (KB-Informed)

From the knowledge base and CONTEXT.md:

| Keyword Pattern | Inferred Field | Default Config |
|----------------|---------------|----------------|
| `name`, `title` | `Char(required=True)` | Primary display field |
| `description`, `notes`, `comment` | `Text` | Multiline text |
| `email` | `Char` | widget="email" |
| `phone` | `Char` | widget="phone" |
| `amount`, `price`, `cost`, `total` | `Float` or `Monetary` | digits=(16,2) |
| `date`, `deadline` | `Date` | |
| `datetime`, `timestamp` | `Datetime` | |
| `active`, `is_*`, `has_*` | `Boolean` | default=True for active |
| `image`, `photo` | `Binary` | |
| `state`, `status` | `Selection` | default="draft" |
| `partner`, `customer`, `vendor` | `Many2one("res.partner")` | |
| `user`, `responsible`, `assigned` | `Many2one("res.users")` | |
| `company` | `Many2one("res.company")` | index=True |
| `tag`, `category` (plural) | `Many2many` | |
| `line`, `detail`, `item` (plural) | `One2many` | |

### Anti-Patterns to Avoid

- **Over-asking**: More than 8 questions creates interrogation fatigue. Infer and show for review.
- **Generic questions**: "What fields do you want?" is useless. Ask Odoo-domain-specific questions.
- **Silent inference**: Never assume without showing. Always display what was inferred.
- **Spec drift**: The spec.json must be the single source of truth. The markdown summary is a view of it, not a separate document.
- **Breaking backward compatibility**: New spec fields must be optional so existing `render-module` still works.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NL parsing | Custom NLP pipeline | LLM reasoning in agent prompt | Agent IS the NLP engine; prompt engineering is sufficient |
| Spec validation | Custom schema validator | JSON structure checks in workflow | Keep it simple; the agent generates valid JSON by construction |
| Field type inference | Complex rule engine | Keyword-to-type mapping table in workflow | Deterministic mapping is simpler and more debuggable than ML |
| Markdown rendering | Template engine for spec display | Inline markdown generation in agent | Agent writes markdown naturally; no template needed for display |
| Approval flow | Custom state machine | GSD checkpoint pattern | GSD already provides approve/reject/feedback pattern |

**Key insight:** The LLM agent (odoo-scaffold) IS the intelligence layer. The workflow file provides structure and rules; the agent applies them using natural language reasoning. No custom code is needed for NL parsing, question generation, or spec inference.

## Common Pitfalls

### Pitfall 1: Spec JSON Incompatibility with render-module
**What goes wrong:** Extended spec includes new fields that break `render-module` because it doesn't expect them.
**Why it happens:** Adding required fields or changing field names in the spec schema.
**How to avoid:** All new fields are optional with sensible defaults. The `render-module` function in `renderer.py` uses `.get()` with defaults for all fields. Test backward compatibility by rendering an old-format spec.
**Warning signs:** `render-module` throws KeyError or produces broken output with new spec format.

### Pitfall 2: Question Fatigue
**What goes wrong:** User abandons the process because too many questions are asked.
**Why it happens:** Not respecting the 8-question maximum, or asking generic questions that don't add value.
**How to avoid:** Enforce tier system. Tier 1 is 3-5 questions max. Tier 2 is triggered only by complexity signals. Total maximum 8.
**Warning signs:** More than 5 questions in Tier 1, or Tier 2 triggered without clear complexity signals.

### Pitfall 3: Spec-Markdown Desync
**What goes wrong:** The markdown summary shown to user doesn't match the spec.json that gets committed.
**Why it happens:** Generating markdown and JSON separately, then one gets updated but not the other.
**How to avoid:** Generate spec.json FIRST, then render markdown FROM the JSON. Never maintain them independently. The workflow must enforce this order.
**Warning signs:** User approves a summary, but the committed JSON has different values.

### Pitfall 4: Knowledge Base Not Loaded
**What goes wrong:** Follow-up questions are generic instead of Odoo-specific because the agent didn't load KB files.
**Why it happens:** Missing `@include` references in the updated agent definition.
**How to avoid:** The updated `odoo-scaffold.md` agent MUST include `@~/.claude/odoo-gen/knowledge/MASTER.md` and relevant domain-specific KB files. Verify by checking that generated questions reference Odoo-specific concepts.
**Warning signs:** Questions like "what fields?" instead of "Should this model track serial numbers or lot numbers?"

### Pitfall 5: Approval Checkpoint Not Blocking
**What goes wrong:** Generation starts before user has reviewed the spec.
**Why it happens:** Checkpoint not properly integrated, or auto-mode bypasses it.
**How to avoid:** The approval step must be a `checkpoint:human-verify` in the workflow. The spec.json commit happens ONLY after approval.
**Warning signs:** Files generated without user seeing the spec summary first.

## Code Examples

### Existing render-module Spec Input (Phase 1)

From `workflows/scaffold.md` Phase 3:

```json
{
  "module_name": "inventory_tracking",
  "module_title": "Inventory Tracking",
  "summary": "Track inventory items with stock moves and warehouse locations",
  "author": "",
  "website": "",
  "license": "LGPL-3",
  "category": "Inventory",
  "odoo_version": "17.0",
  "application": true,
  "depends": ["base", "stock"],
  "models": [
    {
      "name": "inventory.item",
      "description": "Inventory Item",
      "fields": [
        {"name": "name", "type": "Char", "string": "Name", "required": true, "help": "Item display name"},
        {"name": "warehouse_id", "type": "Many2one", "string": "Warehouse", "comodel_name": "stock.warehouse", "required": false, "help": "Warehouse location"}
      ]
    }
  ]
}
```

### Workflow File Pattern (from scaffold.md)

```markdown
# Workflow Title

Overview paragraph.

## Phase 1: [Name]
### Steps
1. Step detail
2. Step detail

## Phase 2: [Name]
### Steps
...
```

### Agent Definition Pattern (from odoo-scaffold.md)

```markdown
---
name: agent-name
description: What the agent does
tools: Read, Write, Bash, Glob, Grep
color: green
---
<role>
You are [role description].

## Workflow
### Phase 1: [Name]
[Steps]

## Knowledge Base
@~/.claude/odoo-gen/knowledge/MASTER.md
@~/.claude/odoo-gen/knowledge/models.md
</role>
```

### GSD Checkpoint Pattern

From the `/odoo-gen:new` command approval step:

```
Wait for user confirmation before proceeding.
- If user says "yes", "ok", "looks good", "confirm", "approved" -> proceed
- If user requests changes -> update the spec and re-present
```

This informal pattern in Phase 1 becomes a formal GSD checkpoint in Phase 4.

## State of the Art

| Old Approach (Phase 1) | New Approach (Phase 4) | Impact |
|------------------------|------------------------|--------|
| Inline description -> immediate scaffold | Description -> questions -> spec -> approve -> scaffold | Much richer, more accurate module specs |
| Basic field inference from NL | KB-informed field inference with smart defaults | Fewer post-generation fixes needed |
| Informal confirmation ("yes/no") | GSD checkpoint with structured approval options | Professional review flow, change requests supported |
| Spec as temporary JSON | Spec committed to git as `spec.json` | Auditable, reproducible, diffable generation contract |
| `/odoo-gen:new` only | `/odoo-gen:plan` (full) + `/odoo-gen:new` (quick) | Users choose depth of specification |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INPT-01 | User can describe a module need in NL via GSD command | `/odoo-gen:plan` command accepts NL description via `$ARGUMENTS`. Existing `new.md` pattern proves this works. |
| INPT-02 | System asks structured follow-up questions (models, fields, views, inheritance, groups) | Tiered question strategy (3-5 Tier 1 + 2-3 Tier 2) with complexity triggers. KB files inform domain-specific questions. |
| INPT-03 | System parses input into structured module specification | Extended JSON spec format (backward-compatible with `render-module`). Smart defaults from keyword-to-type mapping table. |
| INPT-04 | User can review and approve parsed specification before generation | Markdown summary rendered from spec.json. GSD checkpoint for approval. Three options: approve, request changes, edit directly. Spec committed to git on approval. |
</phase_requirements>

## Open Questions

1. **Should `/odoo-gen:new` be updated to use the spec workflow too?**
   - What we know: CONTEXT.md says Phase 4 "upgrades" the flow from direct scaffold to spec-based. The `new` command currently does quick scaffold.
   - What's unclear: Whether `new` should remain as a quick/simple path or be fully upgraded.
   - Recommendation: Keep `new` as-is for quick scaffolding. Implement the spec pipeline in `/odoo-gen:plan`. Later phases can optionally wire `new` to use `plan` internally. This avoids breaking existing functionality.

2. **How deep should spec.json validation go?**
   - What we know: The agent generates the JSON, so it should be structurally valid by construction.
   - What's unclear: Whether we need schema validation (e.g., jsonschema) or just trust agent output.
   - Recommendation: Basic structural checks in the workflow (required fields present, model names in dot-notation, field types from known set). No external schema library needed.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `commands/new.md`, `agents/odoo-scaffold.md`, `workflows/scaffold.md` -- existing command/agent/workflow patterns
- Codebase analysis: `python/src/odoo_gen_utils/renderer.py` -- existing `render_module` input format
- Codebase analysis: `knowledge/MASTER.md` -- Odoo 17.0 naming conventions and field patterns
- Codebase analysis: `defaults.json` -- default configuration values

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions -- user's explicit design choices for Phase 4

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components exist from Phases 1-3; Phase 4 extends them
- Architecture: HIGH -- follows established command/agent/workflow pattern; no new infrastructure
- Pitfalls: HIGH -- direct analysis of existing codebase reveals compatibility constraints

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable -- no external dependencies changing)
