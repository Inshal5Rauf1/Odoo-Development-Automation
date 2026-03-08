"""Semantic validation for generated Odoo modules.

Catches field reference errors, XML ID conflicts, ACL mismatches, and
manifest dependency gaps in rendered output files -- eliminating the
Docker round-trip for the majority of generation bugs.

10 checks total:
  ERRORS (E1-E6) -- generation is broken, will fail at install
  WARNINGS (W1-W4) -- might be wrong, might be intentional

All stdlib: ast, xml.etree, csv, difflib, dataclasses, time, pathlib.
"""

from __future__ import annotations

import ast
import csv
import difflib
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from odoo_gen_utils.registry import ModelRegistry


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationIssue:
    """A single semantic validation issue."""

    code: str  # "E1", "W3", etc.
    severity: str  # "error" or "warning"
    file: str  # relative path inside module
    line: int | None  # line number if available
    message: str  # human-readable description
    fixable: bool = False  # can auto_fix handle this?
    suggestion: str | None = None  # e.g., "Did you mean 'amount'?"


@dataclass
class SemanticValidationResult:
    """Aggregated validation output from ``semantic_validate()``."""

    module: str
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    duration_ms: int = 0

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_fixable_errors(self) -> bool:
        return any(issue.fixable for issue in self.errors)


# ---------------------------------------------------------------------------
# Internal index types (mutable, used only during validation)
# ---------------------------------------------------------------------------


@dataclass
class _ParsedModel:
    model_name: str
    fields: dict[str, dict[str, Any]]  # field_name -> {type, comodel_name, ...}
    comodels: list[str]
    inherits: list[str]
    imports: list[str]  # odoo.addons.X module names
    depends_decorators: list[tuple[str, list[str]]]  # (method, [field_names])
    file_path: str
    line_numbers: dict[str, int] = field(default_factory=dict)


@dataclass
class _ParsedXml:
    record_ids: dict[str, int]  # xml_id -> line
    field_refs: list[tuple[str, str, int]]  # (model, field_name, line)
    group_refs: list[tuple[str, int]]  # (group_ref, line)
    external_refs: list[str]  # module.xml_id
    rule_domains: list[tuple[str, str, int]]  # (model_xml_id, domain_str, line)
    file_path: str


# ---------------------------------------------------------------------------
# Known Odoo data
# ---------------------------------------------------------------------------

_KNOWN_MODELS_CACHE: dict[str, Any] | None = None
_KNOWN_GROUPS: frozenset[str] = frozenset({
    "base.group_user", "base.group_public", "base.group_portal",
    "base.group_system", "base.group_no_one", "base.group_erp_manager",
    "base.group_multi_company", "base.group_multi_currency",
    "account.group_account_manager", "account.group_account_invoice",
    "account.group_account_user", "account.group_account_readonly",
    "sale.group_sale_manager", "sale.group_sale_salesman",
    "purchase.group_purchase_manager", "purchase.group_purchase_user",
    "stock.group_stock_manager", "stock.group_stock_user",
    "hr.group_hr_manager", "hr.group_hr_user",
})

# View metadata field names -- NOT model fields, should not trigger E3
_VIEW_META_FIELDS: frozenset[str] = frozenset({
    "name", "model", "arch", "priority", "inherit_id", "type",
    "groups_id", "active", "sequence",
})


def _load_known_models() -> dict[str, Any]:
    """Load and cache known_odoo_models.json."""
    global _KNOWN_MODELS_CACHE  # noqa: PLW0603
    if _KNOWN_MODELS_CACHE is not None:
        return _KNOWN_MODELS_CACHE
    data_path = Path(__file__).resolve().parent.parent / "data" / "known_odoo_models.json"
    if data_path.exists():
        data = json.loads(data_path.read_text(encoding="utf-8"))
        _KNOWN_MODELS_CACHE = data.get("models", {})
    else:
        _KNOWN_MODELS_CACHE = {}
    return _KNOWN_MODELS_CACHE


def _get_inherited_fields(
    inherits: list[str],
    known_models: dict[str, Any],
    module_models: dict[str, _ParsedModel],
) -> dict[str, dict[str, Any]]:
    """Collect fields from _inherit parents via known models and module models."""
    inherited: dict[str, dict[str, Any]] = {}
    for parent in inherits:
        known = known_models.get(parent)
        if known and "fields" in known:
            for fname, fdef in known["fields"].items():
                inherited[fname] = fdef
        parsed = module_models.get(parent)
        if parsed:
            for fname, fdef in parsed.fields.items():
                inherited[fname] = fdef
    return inherited


# ---------------------------------------------------------------------------
# Parsers (single-pass for each file type)
# ---------------------------------------------------------------------------


def _parse_python_file(
    py_path: Path, module_dir: Path
) -> tuple[list[_ParsedModel], list[str] | None]:
    """Parse a Python file for model definitions.

    Returns (models, error_or_none).
    If syntax error, returns ([], error_message).
    """
    source = py_path.read_text(encoding="utf-8")
    rel = str(py_path.relative_to(module_dir))
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError as exc:
        return [], [f"Python syntax error in {rel}: {exc.msg} (line {exc.lineno})"]

    models: list[_ParsedModel] = []
    imports: list[str] = []

    for node in ast.walk(tree):
        # Collect imports from odoo.addons.*
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod_name = ""
            if isinstance(node, ast.ImportFrom) and node.module:
                mod_name = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("odoo.addons."):
                        parts = alias.name.split(".")
                        if len(parts) >= 3:
                            imports.append(parts[2])
            if mod_name.startswith("odoo.addons."):
                parts = mod_name.split(".")
                if len(parts) >= 3:
                    imports.append(parts[2])

        # Collect model classes
        if isinstance(node, ast.ClassDef):
            model_info = _extract_model_info(node, rel)
            if model_info:
                model_info.imports = imports
                models.append(model_info)

    return models, None


def _extract_model_info(node: ast.ClassDef, file_path: str) -> _ParsedModel | None:
    """Extract model name, fields, inherits from an AST ClassDef."""
    model_name: str | None = None
    inherits: list[str] = []
    fields_dict: dict[str, dict[str, Any]] = {}
    comodels: list[str] = []
    depends_decs: list[tuple[str, list[str]]] = []
    line_numbers: dict[str, int] = {}

    for stmt in node.body:
        # _name = '...'
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    if target.id == "_name" and isinstance(stmt.value, ast.Constant):
                        model_name = str(stmt.value.value)
                    elif target.id == "_inherit":
                        inherits = _extract_inherit(stmt.value)

        # Field assignments: name = fields.Char(...)
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name) and isinstance(stmt.value, ast.Call):
                finfo = _extract_field_call(stmt.value)
                if finfo:
                    fields_dict[target.id] = finfo
                    line_numbers[target.id] = stmt.lineno
                    if "comodel_name" in finfo:
                        comodels.append(finfo["comodel_name"])

        # @api.depends(...) decorators on methods
        if isinstance(stmt, ast.FunctionDef):
            for dec in stmt.decorator_list:
                dep_fields = _extract_depends_decorator(dec)
                if dep_fields:
                    depends_decs.append((stmt.name, dep_fields))

    if model_name is None:
        return None

    return _ParsedModel(
        model_name=model_name,
        fields=fields_dict,
        comodels=comodels,
        inherits=inherits,
        imports=[],
        depends_decorators=depends_decs,
        file_path=file_path,
        line_numbers=line_numbers,
    )


def _extract_inherit(node: ast.expr) -> list[str]:
    """Extract _inherit value as a list of strings."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.List):
        result = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                result.append(elt.value)
        return result
    return []


def _extract_field_call(node: ast.Call) -> dict[str, Any] | None:
    """Extract field info from a fields.X(...) call."""
    if not isinstance(node.func, ast.Attribute):
        return None
    if not isinstance(node.func.value, ast.Name):
        return None
    if node.func.value.id != "fields":
        return None

    ftype = node.func.attr
    info: dict[str, Any] = {"type": ftype}

    # First positional arg is often comodel_name for relational fields
    if ftype in ("Many2one", "One2many", "Many2many") and node.args:
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            info["comodel_name"] = first_arg.value

    # Check keyword args
    for kw in node.keywords:
        if kw.arg == "comodel_name" and isinstance(kw.value, ast.Constant):
            info["comodel_name"] = str(kw.value.value)
        elif kw.arg == "compute" and isinstance(kw.value, ast.Constant):
            info["compute"] = str(kw.value.value)

    return info


def _extract_depends_decorator(dec: ast.expr) -> list[str] | None:
    """Extract field names from @api.depends('f1', 'f2')."""
    if not isinstance(dec, ast.Call):
        return None
    if not isinstance(dec.func, ast.Attribute):
        return None
    if dec.func.attr != "depends":
        return None
    if not isinstance(dec.func.value, ast.Name) or dec.func.value.id != "api":
        return None

    result = []
    for arg in dec.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            result.append(arg.value)
    return result if result else None


def _parse_xml_file(
    xml_path: Path, module_dir: Path
) -> tuple[_ParsedXml | None, str | None]:
    """Parse an XML file for records, field refs, groups, external refs.

    Returns (parsed_xml, error_message_or_none).
    """
    rel = str(xml_path.relative_to(module_dir))
    try:
        tree = ET.parse(xml_path)  # noqa: S314
    except ET.ParseError as exc:
        return None, f"XML parse error in {rel}: {exc}"

    root = tree.getroot()
    record_ids: dict[str, int] = {}
    field_refs: list[tuple[str, str, int]] = []
    group_refs: list[tuple[str, int]] = []
    external_refs: list[str] = []
    rule_domains: list[tuple[str, str, int]] = []

    for record in root.iter("record"):
        xml_id = record.get("id", "")
        record_model = record.get("model", "")

        if xml_id:
            record_ids[xml_id] = 1  # line not easily available from ET

        # Check for ir.rule domain_force
        if record_model == "ir.rule":
            model_ref = ""
            domain_str = ""
            for fld in record:
                if fld.tag == "field":
                    fname = fld.get("name", "")
                    if fname == "model_id":
                        model_ref = fld.get("ref", "")
                    elif fname == "domain_force":
                        domain_str = (fld.text or "").strip()
            if model_ref and domain_str:
                rule_domains.append((model_ref, domain_str, 1))

        # Detect ir.ui.view records to extract arch field refs
        if record_model == "ir.ui.view":
            view_model = ""
            for fld in record:
                if fld.tag == "field" and fld.get("name") == "model":
                    view_model = (fld.text or "").strip()
                # Check for ref="" attributes on fields (external refs)
                if fld.tag == "field" and fld.get("ref"):
                    ref_val = fld.get("ref", "")
                    if "." in ref_val:
                        external_refs.append(ref_val)

            # Find arch content and extract field refs inside form/tree/search
            for fld in record:
                if fld.tag == "field" and fld.get("name") == "arch":
                    _extract_arch_field_refs(fld, view_model, field_refs, group_refs)

        # Non-view records: check for ref="" attributes
        if record_model != "ir.ui.view":
            for fld in record:
                if fld.tag == "field" and fld.get("ref"):
                    ref_val = fld.get("ref", "")
                    if "." in ref_val:
                        external_refs.append(ref_val)

    parsed = _ParsedXml(
        record_ids=record_ids,
        field_refs=field_refs,
        group_refs=group_refs,
        external_refs=external_refs,
        rule_domains=rule_domains,
        file_path=rel,
    )
    return parsed, None


def _extract_arch_field_refs(
    arch_node: ET.Element,
    view_model: str,
    field_refs: list[tuple[str, str, int]],
    group_refs: list[tuple[str, int]],
) -> None:
    """Extract field name references from inside arch (form/tree/search)."""
    # Walk all elements inside arch
    for elem in arch_node.iter():
        # Field references inside form/tree/search
        if elem.tag == "field":
            fname = elem.get("name", "")
            if fname and view_model:
                field_refs.append((view_model, fname, 1))

        # Group references (groups="module.group_name")
        groups_attr = elem.get("groups", "")
        if groups_attr:
            for grp in groups_attr.split(","):
                grp = grp.strip()
                if grp:
                    group_refs.append((grp, 1))


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_e1(module_dir: Path) -> tuple[list[ValidationIssue], set[str]]:
    """E1: Python syntax validation via ast.parse()."""
    issues: list[ValidationIssue] = []
    failed_py: set[str] = set()

    for py_file in module_dir.rglob("*.py"):
        rel = str(py_file.relative_to(module_dir))
        try:
            source = py_file.read_text(encoding="utf-8")
            ast.parse(source, filename=rel)
        except SyntaxError as exc:
            issues.append(ValidationIssue(
                code="E1",
                severity="error",
                file=rel,
                line=exc.lineno,
                message=f"Python syntax error: {exc.msg}",
            ))
            failed_py.add(rel)

    return issues, failed_py


def _check_e2(module_dir: Path) -> tuple[list[ValidationIssue], set[str]]:
    """E2: XML well-formedness via xml.etree."""
    issues: list[ValidationIssue] = []
    failed_xml: set[str] = set()

    for xml_file in module_dir.rglob("*.xml"):
        rel = str(xml_file.relative_to(module_dir))
        try:
            ET.parse(xml_file)  # noqa: S314
        except ET.ParseError as exc:
            issues.append(ValidationIssue(
                code="E2",
                severity="error",
                file=rel,
                line=None,
                message=f"XML parse error: {exc}",
            ))
            failed_xml.add(rel)

    return issues, failed_xml


def _check_e3(
    parsed_xmls: list[_ParsedXml],
    module_models: dict[str, _ParsedModel],
    known_models: dict[str, Any],
) -> list[ValidationIssue]:
    """E3: View field references exist on model."""
    issues: list[ValidationIssue] = []

    for px in parsed_xmls:
        for model_name, field_name, line in px.field_refs:
            # Skip view metadata fields
            if field_name in _VIEW_META_FIELDS:
                continue

            model = module_models.get(model_name)
            if not model:
                continue  # Model not in this module, can't validate

            # Collect all known fields: own + inherited
            all_fields: set[str] = set(model.fields.keys())
            inherited = _get_inherited_fields(model.inherits, known_models, module_models)
            all_fields.update(inherited.keys())
            # Add common implicit fields
            all_fields.update({"id", "create_date", "create_uid", "write_date", "write_uid", "display_name"})

            if field_name not in all_fields:
                suggestion = None
                matches = difflib.get_close_matches(field_name, list(all_fields), n=1, cutoff=0.6)
                if matches:
                    suggestion = f"Did you mean '{matches[0]}'?"

                issues.append(ValidationIssue(
                    code="E3",
                    severity="error",
                    file=px.file_path,
                    line=line,
                    message=f"Field '{field_name}' not found on model '{model_name}'",
                    fixable=suggestion is not None,
                    suggestion=suggestion,
                ))

    return issues


def _check_e4(
    module_dir: Path,
    module_models: dict[str, _ParsedModel],
) -> list[ValidationIssue]:
    """E4: ACL CSV entries reference valid model XML IDs."""
    issues: list[ValidationIssue] = []

    # Build set of valid model XML IDs from parsed models
    valid_model_ids: set[str] = set()
    for model in module_models.values():
        # model_id:id format: model_{technical_name_with_underscores}
        xml_id = "model_" + model.model_name.replace(".", "_")
        valid_model_ids.add(xml_id)

    for csv_file in module_dir.rglob("ir.model.access.csv"):
        rel = str(csv_file.relative_to(module_dir))
        with open(csv_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                continue
            for line_num, row in enumerate(reader, start=2):
                if len(row) < 4:
                    continue
                model_id = row[2].strip() if len(row) > 2 else ""
                if model_id and model_id not in valid_model_ids:
                    issues.append(ValidationIssue(
                        code="E4",
                        severity="error",
                        file=rel,
                        line=line_num,
                        message=f"ACL references unknown model XML ID '{model_id}'",
                    ))

    return issues


def _check_e5(parsed_xmls: list[_ParsedXml]) -> list[ValidationIssue]:
    """E5: XML ID uniqueness across data files."""
    issues: list[ValidationIssue] = []
    seen: dict[str, str] = {}  # xml_id -> first file

    for px in parsed_xmls:
        for xml_id in px.record_ids:
            if xml_id in seen:
                issues.append(ValidationIssue(
                    code="E5",
                    severity="error",
                    file=px.file_path,
                    line=None,
                    message=(
                        f"Duplicate XML ID '{xml_id}' "
                        f"(also in '{seen[xml_id]}')"
                    ),
                ))
            else:
                seen[xml_id] = px.file_path

    return issues


def _check_e6(
    module_dir: Path,
    module_models: dict[str, _ParsedModel],
    parsed_xmls: list[_ParsedXml],
) -> list[ValidationIssue]:
    """E6: Manifest depends completeness."""
    issues: list[ValidationIssue] = []

    # Parse manifest
    manifest_path = module_dir / "__manifest__.py"
    if not manifest_path.exists():
        return issues

    try:
        manifest_src = manifest_path.read_text(encoding="utf-8")
        manifest = ast.literal_eval(manifest_src)
    except (SyntaxError, ValueError):
        return issues

    declared_depends: set[str] = set(manifest.get("depends", []))
    # 'base' is always implicitly available
    declared_depends.add("base")

    # Collect required modules from Python imports
    required_modules: set[str] = set()
    for model in module_models.values():
        for imp in model.imports:
            if imp not in declared_depends:
                required_modules.add(imp)

    # Collect required modules from XML ref="" attributes
    for px in parsed_xmls:
        for ext_ref in px.external_refs:
            parts = ext_ref.split(".", 1)
            if len(parts) == 2:
                module_name = parts[0]
                if module_name not in declared_depends:
                    required_modules.add(module_name)

    for mod in sorted(required_modules):
        issues.append(ValidationIssue(
            code="E6",
            severity="error",
            file="__manifest__.py",
            line=None,
            message=f"Module '{mod}' is referenced but not in manifest depends",
        ))

    return issues


def _check_w1(
    module_models: dict[str, _ParsedModel],
    known_models: dict[str, Any],
    registry: ModelRegistry | None,
) -> list[ValidationIssue]:
    """W1: Comodel references checked against registry and known models."""
    issues: list[ValidationIssue] = []
    all_module_model_names = set(module_models.keys())

    for model in module_models.values():
        for comodel in model.comodels:
            # Check known models
            if comodel in known_models:
                continue
            # Check within this module
            if comodel in all_module_model_names:
                continue
            # Check registry
            if registry and registry.show_model(comodel) is not None:
                continue

            issues.append(ValidationIssue(
                code="W1",
                severity="warning",
                file=model.file_path,
                line=None,
                message=f"Comodel '{comodel}' not found in known models or registry",
            ))

    return issues


def _check_w2(module_models: dict[str, _ParsedModel]) -> list[ValidationIssue]:
    """W2: @api.depends references validated."""
    issues: list[ValidationIssue] = []

    for model in module_models.values():
        all_fields: set[str] = set(model.fields.keys())
        # Add common implicit fields
        all_fields.update({"id", "create_date", "create_uid", "write_date", "write_uid", "display_name"})

        for method_name, dep_fields in model.depends_decorators:
            for dep_field in dep_fields:
                # Dot-notation: only validate first segment
                first_segment = dep_field.split(".")[0]
                if first_segment not in all_fields:
                    issues.append(ValidationIssue(
                        code="W2",
                        severity="warning",
                        file=model.file_path,
                        line=None,
                        message=(
                            f"@api.depends('{dep_field}') on '{method_name}': "
                            f"field '{first_segment}' not found on '{model.model_name}'"
                        ),
                    ))

    return issues


def _check_w3(
    parsed_xmls: list[_ParsedXml],
    module_xml_ids: set[str],
) -> list[ValidationIssue]:
    """W3: Security group references in views validated."""
    issues: list[ValidationIssue] = []

    for px in parsed_xmls:
        for group_ref, line in px.group_refs:
            # Known Odoo groups
            if group_ref in _KNOWN_GROUPS:
                continue
            # Groups defined in this module (without module prefix)
            if group_ref in module_xml_ids:
                continue
            # Check if group is module.id format and module part matches known
            if "." in group_ref:
                # External group -- we can't fully validate, but check known
                pass  # Falls through to warning

            issues.append(ValidationIssue(
                code="W3",
                severity="warning",
                file=px.file_path,
                line=line,
                message=f"Security group '{group_ref}' not found in known groups",
            ))

    return issues


def _check_w4(
    parsed_xmls: list[_ParsedXml],
    module_models: dict[str, _ParsedModel],
) -> list[ValidationIssue]:
    """W4: Record rule domain field references validated."""
    issues: list[ValidationIssue] = []

    for px in parsed_xmls:
        for model_ref, domain_str, line in px.rule_domains:
            # Convert model_ref (e.g., model_res_partner_ext) to model name
            model_name = model_ref.replace("model_", "", 1).replace("_", ".")
            model = module_models.get(model_name)
            if not model:
                continue

            all_fields: set[str] = set(model.fields.keys())
            all_fields.update({"id", "create_date", "create_uid", "write_date", "write_uid", "display_name"})

            # Extract field names from domain tuples: ('field_name', '=', value)
            field_pattern = re.compile(r"\(\s*['\"](\w+)['\"]")
            for match in field_pattern.finditer(domain_str):
                domain_field = match.group(1)
                if domain_field not in all_fields:
                    issues.append(ValidationIssue(
                        code="W4",
                        severity="warning",
                        file=px.file_path,
                        line=line,
                        message=(
                            f"Record rule domain references field '{domain_field}' "
                            f"not found on model '{model_name}'"
                        ),
                    ))

    return issues


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def semantic_validate(
    output_dir: Path,
    registry: ModelRegistry | None = None,
) -> SemanticValidationResult:
    """Run all 10 semantic checks on a generated module directory.

    Parameters
    ----------
    output_dir:
        Path to the module root (contains ``__manifest__.py``).
    registry:
        Optional :class:`ModelRegistry` for comodel lookups.

    Returns
    -------
    SemanticValidationResult
        Structured result with errors, warnings, and duration.
    """
    start = time.perf_counter()
    module_name = output_dir.name
    result = SemanticValidationResult(module=module_name)
    known_models = _load_known_models()

    # --- Phase 1: Syntax checks (E1, E2) ---
    e1_issues, failed_py = _check_e1(output_dir)
    result.errors.extend(e1_issues)

    e2_issues, failed_xml = _check_e2(output_dir)
    result.errors.extend(e2_issues)

    # --- Phase 2: Parse valid files ---
    module_models: dict[str, _ParsedModel] = {}
    all_imports: list[str] = []

    for py_file in output_dir.rglob("*.py"):
        rel = str(py_file.relative_to(output_dir))
        if rel in failed_py:
            continue  # Short-circuit: skip files that failed E1
        models, _err = _parse_python_file(py_file, output_dir)
        for m in models:
            module_models[m.model_name] = m
            all_imports.extend(m.imports)

    parsed_xmls: list[_ParsedXml] = []
    for xml_file in output_dir.rglob("*.xml"):
        rel = str(xml_file.relative_to(output_dir))
        if rel in failed_xml:
            continue  # Short-circuit: skip files that failed E2
        px, _err = _parse_xml_file(xml_file, output_dir)
        if px:
            parsed_xmls.append(px)

    # --- Phase 3: Cross-reference checks ---
    # E5: XML ID uniqueness
    result.errors.extend(_check_e5(parsed_xmls))

    # E3: Field references
    result.errors.extend(_check_e3(parsed_xmls, module_models, known_models))

    # E4: ACL references
    result.errors.extend(_check_e4(output_dir, module_models))

    # E6: Manifest depends
    result.errors.extend(_check_e6(output_dir, module_models, parsed_xmls))

    # W1: Comodel references
    result.warnings.extend(_check_w1(module_models, known_models, registry))

    # W2: Computed depends
    result.warnings.extend(_check_w2(module_models))

    # W3: Group references
    module_xml_ids: set[str] = set()
    for px in parsed_xmls:
        module_xml_ids.update(px.record_ids.keys())
    result.warnings.extend(_check_w3(parsed_xmls, module_xml_ids))

    # W4: Rule domains
    result.warnings.extend(_check_w4(parsed_xmls, module_models))

    elapsed = time.perf_counter() - start
    result.duration_ms = int(elapsed * 1000)
    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_validation_report(result: SemanticValidationResult) -> None:
    """Print a human-friendly semantic validation report."""
    print(f"\n=== Semantic Validation: {result.module} ===")
    print(f"Duration: {result.duration_ms}ms\n")

    if not result.errors and not result.warnings:
        print("All checks passed. No issues found.")
        return

    if result.errors:
        print(f"ERRORS ({len(result.errors)}):")
        for issue in result.errors:
            loc = f"{issue.file}"
            if issue.line:
                loc += f":{issue.line}"
            print(f"  [{issue.code}] {loc} -- {issue.message}")
            if issue.suggestion:
                print(f"         Suggestion: {issue.suggestion}")

    if result.warnings:
        print(f"\nWARNINGS ({len(result.warnings)}):")
        for issue in result.warnings:
            loc = f"{issue.file}"
            if issue.line:
                loc += f":{issue.line}"
            print(f"  [{issue.code}] {loc} -- {issue.message}")
            if issue.suggestion:
                print(f"         Suggestion: {issue.suggestion}")

    print(f"\nSummary: {len(result.errors)} error(s), {len(result.warnings)} warning(s)")
