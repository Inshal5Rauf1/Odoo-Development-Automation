"""Constraint enrichment for model specs."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from odoo_gen_utils.preprocessors._registry import register_preprocessor


@register_preprocessor(order=30, name="constraints")
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
