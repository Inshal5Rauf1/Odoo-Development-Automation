# Phase 13: Golden Path Regression Testing - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

A single E2E test proves that the full pipeline (render templates with realistic spec, Docker install, run Odoo tests) produces a working module -- catching template regressions automatically.

Requirements: REGR-01, REGR-02 (2 of 10 v1.2 requirements).

</domain>

<decisions>
## Implementation Decisions

### Module Spec Complexity
- Comprehensive spec exercising ALL Phase 12 template fixes and major generation features
- Module: `hr_training` (or similar) with `depends=["base", "mail"]`
- Model 1 (complex): computed fields, constrained fields, state/workflow, mail.thread inheritance (exercises needs_api=True, inherit_list with mail)
- Model 2 (simple): plain Char/Integer fields only (exercises needs_api=False, inherit_list with mail but no api import)
- This ensures both code paths (with/without api import) are tested in Docker, and mail.thread inheritance works on both models
- All field `string=` attributes included for i18n compatibility

### Test Structure: Staged but Linked
- Single test file: `tests/test_golden_path.py` with `@pytest.mark.docker` marker
- Three test methods in dependency order:
  1. `test_golden_path_render` -- renders the spec via render_module(), asserts complete module directory exists with expected files
  2. `test_golden_path_docker_install` -- installs rendered module in Docker Odoo 17.0, asserts InstallResult.success=True
  3. `test_golden_path_docker_tests` -- runs rendered module's own Odoo tests in Docker, asserts all TestResult.passed=True
- Tests share the rendered module via a module-scoped fixture (render once, use for all three tests)
- If render fails, install and test are skipped. If install fails, test is skipped. This prevents cascading noise.

### Fixture: Generated On-the-Fly
- Module is generated via render_module() at test time, NOT pre-committed to fixtures/
- This catches template regressions -- if a template changes, the golden path test re-renders and catches breakage
- Uses tmp_path_factory (module scope) so Docker can access the rendered directory
- The golden path spec is defined as a Python dict inside the test file (not loaded from JSON/YAML)

### Test Assertions
- REGR-01 assertions (render + install):
  - All expected files exist (models/*.py, views/*.xml, security/*.csv, tests/*.py, __manifest__.py)
  - Docker install returns InstallResult(success=True) with no ImportError/registry errors in log
- REGR-02 assertions (Odoo test execution):
  - docker_run_tests() returns at least 1 TestResult
  - Every TestResult.passed is True (zero failures)
  - Test names are non-empty (tests actually ran, not skipped)

### Claude's Discretion
- Exact field definitions in the golden path spec
- Whether to add wizard to the spec (adds complexity but not required by success criteria)
- tmp_path vs tmp_path_factory for module-scoped fixture
- Whether to add render-time assertions for template output (Phase 12 tests already cover this)

</decisions>

<specifics>
## Specific Ideas

- The golden path test should be the "canary in the coal mine" -- if any future template change breaks Odoo installation, this test catches it
- Use the same `docker_install_module()` and `docker_run_tests()` functions from validation/ (proven in Phase 11)
- The generated module's own tests (from test_model.py.j2) must pass inside Odoo -- this validates that the test template produces valid Odoo test code
- Keep the spec realistic but not over-complex -- the goal is regression detection, not feature coverage

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `render_module(spec, template_dir, output_dir)` (renderer.py:327-611): Main rendering pipeline, returns list of created paths
- `get_template_dir()` (renderer.py:146-154): Returns bundled template directory path
- `docker_install_module(module_path)` (docker_runner.py:109-188): Returns InstallResult dataclass
- `docker_run_tests(module_path)` (docker_runner.py:191-262): Returns tuple of TestResult dataclasses
- `check_docker_available()` (docker_runner.py:22-39): Skip predicate for Docker tests
- `TestPhase12FullRenderIntegration` (test_renderer.py:1181-1290): Spec pattern for hr_training with mail + computed fields

### Established Patterns
- `@pytest.mark.docker` marker with `skipif(not check_docker_available())` (test_docker_integration.py)
- Frozen dataclasses for all validation results (InstallResult, TestResult)
- `collect_ignore_glob` in fixtures/conftest.py prevents pytest from collecting Odoo test files
- `norecursedirs = ["tests/fixtures/docker_test_module"]` in pyproject.toml

### Integration Points
- Golden path test calls render_module() then docker_install_module() then docker_run_tests() -- three existing functions chained
- Docker compose expects MODULE_PATH and MODULE_NAME environment variables
- `--test-tags={module_name}` ensures only target module tests run (not 938+ base tests)
- Test file must be in `tests/` directory under the module root with proper `__init__.py`

</code_context>

<deferred>
## Deferred Ideas

- Odoo 18.0 Docker golden path (17.0 first, 18.0 in v1.3+)
- Performance benchmarking of golden path test (track Docker install/test time across commits)
- Multiple golden path specs (wizard-heavy, multi-company, portal) for broader coverage
- CI integration for running golden path on every commit

</deferred>

---

*Phase: 13-golden-path-regression-testing*
*Context gathered: 2026-03-03*
