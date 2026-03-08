"""Jinja2 rendering engine with Odoo-specific filters for module scaffolding."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from odoo_gen_utils.validation.types import Result

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

from odoo_gen_utils.preprocessors import run_preprocessors
from odoo_gen_utils.preprocessors.validation import _validate_no_cycles
from odoo_gen_utils.spec_schema import validate_spec

# Backward-compatible re-exports: tests import these from renderer
from odoo_gen_utils.preprocessors import (  # noqa: F401
    _process_computation_chains,
    _process_constraints,
    _process_performance,
    _process_production_patterns,
    _process_relationships,
    _process_security_patterns,
)

from odoo_gen_utils.context7 import build_context7_from_env, context7_enrich

from odoo_gen_utils.renderer_context import (
    _build_model_context,
    _build_module_context,
    _compute_manifest_data,
    _compute_view_files,
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
        created: list[Path] = []
        created.append(
            render_template(env, "security_group.xml.j2", module_dir / "security" / "security.xml", module_context)
        )
        created.append(
            render_template(env, "access_csv.j2", module_dir / "security" / "ir.model.access.csv", module_context)
        )
        # Phase 37: render record_rules.xml when any model has record_rule_scopes
        has_record_rules = module_context.get("has_record_rules", False)
        if has_record_rules:
            created.append(render_template(
                env, "record_rules.xml.j2", module_dir / "security" / "record_rules.xml",
                module_context,
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


_PKR_CURRENCY_XML = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<odoo>\n'
    '    <data noupdate="0">\n'
    '        <!-- Activate Pakistani Rupee from base module -->\n'
    '        <record id="base.PKR" model="res.currency" forcecreate="false">\n'
    '            <field name="active" eval="True"/>\n'
    '        </record>\n'
    '    </data>\n'
    '</odoo>\n'
)


def _render_document_type_xml(
    doc_types: list[dict[str, Any]], module_name: str
) -> str:
    """Generate noupdate XML records for document type seed data.

    Args:
        doc_types: List of document type dicts with name, code, required_for, etc.
        module_name: Module technical name for XML ID prefix.

    Returns:
        XML string with <odoo><data noupdate="1"> records.
    """
    lines: list[str] = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<odoo>",
        '    <data noupdate="1">',
    ]
    for dt in doc_types:
        code = dt.get("code", "")
        xml_id = f"{module_name}.document_type_{code}"
        lines.append(f'        <record id="{xml_id}" model="document.type">')
        lines.append(f'            <field name="name">{dt.get("name", "")}</field>')
        lines.append(f'            <field name="code">{code}</field>')
        if "required_for" in dt:
            lines.append(f'            <field name="required_for">{dt["required_for"]}</field>')
        if "max_file_size" in dt:
            lines.append(f'            <field name="max_file_size" eval="{dt["max_file_size"]}"/>')
        if "allowed_mime_types" in dt:
            lines.append(f'            <field name="allowed_mime_types">{dt["allowed_mime_types"]}</field>')
        lines.append("        </record>")
    lines.append("    </data>")
    lines.append("</odoo>")
    lines.append("")
    return "\n".join(lines)


def _render_extra_data_files(spec: dict[str, Any], module_dir: Path) -> list[Path]:
    """Render extra data files injected by localization preprocessors (Phase 49)."""
    created: list[Path] = []
    for extra_file in spec.get("extra_data_files", []):
        extra_path = module_dir / extra_file
        extra_path.parent.mkdir(parents=True, exist_ok=True)
        if extra_file == "data/pk_currency_data.xml":
            extra_path.write_text(_PKR_CURRENCY_XML, encoding="utf-8")
            created.append(extra_path)
        elif extra_file == "data/document_type_data.xml":
            # Phase 52: document type seed data from preprocessor
            doc_types = spec.get("_document_type_seed_data", [])
            if not doc_types:
                # Fall back to document_config.default_types
                doc_types = spec.get("document_config", {}).get("default_types", [])
            if doc_types:
                xml_content = _render_document_type_xml(
                    doc_types, spec.get("module_name", "module")
                )
                extra_path.write_text(xml_content, encoding="utf-8")
                created.append(extra_path)
    return created


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
        # Phase 49: extra data files (e.g., Pakistan PKR currency activation)
        created.extend(_render_extra_data_files(spec, module_dir))
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


def render_mail_templates(
    env: Environment,
    spec: dict[str, Any],
    module_dir: Path,
    module_context: dict[str, Any],
) -> "Result[list[Path]]":
    """Render mail_template_data.xml when notifications are present.

    Collects all notification_templates across all models into a flat list
    and renders them via mail_template_data.xml.j2.

    Returns Result.ok([]) when no notifications are present.
    """
    models = spec.get("models", [])
    notification_models = [m for m in models if m.get("has_notifications")]
    if not notification_models:
        return Result.ok([])

    try:
        all_templates: list[dict[str, Any]] = []
        for model in notification_models:
            all_templates.extend(model.get("notification_templates", []))

        if not all_templates:
            return Result.ok([])

        mail_ctx = {
            **module_context,
            "notification_templates": all_templates,
        }
        path = render_template(
            env, "mail_template_data.xml.j2",
            module_dir / "data" / "mail_template_data.xml",
            mail_ctx,
        )
        return Result.ok([path])
    except Exception as exc:
        return Result.fail(f"render_mail_templates failed: {exc}")


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
    *,
    no_context7: bool = False,
    fresh_context7: bool = False,
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
    # Phase 47: Validate spec against Pydantic schema BEFORE any processing
    validated = validate_spec(spec)
    spec = validated.model_dump(exclude_none=True)  # Convert back to dict for preprocessor pipeline

    # Phase 28: validate no circular dependencies BEFORE any preprocessing
    _validate_no_cycles(spec)

    env = create_versioned_renderer(spec.get("odoo_version", "17.0"))
    # Phase 45: single call replaces 10 individual preprocessor calls + override_sources loop
    spec = run_preprocessors(spec)
    # Phase 42: Context7 documentation enrichment
    if no_context7:
        c7_hints: dict[str, str] = {}
    else:
        _c7_client = build_context7_from_env()
        _c7_cache = Path(".odoo-gen-cache/context7")
        c7_hints = context7_enrich(
            spec, _c7_client,
            cache_dir=_c7_cache,
            fresh=fresh_context7,
            odoo_version=spec.get("odoo_version", "17.0"),
        )
    module_name = spec["module_name"]
    module_dir = output_dir / module_name
    ctx = _build_module_context(spec, module_name)
    ctx["c7_hints"] = c7_hints  # Phase 42: inject Context7 hints
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

    if _state is not None:
        _state = _track_artifacts(_state, spec, module_dir)
        try:
            save_state(_state, module_dir)
        except Exception:
            pass
    return created_files, all_warnings
