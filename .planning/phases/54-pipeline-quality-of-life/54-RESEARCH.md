# Phase 54: Pipeline Quality of Life - Research

**Researched:** 2026-03-08
**Domain:** Python pipeline observability, checkpoint hooks, generation manifest, resume-from-interruption
**Confidence:** HIGH

## Summary

Phase 54 replaces the existing `artifact_state.py` (`ModuleState`/`ArtifactState`/`.odoo-gen-state.json`) with a Pydantic v2-based `GenerationManifest` written to `.odoo-gen-manifest.json`. It introduces a `RenderHook` Protocol for observe-only callbacks at pipeline stages, a `GenerationSession` dataclass to track stage completion during a render, and a `resume_from` parameter on `render_module()` to skip already-completed stages after interruption.

The existing codebase has a clear integration surface: `render_module()` at line 788 of `renderer.py` (868 lines total) orchestrates 11 stage lambdas that each return `Result[list[Path]]`. The current artifact state tracking (lines 836-867) is a try/except block that creates a `ModuleState`, calls `_track_artifacts()`, and `save_state()` -- all wrapped in exception handlers so failures never block generation. The new manifest/hook/session system replaces this block entirely.

**Primary recommendation:** Create two new files (`manifest.py` for Pydantic models + `GenerationSession` + save/load, `hooks.py` for `RenderHook` Protocol + `LoggingHook` + `ManifestHook` + `CheckpointPause`), modify `render_module()` to accept `hooks` and `resume_from` parameters, update CLI `render-module` and `show-state` commands, and deprecate `artifact_state.py`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Pydantic model `GenerationManifest` -- NOT plain dict
- File: `.odoo-gen-manifest.json` per module, inside module dir alongside generated code
- REPLACES existing `.odoo-gen-state.json` -- don't maintain two state files that drift apart
- Manifest is a superset of old artifact state: includes file paths, SHA256 checksums, stage results, preprocessor list, timing, validation results
- Key fields: `module`, `spec_version`, `spec_sha256`, `generated_at`, `odoo_version`, `generator_version`, `preprocessing` (preprocessors_run, duration_ms), `stages` (dict of stage_name to StageResult), `artifacts` (files list of path+sha256, total_files, total_lines), `validation` (semantic_errors, semantic_warnings, duration_ms), `models_registered` (list of model names)
- `StageResult` Pydantic model: `status: Literal['complete', 'skipped', 'failed', 'pending']`, `duration_ms`, `reason`, `error`
- `ArtifactEntry` Pydantic model: `path: str`, `sha256: str`
- Old `save_state()`/`load_state()` become `save_manifest()`/`load_manifest()` returning Pydantic objects
- If old `.odoo-gen-state.json` exists, ignore it -- new manifest is authoritative
- Three RenderHook callbacks, observe only -- hooks CANNOT modify state (critical for determinism)
- Same spec + different hooks = same output (hooks are monitoring/logging/pausing, not transforming)
- `RenderHook` Protocol with `@runtime_checkable`: `on_preprocess_complete`, `on_stage_complete`, `on_render_complete`
- `render_module()` takes `hooks: list[RenderHook] = None` parameter (default None = zero overhead)
- Built-in hooks: `LoggingHook` (prints stage progress), `ManifestHook` (writes `.odoo-gen-manifest.json` via on_render_complete)
- `GenerationSession` dataclass tracks all stage results during a render with `record_stage(name, result)`, `is_stage_complete(name)`, `to_manifest()`
- Resume behavior: load existing manifest, check `spec_sha256` (changed = full re-run with warning), re-run preprocessing always (fast <50ms), skip stages where manifest says complete AND output files exist with matching sha256, run remaining stages
- ALL 11 stages are resumable
- `GenerationSession` + `GenerationManifest` REPLACE `ModuleState` and `ArtifactState`
- GSD provides `GSDPauseHook` -- NOT part of the belt itself (clean separation)
- `CheckpointPause(Exception)` -- specific exception that GSD catches

### Claude's Discretion
- Internal helper signatures (SHA256 computation, artifact integrity checking)
- `_artifacts_intact()` implementation details
- How `generator_version` is determined (from `__version__`)
- Exact Pydantic model field ordering and JSON serialization options
- Whether `LoggingHook` uses `click.echo()` or `print()`
- Test fixture design for hook/manifest/resume tests

### Deferred Ideas (OUT OF SCOPE)
- GSD `GSDPauseHook` implementation -- lives in odoo-gsd extension, not in the belt (separate repo/phase)
- Checkpoint approval/rejection workflow (GSD's interactive review flow) -- GSD-side concern
- Manifest diffing (compare two manifests to see what changed) -- nice-to-have for future milestone
- Remote manifest storage/sync -- out of scope
- Stage-level rollback (undo a specific stage's output) -- over-engineering for now
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ARCH-04 | Generation manifest with file paths, SHA256 checksums, template versions, preprocessor list -- persisted as `.odoo-gen-manifest.json` sidecar | Pydantic v2 models (`GenerationManifest`, `StageResult`, `ArtifactEntry`), `save_manifest()`/`load_manifest()` in new `manifest.py`, SHA256 via `hashlib.sha256`, canonical JSON for `spec_sha256` |
| ARCH-05 | Checkpoint hooks via `RenderHook` Protocol in `renderer.py` with `on_preprocess_complete`, `on_stage_complete`, `on_render_complete` callbacks -- zero overhead when `hooks=None` | Python `typing.Protocol` + `@runtime_checkable`, `LoggingHook` + `ManifestHook` in new `hooks.py`, `CheckpointPause(Exception)` for GSD integration |
| ARCH-06 | Generation state persistence with `GenerationSession` dataclass, `resume_from` parameter on `render_module()` to skip completed stages | `GenerationSession` dataclass with `record_stage()`, `is_stage_complete()`, `to_manifest()` in `manifest.py`, `_artifacts_intact()` helper for SHA256 file verification, `--resume` CLI flag |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 (>=2.10,<3.0) | Manifest schema models (GenerationManifest, StageResult, ArtifactEntry) | Already a project dependency; established pattern from spec_schema.py |
| hashlib | stdlib | SHA256 checksums for spec and artifact files | Python stdlib, no dependencies |
| typing | stdlib | Protocol, runtime_checkable, Literal | Python 3.12 stdlib, verified working |
| dataclasses | stdlib | GenerationSession tracking | Python stdlib, project uses frozen dataclasses extensively |
| time | stdlib | Stage duration timing (time.perf_counter_ns() for ms precision) | Stdlib, no dependencies |
| json | stdlib | Manifest JSON serialization/deserialization | Stdlib, Pydantic model_dump() + json.dumps() |
| click | >=8.0 | CLI --resume flag, LoggingHook output | Already a project dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| datetime | stdlib | `generated_at` timestamp in manifest | ISO 8601 UTC timestamp for manifest |
| pathlib | stdlib | File path operations for artifact integrity checking | Already used throughout project |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic for manifest | Plain dataclass + json | Pydantic gives validation, JSON schema, model_dump() -- consistent with spec_schema.py pattern |
| time.perf_counter_ns() | time.time() | perf_counter_ns() gives monotonic nanosecond precision; convert to ms for human readability |
| Protocol for hooks | ABC | Protocol is structural typing (duck typing) -- no inheritance required, cleaner for external implementations like GSDPauseHook |

**Installation:**
```bash
# No new dependencies needed -- all are stdlib or already in pyproject.toml
```

## Architecture Patterns

### Recommended Project Structure
```
python/src/odoo_gen_utils/
├── manifest.py          # NEW: GenerationManifest, StageResult, ArtifactEntry (Pydantic),
│                        #       GenerationSession (dataclass), save_manifest(), load_manifest(),
│                        #       compute_file_sha256(), compute_spec_sha256()
├── hooks.py             # NEW: RenderHook Protocol, LoggingHook, ManifestHook,
│                        #       CheckpointPause exception
├── renderer.py          # MODIFY: render_module() gains hooks + resume_from params,
│                        #          stage loop refactored to named stages with timing
├── cli.py               # MODIFY: render_module_cmd gets --resume flag,
│                        #          show-state reads manifest instead of old state
├── artifact_state.py    # DEPRECATE: keep file but add deprecation warning in docstring
└── ...
```

### Pattern 1: Named Stage Tuple Pattern
**What:** Replace anonymous lambdas with named tuples `(stage_name, stage_fn)` to enable hook callbacks and resume-from
**When to use:** In `render_module()` stage list
**Example:**
```python
# Current (anonymous lambdas):
stages = [
    lambda: render_manifest(env, spec, module_dir, ctx),
    lambda: render_models(env, spec, module_dir, ctx, ...),
    ...
]

# New (named stages):
STAGE_NAMES: list[str] = [
    "manifest", "models", "views", "security", "mail_templates",
    "wizards", "tests", "static", "cron", "reports", "controllers",
]

stages: list[tuple[str, Callable[[], Result]]] = [
    ("manifest", lambda: render_manifest(env, spec, module_dir, ctx)),
    ("models", lambda: render_models(env, spec, module_dir, ctx, ...)),
    ...
]

for stage_name, stage_fn in stages:
    if session.is_stage_complete(stage_name) and _artifacts_intact(stage_name, ...):
        session.record_stage(stage_name, StageResult(status="skipped", reason="resumed"))
        continue
    t0 = time.perf_counter_ns()
    result = stage_fn()
    duration_ms = (time.perf_counter_ns() - t0) // 1_000_000
    stage_result = StageResult(
        status="complete" if result.success else "failed",
        duration_ms=duration_ms,
        error="; ".join(result.errors) if not result.success else None,
    )
    session.record_stage(stage_name, stage_result)
    # Notify hooks
    if hooks:
        for hook in hooks:
            hook.on_stage_complete(module_name, stage_name, stage_result, ...)
```
**Confidence:** HIGH -- directly mirrors existing code structure

### Pattern 2: Observe-Only Hook Protocol
**What:** `@runtime_checkable` Protocol that external code implements without touching belt internals
**When to use:** Any code that wants to observe pipeline progress (logging, manifest writing, GSD checkpoints)
**Example:**
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class RenderHook(Protocol):
    def on_preprocess_complete(
        self, module_name: str, models: list[dict], preprocessors_run: list[str]
    ) -> None: ...

    def on_stage_complete(
        self, module_name: str, stage_name: str, result: "StageResult", artifacts: list[str]
    ) -> None: ...

    def on_render_complete(
        self, module_name: str, manifest: "GenerationManifest"
    ) -> None: ...
```
**Confidence:** HIGH -- verified Protocol + runtime_checkable works on Python 3.12

### Pattern 3: Pydantic v2 Manifest Schema
**What:** Pydantic models with `ConfigDict(protected_namespaces=())` matching the established spec_schema.py pattern
**When to use:** For `GenerationManifest`, `StageResult`, `ArtifactEntry` models
**Example:**
```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class StageResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    status: Literal["complete", "skipped", "failed", "pending"] = "pending"
    duration_ms: int = 0
    reason: str | None = None
    error: str | None = None

class ArtifactEntry(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    path: str
    sha256: str

class GenerationManifest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    module: str
    spec_version: str = "1.0"
    spec_sha256: str
    generated_at: str  # ISO 8601 UTC
    odoo_version: str = "17.0"
    generator_version: str
    preprocessing: PreprocessingInfo
    stages: dict[str, StageResult]
    artifacts: ArtifactInfo
    validation: ValidationInfo | None = None
    models_registered: list[str] = []
```
**Confidence:** HIGH -- same pattern as `spec_schema.py`, Pydantic 2.12.5 verified

### Pattern 4: Resume Guard with SHA256 Integrity
**What:** On `--resume`, load manifest, verify spec unchanged, check file integrity per-stage
**When to use:** When `resume_from` parameter is provided to `render_module()`
**Example:**
```python
def _artifacts_intact(
    manifest: GenerationManifest, stage_name: str, module_dir: Path
) -> bool:
    """Check if all artifacts for a stage still exist with matching SHA256."""
    # Filter artifacts that belong to this stage (by path convention)
    for entry in manifest.artifacts.files:
        full_path = module_dir / entry.path
        if not full_path.exists():
            return False
        actual_sha = compute_file_sha256(full_path)
        if actual_sha != entry.sha256:
            return False  # File was manually edited
    return True
```
**Confidence:** HIGH -- stdlib hashlib, straightforward file I/O

### Anti-Patterns to Avoid
- **Hooks that modify state:** CONTEXT.md explicitly states hooks are observe-only. Never pass mutable references to hooks or let hook return values affect pipeline flow (except `CheckpointPause` which is an exception, not a return value).
- **Maintaining two state files:** The old `.odoo-gen-state.json` must be replaced, not maintained alongside `.odoo-gen-manifest.json`. The manifest is the single source of truth.
- **Blocking on manifest I/O failure:** Like the current artifact_state pattern, manifest operations must be wrapped in try/except -- manifest tracking must never block generation.
- **Computing SHA256 of large binary files synchronously:** Not a concern for this project (generated Odoo modules are small text files), but worth noting the pattern reads entire files into memory.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema validation | Custom dict validators | Pydantic BaseModel + Literal types | Type safety, serialization, validation errors for free |
| File hashing | Custom read-chunk-hash loop | `hashlib.sha256(path.read_bytes()).hexdigest()` | Simple one-liner for small files; generated modules are <1MB total |
| Canonical JSON for spec hash | Custom key sorting | `json.dumps(spec, sort_keys=True, separators=(',', ':'))` | Deterministic, no whitespace variation |
| Duration timing | `datetime.now()` subtraction | `time.perf_counter_ns()` difference | Monotonic clock, immune to system clock adjustments |
| Structural typing for hooks | ABC + inheritance | `typing.Protocol` + `@runtime_checkable` | No import coupling -- GSD implements Protocol without importing belt code |

**Key insight:** The manifest schema is a superset of the old artifact state. Pydantic gives us validation + serialization + JSON Schema for free, which is exactly the pattern established in Phase 47 (spec_schema.py).

## Common Pitfalls

### Pitfall 1: Stage Name Mismatch Between Resume and Generation
**What goes wrong:** If stage names in the manifest don't match the names used in the stage loop, resume silently re-runs everything.
**Why it happens:** Names defined in two places (manifest read and stage loop construction).
**How to avoid:** Define `STAGE_NAMES` as a module-level constant list and use it in both the stage loop and the manifest. The stage list should be `list[tuple[str, Callable]]` where the first element is the stage name from this constant.
**Warning signs:** Resume always says "re-running all stages" even when manifest exists.

### Pitfall 2: Spec SHA256 Sensitivity to Irrelevant Changes
**What goes wrong:** Adding a comment or whitespace to the spec JSON changes the SHA256, causing unnecessary full re-runs on resume.
**Why it happens:** Hashing raw file content instead of canonical form.
**How to avoid:** Hash the canonical JSON (`json.dumps(spec_dict, sort_keys=True, separators=(',', ':'))`), not the raw file bytes. This normalizes whitespace and key ordering.
**Warning signs:** Resume triggers full re-run when only formatting changed.

### Pitfall 3: Hook Exception Kills Pipeline
**What goes wrong:** A buggy hook raises an exception in `on_stage_complete()`, killing the entire render.
**Why it happens:** No exception isolation around hook calls.
**How to avoid:** Wrap every hook callback invocation in `try/except Exception` with logging. Hooks are observability -- they must never kill the pipeline. The one exception is `CheckpointPause`, which should propagate (it's intentional).
**Warning signs:** Pipeline fails with stack trace pointing to hook code.

### Pitfall 4: Circular Import Between manifest.py and renderer.py
**What goes wrong:** `manifest.py` imports types from `renderer.py` and vice versa.
**Why it happens:** `GenerationManifest` needs to be referenced in `render_module()`, and `StageResult` needs to be built from `Result` objects.
**How to avoid:** `manifest.py` and `hooks.py` should be leaf modules with no imports from `renderer.py`. The renderer imports from manifest/hooks, not the other way around. Use string forward references or `TYPE_CHECKING` guards if needed.
**Warning signs:** `ImportError: cannot import name` on startup.

### Pitfall 5: Forgetting to Map Stage Artifacts for Resume Integrity Check
**What goes wrong:** `_artifacts_intact()` can't determine which files belong to which stage, so resume skips integrity checks.
**Why it happens:** The manifest stores flat file list without stage attribution.
**How to avoid:** Either (a) tag each `ArtifactEntry` with the stage that produced it, or (b) track per-stage file lists in `GenerationSession` and include in `StageResult`. The CONTEXT.md mentions `on_stage_complete` receives `artifacts: list[str]`, suggesting per-stage artifact tracking.
**Warning signs:** Resume skips a stage whose output files were manually deleted.

### Pitfall 6: Pydantic protected_namespaces Conflict
**What goes wrong:** Pydantic v2 warns or errors on field names starting with `model_`.
**Why it happens:** Default Pydantic v2 behavior reserves `model_` prefix.
**How to avoid:** Always use `ConfigDict(protected_namespaces=())` on all Pydantic models -- this is the established project pattern from Phase 47.
**Warning signs:** `UserWarning: Field "model_..." has conflict with protected namespace "model_"`.

## Code Examples

Verified patterns from the existing codebase:

### SHA256 File Hashing (stdlib)
```python
# Source: hashlib stdlib, verified on Python 3.12.3
import hashlib
from pathlib import Path

def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA256 hex digest of a file."""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()

def compute_spec_sha256(spec: dict) -> str:
    """Compute SHA256 of canonical JSON representation of spec."""
    import json
    canonical = json.dumps(spec, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

### Pydantic v2 Model Pattern (from spec_schema.py)
```python
# Source: python/src/odoo_gen_utils/spec_schema.py lines 50-53
from pydantic import BaseModel, ConfigDict

class StageResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    status: Literal["complete", "skipped", "failed", "pending"] = "pending"
    duration_ms: int = 0
    reason: str | None = None
    error: str | None = None
```

### Current Stage Loop (to be refactored)
```python
# Source: python/src/odoo_gen_utils/renderer.py lines 843-860
stages = [
    lambda: render_manifest(env, spec, module_dir, ctx),
    lambda: render_models(env, spec, module_dir, ctx, verifier=verifier, warnings_out=all_warnings),
    lambda: render_views(env, spec, module_dir, ctx),
    lambda: render_security(env, spec, module_dir, ctx),
    lambda: render_mail_templates(env, spec, module_dir, ctx),
    lambda: render_wizards(env, spec, module_dir, ctx),
    lambda: render_tests(env, spec, module_dir, ctx),
    lambda: render_static(env, spec, module_dir, ctx),
    lambda: render_cron(env, spec, module_dir, ctx),
    lambda: render_reports(env, spec, module_dir, ctx),
    lambda: render_controllers(env, spec, module_dir, ctx),
]
for stage_fn in stages:
    result = stage_fn()
    if not result.success:
        break
    created_files.extend(result.data or [])
```

### Preprocessor Names (from registry)
```python
# Source: runtime inspection of preprocessors._registry
# These are the values that go into manifest.preprocessing.preprocessors_run
# Format: "name:order"
PREPROCESSOR_NAMES = [
    "relationships:10", "init_override_sources:15", "computation_chains:20",
    "pakistan_hec:25", "academic_calendar:27", "document_management:28",
    "constraints:30", "performance:40", "production_patterns:50",
    "security_patterns:60", "audit_patterns:70", "approval_patterns:80",
    "notification_patterns:90", "webhook_patterns:100",
]
```

### Generator Version Access
```python
# Source: python/src/odoo_gen_utils/__init__.py
from odoo_gen_utils import __version__
# __version__ = "0.1.0"
```

### Existing Artifact State Deprecation Surface
```python
# Files that import from artifact_state.py (must be updated):
# 1. renderer.py:837 -- ModuleState, save_state (replace with manifest)
# 2. renderer.py:765 -- ArtifactKind, ArtifactStatus (in _track_artifacts, remove)
# 3. cli.py:1183 -- format_state_table, load_state (update show-state command)
# 4. tests/test_artifact_state.py -- all 21 tests (keep for backward compat or migrate)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `artifact_state.py` with `ModuleState`/`ArtifactState` | `manifest.py` with `GenerationManifest`/`StageResult`/`ArtifactEntry` | Phase 54 | Single source of truth, SHA256 integrity, per-stage tracking |
| Anonymous stage lambdas | Named `(stage_name, stage_fn)` tuples | Phase 54 | Enables hooks, resume, and manifest stage tracking |
| No pipeline observability | `RenderHook` Protocol with 3 callbacks | Phase 54 | Logging, manifest writing, GSD checkpoint integration |
| No resume capability | `resume_from` + `GenerationSession` | Phase 54 | Recovery from interruptions, skip completed stages |
| `.odoo-gen-state.json` | `.odoo-gen-manifest.json` | Phase 54 | Superset of old data + SHA256 + timing + validation results |

**Deprecated/outdated:**
- `artifact_state.py`: Entire module deprecated. Keep file with deprecation notice in docstring for one milestone, then remove.
- `.odoo-gen-state.json`: Ignored by new code. If found alongside `.odoo-gen-manifest.json`, the manifest is authoritative.
- `_track_artifacts()` in renderer.py: Removed, replaced by `GenerationSession.record_stage()` + `ManifestHook`.

## Open Questions

1. **Per-stage artifact attribution**
   - What we know: The manifest stores a flat `artifacts.files` list. The `on_stage_complete` callback receives `artifacts: list[str]` per stage.
   - What's unclear: Should `ArtifactEntry` have a `stage` field, or should `StageResult` have an `artifacts` field, or both?
   - Recommendation: Add `artifacts: list[str]` to `StageResult` (list of relative paths produced by that stage). This enables per-stage integrity checking for resume and is consistent with the hook callback signature. The flat `artifacts.files` list in the manifest is the aggregate. This is Claude's discretion per CONTEXT.md.

2. **What happens when a stage fails on resume?**
   - What we know: On first run, stage failure breaks the loop. On resume, completed stages are skipped.
   - What's unclear: If stage 5 failed originally, does resume re-run stage 5 specifically?
   - Recommendation: Yes -- any stage not marked "complete" in the manifest gets re-run on resume. Failed stages are re-attempted. This follows naturally from the "skip if complete AND artifacts intact" logic.

3. **LoggingHook output mechanism**
   - What we know: CONTEXT.md says "prints stage progress to console (icon + name + status + duration)". Claude's discretion on whether to use `click.echo()` or `print()`.
   - Recommendation: Use `click.echo()` since the CLI already depends on click, and it handles encoding/piping correctly. Also consistent with how the CLI currently outputs messages.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `python/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd python && .venv/bin/pytest tests/test_manifest.py tests/test_hooks.py -x -q` |
| Full suite command | `cd python && .venv/bin/pytest tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-04a | GenerationManifest Pydantic model round-trip (model_dump/model_validate) | unit | `pytest tests/test_manifest.py::TestGenerationManifest -x` | No -- Wave 0 |
| ARCH-04b | StageResult/ArtifactEntry Pydantic models validation | unit | `pytest tests/test_manifest.py::TestStageResult -x` | No -- Wave 0 |
| ARCH-04c | save_manifest/load_manifest JSON persistence round-trip | unit | `pytest tests/test_manifest.py::TestManifestPersistence -x` | No -- Wave 0 |
| ARCH-04d | compute_file_sha256/compute_spec_sha256 correctness | unit | `pytest tests/test_manifest.py::TestSHA256 -x` | No -- Wave 0 |
| ARCH-04e | render_module produces .odoo-gen-manifest.json sidecar | integration | `pytest tests/test_manifest.py::TestRenderModuleManifest -x` | No -- Wave 0 |
| ARCH-05a | RenderHook Protocol isinstance check with concrete impl | unit | `pytest tests/test_hooks.py::TestRenderHookProtocol -x` | No -- Wave 0 |
| ARCH-05b | LoggingHook prints stage progress (capture click output) | unit | `pytest tests/test_hooks.py::TestLoggingHook -x` | No -- Wave 0 |
| ARCH-05c | ManifestHook writes manifest on on_render_complete | unit | `pytest tests/test_hooks.py::TestManifestHook -x` | No -- Wave 0 |
| ARCH-05d | Hook exceptions don't kill pipeline (except CheckpointPause) | integration | `pytest tests/test_hooks.py::TestHookExceptionIsolation -x` | No -- Wave 0 |
| ARCH-05e | hooks=None means zero hook invocations | unit | `pytest tests/test_hooks.py::TestZeroOverhead -x` | No -- Wave 0 |
| ARCH-06a | GenerationSession record_stage/is_stage_complete | unit | `pytest tests/test_manifest.py::TestGenerationSession -x` | No -- Wave 0 |
| ARCH-06b | GenerationSession.to_manifest() produces valid GenerationManifest | unit | `pytest tests/test_manifest.py::TestSessionToManifest -x` | No -- Wave 0 |
| ARCH-06c | resume skips completed stages, re-runs failed/pending | integration | `pytest tests/test_manifest.py::TestResumeFromStage -x` | No -- Wave 0 |
| ARCH-06d | resume with changed spec_sha256 triggers full re-run | integration | `pytest tests/test_manifest.py::TestResumeSpecChanged -x` | No -- Wave 0 |
| ARCH-06e | resume detects manually edited files (sha256 mismatch) and re-runs stage | integration | `pytest tests/test_manifest.py::TestResumeIntegrityCheck -x` | No -- Wave 0 |
| ARCH-06f | CLI --resume flag wired correctly | integration | `pytest tests/test_manifest.py::TestCLIResume -x` | No -- Wave 0 |
| COMPAT-01 | show-state CLI reads new manifest format | integration | `pytest tests/test_manifest.py::TestShowStateManifest -x` | No -- Wave 0 |
| COMPAT-02 | Existing test_artifact_state.py tests still pass (backward compat) | regression | `pytest tests/test_artifact_state.py -x` | Yes -- 21 tests |

### Sampling Rate
- **Per task commit:** `cd python && .venv/bin/pytest tests/test_manifest.py tests/test_hooks.py -x -q`
- **Per wave merge:** `cd python && .venv/bin/pytest tests/ -x -q`
- **Phase gate:** Full suite green (1669+ tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_manifest.py` -- covers ARCH-04, ARCH-06, COMPAT-01
- [ ] `tests/test_hooks.py` -- covers ARCH-05
- [ ] No new framework install needed -- pytest already configured
- [ ] No conftest changes needed -- existing tmp_path and monkeypatch fixtures suffice

## Sources

### Primary (HIGH confidence)
- **Codebase inspection** -- `renderer.py` (868 lines, stage loop at lines 843-868), `artifact_state.py` (221 lines), `spec_schema.py` (Pydantic v2 pattern), `cli.py` (show-state at 1178-1199, render-module-cmd at 440-552), `preprocessors/_registry.py` (14 registered preprocessors)
- **Python 3.12 stdlib** -- `typing.Protocol`, `runtime_checkable`, `Literal`, `hashlib.sha256`, `time.perf_counter_ns()`, `dataclasses` -- all verified working
- **Pydantic 2.12.5** -- `BaseModel`, `ConfigDict(protected_namespaces=())`, `model_dump()`, `model_validate()` -- verified installed and working

### Secondary (MEDIUM confidence)
- **CONTEXT.md** (54-CONTEXT.md) -- Comprehensive locked decisions from user discussion, exact Protocol signatures, exact Pydantic field definitions, exact resume behavior

### Tertiary (LOW confidence)
- None -- all research is based on codebase inspection and stdlib verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib or existing dependencies, verified on installed Python/Pydantic
- Architecture: HIGH -- clear integration points in renderer.py, established Pydantic pattern from spec_schema.py, CONTEXT.md provides exact signatures
- Pitfalls: HIGH -- derived from codebase analysis (import patterns, exception handling, stage naming consistency)

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable -- no external dependencies, stdlib-based)
