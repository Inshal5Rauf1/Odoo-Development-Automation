"""Per-stub context assembly from spec dict and ModelRegistry.

For each detected :class:`StubInfo`, builds a :class:`StubContext` that
contains everything an LLM (or developer) needs to implement the
method: model fields with type info, related model fields from the
registry, aggregated business rules from the spec, and the source of
cross-module data.

This module is a **leaf** -- it imports only from ``stub_detector``
(sibling) and ``registry`` (parent package), never from renderer or
validation modules.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from odoo_gen_utils.logic_writer.stub_detector import StubInfo
from odoo_gen_utils.registry import ModelEntry, ModelRegistry

logger = logging.getLogger(__name__)

_RELATIONAL_TYPES = frozenset({"Many2one", "One2many", "Many2many"})


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StubContext:
    """Assembled context for a single detected stub."""

    model_fields: dict[str, dict[str, Any]]
    """All fields on the model with type metadata."""

    related_fields: dict[str, dict[str, Any]]
    """Fields on referenced comodels, keyed by comodel name."""

    business_rules: list[str]
    """Flat list of business-rule strings aggregated from the spec."""

    registry_source: str | None
    """``'registry'``, ``'known_models'``, or ``None``."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_stub_context(
    stub: StubInfo,
    spec: dict[str, Any],
    registry: ModelRegistry | None = None,
) -> StubContext:
    """Assemble rich context for *stub* from *spec* and *registry*.

    Steps:
    1. Locate the spec model matching ``stub.model_name``.
    2. Extract all field metadata into ``model_fields``.
    3. Look up comodel fields in the registry for relational fields.
    4. Aggregate business rules from multiple spec locations.
    """
    model = _find_spec_model(stub.model_name, spec)
    if model is None:
        return StubContext(
            model_fields={},
            related_fields={},
            business_rules=[],
            registry_source=None,
        )

    model_fields = _build_model_fields(model)
    related_fields, reg_source = _build_related_fields(model_fields, registry)
    business_rules = _aggregate_business_rules(stub, model, model_fields)

    return StubContext(
        model_fields=model_fields,
        related_fields=related_fields,
        business_rules=business_rules,
        registry_source=reg_source,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_spec_model(
    model_name: str, spec: dict[str, Any]
) -> dict[str, Any] | None:
    """Locate a model dict in *spec* by ``name`` or ``_name``.

    Searches ``spec["models"]`` first, then ``spec.get("wizards", [])``.
    """
    for model in spec.get("models", []):
        if model.get("name") == model_name or model.get("_name") == model_name:
            return model
    for wizard in spec.get("wizards", []):
        if (
            wizard.get("name") == model_name
            or wizard.get("_name") == model_name
        ):
            return wizard
    return None


def _build_model_fields(
    model: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Extract field metadata from *model* into a name-keyed dict."""
    result: dict[str, dict[str, Any]] = {}
    for field_def in model.get("fields", []):
        name = field_def.get("name", "")
        if not name:
            continue
        entry: dict[str, Any] = {}
        for key in (
            "type",
            "string",
            "help",
            "compute",
            "store",
            "depends",
            "constrains",
            "comodel_name",
            "inverse_name",
            "relation",
            "required",
            "readonly",
            "default",
        ):
            if key in field_def:
                entry[key] = field_def[key]
        result[name] = entry
    return result


def _build_related_fields(
    model_fields: dict[str, dict[str, Any]],
    registry: ModelRegistry | None,
) -> tuple[dict[str, dict[str, Any]], str | None]:
    """Look up comodel fields for relational fields in *model_fields*.

    Returns ``(related_fields_dict, registry_source_string)``.
    ``registry_source`` is ``"registry"`` if any comodel came from
    registered modules, ``"known_models"`` if from standard Odoo models,
    or ``None`` if no comodels were found anywhere.
    """
    if registry is None:
        return {}, None

    related: dict[str, dict[str, Any]] = {}
    source: str | None = None

    for _field_name, field_meta in model_fields.items():
        ftype = field_meta.get("type", "")
        comodel = field_meta.get("comodel_name")
        if ftype not in _RELATIONAL_TYPES or not comodel:
            continue
        if comodel in related:
            continue  # already looked up

        # Try registered modules first
        entry: ModelEntry | None = registry.show_model(comodel)
        if entry is not None:
            related[comodel] = dict(entry.fields)
            source = "registry"
            continue

        # Try known Odoo models
        # Access _known_models directly (loaded via load_known_models)
        known = registry._known_models.get(comodel)  # noqa: SLF001
        if known is not None:
            related[comodel] = dict(known.get("fields", {}))
            if source is None:
                source = "known_models"
            continue

        logger.debug("Comodel %s not found in registry or known models", comodel)

    return related, source


def _aggregate_business_rules(
    stub: StubInfo,
    model: dict[str, Any],
    model_fields: dict[str, dict[str, Any]],
) -> list[str]:
    """Collect business-rule strings from all spec locations.

    Sources:
    1. Model description
    2. Field ``help`` texts for target fields
    3. ``complex_constraints`` messages
    4. ``workflow_states`` name + description
    5. ``approval_levels`` name + description
    6. Field ``depends`` lists for target fields
    """
    rules: list[str] = []

    # 1. Model description
    desc = model.get("description", "")
    if desc:
        rules.append(desc)

    # 2. Field help texts for target fields
    for target in stub.target_fields:
        field_meta = model_fields.get(target, {})
        help_text = field_meta.get("help", "")
        if help_text:
            rules.append(help_text)

    # 3. Complex constraints
    for cc in model.get("complex_constraints", []):
        msg = cc.get("message", "")
        if msg:
            rules.append(msg)

    # 4. Workflow states
    for state in model.get("workflow_states", []):
        name = state.get("name", "")
        desc = state.get("description", "")
        if name:
            entry = f"{name}: {desc}" if desc else name
            rules.append(entry)

    # 5. Approval levels
    for level in model.get("approval_levels", []):
        name = level.get("name", "")
        desc = level.get("description", "")
        if name:
            entry = f"{name}: {desc}" if desc else name
            rules.append(entry)

    # 6. Depends for target fields
    for target in stub.target_fields:
        field_meta = model_fields.get(target, {})
        depends = field_meta.get("depends", [])
        if depends:
            rules.append(f"{target} depends on: {', '.join(depends)}")

    return rules
