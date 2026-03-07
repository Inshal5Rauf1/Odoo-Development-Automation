"""Computation chain enrichment for computed fields."""

from __future__ import annotations

from typing import Any

from odoo_gen_utils.preprocessors._registry import register_preprocessor


@register_preprocessor(order=20, name="computation_chains")
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
