"""Audit trail pattern processing."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from odoo_gen_utils.preprocessors._registry import register_preprocessor
from odoo_gen_utils.renderer_utils import _to_class

logger = logging.getLogger(__name__)


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
        "record_rule_scopes": [],
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


@register_preprocessor(order=70, name="audit_patterns")
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
