# Agentic Odoo Module Development Workflow

## What This Is

A domain-specific extension of the GSD (Get Shit Done) framework that automates Odoo 17.0 and 18.0 module development end-to-end. A developer describes a business need in natural language through their AI coding assistant (Claude Code, Gemini, Codex, OpenCode), the system semantically searches GitHub and the Odoo Community Association (OCA) for similar modules, then either forks and extends a match or builds from scratch — producing OCA-grade modules through 8 coordinated AI agents with human review at 3 checkpoints.

**This is NOT a standalone CLI tool.** It is a GSD extension — agents, workflows, commands, templates, and a knowledge base that plug into GSD's orchestration layer. GSD handles context management, state persistence, hallucination prevention, phase execution, and checkpoint coordination. We build the Odoo-specific intelligence on top.

## Current State

**Shipped:** v1.0 (2026-03-03) — Odoo Module Automation MVP
- 9 phases, 26 plans, 139 commits over 3 days
- 4,150 LOC Python, 243 tests passing
- 8 agents, 13 knowledge files, 24 Jinja2 templates, 12 commands
- See: `.planning/MILESTONES.md` for details

## Core Value

Compress months of repetitive Odoo module development into days by leveraging GSD's orchestration + existing open-source modules as foundations + Odoo-specialized AI agents, so developers focus on business logic and design decisions.

## Architecture

```
Layer 1: GSD Orchestration (INHERITED — not built by us)
  - Context management, hallucination prevention
  - Phase/wave execution, state persistence
  - Checkpoint-based human review
  - Agent spawning with fresh context windows
  - Git integration, atomic commits

Layer 2: Odoo Extension (BUILT BY US)
  - Odoo-specific agents (model gen, view gen, security gen, etc.)
  - Odoo-specific workflows (module creation, validation, fork-and-extend)
  - Odoo-specific commands (/odoo-gen:new, /odoo-gen:validate, etc.)
  - Odoo knowledge base (OCA standards, Odoo 17 patterns, pylint-odoo rules)
  - Jinja2 templates for module scaffolding

Layer 3: Python Utilities (BUILT BY US)
  - Jinja2 template rendering engine
  - pylint-odoo integration
  - Docker-based Odoo 17 validation
  - ChromaDB semantic search index
  - Module structure analysis tools

Layer 4: AI Coding Assistant (USER'S ENVIRONMENT)
  - Claude Code, Gemini, Codex, OpenCode, etc.
  - GSD + odoo-gen extension installed
```

## Requirements

### Validated

**Inherited from GSD (v1.0):**
- CLI command invocation — v1.0
- Rich terminal output — v1.0
- Configuration file for settings — v1.0
- Help text and usage — v1.0
- Human review checkpoints — v1.0
- Approve/change/reject at checkpoints — v1.0
- State persistence and resumability — v1.0
- Extensible knowledge base — v1.0

**Odoo-specific (v1.0 — 68/68 requirements shipped):**
- User describes module need in natural language — v1.0
- System asks Odoo-specific follow-up questions — v1.0
- System parses input into structured module specification — v1.0
- User reviews and approves parsed spec before generation — v1.0
- System semantically searches GitHub/OCA for similar modules — v1.0
- System scores, ranks, and presents matches with gap analysis — v1.0
- System forks and extends matching modules when chosen — v1.0
- System builds modules from scratch when no match — v1.0
- System generates complete module files (models, views, security, manifest, tests) — v1.0
- Generated modules install cleanly on Odoo 17.0 (CE and EE) — v1.0
- Generated modules include full security (ACLs, record rules, group hierarchy) — v1.0
- Generated modules include tests with real assertions — v1.0
- Generated modules pass OCA quality standards (pylint-odoo, i18n) — v1.0
- Docker-based Odoo 17 validates installation and test execution — v1.0
- System auto-fixes pylint/Docker failures before escalating to human — v1.0
- System supports Odoo 17.0 (primary) and 18.0, CE and EE editions — v1.0

### Active

(No active requirements — next milestone not yet planned)

### Out of Scope

- Web UI / browser interface — GSD extension runs inside AI coding assistants
- Mobile app — not applicable
- Standalone CLI tool — we inherit GSD's interface, not build our own
- Building our own orchestration layer — GSD provides this
- Real-time collaborative editing — single-user workflow
- Module deployment to production — system generates, human deploys
- Offline mode — requires AI coding assistant with internet access

## Context

- v1.0 shipped 2026-03-03 with 4,150 LOC Python, 243 tests, and full pipeline coverage
- Tech stack: Python 3.12, Jinja2, Click CLI, pylint-odoo, ChromaDB, sentence-transformers, Docker
- 8 specialized agents: odoo-scaffold, odoo-model-gen, odoo-view-gen, odoo-test-gen, odoo-security-gen, odoo-validator, odoo-search, odoo-extend
- 12 user commands via /odoo-gen:* prefix (new, validate, search, plan, extend, etc.)
- 13 knowledge base files covering Odoo 17.0/18.0 OCA standards
- Known tech debt: 7 items (3 orphaned templates, gh CLI auth setup, Docker live testing, field string= i18n, missing Phase 9 VERIFICATION.md)
- Distribution: users clone into `~/.claude/odoo-gen/` and run `install.sh`

## Constraints

- **Dependency**: Requires GSD installed (`~/.claude/get-shit-done/`)
- **Target Version**: Odoo 17.0 primary, 18.0 secondary
- **Quality Standard**: OCA-grade — pylint-odoo clean, proper i18n, full security, tests
- **Interface**: GSD commands via AI coding assistant (not standalone CLI)
- **Distribution**: Clone into `~/.claude/odoo-gen/` (like GSD)
- **Edition Support**: Both Community and Enterprise
- **Test Infrastructure**: Docker-based Odoo instances for validation
- **Build Strategy**: Search-first — check for existing modules before building from scratch
- **Human Oversight**: GSD checkpoint-based review at key generation stages
- **API Budget**: Unconstrained — prioritize quality
- **Python Utilities**: Python 3.12 (Odoo 17 constraint: 3.10-3.12 only, 3.13+ breaks validation)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GSD extension (not standalone CLI) | GSD provides orchestration, context management, hallucination prevention | Good — inherited ~19% of requirements for free |
| Depend on GSD (not fork) | Benefit from GSD updates automatically, avoid divergence | Good — no maintenance burden |
| Clone-based install (~/.claude/) | Same pattern as GSD, works with any AI coding assistant | Good — simple setup via install.sh |
| Odoo 17.0 primary target | Stable, widely adopted, strong OCA support | Good — 18.0 added as secondary |
| Fork-and-extend strategy | Leverage existing OCA/GitHub modules as foundation | Good — ChromaDB search + companion _ext modules |
| Semantic search (ChromaDB + sentence-transformers) | Intent-based matching, not just keywords | Good — requires PyTorch (~2GB), CPU-only configured |
| Python 3.12 for utilities | Odoo 17 supports 3.10-3.12 only; 3.13+ breaks validation | Good — uv venv isolation works |
| Checkpoint-based human review | GSD provides the mechanism; we wire Odoo-specific checkpoints | Good — 3 checkpoints in generate.md |
| OCA quality as the bar | pylint-odoo, i18n, full security, tests | Good — auto-fix loops reduce manual work |
| Docker for validation | Only way to truly verify module installs and tests pass | Partial — all tests mock subprocess, no live testing yet |
| UI UX Pro Max Skill pattern | Reasoning engine + hierarchical system + rule library | Good — knowledge base architecture follows this |
| Jinja2 deterministic + AI enrichment | Structural files via templates, business logic via agents | Good — hybrid approach prevents hallucinations |
| Version-aware template fallback | FileSystemLoader([version_dir, shared_dir]) | Good — clean 17.0/18.0 separation |

## Prior Art

| Project | Relevance | How we use it |
|---------|-----------|---------------|
| **GSD (Get Shit Done)** | INHERIT | Full orchestration layer — context, state, phases, agents, checkpoints |
| **erp_claude** (Baptiste-banani) | ADOPT KNOWLEDGE | Odoo 17 model/view skills → foundation for our knowledge base |
| **UI UX Pro Max Skill** | ADOPT PATTERN | Reasoning engine, hierarchical system, rule library → template for our skill architecture |
| **Ralph** (snarktank) | REFERENCE | Fresh context loop + accumulated knowledge pattern → confirms GSD approach |
| **Cognee** (topoteretes) | REFERENCE | Knowledge graph pipeline (cognify/memify/search) → informs knowledge base design |
| **LangExtract** (Google) | REFERENCE | Source-grounded extraction → informs spec parsing approach |
| **Agent Lightning** (Microsoft) | FUTURE | RL-based agent optimization → v2+ when we have agents to optimize |
| **Gemini-Odoo-Module-Generator** | COMPETITOR | Single-agent Gemini CLI → baseline we must exceed |
| **Ruflo** (ruvnet) | SKIP | Over-engineered for our needs (60+ agents, Byzantine consensus) |
| **LobeHub** | SKIP | Web chat platform, different product category |

---
*Last updated: 2026-03-03 after v1.0 milestone*
