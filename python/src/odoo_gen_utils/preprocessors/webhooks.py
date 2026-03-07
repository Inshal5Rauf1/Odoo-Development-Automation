"""Webhook pattern processing."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from odoo_gen_utils.preprocessors._registry import register_preprocessor

logger = logging.getLogger(__name__)


@register_preprocessor(order=100, name="webhook_patterns")
def _process_webhook_patterns(spec: dict[str, Any]) -> dict[str, Any]:
    """Pre-process webhook configuration on models.

    For each model with a ``webhooks`` block:
    1. Parses ``on_create`` (bool), ``on_write`` (field list), ``on_unlink`` (bool)
    2. Sets ``webhook_config``, ``webhook_watched_fields``, ``has_webhooks``
    3. Sets ``webhook_on_create``, ``webhook_on_write``, ``webhook_on_unlink``
    4. Adds ``"webhooks"`` to ``override_sources["create"]`` if ``on_create``
    5. Adds ``"webhooks"`` to ``override_sources["write"]`` if ``on_write`` non-empty

    Returns a new spec dict. Pure function -- does NOT mutate the input spec.
    """
    models = spec.get("models", [])
    webhook_models = [m for m in models if m.get("webhooks")]
    if not webhook_models:
        return spec

    new_models = []
    for model in models:
        webhooks = model.get("webhooks")
        if not webhooks:
            new_models.append(model)
            continue

        # Shallow copy model
        new_model = {**model}

        on_create = webhooks.get("on_create", False)
        on_write = webhooks.get("on_write", [])
        on_unlink = webhooks.get("on_unlink", False)

        new_model["has_webhooks"] = True
        new_model["webhook_config"] = {
            "on_create": on_create,
            "on_write": on_write,
            "on_unlink": on_unlink,
        }
        new_model["webhook_watched_fields"] = on_write
        new_model["webhook_on_create"] = on_create
        new_model["webhook_on_write"] = bool(on_write)
        new_model["webhook_on_unlink"] = on_unlink

        # Merge override_sources (same pattern as approval preprocessor)
        existing_sources = model.get("override_sources")
        if existing_sources:
            merged = defaultdict(set)
            for key, sources in existing_sources.items():
                merged[key].update(sources)
            new_model["override_sources"] = merged
        else:
            new_model.setdefault("override_sources", defaultdict(set))

        if on_create:
            new_model["override_sources"]["create"].add("webhooks")
        if on_write:
            new_model["override_sources"]["write"].add("webhooks")

        new_models.append(new_model)

    return {**spec, "models": new_models}
