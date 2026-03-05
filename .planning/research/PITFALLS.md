# Pitfalls Research

**Domain:** Extending an Odoo module code generator with spec design patterns, template generation, and performance patterns
**Researched:** 2026-03-05
**Confidence:** HIGH (verified against Odoo 17.0/18.0 official docs, existing codebase analysis, and community sources)

---

## Critical Pitfalls

### Pitfall 1: Computed Field Dependency Chains That Create Circular Recomputation

**What goes wrong:**
When generating computed fields that depend on other computed fields across models, the spec can produce circular `@api.depends` chains. Example: `order.total_amount` depends on `order_line.subtotal`, and `order_line.subtotal` depends on `order.discount_rate`. Odoo does not raise an error at install time for cross-model circular depends -- it silently causes infinite recomputation loops at runtime, hanging the server or producing stack overflows. The current template (`model.py.j2`) generates `@api.depends()` decorators directly from the spec's `depends` list with no validation.

**Why it happens:**
The spec design treats each model's computed fields independently. There is no cross-model dependency graph analysis. A user specifies `depends: ["order_line_ids.subtotal"]` on one model and `depends: ["order_id.discount_rate"]` on another, each locally valid, but circularly dependent. The renderer produces syntactically correct Python that installs cleanly but fails at runtime.

**How to avoid:**
- Build a directed dependency graph from all computed fields across all models before rendering. Use a topological sort -- if the sort fails (cycle detected), reject the spec with a clear error message naming the cycle.
- Add a `validate_computed_chains(spec)` function that runs before `render_module()` and returns `Result[None]` with cycle details on failure.
- The dependency graph must resolve dotted paths: `order_line_ids.subtotal` means "field `subtotal` on the model that `order_line_ids` points to." This requires resolving `comodel_name` from the spec.

**Warning signs:**
- Spec has computed fields with `depends` referencing relational field paths (e.g., `line_ids.amount`)
- Two or more models have computed fields that reference each other
- Docker tests pass (because tests create records sequentially, never triggering the recomputation cascade) but production use hangs

**Phase to address:**
Phase 1 (Spec Design Extensions) -- dependency chain validation must be part of the spec validation pipeline, not a post-render check.

**Confidence:** HIGH -- verified via [Odoo computed field docs](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/08_compute_onchange.html) and [community reports of circular dependency errors](https://www.odoo.com/forum/help-1/circular-dependency-error-275043)

---

### Pitfall 2: Monetary Fields Without currency_id Cause AssertionError at Install

**What goes wrong:**
Odoo's `fields.Monetary` requires a companion `currency_id` Many2one field pointing to `res.currency`. If the model has no `currency_id` field, Odoo raises `AssertionError: Field %s with unknown currency_field None` during module installation. The current model template has no awareness of Monetary fields at all -- it renders them like any other field type. Auto-detection of "this model needs a currency_id" does not exist.

**Why it happens:**
Monetary fields look syntactically identical to Float fields in the spec (`type: Monetary`). Without explicit currency_id injection logic, the renderer produces a model with `fields.Monetary(string="Amount")` but no `currency_id` field. This always crashes at install, but the error message (`unknown currency_field None`) is cryptic and not caught by pylint-odoo.

**How to avoid:**
- Add monetary field auto-detection to `_build_model_context()`: if any field has `type == "Monetary"`, ensure the model has a `currency_id` field. If missing, inject one with `default=lambda self: self.env.company.currency_id`.
- The injected `currency_id` must also appear in the view (form and tree) to avoid `<field name="currency_id" invisible="1"/>` being missing.
- Add `currency_field` parameter support to the spec: allow overriding the default `currency_id` name (Odoo supports `currency_field="custom_currency_id"`).
- Add a Docker auto-fix pattern for this error in the error_patterns registry.

**Warning signs:**
- Spec contains any field with `type: Monetary` but no field named `currency_id` on the same model
- Docker validation fails with `AssertionError` containing `currency_field` -- this is the exact error
- `account` is not in the module's `depends` list when Monetary fields are used (common companion mistake)

**Phase to address:**
Phase 1 (Spec Design Extensions) -- monetary auto-detection must be implemented alongside the spec validation enhancements.

**Confidence:** HIGH -- verified via [Odoo forum](https://www.odoo.com/forum/help-1/assertionerror-field-s-with-unknown-currency-field-none-193965) and [Monetary field guide](https://fairchanceforcrm.com/odoo-monetary-field/)

---

### Pitfall 3: QWeb Report Templates That Crash wkhtmltopdf in Docker

**What goes wrong:**
QWeb report templates generate PDFs via wkhtmltopdf. Common template generation mistakes that produce valid XML but crash PDF rendering:
1. External CSS/font references that wkhtmltopdf cannot resolve (no internet in Docker container)
2. Large images without explicit width/height causing infinite layout loops
3. Missing `<div class="page">` wrapper -- wkhtmltopdf produces empty PDFs without it
4. Using `t-foreach` on an empty recordset without `t-if` guard -- produces blank pages
5. Report action XML referencing a model that does not match `t-foreach="docs"` context

**Why it happens:**
QWeb reports have two rendering layers: XML template (validated by Odoo's XML parser) and PDF conversion (validated only by actually printing). A template can be XML-valid, install cleanly, and even render in the web UI preview, but crash when generating a PDF. Docker tests do not exercise PDF generation by default -- they only verify installation and basic test execution.

**How to avoid:**
- Generate reports with `web.report_layout` as the outer template (provides standard header/footer/page structure).
- Always include `<div class="page">` as the content wrapper.
- Never reference external resources (CDN fonts, external images). Bundle all assets in `static/`.
- Add a report validation step that checks: (a) report action XML references an existing model, (b) template uses `t-foreach="docs"` correctly, (c) template includes `page` div.
- Include `web` in the `depends` list when generating reports (required for report assets).

**Warning signs:**
- Report template does not extend `web.external_layout` or `web.internal_layout`
- Template uses `<img src="http://...">` or `<link href="http://...">`
- Report action's `model` attribute does not match any model in the spec
- No `<div class="page">` element in the template

**Phase to address:**
Phase 2 (Template Generation) -- QWeb report templates must include structural validation before rendering.

**Confidence:** MEDIUM -- verified via [Odoo 17.0 QWeb Reports docs](https://www.odoo.com/documentation/17.0/developer/reference/backend/reports.html); wkhtmltopdf-specific failure modes based on community patterns

---

### Pitfall 4: HTTP Controllers Generated Without Proper Security (CSRF, Auth, ACL)

**What goes wrong:**
Generated HTTP controllers that expose REST endpoints create three security gaps:
1. **JSON routes have no CSRF protection by default** -- `type='json'` routes skip CSRF validation unless `csrf=True` is explicitly set. Developers (and code generators) assume CSRF is always on.
2. **Missing `auth` parameter defaults to `auth='user'`** which requires session login -- external API consumers get 403. Switching to `auth='none'` removes all authentication.
3. **No ACL check in controller logic** -- even with `auth='user'`, the controller can access any model method without respecting `ir.model.access` or record rules unless `sudo()` is avoided.

**Why it happens:**
The asymmetry between HTTP and JSON route CSRF defaults is not documented clearly. Controller generation templates typically focus on routing correctness, not security policy. The current codebase has no controller template at all, so this is a greenfield risk.

**How to avoid:**
- Default all generated routes to `auth='user', csrf=True` unless the spec explicitly marks an endpoint as public.
- Generate controller methods that use `self.env['model.name'].search()` (respects ACL) rather than `self.env['model.name'].sudo().search()`.
- Add `website` to depends if generating public-facing controllers (provides proper website auth framework).
- Include rate limiting guidance in generated controller comments.
- For API endpoints, generate token-based auth pattern using `auth='none'` + custom token validation, not bare `auth='none'`.

**Warning signs:**
- Controller template generates `type='json'` without explicit `csrf=True`
- Any route with `auth='none'` and no custom authentication logic
- Controller methods using `.sudo()` without explicit justification
- No tests generated for controller authentication/authorization

**Phase to address:**
Phase 2 (Template Generation) -- controller templates must include security by default.

**Confidence:** HIGH -- verified via [Odoo 18.0 Web Controllers docs](https://www.odoo.com/documentation/18.0/th/developer/reference/backend/http.html) and [GitHub issue #43151 on JSON CSRF](https://github.com/odoo/odoo/issues/43151)

---

### Pitfall 5: Adding New Renderer Stages Without Updating the Orchestration Pipeline

**What goes wrong:**
The current `render_module()` has 7 stage functions called in sequence. Adding new templates (reports, dashboards, controllers, cron jobs, import/export wizards) means adding new stages. Common mistakes when extending:
1. New stage added to the list but not reflected in `_compute_manifest_data()` -- generated files exist on disk but are not listed in `__manifest__.py`, so Odoo never loads them.
2. New stage renders files but `_build_module_context()` does not include the new context keys -- template crashes with `UndefinedError` (StrictUndefined is on, which is correct behavior).
3. New stage renders files but `_track_artifacts()` does not track them -- artifact state becomes incomplete.
4. New stage's `init_*.py.j2` template is missing or does not import the new Python files.
5. Manifest `data` vs `demo` file ordering -- new data files added after views cause "field not found" errors because views reference models/data not yet loaded.

**Why it happens:**
The renderer was designed for a fixed set of artifacts (models, views, security, wizards, tests, static). Each new artifact type requires updates to 4-5 coordination points: the stage list, manifest data computation, module context building, artifact tracking, and `__init__.py` generation. Missing any one of these produces a module that installs partially or not at all.

**How to avoid:**
- Create a checklist for "adding a new render stage" that covers all coordination points:
  1. New stage function (e.g., `render_reports()`)
  2. New template files (e.g., `report.xml.j2`, `report_template.xml.j2`)
  3. Update `_compute_manifest_data()` to include new files in correct load order
  4. Update `_build_module_context()` with new context keys (e.g., `reports`, `has_reports`)
  5. Update `_track_artifacts()` to track new artifact kinds
  6. Update `__init__.py` templates if new Python files are generated
  7. Add the stage to `render_module()`'s stage list
  8. Write tests for the new stage in isolation AND as part of golden path
- Consider a registry pattern: each stage registers itself with the files it produces and the manifest entries it needs. The orchestrator computes the manifest from the registry, not hardcoded lists.

**Warning signs:**
- Module installs but reports/cron/controllers are not visible in the UI (files on disk but not in manifest)
- `UndefinedError` from Jinja2 when rendering new templates (context key missing)
- Artifact state shows fewer items than files on disk
- `__init__.py` does not import a generated Python file

**Phase to address:**
Phase 2 (Template Generation) -- establish the extension pattern before adding the first new template type. Retrofitting is harder than designing upfront.

**Confidence:** HIGH -- derived directly from codebase analysis of `renderer.py` coordination points

---

### Pitfall 6: ir.cron Generation with doall=True Causing Server Overload on Restart

**What goes wrong:**
Generated `ir.cron` XML records with `doall="True"` cause all missed executions to fire simultaneously when the Odoo server restarts after downtime. If a cron job processes 1000 records per run and the server was down for 24 hours with an hourly schedule, 24 executions fire at once on startup, processing 24,000 records and potentially crashing the server or locking the database.

**Why it happens:**
`doall` is a non-obvious parameter. The natural assumption is "yes, I want all scheduled executions to run" -- it sounds like reliability. The danger is not apparent until the server has been down for a meaningful period. Template generators tend to default to "safe-sounding" options.

**How to avoid:**
- Default all generated cron jobs to `<field name="doall" eval="False"/>`. Document in a generated comment why this is the default.
- For cron jobs that process records, generate batch processing with `_commit_progress()` and `_cr.commit()` per batch, so interrupted crons resume from where they left off rather than reprocessing everything.
- Add `numbercall` with `-1` (infinite) as default, not a fixed count.
- Generate the cron with `active="True"` but include a comment about setting to False during development.

**Warning signs:**
- Generated cron XML has `doall` set to True or missing (defaults vary by Odoo version)
- Cron method processes all matching records without batch size limit
- No `_commit_progress()` call in generated cron method body
- Cron runs more frequently than every 4 hours without a documented reason

**Phase to address:**
Phase 2 (Template Generation) -- cron template must encode these defaults.

**Confidence:** HIGH -- verified via [Odoo Experience 2025 talk on cron best practices](https://www.odoo.com/event/odoo-experience-2025-6601/track/best-practices-to-design-odoo-crons-8754)

---

### Pitfall 7: Database Index Generation That Conflicts with Odoo's Built-in Indexes

**What goes wrong:**
Generating explicit `CREATE INDEX` statements or `index=True` on fields that Odoo already indexes automatically creates duplicate indexes. Odoo automatically indexes: all `Many2one` fields (foreign key), the `id` field (primary key), and fields used in `_rec_name`. Adding `index=True` to these fields doubles the index overhead without performance benefit. Worse, adding composite indexes via `_sql_constraints` or raw SQL in `init()` hooks can conflict with Odoo's ORM index management.

**Why it happens:**
Performance-conscious developers (and code generators) add indexes "just in case." Without knowledge of what Odoo already indexes, the generator produces redundant indexes. The Odoo ORM silently creates the duplicate index -- no warning, just wasted disk space and slower writes.

**How to avoid:**
- Build an "already indexed" knowledge set: `Many2one` fields (automatic FK index), `id` (PK), `_rec_name` fields (Odoo 17+ indexes these).
- Only generate `index=True` for fields that are: (a) used in `_order` but are not `id`, (b) frequently used in `search()` domain filters but are not relational fields, (c) `Char` or `Date`/`Datetime` fields used in range queries.
- Never generate raw SQL `CREATE INDEX` -- use Odoo's `index=True` parameter exclusively.
- Document which fields are auto-indexed in the generated model file as comments.

**Warning signs:**
- `index=True` on a Many2one field (already indexed by FK constraint)
- `index=True` on `id` or `name` when `name` is `_rec_name` (already indexed)
- Raw SQL CREATE INDEX in model `init()` method
- More than 3 custom indexes per model (over-indexing)

**Phase to address:**
Phase 3 (Performance Patterns) -- index generation must be aware of Odoo's automatic indexing behavior.

**Confidence:** MEDIUM -- based on Odoo ORM internals and [PostgreSQL optimization guide for Odoo](https://cloudpepper.io/blog/optimize-odoo-and-postgresql-performance-tuning-guide/)

---

### Pitfall 8: ormcache on Methods That Take Mutable or Context-Dependent Arguments

**What goes wrong:**
Generating `@tools.ormcache()` decorators on methods that receive the `self` recordset (which includes context) or mutable arguments produces stale cached results. The cache key is computed from positional arguments, and when a context parameter changes (e.g., different company, different language), the cached result from a previous context is returned. This causes data leakage between companies in multi-company setups and wrong translations.

**Why it happens:**
`ormcache` looks simple: "add decorator, method gets cached." But the caching mechanism uses positional argument hashing. If a method's behavior depends on `self.env.context`, `self.env.company`, or `self.env.user`, the cache must include those in its key. The template generator has no way to know which methods are context-dependent without analyzing the method body.

**How to avoid:**
- Only generate `ormcache` for methods that: (a) take explicit, immutable arguments (strings, ints, tuples), (b) do not access `self.env.context`, `self.env.company`, or `self.env.user`, (c) return deterministic results for the same arguments.
- For context-dependent caching, generate `@tools.ormcache_context(keys=('lang', 'company_id'))` instead.
- Always generate a corresponding `clear_caches()` call in the `write()` and `unlink()` methods of models whose data feeds cached methods.
- Never cache methods that touch `ir.config_parameter` (values change at runtime).

**Warning signs:**
- `ormcache` on a method that accesses `self.env.company` or `self.env.context` without `ormcache_context`
- No `clear_caches()` override in the model that owns the cached method
- Cached method returns different results for different users but cache serves same result to all

**Phase to address:**
Phase 3 (Performance Patterns) -- caching template must include cache invalidation logic by default.

**Confidence:** HIGH -- verified via [Odoo ormcache GitHub issue #35289](https://github.com/odoo/odoo/issues/35289) and [ORM Cache documentation](https://www.cybrosys.com/odoo/odoo-books/odoo-17-development/performance-optimisation/orm-cache/)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding manifest data file order in `_compute_manifest_data()` for each new template type | Quick to add new file types | Every new template type requires updating the hardcoded list; ordering bugs when files are added in wrong position | Never -- use a registry or computed ordering based on file type priorities |
| Generating TODO stubs in computed fields (current approach) | Templates render without errors | Generated modules have non-functional computed fields; Docker tests pass but business logic is missing | Only for MVP scaffold -- must be flagged clearly in generated code and validation report |
| Skipping report PDF validation in Docker tests | Tests run faster, fewer Docker dependencies (wkhtmltopdf) | Report templates can install but crash when printing; users discover issues in production | Only if report rendering is tested separately outside the main validation pipeline |
| Adding all new context keys to `_build_model_context()` as optional dict lookups | Backward compatibility with existing specs | Context dict grows unboundedly; template variables become unpredictable; hard to know what keys a template expects | First 2-3 template types; then refactor to typed dataclass |
| Using `spec.get("reports", [])` pattern for every new feature | No spec schema changes needed | Spec structure is undocumented and unpredictable; impossible to validate without a schema | Never -- define a spec schema (Pydantic or JSON Schema) before adding features |
| Generating import/export wizards with `sudo()` for convenience | Avoids ACL complexity in wizard logic | Security bypass; any user with wizard access can read/write all records | Never -- wizards must respect the current user's permissions |

---

## Integration Gotchas

Common mistakes when connecting new features to the existing renderer pipeline.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| New Jinja2 templates | Adding template to `templates/shared/` without testing both 17.0 and 18.0 renderer paths | Test with both `create_versioned_renderer("17.0")` and `create_versioned_renderer("18.0")`; version-specific templates go in version dirs |
| Manifest data ordering | Adding report XML files after view files | Reports require model and view definitions to exist first; add report data files after views but before menu |
| New spec keys | Adding keys to spec dict without updating golden path test fixtures | Update `_make_spec()` helper in tests; add keys to golden path spec; verify StrictUndefined does not break existing templates |
| Auto-fix for new patterns | Adding new auto-fix functions without wiring into `run_docker_fix_loop` dispatch | Register new fix pattern in `FIXABLE_DOCKER_PATTERNS` and implement handler in dispatch; write integration test proving fix loop catches the new pattern |
| Dashboard views (graph/pivot) | Using `<graph>` view type without `group_by` fields on the model | Graph views require at least one field suitable for grouping; generate `group_expand` on Selection/Many2one fields used in graph |
| Controller + test generation | Generating controller tests that use `self.url_open()` without proper test class | Controller tests must inherit `HttpCase`, not `TransactionCase`; different test infrastructure |
| Cron data files | Putting cron XML in `views/` directory | Cron definitions go in `data/` directory; they are data records, not views; manifest must list them in `data` section |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Generated `store=True` on all computed fields | Slow writes; every record save triggers recomputation cascade across related models | Only set `store=True` when the field is used in search domains, `_order`, or report aggregations; default to `store=False` | >1000 records with 3+ stored computed fields |
| Bulk import wizard using `create()` in a for loop | Import of 1000 records takes minutes; server timeout | Generate `create_multi` pattern: collect dicts, call `Model.create(vals_list)` once | >100 records per import |
| Missing `_order` on models shown in list views | Full table scan for every list view load; ORDER BY id is the default but not useful | Generate `_order` based on the most likely sort field (date fields, sequence, name) | >10,000 records in the model |
| Archival cron that searches all records without domain filter | Cron scans entire table every run; locks table during archival | Generate cron domain that filters only records eligible for archival (e.g., `[('write_date', '<', threshold), ('active', '=', True)]`) | >50,000 records |
| `related` fields creating deep join chains | Each dot in `related='partner_id.country_id.name'` adds a SQL JOIN; 4+ levels cause query plan explosion | Limit generated `related` fields to 2 levels max; for deeper chains, use a computed field with explicit SQL or caching | >3 levels of relation traversal |
| Index on low-cardinality fields | Index on Boolean or Selection fields with <5 values wastes space and slows writes; query planner ignores them | Only index fields with high cardinality (>100 distinct values) or used in exact-match lookups with selective conditions | Any scale -- indexes on Boolean fields never help |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Import wizard with `sudo()` bypasses record rules | Users can import records they should not see; data leakage across companies | Generate import logic without `sudo()`; use `self.env['model'].with_context(active_test=False).create()` which respects ACLs |
| Generated controllers with `auth='none'` for convenience | Anyone on the network can call the endpoint; data exfiltration | Default to `auth='user'`; for API endpoints, generate API key validation pattern |
| Report template accessing `sudo()` records | Report prints data the user does not have access to | Generate reports using `docs` context (already filtered by user access); avoid `sudo()` in report templates |
| Cron job running as admin without company scoping | Cron processes all companies' data; cross-company data corruption | Generate cron methods with `self.env.companies` scoping; iterate companies when processing multi-company data |
| Export wizard dumping all fields including `password` or `token` fields | Sensitive data exported to CSV/XLSX | Generate export field whitelist from spec; exclude fields with names matching `password`, `token`, `secret`, `key` |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Dashboard view generated with raw field names as labels | User sees `total_amount_untaxed` instead of "Subtotal" | Use field `string` attribute in graph/pivot measure labels; generate meaningful group-by labels |
| Report template with no page break logic for long lists | PDF prints a single continuous page; content overflows | Generate `<div style="page-break-inside: avoid">` for table rows; add page breaks between logical sections |
| Import wizard with no error feedback | User uploads CSV, gets silent failure or cryptic Python traceback | Generate import with row-by-row validation; collect errors; show summary of success/failure counts |
| Cron job with no user-visible status | Users do not know if the scheduled action ran or what it did | Generate a `last_run_status` field or use `ir.logging` to record execution results |
| Graph view with too many measures | Dashboard is cluttered and slow to render | Limit generated graph views to 3-4 measures max; use pivot view for detailed analysis |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Monetary fields:** Often missing `currency_id` companion field -- verify every model with a Monetary field has a Many2one to `res.currency`
- [ ] **QWeb reports:** Often missing `web.external_layout` wrapper -- verify report template extends a standard layout, not standalone XML
- [ ] **Controllers:** Often missing CSRF on JSON routes -- verify all `type='json'` routes have explicit `csrf=True` if they modify data
- [ ] **Cron jobs:** Often missing `doall=False` -- verify generated cron XML defaults to not replaying missed executions
- [ ] **Import wizards:** Often missing file type validation -- verify wizard checks file extension and content type before processing
- [ ] **Dashboard views:** Often missing graph `type` attribute -- verify `<graph type="bar">` (or line/pie) is explicitly set, not defaulting
- [ ] **Computed chains:** Often missing cycle detection -- verify no circular `@api.depends` paths exist across all models in the spec
- [ ] **Stored computed fields:** Often missing recomputation trigger -- verify `store=True` fields have all their `depends` paths actually traversable
- [ ] **Manifest file ordering:** Often missing new file types -- verify every generated file appears in `__manifest__.py` `data` or `demo` list
- [ ] **Index generation:** Often redundant on Many2one fields -- verify `index=True` is not set on fields Odoo already indexes automatically
- [ ] **Archival cron:** Often missing `active` field on the model -- verify the model has `active = fields.Boolean(default=True)` if archival is configured
- [ ] **Export wizard:** Often missing field filtering -- verify exported fields do not include sensitive/internal fields

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Circular computed dependency chain | LOW | Identify the cycle via dependency graph analysis; break the cycle by converting one computed field to an onchange or removing the circular depend; re-render the affected models |
| Missing currency_id on Monetary field | LOW | Add currency_id field to spec; add auto-fix pattern to detect `AssertionError: unknown currency_field` and inject the field; re-render model and views |
| Report template crashes wkhtmltopdf | MEDIUM | Cannot auto-fix wkhtmltopdf issues mechanically; requires manual inspection of report template; add structural validation to prevent recurrence |
| Controller security gap (auth='none') | LOW | Add auto-fix that scans generated controller files for `auth='none'` or missing `csrf` and flags them; update template to generate secure defaults |
| Manifest missing new files | LOW | Add a post-render validation that compares files on disk with manifest entries; auto-fix by regenerating manifest from actual file list |
| doall=True on heavy cron | LOW | Update generated cron XML; set doall to False; add batch processing to cron method body |
| Duplicate indexes | LOW | Remove `index=True` from fields that Odoo auto-indexes; no data migration needed |
| ormcache without invalidation | MEDIUM | Add `clear_caches()` override; requires understanding which write operations affect cached data; test cache invalidation explicitly |
| Renderer pipeline not tracking new artifacts | LOW | Update `_track_artifacts()` to include new artifact kinds; add integration test verifying artifact count matches generated file count |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Circular computed dependency chains | Phase 1: Spec Design Extensions | `validate_computed_chains()` returns error for specs with cycles; unit tests for cycle detection |
| Missing currency_id for Monetary fields | Phase 1: Spec Design Extensions | Spec with Monetary field but no currency_id is rejected or auto-corrected; Docker test confirms install |
| Relationship pattern validation (through-models, self-ref) | Phase 1: Spec Design Extensions | Spec validator checks comodel_name references resolve to models in spec or Odoo base |
| Constraint cross-model validation | Phase 1: Spec Design Extensions | Cross-model SQL constraints are rejected (Odoo does not support them); Python constraints generated instead |
| QWeb report structural validation | Phase 2: Template Generation (Reports) | Report template passes XML validation AND has required structure (page div, external layout) |
| Controller security defaults | Phase 2: Template Generation (Controllers) | All generated routes have explicit auth and csrf; no `sudo()` without comment |
| Cron doall/batch defaults | Phase 2: Template Generation (Cron) | Generated cron XML has doall=False; method body uses batch processing with commit |
| Import/export security | Phase 2: Template Generation (Import/Export) | No `sudo()` in import wizard; export excludes sensitive fields |
| Dashboard view quality | Phase 2: Template Generation (Dashboards) | Graph/pivot views have explicit type, limited measures, proper labels |
| Renderer pipeline coordination | Phase 2: Template Generation (All) | Checklist/registry pattern prevents missed manifest entries; integration test verifies all files in manifest |
| Index generation awareness | Phase 3: Performance Patterns | No `index=True` on auto-indexed fields; only on spec-justified fields |
| ormcache generation safety | Phase 3: Performance Patterns | Cache only context-free methods; invalidation generated alongside cache |
| store=True selectivity | Phase 3: Performance Patterns | Computed fields default to store=False; store=True requires justification in spec |
| Bulk operation patterns | Phase 3: Performance Patterns | Import wizard uses create_multi; cron uses batch processing |
| Archival strategy completeness | Phase 3: Performance Patterns | Archival generates active field, domain filter, cron with batch processing |

---

## Sources

**Odoo Official Documentation:**
- [QWeb Reports - Odoo 17.0](https://www.odoo.com/documentation/17.0/developer/reference/backend/reports.html)
- [Web Controllers - Odoo 18.0](https://www.odoo.com/documentation/18.0/th/developer/reference/backend/http.html)
- [Computed Fields Tutorial - Odoo 19.0](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/08_compute_onchange.html)
- [ORM API - Odoo 19.0](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html)

**Community Sources:**
- [Circular Dependency Error - Odoo Forum](https://www.odoo.com/forum/help-1/circular-dependency-error-275043)
- [AssertionError: unknown currency_field - Odoo Forum](https://www.odoo.com/forum/help-1/assertionerror-field-s-with-unknown-currency-field-none-193965)
- [Monetary Field Guide - FairChance](https://fairchanceforcrm.com/odoo-monetary-field/)
- [JSON Route CSRF Issue #43151 - GitHub](https://github.com/odoo/odoo/issues/43151)
- [ormcache Exception Issue #35289 - GitHub](https://github.com/odoo/odoo/issues/35289)
- [ORM Cache Book - Cybrosys](https://www.cybrosys.com/odoo/odoo-books/odoo-17-development/performance-optimisation/orm-cache/)
- [Best Practices for Odoo Crons - Odoo Experience 2025](https://www.odoo.com/event/odoo-experience-2025-6601/track/best-practices-to-design-odoo-crons-8754)
- [PostgreSQL Optimization for Odoo - Cloudpepper](https://cloudpepper.io/blog/optimize-odoo-and-postgresql-performance-tuning-guide/)

**Existing Codebase Analysis:**
- `renderer.py` -- 7 stage functions, `_build_model_context()`, `_compute_manifest_data()` coordination points
- `auto_fix.py` -- 5 fixable pylint codes, 5 Docker error patterns, AST-based fix pipeline
- `validation/types.py` -- Result[T] type, immutable dataclasses
- `model.py.j2` -- current computed field, onchange, constraint generation patterns

---
*Pitfalls research for: v3.1 Design Flaws & Feature Gaps (spec design, template generation, performance patterns)*
*Researched: 2026-03-05*
