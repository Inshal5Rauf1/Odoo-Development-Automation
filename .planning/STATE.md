---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-03T04:27:00Z"
progress:
  total_phases: 9
  completed_phases: 8
  total_plans: 26
  completed_plans: 24
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** Compress months of repetitive Odoo module development into days by extending GSD's orchestration with Odoo-specialized agents, knowledge, and validation.
**Architecture:** GSD extension (not standalone CLI)
**Current focus:** Phase 9 - Edition & Version Support (Phases 1-8 complete)

## Current Position

Phase: 9 of 9 (Edition & Version Support) -- IN PROGRESS
Plan: 2 of 3 complete in Phase 9 (09-01, 09-02 done, 09-03 remaining)
Status: Plan 09-02 complete -- Versioned templates (17.0/18.0/shared) + version-aware renderer. Ready for 09-03.
Last activity: 2026-03-03 -- Completed 09-02 (versioned templates and renderer)

Progress: [█████████████████████████] 97% (Phases 1-8 complete, Phase 9: 2/3 plans done)

## Performance Metrics

**Velocity:**
- Total plans completed: 12
- Average duration: 4.4 min
- Total execution time: 0.9 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | 13 min | 3.25 min |
| 02 | 3 | 18 min | 6.0 min |
| 03 | 3 | 17 min | 5.7 min |
| 04 | 2 | 9 min | 4.5 min |

**Recent Trend:**
- Last 5 plans: 02-03 (5 min), 03-03 (6 min), 03-02 (6 min), 04-01 (5 min), 04-02 (4 min)
- Trend: Consistent

*Updated after each plan completion*

| Phase 05 P03 | 3 min | 2 tasks | 3 files |
| Phase 05 P01 | 7 | 2 tasks | 10 files |
| Phase 05 P02 | 2 min | 2 tasks | 3 files |
| Phase 06 P01 | 5min | 2 tasks | 3 files |
| Phase 06 P02 | 3min | 2 tasks | 4 files |
| Phase 07 P01 | 5min | 2 tasks | 3 files |
| Phase 07 P02 | 4 min | 2 tasks | 1 files |
| Phase 07 P03 | 7 min | 2 tasks | 4 files |
| Phase 08 P01 | 5 min | 2 tasks | 8 files |
| Phase 08 P02 | 4 min | 2 tasks | 6 files |
| Phase 08 P03 | 5 min | 2 tasks | 7 files |
| Phase 09 P02 | 3 min | 2 tasks | 26 files |
| Phase 09 P01 | 2 min | 1 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Architecture]: odoo-gen is a GSD extension, not a standalone CLI tool
- [Architecture]: Depend on GSD (not fork) — benefit from upstream updates
- [Architecture]: Clone-based install into ~/.claude/odoo-gen/
- [Architecture]: UI UX Pro Max Skill pattern for reasoning engine + rule library
- [Roadmap]: Phase 1 is GSD extension setup + Odoo foundation (not CLI build)
- [Roadmap]: Knowledge Base moved to Phase 2 (before validation, so agents have expertise)
- [Roadmap]: Phases 2 and 3 can run in parallel after Phase 1
- [Roadmap]: Old standalone CLI plans deleted — wrong architecture
- [Commands]: Forward reference to scaffold.md in new.md (resolved at invocation time)
- [Commands]: help.md uses inline command table (self-contained, no external workflow)
- [Templates]: Combined form+tree+search views into single per-model view file for render_module
- [Templates]: Single menu.xml for all models (cleaner OCA structure)
- [Package]: Hatchling build backend for pyproject.toml-native packaging
- [Agents]: Symlinks for agent registration (ln -sf) instead of copy -- keeps agents in extension dir
- [Agents]: odoo-scaffold agent includes comprehensive Odoo 17.0 specifics to prevent LLM hallucinations
- [Security]: defaults.json api_keys uses $ENV_VAR references resolved at runtime -- never stores secrets
- [Infra]: Wrapper script at bin/odoo-gen-utils resolves venv path portably across platforms
- [Workflows]: Scaffold workflow defines 4 phases: input parsing, spec confirmation, generation (odoo-gen-utils), post-generation
- [Workflows]: Help workflow uses inline table with Active/Planned status labels
- [Templates]: Chatter section in form views conditional on 'mail' in depends
- [Validation]: Tuples (not lists) for frozen dataclass fields -- immutability compliance
- [Validation]: noqa F401 on __init__.py re-exports to prevent ruff from stripping public API
- [Validation]: Recursive tuple-to-list conversion needed for JSON serialization of dataclasses
- [Knowledge]: Each knowledge file follows consistent Rule + WRONG + CORRECT + Why format with Changed in 17.0 section
- [Knowledge]: TransactionCase as primary test base class (SavepointCase deprecated in 17.0)
- [Knowledge]: tree (not list) in view_mode for Odoo 17.0
- [Knowledge]: All three inheritance patterns documented: _inherit, _inherits, _name+_inherit
- [Knowledge]: Jinja2 template syntax for email templates in data.md (Odoo 17.0 default)
- [Knowledge]: pylint-odoo rules in compact table format (Rule | Trigger | Fix) to save context budget
- [Knowledge]: models.md trimmed from 646 to 482 lines by consolidating examples while preserving all rules
- [Validation]: Regex alternation pattern for module-not-found parsing (quoted vs unquoted)
- [Validation]: Always-teardown guarantee via finally blocks in Docker runner
- [Validation]: Graceful degradation when Docker unavailable (return empty/failure results, no exceptions)
- [Knowledge]: Custom rules extend defaults, never override shipped rules
- [Knowledge]: Format-only validation for custom rules (headings, code blocks, line count)
- [Knowledge]: Knowledge base installed via symlink (same pattern as agents)
- [Knowledge]: validate-kb defaults to custom/ only; --all flag validates shipped + custom
- [Knowledge]: All 6 agents wired to KB via @include references to ~/.claude/odoo-gen/knowledge/
- [Validation]: Module-level caching for error patterns (avoid repeated JSON file I/O)
- [Validation]: IGNORECASE | MULTILINE regex flags for robust log matching
- [Validation]: Unrecognized errors fall back to raw traceback (not silent failure)
- [Validation]: validate CLI exit code 1 for any violations/failures, 0 only when fully clean
- [Workflows]: Spec workflow defines 4 phases: NL parsing, tiered follow-up, structured spec, approval
- [Workflows]: Tiered question strategy: 3-5 Tier 1 always, 0-3 Tier 2 on complexity triggers, max 8 total
- [Workflows]: 7 complexity triggers: workflow, multi-company, inheritance, portal, reporting, integration, automation
- [Spec]: Extended JSON spec schema backward-compatible with render-module (all new fields optional with null defaults)
- [Agents]: odoo-scaffold dual-mode: Quick Mode via /odoo-gen:new, Specification Mode via /odoo-gen:plan
- [Agents]: Agent KB expanded from 5 to 12 files for domain-specific question generation
- [Spec]: JSON-first rendering -- spec.json is source of truth, markdown summary is derived view
- [Spec]: Approval gate blocks generation -- no downstream process uses spec until user explicitly approves
- [Spec]: Targeted follow-up on changes -- 1-3 focused questions about flagged sections only
- [Spec]: 3-round iteration limit advisory (not hard stop) to prevent interrogation fatigue
- [Phase 05-03]: generate.md trigger placed in spec.md Step 4.3 AFTER spec commit and BEFORE report step
- [Phase 05-03]: Wave 1 sequential guard: all odoo-model-gen tasks complete before Wave 2 spawns (view-gen reads completed model files)
- [Phase 05-03]: CODG-09 corrected: Odoo 17.0 uses tree not list (list is Odoo 18+ only); CODG-10 corrected to README.rst (OCA standard)
- [Phase 05]: Jinja2 StrictUndefined requires field.compute is defined check for optional spec keys
- [Phase 05]: Canonical manifest ordering: security -> sequences -> data -> views -> wizard views
- [Phase 05-02]: odoo-model-gen uses Write tool to rewrite ENTIRE model file (not patch stubs inline)
- [Phase 05-02]: odoo-view-gen Wave 2 only enriches <header> action buttons; kanban deferred to Phase 7
- [Phase 05-02]: odoo-test-gen Phase 5 scope is computed/constraint/onchange only; CRUD + access rights deferred to Phase 6
- [Phase 06-01]: Use company_ids OCA shorthand (not user.company_ids.ids) in domain_force for Odoo 17.0 multi-company record rules
- [Phase 06-01]: Enrich model dicts with has_company_field before passing enriched_models to record_rules template context
- [Phase 06-01]: workflow_states key added in 06-01 (not 06-02) to consolidate all renderer.py changes into one plan
- [Phase 06-01]: _compute_manifest_data() extended with has_company_modules param (default False for backward compatibility)
- [Phase 06-02]: odoo-security-gen is standalone only — security is deterministic via Jinja2, not added to generate.md pipeline
- [Phase 06-02]: Workflow transition tests guarded by state_field not None AND workflow_states|length >= 2
- [Phase 06-02]: Access rights tests use groups_id [(6, 0, [...])] to SET group list (not additive (4, id) form)
- [Phase 06-02]: odoo-test-gen now rewrites ENTIRE test file (not appends) with all 7 Phase 6 test categories
- [Phase 07-01]: Static i18n extraction using ast + xml.etree.ElementTree (no new dependencies, no live Odoo server)
- [Phase 07-01]: ElementTree line numbers unreliable -- use 0 for all XML entries in POT source references
- [Phase 07-01]: Always generate POT header even when no translatable strings found (Odoo expects file to exist)
- [Phase 07-01]: Known gap accepted: Python field string= auto-translations not extracted (requires Odoo runtime, deferred to Phase 9)
- [Phase 07-02]: REVW-05 handled by existing GSD auto_advance config -- no new code, noted in workflow
- [Phase 07-02]: Checkpoints written as prose markdown sections for agent consumption (not PLAN.md XML)
- [Phase 07-02]: Max 3 retry limit per checkpoint with graceful escalation message
- [Phase 07-02]: i18n extraction (Step 3.5) is non-blocking -- failure does not prevent commit
- [Phase 07-03]: Keyword matching for Docker pattern identification (simple, sufficient for 4 patterns)
- [Phase 07-03]: Regex-based file rewriting for pylint fixes (read -> transform -> write back, immutable)
- [Phase 07-03]: Step 3.6 validation is informational, does not block commit (QUAL-09, QUAL-10)
- [Phase 08-01]: ast.literal_eval for manifest parsing -- safe against malicious manifests, never uses eval()
- [Phase 08-01]: get_github_token is public API (no underscore) -- exported from search/__init__.py for CLI and external use
- [Phase 08-01]: Lazy imports for chromadb and github -- CLI loads without search dependencies installed
- [Phase 08-01]: CPU-only torch via uv index config -- avoids pulling full CUDA toolkit
- [Phase 08-02]: Cosine distance to similarity: 1.0 - (distance / 2.0) for 0.0-1.0 range
- [Phase 08-02]: GitHub fallback results get fixed relevance_score=0.5 (unranked)
- [Phase 08-02]: Auto-fallback to GitHub when OCA returns 0 results, even without --github flag
- [Phase 08-02]: Refined spec overwrites original spec.json path (REFN-03 source of truth for all downstream)
- [Phase 08-02]: Gap analysis runs only on selected result, not all 5 upfront (Decision A)
- [Phase 08-02]: Follow-up queries independently re-query ChromaDB, no session state (Decision A)
- [Phase 08-03]: subprocess.run(check=True) for git commands -- CalledProcessError propagates naturally (not wrapped in RuntimeError)
- [Phase 08-03]: AST-based field extraction scans for fields.X() call pattern with _ODOO_FIELD_TYPES frozenset
- [Phase 08-03]: XML ElementTree for view type detection -- looks for form/tree/search/kanban tags in arch content
- [Phase 08-03]: Security group extraction from res.groups records AND ir.module.category records with 'group' in ID
- [Phase 08-03]: Companion module naming: {original}_ext suffix per Decision C
- [Phase 08-03]: Refined spec saved to both {module}_ext/spec.json AND overwrites original (REFN-03)
- [Phase 09-02]: FileSystemLoader([version_dir, shared_dir]) for template fallback -- version-specific overrides shared
- [Phase 09-02]: create_renderer() backward compat: detects base templates dir, falls back to versioned 17.0 loading
- [Phase 09-02]: Separate template files per version (no conditional version logic inside templates)
- [Phase 09-01]: JSON data file for Enterprise registry (not hardcoded Python)
- [Phase 09-01]: Module-level caching for registry to avoid repeated file I/O
- [Phase 09-01]: community_alternative as nullable object (null when no OCA equivalent)

### Pending Todos

None yet.

### Blockers/Concerns

- gh CLI not authenticated -- needed for Phase 8 (GitHub API search). Not blocking until then.
- sentence-transformers pulls PyTorch (~2GB) -- plan CPU-only install strategy for Phase 8.
- GSD must be installed as prerequisite -- document in setup instructions.

## Session Continuity

Last session: 2026-03-03
Stopped at: Completed 09-02-PLAN.md (versioned templates + renderer). 243 tests pass. Ready for 09-03.
Resume file: No active checkpoint -- continue with 09-03
