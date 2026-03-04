# Phase 11: Live Integration Testing & i18n - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Docker validation runs against real Odoo 17.0 containers and i18n extracts field `string=` translations. Specifically: `odoo-gen-utils validate <module> --docker` spins up a real Odoo 17.0 + PostgreSQL container, installs a module, and reports pass/fail. The i18n extractor handles `fields.Char(string="Label")` patterns in Python files.

This phase resolves DEBT-03 and DEBT-04. No new features, commands, or agents.

</domain>

<decisions>
## Implementation Decisions

### Docker Test Fixture: Generated via odoo-gen
- Use the odoo-gen pipeline to generate a real Odoo module as the test fixture
- This validates both the generation workflow AND the Docker validation in one pass
- The generated module should be a simple but real module (not a hand-crafted minimal stub)
- Store the generated fixture or generation spec in `tests/fixtures/` or equivalent
- Fixture must include: `__manifest__.py`, at least one model, at least one test class

### Docker Test Marker: @pytest.mark.docker
- New separate marker `@pytest.mark.docker` — independent from `@pytest.mark.e2e`
- Tests skip when Docker daemon is not running (check via `check_docker_available()`)
- Register marker in `[tool.pytest.ini_options]` alongside existing `e2e` and `e2e_slow`
- Docker availability and GitHub token are independent concerns — separate markers allow running each independently
- `pytest -m docker` for Docker tests only, `pytest -m "docker or e2e"` for all external-dependency tests

### i18n Field string= Extraction: All Values
- Extract ALL `fields.Char(string="Label")` patterns, not just unwrapped ones
- Odoo's framework translates field string= automatically — they all need .pot entries
- Pattern covers all field types: `fields.Char(string=...)`, `fields.Many2one(..., string=...)`, `fields.Text(string=...)`, `fields.Selection(..., string=...)`, etc.
- The AST walker in `extract_python_strings()` needs to be extended to find `Call` nodes where the function is `fields.*` and has a `string` keyword argument
- Existing `_("text")` extraction continues to work unchanged

### Claude's Discretion
- Exact AST node matching strategy for field definitions (attribute access vs name matching)
- Whether to create a conftest.py with shared Docker fixtures or keep fixtures inline
- Docker container startup timeout values
- How to handle the generated fixture module in CI (pre-generate and commit, or generate on-the-fly)
- Whether `extract_xml_strings` also needs field string= handling (XML `<field string="..."/>` is already covered)

</decisions>

<specifics>
## Specific Ideas

- The generated fixture module serves double duty: validates Docker AND provides a real module for i18n extraction testing
- Docker tests should tear down containers even on failure (existing `_teardown()` already handles this)
- The `validate` CLI command already has `--pylint-only` to skip Docker — no new flags needed
- Field string= extraction should handle both `string="Label"` and `string='Label'` (single/double quotes)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docker_runner.py` — `docker_install_module()`, `docker_run_tests()`, `check_docker_available()` all complete
- `docker-compose.yml` — Odoo 17 + PostgreSQL 16, health checks, module mount as read-only
- `i18n_extractor.py` — `extract_python_strings()` uses `ast.parse()`, extend the AST walk
- `log_parser.py` — `parse_install_log()`, `parse_test_log()` handle all Odoo log patterns
- `validation/types.py` — `InstallResult`, `TestResult`, `ValidationReport` frozen dataclasses
- `test_docker_runner.py` — existing mocked tests show the mock structure, new tests remove mocks
- `test_i18n_extractor.py` — existing tests for `_()` and XML extraction, add field string= tests

### Established Patterns
- Frozen dataclasses for all return types
- `@patch("odoo_gen_utils.validation.docker_runner._run_compose")` for mocking
- `tmp_path` fixture for temp module directories
- Click CLI with `@click.command()` decorators
- `e2e` and `e2e_slow` markers in pyproject.toml (Phase 10 precedent)

### Integration Points
- `docker_install_module(module_path)` receives a Path — fixture module must be a real directory
- `extract_python_strings(file_path)` receives a single file Path — walks AST of that file
- `generate_pot()` deduplicates by msgid — field string= entries merge with any matching `_()` entries
- `validate` CLI command calls `docker_install_module()` when `--pylint-only` is not set

</code_context>

<deferred>
## Deferred Ideas

- Odoo 18.0 Docker validation — out of scope per REQUIREMENTS.md, 17.0 first
- Docker-based test execution in CI pipeline — needs CI Docker-in-Docker setup
- Field `help=` parameter extraction (another translatable Odoo field attribute) — v1.2+

</deferred>

---

*Phase: 11-live-integration-testing-i18n*
*Context gathered: 2026-03-03*
