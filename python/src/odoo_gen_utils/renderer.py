"""Jinja2 rendering engine with Odoo-specific filters for module scaffolding."""

from __future__ import annotations

import json
import re
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from odoo_gen_utils.validation.types import Result

if TYPE_CHECKING:
    from odoo_gen_utils.verifier import EnvironmentVerifier, VerificationWarning


# Sequence field names that trigger ir.sequence generation.
SEQUENCE_FIELD_NAMES: frozenset[str] = frozenset({"reference", "ref", "number", "code", "sequence"})

# Phase 26: Monetary field name patterns that trigger Float -> Monetary rewrite.
MONETARY_FIELD_PATTERNS: frozenset[str] = frozenset({
    "amount", "fee", "salary", "price", "cost", "balance",
    "total", "subtotal", "tax", "discount", "payment",
    "revenue", "expense", "budget", "wage", "rate",
    "charge", "premium", "debit", "credit",
})


def _is_monetary_field(field: dict[str, Any]) -> bool:
    """Check whether a field should be rendered as fields.Monetary.

    Returns True when:
    - field type is already "Monetary", OR
    - field type is "Float" AND the field name contains a monetary pattern keyword.

    Returns False when:
    - field has explicit ``"monetary": False`` opt-out
    - field type is not Float/Monetary
    - field name does not contain any monetary pattern
    """
    if field.get("monetary") is False:
        return False
    field_type = field.get("type", "")
    if field_type == "Monetary":
        return True
    if field_type != "Float":
        return False
    name = field.get("name", "")
    return any(pattern in name for pattern in MONETARY_FIELD_PATTERNS)


def _process_relationships(spec: dict[str, Any]) -> dict[str, Any]:
    """Pre-process relationships section, synthesizing through-models.

    Returns a new spec dict with:
    - Through-models appended to spec["models"]
    - One2many fields injected on parent models for through-models
    - Self-referential M2M fields enriched with relation/column params

    Pure function -- does NOT mutate the input spec.
    """
    relationships = spec.get("relationships", [])
    if not relationships:
        return spec

    # Deep-copy models to avoid mutating the original spec
    new_models = [{**m, "fields": list(m.get("fields", []))} for m in spec.get("models", [])]

    for rel in relationships:
        if rel["type"] == "m2m_through":
            through_model = _synthesize_through_model(rel, spec)
            new_models.append(through_model)
            _inject_one2many_links(new_models, rel)
        elif rel["type"] == "self_m2m":
            _enrich_self_referential_m2m(new_models, rel)

    return {**spec, "models": new_models}


def _synthesize_through_model(
    rel: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    """Synthesize a through-model dict from a m2m_through relationship.

    Returns a model dict suitable for appending to spec["models"].
    Raises ValueError if auto-generated FK names collide with through_fields.
    """
    from_model = rel["from"]
    to_model = rel["to"]
    through_name = rel["through_model"]

    # Derive FK field names from model names
    from_fk = _to_python_var(from_model.rsplit(".", 1)[-1]) + "_id"
    to_fk = _to_python_var(to_model.rsplit(".", 1)[-1]) + "_id"

    # Check for collisions with through_fields
    through_field_names = {f["name"] for f in rel.get("through_fields", [])}
    for fk_name in (from_fk, to_fk):
        if fk_name in through_field_names:
            msg = (
                f"FK name collision: auto-generated '{fk_name}' collides with "
                f"a through_field name in '{through_name}'"
            )
            raise ValueError(msg)

    fields: list[dict[str, Any]] = [
        {
            "name": from_fk,
            "type": "Many2one",
            "comodel_name": from_model,
            "string": from_model.rsplit(".", 1)[-1].replace("_", " ").title(),
            "required": True,
            "ondelete": "cascade",
        },
        {
            "name": to_fk,
            "type": "Many2one",
            "comodel_name": to_model,
            "string": to_model.rsplit(".", 1)[-1].replace("_", " ").title(),
            "required": True,
            "ondelete": "cascade",
        },
    ]
    fields.extend(rel.get("through_fields", []))

    return {
        "name": through_name,
        "description": through_name.rsplit(".", 1)[-1].replace("_", " ").title(),
        "fields": fields,
        "_synthesized": True,
    }


def _inject_one2many_links(
    models: list[dict[str, Any]], rel: dict[str, Any]
) -> None:
    """Inject One2many fields on parent models pointing to through-model.

    Mutates the models list in-place (caller provides a copy).
    Skips injection if a field with the target name already exists.
    """
    through_name = rel["through_model"]
    through_last = through_name.rsplit(".", 1)[-1]
    target_field_name = f"{_to_python_var(through_last)}_ids"

    from_fk = _to_python_var(rel["from"].rsplit(".", 1)[-1]) + "_id"
    to_fk = _to_python_var(rel["to"].rsplit(".", 1)[-1]) + "_id"

    for model in models:
        if model["name"] == rel["from"]:
            if not any(f.get("name") == target_field_name for f in model.get("fields", [])):
                model["fields"].append({
                    "name": target_field_name,
                    "type": "One2many",
                    "comodel_name": through_name,
                    "inverse_name": from_fk,
                    "string": through_last.replace("_", " ").title() + "s",
                })
        elif model["name"] == rel["to"]:
            if not any(f.get("name") == target_field_name for f in model.get("fields", [])):
                model["fields"].append({
                    "name": target_field_name,
                    "type": "One2many",
                    "comodel_name": through_name,
                    "inverse_name": to_fk,
                    "string": through_last.replace("_", " ").title() + "s",
                })


def _enrich_self_referential_m2m(
    models: list[dict[str, Any]], rel: dict[str, Any]
) -> None:
    """Enrich model fields with self-referential M2M relation/column params.

    Mutates the models list in-place (caller provides a copy).
    Adds/replaces fields with explicit relation, column1, column2.
    """
    model_name = rel["model"]
    target_model = next((m for m in models if m["name"] == model_name), None)
    if target_model is None:
        return

    table_base = _to_python_var(model_name)
    field_name = rel["field_name"]
    relation_table = f"{table_base}_{field_name}_rel"

    primary_field: dict[str, Any] = {
        "name": field_name,
        "type": "Many2many",
        "comodel_name": model_name,
        "relation": relation_table,
        "column1": f"{table_base}_id",
        "column2": f"{field_name.rstrip('_ids')}_id",
        "string": rel.get("string", field_name.replace("_", " ").title()),
    }

    inverse_name = rel.get("inverse_field_name")
    inverse_field: dict[str, Any] | None = None
    if inverse_name:
        inverse_field = {
            "name": inverse_name,
            "type": "Many2many",
            "comodel_name": model_name,
            "relation": relation_table,
            "column1": f"{field_name.rstrip('_ids')}_id",  # REVERSED
            "column2": f"{table_base}_id",                   # REVERSED
            "string": rel.get("inverse_string", inverse_name.replace("_", " ").title()),
        }

    # Replace or append fields on the target model
    names_to_remove = {field_name}
    if inverse_name:
        names_to_remove.add(inverse_name)
    fields = [f for f in target_model.get("fields", []) if f.get("name") not in names_to_remove]
    fields.append(primary_field)
    if inverse_field:
        fields.append(inverse_field)
    target_model["fields"] = fields


def _resolve_comodel(
    spec: dict[str, Any], model_name: str, field_name: str
) -> str | None:
    """Resolve the comodel_name of a relational field on a model."""
    for model in spec.get("models", []):
        if model["name"] == model_name:
            for field in model.get("fields", []):
                if field.get("name") == field_name:
                    return field.get("comodel_name")
    return None


def _validate_no_cycles(spec: dict[str, Any]) -> None:
    """Validate that computation_chains contain no circular dependencies.

    Builds a directed graph where nodes are "model.field" identifiers
    and edges represent "depends on" relationships. Uses graphlib to
    detect cycles.

    Raises ValueError with actionable message naming cycle participants.
    """
    chains = spec.get("computation_chains", [])
    if not chains:
        return

    # Build dependency graph: node = "model.field", edges = depends_on
    graph: dict[str, set[str]] = {}
    for chain in chains:
        node = chain["field"]  # e.g., "university.student.gpa"
        model_name = node.rsplit(".", 1)[0]
        deps: set[str] = set()
        for dep in chain.get("depends_on", []):
            if "." in dep:
                # Cross-model: "enrollment_ids.weighted_grade"
                rel_field, target_field = dep.split(".", 1)
                target_model = _resolve_comodel(spec, model_name, rel_field)
                if target_model:
                    deps.add(f"{target_model}.{target_field}")
            else:
                # Local field -- only add if it's also a chain node
                local_node = f"{model_name}.{dep}"
                if any(c["field"] == local_node for c in chains):
                    deps.add(local_node)
        graph[node] = deps

    try:
        ts = TopologicalSorter(graph)
        list(ts.static_order())
    except CycleError as exc:
        cycle_nodes = exc.args[1]
        cycle_str = " -> ".join(str(n) for n in cycle_nodes)
        msg = (
            f"Circular dependency detected in computation_chains: "
            f"{cycle_str}. Break the cycle by removing one dependency."
        )
        raise ValueError(msg) from None


def _process_constraints(spec: dict[str, Any]) -> dict[str, Any]:
    """Enrich model specs with constraint method metadata from constraints section.

    For each constraint:
    1. Classify by type (temporal, cross_model, capacity)
    2. Locate target model in spec
    3. Inject constraint metadata into model dict

    Returns a new spec dict with enriched models. Pure function.
    """
    constraints = spec.get("constraints", [])
    if not constraints:
        return spec

    # Build model name set for validation
    model_names = {m["name"] for m in spec.get("models", [])}

    # Group constraints by model
    model_constraints: dict[str, list[dict[str, Any]]] = {}
    for constraint in constraints:
        model_name = constraint["model"]
        if model_name not in model_names:
            continue  # silently skip constraints for non-existent models
        model_constraints.setdefault(model_name, []).append(constraint)

    if not model_constraints:
        return spec

    # Enrich each constraint with preprocessed metadata
    def _enrich_constraint(c: dict[str, Any]) -> dict[str, Any]:
        enriched = {**c}
        ctype = c["type"]
        if ctype == "temporal":
            # Build check_expr with False guards
            fields = c["fields"]
            guards = " and ".join(f"rec.{f}" for f in fields)
            condition = c["condition"]
            # Prefix field references with rec.
            check_condition = condition
            for field in fields:
                # Replace bare field names with rec.field (word boundary aware)
                check_condition = re.sub(
                    rf"\b{re.escape(field)}\b",
                    f"rec.{field}",
                    check_condition,
                )
            enriched["check_expr"] = f"{guards} and {check_condition}"
        elif ctype == "cross_model":
            # Generate check_body for cross-model validation
            count_domain_field = c["count_domain_field"]
            capacity_model = c["capacity_model"]
            capacity_field = c["capacity_field"]
            related_model = c["related_model"]
            message = c["message"]
            enriched["check_body"] = (
                f"course = rec.{count_domain_field}\n"
                f"count = self.env[\"{related_model}\"].search_count([\n"
                f"    (\"{count_domain_field}\", \"=\", course.id),\n"
                f"])\n"
                f"if course.{capacity_field} and count > course.{capacity_field}:\n"
                f"    raise ValidationError(\n"
                f"        _(\"{message}\",\n"
                f"          course.{capacity_field})\n"
                f"    )"
            )
            enriched["write_trigger_fields"] = c.get("trigger_fields", [])
        elif ctype == "capacity":
            # Generate check_body for capacity validation
            count_model = c.get("count_model", "")
            count_domain_field = c.get("count_domain_field", "")
            max_value = c.get("max_value")
            max_field = c.get("max_field")
            message = c["message"]
            if max_field:
                max_ref = f"rec.{max_field}"
            else:
                max_ref = str(max_value)
            enriched["check_body"] = (
                f"count = self.env[\"{count_model}\"].search_count([\n"
                f"    (\"{count_domain_field}\", \"=\", rec.id),\n"
                f"])\n"
                f"if count > {max_ref}:\n"
                f"    raise ValidationError(\n"
                f"        _(\"{message}\",\n"
                f"          {max_ref})\n"
                f"    )"
            )
            enriched["write_trigger_fields"] = c.get("trigger_fields", [])
        return enriched

    # Deep-copy models and enrich with constraint metadata
    new_models = []
    for model in spec.get("models", []):
        mc = model_constraints.get(model["name"])
        if not mc:
            new_models.append(model)
            continue

        enriched_constraints = [_enrich_constraint(c) for c in mc]
        create_constraints = [
            c for c in enriched_constraints
            if c["type"] in ("cross_model", "capacity")
        ]
        write_constraints = [
            c for c in enriched_constraints
            if c["type"] in ("cross_model", "capacity")
        ]

        new_models.append({
            **model,
            "complex_constraints": enriched_constraints,
            "create_constraints": create_constraints,
            "write_constraints": write_constraints,
            "has_create_override": bool(create_constraints),
            "has_write_override": bool(write_constraints),
        })

    return {**spec, "models": new_models}


def _process_computation_chains(spec: dict[str, Any]) -> dict[str, Any]:
    """Enrich computed field specs from computation_chains section.

    For each chain entry:
    1. Locate the target field in the matching model
    2. Set field.depends = chain.depends_on (the @api.depends paths)
    3. Set field.store = True
    4. Set field.compute if not already set (convention: _compute_{field_name})

    Returns a new spec dict with enriched models. Pure function.
    """
    chains = spec.get("computation_chains", [])
    if not chains:
        return spec

    # Build a lookup: model_name -> {field_name -> chain_entry}
    chain_lookup: dict[str, dict[str, dict]] = {}
    for chain in chains:
        parts = chain["field"].rsplit(".", 1)
        model_name, field_name = parts[0], parts[1]
        chain_lookup.setdefault(model_name, {})[field_name] = chain

    # Deep-copy models and enrich fields
    new_models = []
    for model in spec.get("models", []):
        model_chains = chain_lookup.get(model["name"], {})
        if not model_chains:
            new_models.append(model)
            continue

        new_fields = []
        for field in model.get("fields", []):
            fname = field.get("name", "")
            if fname in model_chains:
                chain = model_chains[fname]
                field = {
                    **field,
                    "depends": chain["depends_on"],
                    "store": True,
                    "compute": field.get("compute", f"_compute_{fname}"),
                }
            new_fields.append(field)
        new_models.append({**model, "fields": new_fields})

    return {**spec, "models": new_models}


def _topologically_sort_fields(
    computed_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort computed fields so dependencies come before dependents.

    Uses graphlib.TopologicalSorter. If fields have no inter-dependencies
    (common case), preserves original order.
    """
    field_names = {f["name"] for f in computed_fields}
    field_map = {f["name"]: f for f in computed_fields}

    graph: dict[str, set[str]] = {}
    for field in computed_fields:
        deps = set()
        for dep in field.get("depends", []):
            # Only consider local dependencies (no dots) that are
            # themselves computed fields
            if "." not in dep and dep in field_names:
                deps.add(dep)
        graph[field["name"]] = deps

    try:
        ts = TopologicalSorter(graph)
        sorted_names = list(ts.static_order())
    except CycleError:
        # Intra-model cycles caught by _validate_no_cycles already
        return computed_fields

    # Rebuild list in sorted order
    result = []
    for name in sorted_names:
        if name in field_map:
            result.append(field_map[name])
    return result


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
    # Phase 29: complex constraints from preprocessor
    complex_constraints = model.get("complex_constraints", [])
    create_constraints = model.get("create_constraints", [])
    write_constraints = model.get("write_constraints", [])
    has_create_override = model.get("has_create_override", False)
    has_write_override = model.get("has_write_override", False)
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

    # Phase 12: conditional api import (TMPL-02)
    # Phase 29: also need api when temporal constraints exist (@api.constrains)
    # or create/write overrides exist (@api.model_create_multi)
    has_temporal = any(c.get("type") == "temporal" for c in complex_constraints)
    needs_api = bool(
        computed_fields or onchange_fields or constrained_fields
        or sequence_fields or has_temporal or has_create_override
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
                    "wizard_xml_id": wxid, "wizard_class": _to_class(wizard["name"]), "needs_api": True}
            created.append(render_template(env, "wizard.py.j2", module_dir / "wizards" / f"{wvar}.py", wctx))
            created.append(render_template(
                env, "wizard_form.xml.j2", module_dir / "views" / f"{wxid}_wizard_form.xml", wctx))
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
    wiz_files = [f"views/{_to_xml_id(w['name'])}_wizard_form.xml" for w in spec_wizards]
    manifest_files = _compute_manifest_data(spec, data_files, wiz_files, has_company_modules=has_company)
    return {
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
        "has_wizards": bool(spec_wizards),
        "spec_wizards": spec_wizards,
    }


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
    """Orchestrate rendering of a complete Odoo module via 7 stage functions.

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
    # Phase 28: process computation chains
    spec = _process_computation_chains(spec)
    # Phase 29: process complex constraints
    spec = _process_constraints(spec)
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
