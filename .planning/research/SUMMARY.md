# Project Research Summary

**Project:** Odoo Module Automation (odoo-gen)
**Domain:** Multi-agent AI orchestration for automated Odoo 17.0 module code generation
**Researched:** 2026-03-01
**Confidence:** MEDIUM-HIGH

## Executive Summary

This project is a CLI tool that uses multiple AI coding agents (Claude Code, Codex CLI, Gemini CLI) to automate the creation of production-ready Odoo 17.0 modules. Experts in this space build such systems as deterministic pipelines with human checkpoints -- not as conversational multi-agent debates. The key architectural insight is that these AI CLI tools are subprocesses, not API-based agents, so heavyweight frameworks like CrewAI and LangGraph are the wrong abstraction. A thin custom orchestrator using Python asyncio subprocess management is the correct pattern, validated by multiple open-source projects (MCO, claude-octopus, parallel-code). Pydantic-AI handles the structured LLM interactions (intent parsing, spec generation) where typed output matters; the CLI subprocesses handle the actual file generation where they excel.

The recommended approach is to build in five phases, starting with foundation (CLI + scaffolding + validation) before adding intelligence (agents + search). The critical constraint shaping every decision is Odoo 17's Python version lock: 3.10-3.12 only. Python 3.13+ will silently break Odoo validation. The stack is Python 3.12, uv for package management, Typer for CLI, Pydantic for data models, sentence-transformers + ChromaDB for semantic module search, Docker SDK for Odoo validation, and Jinja2 for code templating. Every component is production-ready with verified versions.

The top risks are: (1) Odoo version confusion in generated code -- LLMs mix APIs from different Odoo versions, producing modules that install but behave incorrectly; (2) the "god agent" anti-pattern -- a single monolithic agent cannot reliably produce 10-20 interconnected files with correct cross-references; (3) Docker validation giving false confidence -- tests that pass against an empty database with admin user do not prove the module works in production; and (4) context window overflow silently degrading output quality as module complexity grows. All four are preventable with the architectural patterns identified in research: version-pinned prompts, single-responsibility agents with schema-based context passing, realistic Docker test environments, and maker-checker loops.

## Key Findings

### Recommended Stack

The stack is mature and well-verified. Python 3.12 is the hard constraint (maximum version Odoo 17 supports; minimum version for modern library compatibility). uv replaces the entire pip/poetry/pyenv toolchain with a single Rust-based tool that is 10-100x faster. The stack splits into four functional groups: CLI (Typer + Rich), orchestration (asyncio + Pydantic-AI), search (sentence-transformers + ChromaDB + PyGithub), and validation (Docker SDK + pylint-odoo).

**Core technologies:**
- **Python 3.12** -- Runtime. Maximum Odoo 17 supported version. 3.13+ breaks Odoo.
- **uv** -- Package/project manager. Replaces pip+poetry+pyenv+virtualenv. 10-100x faster.
- **Typer + Rich** -- CLI framework + terminal UI. Auto-generated help, rich progress bars, syntax highlighting.
- **Pydantic + Pydantic-AI** -- Data validation + structured LLM output. Type-safe module specs and agent responses.
- **asyncio (stdlib)** -- Subprocess orchestration. Spawns CLI agents with timeout control and streaming.
- **sentence-transformers + ChromaDB** -- Local semantic search. Offline, free, sufficient for thousands of modules.
- **PyGithub** -- GitHub API access for module discovery. Typed models, pagination, rate limit handling.
- **Docker SDK + pylint-odoo** -- Validation pipeline. Real Odoo 17 installation testing + OCA quality linting.
- **Jinja2** -- Code templating. Module scaffolding with template inheritance.
- **Ruff** -- Linter + formatter. Replaces Flake8+Black+isort. 150x faster.

**Critical version constraint:** `requires-python = ">=3.12,<3.13"`. This is non-negotiable.

**Dependency warning:** sentence-transformers pulls PyTorch (~2GB). Offer CPU-only install and pre-built embedding index as alternatives.

### Expected Features

**Must have (table stakes -- P1):**
- Natural language input with structured follow-up questions -- the entry point to the tool
- Complete module file generation (models, views, security, manifest, tests) with real content, not stubs
- Security layer generation (ACLs + record rules + group hierarchy) -- the most commonly botched part of Odoo modules
- OCA quality compliance via pylint-odoo -- automated quality gate
- Human review checkpoints after each generation stage -- essential for trust in ERP code
- Docker-based validation (install + test execution) -- the only reliable proof a module works
- Test generation with actual assertions (TransactionCase, access rights tests)
- CLI interface with rich terminal output

**Should have (differentiators -- P2):**
- Semantic search of GitHub/OCA repositories -- the "search-first" core differentiator
- Fork-and-extend workflow -- adapt existing modules instead of rebuilding from scratch
- Multi-agent specialization -- different agents for models, views, security, tests
- Incremental diff review at each generation stage
- Manifest dependency resolution -- auto-detect correct module dependencies

**Defer (v2+):**
- Module adaptation intelligence (deep Odoo ORM understanding for fork modification)
- Actionable validation feedback (parsing Odoo logs to diagnose failures)
- CE/EE edition awareness
- Odoo 18.0 support -- only after 17.0 pipeline is proven solid

**Anti-features (explicitly avoid):**
- Web UI (developers live in terminals; adds months of scope for marginal UX gain)
- Autonomous production deployment (ERP modules affect live business data; human deploys)
- Multi-version support in v1 (version blindness is the #1 AI code generation flaw per Odoo Experience 2025)
- Full business logic generation without review (silent failures in ERP are the worst outcome)

### Architecture Approach

The system is a five-layer architecture: CLI (user interface), Orchestration (pipeline control + state + checkpoints), Agent Execution (adapter pattern wrapping each AI CLI tool), Search/Retrieval (semantic module matching), and Validation (Docker + linting). The pipeline is sequential with checkpoint gates -- models must exist before views, views before security, everything before tests. Each generation task uses a maker-checker loop (one agent generates, another validates, max 3 iterations). State is persisted after every stage for crash recovery and resume capability.

**Major components:**
1. **Pipeline Controller** -- orchestrates the sequential generation flow with stage transitions and checkpoint gates
2. **Agent Adapters** -- uniform interface wrapping Claude Code, Codex CLI, Gemini CLI as interchangeable subprocesses
3. **Interactive Questioner** -- LLM-powered requirement gathering with Odoo-specific follow-up questions
4. **Search Engine** -- GitHub/OCA API search + embedding-based semantic re-ranking with version/quality filtering
5. **Generator Tasks** -- per-file-type code generation (models, views, security, logic, tests, i18n) with Odoo domain prompts
6. **Validation Pipeline** -- pylint-odoo + Docker install + test execution as the quality gate
7. **State Manager** -- persistent pipeline state for resumability; immutable state transitions

**Key patterns:**
- Sequential pipeline with checkpoint gates (not parallel, due to file dependencies)
- Adapter pattern for multi-LLM support (swap agents without pipeline changes)
- Maker-checker loops for quality (generator + reviewer agent per task)
- Persistent state for resumability (JSON files, `odoo-gen resume` command)
- Two-path decision router (fork-and-extend vs. build-from-scratch based on search results)

### Critical Pitfalls

1. **Odoo version confusion** -- LLMs mix v8-v18 patterns. Generated code uses deprecated `@api.multi`, `_columns`, or `openerp` imports. Prevention: version-pinned pylint-odoo on every output, Odoo 17 API examples in every agent prompt, version canary tests. Address in Phase 1.

2. **God agent anti-pattern** -- Single agent generating all files produces inconsistent cross-references (views referencing non-existent fields, security ACLs with wrong model names). 79% of multi-agent system failures originate from specification/coordination issues. Prevention: single-responsibility agents with strict input/output contracts, no prompt exceeding 6K tokens. Address in Phase 3.

3. **Security as afterthought** -- ACLs generated after models create mismatches. Missing record rules, wrong model references, flat group hierarchies. The most common "looks done but isn't" failure. Prevention: generate security IN PARALLEL with models, automated cross-reference validation. Address in Phase 3.

4. **Docker validation false confidence** -- Tests pass against empty database with admin user. Module breaks in production with existing data, restricted users, other modules installed. Prevention: install common base modules (sale, purchase, account), test as non-admin user, seed demo data. Address in Phase 2.

5. **Context window overflow** -- Module context grows beyond effective attention. Field names become inconsistent across files. "Lost in the middle" phenomenon degrades output silently. Prevention: pass schema references not full code, cap agent context at 50% of window, cross-file consistency checks. Address in Phase 3.

6. **Search returning noise** -- GitHub API limitations (10 req/min code search, 1000 result cap). OCA module descriptions are vague. Wrong-version modules appear as top results. Prevention: filter by Odoo version first, check maintenance signals, prefer OCA repos, pre-index locally. Address in Phase 4.

7. **Fork-and-extend producing unmaintainable code** -- AI rewrites core methods instead of using Odoo inheritance (`_inherit`, xpath). Merge conflicts with upstream become impossible. Prevention: 40% modification threshold (exceed it = build from scratch), enforce inheritance patterns, track fork divergence. Address in Phase 4.

## Implications for Roadmap

Based on combined research, here is the suggested phase structure. The ordering is driven by three principles: (1) dependencies (you cannot validate what you have not generated), (2) risk front-loading (tackle the hardest unknowns early), and (3) incremental value delivery (each phase produces a usable artifact).

### Phase 1: Foundation (CLI + Scaffold + Configuration)

**Rationale:** Everything depends on the CLI skeleton, configuration system, and project structure. Building this first establishes the frame that all subsequent phases plug into.
**Delivers:** `odoo-gen` CLI with `new`, `validate`, `resume` commands. Jinja2 templates for Odoo 17.0 module structure. Configuration system (TOML-based). Pipeline state management (JSON persistence). Project scaffolding that creates valid but empty Odoo modules.
**Addresses features:** CLI interface, basic module scaffolding
**Avoids pitfalls:** Odoo version confusion (version-pinned templates from day one), API key exposure (environment/keychain only), CLI UX failures (progress feedback, interactive mode)
**Stack elements:** Python 3.12, uv, Typer, Rich, Pydantic, Jinja2, Ruff, mypy, pre-commit

### Phase 2: Validation Pipeline

**Rationale:** Build the quality gate BEFORE building the code generator. Without validation, you cannot verify that generation works. This also front-loads Docker infrastructure risk.
**Delivers:** `odoo-gen validate <module_path>` command. Docker manager (container lifecycle via Docker SDK). pylint-odoo integration with `--valid-odoo-versions=17.0`. Odoo install + test runner. Quality scoring and reporting. Realistic test environment (common modules installed, demo data, non-admin user).
**Addresses features:** Docker-based validation, OCA quality compliance
**Avoids pitfalls:** Docker validation false confidence (realistic environment from the start), version confusion (pylint-odoo catches wrong-version patterns)
**Stack elements:** Docker SDK, pylint-odoo, pytest, pytest-docker

### Phase 3: Single-Agent Generation Pipeline

**Rationale:** Deliver the core value proposition with minimal complexity. Start with one agent (Claude Code, the strongest general coder) to prove the generation pipeline end-to-end. This is where the highest technical risk lies (prompt engineering, cross-file consistency) and must be tackled before adding multi-agent complexity.
**Delivers:** End-to-end module generation from natural language input. Interactive questioner for requirement gathering. Sequential generation (models -> views -> security -> logic -> tests -> i18n). Human checkpoint system with approval/rejection. Maker-checker loop (generate + validate per stage). Single agent adapter (Claude Code).
**Addresses features:** Natural language input, complete module generation, security layer generation, test generation, human review checkpoints
**Avoids pitfalls:** God agent (decompose into per-file-type tasks even with single agent), security afterthought (generate security alongside models), context overflow (schema-based context, not full code), version confusion (Odoo 17 examples in every prompt)
**Stack elements:** Pydantic-AI, asyncio, Jinja2 templates, agent adapter pattern
**Research flag:** NEEDS DEEPER RESEARCH. Prompt engineering for Odoo module components (models vs views vs security) requires iterative experimentation. Agent subprocess I/O behavior for Claude Code needs a spike.

### Phase 4: Search and Retrieval

**Rationale:** The "search-first" strategy is the project's core differentiator, but it is an enhancement to generation, not a prerequisite. You can generate modules without search; search makes them better. Building it after the generation pipeline means the fork-and-extend path has a proven from-scratch path to fall back on.
**Delivers:** `odoo-gen search <description>` command. GitHub/OCA repository search. Embedding index for semantic module matching. Decision router (fork vs. scratch, 0.7 threshold). Fork-and-extend handler with Odoo inheritance patterns. Curated index of top 200 OCA modules for Odoo 17.0.
**Addresses features:** Semantic search, fork-and-extend workflow, manifest dependency resolution
**Avoids pitfalls:** Search noise (version filter first, quality thresholds, prefer OCA), Frankenstein forks (40% modification cap, enforce inheritance, track divergence)
**Stack elements:** sentence-transformers, ChromaDB, PyGithub
**Research flag:** NEEDS DEEPER RESEARCH. OCA repo structure and manifest parsing need investigation. Embedding effectiveness on Odoo module descriptions needs benchmarking. GitHub API rate limits need workaround strategy.

### Phase 5: Multi-Agent + Quality Loops

**Rationale:** Adding multiple LLM agents requires a stable pipeline to enhance. This phase improves output quality through agent specialization and competition, not by changing the pipeline structure.
**Delivers:** Additional agent adapters (Codex CLI, Gemini CLI). Agent routing (best agent per task type). Maker-checker loops across different agents (one generates, another reviews). Fallback chains (if preferred agent fails, try next). Parallel execution for independent tasks.
**Addresses features:** Multi-agent specialization, incremental diff review
**Avoids pitfalls:** God agent (specialized agents with bounded prompts), tight coupling to single LLM (adapter pattern)
**Stack elements:** asyncio parallel execution, additional agent adapters
**Research flag:** NEEDS SPIKE. Each CLI agent (Claude Code, Codex, Gemini) has different subprocess I/O behavior. Routing heuristics (which agent for which task) need empirical testing.

### Phase Ordering Rationale

- **Foundation before everything** because CLI, state management, and configuration are dependencies for every other component.
- **Validation before generation** because without validation you cannot verify generated code works. Building validation early means every subsequent phase can be tested against real Odoo 17.0.
- **Single-agent generation before search** because the from-scratch pipeline is simpler, delivers core value, and provides a fallback for the fork-and-extend path. Generation is the core promise; search is the differentiator.
- **Search after generation** because search enhances generation quality but does not enable it. A working from-scratch pipeline must exist before fork-and-extend can be built.
- **Multi-agent last** because orchestrating multiple LLMs is the highest-complexity, lowest-urgency enhancement. The pipeline must be stable before adding this dimension.
- **Human checkpoints woven into Phase 3** (not a separate phase) because they are integral to the generation flow, not a bolt-on feature.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Single-Agent Generation):** Prompt engineering for Odoo module components is iterative and domain-specific. Need to research effective few-shot examples, context structures, and Odoo 17 API patterns for each file type (models, views, security, wizards). Agent subprocess I/O behavior for Claude Code needs a spike.
- **Phase 4 (Search and Retrieval):** OCA repository structure is not well-documented for automated parsing. Need to research manifest schema, README conventions, and effective embedding strategies for code module descriptions. GitHub API rate limits need workaround design.
- **Phase 5 (Multi-Agent):** Agent routing heuristics (which LLM is best for which Odoo task) need empirical benchmarking. Subprocess I/O differs across agents.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** CLI frameworks, configuration, project structure are well-documented. Typer, Pydantic, Jinja2 have excellent docs.
- **Phase 2 (Validation):** Docker-based testing and pylint-odoo integration are well-documented by Odoo and OCA. Standard patterns apply.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via PyPI and official docs. Python 3.12 constraint is firm and verified against Odoo 17 Docker image. Every library supports 3.12. |
| Features | MEDIUM | Table stakes are clear from competitor analysis and Odoo Experience 2025 talks. Differentiator value (search-first, fork-and-extend) is logical but unproven in this specific domain. Anti-features are well-reasoned. |
| Architecture | MEDIUM | Subprocess-adapter pattern validated by multiple OSS projects. Sequential pipeline with checkpoints is standard. The specific combination (multi-LLM + semantic search + Odoo domain + fork-and-extend) is novel enough that integration patterns need validation. |
| Pitfalls | MEDIUM-HIGH | Odoo version confusion, security afterthought, and Docker false confidence are well-documented by OCA and Odoo Experience talks. God agent and context overflow are supported by peer-reviewed research. Fork divergence risks come from ICSE 2020 paper. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Agent subprocess behavior:** How exactly do Claude Code, Codex CLI, and Gemini CLI differ in subprocess I/O (stdin prompts, stdout format, exit codes, error handling)? Need a practical spike before Phase 3.
- **OCA repo indexing:** How are OCA repos organized? What metadata is in each `__manifest__.py`? How many Odoo 17.0 modules exist across OCA? Need to crawl and analyze before Phase 4.
- **Embedding effectiveness on Odoo descriptions:** How well does all-MiniLM-L6-v2 perform on short module descriptions and README content? Need benchmarking with real OCA modules before Phase 4.
- **Prompt engineering for Odoo:** What prompting patterns produce the best Odoo model/view/security code? This is iterative and will need continuous research during Phase 3.
- **Token cost per module:** With unconstrained API budget, still worth understanding cost to set expectations. Maker-checker loops could mean 12-48 API calls per module.
- **CE vs EE structural differences:** How do Community and Enterprise edition modules differ? Impacts template design if EE support is added later.

## Sources

### Primary (HIGH confidence)
- [Odoo 17 Docker Hub](https://hub.docker.com/_/odoo) -- Docker image tags, Python compatibility
- [Odoo 17.0 Developer Documentation](https://www.odoo.com/documentation/17.0/developer/tutorials/backend.html) -- Module structure, ORM API, security
- [Odoo 17.0 Security Documentation](https://www.odoo.com/documentation/17.0/developer/reference/backend/security.html) -- ACLs, record rules, groups
- [OCA pylint-odoo](https://github.com/OCA/pylint-odoo) -- Version 10.0.1, official OCA linting
- [OCA Coding Standards](https://odoo-community.org/resources/code) -- Quality requirements
- [GitHub REST API Rate Limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) -- API constraints
- [Microsoft Azure Architecture Center: AI Agent Design Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) -- Orchestration patterns
- [PyPI verified versions](https://pypi.org) -- Typer 0.24.1, Rich 14.3.3, Pydantic 2.12.5, Pydantic-AI 1.63.0, ChromaDB 1.5.2, sentence-transformers 5.2.3, Ruff 0.15.4, pytest 9.0.2
- [uv documentation](https://docs.astral.sh/uv/) -- Package manager
- [Evil Martians: CLI UX Best Practices](https://evilmartians.com/chronicles/cli-ux-best-practices-3-patterns-for-improving-progress-displays) -- CLI design patterns
- [Fork Management Challenges (ICSE 2020)](https://dl.acm.org/doi/10.1145/3377813.3381362) -- Fork divergence research

### Secondary (MEDIUM confidence)
- [Why Multi-Agent LLM Systems Fail (arXiv)](https://arxiv.org/html/2503.13657v1) -- 79% failure rate from specification issues
- [Anthropic 2026 Agentic Coding Trends Report](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf) -- Industry patterns
- [Beyond Code Generation: AI in Odoo SDLC (Odoo Experience 2025)](https://oduist.com/blog/odoo-experience-2025-ai-summaries-2/305-beyond-code-generation-integrating-ai-into-odoo-s-development-lifecycle-lessons-learned-306) -- Version blindness, human review
- [Developing Odoo Modules Using AI (Odoo Experience 2025)](https://oduist.com/blog/odoo-experience-2025-ai-summaries-2/357-developing-odoo-modules-using-ai-a-practical-guide-358) -- Practical patterns
- [AI-Agents-Orchestrator (GitHub)](https://github.com/hoangsonww/AI-Agents-Orchestrator) -- Multi-LLM adapter pattern
- [Factory.ai: Context Window Problem](https://factory.ai/news/context-window-problem) -- Attention degradation
- [A Plan-Do-Check-Act Framework for AI Code Generation (InfoQ)](https://www.infoq.com/articles/PDCA-AI-code-generation/) -- Checkpoint patterns
- [Gemini-Odoo-Module-Generator (GitHub)](https://github.com/jeevanism/Gemini-Odoo-Module-Generator) -- Competitor analysis

### Tertiary (LOW confidence)
- [Claude Code Bridge (GitHub)](https://github.com/bfly123/claude_code_bridge) -- Multi-AI collaboration reference
- [Claude Octopus (GitHub)](https://github.com/nyldn/claude-octopus) -- Multi-agent coordinator reference
- [Parallel Code (GitHub)](https://github.com/johannesjo/parallel-code) -- Worktree-based parallel execution
- [Faros AI: Best AI Coding Agents 2026](https://www.faros.ai/blog/best-ai-coding-agents-2026) -- Single commercial source
- [dasroot.net: Multi-Agent Multi-LLM Systems 2026](https://dasroot.net/posts/2026/02/multi-agent-multi-llm-systems-future-ai-architecture-guide-2026/) -- Single source

---
*Research completed: 2026-03-01*
*Ready for roadmap: yes*
