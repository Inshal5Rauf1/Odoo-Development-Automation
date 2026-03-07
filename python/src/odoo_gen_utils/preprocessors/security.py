"""Security pattern processing (RBAC, ACL, record rules, field groups)."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from odoo_gen_utils.preprocessors._registry import register_preprocessor
from odoo_gen_utils.renderer_utils import _to_python_var

logger = logging.getLogger(__name__)


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
    if model.get("record_rules") is not None:
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


@register_preprocessor(order=60, name="security_patterns")
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
