# Generate Workflow

End-to-end code generation from an approved spec.json.
Called from spec.md after user approval. NOT called by scaffold.md or /odoo-gen:new.

---

## Overview

This workflow implements a two-pass hybrid approach to module generation:

1. **Pass 1 (Jinja2):** `odoo-gen-utils render-module` runs the Jinja2 template engine to produce all structural files, including `# TODO: implement` method stubs for computed fields, onchange handlers, and constraint methods.

2. **Wave 1 (sequential after Pass 1):** The `odoo-model-gen` agent rewrites each model file with complete, OCA-compliant method bodies, replacing all `# TODO: implement` stubs. Wave 1 must complete entirely before Wave 2 begins, because Wave 2 agents read the completed model files.

3. **Wave 2 (parallel after Wave 1):** Two agents run in parallel:
   - `odoo-view-gen` enriches view files with action buttons for workflow state transitions
   - `odoo-test-gen` adds computed field tests, constraint tests, and onchange tests to the Jinja2-generated test stubs

4. **Commit:** All generated files are committed to git in a single atomic commit.

5. **Report:** A generation summary is displayed to the user.

This workflow does NOT generate kanban views (deferred to Phase 7 per Decision F).
This workflow does NOT generate CRUD overrides (deferred to Phase 7 per Decision A).

---

## Inputs

- `$MODULE_NAME` — module technical name (from spec.json `module_name` field)
- `$SPEC_PATH` — absolute path to approved spec.json (e.g., `./$MODULE_NAME/spec.json`)
- `$OUTPUT_DIR` — output directory (default: current working directory)

---

## Step 1: Render Structural Files

Run the render-module CLI to produce the complete OCA module structure:

```bash
odoo-gen-utils render-module \
  --spec-file "$SPEC_PATH" \
  --output-dir "$OUTPUT_DIR"
```

This produces:
- `$MODULE_NAME/__manifest__.py` — with correct load order (sequences first, wizard views last)
- `$MODULE_NAME/__init__.py` — imports models/ and wizards/ (if any)
- `$MODULE_NAME/models/__init__.py` and `models/*.py` — with `# TODO: implement` method stubs for computed/onchange/constrains
- `$MODULE_NAME/views/*_views.xml` — form (with `<header>` if state field) + tree + search
- `$MODULE_NAME/views/*_action.xml` and `views/menu.xml`
- `$MODULE_NAME/data/sequences.xml` (if sequence fields detected) and `data/data.xml`
- `$MODULE_NAME/wizards/__init__.py` and `wizards/*.py` (if wizards in spec)
- `$MODULE_NAME/views/*_wizard_form.xml` (if wizards in spec)
- `$MODULE_NAME/security/security.xml` and `security/ir.model.access.csv`
- `$MODULE_NAME/tests/__init__.py` and `tests/test_*.py`
- `$MODULE_NAME/README.rst`

Verify the CLI exits with code 0 before continuing. If it fails, report the error and stop.

---

## Step 2: Wave 1 — Model Method Bodies

IMPORTANT: Wave 1 must complete fully before Wave 2 begins. `odoo-view-gen` reads the
completed model files to add correct action button names.

For each model in `spec.models` that has at least one field with `compute`, `onchange`, or
`constrains` key:

Spawn an `odoo-model-gen` Task (one per model file, can run in parallel across models):

**Task prompt for odoo-model-gen:**
> Read the file `$OUTPUT_DIR/$MODULE_NAME/models/{model_var}.py` and the spec at `$SPEC_PATH`.
> Model to process: `{model_name}`.
> Rewrite the ENTIRE model file with complete OCA-compliant method bodies replacing all
> `# TODO: implement` stubs. Do NOT change any field declarations. Follow all REQUIRED
> patterns from your system prompt (for rec in self:, ValidationError for constraints, etc.).
> When done, confirm how many TODO stubs were replaced.

Wait for ALL odoo-model-gen tasks to complete before proceeding to Wave 2.

If a model has NO computed/onchange/constrains fields: skip it (no agent spawn needed, Jinja2 output is already complete).

---

## Step 3: Wave 2 — View Enrichment + Test Generation

Spawn these two agents in parallel using the Task tool:

### Task A: odoo-view-gen

**Prompt:**
> Read all view files in `$OUTPUT_DIR/$MODULE_NAME/views/` and the corresponding model files
> in `$OUTPUT_DIR/$MODULE_NAME/models/`. Read spec at `$SPEC_PATH`.
> For each model that has workflow_states in the spec: enrich the form view's `<header>` block
> with action buttons for each state transition (matching action_{state} methods in the model).
> Use `invisible="state != '{current_state}'"` pattern. Do NOT add kanban views.
> Write enriched view files back to the same paths.

### Task B: odoo-test-gen

**Prompt:**
> Read all model files in `$OUTPUT_DIR/$MODULE_NAME/models/` and the corresponding test files
> in `$OUTPUT_DIR/$MODULE_NAME/tests/`. Read spec at `$SPEC_PATH`.
> For each model: rewrite the complete test_{model_var}.py file with all Phase 6 test categories:
> (1) Computed field tests (2 per computed field: basic + zero_case)
> (2) Constraint tests (valid + invalid with assertRaises(ValidationError))
> (3) Onchange tests (1 per onchange handler)
> (4) CRUD write test (1 per model: write a field, assert changed)
> (5) CRUD unlink test (1 per model: delete record, assert browse().exists() is False)
> (6) Access rights tests (2 per model: test_user_can_create with module User group via with_user(),
>     test_no_group_cannot_create with base.group_user only, assertRaises(AccessError))
> (7) Workflow transition tests (1 per consecutive state pair when workflow_states in spec has 2+ entries,
>     call action_STATE_KEY(), assert state changed)
> Use TransactionCase. Import AccessError from odoo.exceptions. Do NOT duplicate existing test method names.
> Read the module_name from spec.json to build group refs: MODULE_NAME.group_MODULE_NAME_user

Wait for BOTH tasks to complete.

---

## Step 4: Commit Generated Module

```bash
git add "$OUTPUT_DIR/$MODULE_NAME/"
git commit -m "feat($MODULE_NAME): generate complete Odoo 17.0 module from spec

Generated files: models, views, security, tests, data, wizards (if any)
Spec: $SPEC_PATH
"
```

If git commit fails (not in a repo, no changes staged): report the issue, confirm that
all files were written to disk, and suggest manual commit steps.

---

## Step 5: Summary Report

After commit, display:

```
Generation Complete: $MODULE_NAME

Files generated: {count from render-module output}
Models: {model names}
Views: form + tree + search per model
Wizards: {count or "none"}
Tests: {count of test files}

Method stubs filled: {total TODO stubs replaced by odoo-model-gen}
View enrichments: {count of buttons added by odoo-view-gen}

Next steps:
- Validate the module: /odoo-gen:validate ./$MODULE_NAME/
- Review generated code: check models/ and views/ for correctness
- If validation fails: /odoo-gen:validate will show specific issues to fix
```

---

## Error Handling

- **render-module CLI fails**: Stop generation. Show the error. Fix the spec.json and retry.
- **odoo-model-gen returns error for a model**: Log the error, continue with remaining models, report at end.
- **Wave 2 task fails**: Log the error, do not block the commit. Report which enrichment failed.
- **git commit fails**: Report error, confirm files exist on disk, provide manual commit command.
