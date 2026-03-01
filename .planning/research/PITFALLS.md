# Pitfalls Research

**Domain:** Multi-agent AI system for automated Odoo 17.0 module development
**Researched:** 2026-03-01
**Confidence:** MEDIUM-HIGH (multi-source verified across domains; some Odoo-AI-specific claims from single sources flagged)

## Critical Pitfalls

### Pitfall 1: Odoo Version Confusion in Generated Code

**What goes wrong:**
AI agents mix APIs, ORM methods, view syntaxes, and template patterns across Odoo versions. An agent trained on general Python/Odoo data will conflate v12 `_columns` style with v17 `fields.Char()`, use deprecated `@api.one`/`@api.multi` decorators (removed since v13), reference `odoo.http.JsonRequest` patterns that changed in v16+, or generate QWeb templates using v15 syntax in a v17 module. The generated module installs but behaves incorrectly, or worse, passes basic tests but fails in production edge cases.

**Why it happens:**
LLM training data contains Odoo code from all versions (8-18). Odoo's API has changed dramatically across versions -- the ORM was rewritten between v8 and v10, controllers changed in v16, and QWeb evolved continuously. Without explicit version pinning in every prompt and validation step, agents default to the most common patterns in training data, which skew toward older versions with more Stack Overflow answers.

**How to avoid:**
- Pin `--valid-odoo-versions=17.0` in every pylint-odoo check
- Include Odoo 17.0 API reference snippets in every agent's system prompt as authoritative examples
- Build a version-specific code linter that runs before any human review checkpoint
- Create a "version canary" test: import patterns and decorator usage that would fail if wrong-version code is present
- Use Odoo 17.0 official docs as RAG context, not generic training data

**Warning signs:**
- `@api.one` or `@api.multi` decorators in generated code
- `_columns` or `_defaults` dictionary patterns
- `cr.execute()` without `self.env.cr`
- `openerp` imports instead of `odoo` imports
- XML `<openerp>` tags instead of `<odoo>` tags

**Phase to address:**
Phase 1 (Agent Foundation) -- version-awareness must be baked into agent prompts and validation from day one. A late fix means rewriting all prompt templates and re-validating every generated module.

---

### Pitfall 2: The "God Agent" Anti-Pattern

**What goes wrong:**
A single orchestrator agent tries to handle too many responsibilities -- analyzing user intent, searching modules, generating models, writing views, creating security files, running tests, and fixing failures. This dilutes the model's attention, leads to hallucinations, and produces incoherent modules where the security ACLs don't match the models, views reference non-existent fields, or test files import classes that were renamed mid-generation.

**Why it happens:**
It is simpler to build one powerful agent than to design inter-agent communication protocols. Early prototypes that "just work" with a single agent create the illusion that the approach scales. Research shows 41-86.7% of multi-agent systems fail in production, with 79% of failures originating from specification and coordination issues, not technical bugs ([source](https://arxiv.org/html/2503.13657v1)). But a monolithic agent fails worse -- it just fails silently with subtly wrong output instead of loudly with coordination errors.

**How to avoid:**
- Design agents with single responsibilities: one for models, one for views/templates, one for security, one for tests, one for business logic
- Use a lightweight orchestrator that routes tasks but does NOT generate code itself
- Define strict contracts between agents: the models agent outputs a schema, the views agent consumes that schema
- Each agent gets only the context it needs (not the entire module), reducing "lost in the middle" token waste

**Warning signs:**
- One agent's prompt exceeds 8,000 tokens of instructions
- A single agent invocation takes more than 3 minutes
- Generated output quality degrades as module complexity increases
- Agent produces working simple modules but fails on 5+ model modules

**Phase to address:**
Phase 2 (Agent Design) -- agent boundaries and communication protocols must be designed before any code generation logic is built. Retrofitting single-responsibility onto a monolithic agent requires a full rewrite.

---

### Pitfall 3: Fork-and-Extend Produces Unmaintainable Frankenstein Modules

**What goes wrong:**
The system finds a partially-matching OCA module, forks it, and AI agents heavily modify it to fit the user's needs. The result is a module that has the forked module's architecture but violates it everywhere -- naming conventions clash, the original module's test suite breaks, dependencies become tangled, and the module cannot receive upstream security patches. When the OCA module is updated, merging becomes impossible because the AI rewrote core methods without preserving the original structure.

**Why it happens:**
AI agents treat forked code as a canvas to paint on rather than a structure to respect. They don't understand architectural intent -- why the original author chose certain patterns, what the test coverage protects, or how the module fits into the broader OCA ecosystem. Research on divergent forks shows merge conflicts increase exponentially with the number of structural changes, and AI agents make many structural changes because they optimize for "working code" not "mergeable code" ([source](https://dl.acm.org/doi/10.1145/3377813.3381362)).

**How to avoid:**
- Set a "modification threshold": if the AI would change more than 40% of the forked module's code, build from scratch instead
- Preserve the original module's class hierarchy, method signatures, and naming conventions
- Use Odoo's inheritance mechanisms (`_inherit`, `_inherits`) to extend rather than modify -- never rewrite original methods when you can override them
- Maintain the fork relationship: track the upstream commit hash, run upstream tests on the extended module
- Create a "fork health" metric that measures divergence from upstream

**Warning signs:**
- AI agent rewrites `create()`, `write()`, or `unlink()` methods in the base class instead of extending via inheritance
- Forked module's original test suite fails after AI modifications
- More than 30% of original files are heavily modified (not just extended)
- Dependencies list changes significantly from the original manifest

**Phase to address:**
Phase 3 (Module Search and Reuse) -- the fork-vs-build decision logic and the extend-via-inheritance strategy must be designed into the search-and-reuse pipeline. This cannot be bolted on after the code generation agents are built.

---

### Pitfall 4: Security Files as an Afterthought

**What goes wrong:**
The AI generates models, views, and business logic, then tacks on security (ACLs, record rules, group hierarchy) at the end. The result: `ir.model.access.csv` entries don't match actual model names (typos in `model_id:id` references), record rules reference fields that don't exist, group hierarchy doesn't match the intended access pattern, and users can see/modify data they shouldn't. This is the most common "looks done but isn't" failure in Odoo modules.

**Why it happens:**
Security in Odoo is spread across multiple interconnected files: `ir.model.access.csv`, XML record rules, group definitions in XML data files, and sometimes Python `_check_*` methods. AI agents generating these files need complete knowledge of the model structure, field names, and business rules. If security is generated after models (as a separate step), any model name changes, field renames, or late additions create mismatches. Odoo's security errors are also notoriously silent -- a missing ACL just shows "Access Denied" with no pointer to which model or rule failed.

**How to avoid:**
- Generate security IN PARALLEL with models, not after them. When a model is defined, its ACL entry should be generated in the same step
- Validate security files by cross-referencing: every model in `__manifest__.py` must have at least one ACL entry, every field in record rules must exist in the model
- Write a security validation script that catches mismatches before Docker testing (faster feedback)
- Include security groups in the user's initial requirement gathering -- "who can see this?" must be answered before generation starts

**Warning signs:**
- `ir.model.access.csv` has fewer rows than the number of models in the module
- Record rules reference `object.field_name` where `field_name` doesn't exist
- No group hierarchy (flat groups instead of parent-child relationships)
- Module installs fine but users immediately see "Access Denied" errors

**Phase to address:**
Phase 2 (Agent Design) -- the security agent and model agent must share context or be the same agent. Phase 4 (Validation) must include an automated security cross-reference check.

---

### Pitfall 5: Docker Validation Gives False Confidence

**What goes wrong:**
Module passes Docker-based installation and test execution, but the Docker environment doesn't match real-world conditions. Tests pass because the database is empty (no existing data conflicts), the user running tests is the admin (bypassing ACLs), no other modules are installed (missing cross-module conflicts), and the Odoo instance uses the default configuration (no workers, no cron, no email). The module ships, and fails in the customer's environment with existing data, multi-user access, and module conflicts.

**Why it happens:**
Docker environments are designed for speed and isolation, which is the opposite of production realism. Odoo's module system has deep cross-module interactions -- a module that works alone may break when `sale`, `purchase`, or `account` modules are installed. Additionally, Odoo's test framework runs tests as the admin user by default, which means ACL and record rule bugs are invisible ([source](https://www.odoo.com/documentation/17.0/developer/reference/backend/security.html)).

**How to avoid:**
- Install a realistic set of base modules (sale, purchase, account, hr) in the Docker environment, not just `base`
- Run tests as a non-admin user to validate ACLs actually work
- Seed the database with demo data (Odoo provides `--load-language` and demo data flags)
- Add a "conflict detection" step: install the generated module alongside the 20 most common OCA modules and check for import errors, XML ID conflicts, or field overwrites
- Test with `--workers=2` to catch concurrency bugs in computed fields

**Warning signs:**
- All tests pass but only test happy paths
- Tests use `self.env.ref('base.user_admin')` instead of creating test users with restricted access
- Docker compose file only installs the module under test with no other modules
- No demo data loading in test configuration
- Test suite completes in under 5 seconds for a complex module (suspiciously fast)

**Phase to address:**
Phase 4 (Docker Validation) -- the Docker test environment design is a first-class deliverable, not infrastructure glue. Treat it as a product component with its own requirements.

---

### Pitfall 6: Context Window Overflow Degrades Output Quality Silently

**What goes wrong:**
As module complexity grows (more models, more views, more business logic), the accumulated context passed to AI agents exceeds their effective processing capacity. The agent doesn't error out -- it silently degrades. Field names become inconsistent across files, imports reference wrong modules, computed field dependencies are incomplete, and view XML references non-existent fields. The "lost in the middle" phenomenon means information in the middle of a large context is effectively ignored.

**Why it happens:**
Even with 200K token windows (Claude) or 128K (GPT-4o), effective attention degrades well before the limit. Odoo modules are particularly context-hungry: a module with 10 models generates ~2,000 lines of Python, ~3,000 lines of XML views, ~500 lines of security files, plus tests. Passing the entire module as context to an agent exceeds what any current model can reliably process while maintaining cross-file consistency ([source](https://factory.ai/news/context-window-problem)).

**How to avoid:**
- Never pass the entire module as context to a single agent call. Instead, pass the module schema (model names, field names, types) as a compact reference
- Use a "module manifest" data structure that agents can reference -- field names, types, relations -- without seeing full code
- Implement periodic context summarization: after each generation step, summarize what was built before moving to the next step
- For modules with 5+ models, split generation into model groups and validate cross-references separately
- Monitor token usage per agent call; flag calls exceeding 50% of context window

**Warning signs:**
- Field names are inconsistent between Python models and XML views (e.g., `partner_id` in model but `customer_id` in view)
- Import statements reference modules that don't exist in the generated code
- Computed fields depend on fields that were renamed or removed in a later generation step
- Agent output quality drops noticeably between 3-model and 8-model modules

**Phase to address:**
Phase 2 (Agent Design) -- context management strategy must be designed as part of the agent architecture. Phase 5 (Complex Modules) will stress-test this with larger modules.

---

### Pitfall 7: GitHub/OCA Search Returns Noise, Not Signal

**What goes wrong:**
Semantic search for existing modules returns hundreds of results with high apparent relevance but low actual utility. The system picks a module based on name/description similarity, but the module targets a different Odoo version, is abandoned (no updates in 2+ years), has no tests, fails OCA quality checks, or solves a subtly different business problem. The AI then wastes time trying to adapt an unsuitable base module, producing worse results than building from scratch.

**Why it happens:**
GitHub's search API has severe limitations: code search is limited to 10 requests/minute, results capped at 1,000, only default branches are searched, and semantic understanding is limited to keyword matching. OCA repositories use standardized but often vague module descriptions. Module names like `hr_leave_custom` could mean anything. Embedding-based semantic search helps with intent matching but cannot assess code quality, version compatibility, or maintenance status ([source](https://docs.github.com/en/rest/search/search)).

**How to avoid:**
- Filter results by Odoo version FIRST (check `__manifest__.py` for version compatibility) before ranking by relevance
- Check maintenance signals: last commit date, open issues count, CI status, number of contributors
- Prefer OCA-hosted modules (quality-guaranteed) over random GitHub repos
- Set a minimum quality threshold: module must have tests, must pass pylint-odoo, must have been updated within 18 months
- Cache and index OCA module manifests locally rather than relying on GitHub API per-search
- Build a curated index of the ~200 most commonly useful OCA modules for Odoo 17.0

**Warning signs:**
- Search returns modules for Odoo 12 or 14 as top results
- Top result has no commits in 2+ years
- Module description matches but actual functionality diverges significantly
- System spends more time adapting a forked module than building from scratch would take

**Phase to address:**
Phase 3 (Module Search and Reuse) -- search quality and filtering must be extensively tested with real-world queries before being integrated into the generation pipeline.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding Odoo version in agent prompts | Quick to get working | Every version bump requires updating every prompt template | Never -- use a shared config variable |
| Skipping i18n/translation wrapping | Code generates faster without `_()` wrappers | Fails OCA quality checks; unusable in multi-language environments | Never -- OCA compliance requires i18n |
| Using `sudo()` in generated business logic | Bypasses ACL issues during development | Massive security hole in production; bypasses all record rules | Never in generated modules -- only in system-level migration scripts |
| Single Docker image for all validation | Simpler infrastructure | Cannot test CE vs EE differences, cross-version compatibility | MVP only -- must add EE testing before release |
| Storing all agent state in memory | Fast prototyping of orchestrator | Cannot resume interrupted generation; loses work on crash | Early prototypes only -- add persistence by Phase 3 |
| Using `self.env.ref()` with hardcoded XML IDs in tests | Tests are easy to write | Tests break when installed alongside modules that override those records | Never -- create test-specific records |

## Integration Gotchas

Common mistakes when connecting to external services in this system.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GitHub API | Hitting 10 req/min code search limit, then failing silently | Cache results aggressively; pre-index OCA repos locally; implement exponential backoff with clear user feedback |
| Multiple LLM Providers (Claude, Codex, Gemini) | Each provider uses different auth headers (Bearer vs x-api-key vs x-goog-api-key), leading to key leakage or misconfiguration | Use an API gateway or unified client that handles auth per provider; never expose raw keys to agent code ([source](https://aembit.io/blog/securing-ai-agents-without-secrets/)) |
| Docker Engine API | Starting Odoo container and immediately running tests before DB is ready | Use PostgreSQL health checks in docker-compose; wait for Odoo to be fully initialized before test execution ([source](https://github.com/odoo/docker/issues/258)) |
| OCA Git Repositories | Cloning full OCA repos (~50+ repos, gigabytes of data) on every search | Clone once, store locally, pull updates on a schedule; search the local index, not live repos |
| pylint-odoo | Running pylint-odoo without `--valid-odoo-versions=17.0` | Always specify version; checks differ by version; wrong version flag produces false positives/negatives |

## Performance Traps

Patterns that work at small scale but fail as module complexity grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Passing full module source as agent context | Slow responses, inconsistent field names across files | Use structured schema references instead of raw code | Modules with 5+ models (~5,000+ lines total) |
| Sequential agent execution (model then view then security then test) | 10-15 minute generation time for simple modules | Parallelize independent steps (security + views can run concurrently after models) | Any module -- this is pure waste from day one |
| Docker cold-start per validation run | 30-60 second overhead per test cycle | Keep a warm Odoo container pool; reuse containers with database reset | Iterative fix cycles (agent generates, tests fail, agent fixes, tests again) |
| Loading all OCA module descriptions into embeddings | Embedding index grows to 100K+ entries; search is slow and noisy | Index only Odoo 17.0 modules; pre-filter by category; limit to maintained modules | More than 5,000 modules indexed |
| Synchronous LLM calls in the orchestrator | Orchestrator blocks waiting for each agent; total time = sum of all agents | Use async calls with structured dependency tracking | Any multi-agent workflow with 3+ agents |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| LLM API keys stored in CLI config files in plaintext | Key theft if machine is compromised; unauthorized API usage costing thousands | Use OS keychain (keyring library) or environment variables; never write keys to disk |
| Generated modules use `sudo()` to bypass access control | Deployed module gives all users admin-level data access | Lint for `sudo()` usage; require justification comment for any `sudo()` call; flag in review |
| Agent prompts include real customer data as examples | Training data leakage; privacy violation | Use synthetic/anonymized data in all prompts and examples |
| Docker test environment shares host network | Odoo test instance is accessible from the network during testing | Use isolated Docker networks; bind Odoo to localhost only |
| Generated modules don't sanitize user input in controllers | XSS/injection attacks on any web-facing Odoo endpoints | Include input validation checks in the security agent's responsibilities; test with malicious input patterns |
| OCA module forks may contain known vulnerabilities | Inherited security issues from outdated upstream code | Check CVE databases and OCA security advisories before forking; pin to latest patched version |

## UX Pitfalls

Common user experience mistakes in CLI tool design for this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No progress feedback during module generation (agents running silently) | User thinks tool is frozen; kills process after 30 seconds | Stream agent status updates: "Generating models... Generating views... Running tests..." ([source](https://evilmartians.com/chronicles/cli-ux-best-practices-3-patterns-for-improving-progress-displays)) |
| Requiring all module requirements upfront via flags | User must know exact Odoo field types, model names, and relationships before starting | Use interactive mode: ask questions progressively, offer defaults, show examples ([source](https://www.lucasfcosta.com/blog/ux-patterns-cli-tools)) |
| Cryptic error messages when generation fails | User has no idea what went wrong or how to fix it | Every error should include: what failed, why it likely failed, and suggested next steps |
| No way to resume interrupted generation | A network timeout at 80% completion means starting over | Save generation state at each checkpoint; allow `odoo-gen resume` command |
| Dumping 500+ lines of generated code to stdout | User is overwhelmed; cannot review effectively | Write to files, show summary of what was generated, offer `--diff` to review changes |
| No dry-run mode | User must commit to full generation to see what the tool will produce | Offer `odoo-gen plan` that shows what modules/files will be created without generating them |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Models:** Often missing `_description` attribute -- Odoo 17 logs warnings without it; verify every model class has `_description`
- [ ] **Security:** Often missing record rules -- having ACLs is not enough; verify record rules exist for multi-company and multi-user scenarios
- [ ] **Views:** Often missing `groups=` attributes on sensitive buttons/fields -- verify that admin-only actions are group-restricted in XML
- [ ] **Translations:** Often missing `_()` wrappers on user-facing strings -- verify all strings in Python are wrapped; all labels in XML use `string=` (not hardcoded text nodes)
- [ ] **Manifest:** Often missing `license`, `author`, `website`, `category` -- OCA requires all of these; verify against OCA manifest requirements
- [ ] **Tests:** Often testing only happy paths -- verify tests include edge cases: empty recordsets, access denied scenarios, concurrent writes
- [ ] **Data files:** Often missing `noupdate="1"` on initial data records -- verify that seed data won't be overwritten on module update
- [ ] **Controllers:** Often missing CSRF protection -- verify `csrf=True` on all HTTP POST routes (default in Odoo 17 but explicit is safer)
- [ ] **Dependencies:** Often over-specified -- listing modules in `depends` that aren't actually used; verify each dependency is truly needed (extra deps slow installation)
- [ ] **Computed fields:** Often missing `store=True` when needed for search/groupby, or using `store=True` with incomplete `@api.depends` -- verify stored computed fields have correct dependencies

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Version-mixed code in generated module | MEDIUM | Run pylint-odoo with `--valid-odoo-versions=17.0`; fix flagged issues; re-run agent with stricter version prompt |
| God agent producing inconsistent output | HIGH | Redesign agent boundaries; split into specialized agents; rewrite orchestrator; discard existing prompts |
| Unmaintainable forked module | HIGH | Assess divergence; if >40% changed, abandon fork and regenerate from scratch using original as inspiration only |
| Security files don't match models | LOW | Run cross-reference validation script; auto-generate missing ACL entries from model introspection |
| False-positive Docker validation | MEDIUM | Add realistic test environment (more modules, demo data, non-admin user); re-run all previously "passing" modules |
| Context overflow degradation | MEDIUM | Implement schema-based context passing; reduce per-agent context; add cross-file consistency checks |
| Search returning unsuitable modules | LOW | Tighten filters (version, maintenance status, quality score); expand curated index; add human confirmation step |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Version confusion | Phase 1 (Foundation) | pylint-odoo passes with `--valid-odoo-versions=17.0` on every generated module |
| God agent anti-pattern | Phase 2 (Agent Design) | No single agent prompt exceeds 6K tokens; each agent has a defined input/output contract |
| Frankenstein forks | Phase 3 (Search/Reuse) | Fork divergence metric stays below 40%; upstream test suite still passes |
| Security afterthought | Phase 2 (Agent Design) + Phase 4 (Validation) | Automated cross-reference check: every model has ACLs; every record rule references valid fields |
| False Docker confidence | Phase 4 (Validation) | Test environment includes 5+ common modules, demo data, non-admin test user |
| Context overflow | Phase 2 (Agent Design) | Consistent field names across files verified by automated cross-reference; modules with 10+ models generate correctly |
| Search noise | Phase 3 (Search/Reuse) | Top-3 search results are version-compatible and actively maintained; false positive rate below 30% |
| CLI UX failures | Phase 1 (Foundation) | Interactive mode works for naive users; progress feedback on every operation >2 seconds |
| API key exposure | Phase 1 (Foundation) | No API keys in config files, logs, or version control; keys loaded from environment or keychain only |
| Generated `sudo()` usage | Phase 4 (Validation) | Automated lint check flags all `sudo()` calls; zero `sudo()` in generated business logic without explicit justification |

## Sources

- [GitHub Blog: Multi-agent workflows often fail](https://github.blog/ai-and-ml/generative-ai/multi-agent-workflows-often-fail-heres-how-to-engineer-ones-that-dont/) -- MEDIUM confidence (verified patterns across multiple sources)
- [Why Multi-Agent LLM Systems Fail (research paper)](https://arxiv.org/html/2503.13657v1) -- HIGH confidence (peer-reviewed research with quantified failure rates)
- [Augment Code: Why Multi-Agent LLM Systems Fail](https://www.augmentcode.com/guides/why-multi-agent-llm-systems-fail-and-how-to-fix-them) -- MEDIUM confidence
- [Towards Data Science: 17x Error Trap of Bag of Agents](https://towardsdatascience.com/why-your-multi-agent-system-is-failing-escaping-the-17x-error-trap-of-the-bag-of-agents/) -- MEDIUM confidence
- [Odoo 17.0 Security Documentation](https://www.odoo.com/documentation/17.0/developer/reference/backend/security.html) -- HIGH confidence (official docs)
- [Odoo 17.0 Module Manifests](https://www.odoo.com/documentation/17.0/developer/reference/backend/module.html) -- HIGH confidence (official docs)
- [OCA pylint-odoo](https://github.com/OCA/pylint-odoo) -- HIGH confidence (official OCA tool)
- [GitHub REST API Rate Limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) -- HIGH confidence (official docs)
- [GitHub Search API Limits](https://docs.github.com/en/rest/search/search) -- HIGH confidence (official docs)
- [Factory.ai: Context Window Problem](https://factory.ai/news/context-window-problem) -- MEDIUM confidence
- [Odoo Docker PostgreSQL Init Issue](https://github.com/odoo/docker/issues/258) -- HIGH confidence (official repo issue)
- [Beyond Code Generation: AI in Odoo's SDLC - OXP 2025](https://oduist.com/blog/odoo-experience-2025-ai-summaries-2/305-beyond-code-generation-integrating-ai-into-odoo-s-development-lifecycle-lessons-learned-306) -- MEDIUM confidence (conference talk summary)
- [Securing AI Agents Without Secrets](https://aembit.io/blog/securing-ai-agents-without-secrets/) -- MEDIUM confidence
- [Evil Martians: CLI UX Best Practices](https://evilmartians.com/chronicles/cli-ux-best-practices-3-patterns-for-improving-progress-displays) -- HIGH confidence (well-established patterns)
- [Lucas Costa: UX Patterns for CLI Tools](https://www.lucasfcosta.com/blog/ux-patterns-cli-tools) -- HIGH confidence
- [Odoo 17 Computed Fields Documentation](https://www.odoo.com/documentation/17.0/developer/tutorials/getting_started/09_compute_onchange.html) -- HIGH confidence (official docs)
- [Fork Management Challenges (ICSE 2020 paper)](https://dl.acm.org/doi/10.1145/3377813.3381362) -- HIGH confidence (peer-reviewed)

---
*Pitfalls research for: Agentic Odoo Module Development Workflow*
*Researched: 2026-03-01*
