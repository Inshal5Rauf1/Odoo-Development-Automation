"""Jinja2 rendering engine with Odoo-specific filters for module scaffolding."""

from __future__ import annotations

import json
import re
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from odoo_gen_utils.validation.types import Result

from collections import defaultdict

from odoo_gen_utils.renderer_utils import (
    _is_monetary_field,
    _model_ref,
    _to_class,
    _to_python_var,
    _to_xml_id,
    _topologically_sort_fields,
    INDEXABLE_TYPES,
    MONETARY_FIELD_PATTERNS,
    NON_INDEXABLE_TYPES,
    SEQUENCE_FIELD_NAMES,
)

from odoo_gen_utils.preprocessors import (
    _process_computation_chains,
    _process_constraints,
    _process_performance,
    _process_production_patterns,
    _process_relationships,
    _validate_no_cycles,
)

if TYPE_CHECKING:
    from odoo_gen_utils.verifier import EnvironmentVerifier, VerificationWarning








def _register_filters(env: Environment) -> Environment:
    """Register Odoo-specific Jinja2 filters on an Environment.

    Args:
        env: Jinja2 Environment to register filters on.

    Returns:
        The same Environment with filters registered.
    """
    env.filters["model_ref"] = _model_ref
    env.filters["to_class"] = _to_class
    env.filters["to_python_var"] = _to_python_var
    env.filters["to_xml_id"] = _to_xml_id
    return env


def create_versioned_renderer(version: str) -> Environment:
    """Create a Jinja2 Environment that loads version-specific then shared templates.

    Uses a FileSystemLoader with a fallback chain: version-specific directory first,
    then shared directory. Templates in the version directory override shared ones.

    Args:
        version: Odoo version string (e.g., "17.0", "18.0").

    Returns:
        Configured Jinja2 Environment with versioned template loading.
    """
    base = Path(__file__).parent / "templates"
    version_dir = str(base / version)
    shared_dir = str(base / "shared")
    env = Environment(
        loader=FileSystemLoader([version_dir, shared_dir]),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return _register_filters(env)


def create_renderer(template_dir: Path) -> Environment:
    """Create a Jinja2 Environment configured for Odoo module rendering.

    Uses StrictUndefined to fail loudly on missing template variables (Pitfall 1 prevention).
    Registers custom filters for Odoo-specific name conversions.

    If template_dir is the base templates directory (containing 17.0/, 18.0/, shared/
    subdirectories), falls back to create_versioned_renderer("17.0") for backward
    compatibility after the template reorganization in Phase 9.

    Args:
        template_dir: Path to the directory containing .j2 template files.

    Returns:
        Configured Jinja2 Environment.
    """
    # Detect if this is the base templates dir (reorganized layout)
    base_templates = Path(__file__).parent / "templates"
    if template_dir.resolve() == base_templates.resolve():
        return create_versioned_renderer("17.0")

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return _register_filters(env)


def render_template(
    env: Environment,
    template_name: str,
    output_path: Path,
    context: dict[str, Any],
) -> Path:
    """Render a single Jinja2 template to a file.

    Creates parent directories as needed.

    Args:
        env: Jinja2 Environment with loaded templates.
        template_name: Name of the template file (e.g., "manifest.py.j2").
        output_path: Destination file path for the rendered output.
        context: Dictionary of template variables.

    Returns:
        The output_path where the rendered file was written.
    """
    template = env.get_template(template_name)
    content = template.render(**context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def get_template_dir() -> Path:
    """Return the path to the bundled templates directory.

    The templates are shipped alongside this module in the templates/ subdirectory.

    Returns:
        Absolute path to the templates directory.
    """
    return Path(__file__).parent / "templates"


def _build_model_context(spec: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    """Build the template context for a single model from the module spec.

    Extends the base context with Phase 5 keys:
    - computed_fields: fields with compute= key
    - onchange_fields: fields with onchange= key
    - constrained_fields: fields with constrains= key
    - sequence_fields: Char fields with sequence names and required=True
    - sequence_field_names: list version of SEQUENCE_FIELD_NAMES for template use
    - state_field: the state/status Selection field or None
    - wizards: list of wizard specs from spec root
    - has_computed: bool
    - has_sequence_fields: bool

    Args:
        spec: Full module specification dictionary.
        model: Single model dictionary from spec["models"].

    Returns:
        Context dictionary suitable for rendering model-related templates.
    """
    model_var = _to_python_var(model["name"])
    model_xml_id = _to_xml_id(model["name"])

    fields = model.get("fields", [])
    required_fields = [f for f in fields if f.get("required")]
    # Phase 29: complex constraints from preprocessor
    complex_constraints = model.get("complex_constraints", [])
    create_constraints = model.get("create_constraints", [])
    write_constraints = model.get("write_constraints", [])
    has_create_override = bool(model.get("override_sources", {}).get("create"))
    has_write_override = bool(model.get("override_sources", {}).get("write"))
    needs_translate = bool(complex_constraints)

    has_constraints = any(
        f.get("constraints") for f in fields
    ) or bool(model.get("sql_constraints")) or bool(complex_constraints)

    # Phase 5 extensions ---------------------------------------------------
    computed_fields = [f for f in fields if f.get("compute")]
    # Phase 28: topologically sort computed fields by dependency order
    if len(computed_fields) > 1:
        computed_fields = _topologically_sort_fields(computed_fields)
    onchange_fields = [f for f in fields if f.get("onchange")]
    constrained_fields = [f for f in fields if f.get("constrains")]
    sequence_fields = [
        f for f in fields
        if f.get("type") == "Char"
        and f.get("name") in SEQUENCE_FIELD_NAMES
        and f.get("required")
    ]
    state_field = next(
        (
            f for f in fields
            if f.get("name") in ("state", "status") and f.get("type") == "Selection"
        ),
        None,
    )
    wizards = spec.get("wizards", [])

    # Phase 26: monetary field detection (immutable rewrite)
    has_monetary = any(_is_monetary_field(f) for f in fields)
    if has_monetary:
        fields = [
            {**f, "type": "Monetary"} if _is_monetary_field(f) and f.get("type") == "Float" else f
            for f in fields
        ]
    has_currency_id = any(f.get("name") == "currency_id" for f in fields)
    needs_currency_id = has_monetary and not has_currency_id

    # Phase 6: multi-company field detection
    has_company_field = any(
        f.get("name") == "company_id" and f.get("type") == "Many2one"
        for f in fields
    )

    # Phase 12 + 21: mail.thread auto-inheritance (TMPL-01)
    # Smart injection: skip line items, honor chatter flag, avoid duplicates on in-module parents
    explicit_inherit = model.get("inherit")
    inherit_list = [explicit_inherit] if explicit_inherit else []

    # Collect all model names in this module for line item & parent detection
    module_model_names = {m["name"] for m in spec.get("models", [])}

    # Detect if this model is a line item (has required Many2one _id to in-module model)
    is_line_item = any(
        f.get("type") == "Many2one"
        and f.get("required")
        and f.get("comodel_name") in module_model_names
        and f.get("name", "").endswith("_id")
        for f in fields
    )

    # Read explicit chatter flag: None=auto, True=force, False=skip
    chatter = model.get("chatter")
    if chatter is None:
        chatter = not is_line_item

    # Detect if parent (explicit_inherit) is another model in the same module
    parent_is_in_module = explicit_inherit in module_model_names if explicit_inherit else False

    if chatter and "mail" in spec.get("depends", []) and not parent_is_in_module:
        for mixin in ("mail.thread", "mail.activity.mixin"):
            if mixin not in inherit_list:
                inherit_list.append(mixin)

    # Phase 27: hierarchical model detection
    is_hierarchical = model.get("hierarchical", False)
    if is_hierarchical:
        field_names_set = {f.get("name") for f in fields}
        hierarchical_injections: list[dict[str, Any]] = []
        if "parent_id" not in field_names_set:
            hierarchical_injections.append({
                "name": "parent_id",
                "type": "Many2one",
                "comodel_name": model["name"],
                "string": "Parent",
                "index": True,
                "ondelete": "cascade",
            })
        if "child_ids" not in field_names_set:
            hierarchical_injections.append({
                "name": "child_ids",
                "type": "One2many",
                "comodel_name": model["name"],
                "inverse_name": "parent_id",
                "string": "Children",
            })
        if "parent_path" not in field_names_set:
            hierarchical_injections.append({
                "name": "parent_path",
                "type": "Char",
                "index": True,
                "internal": True,
            })
        if hierarchical_injections:
            fields = [*fields, *hierarchical_injections]

    # Phase 27: view_fields excludes internal fields (e.g. parent_path)
    view_fields = [f for f in fields if not f.get("internal")]

    # Phase 30: cron methods targeting this model
    cron_methods = [
        c for c in spec.get("cron_jobs", [])
        if c.get("model_name") == model["name"]
    ]

    # Phase 31: reports and dashboards targeting this model
    model_reports = [
        r for r in spec.get("reports", [])
        if r.get("model_name") == model["name"]
    ]
    has_dashboard = any(
        d.get("model_name") == model["name"]
        for d in spec.get("dashboards", [])
    )

    # Phase 34: production pattern keys
    is_bulk = model.get("is_bulk", False)
    is_cacheable = model.get("is_cacheable", False)
    cache_lookup_field = model.get("cache_lookup_field", "name")
    needs_tools = model.get("needs_tools", False)
    is_archival = model.get("is_archival", False)
    archival_batch_size = model.get("archival_batch_size", 100)
    archival_days = model.get("archival_days", 365)

    # Phase 34-02: filter archival cron from generic cron_methods
    # (archival has a dedicated template block, not a stub)
    if is_archival:
        cron_methods = [c for c in cron_methods if c.get("method") != "_cron_archive_old_records"]

    # Phase 12: conditional api import (TMPL-02)
    # Phase 29: also need api when temporal constraints exist (@api.constrains)
    # or create/write overrides exist (@api.model_create_multi)
    # Phase 30: also need api when cron methods exist (@api.model)
    # Phase 34: also need api when bulk or cacheable (for @api.model_create_multi)
    has_temporal = any(c.get("type") == "temporal" for c in complex_constraints)
    needs_api = bool(
        computed_fields or onchange_fields or constrained_fields
        or sequence_fields or has_temporal or has_create_override
        or cron_methods or is_bulk or is_cacheable or is_archival
    )

    return {
        "module_name": spec["module_name"],
        "module_title": spec.get("module_title", spec["module_name"].replace("_", " ").title()),
        "summary": spec.get("summary", ""),
        "author": spec.get("author", ""),
        "website": spec.get("website", ""),
        "license": spec.get("license", "LGPL-3"),
        "category": spec.get("category", "Uncategorized"),
        "odoo_version": spec.get("odoo_version", "17.0"),
        "depends": spec.get("depends", ["base"]),
        "application": spec.get("application", True),
        "models": spec.get("models", []),
        "model_name": model["name"],
        "model_description": model.get("description", model["name"]),
        "model_var": model_var,
        "model_xml_id": model_xml_id,
        "fields": fields,
        "required_fields": required_fields,
        "has_constraints": has_constraints,
        "sql_constraints": model.get("sql_constraints", []),
        "inherit": model.get("inherit"),
        # Phase 5 keys
        "computed_fields": computed_fields,
        "onchange_fields": onchange_fields,
        "constrained_fields": constrained_fields,
        "sequence_fields": sequence_fields,
        "sequence_field_names": list(SEQUENCE_FIELD_NAMES),
        "state_field": state_field,
        "wizards": wizards,
        "has_computed": bool(computed_fields),
        "has_sequence_fields": bool(sequence_fields),
        # Phase 6 keys
        "has_company_field": has_company_field,
        "workflow_states": model.get("workflow_states", []),
        # Phase 12 keys
        "inherit_list": inherit_list,
        "needs_api": needs_api,
        # Phase 26 keys
        "needs_currency_id": needs_currency_id,
        # Phase 27 keys
        "is_hierarchical": is_hierarchical,
        "view_fields": view_fields,
        # Phase 29 keys
        "complex_constraints": complex_constraints,
        "create_constraints": create_constraints,
        "write_constraints": write_constraints,
        "has_create_override": has_create_override,
        "has_write_override": has_write_override,
        "needs_translate": needs_translate,
        # Phase 30 keys
        "cron_methods": cron_methods,
        # Phase 31 keys
        "model_reports": model_reports,
        "has_dashboard": has_dashboard,
        # Phase 33 keys
        "model_order": model.get("model_order", ""),
        "is_transient": model.get("transient", False),
        "transient_max_hours": model.get("transient_max_hours"),
        "transient_max_count": model.get("transient_max_count"),
        # Phase 34 keys
        "is_bulk": is_bulk,
        "is_cacheable": is_cacheable,
        "cache_lookup_field": cache_lookup_field,
        "needs_tools": needs_tools,
        "is_archival": is_archival,
        "archival_batch_size": archival_batch_size,
        "archival_days": archival_days,
    }


def _compute_manifest_data(
    spec: dict[str, Any],
    data_files: list[str],
    wizard_view_files: list[str],
    has_company_modules: bool = False,
) -> list[str]:
    """Compute the canonical manifest data file list.

    Canonical load order:
    1. security/security.xml
    2. security/ir.model.access.csv
    3. security/record_rules.xml (only if has_company_modules)
    4. data files (sequences.xml first, then data.xml)
    5. per-model view files (*_views.xml, *_action.xml)
    6. views/menu.xml
    7. wizard view files (*_wizard_form.xml)

    Args:
        spec: Full module specification dictionary.
        data_files: List of data file paths relative to module root (e.g., ["data/sequences.xml"]).
        wizard_view_files: List of wizard view file paths (e.g., ["views/confirm_wizard_wizard_form.xml"]).
        has_company_modules: Whether any model has a company_id Many2one field.

    Returns:
        Ordered list of file paths for the manifest data section.
    """
    manifest_files: list[str] = [
        "security/security.xml",
        "security/ir.model.access.csv",
    ]
    if has_company_modules:
        manifest_files.append("security/record_rules.xml")

    manifest_files.extend(data_files)

    for model in spec.get("models", []):
        model_var = _to_python_var(model["name"])
        manifest_files.append(f"views/{model_var}_views.xml")
        manifest_files.append(f"views/{model_var}_action.xml")

    # Phase 31: dashboard view files (after model views, before menu)
    dashboard_models_seen: set[str] = set()
    for dashboard in spec.get("dashboards", []):
        model_xml = _to_xml_id(dashboard["model_name"])
        if model_xml not in dashboard_models_seen:
            dashboard_models_seen.add(model_xml)
            manifest_files.append(f"views/{model_xml}_graph.xml")
            manifest_files.append(f"views/{model_xml}_pivot.xml")

    manifest_files.append("views/menu.xml")
    manifest_files.extend(wizard_view_files)

    return manifest_files


def _compute_view_files(spec: dict[str, Any]) -> list[str]:
    """Compute the list of view file paths for the manifest data section.

    Args:
        spec: Full module specification dictionary.

    Returns:
        List of view file relative paths (e.g., ["item_views.xml", ...]).
    """
    view_files = []
    for model in spec.get("models", []):
        model_var = _to_python_var(model["name"])
        view_files.append(f"{model_var}_views.xml")
        view_files.append(f"{model_var}_action.xml")
    view_files.append("menu.xml")
    return view_files


def render_manifest(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render __manifest__.py, root __init__.py, and models/__init__.py.

    Args:
        env: Configured Jinja2 Environment.
        spec: Full module specification dictionary.
        module_dir: Path to the module directory.
        module_context: Shared module-level template context.

    Returns:
        Result containing list of created file Paths on success.
    """
    try:
        created: list[Path] = []
        created.append(
            render_template(env, "manifest.py.j2", module_dir / "__manifest__.py", module_context)
        )
        created.append(
            render_template(env, "init_root.py.j2", module_dir / "__init__.py", module_context)
        )
        created.append(
            render_template(env, "init_models.py.j2", module_dir / "models" / "__init__.py", module_context)
        )
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_manifest failed: {exc}")


def render_models(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
    verifier: "EnvironmentVerifier | None" = None,
    warnings_out: list | None = None,
) -> Result[list[Path]]:
    """Render per-model .py files, views, and action files.

    Args:
        env: Configured Jinja2 Environment.
        spec: Full module specification dictionary.
        module_dir: Path to the module directory.
        module_context: Shared module-level template context.
        verifier: Optional EnvironmentVerifier for inline verification.
        warnings_out: Optional mutable list to collect verification warnings into.

    Returns:
        Result containing list of created file Paths on success.
    """
    try:
        models = spec.get("models", [])
        created: list[Path] = []

        for model in models:
            model_ctx = _build_model_context(spec, model)
            model_var = _to_python_var(model["name"])

            if verifier is not None:
                model_result = verifier.verify_model_spec(model)
                if model_result.success and warnings_out is not None:
                    warnings_out.extend(model_result.data or [])

            created.append(
                render_template(env, "model.py.j2", module_dir / "models" / f"{model_var}.py", model_ctx)
            )
            created.append(
                render_template(env, "view_form.xml.j2", module_dir / "views" / f"{model_var}_views.xml", model_ctx)
            )

            if verifier is not None:
                field_names = [f.get("name", "") for f in model.get("fields", [])]
                view_result = verifier.verify_view_spec(model.get("name", ""), field_names)
                if view_result.success and warnings_out is not None:
                    warnings_out.extend(view_result.data or [])

            created.append(
                render_template(env, "action.xml.j2", module_dir / "views" / f"{model_var}_action.xml", model_ctx)
            )

        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_models failed: {exc}")


def render_views(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render views/menu.xml for all models.

    Args:
        env: Configured Jinja2 Environment.
        spec: Full module specification dictionary.
        module_dir: Path to the module directory.
        module_context: Shared module-level template context.

    Returns:
        Result containing list of created file Paths on success.
    """
    try:
        created: list[Path] = []
        created.append(
            render_template(env, "menu.xml.j2", module_dir / "views" / "menu.xml", module_context)
        )
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_views failed: {exc}")


def render_security(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render security files: security.xml, ir.model.access.csv, optional record_rules.xml.

    Args:
        env: Configured Jinja2 Environment.
        spec: Full module specification dictionary.
        module_dir: Path to the module directory.
        module_context: Shared module-level template context.

    Returns:
        Result containing list of created file Paths on success.
    """
    try:
        models = spec.get("models", [])
        created: list[Path] = []
        created.append(
            render_template(env, "security_group.xml.j2", module_dir / "security" / "security.xml", module_context)
        )
        created.append(
            render_template(env, "access_csv.j2", module_dir / "security" / "ir.model.access.csv", module_context)
        )
        has_company = any(
            any(f.get("name") == "company_id" and f.get("type") == "Many2one" for f in m.get("fields", []))
            for m in models
        )
        if has_company:
            enriched = [
                {**m, "has_company_field": any(
                    f.get("name") == "company_id" and f.get("type") == "Many2one" for f in m.get("fields", [])
                )}
                for m in models
            ]
            created.append(render_template(
                env, "record_rules.xml.j2", module_dir / "security" / "record_rules.xml",
                {**module_context, "models": enriched},
            ))
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_security failed: {exc}")


def render_wizards(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render wizard files: wizards/__init__.py, per-wizard .py, per-wizard form XML.

    Args:
        env: Configured Jinja2 Environment.
        spec: Full module specification dictionary.
        module_dir: Path to the module directory.
        module_context: Shared module-level template context.

    Returns:
        Result containing list of created file Paths on success (empty if no wizards).
    """
    try:
        spec_wizards = spec.get("wizards", [])
        if not spec_wizards:
            return Result.ok([])
        created: list[Path] = []
        created.append(
            render_template(env, "init_wizards.py.j2", module_dir / "wizards" / "__init__.py", {**module_context})
        )
        for wizard in spec_wizards:
            wvar = _to_python_var(wizard["name"])
            wxid = _to_xml_id(wizard["name"])
            wctx = {**module_context, "wizard": wizard, "wizard_var": wvar,
                    "wizard_xml_id": wxid, "wizard_class": _to_class(wizard["name"]), "needs_api": True,
                    "transient_max_hours": wizard.get("transient_max_hours"),
                    "transient_max_count": wizard.get("transient_max_count")}
            py_template = wizard.get("template", "wizard.py.j2")
            form_template = wizard.get("form_template", "wizard_form.xml.j2")
            created.append(render_template(env, py_template, module_dir / "wizards" / f"{wvar}.py", wctx))
            created.append(render_template(
                env, form_template, module_dir / "views" / f"{wxid}_wizard_form.xml", wctx))
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_wizards failed: {exc}")


def render_tests(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render tests/__init__.py and per-model test files.

    Args:
        env: Configured Jinja2 Environment.
        spec: Full module specification dictionary.
        module_dir: Path to the module directory.
        module_context: Shared module-level template context.

    Returns:
        Result containing list of created file Paths on success.
    """
    try:
        created: list[Path] = []
        created.append(
            render_template(env, "init_tests.py.j2", module_dir / "tests" / "__init__.py", module_context)
        )
        for model in spec.get("models", []):
            model_ctx = _build_model_context(spec, model)
            model_var = _to_python_var(model["name"])
            created.append(
                render_template(env, "test_model.py.j2", module_dir / "tests" / f"test_{model_var}.py", model_ctx)
            )
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_tests failed: {exc}")


def render_static(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> Result[list[Path]]:
    """Render data.xml, sequences.xml, demo data, static/index.html, and README.rst.

    Args:
        env: Configured Jinja2 Environment.
        spec: Full module specification dictionary.
        module_dir: Path to the module directory.
        module_context: Shared module-level template context.

    Returns:
        Result containing list of created file Paths on success.
    """
    try:
        models = spec.get("models", [])
        created: list[Path] = []
        # data/data.xml stub
        data_xml_path = module_dir / "data" / "data.xml"
        data_xml_path.parent.mkdir(parents=True, exist_ok=True)
        data_xml_path.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n'
            "    <!-- Static data records go here -->\n</odoo>\n",
            encoding="utf-8",
        )
        created.append(data_xml_path)
        # sequences.xml if needed
        seq_models = [
            m for m in models
            if any(f.get("type") == "Char" and f.get("name") in SEQUENCE_FIELD_NAMES and f.get("required")
                   for f in m.get("fields", []))
        ]
        if seq_models:
            seq_ctx = {
                **module_context,
                "sequence_models": [
                    {"model": m, "model_var": _to_python_var(m["name"]),
                     "sequence_fields": [f for f in m.get("fields", [])
                                         if f.get("type") == "Char" and f.get("name") in SEQUENCE_FIELD_NAMES
                                         and f.get("required")]}
                    for m in seq_models
                ],
            }
            created.append(render_template(env, "sequences.xml.j2", module_dir / "data" / "sequences.xml", seq_ctx))
        # demo data
        created.append(render_template(env, "demo_data.xml.j2", module_dir / "demo" / "demo_data.xml", module_context))
        # static/description/index.html
        static_dir = module_dir / "static" / "description"
        static_dir.mkdir(parents=True, exist_ok=True)
        index_html = static_dir / "index.html"
        index_html.write_text(
            '<!DOCTYPE html>\n<html>\n<head><title>Module Description</title></head>\n'
            '<body><p>See README.rst for module documentation.</p></body>\n</html>\n',
            encoding="utf-8",
        )
        created.append(index_html)
        # README.rst
        created.append(render_template(env, "readme.rst.j2", module_dir / "README.rst", module_context))
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_static failed: {exc}")


def render_cron(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> "Result[list[Path]]":
    """Render ir.cron scheduled action XML from spec cron_jobs.

    Validates method names are valid Python identifiers.
    Returns Result.ok([]) when no cron_jobs are present.
    """
    cron_jobs = spec.get("cron_jobs")
    if not cron_jobs:
        return Result.ok([])
    # Validate method names
    for cron in cron_jobs:
        method = cron.get("method", "")
        if not method.isidentifier():
            return Result.fail(
                f"Invalid cron method name '{method}': must be a valid Python identifier"
            )
    cron_ctx = {**module_context, "cron_jobs": cron_jobs}
    try:
        path = render_template(env, "cron_data.xml.j2", module_dir / "data" / "cron_data.xml", cron_ctx)
        return Result.ok([path])
    except Exception as exc:
        return Result.fail(f"render_cron failed: {exc}")


def render_reports(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> "Result[list[Path]]":
    """Render QWeb report templates and graph/pivot dashboard views.

    Handles two spec sections:
    - spec["reports"]: ir.actions.report + QWeb template + optional paper format
    - spec["dashboards"]: graph view + pivot view per model

    Returns Result.ok([]) when neither section is present.
    """
    reports = spec.get("reports", [])
    dashboards = spec.get("dashboards", [])
    if not reports and not dashboards:
        return Result.ok([])
    try:
        created: list[Path] = []
        for report in reports:
            report_ctx = {**module_context, "report": report}
            created.append(render_template(
                env, "report_action.xml.j2",
                module_dir / "data" / f"report_{report['xml_id']}.xml",
                report_ctx,
            ))
            created.append(render_template(
                env, "report_template.xml.j2",
                module_dir / "data" / f"report_{report['xml_id']}_template.xml",
                report_ctx,
            ))
        for dashboard in dashboards:
            model_xml = _to_xml_id(dashboard["model_name"])
            dash_ctx = {**module_context, "dashboard": dashboard, "model_xml_id": model_xml}
            created.append(render_template(
                env, "graph_view.xml.j2",
                module_dir / "views" / f"{model_xml}_graph.xml",
                dash_ctx,
            ))
            created.append(render_template(
                env, "pivot_view.xml.j2",
                module_dir / "views" / f"{model_xml}_pivot.xml",
                dash_ctx,
            ))
        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_reports failed: {exc}")


def render_controllers(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> "Result[list[Path]]":
    """Render HTTP controller files and import/export wizard files.

    Generates controllers/main.py with @http.route decorators and
    controllers/__init__.py for each controller definition.
    Also generates import wizard .py and form XML for models with import_export:true.
    """
    try:
        created: list[Path] = []
        module_name = module_context["module_name"]

        # --- HTTP controllers ---
        controllers = spec.get("controllers")
        if controllers:
            for controller in controllers:
                class_name = controller.get("class_name") or (
                    _to_class(module_name) + "Controller"
                )
                routes = controller.get("routes", [])
                ctrl_ctx = {
                    **module_context,
                    "controller_class": class_name,
                    "routes": routes,
                    "module_name": module_name,
                }
                created.append(render_template(
                    env, "init_controllers.py.j2",
                    module_dir / "controllers" / "__init__.py",
                    ctrl_ctx,
                ))
                created.append(render_template(
                    env, "controller.py.j2",
                    module_dir / "controllers" / "main.py",
                    ctrl_ctx,
                ))

        # --- Import/export wizards ---
        import_export_models = [
            m for m in spec.get("models", []) if m.get("import_export")
        ]
        if import_export_models:
            import_wizard_modules: list[str] = []
            for model in import_export_models:
                model_name = model["name"]
                model_var = _to_python_var(model_name)
                model_xml_id = _to_xml_id(model_name)
                model_class = _to_class(model_name) + "ImportWizard"
                model_description = model.get(
                    "description", model_name.replace(".", " ").title()
                )
                # Non-relational, non-internal fields for export headers
                export_fields = [
                    f for f in model.get("fields", [])
                    if f.get("type") not in (
                        "Many2one", "One2many", "Many2many", "Binary",
                    )
                ]
                wiz_ctx = {
                    **module_context,
                    "model_name": model_name,
                    "model_var": model_var,
                    "model_xml_id": model_xml_id,
                    "wizard_class": model_class,
                    "model_description": model_description,
                    "export_fields": export_fields,
                    "transient_max_hours": model.get("transient_max_hours", 1.0),
                    "transient_max_count": model.get("transient_max_count", 0),
                }
                wizard_filename = f"{model_var}_import_wizard"
                import_wizard_modules.append(wizard_filename)
                created.append(render_template(
                    env, "import_wizard.py.j2",
                    module_dir / "wizards" / f"{wizard_filename}.py",
                    wiz_ctx,
                ))
                created.append(render_template(
                    env, "import_wizard_form.xml.j2",
                    module_dir / "views" / f"{model_xml_id}_import_wizard_form.xml",
                    wiz_ctx,
                ))
            # Render or update wizards/__init__.py with import wizard imports
            # Combine existing spec_wizards with import wizard modules
            existing_wizard_imports = [
                _to_python_var(w["name"])
                for w in module_context.get("spec_wizards", [])
            ]
            all_wizard_imports = existing_wizard_imports + import_wizard_modules
            init_content = "\n".join(
                f"from . import {name}" for name in all_wizard_imports
            ) + "\n"
            init_path = module_dir / "wizards" / "__init__.py"
            init_path.parent.mkdir(parents=True, exist_ok=True)
            init_path.write_text(init_content)
            created.append(init_path)

        return Result.ok(created)
    except Exception as exc:
        return Result.fail(f"render_controllers failed: {exc}")


def _build_module_context(spec: dict[str, Any], module_name: str) -> dict[str, Any]:
    """Build the shared module-level template context from the spec."""
    models = spec.get("models", [])
    spec_wizards = spec.get("wizards", [])
    has_seq = any(
        any(f.get("type") == "Char" and f.get("name") in SEQUENCE_FIELD_NAMES and f.get("required")
            for f in m.get("fields", []))
        for m in models
    )
    has_company = any(
        any(f.get("name") == "company_id" and f.get("type") == "Many2one" for f in m.get("fields", []))
        for m in models
    )
    data_files: list[str] = []
    if has_seq:
        data_files.append("data/sequences.xml")
    data_files.append("data/data.xml")
    # Phase 30: cron data file
    if spec.get("cron_jobs"):
        data_files.append("data/cron_data.xml")
    # Phase 31: report data files
    for report in spec.get("reports", []):
        data_files.append(f"data/report_{report['xml_id']}.xml")
        data_files.append(f"data/report_{report['xml_id']}_template.xml")
    wiz_files = [f"views/{_to_xml_id(w['name'])}_wizard_form.xml" for w in spec_wizards]
    # Phase 32: import/export wizard detection
    import_export_models = [m for m in models if m.get("import_export")]
    has_import_export = bool(import_export_models)
    # Add import wizard form view files to manifest
    for m in import_export_models:
        wiz_files.append(f"views/{_to_xml_id(m['name'])}_import_wizard_form.xml")
    # Build import_export_wizards list for ACL generation
    import_export_wizards = [
        {"name": f"{m['name']}.import.wizard"} for m in import_export_models
    ]
    manifest_files = _compute_manifest_data(spec, data_files, wiz_files, has_company_modules=has_company)
    ctx: dict[str, Any] = {
        "module_name": module_name,
        "module_title": spec.get("module_title", module_name.replace("_", " ").title()),
        "module_technical_name": module_name,
        "summary": spec.get("summary", ""),
        "author": spec.get("author", ""),
        "website": spec.get("website", ""),
        "license": spec.get("license", "LGPL-3"),
        "category": spec.get("category", "Uncategorized"),
        "odoo_version": spec.get("odoo_version", "17.0"),
        "depends": spec.get("depends", ["base"]),
        "application": spec.get("application", True),
        "models": models,
        "view_files": _compute_view_files(spec),
        "manifest_files": manifest_files,
        "has_wizards": bool(spec_wizards) or has_import_export,
        "spec_wizards": spec_wizards,
        "has_controllers": bool(spec.get("controllers")),
        "has_import_export": has_import_export,
        "import_export_wizards": import_export_wizards,
    }
    if has_import_export:
        ctx["external_dependencies"] = {"python": ["openpyxl"]}
    return ctx


def _track_artifacts(state: Any, spec: dict[str, Any], module_dir: Path) -> Any:
    """Track artifact state transitions for all generated files."""
    try:
        from odoo_gen_utils.artifact_state import ArtifactKind, ArtifactStatus
    except Exception:
        return state
    transitions = [("MANIFEST", "__manifest__", "__manifest__.py")]
    for model in spec.get("models", []):
        mv = _to_python_var(model["name"])
        transitions.append(("MODEL", model["name"], f"models/{mv}.py"))
        transitions.append(("VIEW", model["name"], f"views/{mv}_views.xml"))
        transitions.append(("TEST", model["name"], f"tests/test_{mv}.py"))
    transitions.append(("SECURITY", "ir.model.access.csv", "security/ir.model.access.csv"))
    for kind_name, art_name, file_path in transitions:
        try:
            kind = getattr(ArtifactKind, kind_name, None)
            if kind is not None:
                state = state.transition(
                    kind=kind.value, name=art_name, file_path=file_path,
                    new_status=ArtifactStatus.GENERATED.value,
                )
        except Exception:
            pass
    return state


def render_module(
    spec: dict[str, Any],
    template_dir: Path,
    output_dir: Path,
    verifier: "EnvironmentVerifier | None" = None,
) -> "tuple[list[Path], list[VerificationWarning]]":
    """Orchestrate rendering of a complete Odoo module via 10 stage functions.

    Args:
        spec: Module specification dictionary with module_name, models, etc.
        template_dir: Path to Jinja2 template files (kept for backward compat).
        output_dir: Root directory where the module will be created.
        verifier: Optional EnvironmentVerifier for inline MCP-backed verification.

    Returns:
        Tuple of (created_files, verification_warnings).
    """
    # Phase 28: validate no circular dependencies FIRST
    _validate_no_cycles(spec)

    env = create_versioned_renderer(spec.get("odoo_version", "17.0"))
    spec = _process_relationships(spec)
    # Phase 36: initialize override_sources for all models
    for model in spec.get("models", []):
        if "override_sources" not in model:
            model["override_sources"] = defaultdict(set)
    # Phase 28: process computation chains
    spec = _process_computation_chains(spec)
    # Phase 29: process complex constraints
    spec = _process_constraints(spec)
    # Phase 33: performance optimization (index, store, sql_constraints, transient config)
    spec = _process_performance(spec)
    # Phase 34: production patterns (bulk create, ORM cache)
    spec = _process_production_patterns(spec)
    module_name = spec["module_name"]
    module_dir = output_dir / module_name
    ctx = _build_module_context(spec, module_name)
    all_warnings: list = []

    try:
        from odoo_gen_utils.artifact_state import ModuleState, save_state
        _state: ModuleState | None = ModuleState(module_name=module_name)
    except Exception:
        _state = None

    created_files: list[Path] = []
    stages = [
        lambda: render_manifest(env, spec, module_dir, ctx),
        lambda: render_models(env, spec, module_dir, ctx, verifier=verifier, warnings_out=all_warnings),
        lambda: render_views(env, spec, module_dir, ctx),
        lambda: render_security(env, spec, module_dir, ctx),
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

    if _state is not None:
        _state = _track_artifacts(_state, spec, module_dir)
        try:
            save_state(_state, module_dir)
        except Exception:
            pass
    return created_files, all_warnings
