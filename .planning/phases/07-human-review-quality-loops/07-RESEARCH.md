# Phase 7: Human Review & Quality Loops - Research

**Researched:** 2026-03-02
**Domain:** Human-in-the-loop review wiring, i18n .pot generation, pylint-odoo auto-fix, Docker failure auto-fix
**Confidence:** MEDIUM-HIGH (GSD internals HIGH from source read; i18n approach MEDIUM from community sources; pylint auto-fix list MEDIUM from OCA repo analysis; Docker auto-fix patterns MEDIUM)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REVW-01 | System pauses for human review after model generation | GSD checkpoint mechanism — `type="checkpoint:human-verify"` in PLAN.md tasks |
| REVW-02 | System pauses for human review after view generation | Same GSD checkpoint mechanism, second stage checkpoint |
| REVW-03 | System pauses for human review after security generation | Third checkpoint stage |
| REVW-04 | System pauses for human review after business logic generation | Fourth checkpoint stage |
| REVW-05 | User can approve, request changes, or reject at each checkpoint | GSD checkpoint protocol — user types "approved" or describes issues |
| REVW-06 | System incorporates feedback and regenerates the rejected section | Agent re-invocation pattern: re-spawn with spec + original file + user feedback |
| QUAL-06 | System generates i18n .pot file for all translatable strings | click-odoo-makepot requires running Odoo; agent-driven extraction is the viable alternative |
| QUAL-09 | Auto-fix pylint-odoo violations and re-validate before escalating | Mechanical fixes for W8113, W8111, C8116, W8150; LLM fix for others via odoo-validator agent |
| QUAL-10 | Auto-fix Docker install/test failures before escalating | Parse error_patterns.json diagnosis; attempt fix; re-validate; max 2 attempts |
</phase_requirements>

---

## Summary

Phase 7 wires GSD's existing checkpoint mechanism into the Odoo generation pipeline and adds quality loops for i18n, pylint-odoo violations, and Docker failures. GSD already provides the complete infrastructure: `checkpoint:human-verify` tasks in PLAN.md files pause execution and present structured review UI to the user. Phase 7's work is purely wiring checkpoints at the right points in `generate.md` and implementing the auto-fix loops in the Python utility package and/or the odoo-validator agent.

The critical architectural discovery is that checkpoints in GSD are NOT runtime mechanisms — they are declared in PLAN.md files as `type="checkpoint:human-verify"` tasks. The generate.md workflow itself is NOT a PLAN.md file; it is a workflow document read by the orchestrating agent. This means Phase 7 must convert generate.md into a checkpoint-aware agent workflow OR create a new PLAN.md-based approach that wraps generate.md calls with checkpoint tasks between generation stages.

For i18n .pot generation: the canonical Odoo approach (`odoo-bin --i18n-export`) requires a running Odoo server with a database. The community tool `click-odoo-makepot` (from `click-odoo-contrib`) also requires a database connection. The practical approach for this extension — which runs generation offline — is agent-driven static extraction: the odoo-validator agent reads Python files for `_()` calls, reads XML view files for `string=` attributes and text nodes, and writes a .pot file following the standard gettext PO Template format. This is lower fidelity than `odoo-bin --i18n-export` (misses field string auto-translations) but works without a running Odoo instance and produces a valid starting .pot file.

For pylint-odoo auto-fix: a small set of violations are mechanically fixable (W8113 removes redundant `string=` params; W8111 renames deprecated field params; C8116 removes superfluous manifest keys; W8150 converts absolute to relative imports). The remaining violations require LLM judgment via the odoo-validator agent. The auto-fix loop runs pylint → fix mechanical violations → run pylint again → send remaining violations to agent for LLM fix → run pylint again → escalate if still failing. Max 2 auto-fix attempts before escalating.

For Docker auto-fix: the existing `error_patterns.json` + `diagnose_errors()` infrastructure already classifies errors. Auto-fixable patterns include XML parse errors (file and line number available, agent can rewrite), missing ACL entries (can be regenerated), and missing imports in `__init__.py`. Non-auto-fixable: circular dependencies (require architectural decisions), missing Odoo dependencies (require manifest changes), constraint violations in test data (require test rewrite). Max 2 Docker auto-fix attempts before escalating.

**Primary recommendation:** Wire checkpoints into generate.md as a new `generate-with-review.md` workflow variant, with a `skip_review` config flag. Implement pylint auto-fix as a Python utility function + agent fallback. Implement i18n extraction as static agent-driven file writing. Keep Docker auto-fix at max 2 attempts.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `difflib` | stdlib | Unified diff generation for REVW-06 before/after view | No dependency; standard; `difflib.unified_diff()` produces git-compatible output |
| `pylint-odoo` | already installed (Phase 3) | Re-validation after auto-fix | Already in stack |
| `click-odoo-contrib` | 1.23.x | click-odoo-makepot for .pot generation when Docker available | OCA standard for .pot generation |
| Python `re` | stdlib | Mechanical pylint fix — regex-based source edits | No dependency needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `difflib.HtmlDiff` | stdlib | Rich HTML diff for terminal display | Only if terminal supports HTML rendering — skip, use unified_diff instead |
| `gettext` stdlib | stdlib | Parse/write .pot file format | Writing the .pot header and entry format correctly |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Agent-driven static i18n extraction | click-odoo-makepot | click-odoo-makepot is more accurate (captures field string auto-translations) but requires a running Odoo database; static extraction works offline and produces a usable starting .pot |
| Agent-driven static i18n extraction | odoo-bin --i18n-export | Same issue — requires full Odoo server + database; Docker environment is ephemeral and teardown after each validation run |
| Python regex-based pylint auto-fix | autopep8 / black | autopep8 is not pylint-odoo aware; black reformats code but doesn't fix Odoo-specific violations |

**Installation (new dependencies):**
```bash
# click-odoo-contrib for .pot generation (optional path, only if Docker available)
uv pip install click-odoo-contrib
# No new dependencies needed for diff generation or pylint auto-fix
```

---

## Architecture Patterns

### How GSD Checkpoints Actually Work

**CRITICAL FINDING from reading GSD source:**

GSD checkpoints are declared in PLAN.md files using XML task syntax. They are NOT a runtime API. The execute-plan.md workflow reads `type="checkpoint:*"` tasks and stops execution to present them to the user.

```xml
<!-- From get-shit-done/get-shit-done/references/checkpoints.md -->
<task type="checkpoint:human-verify" gate="blocking">
  <what-built>[What was generated]</what-built>
  <how-to-verify>
    [Exact steps to review the generated output]
  </how-to-verify>
  <resume-signal>Type "approved" or describe what to change</resume-signal>
</task>
```

The checkpoint types are:
- `checkpoint:human-verify` (90% of use) — user confirms generated output is correct
- `checkpoint:decision` (9%) — user chooses between options
- `checkpoint:human-action` (1%) — user does something Claude cannot automate

For Odoo generation review (REVW-01..04), `checkpoint:human-verify` is correct: show the generated files, ask user to approve or describe changes.

**Auto-mode bypass:** When `workflow.auto_advance` is `true` in config.json (currently `false` in this project), human-verify checkpoints are auto-approved. This satisfies REVW-05 (skippable checkpoints) — the mechanism already exists.

### Pattern 1: Review Checkpoint Placement in generate.md

The generate.md workflow is an agent-readable workflow document (not a PLAN.md). Checkpoints cannot be declared in it directly — generate.md is read by the orchestrating agent (the main Claude Code session), which calls Task() for sub-agents.

**Pattern: The orchestrating agent inserts checkpoints between generation stages.**

The orchestrating agent that reads generate.md must pause after each wave and present a checkpoint to the user before spawning the next wave's agents. This is done in the main agent context (Pattern C in execute-plan.md: "Execute entirely in main context").

```
generate.md Step 1 (render-module CLI)
    ↓
CHECKPOINT: Review models and structure (human-verify)
    ↓ [user: "approved" or "fix the X field"]
generate.md Step 2 (Wave 1: odoo-model-gen)
    ↓
CHECKPOINT: Review generated model methods (human-verify)
    ↓ [user: "approved" or "redo the _compute_total with different logic"]
generate.md Step 3 (Wave 2: view-gen + test-gen in parallel)
    ↓
CHECKPOINT: Review views and tests (human-verify)
    ↓ [user: "approved"]
generate.md Step 4 (commit)
```

**Feedback incorporation (REVW-06):** When user describes changes at a checkpoint:
1. User types: "The _compute_total should divide by quantity, not multiply"
2. Orchestrating agent re-spawns odoo-model-gen with: `[original task prompt] + "USER FEEDBACK: " + [user description] + "Rewrite the file incorporating this feedback."`
3. Checkpoint repeats (up to MAX_REGENERATION_RETRIES attempts)
4. On max retries reached: escalate — "Max regeneration attempts reached. Here are the current files. Please edit manually and type 'approved' when ready."

**MAX_REGENERATION_RETRIES = 3** — this matches the ReCode framework's `max_retry: 4` pattern from research, trimmed to 3 for ERP modules where the spec is already well-defined. Beyond 3 attempts, the feedback is likely too ambiguous for the agent to resolve without human intervention.

### Pattern 2: Diff View for REVW-06

Before re-showing a regenerated section, display a unified diff:

```python
# Source: Python stdlib difflib
import difflib

def show_diff(original: str, regenerated: str, filename: str) -> str:
    """Generate a unified diff for display at a checkpoint."""
    original_lines = original.splitlines(keepends=True)
    regen_lines = regenerated.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        regen_lines,
        fromfile=f"original/{filename}",
        tofile=f"regenerated/{filename}",
        n=3,  # 3 lines of context
    )
    return "".join(diff)
```

Display pattern at checkpoint:
```
Changes in models/library_book.py (regenerated based on your feedback):

--- original/library_book.py
+++ regenerated/library_book.py
@@ -45,7 +45,7 @@
     @api.depends('quantity', 'unit_price')
     def _compute_total_amount(self):
         for rec in self:
-            rec.total_amount = rec.quantity * rec.unit_price
+            rec.total_amount = rec.quantity / rec.unit_price if rec.quantity else 0.0

Does this look correct? Type "approved" or describe further changes.
```

**Do NOT** add diff view for the FIRST generation pass (nothing to diff against). Only show diff when regenerating after user feedback.

### Pattern 3: i18n .pot File Generation (QUAL-06)

**Two-path approach:**

**Path A: Docker available** — use `click-odoo-makepot` inside the Docker environment:
```bash
# Inside Docker container (Odoo already installed for validation)
click-odoo-makepot -c /etc/odoo/odoo.conf -d test_db -m MODULE_NAME --addons-dir /mnt/extra-addons
```

**Path B: Docker not available (primary path)** — static agent-driven extraction:

The agent reads all Python and XML files and writes a .pot file following the standard format.

**Extraction sources:**
- Python files: `_()` calls (but NOT selection field labels — these are auto-handled by Odoo's field mechanism)
- XML view files: `string=` attributes on `<button>`, `<form>`, `<group>`, `<page>` elements; text content inside translatable elements
- XML data files: record `name` fields where applicable

**Standard .pot header format:**
```python
# Source: standard gettext PO Template format
pot_header = """\
# Translation Template for {module_name}
# Copyright (C) {year} {author}
# This file is distributed under the same license as the {module_name} package.
#
msgid ""
msgstr ""
"Project-Id-Version: {module_name} {version}\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: {datetime}\\n"
"PO-Revision-Date: {datetime}\\n"
"Last-Translator: Automatically generated\\n"
"Language-Team: none\\n"
"Language: \\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"
"""
```

**Entry format:**
```
#: models/library_book.py:45
msgid "A borrower must be selected."
msgstr ""
```

**Output location:** `{module_name}/i18n/{module_name}.pot`

**Do NOT hand-roll** the .pot file string extraction for Python — use `ast` module to parse `_()` calls properly rather than regex on raw source:

```python
# Source: Python stdlib ast
import ast

def extract_gettext_strings(py_source: str) -> list[str]:
    """Extract _() call arguments from Python source using AST."""
    tree = ast.parse(py_source)
    strings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "_":
                if node.args and isinstance(node.args[0], ast.Constant):
                    strings.append(node.args[0].value)
    return strings
```

### Pattern 4: pylint-odoo Auto-Fix Loop (QUAL-09)

**Mechanically auto-fixable violations (attempt first, no LLM needed):**

| Rule Code | Symbol | What It Is | Mechanical Fix |
|-----------|--------|------------|----------------|
| W8113 | attribute-string-redundant | `string="Field Name"` equals field variable name title-cased | Remove the `string=` parameter |
| W8111 | renamed-field-parameter | Deprecated field param (e.g., `track_visibility`) | Replace with current equivalent (e.g., `tracking`) |
| C8116 | manifest-superfluous-key | Manifest key with default value (e.g., `'installable': True`) | Remove the key |
| W8150 | odoo-addons-relative-import | `from odoo.addons.module.x import y` | Convert to `from .x import y` |
| W8160 | missing-translation | String not wrapped in `_()` — found in raise/UserError/ValidationError | Wrap with `_("...")` |

**LLM-required violations (send to odoo-validator agent):**

| Rule Code | Symbol | Why LLM Required |
|-----------|--------|-----------------|
| E8103 | sql-injection-risk | Requires understanding query context |
| E8135 | write-in-compute | Requires understanding compute method logic |
| W8106 | method-compute | Missing super() call — requires understanding method chain |
| W8138 | except-pass | Empty except block — requires context on what to do instead |
| E8102 | cr-commit | `cr.commit()` call — requires understanding transaction context |
| C8101 | manifest-required-key | Missing required key — requires knowing what value to add |
| C8112 | missing-readme | Missing README file — agent can generate it |

**Auto-fix loop implementation:**

```python
def auto_fix_loop(module_path: Path, max_attempts: int = 2) -> tuple[Violation, ...]:
    """
    Run pylint → mechanical fix → pylint → LLM fix → pylint.
    Returns remaining violations after all fix attempts.
    """
    violations = run_pylint_odoo(module_path)

    for attempt in range(max_attempts):
        if not violations:
            break

        # Attempt 1: mechanical fixes first
        mechanical_fixable = [v for v in violations
                               if v.rule_code in MECHANICAL_FIX_CODES]
        if mechanical_fixable:
            apply_mechanical_fixes(module_path, mechanical_fixable)
            violations = run_pylint_odoo(module_path)

        # Attempt 2: LLM fixes for remaining
        if violations:
            # spawn odoo-validator agent with violations list
            # agent rewrites affected files
            violations = run_pylint_odoo(module_path)

    return violations  # escalate any remaining
```

`MECHANICAL_FIX_CODES = {"W8113", "W8111", "C8116", "W8150", "W8160"}`

### Pattern 5: Docker Auto-Fix Loop (QUAL-10)

**Auto-fixable Docker failure patterns (from existing error_patterns.json + new patterns):**

| Pattern ID | Error Pattern | Auto-Fix Strategy |
|------------|---------------|-------------------|
| `xml-parse-error` | XML syntax error | Parse error message for file+line, agent rewrites that XML file |
| `missing-acl` | No ACL rule for model | Regenerate ir.model.access.csv via Jinja2 renderer |
| `import-error` | Missing import in __init__.py | Add the missing import to __init__.py |
| `view-field-not-found` | Field in view but not in model | Remove field from view OR add field to model |
| `missing-required-field` | Required field has no default | Add `default=False/0/""` to the field definition |

**Non-auto-fixable (escalate immediately):**
- `circular-dependency` — architectural issue requiring human decision
- `module-not-found` — missing dependency in manifest, human must add
- `database-error` (psycopg2 errors) — likely schema corruption, needs clean Docker run
- `constraint-violation` — test data or logic issue requiring human review

**Docker auto-fix loop:**

```
1. Run docker_install_module() → get InstallResult
2. If failed: diagnose_errors(log_output) → classify each error
3. For auto-fixable: spawn odoo-validator agent with error + file context → agent applies fix
4. Re-run docker_install_module() → check again
5. Repeat max 2 times total
6. If still failing: escalate to checkpoint:human-verify with diagnosis summary
```

**Max attempts = 2** for Docker auto-fix. Docker runs take 2-5 minutes each; 2 attempts = up to 10 minutes. Beyond that, user time is better spent reviewing manually.

### Recommended Project Structure Changes

Phase 7 adds to the existing structure:

```
python/src/odoo_gen_utils/
├── validation/
│   ├── auto_fix.py          # NEW: mechanical pylint fixes + auto-fix loop orchestration
│   └── i18n_extractor.py    # NEW: static .pot file extraction (AST + XML parsing)
workflows/
├── generate.md              # MODIFIED: add checkpoint stages between waves
├── generate-with-review.md  # ALTERNATIVE: separate workflow variant with explicit checkpoints
agents/
├── odoo-validator.md        # MODIFIED: expand to handle LLM-based pylint fixes + Docker fixes
```

### Anti-Patterns to Avoid

- **Checkpoint spam:** Do NOT add a checkpoint after every individual file generation. One checkpoint per STAGE (models, views, security+tests) is correct. The anti-pattern in GSD's own docs explicitly warns against "checkpoint after every task."
- **Diff on first generation:** Do NOT show a diff on the first generation pass — there is nothing to diff against. Only show diff when regenerating after user feedback.
- **Blocking regeneration on validation:** Do NOT block the review checkpoint on pylint/Docker validation. Checkpoints are for human content review. Validation (QUAL-06, QUAL-09, QUAL-10) runs AFTER all stages are approved, as a separate quality gate.
- **Infinite retry:** Never loop indefinitely. 3 regeneration retries for human review, 2 for auto-fix loops.
- **Running odoo-bin for .pot generation during offline workflow:** The extension generates code offline. Do not attempt to run odoo-bin outside of Docker context.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Checkpoint UI and user interaction protocol | Custom pause/wait mechanism | GSD `checkpoint:human-verify` task type | Already implemented in execute-plan.md; handles auto-mode, fresh agent spawn, structured display |
| Auto-advance / skip-checkpoint feature | Custom config flag and bypass logic | GSD `workflow.auto_advance = true` in config.json | Already implemented in execute-phase.md checkpoint_handling step |
| Diff generation | Custom diff algorithm | Python stdlib `difflib.unified_diff()` | Battle-tested, no dependency |
| AST parsing for _() extraction | Regex on Python source | Python stdlib `ast.parse()` | Regex fails on multiline strings, comments, nested calls |
| .pot file format | Custom format string | Standard gettext format (write known-correct header + msgid/msgstr entries) | Standard is well-documented and simple to write correctly |
| pylint output parsing | Custom parser | Already built: `parse_pylint_output()` in pylint_runner.py | Phase 3 deliverable, already handles JSON2 format |
| Docker log parsing | Custom log parser | Already built: `parse_install_log()`, `parse_test_log()`, `diagnose_errors()` | Phase 3 deliverables |

**Key insight:** 80% of Phase 7 is wiring — connecting existing GSD mechanisms and existing Python utility functions to the right places in the workflow. New code is only: mechanical pylint fixer, static i18n extractor, and checkpoint placement in generate.md.

---

## Common Pitfalls

### Pitfall 1: Checkpoint Placement in Workflow vs PLAN.md

**What goes wrong:** Developer adds `type="checkpoint:human-verify"` syntax inside generate.md thinking it will work there.

**Why it happens:** The checkpoint syntax is documented for PLAN.md files. generate.md is a workflow document read by the orchestrating agent — it is processed as agent instructions, not as a structured PLAN to execute.

**How to avoid:** Checkpoints in generate.md must be expressed as AGENT INSTRUCTIONS — prose telling the orchestrating agent to "pause and ask the user to review" at this point. The orchestrating agent implements the checkpoint protocol from `checkpoints.md` in its main context (Pattern C). Alternatively, generate.md is refactored to explicitly instruct the agent to use the GSD checkpoint display format at each stage.

**Correct pattern in generate.md:**
```markdown
## Checkpoint: Review Generated Models

Before proceeding to Wave 1, pause and present the following checkpoint to the user:

Display the checkpoint box:
╔══════════════════════════════════════════╗
║  CHECKPOINT: Review Generated Models     ║
╚══════════════════════════════════════════╝

What was built: {list all files from render-module output}

How to verify:
1. Review models/{model_var}.py for field definitions
2. Check that all required fields are present
3. Verify relationships match the spec

YOUR ACTION: Type "approved" or describe what needs to change
```

### Pitfall 2: Re-seeding vs Patching During Regeneration

**What goes wrong:** When user requests changes at a checkpoint, agent tries to patch only the changed section rather than rewriting the full file.

**Why it happens:** Partial patching seems efficient. But Odoo model files have interdependencies (imports, field order, method placement) that break if patched piecemeal.

**How to avoid:** Always rewrite the ENTIRE file when regenerating after feedback — same pattern as odoo-model-gen Phase 5 design decision: "odoo-model-gen uses Write tool to rewrite ENTIRE model file (not patch stubs inline)."

**Warning signs:** Agent uses `Edit` tool with line ranges on a regeneration pass.

### Pitfall 3: click-odoo-makepot Requires Live Database

**What goes wrong:** Plan includes `click-odoo-makepot` as the .pot generation command without accounting for the fact that it requires a running Odoo instance with the module installed.

**Why it happens:** Documentation describes it as a tool for "generating .pot files" without prominently stating the database prerequisite.

**How to avoid:** Use static agent-driven extraction as the primary path. If Docker is available AND the module has already been successfully installed (post-QUAL-04 success), then `click-odoo-makepot` can be run inside the Docker container before teardown. Otherwise, static extraction is the fallback.

**Key distinction:** click-odoo-makepot runs INSIDE the Odoo environment after module install. It cannot run standalone.

### Pitfall 4: pylint Auto-Fix Corrupting Python Files

**What goes wrong:** Mechanical regex-based pylint fixes corrupt Python files — e.g., removing `string=` parameter leaves trailing comma, or removing a parameter in the middle of a multi-line field definition breaks the AST.

**Why it happens:** Regex string replacement on Python source is brittle. Multi-line field definitions with complex indentation require proper AST manipulation.

**How to avoid:** For mechanical fixes, use `ast` module to parse and `astunparse` or `ast.unparse()` (Python 3.9+) to rewrite, OR use simple regex ONLY for single-line cases and fall back to LLM for multi-line. Verify the file parses cleanly after each mechanical fix:

```python
try:
    ast.parse(fixed_source)
except SyntaxError:
    # rollback — revert to original source
    raise
```

**Warning signs:** Mechanical fixer produces new pylint violations it didn't before.

### Pitfall 5: Stale Docker Container Between Auto-Fix Attempts

**What goes wrong:** Auto-fix loop runs Docker install → finds error → fixes file → runs Docker install AGAIN without stopping the first container → port conflict or stale database state causes false failure.

**Why it happens:** `docker_install_module()` already calls `_teardown()` in a `finally` block, but if called twice rapidly, the second `up -d --wait` may race with the first teardown.

**How to avoid:** The existing `_teardown()` + `finally` pattern already handles this correctly. The auto-fix loop simply calls `docker_install_module()` again — each call is fully self-contained. The pitfall is only if someone tries to reuse a running container between attempts. Always use the full `docker_install_module()` call, never try to keep a container warm between fix attempts.

### Pitfall 6: i18n Extraction Missing Field String Translations

**What goes wrong:** The static .pot extraction finds `_()` calls in Python but misses the `string=` parameter of fields (which Odoo auto-translates through its field mechanism).

**Why it happens:** Field string parameters don't use `_()` — they're registered for translation differently by the Odoo framework at model loading time.

**How to avoid:** Accept this limitation for the static extraction path. Document it: "The generated .pot file contains explicit `_()` strings and XML view strings. Field `string=` parameters are automatically translatable by Odoo and appear in the .pot file only when generated via `click-odoo-makepot` with a running Odoo instance." This is acceptable — the .pot file serves as a starting point, not a complete extraction.

---

## Code Examples

Verified patterns from official sources and GSD internals:

### GSD Checkpoint Task Syntax (from checkpoints.md)
```xml
<!-- Source: ~/.claude/get-shit-done/references/checkpoints.md -->
<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Generated Odoo module models — {count} model files with field definitions and method stubs</what-built>
  <how-to-verify>
    Review the following generated files:
    1. models/__init__.py — imports all model modules
    2. models/{model_var}.py per model — field definitions match spec

    Check:
    - All required fields from spec are present
    - Field types match spec (Char, Integer, Many2one, etc.)
    - Computed field stubs have correct @api.depends decorators
  </how-to-verify>
  <resume-signal>Type "approved" or describe what needs to change</resume-signal>
</task>
```

### GSD auto_advance Config Check (from execute-phase.md)
```bash
# Source: ~/.claude/get-shit-done/workflows/execute-phase.md checkpoint_handling step
AUTO_CFG=$(node ~/.claude/get-shit-done/bin/gsd-tools.cjs config-get workflow.auto_advance 2>/dev/null || echo "false")
```
When `AUTO_CFG` is `"true"`, human-verify checkpoints auto-approve. This is the mechanism for REVW-05 (skippable via config).

### Diff Generation (Python stdlib)
```python
# Source: Python stdlib difflib documentation
import difflib
from pathlib import Path

def generate_diff(original_path: Path, regenerated_content: str) -> str:
    """Generate unified diff between original file and regenerated content."""
    original_content = original_path.read_text(encoding="utf-8")
    original_lines = original_content.splitlines(keepends=True)
    regen_lines = regenerated_content.splitlines(keepends=True)

    diff_lines = difflib.unified_diff(
        original_lines,
        regen_lines,
        fromfile=f"original/{original_path.name}",
        tofile=f"regenerated/{original_path.name}",
        n=3,
    )
    return "".join(diff_lines)
```

### AST-based _() String Extraction (Python stdlib)
```python
# Source: Python stdlib ast documentation
import ast
from pathlib import Path

def extract_translatable_strings(py_file: Path) -> list[tuple[str, int]]:
    """Extract all _('...') call string literals with line numbers.

    Returns list of (string, line_number) tuples.
    """
    source = py_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and
                isinstance(node.func, ast.Name) and
                node.func.id == "_" and
                node.args and
                isinstance(node.args[0], ast.Constant) and
                isinstance(node.args[0].value, str)):
            results.append((node.args[0].value, node.lineno))
    return results
```

### XML String Extraction for .pot
```python
# Source: Python stdlib xml.etree.ElementTree
import xml.etree.ElementTree as ET
from pathlib import Path

def extract_xml_translatable_strings(xml_file: Path) -> list[tuple[str, str]]:
    """Extract translatable strings from Odoo view XML files.

    Returns list of (string, source_ref) tuples.
    """
    try:
        tree = ET.parse(xml_file)
    except ET.ParseError:
        return []

    results = []
    # Extract string= attributes from form/button/group/page elements
    TRANSLATABLE_ATTRS = {"string", "placeholder", "confirm", "help", "sum"}
    TRANSLATABLE_TAGS = {"button", "form", "tree", "group", "page", "field", "filter", "separator"}

    for elem in tree.iter():
        if elem.tag in TRANSLATABLE_TAGS:
            for attr in TRANSLATABLE_ATTRS:
                value = elem.get(attr, "")
                if value and not value.startswith("%("):  # skip format strings
                    results.append((value, f"{xml_file.name}"))
    return results
```

### .pot File Writer
```python
# Source: standard gettext PO Template format specification
from datetime import datetime
from pathlib import Path

def write_pot_file(
    module_path: Path,
    strings: list[tuple[str, str, int]],  # (msgid, source_file, line)
    module_name: str,
    author: str = "",
    version: str = "17.0.1.0.0",
) -> Path:
    """Write a .pot file for an Odoo module."""
    pot_dir = module_path / "i18n"
    pot_dir.mkdir(exist_ok=True)
    pot_file = pot_dir / f"{module_name}.pot"

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M+0000")

    lines = [
        f"# Translation Template for {module_name}\n",
        f"# Copyright (C) {datetime.utcnow().year} {author}\n",
        "#\n",
        'msgid ""\n',
        'msgstr ""\n',
        f'"Project-Id-Version: {module_name} {version}\\n"\n',
        '"Report-Msgid-Bugs-To: \\n"\n',
        f'"POT-Creation-Date: {now}\\n"\n',
        f'"PO-Revision-Date: {now}\\n"\n',
        '"Last-Translator: Automatically generated\\n"\n',
        '"Language-Team: none\\n"\n',
        '"Language: \\n"\n',
        '"MIME-Version: 1.0\\n"\n',
        '"Content-Type: text/plain; charset=UTF-8\\n"\n',
        '"Content-Transfer-Encoding: 8bit\\n"\n',
        '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n',
        "\n",
    ]

    seen: set[str] = set()
    for msgid, source_file, lineno in sorted(strings, key=lambda x: x[0]):
        if msgid in seen:
            continue
        seen.add(msgid)
        lines.append(f"#: {source_file}:{lineno}\n")
        escaped = msgid.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'msgid "{escaped}"\n')
        lines.append('msgstr ""\n')
        lines.append("\n")

    pot_file.write_text("".join(lines), encoding="utf-8")
    return pot_file
```

### Mechanical pylint Fix: W8113 (attribute-string-redundant)
```python
# Source: pylint-odoo W8113 rule description
import re

def fix_redundant_string_attr(source: str, violation: Violation) -> str:
    """Remove redundant string= parameter from field declarations.

    W8113: string="Field Name" when it equals title-case of variable name.
    Only fixes single-line cases. Multi-line: fall back to LLM.
    """
    lines = source.splitlines(keepends=True)
    line_idx = violation.line - 1  # 1-indexed to 0-indexed

    # Pattern: string="Any Text", — remove this parameter
    # Only handle single-line cases
    pattern = re.compile(r',?\s*string\s*=\s*["\'][^"\']*["\'],?')
    fixed_line = pattern.sub("", lines[line_idx], count=1)

    # Clean up double commas or trailing comma before closing paren
    fixed_line = re.sub(r',\s*,', ',', fixed_line)
    fixed_line = re.sub(r',\s*\)', ')', fixed_line)

    lines[line_idx] = fixed_line
    return "".join(lines)
```

### Feedback Incorporation Prompt Pattern
```python
# How to re-invoke odoo-model-gen with user feedback
REGENERATION_PROMPT_TEMPLATE = """
Read the file {model_path} and the spec at {spec_path}.
Model to process: {model_name}.

ORIGINAL GENERATION TASK:
{original_task}

USER FEEDBACK FROM REVIEW:
{user_feedback}

Rewrite the ENTIRE model file incorporating the user's feedback.
Preserve all field declarations. Apply only the changes the user described.
Confirm how many changes were made based on the feedback.
"""
```

---

## Odoo-Specific Patterns

### i18n .pot Directory Placement
Per OCA convention and Odoo 17 documentation:
```
{module_name}/
├── i18n/
│   ├── {module_name}.pot   # Template (source strings)
│   ├── fr.po               # French
│   └── es.po               # Spanish
```

The .pot file is listed in `__manifest__.py` `'data'` only if it contains data records. For i18n, the `i18n/` directory is auto-discovered by Odoo — do NOT add .pot to the `'data'` list. This is a common mistake.

### pylint-odoo Auto-Fixable Violations — Definitive List

Based on OCA/pylint-odoo README and OCA/odoo-pre-commit-hooks analysis:

**Mechanical (regex/AST fix, no LLM):**
- W8113 `attribute-string-redundant` — remove `string=` when redundant
- W8111 `renamed-field-parameter` — rename deprecated params (track_visibility → tracking, etc.)
- C8116 `manifest-superfluous-key` — remove manifest keys matching defaults (`installable: True`, `data: []`, `application: False`)
- W8150 `odoo-addons-relative-import` — convert absolute odoo.addons imports to relative

**OCA odoo-pre-commit-hooks auto-fixable (has --fix flag):**
- `field-string-redundant` (same as W8113)
- `manifest-superfluous-key` (same as C8116)
- `po-pretty-format` — sorts and reformats .po/.pot files

**LLM-required (spawn odoo-validator agent):**
- W8160 `missing-translation` — add `_()` wrapping, requires understanding context
- E8103 `sql-injection-risk` — fix SQL query parameterization
- E8135 `write-in-compute` — restructure compute method
- W8106 `method-compute` — add super() call
- W8138 `except-pass` — fill empty except block
- C8112 `missing-readme` — generate README.rst

### Common Odoo Docker Install Failures — Auto-Fixable vs Not

Based on error_patterns.json (Phase 3) and Odoo community analysis:

| Failure | Auto-Fixable? | Fix Strategy |
|---------|--------------|--------------|
| XML parse error (mismatched tag) | YES | Parse error for file+line, rewrite file |
| Missing ACL entry | YES | Regenerate ir.model.access.csv from spec |
| Field not found in view | YES | Remove field from view or add to model |
| Missing __init__.py import | YES | Add import to __init__.py |
| Missing Odoo module dependency | NO | User must add to manifest + Docker image |
| Python package not installed | NO | User must add to requirements.txt + Docker |
| Circular dependency | NO | Requires architectural decision |
| Database constraint violation | NO | Likely test data issue, user must review |
| Timeout during install (>300s) | NO | Performance or Docker issue |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| odoo-bin --i18n-export for .pot | click-odoo-makepot (requires DB) vs static extraction | Always | Static extraction is the offline-capable alternative |
| Manual pylint fix review | Pre-commit hooks with `--fix` flag (OCA/odoo-pre-commit-hooks) | 2023-2024 | OCA pre-commit hooks have autofix for field-string-redundant, manifest-superfluous-key |
| Checkpoint = custom pause logic | GSD `checkpoint:human-verify` task type | Phase 1 of this project | Already implemented, just wire it |
| `@api.one`, `@api.multi` | Removed, iterate `for rec in self:` | Odoo 17.0 | All generated code already follows this |

**Deprecated/outdated:**
- `odoo-bin --i18n-export --language=` (still works but requires running server + DB)
- `xgettext` on Python-only (misses XML view strings — incomplete extraction)
- `pygettext` (Python 2 era, superseded by babel/xgettext)

---

## Open Questions

1. **Checkpoint placement granularity**
   - What we know: GSD warns against checkpoints after every task
   - What's unclear: Should security generation and test generation be one combined checkpoint (Wave 2) or two separate checkpoints?
   - Recommendation: Combine security + tests into one checkpoint — they are reviewed together (does the security match the tests?). That gives 3 checkpoints: (1) after Jinja2 render, (2) after Wave 1 model methods, (3) after Wave 2 views+tests+security.

2. **REVW-05 (skippable) — is auto_advance sufficient or does it need a per-command flag?**
   - What we know: `workflow.auto_advance = true` in config.json bypasses all human-verify checkpoints
   - What's unclear: User may want to skip checkpoints for one specific `/odoo-gen:new` call without changing global config
   - Recommendation: For Phase 7, `auto_advance` is sufficient — it's already the GSD standard. A per-call `--no-review` flag is a Phase 9 polish item.

3. **click-odoo-makepot integration timing**
   - What we know: click-odoo-makepot requires a running Odoo with module installed
   - What's unclear: Should it run BEFORE Docker teardown (after successful QUAL-04 validation), or always use static extraction?
   - Recommendation: Use static extraction always for simplicity. If click-odoo-makepot is desired in future, add it as a post-validation step before teardown in docker_runner.py.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x (existing — Phase 3 infrastructure) |
| Config file | `python/pyproject.toml` (existing) |
| Quick run command | `cd python && python -m pytest tests/ -x -q` |
| Full suite command | `cd python && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REVW-01..04 | Checkpoint placement in generate.md | Manual review | Read generate.md and verify checkpoint instructions present | N/A (workflow doc) |
| REVW-05 | auto_advance bypasses checkpoints | Unit (config parsing) | `pytest tests/test_auto_advance.py -x` | Wave 0 |
| REVW-06 | Feedback incorporated in re-generation | Unit (prompt template) | `pytest tests/test_regeneration_prompt.py -x` | Wave 0 |
| QUAL-06 | .pot file generated with correct format | Unit (i18n_extractor) | `pytest tests/test_i18n_extractor.py -x` | Wave 0 |
| QUAL-09 | pylint auto-fix reduces violations | Unit (auto_fix) | `pytest tests/test_pylint_autofix.py -x` | Wave 0 |
| QUAL-10 | Docker auto-fix re-validates | Integration (mock Docker) | `pytest tests/test_docker_autofix.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd python && python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `python/tests/test_i18n_extractor.py` — covers QUAL-06 (AST extraction, XML extraction, .pot format)
- [ ] `python/tests/test_pylint_autofix.py` — covers QUAL-09 (W8113/W8111/C8116/W8150 mechanical fixes)
- [ ] `python/tests/test_docker_autofix.py` — covers QUAL-10 (auto-fix loop with mock docker_install_module)
- [ ] `python/tests/test_auto_advance.py` — covers REVW-05 (config flag behavior)
- [ ] `python/tests/test_regeneration_prompt.py` — covers REVW-06 (prompt template construction)

---

## Sources

### Primary (HIGH confidence)
- GSD source: `/home/inshal-rauf/get-shit-done/get-shit-done/references/checkpoints.md` — full checkpoint protocol, task types, display format
- GSD source: `/home/inshal-rauf/get-shit-done/get-shit-done/workflows/execute-phase.md` — checkpoint_handling step, auto_advance behavior
- GSD source: `/home/inshal-rauf/get-shit-done/get-shit-done/workflows/execute-plan.md` — checkpoint_protocol step, Pattern A/B/C routing
- Project source: `/home/inshal-rauf/Odoo_module_automation/workflows/generate.md` — current pipeline structure
- Project source: `/home/inshal-rauf/Odoo_module_automation/python/src/odoo_gen_utils/validation/pylint_runner.py` — existing pylint infrastructure
- Project source: `/home/inshal-rauf/Odoo_module_automation/python/src/odoo_gen_utils/validation/docker_runner.py` — Docker runner with teardown guarantees
- Project source: `/home/inshal-rauf/Odoo_module_automation/python/src/odoo_gen_utils/validation/error_patterns.json` — existing error classification
- Project source: `/home/inshal-rauf/Odoo_module_automation/knowledge/i18n.md` — i18n rules including .pot generation guidance
- Python stdlib: `difflib.unified_diff` — official documentation
- Python stdlib: `ast.parse`, `ast.walk` — official documentation

### Secondary (MEDIUM confidence)
- WebFetch: https://github.com/OCA/odoo-pre-commit-hooks — auto-fixable checks confirmed: field-string-redundant, manifest-superfluous-key, po-pretty-format
- WebFetch: https://github.com/acsone/click-odoo-contrib — click-odoo-makepot confirmed requires database; confirmed CLI options
- WebSearch + multiple sources: pylint-odoo W8113, W8111, C8116, W8150 confirmed as mechanical-fixable

### Tertiary (LOW confidence — needs validation)
- ReCode framework `max_retry: 4` parameter — used as reference for retry limit recommendation (set to 3 for this project)
- OCA pre-commit hooks `oca-checks-odoo-module --fix` flag — confirmed existence, specific W8xxx codes need validation against current version

---

## Metadata

**Confidence breakdown:**
- GSD checkpoint mechanism: HIGH — read source directly
- i18n .pot approach (static extraction): MEDIUM — no official Odoo static extractor exists, pattern derived from knowledge
- pylint auto-fixable violations list: MEDIUM — confirmed from OCA pre-commit-hooks source + pylint-odoo README analysis
- Docker auto-fix patterns: MEDIUM — derived from existing error_patterns.json + Odoo community
- Max retry limits: LOW — industry convention (3-5 retries) supported by ReCode paper reference

**Research date:** 2026-03-02
**Valid until:** 2026-06-01 (90 days — pylint-odoo and GSD are stable; OCA pre-commit hooks evolve faster)
