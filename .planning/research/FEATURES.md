# Feature Research

**Domain:** AI-powered Odoo module development automation (CLI-based multi-agent orchestration)
**Researched:** 2026-03-01
**Confidence:** MEDIUM (emerging domain; some features verified via Odoo Experience 2025 talks and existing tools, others extrapolated from broader agentic-coding ecosystem patterns)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any credible Odoo module automation tool must have. Without these, developers will dismiss the tool as a toy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Natural language input** | Developers describe what they need conversationally; every modern AI coding tool accepts NL input. Without it, the tool is just a fancier scaffold command. | MEDIUM | Must handle ambiguity, domain-specific Odoo terminology ("computed fields", "wizard", "one2many"), and incomplete descriptions. Gemini-Odoo-Module-Generator already does this. |
| **Structured follow-up questions** | Users never give complete specs on the first pass. The tool must ask what's missing: model names, field types, which existing models to inherit, required views, user groups. | MEDIUM | Interview-style gathering like Gemini tool's approach. Map questions to Odoo-specific concepts (inheritance type, CE vs EE features, report requirements). Must not be tedious -- 5-10 targeted questions, not 50. |
| **Complete module file generation** | The built-in `odoo scaffold` command only produces skeleton files with placeholder content. Users expect the tool to generate *real*, populated files: models with actual fields and methods, views with working XML, security ACLs, `__manifest__.py` with correct dependencies. | HIGH | The core value proposition. Must produce: `__init__.py`, `__manifest__.py`, models/*.py, views/*.xml, security/ir.model.access.csv, security/*_groups.xml, data/*.xml, i18n/*.pot, tests/test_*.py. Each file must be syntactically valid and internally consistent. |
| **Security layer generation (ACLs + record rules)** | Missing ACLs are "the most common mistake" in Odoo development per OCA. A module without proper security is unusable in production. Every generated module must have group hierarchy, access control lists, and record rules. | MEDIUM | Generate `ir.model.access.csv` with correct model references, group XML IDs, and CRUD permissions. Generate record rules for multi-company scenarios. This is where most hand-coded modules fail -- the automation should get it right by default. |
| **OCA quality compliance** | The project explicitly targets OCA-grade quality. Modules that fail `pylint-odoo` or violate coding standards are not production-ready. | MEDIUM | Run `pylint-odoo` as a post-generation validation step. Enforce naming conventions, i18n extraction, proper XML IDs, import ordering. This is a mechanical check -- high value, moderate implementation effort. |
| **Odoo 17.0 compatibility** | Target version per project requirements. Generated code must use correct API version (no mixing 14.0 `api.multi` patterns with 17.0 code). | MEDIUM | Version-specific templates and validation. The Odoo Experience 2025 talk specifically called out "version blindness" (mixing APIs across versions) as the #1 AI code generation flaw for Odoo. |
| **Clean module installation** | A module that doesn't install on a real Odoo instance is worthless. Docker-based validation is the only way to verify this. | HIGH | Requires Docker infrastructure: spin up Odoo 17.0 + PostgreSQL, install module, run tests, report results. This is the final quality gate. |
| **Test generation** | Modules without tests don't pass OCA review and can't be trusted in production. At minimum: model CRUD tests, access rights tests, computed field tests. | MEDIUM | Generate `tests/__init__.py` and `tests/test_*.py` with `TransactionCase` or `HttpCase` subclasses. Tests should actually exercise the generated business logic, not just exist as empty stubs. |
| **Human review checkpoints** | The Odoo Experience 2025 talks stress: keep business logic human-owned, let AI handle boilerplate. Fully autonomous generation is risky for ERP systems where "silent failures" (code that runs but does the wrong thing) are the worst outcome. | MEDIUM | Pause and present generated artifacts at key stages: after models, after views, after security, after business logic. Developer approves or requests changes before the next stage proceeds. |
| **CLI interface** | The project targets developers. A CLI tool (`odoo-gen`) is the expected interface for dev tooling. Web UIs add scope without adding value for this audience. | LOW | Standard CLI with commands like `odoo-gen new`, `odoo-gen search`, `odoo-gen validate`. Use rich terminal output (tables, colored diffs) for review stages. |

### Differentiators (Competitive Advantage)

Features that distinguish this system from existing tools like `odoo scaffold`, Gemini-Odoo-Module-Generator, and general-purpose AI coding assistants.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Semantic search of GitHub/OCA repositories** | The "search-first" strategy is the project's core differentiator. Instead of always generating from scratch, find existing OCA modules that partially solve the problem and extend them. No existing Odoo AI tool does this. odoo-code-search.com exists for manual browsing but nobody has built automated semantic search that maps NL intent to existing module discovery. | HIGH | Requires: embedding Odoo module descriptions/README/manifest data, vector similarity search, scoring/ranking algorithm. Must map "leave management with approval workflow" to finding `hr_holidays` extensions. GitHub API + OCA repo crawling + embedding pipeline. |
| **Fork-and-extend workflow** | When a 70% match is found, fork it and extend rather than rebuild. This is dramatically faster and more reliable than generating from scratch. Leverages thousands of battle-tested OCA modules as foundations. | HIGH | Must: clone the matching repo, analyze its structure, identify extension points (inheritance, field additions, view modifications), generate only the delta code. This is harder than from-scratch generation because the AI must understand existing code. |
| **Multi-agent specialization** | Different agents handle different aspects of module generation (models, views, security, business logic, tests). Each agent can be optimized with domain-specific prompts and examples. The generator-critic pattern (one agent generates, another validates) catches errors that a single-pass approach misses. | HIGH | Orchestrator coordinates specialized agents. Each agent has Odoo-domain-specific skills. Agents can review each other's output (views agent checks that views reference models that the models agent actually created). This is the architectural differentiator. |
| **Incremental stage-based generation with diff review** | Instead of dumping a complete module, generate in stages and show diffs at each stage. Developer sees exactly what was generated, can accept/reject/modify individual pieces. | MEDIUM | Stage 1: models + fields. Stage 2: views. Stage 3: security. Stage 4: business logic. Stage 5: tests. At each stage, show the generated code as a diff/patch. Developer can edit before the next stage (which builds on the approved previous stage). |
| **Module adaptation intelligence** | When extending a forked module, intelligently modify rather than blindly append. Understand Odoo inheritance patterns (`_inherit`, `_inherits`), know when to use Python inheritance vs XML `<xpath>` expressions, handle computed field dependencies. | HIGH | Deep Odoo ORM knowledge encoded in agent prompts. Must handle: model inheritance, view inheritance with xpath, security group extension, data migration considerations. |
| **Manifest dependency resolution** | Automatically determine correct `__manifest__.py` dependencies based on which models are inherited, which views are extended, which groups are referenced. Incorrect dependencies cause install failures. | MEDIUM | Analyze generated code for references to external models (e.g., `res.partner`, `account.move`), resolve them to the correct Odoo module names, populate the `depends` list. Cross-reference with OCA module naming conventions. |
| **Validation pipeline with actionable feedback** | Don't just say "module failed to install" -- tell the developer exactly what broke and suggest fixes. Run pylint-odoo, attempt installation, run tests, report each failure with context. | MEDIUM | Chain: syntax check -> pylint-odoo -> Docker install -> test execution -> report. Each stage produces structured feedback. If installation fails, parse the Odoo log to identify the specific error (missing dependency, bad XML, field reference error). |
| **Community/Enterprise edition awareness** | Generate modules compatible with CE, EE, or both. Know which Odoo modules are EE-only (e.g., `account_asset`, `helpdesk`) and handle accordingly. | LOW | Metadata in the search/generation pipeline. Flag when user requests features that depend on EE modules. Offer CE-compatible alternatives where possible. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem valuable but create more problems than they solve.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Web UI / browser interface** | "Easier to use than CLI", "can show visual previews" | Massive scope increase (frontend framework, hosting, auth). The users are developers who live in terminals. A web UI adds months of work for marginal UX improvement. Per project requirements: CLI-only for v1. | Rich CLI with colored output, interactive prompts, and terminal-based diff viewing. Consider `gum` or `rich` for beautiful terminal UX. |
| **Real-time collaborative editing** | "Multiple devs working on the same module" | Single-user CLI workflow. Collaborative editing requires conflict resolution, real-time sync, and shared state -- all massive complexity for a 1-2 modules/week cadence. | Git-based workflow. Generate, commit, review via normal PR process. |
| **Autonomous deployment to production** | "Generate and deploy in one step" | ERP modules affect live business data. Auto-deploying AI-generated code to production is reckless. Per project requirements: system generates, human deploys. | Generate module + Docker validation report. Developer handles staging/production deployment through existing CI/CD. |
| **Odoo 18.0/19.0 support in v1** | "Future-proof from the start" | Multi-version support multiplies template complexity and testing burden. Odoo Experience 2025 warned about "version blindness" as the #1 AI code generation flaw. Focus on one version and do it well. | Target 17.0 exclusively. Add 18.0 support only after the 17.0 pipeline is solid and proven. |
| **Visual form/view designer** | "Drag and drop to design views" | Building a visual Odoo view editor is a massive standalone project. View XML generation from specifications is sufficient for the target audience (developers). | Generate well-structured view XML with clear comments. Show previews via screenshots from the Docker validation environment if needed. |
| **Module marketplace / sharing** | "Publish generated modules for others" | Distribution, versioning, licensing, quality control -- all tangential to the core value of generating modules. OCA already serves this role. | Output OCA-compliant modules that developers can submit to OCA through the standard contribution process if desired. |
| **Full business logic generation without human review** | "Just describe what I want and get a complete module" | The Odoo Experience 2025 talk is explicit: "silent failure" (code that runs but does the wrong thing) is the worst outcome in ERP. Business logic must be human-reviewed. AI is great at boilerplate, terrible at encoding nuanced business rules. | Generate boilerplate and structural code autonomously. Flag business logic sections for human review. Present computed field logic, workflow transitions, and domain filters for explicit approval. |
| **General-purpose code assistant** | "Also help me debug existing modules, answer Odoo questions, write documentation" | Scope creep. A module generator and a general coding assistant are different products. Trying to be both dilutes the core value. | Stay focused on the generation workflow. Developers can use Claude Code, Copilot, or Cursor for general Odoo development questions. |

## Feature Dependencies

```
[NL Input + Follow-up Questions]
    |
    v
[Semantic Search (GitHub/OCA)] -----> [Fork-and-Extend Workflow]
    |                                       |
    |                                       v
    |                              [Module Adaptation Intelligence]
    |                                       |
    v                                       v
[Complete Module File Generation] <---------+
    |
    +---> [Models + Fields Generation]
    |         |
    |         v
    |     [Views Generation] (requires models to reference)
    |         |
    |         v
    |     [Security Layer Generation] (requires models and groups)
    |         |
    |         v
    |     [Business Logic Generation] (requires models, views, security)
    |         |
    |         v
    |     [Test Generation] (requires all above to test against)
    |
    v
[Manifest Dependency Resolution] (requires all generated files to analyze)
    |
    v
[OCA Quality Compliance] (pylint-odoo on generated code)
    |
    v
[Docker Validation] (install + test execution)
    |
    v
[Human Review Checkpoints] (woven throughout generation stages)
```

### Dependency Notes

- **Views require Models:** View XML references model names and field names. Models must be generated and approved before views can be created.
- **Security requires Models + Groups:** ACLs reference model names; record rules reference fields. Group hierarchy must be defined before ACLs.
- **Business Logic requires Models + Views + Security:** Computed fields, onchange methods, and workflow logic depend on the model structure, and may reference view elements or security groups.
- **Tests require Everything:** Tests exercise models, check security, validate computed fields -- they must be generated last.
- **Fork-and-Extend conflicts with From-Scratch:** These are two parallel paths that converge at the same output. The system must decide which path to take based on search results. If fork-and-extend is chosen, the generation pipeline adapts to produce delta code rather than complete modules.
- **Semantic Search enables Fork-and-Extend:** Without search, the system can only build from scratch. Search is the prerequisite for the reuse strategy.
- **Docker Validation requires all generated files:** Cannot validate a partial module (missing security = install failure).
- **Human Review is woven throughout:** Not a single checkpoint but multiple pause points after each generation stage.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what's needed to validate the core workflow end-to-end.

- [ ] **Natural language input with structured follow-up questions** -- The entry point. Without it, there's no product.
- [ ] **Complete module file generation (from scratch)** -- The core value. Must produce all standard Odoo module files with real content.
- [ ] **Security layer generation (ACLs + record rules)** -- Modules without security are unusable. This must be table stakes from day one.
- [ ] **OCA quality compliance (pylint-odoo)** -- Automated quality gate. Low effort, high value.
- [ ] **Human review checkpoints (stage-based)** -- Essential for trust. Developers must see and approve what's generated.
- [ ] **Docker-based validation (install + test)** -- The final proof that the module works. Without this, quality claims are unverifiable.
- [ ] **Test generation** -- OCA requires tests. Modules without them fail quality review.
- [ ] **CLI interface** -- The delivery mechanism.

### Add After Validation (v1.x)

Features to add once the from-scratch generation pipeline is proven reliable.

- [ ] **Semantic search of GitHub/OCA repositories** -- Add when from-scratch generation works well enough that extending existing modules provides clear incremental value over generating from scratch
- [ ] **Fork-and-extend workflow** -- Add immediately after semantic search. This is the "compress months into days" differentiator.
- [ ] **Multi-agent specialization** -- Add when single-agent generation hits quality ceilings. Split into specialized agents when the prompts for a single agent become too complex.
- [ ] **Incremental diff review** -- Add when developers request finer-grained control over generation. Enhances the checkpoint workflow.
- [ ] **Manifest dependency resolution** -- Add when modules with cross-module dependencies become common use cases.

### Future Consideration (v2+)

Features to defer until the core pipeline is battle-tested.

- [ ] **Module adaptation intelligence** -- Requires deep Odoo ORM knowledge and sophisticated code understanding. Defer until fork-and-extend basic workflow is proven.
- [ ] **Validation pipeline with actionable feedback** -- Rich error diagnosis requires significant effort to parse Odoo logs and map failures to fixes. Start with pass/fail, evolve to detailed feedback.
- [ ] **Community/Enterprise edition awareness** -- Useful but not critical for v1. Most generated modules will target CE initially.
- [ ] **Odoo 18.0 support** -- Only after 17.0 pipeline is solid.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Natural language input + follow-ups | HIGH | MEDIUM | P1 |
| Complete module file generation | HIGH | HIGH | P1 |
| Security layer generation | HIGH | MEDIUM | P1 |
| OCA quality compliance (pylint-odoo) | HIGH | LOW | P1 |
| Human review checkpoints | HIGH | MEDIUM | P1 |
| Docker-based validation | HIGH | MEDIUM | P1 |
| Test generation | HIGH | MEDIUM | P1 |
| CLI interface | MEDIUM | LOW | P1 |
| Semantic search (GitHub/OCA) | HIGH | HIGH | P2 |
| Fork-and-extend workflow | HIGH | HIGH | P2 |
| Multi-agent specialization | MEDIUM | HIGH | P2 |
| Incremental diff review | MEDIUM | MEDIUM | P2 |
| Manifest dependency resolution | MEDIUM | MEDIUM | P2 |
| Module adaptation intelligence | MEDIUM | HIGH | P3 |
| Actionable validation feedback | MEDIUM | MEDIUM | P3 |
| CE/EE edition awareness | LOW | LOW | P3 |
| Odoo 18.0 support | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch -- without these, the tool doesn't deliver its core promise
- P2: Should have, add when core is working -- these are the differentiators
- P3: Nice to have, future consideration -- valuable but not urgent

## Competitor Feature Analysis

| Feature | Odoo `scaffold` | Gemini-Odoo-Module-Generator | General AI Assistants (Cursor/Copilot) | Our Approach |
|---------|-----------------|------------------------------|----------------------------------------|--------------|
| Natural language input | No (command-line args only) | Yes (interview-style) | Yes (chat-based) | Yes, with Odoo-specific structured follow-ups |
| Module file generation | Skeleton only (empty templates) | Full scaffolding with content | File-by-file on request | Complete, all-files-at-once with internal consistency |
| Security generation | Empty CSV template | Basic ACLs | On request, often incorrect | Full ACLs + record rules + group hierarchy by default |
| OCA compliance | No | Not mentioned | No awareness of OCA standards | Built-in pylint-odoo validation |
| Existing module search | No | No | No (search within current codebase only) | Semantic search across GitHub + OCA repos |
| Fork-and-extend | No | No (new modules only) | Manual (developer-driven) | Automated fork + intelligent extension |
| Docker validation | No | No | No | Built-in install and test verification |
| Test generation | No | Not mentioned | On request, generic | Odoo-specific test cases (TransactionCase, access rights tests) |
| Human review checkpoints | N/A | Design doc review before scaffolding | Inline code review | Stage-based approval after models, views, security, logic |
| Multi-agent coordination | N/A | Single agent (Gemini CLI) | Single agent per session | Multiple specialized agents with orchestration |
| Version awareness | Template-based per version | Configurable | Depends on context provided | Strict 17.0 targeting with version-specific validation |

## Sources

- [Beyond Code Generation: Integrating AI into Odoo's Development Lifecycle -- Odoo Experience 2025](https://oduist.com/blog/odoo-experience-2025-ai-summaries-2/305-beyond-code-generation-integrating-ai-into-odoo-s-development-lifecycle-lessons-learned-306) -- MEDIUM confidence (summary, not primary source)
- [Developing Odoo Modules Using AI: A Practical Guide -- Odoo Experience 2025](https://oduist.com/blog/odoo-experience-2025-ai-summaries-2/357-developing-odoo-modules-using-ai-a-practical-guide-358) -- MEDIUM confidence
- [Gemini-Odoo-Module-Generator on GitHub](https://github.com/jeevanism/Gemini-Odoo-Module-Generator) -- HIGH confidence (primary source, verified repo)
- [OCA pylint-odoo on GitHub](https://github.com/OCA/pylint-odoo) -- HIGH confidence
- [Odoo 17.0 Building a Module Tutorial](https://www.odoo.com/documentation/17.0/developer/tutorials/backend.html) -- HIGH confidence (official docs)
- [Odoo Security Documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html) -- HIGH confidence (official docs)
- [OCA Coding Standards and Resources](https://odoo-community.org/resources/code) -- HIGH confidence
- [Odoo Code Search (1.9B lines)](https://odoo-code-search.com/) -- HIGH confidence (verified tool)
- [Anthropic 2026 Agentic Coding Trends Report](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf) -- MEDIUM confidence
- [Microsoft AI Agent Design Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) -- HIGH confidence (official docs)
- [Google ADK Multi-Agent Patterns](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) -- HIGH confidence (official blog)
- [Faros AI: Best AI Coding Agents for 2026](https://www.faros.ai/blog/best-ai-coding-agents-2026) -- LOW confidence (single source, commercial)
- [Qodo: State of AI Code Quality in 2025](https://www.qodo.ai/reports/state-of-ai-code-quality/) -- MEDIUM confidence
- [Docker-based Odoo Testing (Much Consulting)](https://muchconsulting.com/blog/odoo-2/odoo-docker-128) -- MEDIUM confidence

---
*Feature research for: AI-powered Odoo module development automation*
*Researched: 2026-03-01*
