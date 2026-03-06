"""Preprocessing functions for Odoo module spec enrichment."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from graphlib import CycleError, TopologicalSorter
from typing import Any

logger = logging.getLogger(__name__)

from odoo_gen_utils.renderer_utils import (
    _to_class,
    _to_python_var,
    _topologically_sort_fields,
    INDEXABLE_TYPES,
    NON_INDEXABLE_TYPES,
)


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

        new_model = {
            **model,
            "complex_constraints": enriched_constraints,
            "create_constraints": create_constraints,
            "write_constraints": write_constraints,
            "has_create_override": bool(create_constraints),
            "has_write_override": bool(write_constraints),
        }

        # Override flag migration: use set[str] via override_sources
        if create_constraints:
            new_model.setdefault("override_sources", defaultdict(set))["create"].add("constraints")
        if write_constraints:
            new_model.setdefault("override_sources", defaultdict(set))["write"].add("constraints")

        new_models.append(new_model)

    return {**spec, "models": new_models}


def _process_performance(spec: dict[str, Any]) -> dict[str, Any]:
    """Enrich fields with index/store and models with _order/_sql_constraints.

    Analyzes:
    1. Search view fields (Char/Many2one/Selection) -> index=True
    2. Record rule domains (company_id) -> index=True
    3. Model _order -> index=True on order fields
    4. Computed fields in tree views/search/order -> store=True
    5. unique_together spec -> _sql_constraints
    6. TransientModel flag -> _transient_max_hours/_transient_max_count

    Pure function -- does NOT mutate the input spec.
    """
    models = spec.get("models", [])
    if not models:
        return spec

    new_models = []
    for model in models:
        new_model = _enrich_model_performance(model)
        new_models.append(new_model)

    return {**spec, "models": new_models}


def _enrich_model_performance(model: dict[str, Any]) -> dict[str, Any]:
    """Enrich a single model dict with performance attributes.

    Pure function -- returns a new model dict without mutating the input.
    """
    fields = model.get("fields", [])
    field_names = {f["name"] for f in fields}

    # --- Determine which fields need index=True ---

    # Search view fields: Char, Many2one (appear in <search>), Selection (group-by)
    search_fields = {
        f["name"] for f in fields
        if f.get("type") in ("Char", "Many2one", "Selection")
        and not f.get("internal")
    }

    # Order fields: parse model.order
    order_str = model.get("order", "")
    order_parts = [part.strip().split()[0] for part in order_str.split(",") if part.strip()]
    order_fields = {name for name in order_parts if name in field_names}

    # Domain fields: company_id is used in record rules
    domain_fields: set[str] = set()
    if any(f["name"] == "company_id" for f in fields):
        domain_fields.add("company_id")

    index_fields = search_fields | order_fields | domain_fields

    # --- Determine which computed fields need store=True ---

    # View fields (excluding internal)
    view_fields = [f for f in fields if not f.get("internal")]

    # Tree view fields: first 6 non-One2many/Html/Text fields
    tree_fields: set[str] = set()
    count = 0
    for f in view_fields:
        if f.get("type") not in ("One2many", "Html", "Text"):
            tree_fields.add(f["name"])
            count += 1
            if count >= 6:
                break

    visible_fields = tree_fields | search_fields | order_fields

    # --- Build new fields list (immutable) ---
    new_fields = []
    for field in fields:
        enriched = {**field}
        ftype = field.get("type", "")

        # Index enrichment
        if field["name"] in index_fields and ftype in INDEXABLE_TYPES:
            enriched["index"] = True

        # Store enrichment for computed fields
        if field.get("compute") and field["name"] in visible_fields:
            if not field.get("store"):
                enriched["store"] = True

        new_fields.append(enriched)

    new_model: dict[str, Any] = {**model, "fields": new_fields}

    # --- model_order: validated _order string ---
    if order_str:
        valid_parts = []
        for part in order_str.split(","):
            part = part.strip()
            if not part:
                continue
            field_name = part.split()[0]
            if field_name in field_names:
                valid_parts.append(part)
        if valid_parts:
            new_model["model_order"] = ", ".join(valid_parts)

    # --- unique_together -> sql_constraints ---
    unique_together = model.get("unique_together", [])
    if unique_together:
        sql_constraints = list(model.get("sql_constraints", []))
        for unique in unique_together:
            ufields = unique.get("fields", [])
            # Validate all fields exist
            if not all(fname in field_names for fname in ufields):
                continue
            constraint_name = "unique_" + "_".join(ufields)
            definition = "UNIQUE(%s)" % ", ".join(ufields)
            message = unique.get("message", "%s must be unique." % ", ".join(ufields))
            sql_constraints.append({
                "name": constraint_name,
                "definition": definition,
                "message": message,
            })
        new_model["sql_constraints"] = sql_constraints

    # --- TransientModel cleanup ---
    if model.get("transient"):
        new_model["transient_max_hours"] = model.get("transient_max_hours", 1.0)
        new_model["transient_max_count"] = model.get("transient_max_count", 0)

    return new_model


def _process_production_patterns(spec: dict[str, Any]) -> dict[str, Any]:
    """Enrich models with bulk create, ORM cache, and archival production patterns.

    Analyzes:
    1. bulk:true -> is_bulk=True, override_sources["create"].add("bulk")
    2. cacheable:true -> is_cacheable=True, needs_tools=True,
       override_sources["create"].add("cache"), override_sources["write"].add("cache"),
       cache_lookup_field (from cache_key or first unique Char or "name")
    3. archival:true -> is_archival=True, active field injection,
       archival wizard in spec["wizards"], archival cron in spec["cron_jobs"]

    Preserves existing override_sources from Phase 29 constraints (union, don't replace).

    Pure function -- does NOT mutate the input spec.
    """
    models = spec.get("models", [])
    if not models:
        return spec

    new_models = []
    new_wizards = list(spec.get("wizards", []))
    new_cron_jobs = list(spec.get("cron_jobs", []))

    for model in models:
        new_model = {**model, "fields": list(model.get("fields", []))}

        is_bulk = bool(model.get("bulk"))
        is_cacheable = bool(model.get("cacheable"))
        is_archival = bool(model.get("archival"))

        if not is_bulk and not is_cacheable and not is_archival:
            new_models.append(new_model)
            continue

        if is_bulk:
            new_model["is_bulk"] = True
            new_model["has_create_override"] = True
            new_model.setdefault("override_sources", defaultdict(set))["create"].add("bulk")

        if is_cacheable:
            new_model["is_cacheable"] = True
            new_model["needs_tools"] = True
            new_model["has_create_override"] = True
            new_model["has_write_override"] = True
            new_model.setdefault("override_sources", defaultdict(set))["create"].add("cache")
            new_model.setdefault("override_sources", defaultdict(set))["write"].add("cache")

            # Determine cache lookup field
            cache_key = model.get("cache_key")
            if cache_key:
                new_model["cache_lookup_field"] = cache_key
            else:
                # Find first unique Char field
                fields = model.get("fields", [])
                unique_char = next(
                    (f["name"] for f in fields
                     if f.get("type") == "Char" and f.get("unique")),
                    None,
                )
                new_model["cache_lookup_field"] = unique_char or "name"

        if is_archival:
            new_model["is_archival"] = True
            new_model["archival_batch_size"] = model.get("archival_batch_size", 100)
            new_model["archival_days"] = model.get("archival_days", 365)

            # Inject active field if not already present
            existing_field_names = {f["name"] for f in new_model["fields"]}
            if "active" not in existing_field_names:
                new_model["fields"] = [
                    *new_model["fields"],
                    {
                        "name": "active",
                        "type": "Boolean",
                        "default": True,
                        "index": True,
                        "string": "Active",
                    },
                ]

            # Inject archival wizard into spec wizards
            wizard_name = f"{model['name']}.archive.wizard"
            new_wizards.append({
                "name": wizard_name,
                "target_model": model["name"],
                "template": "archival_wizard.py.j2",
                "form_template": "archival_wizard_form.xml.j2",
                "fields": [
                    {
                        "name": "days_threshold",
                        "type": "Integer",
                        "string": "Archive records older than (days)",
                        "default": 365,
                        "required": True,
                    },
                ],
                "transient_max_hours": 1.0,
            })

            # Inject archival cron into spec cron_jobs
            new_cron_jobs.append({
                "name": f"Archive Old {model.get('description', model['name'])} Records",
                "model_name": model["name"],
                "method": "_cron_archive_old_records",
                "interval_number": 1,
                "interval_type": "days",
                "doall": False,
            })

        # Preserve existing override flags from Phase 29 (OR, don't replace)
        if model.get("has_create_override"):
            new_model["has_create_override"] = True
        if model.get("has_write_override"):
            new_model["has_write_override"] = True

        # Preserve existing override_sources from Phase 29 (union via setdefault)
        existing_sources = model.get("override_sources")
        if existing_sources:
            merged = new_model.setdefault("override_sources", defaultdict(set))
            for key, sources in existing_sources.items():
                merged[key].update(sources)

        new_models.append(new_model)

    return {**spec, "models": new_models, "wizards": new_wizards, "cron_jobs": new_cron_jobs}


def _parse_crud(crud_str: str) -> dict[str, int]:
    """Convert a CRUD string like 'cru' to permission dict.

    Characters: c=create, r=read, u=write/update, d=delete/unlink.
    Normalizes to lowercase. Raises ValueError on invalid characters.

    Returns:
        Dict with perm_create, perm_read, perm_write, perm_unlink as 0/1.
    """
    normalized = crud_str.lower()
    valid_chars = set("crud")
    invalid = set(normalized) - valid_chars
    if invalid:
        msg = f"CRUD string '{crud_str}' contains invalid characters: {sorted(invalid)}"
        raise ValueError(msg)
    return {
        "perm_create": int("c" in normalized),
        "perm_read": int("r" in normalized),
        "perm_write": int("u" in normalized),
        "perm_unlink": int("d" in normalized),
    }


def _security_validate_spec(security: dict[str, Any]) -> None:
    """Validate that defaults keys exactly match roles array.

    Also validates CRUD strings contain only c, r, u, d.
    Raises ValueError on mismatch.
    """
    roles_set = set(security.get("roles", []))
    defaults_keys = set(security.get("defaults", {}).keys())
    if roles_set != defaults_keys:
        missing = roles_set - defaults_keys
        extra = defaults_keys - roles_set
        parts = []
        if missing:
            parts.append(f"missing from defaults: {sorted(missing)}")
        if extra:
            parts.append(f"extra in defaults: {sorted(extra)}")
        msg = f"Security defaults keys must match roles array. {'; '.join(parts)}"
        raise ValueError(msg)
    # Validate CRUD strings
    for role, crud in security.get("defaults", {}).items():
        _parse_crud(crud)
    # Validate per-model ACL overrides
    for model_name, acl in security.get("acl", {}).items():
        for role, crud in acl.items():
            _parse_crud(crud)


def _security_build_roles(
    module_name: str, security: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build list of role dicts with xml_id, implied_ids chain, labels.

    Roles ordered lowest-to-highest per security['roles'] array order.
    Lowest role implies base.group_user; each subsequent role implies the previous.
    """
    roles_list = security["roles"]
    result: list[dict[str, Any]] = []
    for i, role_name in enumerate(roles_list):
        if i == 0:
            implied_ids = "base.group_user"
        else:
            prev_role = roles_list[i - 1]
            implied_ids = f"group_{module_name}_{prev_role}"
        is_highest = i == len(roles_list) - 1
        result.append({
            "name": role_name,
            "label": role_name.replace("_", " ").title(),
            "xml_id": f"group_{module_name}_{role_name}",
            "implied_ids": implied_ids,
            "is_highest": is_highest,
        })
    return result


def _security_build_acl_matrix(
    spec: dict[str, Any], security: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build security_acl list on each model from defaults with per-model overrides.

    Returns new model list with security_acl injected on each model.
    """
    defaults = security.get("defaults", {})
    acl_overrides = security.get("acl", {})
    roles = security["roles"]

    new_models = []
    for model in spec.get("models", []):
        model_acl_override = acl_overrides.get(model["name"], {})
        acl_entries = []
        for role in roles:
            crud_str = model_acl_override.get(role, defaults.get(role, ""))
            perms = _parse_crud(crud_str)
            acl_entries.append({
                "role": role,
                **perms,
            })
        new_models.append({**model, "security_acl": acl_entries})
    return new_models


def _security_detect_record_rule_scopes(model: dict[str, Any]) -> list[str]:
    """Auto-detect record rule scopes from model fields.

    Scopes:
    - 'ownership': if field named user_id (Many2one) or create_uid exists
    - 'department': if field named department_id exists
    - 'company': if field named company_id (Many2one) exists

    If model has 'record_rules' key, use that instead (override).
    """
    if "record_rules" in model:
        return list(model["record_rules"])

    fields = model.get("fields", [])
    scopes: list[str] = []

    has_user_id = any(
        f.get("name") == "user_id" and f.get("type") == "Many2one"
        for f in fields
    )
    has_create_uid = any(f.get("name") == "create_uid" for f in fields)
    if has_user_id or has_create_uid:
        scopes.append("ownership")

    if any(f.get("name") == "department_id" for f in fields):
        scopes.append("department")

    if any(
        f.get("name") == "company_id" and f.get("type") == "Many2one"
        for f in fields
    ):
        scopes.append("company")

    return scopes


def _security_enrich_fields(
    spec: dict[str, Any],
    roles: list[dict[str, Any]],
) -> dict[str, Any]:
    """Enrich model fields with groups= attribute for sensitive/restricted fields.

    - sensitive:true fields without explicit groups get highest role group
    - Bare role name in groups (e.g. 'manager') resolved to full external ID
    - Full external IDs (containing '.') are left as-is
    - Non-sensitive fields without groups are unchanged

    Pure function -- does NOT mutate the input spec.
    """
    module_name = spec["module_name"]
    role_names = {r["name"] for r in roles}
    highest_role = next((r for r in roles if r.get("is_highest")), roles[-1] if roles else None)

    new_models = []
    for model in spec.get("models", []):
        new_fields = []
        for field in model.get("fields", []):
            enriched = {**field}
            groups_val = field.get("groups")

            if field.get("sensitive") and not groups_val:
                # Default to highest role group
                if highest_role:
                    enriched["groups"] = f"{module_name}.{highest_role['xml_id']}"
            elif groups_val:
                if "." in groups_val:
                    # Full external ID -- keep as-is
                    pass
                elif groups_val in role_names:
                    # Bare role name -- resolve to full external ID
                    enriched["groups"] = f"{module_name}.group_{module_name}_{groups_val}"

            new_fields.append(enriched)
        new_models.append({**model, "fields": new_fields})

    return {**spec, "models": new_models}


def _security_auto_fix_views(spec: dict[str, Any]) -> dict[str, Any]:
    """Auto-fix view fields referencing restricted fields by adding view_groups.

    For each model, builds a set of restricted field names (those with 'groups' key),
    then adds 'view_groups' key to each restricted field with the same groups value.
    Logs INFO for each auto-fixed field.

    Also cross-references restricted fields against:
    1. Search view candidates (Char/Many2one/Selection) -- warns if restricted field
       would appear in search view accessible to lower-privilege roles.
    2. Computed field dependencies -- warns if a non-restricted computed field depends
       on a restricted field, exposing the value through the computed chain.

    Pure function -- does NOT mutate the input spec.
    """
    new_models = []
    for model in spec.get("models", []):
        fields = model.get("fields", [])
        model_name = model.get("name", "")

        # Build restricted field lookup: name -> groups value
        restricted = {
            f["name"]: f["groups"]
            for f in fields
            if f.get("groups")
        }

        if not restricted:
            new_models.append(model)
            continue

        # Cross-reference: search view candidates
        search_field_types = ("Char", "Many2one", "Selection")
        for field in fields:
            fname = field.get("name", "")
            if fname in restricted and field.get("type") in search_field_types:
                logger.warning(
                    "Restricted field '%s' (groups='%s') is a %s field that may "
                    "appear in search view for model '%s'. Lower-privilege roles "
                    "will not see this field in search filters.",
                    fname,
                    restricted[fname],
                    field.get("type"),
                    model_name,
                )

        # Cross-reference: computed field dependencies
        for field in fields:
            fname = field.get("name", "")
            deps = field.get("depends", [])
            if fname not in restricted and deps:
                # Check if any dependency is a restricted field
                for dep in deps:
                    dep_base = dep.split(".")[0]  # handle dotted paths
                    if dep_base in restricted:
                        logger.warning(
                            "Computed field '%s' in model '%s' depends on "
                            "restricted field '%s' (groups='%s'). The computed "
                            "value may expose restricted data to lower-privilege roles.",
                            fname,
                            model_name,
                            dep_base,
                            restricted[dep_base],
                        )

        new_fields = []
        for field in fields:
            fname = field.get("name", "")
            if fname in restricted:
                enriched = {**field, "view_groups": restricted[fname]}
                logger.info(
                    "Auto-applied groups='%s' to field '%s' in views for model '%s'",
                    restricted[fname],
                    fname,
                    model_name,
                )
                new_fields.append(enriched)
            else:
                new_fields.append(field)
        new_models.append({**model, "fields": new_fields})

    return {**spec, "models": new_models}


def _inject_legacy_security(spec: dict[str, Any]) -> dict[str, Any]:
    """Inject legacy User/Manager two-tier security when no security block exists.

    Returns new spec with security_roles and enriched models.
    """
    module_name = spec["module_name"]
    legacy_security = {
        "roles": ["user", "manager"],
        "defaults": {
            "user": "cru",
            "manager": "crud",
        },
    }
    roles = _security_build_roles(module_name, legacy_security)
    new_models = _security_build_acl_matrix(spec, legacy_security)

    # Detect record rule scopes for each model
    enriched_models = []
    for model in new_models:
        scopes = _security_detect_record_rule_scopes(model)
        enriched_models.append({**model, "record_rule_scopes": scopes})

    result = {**spec, "security_roles": roles, "models": enriched_models}
    result = _security_enrich_fields(result, roles)
    result = _security_auto_fix_views(result)
    return result


def _process_security_patterns(spec: dict[str, Any]) -> dict[str, Any]:
    """Pre-process security section, building RBAC infrastructure.

    If no security block: injects legacy User/Manager two-tier system.
    If security block present: validates, builds role hierarchy, ACL matrix,
    and record rule scopes.

    Returns a new spec dict with:
    - security_roles: list of role dicts with xml_id, implied_ids, etc.
    - models enriched with security_acl and record_rule_scopes

    Pure function -- does NOT mutate the input spec.
    """
    security = spec.get("security")
    if not security:
        return _inject_legacy_security(spec)

    module_name = spec["module_name"]

    # Validate
    _security_validate_spec(security)

    # Build roles
    roles = _security_build_roles(module_name, security)

    # Build ACL matrix
    new_models = _security_build_acl_matrix(spec, security)

    # Detect record rule scopes for each model
    enriched_models = []
    for model in new_models:
        scopes = _security_detect_record_rule_scopes(model)
        enriched_models.append({**model, "record_rule_scopes": scopes})

    result = {**spec, "security_roles": roles, "models": enriched_models}
    result = _security_enrich_fields(result, roles)
    result = _security_auto_fix_views(result)
    return result


def _build_audit_log_model(
    module_name: str, audited_models: list[dict[str, Any]]
) -> dict[str, Any]:
    """Synthesize the audit.trail.log companion model dict.

    This model stores one row per write()/create()/unlink() call on audited models.
    Fields: res_model, res_id, changes, user_id, operation.

    Args:
        module_name: Technical module name.
        audited_models: List of model dicts that have audit=True.

    Returns:
        Model dict suitable for appending to spec["models"].
    """
    return {
        "name": "audit.trail.log",
        "description": "Audit Trail Log",
        "_synthesized": True,
        "_is_audit_log": True,
        "chatter": False,
        "audit": False,
        "fields": [
            {
                "name": "res_model",
                "type": "Char",
                "string": "Resource Model",
                "required": True,
                "index": True,
                "readonly": True,
            },
            {
                "name": "res_id",
                "type": "Many2oneReference",
                "string": "Resource ID",
                "model_field": "res_model",
                "readonly": True,
            },
            {
                "name": "changes",
                "type": "Json",
                "string": "Changes",
                "readonly": True,
            },
            {
                "name": "user_id",
                "type": "Many2one",
                "comodel_name": "res.users",
                "string": "User",
                "required": True,
                "readonly": True,
                "index": True,
            },
            {
                "name": "operation",
                "type": "Selection",
                "selection": [
                    ("write", "Write"),
                    ("create", "Create"),
                    ("unlink", "Delete"),
                ],
                "string": "Operation",
                "required": True,
                "readonly": True,
            },
        ],
    }


def _process_audit_patterns(spec: dict[str, Any]) -> dict[str, Any]:
    """Pre-process audit trail configuration, enriching audited models.

    Scans models for ``audit: true``. For each audited model:
    1. Builds exclude set (auto-exclude + spec audit_exclude)
    2. Computes audit_fields (fields not in exclude set)
    3. Sets has_audit, audit_fields, audit_exclude, has_write_override
    4. Adds "audit" to override_sources["write"]

    Also:
    - Synthesizes audit.trail.log companion model
    - Injects auditor role if not already present
    - Sets ACL on audit.trail.log: read-only for auditor + highest role

    Returns a new spec dict. Pure function -- does NOT mutate the input spec.
    """
    models = spec.get("models", [])
    audited = [m for m in models if m.get("audit")]
    if not audited:
        return spec

    module_name = spec["module_name"]

    # Auto-exclude constants
    ALWAYS_EXCLUDE = {"message_ids", "activity_ids", "write_date", "write_uid"}
    SKIP_TYPES = {"One2many", "Many2many", "Binary"}

    new_models = []
    for model in models:
        if not model.get("audit"):
            new_models.append(model)
            continue

        # Shallow-copy model and deep-copy fields list
        new_model = {**model, "fields": list(model.get("fields", []))}

        # Build exclude set
        spec_excludes = set(model.get("audit_exclude", []))
        type_excludes = {
            f["name"]
            for f in model.get("fields", [])
            if f.get("type") in SKIP_TYPES
        }
        all_excludes = ALWAYS_EXCLUDE | spec_excludes | type_excludes

        # Compute auditable fields
        auditable_fields = [
            f for f in model.get("fields", [])
            if f["name"] not in all_excludes
        ]

        new_model["has_audit"] = True
        new_model["audit_fields"] = auditable_fields
        new_model["audit_exclude"] = sorted(all_excludes)
        new_model["has_write_override"] = True

        # Add "audit" to override_sources["write"] -- preserve existing sources
        existing_sources = model.get("override_sources")
        if existing_sources:
            # Copy the defaultdict and its sets
            merged = defaultdict(set)
            for key, sources in existing_sources.items():
                merged[key].update(sources)
            new_model["override_sources"] = merged
        else:
            new_model.setdefault("override_sources", defaultdict(set))
        new_model["override_sources"]["write"].add("audit")

        new_models.append(new_model)

    # Synthesize audit.trail.log model
    audit_log_model = _build_audit_log_model(module_name, audited)

    # Inject auditor role if needed
    security_roles = list(spec.get("security_roles", []))
    role_names = {r["name"] for r in security_roles}

    if "auditor" not in role_names:
        auditor_role = {
            "name": "auditor",
            "label": "Auditor",
            "xml_id": f"group_{module_name}_auditor",
            "implied_ids": "base.group_user",
            "is_highest": False,
        }
        security_roles.append(auditor_role)

    # Set ACL on audit.trail.log: read-only for auditor + highest role, no access for others
    highest_role = next(
        (r for r in security_roles if r.get("is_highest")),
        security_roles[-1] if security_roles else None,
    )
    audit_acl = []
    for role in security_roles:
        if role["name"] == "auditor" or (highest_role and role["name"] == highest_role["name"]):
            audit_acl.append({
                "role": role["name"],
                "perm_read": 1,
                "perm_write": 0,
                "perm_create": 0,
                "perm_unlink": 0,
            })
        else:
            audit_acl.append({
                "role": role["name"],
                "perm_read": 0,
                "perm_write": 0,
                "perm_create": 0,
                "perm_unlink": 0,
            })
    audit_log_model["security_acl"] = audit_acl

    new_models.append(audit_log_model)

    return {
        **spec,
        "models": new_models,
        "security_roles": security_roles,
        "has_audit_log": True,
    }


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
