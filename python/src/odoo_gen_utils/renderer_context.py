"""Context builders for Jinja2 rendering of Odoo module templates.

Extracted from renderer.py -- builds model-level and module-level template
contexts consumed by the render stage functions.
"""

from __future__ import annotations

from typing import Any

from odoo_gen_utils.renderer_utils import (
    _is_monetary_field,
    _to_class,
    _to_python_var,
    _to_xml_id,
    _topologically_sort_fields,
    SEQUENCE_FIELD_NAMES,
)


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

    # Phase 38: audit trail context keys (defaults prevent StrictUndefined crashes)
    has_audit = model.get("has_audit", False)
    audit_fields = model.get("audit_fields", [])
    audit_field_names = {f["name"] for f in audit_fields}
    audit_exclude = model.get("audit_exclude", [])

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
        # Phase 38 keys
        "has_audit": has_audit,
        "audit_fields": audit_fields,
        "audit_field_names": audit_field_names,
        "audit_exclude": audit_exclude,
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
    has_record_rules = any(m.get("record_rule_scopes") for m in models)
    manifest_files = _compute_manifest_data(
        spec, data_files, wiz_files,
        has_company_modules=has_company or has_record_rules,
    )
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
        "security_roles": spec.get("security_roles", []),
        "has_record_rules": has_record_rules,
        # Phase 38 keys
        "has_audit_log": spec.get("has_audit_log", False),
    }
    if has_import_export:
        ctx["external_dependencies"] = {"python": ["openpyxl"]}
    return ctx
