"""Jinja2 rendering engine with Odoo-specific filters for module scaffolding."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


# Sequence field names that trigger ir.sequence generation.
SEQUENCE_FIELD_NAMES: frozenset[str] = frozenset({"reference", "ref", "number", "code", "sequence"})


def _model_ref(name: str) -> str:
    """Convert Odoo dot-notation model name to external ID format.

    Example: "inventory.item" -> "model_inventory_item"
    """
    return f"model_{name.replace('.', '_')}"


def _to_class(name: str) -> str:
    """Convert Odoo dot-notation model name to Python class name.

    Example: "inventory.item" -> "InventoryItem"
    """
    return "".join(word.capitalize() for word in name.replace(".", "_").split("_"))


def _to_python_var(name: str) -> str:
    """Convert Odoo dot-notation model name to Python variable name.

    Example: "inventory.item" -> "inventory_item"
    """
    return name.replace(".", "_")


def _to_xml_id(name: str) -> str:
    """Convert Odoo dot-notation model name to XML id attribute format.

    Example: "inventory.item" -> "inventory_item"
    """
    return name.replace(".", "_")


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
    has_constraints = any(
        f.get("constraints") for f in fields
    ) or bool(model.get("sql_constraints"))

    # Phase 5 extensions ---------------------------------------------------
    computed_fields = [f for f in fields if f.get("compute")]
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

    # Phase 6: multi-company field detection
    has_company_field = any(
        f.get("name") == "company_id" and f.get("type") == "Many2one"
        for f in fields
    )

    # Phase 12: mail.thread auto-inheritance (TMPL-01)
    explicit_inherit = model.get("inherit")
    inherit_list = [explicit_inherit] if explicit_inherit else []
    if "mail" in spec.get("depends", []):
        for mixin in ("mail.thread", "mail.activity.mixin"):
            if mixin not in inherit_list:
                inherit_list.append(mixin)

    # Phase 12: conditional api import (TMPL-02)
    needs_api = bool(computed_fields or onchange_fields or constrained_fields or sequence_fields)

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


def render_module(spec: dict[str, Any], template_dir: Path, output_dir: Path) -> list[Path]:
    """Render a complete Odoo module from a specification dictionary.

    Produces the full OCA directory structure:
        __manifest__.py, __init__.py, models/, views/, security/,
        tests/, demo/, static/description/, README.rst,
        data/ (sequences.xml + data.xml), wizards/ (if spec has wizards)

    When ``odoo_version`` is present in *spec*, templates are loaded from the
    corresponding versioned directory (e.g. ``templates/18.0/``) with a fallback
    to ``templates/shared/``.  The *template_dir* parameter is still accepted for
    backward compatibility but is ignored when the spec contains ``odoo_version``.

    Args:
        spec: Module specification dictionary with module_name, models, etc.
        template_dir: Path to Jinja2 template files.
        output_dir: Root directory where the module will be created.

    Returns:
        List of all created file paths.
    """
    version = spec.get("odoo_version", "17.0")
    env = create_versioned_renderer(version)
    module_name = spec["module_name"]
    module_dir = output_dir / module_name
    created_files: list[Path] = []

    models = spec.get("models", [])
    spec_wizards = spec.get("wizards", [])
    has_wizards = bool(spec_wizards)

    # Detect sequence fields across all models
    models_with_sequences = [
        m for m in models
        if any(
            f.get("type") == "Char"
            and f.get("name") in SEQUENCE_FIELD_NAMES
            and f.get("required")
            for f in m.get("fields", [])
        )
    ]
    has_sequences = bool(models_with_sequences)

    # Detect models with company_id field (Phase 6 record rules)
    models_with_company_field = [
        m for m in models
        if any(
            f.get("name") == "company_id" and f.get("type") == "Many2one"
            for f in m.get("fields", [])
        )
    ]
    has_company_modules = bool(models_with_company_field)

    # Enrich model dicts with has_company_field for template access
    enriched_models = []
    for m in models:
        m_copy = dict(m)
        m_copy["has_company_field"] = any(
            f.get("name") == "company_id" and f.get("type") == "Many2one"
            for f in m.get("fields", [])
        )
        enriched_models.append(m_copy)

    # Compute data files for manifest (canonical order)
    data_files: list[str] = []
    if has_sequences:
        data_files.append("data/sequences.xml")
    data_files.append("data/data.xml")

    # Compute wizard view files for manifest
    wizard_view_files: list[str] = []
    for wizard in spec_wizards:
        wizard_xml_id = _to_xml_id(wizard["name"])
        wizard_view_files.append(f"views/{wizard_xml_id}_wizard_form.xml")

    # Compute manifest file list with canonical ordering
    all_manifest_files = _compute_manifest_data(spec, data_files, wizard_view_files, has_company_modules=has_company_modules)

    # -- Shared context for module-level templates --
    module_context = {
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
        "manifest_files": all_manifest_files,
        "has_wizards": has_wizards,
        "spec_wizards": spec_wizards,
    }

    # 1. __manifest__.py (uses updated manifest_files with canonical ordering)
    created_files.append(
        render_template(env, "manifest.py.j2", module_dir / "__manifest__.py", module_context)
    )

    # 2. Root __init__.py (conditionally imports wizards)
    created_files.append(
        render_template(env, "init_root.py.j2", module_dir / "__init__.py", module_context)
    )

    # 3. models/__init__.py
    created_files.append(
        render_template(env, "init_models.py.j2", module_dir / "models" / "__init__.py", module_context)
    )

    # 4. Per-model files
    for model in models:
        model_ctx = _build_model_context(spec, model)
        model_var = _to_python_var(model["name"])

        # models/<model_var>.py
        created_files.append(
            render_template(env, "model.py.j2", module_dir / "models" / f"{model_var}.py", model_ctx)
        )

        # views/<model_var>_views.xml (form + tree + search combined)
        created_files.append(
            render_template(env, "view_form.xml.j2", module_dir / "views" / f"{model_var}_views.xml", model_ctx)
        )

        # views/<model_var>_action.xml
        created_files.append(
            render_template(env, "action.xml.j2", module_dir / "views" / f"{model_var}_action.xml", model_ctx)
        )

    # 5. views/menu.xml (single menu file for all models)
    created_files.append(
        render_template(env, "menu.xml.j2", module_dir / "views" / "menu.xml", module_context)
    )

    # 6. security/security.xml
    created_files.append(
        render_template(env, "security_group.xml.j2", module_dir / "security" / "security.xml", module_context)
    )

    # 7. security/ir.model.access.csv
    created_files.append(
        render_template(env, "access_csv.j2", module_dir / "security" / "ir.model.access.csv", module_context)
    )

    # 7b. security/record_rules.xml (if any model has company_id field)
    if has_company_modules:
        record_rules_ctx = {
            **module_context,
            "models": enriched_models,
        }
        created_files.append(
            render_template(
                env,
                "record_rules.xml.j2",
                module_dir / "security" / "record_rules.xml",
                record_rules_ctx,
            )
        )

    # 8. data/data.xml (always emit as stub)
    data_xml_path = module_dir / "data" / "data.xml"
    data_xml_path.parent.mkdir(parents=True, exist_ok=True)
    data_xml_path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<odoo>\n"
        "    <!-- Static data records go here -->\n"
        "</odoo>\n",
        encoding="utf-8",
    )
    created_files.append(data_xml_path)

    # 9. data/sequences.xml (if any model has sequence fields)
    if has_sequences:
        # Build sequences context: all sequence models + their sequence fields
        sequences_ctx = {
            **module_context,
            "sequence_models": [
                {
                    "model": m,
                    "model_var": _to_python_var(m["name"]),
                    "sequence_fields": [
                        f for f in m.get("fields", [])
                        if f.get("type") == "Char"
                        and f.get("name") in SEQUENCE_FIELD_NAMES
                        and f.get("required")
                    ],
                }
                for m in models_with_sequences
            ],
        }
        created_files.append(
            render_template(
                env,
                "sequences.xml.j2",
                module_dir / "data" / "sequences.xml",
                sequences_ctx,
            )
        )

    # 10. Wizard files (if spec has wizards)
    if has_wizards:
        # wizards/__init__.py
        wizards_ctx = {**module_context}
        created_files.append(
            render_template(
                env,
                "init_wizards.py.j2",
                module_dir / "wizards" / "__init__.py",
                wizards_ctx,
            )
        )

        # Per-wizard files
        for wizard in spec_wizards:
            wizard_var = _to_python_var(wizard["name"])
            wizard_xml_id = _to_xml_id(wizard["name"])
            wizard_ctx = {
                **module_context,
                "wizard": wizard,
                "wizard_var": wizard_var,
                "wizard_xml_id": wizard_xml_id,
                "wizard_class": _to_class(wizard["name"]),
            }

            # wizards/<wizard_var>.py
            created_files.append(
                render_template(
                    env,
                    "wizard.py.j2",
                    module_dir / "wizards" / f"{wizard_var}.py",
                    wizard_ctx,
                )
            )

            # views/<wizard_xml_id>_wizard_form.xml
            created_files.append(
                render_template(
                    env,
                    "wizard_form.xml.j2",
                    module_dir / "views" / f"{wizard_xml_id}_wizard_form.xml",
                    wizard_ctx,
                )
            )

    # 11. tests/__init__.py
    created_files.append(
        render_template(env, "init_tests.py.j2", module_dir / "tests" / "__init__.py", module_context)
    )

    # 12. Per-model test files
    for model in models:
        model_ctx = _build_model_context(spec, model)
        model_var = _to_python_var(model["name"])
        created_files.append(
            render_template(
                env, "test_model.py.j2", module_dir / "tests" / f"test_{model_var}.py", model_ctx
            )
        )

    # 13. demo/demo_data.xml
    created_files.append(
        render_template(env, "demo_data.xml.j2", module_dir / "demo" / "demo_data.xml", module_context)
    )

    # 14. static/description/index.html
    static_dir = module_dir / "static" / "description"
    static_dir.mkdir(parents=True, exist_ok=True)
    index_html = static_dir / "index.html"
    index_html.write_text(
        '<!DOCTYPE html>\n<html>\n<head><title>Module Description</title></head>\n'
        '<body><p>See README.rst for module documentation.</p></body>\n</html>\n',
        encoding="utf-8",
    )
    created_files.append(index_html)

    # 15. README.rst
    created_files.append(
        render_template(env, "readme.rst.j2", module_dir / "README.rst", module_context)
    )

    return created_files
