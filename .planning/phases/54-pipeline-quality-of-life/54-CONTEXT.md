# Phase 54: Pipeline Quality of Life - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Generation pipeline produces a manifest of what it generated (`.odoo-gen-manifest.json`), supports human checkpoint callbacks at key stages via `RenderHook` Protocol, tracks stage completion with `GenerationSession` dataclass, and can resume from where it left off via `resume_from` parameter. Replaces existing `artifact_state.py` (`ModuleState`/`ArtifactState`/`.odoo-gen-state.json`) with the manifest as single source of truth.

</domain>

<decisions>
## Implementation Decisions

### Manifest Content & Schema
- Pydantic model `GenerationManifest` — NOT plain dict
- File: `.odoo-gen-manifest.json` per module, inside module dir alongside generated code
- REPLACES existing `.odoo-gen-state.json` — don't maintain two state files that drift apart
- Manifest is a superset of old artifact state: includes file paths, SHA256 checksums, stage results, preprocessor list, timing, validation results
- Key fields:
  - `module`, `spec_version`, `spec_sha256`, `generated_at`, `odoo_version`, `generator_version`
  - `preprocessing`: `preprocessors_run` (list of "name:order"), `duration_ms`
  - `stages`: dict of stage_name → `StageResult` (status, duration_ms, reason, error)
  - `artifacts`: `files` (list of path + sha256), `total_files`, `total_lines`
  - `validation`: semantic_errors, semantic_warnings, duration_ms
  - `models_registered`: list of model names
- `StageResult` Pydantic model: `status: Literal['complete', 'skipped', 'failed', 'pending']`, `duration_ms`, `reason`, `error`
- `ArtifactEntry` Pydantic model: `path: str`, `sha256: str`
- Old `save_state()`/`load_state()` become `save_manifest()`/`load_manifest()` returning Pydantic objects
- If old `.odoo-gen-state.json` exists, ignore it — new manifest is authoritative
- Manifest used by: registry update (models_registered), semantic validation (file list), resume (stages), checker (spec_sha256), GSD (post-generation state)

### RenderHook Protocol Design
- Three callbacks, observe only — hooks CANNOT modify state (critical for determinism)
- Same spec + different hooks = same output (hooks are monitoring/logging/pausing, not transforming)
- Protocol definition:
  ```python
  @runtime_checkable
  class RenderHook(Protocol):
      def on_preprocess_complete(self, module_name: str, models: list[dict], preprocessors_run: list[str]) -> None: ...
      def on_stage_complete(self, module_name: str, stage_name: str, result: StageResult, artifacts: list[str]) -> None: ...
      def on_render_complete(self, module_name: str, manifest: GenerationManifest) -> None: ...
  ```
- `render_module()` takes `hooks: list[RenderHook] = None` parameter (default None = zero overhead)
- Hooks called in order: all hooks get on_preprocess_complete, then per-stage on_stage_complete, then on_render_complete
- Built-in hooks shipped with belt:
  - `LoggingHook`: prints stage progress to console (icon + name + status + duration)
  - `ManifestHook`: writes `.odoo-gen-manifest.json` after render (via on_render_complete)

### Stage Tracking & Resume
- `GenerationSession` dataclass tracks all stage results during a render
- Key methods: `record_stage(name, result)`, `is_stage_complete(name)`, `to_manifest()`
- Resume behavior (`--resume` flag):
  1. Load existing `.odoo-gen-manifest.json` from output dir
  2. Check `spec_sha256` — if spec changed, FULL re-run (warn user)
  3. If spec unchanged, re-run preprocessing (fast <50ms, ensures fresh context)
  4. Skip stages where manifest says `status='complete'` AND output files still exist with matching sha256
  5. Run remaining stages from where it stopped
- ALL 11 stages are resumable — each produces own files, none depends on runtime state from previous stage
- Why re-run preprocessing on resume: stateless pure functions (<50ms), guarantees correct context dict
- Why check sha256 of existing artifacts: if someone manually edited a generated file, don't overwrite silently — re-run that stage
- `GenerationSession` + `GenerationManifest` REPLACE `ModuleState` and `ArtifactState` — old code deprecated

### GSD Checkpoint Integration
- GSD provides `GSDPauseHook` implementing `RenderHook` Protocol — NOT part of the belt itself
- The belt knows NOTHING about GSD, checkpoints, or human review — clean separation
- Pauses after configurable stages by raising `CheckpointPause` exception
- `CheckpointPause(Exception)` — specific exception that GSD catches
- Default checkpoint stages: `['models', 'security']` — hardest to fix after the fact
- Configurable via `.planning/config.json` under `odoo.checkpoint_stages`
- Empty list = no pauses (YOLO mode); all 11 stages = maximum review
- Checkpoint file format: `.odoo-gen-checkpoints/{module}_{stage}.json` with module, stage, artifacts list, timestamp, status (awaiting_review/approved/rejected)
- GSD resume flow: read checkpoint file, if "approved" → proceed, if "rejected" → prompt for feedback and re-run stage
- How GSD handles pause:
  ```python
  try:
      render_module(spec, output_dir, hooks=[GSDPauseHook(...)])
  except CheckpointPause as e:
      print(e.message)
      print("Review files, then run: odoo-gen generate --resume")
  ```

### Claude's Discretion
- Internal helper signatures (SHA256 computation, artifact integrity checking)
- `_artifacts_intact()` implementation details
- How `generator_version` is determined (from `__version__`)
- Exact Pydantic model field ordering and JSON serialization options
- Whether `LoggingHook` uses `click.echo()` or `print()`
- Test fixture design for hook/manifest/resume tests

</decisions>

<specifics>
## Specific Ideas

- User provided exact JSON schema for `.odoo-gen-manifest.json` with all fields and nesting
- User provided exact Pydantic model definitions: `StageResult`, `ArtifactEntry`, `GenerationManifest`
- User provided exact `RenderHook` Protocol with `@runtime_checkable` and three method signatures
- User provided exact `GSDPauseHook` implementation pattern with `CheckpointPause` exception
- User provided exact `GenerationSession` class interface with `record_stage()`, `is_stage_complete()`, `to_manifest()`
- User specified REPLACE (not extend) strategy for `artifact_state.py` → manifest
- User specified preprocessing ALWAYS re-runs on resume (fast, ensures fresh context)
- User specified sha256 integrity check for artifact files on resume — don't overwrite manually edited files
- User specified default checkpoint stages: models + security (hardest to fix after the fact)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `artifact_state.py`: `ModuleState`, `ArtifactState`, `save_state()`/`load_state()`, `format_state_table()` — BEING REPLACED but patterns are reusable
- `spec_schema.py`: Pydantic v2 models with `ConfigDict(protected_namespaces=())` — same pattern for manifest models
- `renderer.py:788-868`: `render_module()` with 11 stage lambdas — hook integration points between stages
- `preprocessors/_registry.py`: `run_preprocessors()` returns preprocessor names via registry — data for manifest's `preprocessors_run`

### Established Patterns
- Pydantic v2 with `ConfigDict(protected_namespaces=())` for all models (Phase 47)
- `render_module()` returns `(files, warnings)` — needs to also handle hooks parameter
- Stage lambdas return `Result` objects with `.success` and `.data` (list of paths)
- Lazy imports in CLI commands (Phase 47 pattern)

### Integration Points
- `renderer.py`: `render_module()` signature change (add `hooks` and `resume_from` params)
- `artifact_state.py`: deprecate/replace with new manifest module
- `cli.py`: `render_module_cmd()` needs `--resume` flag, hook instantiation
- New file: `manifest.py` (Pydantic models + save/load + GenerationSession)
- New file: `hooks.py` (RenderHook Protocol + LoggingHook + ManifestHook + CheckpointPause)
- `cli.py`: `show-state` command updated to read new manifest format

</code_context>

<deferred>
## Deferred Ideas

- GSD `GSDPauseHook` implementation — lives in odoo-gsd extension, not in the belt (separate repo/phase)
- Checkpoint approval/rejection workflow (GSD's interactive review flow) — GSD-side concern
- Manifest diffing (compare two manifests to see what changed) — nice-to-have for future milestone
- Remote manifest storage/sync — out of scope
- Stage-level rollback (undo a specific stage's output) — over-engineering for now

</deferred>

---

*Phase: 54-pipeline-quality-of-life*
*Context gathered: 2026-03-08*
