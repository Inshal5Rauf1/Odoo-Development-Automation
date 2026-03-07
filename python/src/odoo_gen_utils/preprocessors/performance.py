"""Performance enrichment for model fields and indexes."""

from __future__ import annotations

from typing import Any

from odoo_gen_utils.preprocessors._registry import register_preprocessor
from odoo_gen_utils.renderer_utils import INDEXABLE_TYPES, NON_INDEXABLE_TYPES


@register_preprocessor(order=40, name="performance")
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
