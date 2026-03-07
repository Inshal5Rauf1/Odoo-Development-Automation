"""Approval workflow pattern processing."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from odoo_gen_utils.preprocessors._registry import register_preprocessor

logger = logging.getLogger(__name__)


@register_preprocessor(order=80, name="approval_patterns")
def _process_approval_patterns(spec: dict[str, Any]) -> dict[str, Any]:
    """Pre-process approval workflow configuration, enriching approval models.

    For each model with an ``approval`` block:
    1. Validates role references against ``security_roles`` (skip if ``group`` explicit)
    2. Synthesizes state Selection field (draft + levels + terminal + optional rejected)
    3. Builds action method specs for each level transition
    4. Resolves group XML IDs (role-based or explicit override)
    5. Builds submit, reject, and reset action specs
    6. Sets lock_after, editable_fields for stage locking
    7. Builds approval_record_rules (two-tier: draft-owner + manager-full)
    8. Adds ``"approval"`` to ``override_sources["write"]``
    9. Sets ``has_write_override = True``, ``needs_translate = True``
    10. Adds ``"approval"`` to ``record_rule_scopes``

    Returns a new spec dict. Pure function -- does NOT mutate the input spec.
    """
    models = spec.get("models", [])
    approval_models = [m for m in models if m.get("approval")]
    if not approval_models:
        return spec

    module_name = spec["module_name"]
    security_roles = spec.get("security_roles", [])
    role_lookup = {r["name"]: r for r in security_roles}

    new_models = []
    for model in models:
        if not model.get("approval"):
            new_models.append(model)
            continue

        # Shallow-copy model and deep-copy fields list
        new_model = {**model, "fields": list(model.get("fields", []))}
        approval = model["approval"]
        levels = approval["levels"]

        # 1. Validate all roles exist in security_roles (skip if group explicit)
        for level in levels:
            role = level.get("role")
            if role and role not in role_lookup and not level.get("group"):
                raise ValueError(
                    f"Approval role '{role}' not found in security_roles. "
                    f"Available roles: {list(role_lookup.keys())}"
                )

        # 2. Build state Selection with auto-prepended draft
        initial_label = approval.get("initial_label", "Draft")
        state_selection: list[tuple[str, str]] = [("draft", initial_label)]
        for level in levels:
            label = level.get("label", level["state"].replace("_", " ").title())
            state_selection.append((level["state"], label))
        # Terminal state from last level's "next"
        terminal = levels[-1]["next"]
        terminal_label = terminal.replace("_", " ").title()
        state_selection.append((terminal, terminal_label))
        # Optional rejected state
        on_reject = approval.get("on_reject", "draft")
        if on_reject == "rejected":
            state_selection.append(("rejected", "Rejected"))

        # 3. Remove any existing state/status Selection field from model fields
        new_model["fields"] = [
            f for f in new_model["fields"]
            if not (f.get("name") in ("state", "status") and f.get("type") == "Selection")
        ]

        # 4. Inject synthesized state field
        state_field = {
            "name": "state",
            "type": "Selection",
            "selection": state_selection,
            "default": "draft",
            "tracking": True,
            "required": True,
        }
        new_model["fields"].insert(0, state_field)

        # 5. Build action method specs -- one per level
        action_methods = []
        for i, level in enumerate(levels):
            if i == 0:
                from_state = "draft"
                from_state_label = initial_label
            else:
                from_state = levels[i - 1]["state"]
                from_state_label = levels[i - 1].get(
                    "label", levels[i - 1]["state"].replace("_", " ").title()
                )

            group_xml_id = level.get("group") or (
                f"{module_name}.group_{module_name}_{level['role']}"
            )
            role_label = role_lookup.get(level.get("role", ""), {}).get(
                "label", level.get("role", "").replace("_", " ").title()
            )

            action_methods.append({
                "name": f"action_approve_{level['state']}",
                "from_state": from_state,
                "to_state": level["state"],
                "from_state_label": from_state_label,
                "group_xml_id": group_xml_id,
                "role_label": role_label,
                "button_label": f"Approve ({role_label})",
            })

        # 6. Build submit action (draft -> first level)
        first_level = levels[0]
        submit_action = {
            "name": "action_submit",
            "from_state": "draft",
            "to_state": first_level["state"],
            "from_state_label": initial_label,
            "group_xml_id": "",
            "role_label": "",
            "button_label": "Submit",
        }

        # 7. Build reject action (if reject_allowed_from non-empty or defaults to all non-terminal)
        reject_allowed_from = approval.get("reject_allowed_from")
        if reject_allowed_from is None:
            # Default: all non-terminal level states
            reject_allowed_from = [level["state"] for level in levels]
        reject_action = None
        if reject_allowed_from:
            reject_action = {
                "name": "action_reject",
                "to_state": on_reject,
                "reject_allowed_from": reject_allowed_from,
            }

        # 8. Build reset action (always generated)
        reset_action = {
            "name": "action_reset_to_draft",
            "to_state": "draft",
        }

        # 9. Build approval_record_rules (two-tier)
        model_var = model["name"].replace(".", "_")
        record_rules = [
            {
                "xml_id": f"rule_{model_var}_draft",
                "name": f"{model['description']}: Draft Records",
                "domain_force": "['|', ('state', '!=', 'draft'), ('create_uid', '=', user.id)]",
                "scope": "draft_owner",
            },
            {
                "xml_id": f"rule_{model_var}_manager",
                "name": f"{model['description']}: Manager Full Access",
                "domain_force": "[(1, '=', 1)]",
                "scope": "manager_full",
            },
        ]

        # 10. Set all enrichment keys on model
        new_model["has_approval"] = True
        new_model["approval_levels"] = levels
        new_model["approval_action_methods"] = action_methods
        new_model["approval_submit_action"] = submit_action
        new_model["approval_reject_action"] = reject_action
        new_model["approval_reset_action"] = reset_action
        new_model["approval_state_field_name"] = "state"
        new_model["lock_after"] = approval.get("lock_after", "draft")
        new_model["editable_fields"] = approval.get("editable_fields", [])
        new_model["on_reject"] = on_reject
        new_model["reject_allowed_from"] = reject_allowed_from
        new_model["approval_record_rules"] = record_rules
        new_model["needs_translate"] = True

        # 11. Add "approval" to override_sources["write"]
        existing_sources = model.get("override_sources")
        if existing_sources:
            merged = defaultdict(set)
            for key, sources in existing_sources.items():
                merged[key].update(sources)
            new_model["override_sources"] = merged
        else:
            new_model.setdefault("override_sources", defaultdict(set))
        new_model["override_sources"]["write"].add("approval")
        new_model["has_write_override"] = True

        # 12. Add "approval" to record_rule_scopes
        existing_scopes = list(model.get("record_rule_scopes", []))
        if "approval" not in existing_scopes:
            existing_scopes.append("approval")
        new_model["record_rule_scopes"] = existing_scopes

        new_models.append(new_model)

    return {**spec, "models": new_models}
