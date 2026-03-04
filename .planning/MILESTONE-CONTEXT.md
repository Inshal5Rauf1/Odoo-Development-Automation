# Milestone Context: Environment-Aware Generation

**Source:** User analysis + two external references:
- [Spec-Driven Development (AgentFactory/Panaversity)](https://agentfactory.panaversity.org/docs/General-Agents-Foundations/spec-driven-development/why-specs-beat-vibe-coding)
- [Personal AI Employee (Psqasim)](https://github.com/Psqasim/personal-ai-employee)

## Gap Analysis: What We Have vs. What's Missing

### Already Incorporated (no action needed)

| Concept | Source | Our Implementation |
|---------|--------|--------------------|
| Spec-first generation | SDD | JSON spec → 3 human checkpoints → code generation |
| Multi-agent orchestration | Both | 8 specialized agents via GSD wave execution |
| Knowledge base / "constitution" | SDD | 13 domain files, 80+ WRONG/CORRECT pairs, agent @includes |
| Parallel research subagents | SDD | GSD's 4 parallel researchers (Stack, Features, Architecture, Pitfalls) |
| Human-in-the-loop approval | Both | 3 GSD checkpoints in generate.md workflow |
| Interview/refinement phase | SDD | Follow-up questions in /odoo-gen:new |
| Task delegation with deps | SDD | GSD phase/wave/plan execution |
| Role assignment for agents | SDD | 8 agent .md files with focused responsibilities |
| Validation pipeline | User suggestion | pylint-odoo + Docker install + Docker test execution |
| Auto-fix loops | User suggestion | pylint W0611 + Docker missing_mail_thread dispatch |
| Immutable data patterns | Both | Frozen dataclasses, read-transform-write auto-fix |

### NOT Incorporated (gaps to close)

#### 1. Odoo MCP Server — Live Environment Awareness (HIGH)

**What:** An MCP server that connects to a running Odoo dev instance via XML-RPC/JSON-RPC, giving agents real-time access to the actual environment they're generating code for.

**Why it matters:** Currently our agents generate code based on static knowledge files and templates. They have no way to verify that:
- A target model (`hr.employee`, `sale.order`) actually exists in the user's instance
- An inherited model has the fields they expect
- A module dependency is installed
- Field types match the actual ORM schema

The personal-ai-employee project has a working Odoo MCP server (XML-RPC to `account.move`, `res.partner`) — but it's accounting-focused. We need a DEVELOPMENT-focused MCP that reads model schemas, field definitions, and installed modules.

**Capabilities needed:**
- Query `ir.model` and `ir.model.fields` for schema introspection
- List installed modules and their versions
- Validate view XML against Odoo's actual view architecture
- Check if module dependencies are satisfied
- Read existing model source code from addon paths

**Reference implementation:** `Psqasim/personal-ai-employee/mcp_servers/odoo_mcp/server.py` — uses `xmlrpc.client.ServerProxy` against `/xmlrpc/2/common` and `/xmlrpc/2/object` endpoints.

#### 2. Inline Environment Verification During Generation (HIGH)

**What:** Instead of validating ONLY after full module generation (current Docker-at-end approach), agents verify their output against the live Odoo instance AS they generate each artifact.

**Why it matters:** Current flow is batch:
```
Generate all files → Docker validate → Find errors → Auto-fix → Repeat
```

Proposed flow is inline:
```
Generate model → Verify inheritance chain against live instance
Generate view → Verify field references against actual model schema
Generate security → Verify group hierarchy against installed groups
Generate tests → Verify test base class and fixtures work
```

This turns the agent from "best guess then fix" into "verify as you go" — catching errors at source rather than at the end.

**Impact:** Dramatically reduces auto-fix loop iterations and catches inheritance/field reference errors that currently only surface during Docker install.

#### 3. Context7 MCP for Live Documentation (MEDIUM)

**What:** MCP integration with Context7 for real-time access to Odoo documentation, changelogs, and migration guides during agent execution.

**Why it matters:** Our knowledge base is static (13 manually-maintained files). When Odoo releases updates, our knowledge base is stale until manually updated. Context7 provides:
- Live API documentation for any Odoo version
- Migration guides between versions (17.0 → 18.0)
- OCA module documentation
- Field type reference, widget reference, QWeb syntax

**Complements existing KB:** Static knowledge base stays as the "constitution" (WRONG/CORRECT patterns). Context7 provides supplementary real-time docs when agents hit unfamiliar territory.

#### 4. Expanded Docker Fix Patterns (MEDIUM — known tech debt)

**What:** `FIXABLE_DOCKER_PATTERNS` currently handles 1 of 5 identified error patterns. Expand to cover remaining 4.

**Known patterns needing implementation:**
- Missing module dependency (auto-add to depends)
- Missing field reference in view XML (auto-fix view or model)
- Security access violation (auto-generate missing ACL)
- Missing data file in manifest (auto-add to data list)

**Why it matters:** Each unhandled pattern means a human must manually fix and re-run, breaking the automation promise.

#### 5. Bounded Auto-Fix Iterations (LOW)

**What:** Explicit iteration caps on auto-fix loops (pylint fix loop and Docker fix loop) to prevent infinite cycling.

**Reference:** Personal-ai-employee uses "Ralph Wiggum loop capped at 10 iterations" for bounded reasoning.

**Why it matters:** Currently, if an auto-fix introduces a new error that triggers another fix that re-introduces the original error, the loop could cycle indefinitely. Adding caps (e.g., max 5 iterations) with escalation to human when exhausted.

#### 6. CLI --auto-fix Integration Test (LOW — known tech debt)

**What:** The `validate --auto-fix` CLI path has no integration test. Add one that exercises the full path: module with known violations → validate --auto-fix → violations resolved.

#### 7. Generation Pipeline Observability (LOW)

**What:** File-state-machine pattern for tracking artifact progression through generation stages.

**Reference:** Personal-ai-employee uses markdown files flowing through folders (`Inbox/ → Needs_Action/ → Pending_Approval/ → Approved/ → Done/`).

**Odoo module equivalent:**
- `spec.json` → draft → approved
- `models/*.py` → generated → validated → approved
- `views/*.xml` → generated → validated → approved
- `security/*.csv` → generated → validated → approved

**Why it matters:** Currently generation is opaque — you see the final output but not intermediate states. Pipeline observability helps debug generation failures and gives users visibility into progress.

## Priority Assessment

| Gap | Impact | Effort | Recommendation |
|-----|--------|--------|----------------|
| Odoo MCP Server | HIGH | MEDIUM | v1.3 core feature |
| Inline Environment Verification | HIGH | HIGH | v1.3 core feature (depends on MCP) |
| Context7 MCP Integration | MEDIUM | LOW | v1.3 if time permits |
| Expanded Docker Fix Patterns | MEDIUM | MEDIUM | v1.3 tech debt closure |
| Bounded Auto-Fix Iterations | LOW | LOW | v1.3 quick win |
| CLI --auto-fix Integration Test | LOW | LOW | v1.3 quick win |
| Generation Pipeline Observability | LOW | MEDIUM | v1.4 or later |

## Suggested Milestone Scope

**Name:** v1.3 — Environment-Aware Generation

**Core thesis:** Move from "generate then validate" to "verify as you generate" by connecting agents to a live Odoo instance via MCP.

**Must-have:**
1. Odoo MCP server (XML-RPC model introspection, installed module checks)
2. Agent integration with MCP (model-gen and view-gen agents verify inline)
3. Expanded Docker fix patterns (close remaining 4/5)

**Should-have:**
4. Context7 MCP integration for live docs
5. Bounded auto-fix iterations
6. CLI --auto-fix integration test

**Could-have:**
7. Generation pipeline observability

## New Prior Art

| Project | Relevance | How to use |
|---------|-----------|------------|
| **Personal AI Employee** (Psqasim) | ADOPT PATTERN | Odoo MCP server architecture (XML-RPC, tool definitions, safety-first) |
| **AgentFactory SDD** (Panaversity) | REFERENCE | Three SDD levels, constitution pattern — validates our existing approach |
| **Context7** | INTEGRATE | Live documentation MCP for real-time Odoo API reference |
