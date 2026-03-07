"""Notification pattern processing for approval workflows."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from odoo_gen_utils.preprocessors._registry import register_preprocessor

logger = logging.getLogger(__name__)

# Technical/internal fields excluded from notification email body
_NOTIFICATION_EXCLUDE_NAMES = frozenset({
    "create_uid", "write_uid", "create_date", "write_date",
    "message_ids", "activity_ids", "parent_path", "state",
})

# Field types excluded from notification email body
_NOTIFICATION_EXCLUDE_TYPES = frozenset({"Binary", "One2many", "Many2many"})


def _resolve_recipient(
    recipient: str,
    module_name: str,
    security_roles: list[dict[str, Any]],
) -> str:
    """Resolve a recipient expression to an ``email_to`` template value.

    Supported recipient formats:
    - ``"creator"`` -- record's ``create_uid.partner_id``
    - ``"role:{name}"`` -- users in the named security group
    - ``"field:{field}"`` -- Many2one to ``res.users``/``res.partner`` on the model
    - ``"fixed:{email}"`` -- hardcoded email address

    Returns:
        The ``email_to`` string value.
    """
    if recipient == "creator":
        return "{{ object.create_uid.partner_id.email }}"

    if recipient.startswith("role:"):
        role_name = recipient[5:]
        group_ref = f"{module_name}.group_{module_name}_{role_name}"
        return (
            "{{ ','.join(env.ref('"
            + group_ref
            + "').users.mapped('email')) }}"
        )

    if recipient.startswith("field:"):
        field_name = recipient[6:]
        return "{{ object." + field_name + ".email }}"

    if recipient.startswith("fixed:"):
        return recipient[6:]

    # Fallback -- treat as fixed
    return recipient


def _select_body_fields(
    model: dict[str, Any],
    max_fields: int = 4,
) -> list[dict[str, str]]:
    """Select fields suitable for an auto-generated notification email body.

    Priority:
    1. ``name``/``display_name`` first (always if present)
    2. Required fields
    3. Fields with a ``string`` attribute

    Excludes:
    - Binary, One2many, Many2many types
    - Computed fields (have ``compute`` key)
    - Technical field names (create_uid, write_uid, etc.)

    Returns:
        List of dicts with ``name`` and ``label`` keys.
    """
    fields = model.get("fields", [])
    candidates: list[dict[str, str]] = []
    priority_names: list[dict[str, str]] = []

    for field in fields:
        fname = field.get("name", "")
        ftype = field.get("type", "")

        # Skip excluded types
        if ftype in _NOTIFICATION_EXCLUDE_TYPES:
            continue
        # Skip excluded names
        if fname in _NOTIFICATION_EXCLUDE_NAMES:
            continue
        # Skip computed fields
        if field.get("compute"):
            continue

        label = field.get("string") or fname.replace("_", " ").title()
        entry = {"name": fname, "label": label}

        # Priority: name/display_name always first
        if fname in ("name", "display_name"):
            priority_names.append(entry)
        elif field.get("required"):
            candidates.insert(0, entry)
        elif field.get("string"):
            candidates.append(entry)
        else:
            candidates.append(entry)

    result = priority_names + candidates
    return result[:max_fields]


@register_preprocessor(order=90, name="notification_patterns")
def _process_notification_patterns(spec: dict[str, Any]) -> dict[str, Any]:
    """Pre-process notification configuration on approval models.

    For each model with ``has_approval`` and approval levels containing ``notify``
    objects:
    1. Builds ``notification_templates`` list with template metadata
    2. Enriches ``approval_action_methods`` entries with ``notification`` sub-dict
    3. Enriches ``approval_submit_action`` (level 0 notify) and
       ``approval_reject_action`` (``on_reject_notify``)
    4. Sets ``has_notifications=True``, ``needs_logger=True`` on model
    5. Sets ``has_notification_models=True`` on spec
    6. Adds ``"mail"`` to ``spec["depends"]`` if not present

    Returns a new spec dict. Pure function -- does NOT mutate the input spec.
    """
    models = spec.get("models", [])
    module_name = spec["module_name"]
    security_roles = spec.get("security_roles", [])

    has_any_notifications = False
    new_models = []

    for model in models:
        if not model.get("has_approval"):
            new_models.append(model)
            continue

        # Gather notify objects from the original approval block
        # The approval block is on the *original* model (before approval preprocessor)
        # but after approval preprocessing, model has approval_levels which are the
        # same level dicts (with notify objects still present).
        approval_levels = model.get("approval_levels", [])
        approval_block = model.get("approval", {})

        # Check if any level has notify, or if on_reject_notify is present
        level_notifies = [
            (i, level.get("notify"))
            for i, level in enumerate(approval_levels)
            if level.get("notify")
        ]
        on_reject_notify = approval_block.get("on_reject_notify")

        if not level_notifies and not on_reject_notify:
            new_models.append(model)
            continue

        has_any_notifications = True

        # Shallow copy model + deep copy mutable lists
        new_model = {
            **model,
            "approval_action_methods": [
                {**m} for m in model.get("approval_action_methods", [])
            ],
        }
        if model.get("approval_submit_action"):
            new_model["approval_submit_action"] = {**model["approval_submit_action"]}
        if model.get("approval_reject_action"):
            new_model["approval_reject_action"] = {**model["approval_reject_action"]}

        notification_templates: list[dict[str, Any]] = []
        model_xml_id = model["name"].replace(".", "_")
        body_fields = _select_body_fields(model)

        # Process level notifies
        for level_idx, notify in level_notifies:
            template_name = notify["template"]
            xml_id = template_name
            email_to = _resolve_recipient(
                notify["recipients"], module_name, security_roles,
            )
            level = approval_levels[level_idx]
            state_label = level.get("label", level["state"].replace("_", " ").title())

            template_entry = {
                "xml_id": xml_id,
                "name": template_name.replace("_", " ").title(),
                "model_xml_id": model_xml_id,
                "subject": notify["subject"],
                "email_to": email_to,
                "body_intro": f"The record has been transitioned to {state_label}.",
                "body_fields": body_fields,
            }
            notification_templates.append(template_entry)

            notification_sub = {
                "template_xml_id": xml_id,
                "send_mail": True,
                "email_to": email_to,
            }

            # Level 0 notify enriches submit action
            if level_idx == 0:
                new_model["approval_submit_action"]["notification"] = notification_sub
            else:
                # Find the matching action method
                target_name = f"action_approve_{level['state']}"
                for method in new_model["approval_action_methods"]:
                    if method["name"] == target_name:
                        method["notification"] = notification_sub
                        break

        # Process on_reject_notify
        if on_reject_notify:
            template_name = on_reject_notify["template"]
            xml_id = template_name
            email_to = _resolve_recipient(
                on_reject_notify["recipients"], module_name, security_roles,
            )
            template_entry = {
                "xml_id": xml_id,
                "name": template_name.replace("_", " ").title(),
                "model_xml_id": model_xml_id,
                "subject": on_reject_notify["subject"],
                "email_to": email_to,
                "body_intro": "The record has been rejected.",
                "body_fields": body_fields,
            }
            notification_templates.append(template_entry)

            notification_sub = {
                "template_xml_id": xml_id,
                "send_mail": True,
                "email_to": email_to,
            }
            if new_model.get("approval_reject_action"):
                new_model["approval_reject_action"]["notification"] = notification_sub

        new_model["has_notifications"] = True
        new_model["needs_logger"] = True
        new_model["notification_templates"] = notification_templates

        new_models.append(new_model)

    if not has_any_notifications:
        return spec

    # Build new spec with updated depends
    new_depends = list(spec.get("depends", []))
    if "mail" not in new_depends:
        new_depends.append("mail")

    return {
        **spec,
        "models": new_models,
        "depends": new_depends,
        "has_notification_models": True,
    }
