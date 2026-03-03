# Retrospective

## Milestone: v1.0 — Odoo Module Automation MVP

**Shipped:** 2026-03-03
**Phases:** 9 | **Plans:** 26 | **Commits:** 139 | **Timeline:** 3 days

### What Was Built

1. GSD extension architecture with 12 commands, 8 specialized AI agents, install.sh-based setup
2. Comprehensive Odoo 17.0 knowledge base (13 domain files, 80+ WRONG/CORRECT example pairs)
3. Validation pipeline: pylint-odoo integration + Docker-based Odoo validation + auto-fix loops
4. Specification pipeline: natural language to structured JSON spec with tiered follow-up questions and approval gate
5. Jinja2 rendering engine: 24 templates producing models, views, security, wizards, tests, i18n
6. Semantic search: ChromaDB vector index + OCA repo crawl + gap analysis + fork-and-extend workflow
7. Edition/version support: Enterprise module registry, version-aware templates (17.0/18.0/shared), FileSystemLoader fallback

### What Worked

- **GSD extension model**: Inheriting orchestration (~19% of requirements) let us focus entirely on Odoo domain logic
- **TDD workflow**: RED/GREEN approach prevented regressions across 243 tests — zero test failures at milestone end
- **Wave-based execution**: Parallel plan execution within phases kept velocity high (avg 4.4 min/plan)
- **Knowledge base architecture**: WRONG/CORRECT example pairs in knowledge files effectively guided AI agents
- **Jinja2 + AI hybrid**: Deterministic template rendering for structure + AI agents for business logic was the right split
- **Phase sequencing**: Building validation (Phase 3) before generation (Phase 5) meant we could verify output quality from the start

### What Was Inefficient

- **Context exhaustion**: Multiple sessions hit context limits during complex workflows (milestone audit, complete-milestone), requiring state serialization and resumption
- **Frontmatter inconsistency**: SUMMARY.md files had varying frontmatter formats across phases, making automated extraction difficult
- **Docker validation untested**: All Docker integration tests mock subprocess — never validated against a live Odoo 17.0 Docker instance
- **gh CLI not authenticated**: Search features require `gh auth login` which was never set up during development
- **Orphaned templates**: 3 template files (view_search.xml.j2, view_tree.xml.j2 x2) were created but never wired into the renderer

### Patterns Established

- **Agent + Knowledge pattern**: Each agent gets @include references to relevant knowledge files, preventing hallucinations
- **Immutable data flow**: Frozen dataclasses for validation types, tuple fields for hashability
- **CLI wrapping venv**: bin/odoo-gen-utils wrapper script resolves Python venv portably
- **Spec-first generation**: JSON spec is source of truth; all downstream tools consume it
- **Version-aware templates**: FileSystemLoader([version_dir, shared_dir]) for clean version separation

### Key Lessons

1. **Fix integration bugs early**: The extract-i18n argument mismatch (2 args passed, 1 accepted) persisted through multiple phases because Step 3.5 is non-blocking. Integration testing across workflow boundaries catches these.
2. **Frontmatter should be standardized**: Agreeing on SUMMARY.md schema early would have made milestone extraction trivial.
3. **GSD tooling accelerates**: `gsd-tools` CLI for commits, state updates, and phase management removed significant boilerplate from every plan execution.
4. **3-day build is achievable**: 9 phases, 68 requirements, 4,150 LOC in 3 days with AI-assisted development at quality profile (Opus for all agents).

### Cost Observations

- Model mix: 100% Opus (quality profile selected for entire milestone)
- Sessions: ~8 context windows consumed (several exhaustions required /clear + resume)
- Notable: Average plan execution was 4.4 minutes — the bottleneck was planning and review, not execution

---

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 9 |
| Plans | 26 |
| Requirements | 68 |
| LOC (Python) | 4,150 |
| Tests | 243 |
| Commits | 139 |
| Timeline (days) | 3 |
| Avg plan duration | 4.4 min |

---
*Last updated: 2026-03-03*
