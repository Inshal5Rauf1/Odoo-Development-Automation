# Phase 11: Live Integration Testing & i18n - Research

**Researched:** 2026-03-03
**Domain:** Docker-based Odoo 17.0 live validation, pytest Docker integration patterns, AST-based field `string=` extraction for i18n .pot files
**Confidence:** HIGH

## Summary

Phase 11 resolves two remaining tech debt items: DEBT-03 (Docker validation against a live Odoo 17.0 daemon) and DEBT-04 (Python field `string=` i18n extraction). The existing codebase already has complete Docker lifecycle management (`docker_runner.py`) and i18n extraction (`i18n_extractor.py`) -- but all Docker tests mock `subprocess`, and `extract_python_strings()` only finds `_("text")` calls, missing `fields.Char(string="Label")` patterns.

The Docker infrastructure is solid: `docker-compose.yml` with health checks, `_teardown()` in `finally` blocks, `check_docker_available()` for graceful degradation. The Odoo 17 Docker image (`odoo:17`) is already pulled locally (1.85 GB). The `odoo.conf` mounts `/mnt/extra-addons` as the addons path. All that is needed is: (1) a real Odoo module fixture, (2) integration tests that skip mocking and call real Docker, and (3) an extension to the AST walker for `fields.*` keyword arguments.

**Primary recommendation:** Two independent workstreams: (A) Docker integration tests with a real Odoo module fixture and `@pytest.mark.docker` marker, and (B) extend `extract_python_strings()` AST walker to detect `fields.*(string="...")` patterns. Both can be planned as separate plans within one wave.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEBT-03 | Docker validation runs against a live Odoo 17.0 daemon -- module install and test execution verified with real containers (not just mocked subprocess) | Existing `docker_runner.py` has complete lifecycle management; needs a real module fixture and unmocked tests; Docker daemon confirmed available on dev machine; `odoo:17` image already pulled |
| DEBT-04 | Python field `string=` parameter translations are extracted by the i18n extractor into the .pot file | Existing `extract_python_strings()` only handles `_()` calls; AST pattern for `fields.*(string="...")` verified working (Name+Attribute+keyword match); Odoo auto-translates field `string=` attributes per official docs |
</phase_requirements>

## Standard Stack

### Core (Already in pyproject.toml)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.0 | Test framework | Already used for all 263 tests |
| click | >=8.0 | CLI framework | `validate` and `extract-i18n` commands |
| ast (stdlib) | Python 3.12 | AST parsing | Already used by `extract_python_strings()` |
| subprocess (stdlib) | Python 3.12 | Docker compose invocation | Already used by `docker_runner.py` |

### External Tools
| Tool | Purpose | How Used |
|------|---------|----------|
| Docker Engine | Container runtime | Runs Odoo 17 + PostgreSQL 16 containers for live validation |
| docker compose | Multi-container orchestration | Managed via `_run_compose()` in `docker_runner.py` |
| odoo:17 Docker image | Odoo 17.0 runtime | Official image, 1.85 GB, already pulled locally |
| postgres:16 Docker image | Database backend | Used by docker-compose.yml, tmpfs for ephemeral data |

### No New Dependencies Needed
Both workstreams use only existing libraries and tools. No new pip packages, no pytest plugins, no testcontainers library. The existing `_run_compose()` / `_teardown()` / `check_docker_available()` functions are sufficient for Docker integration tests. The stdlib `ast` module is sufficient for field `string=` extraction.

**Installation:**
```bash
cd python && uv venv && uv pip install -e ".[test]"
```

## Architecture Patterns

### Existing Docker Lifecycle (DO NOT CHANGE)

```python
# Source: python/src/odoo_gen_utils/validation/docker_runner.py
def docker_install_module(module_path: Path, compose_file: Path | None = None, timeout: int = 300) -> InstallResult:
    if not check_docker_available():
        return InstallResult(success=False, log_output="", error_message="Docker not available")
    try:
        _run_compose(compose_file, ["up", "-d", "--wait"], env, timeout=120)
        result = _run_compose(compose_file, ["exec", "-T", "odoo", "odoo", "-i", module_name, ...], env, timeout)
        success, error_msg = parse_install_log(combined_output)
        return InstallResult(success=success, log_output=combined_output, error_message=error_msg)
    except subprocess.TimeoutExpired:
        return InstallResult(success=False, ...)
    finally:
        _teardown(compose_file, env)
```

This is the correct pattern. Tests call `docker_install_module()` directly with a real module path and no mock patches. The `--wait` flag on `docker compose up` blocks until health checks pass. The `finally: _teardown()` guarantees cleanup.

### Existing Docker Compose Configuration (DO NOT CHANGE)

```yaml
# Source: docker/docker-compose.yml
services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo"]
      interval: 5s, timeout: 5s, retries: 5
    tmpfs: /var/lib/postgresql/data
  odoo:
    image: odoo:17
    depends_on:
      db: { condition: service_healthy }
    volumes:
      - ${MODULE_PATH:-.}:/mnt/extra-addons/${MODULE_NAME:-module}:ro
    configs:
      - source: odoo_conf
        target: /etc/odoo/odoo.conf
```

The `MODULE_PATH` and `MODULE_NAME` env vars are set by `docker_install_module()`. The module directory is mounted read-only at `/mnt/extra-addons/<module_name>`. PostgreSQL uses tmpfs so no persistent data survives teardown. The `odoo.conf` sets `addons_path = /mnt/extra-addons`.

### Existing i18n Extraction (EXTEND, DO NOT REWRITE)

```python
# Source: python/src/odoo_gen_utils/i18n_extractor.py
def extract_python_strings(file_path: Path) -> list[tuple[str, str, int]]:
    tree = ast.parse(source, filename=str(file_path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call): continue
        if not isinstance(node.func, ast.Name): continue  # <-- Only catches Name nodes
        if node.func.id != "_": continue                    # <-- Only catches _() calls
        # ... extracts first string argument
```

The current walker only matches `ast.Name` with `id="_"`. To also catch `fields.Char(string="Label")`, we need an additional check for `ast.Attribute` nodes where `node.func.value` is `ast.Name(id="fields")` and any keyword has `arg="string"`.

### AST Pattern for Field String Extraction (VERIFIED WORKING)

```python
# Tested and confirmed working on Python 3.12
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "fields":
        for kw in node.keywords:
            if kw.arg == "string" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                results.append((kw.value.value, str(file_path), node.lineno))
```

This pattern correctly extracts:
- `fields.Char(string="Order Name")` -- basic case
- `fields.Many2one('res.partner', string="Customer")` -- positional + keyword
- `fields.Selection([...], string="Status")` -- complex positional + keyword
- `fields.Float(string="Total Amount")` -- double quotes
- Ignores `fields.Boolean(help="No string attr")` -- no `string=` keyword
- Ignores `fields.Char(required=True)` -- no `string=` keyword

### Marker Pattern for Docker Tests (FOLLOWS Phase 10 PRECEDENT)

```python
# Phase 10 established @pytest.mark.e2e pattern in test_e2e_github.py:
pytestmark = pytest.mark.e2e
skip_no_token = pytest.mark.skipif(
    not os.environ.get("GITHUB_TOKEN"),
    reason="GITHUB_TOKEN not set -- skipping e2e GitHub tests",
)

# Phase 11 follows same pattern with @pytest.mark.docker:
pytestmark = pytest.mark.docker
skip_no_docker = pytest.mark.skipif(
    not _docker_available(),  # call check_docker_available() at import time
    reason="Docker daemon not available -- skipping Docker integration tests",
)
```

Register in `pyproject.toml`:
```toml
markers = [
    "e2e: ...",
    "e2e_slow: ...",
    "docker: Integration tests requiring Docker daemon. Skipped when Docker is unavailable.",
]
```

### Minimal Odoo Module Fixture (Test Fixture Structure)

A valid Odoo module that can be installed in Docker and has a test class:

```
tests/fixtures/docker_test_module/
  __init__.py           # import models
  __manifest__.py       # name, version, depends: [base]
  models/
    __init__.py         # import test_model
    test_model.py       # class with fields.Char(string="...") for i18n testing
  tests/
    __init__.py         # import test_basic
    test_basic.py       # TransactionCase with one assertion
```

The fixture serves double duty per the CONTEXT decisions:
1. Docker tests use it to verify `docker_install_module()` and `docker_run_tests()` work with a real Odoo container
2. i18n tests use it to verify field `string=` extraction produces correct .pot entries

### Anti-Patterns to Avoid

- **DO NOT add pytest-docker or testcontainers** -- the existing `docker_runner.py` already handles lifecycle; adding a plugin creates unnecessary coupling and a new dependency
- **DO NOT mock subprocess in Docker integration tests** -- the entire point is to validate against real Docker
- **DO NOT use session-scoped Docker fixtures** -- each test should spin up and tear down its own containers to avoid state leakage (the existing functions already do this via `_teardown()`)
- **DO NOT modify docker-compose.yml** -- the existing configuration works correctly with health checks, tmpfs, and read-only mounts
- **DO NOT test Odoo 18.0** -- explicitly out of scope per REQUIREMENTS.md
- **DO NOT change `check_docker_available()`** -- the existing `docker info` check is correct; tests use the same function to decide skip
- **DO NOT use `docker run` directly** -- always go through `docker compose` via `_run_compose()` for consistency with the production code path

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Docker lifecycle management | Custom container management | Existing `_run_compose()` + `_teardown()` | Already handles up/exec/down/cleanup |
| Health check waiting | Custom polling/sleep loops | `docker compose up --wait` flag | Compose waits for health checks natively |
| Container cleanup | Custom cleanup scripts | `docker compose down -v --remove-orphans` | Already in `_teardown()` with exception swallowing |
| AST walking framework | Custom visitor class | `ast.walk()` + isinstance checks | Same pattern already used for `_()` extraction |
| .pot file generation | Custom PO file library | Existing `generate_pot()` function | Already handles deduplication and header generation |
| Test module generation | odoo-gen pipeline | Hand-crafted minimal fixture | Pipeline is for production modules; test fixture needs to be small, fast, deterministic |

**Key insight on fixture:** The CONTEXT says "Use the odoo-gen pipeline to generate a real Odoo module as the test fixture." However, running the full pipeline (Jinja2 rendering + spec parsing) adds fragile coupling. A better approach: create a small, hand-crafted fixture module in `tests/fixtures/` that is known-good and deterministic. This fixture validates Docker without depending on the generation pipeline. If the generation pipeline breaks, Docker tests should still pass (they test Docker validation, not generation).

**Counterargument considered:** The CONTEXT explicitly says "a simple but real module (not a hand-crafted minimal stub)." This suggests the fixture should be more than a trivial stub -- it should have a real model, real fields with `string=` attributes, a real test class, and a valid manifest. The fixture can be hand-crafted but realistic. It does NOT need to be generated by the pipeline.

## Common Pitfalls

### Pitfall 1: Docker Image Pull on First Run Takes Minutes
**What goes wrong:** The `odoo:17` image is 1.85 GB. If not pre-pulled, `docker compose up` blocks for minutes on slow connections, causing test timeouts.
**Why it happens:** `docker compose up --wait` will pull images if not present, and the default 120s timeout may not be enough.
**How to avoid:** Document that `docker pull odoo:17` and `docker pull postgres:16` should be run before Docker tests. The `check_docker_available()` skip condition prevents tests from running when Docker is unavailable, but it doesn't check if images are pulled.
**Warning signs:** Test hangs for 5+ minutes then fails with timeout.

### Pitfall 2: Container Port Conflicts
**What goes wrong:** If another Odoo instance is running on the same Docker network, port or container name conflicts can prevent `docker compose up`.
**Why it happens:** The docker-compose.yml does not expose ports (no `ports:` section), but container names may conflict.
**How to avoid:** Use `docker compose down -v --remove-orphans` (already in `_teardown()`) before each test run. The `--remove-orphans` flag handles stale containers.
**Warning signs:** "Conflict. The container name ... is already in use" error.

### Pitfall 3: Odoo Module Install Timeout on Cold Start
**What goes wrong:** First module install after pulling a fresh image takes longer because Odoo initializes the database.
**Why it happens:** Odoo 17 creates the `test_db` database, installs the `base` module (~45s), then installs the custom module. Total can exceed 120s.
**How to avoid:** The existing `docker_install_module()` has a default 300s timeout, which is sufficient. For tests, do not reduce this timeout. The health check on the `db` service ensures PostgreSQL is ready before Odoo starts.
**Warning signs:** "Timeout after 120s" error during install.

### Pitfall 4: AST Pattern Misses Aliased Field Imports
**What goes wrong:** If a module does `from odoo.fields import Char` and then uses `Char(string="Label")` (without `fields.` prefix), the AST pattern won't match.
**Why it happens:** Our AST pattern checks `func.value.id == "fields"` which requires the `fields.Char(...)` call syntax.
**How to avoid:** The OCA coding standard and pylint-odoo enforce `from odoo import fields, models` style imports -- direct field type imports are non-standard. Support the standard pattern only; non-standard imports are already flagged by pylint-odoo.
**Warning signs:** Missing .pot entries for modules that use non-standard imports. Acceptable trade-off.

### Pitfall 5: Stale Docker Volumes Between Test Runs
**What goes wrong:** If a previous test left behind volumes (failed teardown), the next test may find a pre-existing database with stale data.
**Why it happens:** `_teardown()` catches all exceptions to avoid masking the original error, but a hard crash (SIGKILL, OOM) could skip teardown entirely.
**How to avoid:** `docker compose down -v` is already called with `-v` flag to remove volumes. If volumes persist, the fresh `docker compose up` will create a new database. PostgreSQL uses `tmpfs` for data, so no on-disk state survives container removal.
**Warning signs:** "Database already exists" errors or unexpected test data.

### Pitfall 6: Field `string=` Extraction Duplicating XML Entries
**What goes wrong:** If the same label appears in both `fields.Char(string="Name")` in Python and `<field name="name" string="Name"/>` in XML, the .pot file may have duplicate entries.
**Why it happens:** Both `extract_python_strings()` and `extract_xml_strings()` find the same string.
**How to avoid:** The existing `generate_pot()` already deduplicates by msgid, merging source references. This is the correct behavior -- each msgid appears once with all source locations listed. No additional deduplication needed.
**Warning signs:** None -- this is handled correctly by existing code.

## Code Examples

### Docker Integration Test (No Mocks)

```python
import pytest
from pathlib import Path
from odoo_gen_utils.validation.docker_runner import (
    check_docker_available,
    docker_install_module,
    docker_run_tests,
)

pytestmark = pytest.mark.docker

skip_no_docker = pytest.mark.skipif(
    not check_docker_available(),
    reason="Docker daemon not available -- skipping Docker integration tests",
)

FIXTURE_MODULE = Path(__file__).parent / "fixtures" / "docker_test_module"


@skip_no_docker
def test_docker_install_real_module():
    """Install a real Odoo module in a live Docker container."""
    result = docker_install_module(FIXTURE_MODULE)
    assert result.success is True, f"Install failed: {result.error_message}"
    assert result.log_output != "", "Expected non-empty log output"


@skip_no_docker
def test_docker_run_tests_real_module():
    """Run tests in a real Odoo module via Docker."""
    results = docker_run_tests(FIXTURE_MODULE)
    assert len(results) > 0, "Expected at least one test result"
    assert all(r.passed for r in results), f"Test failures: {[r for r in results if not r.passed]}"
```

### Field String= AST Extraction Extension

```python
def extract_python_strings(file_path: Path) -> list[tuple[str, str, int]]:
    source = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    results: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Existing: _("text") calls
        if isinstance(node.func, ast.Name) and node.func.id == "_":
            if node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    results.append((first_arg.value, str(file_path), node.lineno))

        # New: fields.*(string="text") keyword arguments
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "fields":
                for kw in node.keywords:
                    if kw.arg == "string" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        results.append((kw.value.value, str(file_path), node.lineno))

    return results
```

### Minimal Valid Odoo Module Fixture

```python
# tests/fixtures/docker_test_module/__manifest__.py
{
    "name": "Docker Test Module",
    "version": "17.0.1.0.0",
    "category": "Hidden",
    "summary": "Minimal module for Docker integration testing",
    "depends": ["base"],
    "data": [],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
```

```python
# tests/fixtures/docker_test_module/models/test_model.py
from odoo import fields, models

class DockerTestModel(models.Model):
    _name = "docker.test.model"
    _description = "Docker Test Model"

    name = fields.Char(string="Test Name", required=True)
    description = fields.Text(string="Test Description")
    is_active = fields.Boolean(string="Active", default=True)
```

```python
# tests/fixtures/docker_test_module/tests/test_basic.py
from odoo.tests.common import TransactionCase

class TestDockerTestModel(TransactionCase):
    def test_create_record(self):
        record = self.env["docker.test.model"].create({"name": "Test"})
        self.assertEqual(record.name, "Test")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mock all Docker subprocess calls | Test against live Docker daemon | Phase 11 (this phase) | Validates the entire pipeline end-to-end |
| Extract only `_()` calls for i18n | Also extract `fields.*(string="...")` patterns | Phase 11 (this phase) | Captures all translatable field labels per Odoo convention |
| No Docker test marker | `@pytest.mark.docker` separate from `@pytest.mark.e2e` | Phase 11 (this phase) | Independent skip logic for Docker vs GitHub tests |

**Odoo i18n conventions (from official Odoo 17 docs):**
- Field `string` and `help` attributes are **automatically translated** by the Odoo framework
- They **must appear in .pot files** for translators to provide translations
- In XML views, `string=` attributes are already extracted by `extract_xml_strings()` (existing)
- In Python model definitions, `fields.Char(string="...")` must be extracted statically (DEBT-04)
- The `_()` function is for imperative code translations; `fields.*(string="...")` is for declarative field metadata
- `_lt()` (LazyTranslate) is also used for module-level constants but is not in scope for this phase

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | `python/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd python && uv run pytest tests/ -x -q` |
| Full suite command | `cd python && uv run pytest tests/ -v` |
| Docker tests only | `cd python && uv run pytest tests/ -m docker -v` |
| Exclude Docker tests | `cd python && uv run pytest tests/ -m "not docker" -x -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBT-03a | `docker_install_module()` installs a real module in live Odoo 17 container | integration (docker) | `cd python && uv run pytest tests/test_docker_integration.py -m docker -v` | New file |
| DEBT-03b | `docker_run_tests()` runs real Odoo tests and reports pass/fail | integration (docker) | Same as above | New file |
| DEBT-03c | `validate` CLI with Docker runs full pipeline on real container | integration (docker) | Same as above | New file |
| DEBT-04a | `extract_python_strings()` finds `fields.Char(string="Label")` patterns | unit | `cd python && uv run pytest tests/test_i18n_extractor.py -v -k field` | Extend existing |
| DEBT-04b | `extract_python_strings()` finds all field types (Char, Many2one, Text, Selection, etc.) | unit | Same as above | Extend existing |
| DEBT-04c | `extract-i18n` CLI command includes field string= entries in .pot output | unit | `cd python && uv run pytest tests/test_i18n_extractor.py -v` | Extend existing |
| DEBT-04d | Existing `_()` extraction still works unchanged | regression | `cd python && uv run pytest tests/test_i18n_extractor.py -v` | Existing tests |
| Regression | All 263 existing tests continue to pass | regression | `cd python && uv run pytest tests/ -m "not docker" -x -q` | Existing tests |

### Sampling Rate
- **Per task commit:** `cd python && uv run pytest tests/ -m "not docker" -x -q` (existing 263 tests, < 30s)
- **Docker verification:** `cd python && uv run pytest tests/ -m docker -v` (runs only when Docker is available, ~2-5 min per test due to container startup)
- **Per wave merge:** `cd python && uv run pytest tests/ -v` (full suite including docker if available)
- **Phase gate:** Full suite green + at least one Docker test confirmed pass

### Wave 0 Gaps
- [ ] `tests/fixtures/docker_test_module/` -- minimal Odoo module with `__manifest__.py`, model with field `string=` attributes, and test class
- [ ] `tests/test_docker_integration.py` -- integration tests with `@pytest.mark.docker` marker (no mocks)
- [ ] `pyproject.toml` marker registration -- add `docker:` marker to `[tool.pytest.ini_options]`
- [ ] `extract_python_strings()` extension -- add `fields.*(string="...")` AST pattern to existing function
- [ ] `test_i18n_extractor.py` extension -- add unit tests for field `string=` extraction (Char, Many2one, Selection, Text, no-string)

## Effort Estimate

| Workstream | Tasks | Estimated Effort | Risk |
|------------|-------|-----------------|------|
| Docker integration tests (DEBT-03) | Create fixture module, write 2-3 integration tests, register marker | Medium (fixture creation + Docker wait time for testing) | Low -- existing `docker_runner.py` is complete |
| i18n field string= extraction (DEBT-04) | Extend AST walker, add 4-5 unit tests | Small (well-scoped AST change + test additions) | Very low -- AST pattern verified working |
| Regression verification | Run full suite, confirm 263+ tests pass | Trivial (automated) | Very low |

**Recommended wave structure:** Both workstreams are independent and can execute in parallel (Wave 1). Docker tests are slower due to container startup, but the implementation effort is similar.

## Open Questions

1. **How long does a single Docker install cycle take?**
   - What we know: `docker compose up --wait` waits for health checks (~5-10s for PostgreSQL); Odoo base module install takes ~30-60s; custom module install takes ~5-10s. Total estimated: 45-90s per test.
   - What's unclear: Actual cold-start time on this machine with the already-pulled image.
   - Recommendation: Time it during implementation. If > 120s, consider adjusting the test timeout.

2. **Should Docker tests run sequentially or in parallel?**
   - What we know: Each test calls `docker compose up` and `docker compose down`. Running them in parallel would create container name conflicts.
   - Recommendation: Run sequentially within the `test_docker_integration.py` file. The `-v` flag shows individual test progress. pytest's default sequential execution handles this correctly.

3. **Should the fixture module have security/access rules?**
   - What we know: The `docker.test.model` model needs at least `ir.model.access.csv` for the test to create records without AccessError.
   - Recommendation: Include a minimal `security/ir.model.access.csv` granting full access to `base.group_user`. This matches real module patterns and prevents false test failures.

## Sources

### Primary (HIGH confidence)
- [Python ast module documentation](https://docs.python.org/3/library/ast.html) -- AST node types, ast.walk(), ast.Attribute, ast.Call, keyword arguments
- [Odoo 17.0 Translating Modules documentation](https://www.odoo.com/documentation/17.0/developer/howtos/translations.html) -- field `string` and `help` automatically exported; `_()` for imperative code
- [Odoo 17.0 Docker Hub official image](https://hub.docker.com/_/odoo/) -- volume mounts, addons_path, configuration
- Existing codebase: `docker_runner.py`, `i18n_extractor.py`, `docker-compose.yml`, `odoo.conf`, `test_docker_runner.py`, `test_i18n_extractor.py` -- verified current implementation patterns

### Secondary (MEDIUM confidence)
- [pytest-docker PyPI page](https://pypi.org/project/pytest-docker/) -- reference for Docker test patterns (not using the plugin, but confirms approach)
- [Odoo 17 Python translations forum thread](https://www.odoo.com/forum/help-1/solved-odoo-17-exporting-python-translations-not-working-242088) -- confirms field `string=` should be in .pot files
- Phase 10 research and implementation -- established `@pytest.mark.e2e` pattern, skip decorators, pyproject.toml marker registration

### Tertiary (LOW confidence)
- Docker cold-start timing estimates (45-90s) -- based on general Odoo 17 Docker experience, needs real verification
- [testcontainers-python](https://github.com/testcontainers/testcontainers-python) -- reference architecture for container testing (not using, but confirms no-plugin approach is viable)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all tools already in use
- Architecture: HIGH -- existing code is complete and well-structured, only needs extension
- AST pattern: HIGH -- verified working with actual Python 3.12 ast module on real Odoo code patterns
- Docker lifecycle: HIGH -- reviewed existing code, health checks, teardown, and error handling
- i18n conventions: HIGH -- confirmed with official Odoo 17 documentation that field `string=` is auto-translated

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (30 days -- stable domain, Docker images pinned to `odoo:17` and `postgres:16`)
