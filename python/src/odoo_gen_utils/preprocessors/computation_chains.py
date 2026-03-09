"""Sequence-based computation chain preprocessor.

Registered at order=22 (after relationships@10, extensions@12,
init_override_sources@15). Parses computation_chains entries via
ChainSpec Pydantic model, auto-adds fields, sets @api.depends
with dot notation, and enriches field dicts with chain metadata.

Pure function -- never mutates input spec.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from odoo_gen_utils.preprocessors._registry import register_preprocessor
from odoo_gen_utils.spec_schema import ChainSpec, ChainStepSpec

logger = logging.getLogger(__name__)


def _ensure_chain_field(
    model_fields: list[dict[str, Any]],
    step: ChainStepSpec,
) -> list[dict[str, Any]]:
    """Ensure a chain step's field exists on the model.

    If the field is missing, creates a new field dict.
    If it already exists, returns a copy of the list unchanged --
    merging happens in _merge_chain_into_field.

    Returns a NEW list (never mutates the input).
    """
    existing = [f for f in model_fields if f.get("name") == step.field]
    if existing:
        return list(model_fields)

    new_field: dict[str, Any] = {
        "name": step.field,
        "type": step.type,
    }
    if step.digits is not None:
        new_field["digits"] = step.digits
    return [*model_fields, new_field]


def _merge_chain_into_field(
    field: dict[str, Any],
    step: ChainStepSpec,
) -> dict[str, Any]:
    """Merge chain attributes into an existing field dict.

    For direct_input steps: no compute, no store override.
    For computed steps: set store=True, compute, depends.

    Returns a NEW dict (never mutates input).
    """
    if step.source == "direct_input":
        return dict(field)

    merged = {
        **field,
        "store": True,
        "compute": field.get("compute") or f"_compute_{step.field}",
        "depends": list(step.depends),
    }
    return merged


def _build_chain_meta(
    chain: ChainSpec,
    step: ChainStepSpec,
    step_index: int,
) -> dict[str, Any]:
    """Build _chain_meta dict for a chain step."""
    upstream = [
        {
            "model": s.model,
            "field": s.field,
            "source": s.source,
            "type": s.type,
        }
        for s in chain.steps[:step_index]
    ]
    downstream = [
        {
            "model": s.model,
            "field": s.field,
            "source": s.source,
            "type": s.type,
        }
        for s in chain.steps[step_index + 1:]
    ]
    meta: dict[str, Any] = {
        "chain_id": chain.chain_id,
        "chain_description": chain.description,
        "position_in_chain": step_index,
        "total_steps": len(chain.steps),
        "source": step.source,
        "upstream_steps": upstream,
        "downstream_steps": downstream,
    }
    if step.aggregation is not None:
        meta["aggregation"] = step.aggregation
    if step.lookup_table is not None:
        meta["lookup_table"] = dict(step.lookup_table)
    return meta


def _enrich_model(
    model: dict[str, Any],
    steps_for_model: list[tuple[ChainSpec, ChainStepSpec, int]],
) -> dict[str, Any]:
    """Apply all chain steps targeting this model.

    Returns a NEW model dict with enriched fields.
    """
    fields = list(model.get("fields", []))

    for chain, step, step_index in steps_for_model:
        # Ensure field exists
        fields = _ensure_chain_field(fields, step)

        # Merge chain attrs and attach meta
        new_fields = []
        for f in fields:
            if f.get("name") == step.field:
                merged = _merge_chain_into_field(f, step)
                merged["_chain_meta"] = _build_chain_meta(chain, step, step_index)
                new_fields.append(merged)
            else:
                new_fields.append(dict(f))
        fields = new_fields

    return {**model, "fields": fields}


@register_preprocessor(order=22, name="computation_chains")
def _process_computation_chains(spec: dict[str, Any]) -> dict[str, Any]:
    """Enrich computed field specs from sequence-based computation_chains.

    For each validated chain:
    1. Parse via ChainSpec Pydantic model
    2. For each step, ensure field exists on model
    3. Set store=True, compute, depends for non-direct_input steps
    4. Attach _chain_meta with full chain awareness
    5. Store validated chains in spec["_computation_chains"]

    Returns a new spec dict. Pure function.
    """
    raw_chains = spec.get("computation_chains", [])
    if not raw_chains:
        return spec

    # Parse and validate chains -- support both old and new format
    validated_chains: list[ChainSpec] = []
    old_format_chains: list[dict[str, Any]] = []

    for raw in raw_chains:
        # Old per-field format has "field" key, not "chain_id"
        if "field" in raw and "chain_id" not in raw:
            old_format_chains.append(raw)
            continue
        try:
            chain = ChainSpec(**raw)
            validated_chains.append(chain)
        except ValidationError as exc:
            chain_id = raw.get("chain_id", "unknown")
            logger.warning("Skipping invalid chain '%s': %s", chain_id, exc)
            continue

    # If only old-format chains, fall back to legacy behavior
    if not validated_chains and old_format_chains:
        return _process_old_format(spec, old_format_chains)

    if not validated_chains:
        return spec

    # Build lookup: model_name -> [(chain, step, step_index)]
    model_steps: dict[str, list[tuple[ChainSpec, ChainStepSpec, int]]] = {}
    for chain in validated_chains:
        for idx, step in enumerate(chain.steps):
            model_steps.setdefault(step.model, []).append((chain, step, idx))

    # Enrich models
    new_models = []
    seen_models: set[str] = set()
    for model in spec.get("models", []):
        model_name = model["name"]
        seen_models.add(model_name)
        steps = model_steps.get(model_name)
        if steps:
            new_models.append(_enrich_model(model, steps))
        else:
            new_models.append(
                {**model, "fields": [dict(f) for f in model.get("fields", [])]}
            )

    # Warn about chain steps targeting models not in spec
    for model_name in model_steps:
        if model_name not in seen_models:
            logger.warning(
                "Chain step references model '%s' not found in spec models",
                model_name,
            )

    return {
        **spec,
        "models": new_models,
        "_computation_chains": [c.model_dump() for c in validated_chains],
    }


def _process_old_format(
    spec: dict[str, Any],
    chains: list[dict[str, Any]],
) -> dict[str, Any]:
    """Legacy handler for old per-field chain format.

    Maintains backward compatibility with specs using:
      {"field": "model.field_name", "depends_on": [...]}
    """
    chain_lookup: dict[str, dict[str, dict[str, Any]]] = {}
    for chain in chains:
        parts = chain["field"].rsplit(".", 1)
        model_name, field_name = parts[0], parts[1]
        chain_lookup.setdefault(model_name, {})[field_name] = chain

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
