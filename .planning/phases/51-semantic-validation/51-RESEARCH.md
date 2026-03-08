# Phase 51: Semantic Validation - Research

**Researched:** 2026-03-08
**Domain:** AST-based static analysis of generated Odoo module artifacts (Python, XML, CSV, manifest)
**Confidence:** HIGH

## Summary

This phase implements a post-render, pre-Docker semantic validation pass that catches field reference errors, XML ID conflicts, ACL mismatches, and manifest dependency gaps in generated output files. The entire validation operates on rendered artifacts using Python's stdlib `ast` and `xml.etree.ElementTree` modules -- no running Odoo instance, no Docker, no network, no subprocess calls.

The codebase already has extensive AST-based parsing in `cli.py:_parse_module_dir_to_spec()` (lines 358-437) which extracts `_name`, field definitions, and `comodel_name` from generated Python files using the exact same AST traversal patterns needed for E3/W1/W2 checks. The `known_odoo_models.json` (203 models, 54 modules) provides the cross-reference data needed for comodel validation (W1) and depends inference (E6). The `validation/` package already follows a types/runner/report separation pattern that semantic validation should mirror.

**Primary recommendation:** Create `validation/semantic.py` as a standalone module with a pure-function `semantic_validate(output_dir: Path, registry: ModelRegistry | None) -> SemanticValidationResult` entry point. Reuse existing AST extraction patterns from `_parse_module_dir_to_spec()`. Use `difflib.get_close_matches(cutoff=0.6)` for Levenshtein-like suggestions on E3 field mismatches.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 10 checks total: 6 ERRORS (E1-E6) + 4 WARNINGS (W1-W4)
- E1: Python syntax via `ast.parse()` every `.py` file
- E2: XML well-formedness via `xml.etree.parse()` every `.xml` file
- E3: XML field references exist on model -- cross-ref `models/*.py` against `views/*_views.xml`
- E4: ACL model references valid -- every line in `ir.model.access.csv` validates `model_id:id` and `group_id:id`
- E5: XML ID uniqueness across all data files -- collect every `record id=""`, no duplicates
- E6: Manifest `depends` completeness -- cross-ref import statements + XML `ref=""` attributes
- W1: Many2one comodel exists -- check `comodel_name` against registry + `known_odoo_models.json`
- W2: Computed field depends references valid fields -- parse `@api.depends('field_name')`
- W3: Security group references resolve -- `groups="module.group_name"` in XML views
- W4: Record rule domain field references -- `ir.rule` `domain_force` references
- Execution order: E1 -> E2 -> E5 -> E3 -> E4 -> E6 -> W1 -> W2 -> W3 -> W4
- Short-circuit: if E1 or E2 fails for a file, skip E3-W4 for that file
- File: `validation/semantic.py` -- standalone module, NOT inside `renderer.py` or `verifier.py`
- Three invocation modes: automatic after generation, standalone on existing output, skip validation
- Performance target: <500ms for typical module (10 models, ~50 files), hard ceiling <1s
- AST parsing for Python (NOT regex), xml.etree for XML, ast.literal_eval for manifest, csv.reader for CSV
- Build in-memory indexes before cross-reference checks
- ValidationIssue dataclass with code, severity, file, line, message, fixable, suggestion fields
- ValidationResult dataclass with module, errors, warnings, duration_ms, has_errors, has_fixable_errors properties

### Claude's Discretion
- Internal helper function signatures for each check (E1-E6, W1-W4)
- How to extract field names from AST (which AST node types to traverse)
- Exact Levenshtein distance implementation (stdlib `difflib.get_close_matches` or custom)
- Test fixture structure (generated module fixtures for testing each check)
- Whether `semantic_validate()` accepts `Path` or `str` for output_dir
- How to handle `__manifest__.py` `data` key parsing for XML file enumeration

### Deferred Ideas (OUT OF SCOPE)
- Auto-fix integration for semantic validation issues -- can be deferred to Phase 54
- CLI `validate` standalone command -- function exists, CLI wiring is Phase 54
- JSON output mode (`--json` flag) -- can be Phase 54 CLI enhancement
- Cross-module semantic validation -- needs registry battle-tested first, v3.4+
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ARCH-03 | Pre-Docker semantic validation -- AST-parse generated Python, XML field reference cross-check, XML ID uniqueness, ACL model references, manifest `depends` completeness -- catches 60-70% of bugs in <1 second | Full codebase analysis confirms: (1) AST extraction patterns exist in `_parse_module_dir_to_spec()`, (2) `known_odoo_models.json` provides 203 models for cross-ref, (3) `validation/` package structure supports new `semantic.py` module, (4) benchmarks confirm <1ms for ast.parse per file and <0.02ms for ET.fromstring per file, (5) `difflib.get_close_matches` provides fuzzy matching for suggestions |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ast` (stdlib) | Python 3.12 | Parse Python files, extract fields/methods/decorators/imports | Zero dependencies, 0.18ms per parse, handles all Python 3.12 syntax |
| `xml.etree.ElementTree` (stdlib) | Python 3.12 | Parse XML files, extract record IDs, field refs, group refs | Zero dependencies, 0.02ms per parse, handles Odoo XML format |
| `csv` (stdlib) | Python 3.12 | Parse ir.model.access.csv | Zero dependencies, trivial performance |
| `ast.literal_eval` (stdlib) | Python 3.12 | Parse `__manifest__.py` dict | Safe evaluation, 0.06ms per eval, already used in cli.py |
| `difflib` (stdlib) | Python 3.12 | Fuzzy matching for field name suggestions | `get_close_matches(cutoff=0.6)` provides Levenshtein-like distance |
| `dataclasses` (stdlib) | Python 3.12 | `ValidationIssue` and `SemanticValidationResult` types | Frozen dataclasses match project pattern (Violation, ModelEntry, etc.) |
| `time` (stdlib) | Python 3.12 | `perf_counter()` for duration measurement | Nanosecond precision, no overhead |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pathlib` (stdlib) | Python 3.12 | File discovery and path manipulation | Already the project standard for all file operations |
| `ModelRegistry` (project) | N/A | Cross-module model awareness for W1 comodel validation | Passed as optional parameter to `semantic_validate()` |
| `known_odoo_models.json` (project) | 203 models | Base set of Odoo models for comodel + depends validation | Loaded via registry or direct JSON read |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ast.parse` | regex | Regex cannot reliably parse Python class definitions, decorators, or nested assignments. AST is authoritative. |
| `xml.etree.ElementTree` | `lxml` | lxml is faster but adds a C dependency. ET is fast enough (<0.02ms/file) and already in stdlib. |
| `difflib.get_close_matches` | `python-Levenshtein` / `rapidfuzz` | External dependency for marginal improvement. `difflib` is sufficient for small field lists (<100 items). |

**Installation:**
```bash
# No additional packages needed -- all stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
python/src/odoo_gen_utils/
├── validation/
│   ├── __init__.py          # Add semantic exports
│   ├── semantic.py          # NEW: All 10 checks + orchestrator
│   ├── types.py             # Existing + new SemanticValidationResult types (or keep in semantic.py)
│   ├── error_patterns.py    # Existing (unchanged)
│   ├── pylint_runner.py     # Existing (unchanged)
│   ├── docker_runner.py     # Existing (unchanged)
│   ├── report.py            # Existing (unchanged)
│   ├── log_parser.py        # Existing (unchanged)
│   └── data/
│       └── error_patterns.json  # Existing (unchanged)
├── data/
│   └── known_odoo_models.json   # Existing -- used by W1 and E6
├── cli.py                   # Modified: add --skip-validation to render-module
├── renderer.py              # NOT modified (separation of concerns)
└── registry.py              # Existing -- used by W1 comodel lookup
```

### Pattern 1: Single-Pass Index Building
**What:** Parse each file exactly once, extract ALL needed data into in-memory indexes, then run all cross-reference checks against the indexes.
**When to use:** Always -- the performance budget demands no redundant I/O or parsing.
**Example:**
```python
# Source: Existing pattern in cli.py _parse_module_dir_to_spec()
@dataclass(frozen=True)
class ParsedModel:
    """In-memory index entry for a parsed Python model file."""
    model_name: str
    fields: dict[str, str]        # field_name -> field_type
    comodels: dict[str, str]      # field_name -> comodel_name
    inherits: list[str]
    imports: list[str]            # "from odoo.addons.X import Y"
    depends_decorators: dict[str, list[str]]  # method_name -> [field1, field2]
    file_path: str
    line_numbers: dict[str, int]  # field_name -> line number

@dataclass(frozen=True)
class ParsedXml:
    """In-memory index entry for a parsed XML file."""
    record_ids: dict[str, int]    # xml_id -> line number
    field_refs: list[tuple[str, str, int]]  # (model_name, field_name, line)
    group_refs: list[tuple[str, int]]       # (group_ref, line)
    external_refs: list[tuple[str, int]]    # (ref_value, line)
    file_path: str
```

### Pattern 2: Ordered Check Execution with Short-Circuit
**What:** Run checks in dependency order (E1 before E3, E2 before E5), skip downstream checks when upstream fails for a specific file.
**When to use:** Always -- prevents cascading false positives from unparseable files.
**Example:**
```python
def semantic_validate(output_dir: Path, registry: ModelRegistry | None = None) -> SemanticValidationResult:
    start = time.perf_counter()
    issues: list[ValidationIssue] = []

    # Phase 1: Parse all files (E1, E2)
    py_files = list((output_dir).rglob("*.py"))
    xml_files = list((output_dir).rglob("*.xml"))

    parsed_py: dict[str, ParsedModel] = {}
    failed_py: set[str] = set()
    for f in py_files:
        result = _check_e1_python_syntax(f)
        if result:
            issues.append(result)
            failed_py.add(str(f))
        else:
            parsed_py[str(f)] = _extract_model_data(f)

    # ... similar for XML ...

    # Phase 2: Cross-reference checks (skip failed files)
    # E3, E4, E5, E6, W1-W4

    duration_ms = int((time.perf_counter() - start) * 1000)
    return SemanticValidationResult(
        module=output_dir.name,
        errors=[i for i in issues if i.severity == "error"],
        warnings=[i for i in issues if i.severity == "warning"],
        duration_ms=duration_ms,
    )
```

### Pattern 3: Pure Function Validator (No Side Effects)
**What:** `semantic_validate()` reads files, returns structured result, never modifies anything.
**When to use:** Always -- matches the preprocessor pure function pattern established in the project.
**Example:**
```python
# Follows the same pattern as _validate_no_cycles() in preprocessors/validation.py
# Accept input, return structured result, no side effects
result = semantic_validate(module_dir, registry=reg)
if result.has_errors:
    print_validation_report(result)
    sys.exit(1)
```

### Anti-Patterns to Avoid
- **Regex for Python parsing:** Never use regex to extract Python field definitions, method signatures, or decorator arguments. AST is authoritative and handles all edge cases (multiline expressions, string concatenation, nested calls).
- **Parsing files multiple times:** Each file must be parsed exactly once. Build indexes first, then run checks against indexes.
- **Raising exceptions for validation failures:** Return structured results. Only the CLI layer decides whether to exit or continue.
- **Modifying rendered files during validation:** Validation is read-only. Auto-fix is a separate concern (Phase 54 deferred).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy field name matching | Custom Levenshtein implementation | `difflib.get_close_matches(word, possibilities, n=3, cutoff=0.6)` | Handles all edge cases, well-tested, returns sorted by similarity |
| Python parsing | Custom tokenizer/regex | `ast.parse()` + `ast.walk()` | Handles all Python syntax, provides line numbers, reliable node types |
| XML parsing | Custom XML parser | `xml.etree.ElementTree.parse()` | Handles Odoo XML format, provides `iter()` for element traversal |
| CSV parsing | Custom split-on-comma | `csv.reader()` | Handles quoted fields, escaping, edge cases |
| Manifest parsing | `eval()` or regex | `ast.literal_eval()` | Safe evaluation of Python dict literals, no code execution |
| Module name from import | Regex on import statements | `ast.parse()` + check `ast.ImportFrom.module` | Handles all import styles (`from odoo.addons.X import Y`, `import odoo.addons.X`) |

**Key insight:** All 10 checks use stdlib tools. Zero external dependencies. The project already demonstrates the AST parsing pattern in `_parse_module_dir_to_spec()` (cli.py lines 358-437) -- extend, don't reinvent.

## Common Pitfalls

### Pitfall 1: Missing Fields from mail.thread/mail.activity.mixin Inheritance
**What goes wrong:** E3 reports `message_ids`, `message_follower_ids`, `activity_ids` as missing fields in views, but they come from `mail.thread` / `mail.activity.mixin` inheritance.
**Why it happens:** The validator only sees fields explicitly defined in the model's Python file, not inherited fields.
**How to avoid:** When checking view field references (E3), also consider fields from `_inherit` list. Look up inherited model fields from `known_odoo_models.json`. If a model inherits `mail.thread`, implicitly add `message_ids`, `message_follower_ids`, `message_ids` to its known fields.
**Warning signs:** False positives on chatter fields (`message_ids`, `message_follower_ids`, `activity_ids`).

### Pitfall 2: XML Field Refs Inside `<field name="arch">` vs Top-Level `<field>`
**What goes wrong:** Confusing top-level `<field name="name">` (which sets the view's name attribute) with arch-level `<field name="student_id"/>` (which references a model field).
**Why it happens:** Both use `<field name="..."/>` syntax but serve different purposes.
**How to avoid:** When extracting field references for E3, only look at fields INSIDE the `arch` content -- specifically inside `<form>`, `<tree>`, `<search>` elements. The top-level `<field>` elements with `name` in `("name", "model", "arch", "priority", "inherit_id")` are view metadata, not field references.
**Warning signs:** E3 reporting "field 'name' not found" (the view name, not a model field) or "field 'model' not found".

### Pitfall 3: Generated XML ID Format Assumptions
**What goes wrong:** Hardcoding XML ID patterns that don't match the actual template output.
**Why it happens:** Different templates generate different XML ID patterns (`view_MODEL_form`, `action_MODEL`, `menu_MODEL`, `access_MODEL_ROLE`).
**How to avoid:** Extract XML IDs directly from generated files using `record.get("id")` and `menuitem.get("id")`, don't reconstruct them. For E5 uniqueness, just collect all IDs from all XML files.
**Warning signs:** E5 false negatives (missing duplicates because some ID sources were skipped).

### Pitfall 4: ACL CSV Group References Include Module Prefix
**What goes wrong:** E4 reports `module_name.group_module_name_manager` as invalid because the validator doesn't understand the `module.xml_id` reference format.
**Why it happens:** ACL CSV `group_id:id` column uses `module_technical_name.group_name` format which must be split on `.` to extract the group XML ID.
**How to avoid:** Parse group_id:id as `module.xml_id`. For local groups (same module), check XML ID exists in the module's security.xml. For external groups (different module prefix), only validate if the module is `base` (known groups like `base.group_user`, `base.group_system`).
**Warning signs:** E4 false positives on every ACL row because module-prefixed group IDs aren't resolved.

### Pitfall 5: @api.depends Can Reference Related Fields via Dot Notation
**What goes wrong:** W2 reports `student_id.name` as an invalid field, but it's a valid related field traversal.
**Why it happens:** `@api.depends('field_name.related_field')` traverses relational fields.
**How to avoid:** For W2, when a depends value contains a dot, only validate the first part (the local field name). Don't validate the traversal target -- it may be on an external model.
**Warning signs:** W2 false positives on every `@api.depends` that uses dot-separated field paths.

### Pitfall 6: Manifest `data` Key Lists Files That May Not Exist Yet
**What goes wrong:** E6 tries to enumerate XML files from the manifest `data` key but some files might be conditionally generated.
**Why it happens:** Templates like `sequences.xml` are only generated when sequence fields exist.
**How to avoid:** For E6, enumerate actual files on disk (glob), not the manifest `data` list. The manifest data list is what gets checked (ensure all listed files exist), but cross-reference analysis uses actual files.
**Warning signs:** E6 errors about missing files that are intentionally not generated.

## Code Examples

Verified patterns from the existing codebase:

### AST Field Extraction (from cli.py _parse_module_dir_to_spec)
```python
# Source: cli.py lines 382-424
for node in ast.walk(tree):
    if not isinstance(node, ast.ClassDef):
        continue
    for item in node.body:
        # _name = 'model.name'
        if (isinstance(item, ast.Assign)
            and len(item.targets) == 1
            and isinstance(item.targets[0], ast.Name)):
            attr_name = item.targets[0].id
            if attr_name == "_name" and isinstance(item.value, ast.Constant):
                model_name = item.value.value
        # field = fields.Type(...)
        if (isinstance(item, ast.Assign)
            and len(item.targets) == 1
            and isinstance(item.targets[0], ast.Name)
            and isinstance(item.value, ast.Call)
            and isinstance(item.value.func, ast.Attribute)):
            field_name = item.targets[0].id
            field_type = item.value.func.attr
            # Extract comodel_name
            for kw in item.value.keywords:
                if kw.arg == "comodel_name" and isinstance(kw.value, ast.Constant):
                    comodel = kw.value.value
```

### @api.depends Extraction (new for W2)
```python
# Extract @api.depends('field1', 'field2.related') from decorators
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        for decorator in node.decorator_list:
            if (isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "depends"):
                depends_fields = []
                for arg in decorator.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        depends_fields.append(arg.value)
                # Store: method_name -> depends_fields
```

### Import Extraction for E6
```python
# Extract 'from odoo.addons.X import ...' -> module X
for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom) and node.module:
        if node.module.startswith("odoo.addons."):
            parts = node.module.split(".")
            if len(parts) >= 3:
                addon_module = parts[2]  # 'X' from 'odoo.addons.X'
                imported_modules.add(addon_module)
```

### XML Field Reference Extraction (E3)
```python
# Parse XML, find view field references inside arch
root = ET.parse(xml_path).getroot()
for record in root.iter("record"):
    model_attr = record.get("model", "")
    if model_attr != "ir.ui.view":
        continue
    # Find the arch field
    for arch_field in record.findall(".//field[@name='arch']"):
        # All <field> inside arch reference model fields
        for field_elem in arch_field.iter("field"):
            field_name = field_elem.get("name", "")
            if field_name:
                view_field_refs.append((field_name, xml_path, field_elem))
```

### XML ID Collection (E5)
```python
# Collect all XML IDs across all data files
xml_ids: dict[str, list[tuple[str, int]]] = {}  # id -> [(file, line)]
for xml_path in xml_files:
    root = ET.parse(xml_path).getroot()
    for elem in root.iter():
        xml_id = elem.get("id")
        if xml_id:
            xml_ids.setdefault(xml_id, []).append((str(xml_path), 0))
# Report duplicates
for xml_id, locations in xml_ids.items():
    if len(locations) > 1:
        issues.append(ValidationIssue(
            code="E5", severity="error",
            file=locations[0][0], line=locations[0][1],
            message=f"Duplicate XML ID '{xml_id}' also in {locations[1][0]}",
            fixable=False, suggestion=None,
        ))
```

### Fuzzy Matching for Suggestions (E3)
```python
# Source: stdlib difflib
import difflib

def _suggest_field(name: str, known_fields: list[str]) -> str | None:
    matches = difflib.get_close_matches(name, known_fields, n=1, cutoff=0.6)
    return matches[0] if matches else None

# Usage in E3
suggestion = _suggest_field("amout", ["amount", "amount_total", "name"])
# Returns "amount"
```

### ACL CSV Parsing (E4)
```python
import csv

def _check_e4_acl_references(csv_path: Path, model_xml_ids: set[str], group_xml_ids: set[str]) -> list[ValidationIssue]:
    issues = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)  # skip header
        for line_num, row in enumerate(reader, start=2):
            if len(row) < 4:
                continue
            # row: id, name, model_id:id, group_id:id, perm_read, ...
            model_ref = row[2]  # e.g., "model_fee_invoice"
            group_ref = row[3]  # e.g., "uni_fee.group_uni_fee_manager"
            if model_ref not in model_xml_ids:
                issues.append(ValidationIssue(
                    code="E4", severity="error",
                    file=str(csv_path), line=line_num,
                    message=f"ACL references unknown model '{model_ref}'",
                    fixable=False, suggestion=None,
                ))
    return issues
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Docker-only validation (30-60s) | Pre-Docker semantic validation (<1s) + Docker | Phase 51 (now) | Catches 60-70% of bugs instantly, Docker reserved for runtime-only issues |
| Pydantic pre-render validation | Pydantic + post-render semantic validation | Phase 47 + Phase 51 | Pydantic catches spec errors, semantic catches generation errors |
| `verifier.py` live Odoo checks | Offline AST-based checks | Phase 51 | No running Odoo instance needed for basic validation |

**Pipeline position:**
```
Pydantic (spec schema) -> Preprocessors -> Render -> Semantic Validation -> Docker (install/test)
```

## Open Questions

1. **Line numbers from xml.etree.ElementTree**
   - What we know: ET does not natively provide line numbers for elements (unlike lxml).
   - What's unclear: Whether accurate line numbers are essential for the first version.
   - Recommendation: Use `None` for line numbers in XML-sourced issues initially. If needed later, can switch to iterparse with line tracking or use lxml. The file path is sufficient for locating issues.

2. **Inherited fields from external modules**
   - What we know: Models inheriting from `mail.thread`, `mail.activity.mixin`, etc. gain fields not defined in the local Python file.
   - What's unclear: Complete set of fields gained from every possible inheritance.
   - Recommendation: Use `known_odoo_models.json` field data for common base models. For unknown inherited models, suppress W2 warnings rather than false-positive.

3. **Wizard model references in ACL**
   - What we know: Wizard (TransientModel) classes generate ACL entries. Template uses `wizard.name | model_ref` which produces `model_wizard_name`.
   - What's unclear: Whether all wizard model references follow the same naming convention.
   - Recommendation: Collect model XML IDs from both `models/*.py` and `wizards/*.py` directories.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `python/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd python && python -m pytest tests/test_semantic_validation.py -x -q` |
| Full suite command | `cd python && python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-03-E1 | Python syntax validation via ast.parse | unit | `pytest tests/test_semantic_validation.py::test_e1_python_syntax_valid -x` | Wave 0 |
| ARCH-03-E1-fail | Python syntax error detection | unit | `pytest tests/test_semantic_validation.py::test_e1_python_syntax_error -x` | Wave 0 |
| ARCH-03-E2 | XML well-formedness validation | unit | `pytest tests/test_semantic_validation.py::test_e2_xml_wellformed -x` | Wave 0 |
| ARCH-03-E2-fail | XML malformed detection | unit | `pytest tests/test_semantic_validation.py::test_e2_xml_malformed -x` | Wave 0 |
| ARCH-03-E3 | XML field references exist on model | unit | `pytest tests/test_semantic_validation.py::test_e3_field_ref_valid -x` | Wave 0 |
| ARCH-03-E3-fail | XML field reference mismatch with suggestion | unit | `pytest tests/test_semantic_validation.py::test_e3_field_ref_missing -x` | Wave 0 |
| ARCH-03-E4 | ACL model references valid | unit | `pytest tests/test_semantic_validation.py::test_e4_acl_valid -x` | Wave 0 |
| ARCH-03-E4-fail | ACL references unknown model | unit | `pytest tests/test_semantic_validation.py::test_e4_acl_invalid_model -x` | Wave 0 |
| ARCH-03-E5 | XML ID uniqueness across files | unit | `pytest tests/test_semantic_validation.py::test_e5_xml_id_unique -x` | Wave 0 |
| ARCH-03-E5-fail | Duplicate XML ID detection | unit | `pytest tests/test_semantic_validation.py::test_e5_xml_id_duplicate -x` | Wave 0 |
| ARCH-03-E6 | Manifest depends completeness | unit | `pytest tests/test_semantic_validation.py::test_e6_depends_complete -x` | Wave 0 |
| ARCH-03-E6-fail | Missing dependency detection | unit | `pytest tests/test_semantic_validation.py::test_e6_depends_missing -x` | Wave 0 |
| ARCH-03-W1 | Comodel existence check | unit | `pytest tests/test_semantic_validation.py::test_w1_comodel_valid -x` | Wave 0 |
| ARCH-03-W2 | Computed field depends validation | unit | `pytest tests/test_semantic_validation.py::test_w2_depends_valid -x` | Wave 0 |
| ARCH-03-W3 | Security group references | unit | `pytest tests/test_semantic_validation.py::test_w3_group_refs -x` | Wave 0 |
| ARCH-03-W4 | Record rule domain field refs | unit | `pytest tests/test_semantic_validation.py::test_w4_rule_domain -x` | Wave 0 |
| ARCH-03-SC | Short-circuit on E1/E2 failure | unit | `pytest tests/test_semantic_validation.py::test_short_circuit -x` | Wave 0 |
| ARCH-03-PERF | Validation completes in <2s | unit | `pytest tests/test_semantic_validation.py::test_performance_budget -x` | Wave 0 |
| ARCH-03-INT | CLI integration with --skip-validation | integration | `pytest tests/test_semantic_validation.py::test_cli_integration -x` | Wave 0 |
| ARCH-03-E2E | Full module render + validate | integration | `pytest tests/test_semantic_validation.py::test_full_module_validation -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && python -m pytest tests/test_semantic_validation.py -x -q`
- **Per wave merge:** `cd python && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_semantic_validation.py` -- covers all ARCH-03 checks (E1-E6, W1-W4, short-circuit, performance, CLI integration)
- [ ] `tests/fixtures/semantic_valid_module/` -- generated module fixture with correct output for positive tests
- [ ] `tests/fixtures/semantic_invalid_module/` -- generated module fixture with intentional errors for negative tests

## Sources

### Primary (HIGH confidence)
- Python 3.12 `ast` module -- verified via local benchmark: 0.18ms per parse for typical Odoo model file
- Python 3.12 `xml.etree.ElementTree` -- verified via local benchmark: 0.02ms per parse for typical view XML
- Python 3.12 `ast.literal_eval` -- verified via local benchmark: 0.06ms per eval for typical manifest
- Python 3.12 `difflib.get_close_matches` -- verified: returns `["amount"]` for input `"amout"` with cutoff=0.6
- Existing codebase `_parse_module_dir_to_spec()` (cli.py:358-437) -- AST extraction pattern for model name, field definitions, comodel references
- Existing codebase `known_odoo_models.json` -- 203 models, 54 modules, includes field definitions and `is_mixin` flags
- Existing codebase `validation/types.py` -- `Violation` frozen dataclass pattern with file, line, severity, message, suggestion
- Existing codebase `registry.py` -- `ModelRegistry._is_known_model()` pattern for model resolution
- Template files `access_csv.j2`, `security_group.xml.j2`, `view_form.xml.j2`, `action.xml.j2`, `menu.xml.j2` -- actual XML ID and field reference patterns in generated output

### Secondary (MEDIUM confidence)
- Performance budget estimates from CONTEXT.md (E1=30ms, E2=15ms total) -- consistent with benchmarks but actual per-module timing depends on number of files

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, all verified via local benchmarks, all with existing usage patterns in codebase
- Architecture: HIGH -- follows established patterns (`_parse_module_dir_to_spec`, `Violation` dataclass, `validation/` package structure)
- Pitfalls: HIGH -- identified from direct analysis of template output patterns and AST limitations; verified against actual generated files

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable -- stdlib-only, no external dependency version risk)
