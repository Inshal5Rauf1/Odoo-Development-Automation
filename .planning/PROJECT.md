# Agentic Odoo Module Development Workflow

## What This Is

A domain-specific extension of the GSD (Get Shit Done) framework that automates Odoo 17.0 and 18.0 module development end-to-end. A developer describes a business need in natural language through their AI coding assistant (Claude Code, Gemini, Codex, OpenCode), the system semantically searches GitHub and the Odoo Community Association (OCA) for similar modules, then either forks and extends a match or builds from scratch — producing OCA-grade modules through 8 coordinated AI agents with human review at 3 checkpoints.

**This is NOT a standalone CLI tool.** It is a GSD extension — agents, workflows, commands, templates, and a knowledge base that plug into GSD's orchestration layer. GSD handles context management, state persistence, hallucination prevention, phase execution, and checkpoint coordination. We build the Odoo-specific intelligence on top.

## Current State

**Shipped:** v2.1 (2026-03-04) — Auto-Fix & Enhancements
- 19 phases total across 5 milestones, 45 plans, 270+ commits over 4 days
- Auto-fix pipeline handles all 5 common Docker error patterns with bounded iterations
- Context7 REST client for live Odoo documentation queries (graceful fallback)
- Artifact state tracking with JSON sidecar persistence and CLI display
- MCP server with 6 tools for live Odoo introspection (XML-RPC)
- Docker Compose dev environment with Odoo 17 CE + PostgreSQL
- 444 tests passing, 15,700+ LOC Python (src + tests)
- See: `.planning/MILESTONES.md` for full history

## Next Milestone Goals

No milestone currently planned. Ready for `/gsd:new-milestone` to define next direction.

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
  - Auto-fix pipeline (pylint + Docker error dispatch)

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

**Template Quality (v1.2):**
- Templates produce correct mail.thread inheritance when mail in depends — v1.2
- Templates produce conditional api import (only when decorators used) — v1.2
- Templates produce clean manifests (no superfluous keys) — v1.2
- Templates produce clean test imports (no unused ValidationError) — v1.2
- Auto-fix detects missing mail.thread and adds _inherit line — v1.2
- Auto-fix detects and removes unused imports (AST-based) — v1.2
- Knowledge base documents mail.thread rules and triple dependency — v1.2
- Golden path E2E test catches template regressions (render → Docker install → test) — v1.2
- Auto-fix functions wired into CLI runtime (run_docker_fix_loop + pylint W0611) — v1.2

### Validated (cont.)

**Environment-Aware Generation (v2.0):**
- Odoo dev instance via Docker Compose (XML-RPC accessible, data persists) — v2.0
- MCP server with 6 tools: list_models, get_model_fields, list_installed_modules, check_module_dependency, get_view_arch, check_connection — v2.0
- Inline model verification: _inherit, relational comodels, field overrides checked against live instance — v2.0
- Inline view verification: field references and inherited view targets checked against live instance — v2.0
- Graceful degradation when MCP/Odoo unavailable (warnings, not blocks) — v2.0

**Auto-Fix & Enhancements (v2.1):**
- Docker auto-fix pipeline identifies 5 error patterns, auto-fixes 4 mechanically deterministic ones — v2.1
- Pylint and Docker fix loops capped at configurable max (default 5) with escalation — v2.1
- validate --auto-fix resolves violations end-to-end, verified by CI-safe integration test — v2.1
- Context7 MCP for live Odoo docs with graceful fallback (KB remains primary) — v2.1
- Artifact state tracking (pending/generated/validated/approved) with JSON sidecar and CLI display — v2.1

### Active

No active requirements — ready for next milestone definition

### Out of Scope

- Web UI / browser interface — GSD extension runs inside AI coding assistants
- Mobile app — not applicable
- Standalone CLI tool — we inherit GSD's interface, not build our own
- Building our own orchestration layer — GSD provides this
- Real-time collaborative editing — single-user workflow
- Module deployment to production — system generates, human deploys
- Offline mode — requires AI coding assistant with internet access

## Context

- v2.0 shipped 2026-03-04 — environment-aware generation via MCP (Phases 15-17)
- v1.2 shipped 2026-03-04 — template correctness, golden path E2E, auto-fix dispatch wiring
- v1.1 shipped 2026-03-03 — GitHub auth, dependency cleanup, live Docker testing, field string= i18n
- v1.0 shipped 2026-03-03 with 4,150 LOC Python, 243 tests, and full pipeline coverage
- Tech stack: Python 3.12, Jinja2, Click CLI, pylint-odoo, ChromaDB, Docker
- 8 specialized agents: odoo-scaffold, odoo-model-gen, odoo-view-gen, odoo-test-gen, odoo-security-gen, odoo-validator, odoo-search, odoo-extend
- 12 user commands via /odoo-gen:* prefix (new, validate, search, plan, extend, etc.)
- 13 knowledge base files covering Odoo 17.0/18.0 OCA standards
- v2.1 shipped: Docker auto-fix hardening (5 patterns), Context7 REST client, artifact state tracking
- Remaining tech debt: Context7 query_docs not wired into generation pipeline (available on-demand for agents)
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
| Semantic search (ChromaDB) | Intent-based matching, not just keywords | Good — uses built-in ONNX embedding (no PyTorch) |
| Python 3.12 for utilities | Odoo 17 supports 3.10-3.12 only; 3.13+ breaks validation | Good — uv venv isolation works |
| Checkpoint-based human review | GSD provides the mechanism; we wire Odoo-specific checkpoints | Good — 3 checkpoints in generate.md |
| OCA quality as the bar | pylint-odoo, i18n, full security, tests | Good — auto-fix loops reduce manual work |
| Docker for validation | Only way to truly verify module installs and tests pass | Good — live Docker tests verify real installation |
| Jinja2 deterministic + AI enrichment | Structural files via templates, business logic via agents | Good — hybrid approach prevents hallucinations |
| Version-aware template fallback | FileSystemLoader([version_dir, shared_dir]) | Good — clean 17.0/18.0 separation |
| AST-based import analysis | More reliable than regex for complex Python imports | Good — precise unused import detection |
| Immutable read-transform-write | Read file → create new content → compare → write if changed | Good — safe auto-fix pattern |
| Configurable iteration caps (default 5) | Prevent infinite fix loops, escalate to human | Good — replaced hardcoded 2 |
| missing_import excluded from auto-dispatch | Requires human judgment (install package vs add dep) | Good — right boundary |
| Context7 stdlib-only (urllib.request) | No new deps for simple GET calls | Good — zero dependency growth |
| JSON sidecar for artifact state | .odoo-gen-state.json alongside module | Good — non-intrusive observability |
| Warning-only invalid state transitions | Log warnings but never block generation | Good — observability never interferes |

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
| **Personal AI Employee** (Psqasim) | ADOPT PATTERN | Odoo MCP server architecture (XML-RPC, tool definitions, safety-first) |
| **AgentFactory SDD** (Panaversity) | REFERENCE | Three SDD levels, constitution pattern — validates our existing approach |
| **Context7** | INTEGRATE | Live documentation MCP for real-time Odoo API reference |

---
*Last updated: 2026-03-04 — after v2.1 milestone shipped*
