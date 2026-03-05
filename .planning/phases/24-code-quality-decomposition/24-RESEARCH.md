# Phase 24: Code Quality & Decomposition - Research

**Researched:** 2026-03-05
**Domain:** Python code quality — lazy imports, function decomposition, resource path resolution
**Confidence:** HIGH

## Summary

Phase 24 addresses three independent code quality improvements: (1) deferring heavy imports in `cli.py` to inside command functions, (2) decomposing the 728-line `renderer.py` monolith into stage functions under 80 lines each, and (3) replacing the fragile 5-level `Path(__file__).parent.parent...` traversal in `docker_runner.py` with `importlib.resources` or config-based resolution.

All three are well-understood Python refactoring patterns with no external dependencies to add. The Result[T] type from Phase 23 is already available in `odoo_gen_utils.validation.types` and must be used by the decomposed render functions.

**Primary recommendation:** Split into 2 plans — Plan 1: CLI lazy imports + Docker path fix (small, mechanical); Plan 2: renderer decomposition (larger, needs careful extraction and Result[T] integration).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUAL-01 | CLI defers heavy imports inside command functions, module-level = click + stdlib only | Identified 11 heavy import lines (lines 12-43 of cli.py) to move into respective command functions |
| QUAL-02 | render_module decomposed into stage functions each under 80 lines | Identified 7 stages in render_module (lines 352-728): manifest, models, views, security, wizards, tests, static — each maps to a render_* function |
| QUAL-03 | Docker compose file path via importlib.resources instead of 5-level parent traversal | get_compose_file() at docker_runner.py:42-51 uses `.parent.parent.parent.parent.parent / "docker"` — replace with importlib.resources or package data |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| click | (existing) | CLI framework | Already used, only allowed module-level import |
| importlib.resources | stdlib 3.12 | Package resource path resolution | Standard way to locate package data files in Python 3.9+ |
| Result[T] | Phase 23 | Structured return type | Already defined in odoo_gen_utils.validation.types |

### Supporting
No new libraries needed. This phase is pure refactoring.

## Architecture Patterns

### Pattern 1: Lazy Import in Click Commands

**What:** Move heavy library imports from module top-level into the body of each `@main.command()` function that uses them.
**When to use:** CLI tools where startup time matters and not all commands need all imports.

```python
# BEFORE (cli.py lines 12-43): 11 heavy import statements at module level
from odoo_gen_utils.auto_fix import format_escalation, run_docker_fix_loop, run_pylint_fix_loop
from odoo_gen_utils.search import build_oca_index, get_github_token, get_index_status
# ... etc

# AFTER: imports inside each command function
@main.command()
def validate(module_path, ...):
    from odoo_gen_utils.auto_fix import format_escalation, run_docker_fix_loop, run_pylint_fix_loop
    from odoo_gen_utils.validation import (
        check_docker_available, docker_install_module, ...
    )
    # ... command body
```

**Import mapping (which commands use which imports):**

| Import | Used By Command(s) |
|--------|-------------------|
| `auto_fix.*` | `validate` |
| `i18n_extractor.*` | `extract_i18n` |
| `kb_validator.*` | `validate_kb` |
| `search.*`, `search.wizard.*`, `search.analyzer.*`, `search.fork.*`, `search.index.*`, `search.query.*` | `build_index`, `index_status`, `search_modules_cmd`, `extend_module_cmd` |
| `edition.*` | `check_edition` |
| `renderer.*` | `render`, `list_templates`, `render_module_cmd` |
| `verifier.*` | `render_module_cmd` |
| `validation.*` | `validate` |

**Keep at module level:** `click`, `json`, `sys`, `Path` (from pathlib), `__version__`.

### Pattern 2: Stage Function Decomposition for render_module

**What:** Extract the monolithic `render_module()` (lines 352-728, ~376 lines) into independently testable stage functions.
**Target functions (each under 80 lines):**

| Function | Current Lines | Responsibility |
|----------|--------------|----------------|
| `render_manifest` | ~20 | __manifest__.py + root __init__.py + models/__init__.py |
| `render_models` | ~60 | Per-model .py files + per-model views + actions |
| `render_views` | ~15 | Menu XML |
| `render_security` | ~30 | security.xml + ir.model.access.csv + record_rules.xml |
| `render_wizards` | ~40 | wizards/__init__.py + per-wizard .py + per-wizard form XML |
| `render_tests` | ~20 | tests/__init__.py + per-model test files |
| `render_static` | ~30 | data.xml, sequences.xml, demo, static/index.html, README.rst |

**Each stage function signature:**
```python
def render_manifest(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render manifest and init files. Returns Result with created file paths."""
```

**The orchestrator `render_module` becomes ~60 lines:**
```python
def render_module(spec, template_dir, output_dir, verifier=None):
    # Setup (~20 lines: env, module_dir, contexts, state)
    # Call each stage, collect files, short-circuit on failure
    for stage_fn in [render_manifest, render_models, render_views,
                     render_security, render_wizards, render_tests, render_static]:
        result = stage_fn(env, spec, module_dir, module_context, ...)
        if not result.success:
            return [], []  # or propagate Result
        created_files.extend(result.data)
    # Save state, return
```

**Key:** `_build_model_context` (lines 160-285, 125 lines) stays as-is -- it is a pure data function, not a render stage. `_compute_manifest_data` and `_compute_view_files` also stay as helpers.

### Pattern 3: importlib.resources for Docker Compose Path

**What:** Replace the fragile `Path(__file__).parent.parent.parent.parent.parent / "docker" / "docker-compose.yml"` with `importlib.resources`.

**Current problem (docker_runner.py:42-51):**
```python
def get_compose_file() -> Path:
    return (
        Path(__file__).parent.parent.parent.parent.parent
        / "docker"
        / "docker-compose.yml"
    )
```
This traverses: `validation/ -> odoo_gen_utils/ -> src/ -> python/ -> project_root/ -> docker/`. Breaks if package structure changes.

**Solution options:**

1. **importlib.resources (preferred):** Ship `docker-compose.yml` as package data inside `odoo_gen_utils/data/` or similar, then:
```python
from importlib.resources import files

def get_compose_file() -> Path:
    return files("odoo_gen_utils").joinpath("data", "docker-compose.yml")
```
Requires: copy or symlink `docker/docker-compose.yml` into the package data dir, and ensure `pyproject.toml` includes it.

2. **Environment variable / config fallback:**
```python
def get_compose_file() -> Path:
    env_path = os.environ.get("ODOO_GEN_COMPOSE_FILE")
    if env_path:
        return Path(env_path)
    # Fall back to importlib.resources
    return files("odoo_gen_utils").joinpath("data", "docker-compose.yml")
```

**Recommendation:** Use option 2 (importlib.resources + env var override). The env var gives users flexibility; importlib.resources gives a robust default.

**Package data note:** The package already has a `data/` directory under `odoo_gen_utils/validation/data/`. The docker-compose.yml should go under `odoo_gen_utils/data/` (top-level package data) since it is not validation-specific. Alternatively, keep it at `odoo_gen_utils/validation/data/docker-compose.yml` since only docker_runner uses it. Either way, `pyproject.toml` must include the data files via `[tool.hatch.build.targets.wheel]` or equivalent.

### Anti-Patterns to Avoid
- **Moving _build_model_context into each stage:** This function builds context used by multiple stages -- keep it shared.
- **Breaking the public API:** `render_module()` signature must remain backward compatible. The stage functions are internal.
- **Importing Result in renderer.py at module level when it is only needed for return types:** This is fine -- Result is a lightweight dataclass in stdlib-only validation.types, not a heavy import.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Package resource paths | Manual parent traversal | `importlib.resources.files()` | Handles installed packages, editable installs, and zip imports correctly |
| Structured error returns | Custom tuple returns | `Result[T]` from Phase 23 | Already defined, consistent with rest of codebase |

## Common Pitfalls

### Pitfall 1: Circular Import After Lazy Import Refactoring
**What goes wrong:** Moving imports inside functions can surface circular imports that were previously hidden by module-level resolution order.
**Why it happens:** Python resolves module-level imports at import time in dependency order; function-level imports happen at call time.
**How to avoid:** Test each command individually after refactoring. Run `python -c "from odoo_gen_utils.cli import main"` to verify CLI loads without triggering heavy imports.
**Warning signs:** `ImportError` when running a specific command.

### Pitfall 2: importlib.resources Returns Traversable, Not Path
**What goes wrong:** `importlib.resources.files()` returns a `Traversable` object, not a `Path`. Docker compose needs a real filesystem path.
**Why it happens:** `Traversable` is an abstract interface that works for zip files too.
**How to avoid:** Use `importlib.resources.as_file()` context manager to get a real `Path`, or cast with `Path(str(traversable))` for installed packages where the file is on disk.
**Recommended pattern:**
```python
from importlib.resources import files, as_file

def get_compose_file() -> Path:
    ref = files("odoo_gen_utils").joinpath("data", "docker-compose.yml")
    # For editable installs and normal installs, this is already a real path
    return Path(str(ref))
```

### Pitfall 3: Artifact State Tracking Across Stage Functions
**What goes wrong:** The `_state` variable is mutated across multiple render stages inside `render_module`. After decomposition, state tracking must be passed through or handled centrally.
**How to avoid:** Pass `_state` as a parameter to each stage function, or handle state tracking only in the orchestrator after collecting results.
**Recommendation:** Keep state tracking in the orchestrator only -- stage functions return file lists, orchestrator records state transitions.

### Pitfall 4: Verifier Calls During Model Rendering
**What goes wrong:** The `verifier` is called inline during model rendering (lines 502-506, 538-542). After decomposition, `render_models` needs the verifier parameter.
**How to avoid:** Pass `verifier` to `render_models` stage function. Other stages do not need it.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | python/pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `cd python && python -m pytest tests/test_renderer.py tests/test_cli_validate.py -x -q` |
| Full suite command | `cd python && python -m pytest tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUAL-01 | CLI module-level has only click+stdlib imports | unit | `cd python && python -m pytest tests/test_cli_lazy_imports.py -x` | No - Wave 0 |
| QUAL-02 | render_module decomposed, stages under 80 lines | unit | `cd python && python -m pytest tests/test_renderer.py tests/test_render_stages.py -x` | Partial (test_renderer.py exists) |
| QUAL-03 | Docker compose path via importlib.resources | unit | `cd python && python -m pytest tests/test_docker_compose_path.py -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && python -m pytest tests/test_renderer.py tests/test_cli_validate.py -x -q`
- **Per wave merge:** `cd python && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cli_lazy_imports.py` -- verifies CLI module-level imports contain only click+stdlib (QUAL-01)
- [ ] `tests/test_render_stages.py` -- tests each decomposed render_* stage function independently (QUAL-02)
- [ ] `tests/test_docker_compose_path.py` -- tests get_compose_file returns valid path without parent traversal (QUAL-03)

## Sources

### Primary (HIGH confidence)
- Direct source code analysis of `cli.py` (821 lines), `renderer.py` (728 lines), `docker_runner.py` (256 lines)
- Python 3.12 stdlib `importlib.resources` documentation
- Phase 23 Result[T] type in `odoo_gen_utils.validation.types`

### Secondary (MEDIUM confidence)
- Python packaging best practices for package data inclusion

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, pure refactoring
- Architecture: HIGH - patterns are straightforward Python refactoring
- Pitfalls: HIGH - identified from direct code analysis

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain, no external dependencies)
