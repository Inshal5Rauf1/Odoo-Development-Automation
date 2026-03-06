"""Tests for preprocessor functions in odoo_gen_utils.preprocessors.

Phase 38: Unit tests for _process_audit_patterns.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pytest

from odoo_gen_utils.preprocessors import _process_audit_patterns


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec(
    models: list[dict[str, Any]] | None = None,
    security: dict[str, Any] | None = None,
    security_roles: list[dict[str, Any]] | None = None,
    module_name: str = "test_module",
) -> dict[str, Any]:
    """Build a minimal spec for audit preprocessor testing."""
    spec: dict[str, Any] = {
        "module_name": module_name,
        "depends": ["base"],
        "models": models or [],
    }
    if security is not None:
        spec["security"] = security
    if security_roles is not None:
        spec["security_roles"] = security_roles
    return spec


def _make_model(
    name: str = "test.model",
    fields: list[dict[str, Any]] | None = None,
    audit: bool = False,
    audit_exclude: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a minimal model dict for testing."""
    model: dict[str, Any] = {
        "name": name,
        "description": name.replace(".", " ").title(),
        "fields": fields or [
            {"name": "name", "type": "Char", "required": True},
            {"name": "value", "type": "Integer"},
        ],
        **kwargs,
    }
    if audit:
        model["audit"] = True
    if audit_exclude is not None:
        model["audit_exclude"] = audit_exclude
    return model


def _make_security_roles(
    roles: list[str] | None = None,
    module_name: str = "test_module",
) -> list[dict[str, Any]]:
    """Build security_roles list matching _security_build_roles output."""
    roles = roles or ["user", "manager"]
    result = []
    for i, role_name in enumerate(roles):
        is_highest = i == len(roles) - 1
        result.append({
            "name": role_name,
            "label": role_name.replace("_", " ").title(),
            "xml_id": f"group_{module_name}_{role_name}",
            "implied_ids": "base.group_user" if i == 0 else f"group_{module_name}_{roles[i - 1]}",
            "is_highest": is_highest,
        })
    return result


# ---------------------------------------------------------------------------
# TestAuditPreprocessor
# ---------------------------------------------------------------------------


class TestAuditPreprocessor:
    """Test _process_audit_patterns preprocessor."""

    def test_audit_true_enriches_model(self):
        """Spec with audit:true on one model produces has_audit, audit_fields, override_sources[write]=audit."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
                {"name": "email", "type": "Char"},
                {"name": "gpa", "type": "Float"},
            ],
            audit=True,
        )
        spec = _make_spec(
            models=[model],
            security_roles=_make_security_roles(),
        )
        result = _process_audit_patterns(spec)

        # Find the enriched model
        enriched = next(m for m in result["models"] if m["name"] == "university.student")
        assert enriched["has_audit"] is True
        assert isinstance(enriched["audit_fields"], list)
        assert len(enriched["audit_fields"]) > 0
        # All audit_fields should be field dicts with "name" key
        field_names = {f["name"] for f in enriched["audit_fields"]}
        assert "name" in field_names
        assert "email" in field_names
        assert "gpa" in field_names
        # override_sources must include "audit" for "write"
        assert "audit" in enriched["override_sources"]["write"]
        assert enriched["has_write_override"] is True

    def test_audit_true_synthesizes_audit_log_model(self):
        """Spec with audit:true produces audit.trail.log companion model with correct fields."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
            ],
            audit=True,
        )
        spec = _make_spec(
            models=[model],
            security_roles=_make_security_roles(),
        )
        result = _process_audit_patterns(spec)

        # Find synthesized audit.trail.log model
        audit_model = next(
            (m for m in result["models"] if m["name"] == "audit.trail.log"),
            None,
        )
        assert audit_model is not None, "audit.trail.log model not synthesized"

        # Verify required fields
        field_names = {f["name"] for f in audit_model["fields"]}
        assert "res_model" in field_names
        assert "res_id" in field_names
        assert "changes" in field_names
        assert "user_id" in field_names
        assert "operation" in field_names

        # Check specific field attributes
        res_model = next(f for f in audit_model["fields"] if f["name"] == "res_model")
        assert res_model["type"] == "Char"
        assert res_model.get("index") is True
        assert res_model.get("required") is True
        assert res_model.get("readonly") is True

        res_id = next(f for f in audit_model["fields"] if f["name"] == "res_id")
        assert res_id["type"] == "Many2oneReference"
        assert res_id.get("model_field") == "res_model"
        assert res_id.get("readonly") is True

        changes = next(f for f in audit_model["fields"] if f["name"] == "changes")
        assert changes["type"] == "Json"
        assert changes.get("readonly") is True

        user_id = next(f for f in audit_model["fields"] if f["name"] == "user_id")
        assert user_id["type"] == "Many2one"
        assert user_id.get("comodel_name") == "res.users"
        assert user_id.get("required") is True
        assert user_id.get("readonly") is True
        assert user_id.get("index") is True

        operation = next(f for f in audit_model["fields"] if f["name"] == "operation")
        assert operation["type"] == "Selection"
        assert operation.get("required") is True
        assert operation.get("readonly") is True
        # Should have write/create/unlink options
        selection_keys = {s[0] for s in operation.get("selection", [])}
        assert "write" in selection_keys
        assert "create" in selection_keys
        assert "unlink" in selection_keys

        # Metadata flags
        assert audit_model["_synthesized"] is True
        assert audit_model["_is_audit_log"] is True
        assert audit_model.get("chatter") is False
        assert audit_model.get("audit") is False

    def test_audit_auto_excludes_fields(self):
        """Auto-excluded fields (One2many, Many2many, Binary, message_ids, activity_ids, write_date, write_uid) never appear in audit_fields."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
                {"name": "email", "type": "Char"},
                {"name": "photo", "type": "Binary"},
                {"name": "tag_ids", "type": "Many2many", "comodel_name": "university.tag"},
                {"name": "enrollment_ids", "type": "One2many", "comodel_name": "university.enrollment"},
                {"name": "message_ids", "type": "One2many", "comodel_name": "mail.message"},
                {"name": "activity_ids", "type": "One2many", "comodel_name": "mail.activity"},
                {"name": "write_date", "type": "Datetime"},
                {"name": "write_uid", "type": "Many2one", "comodel_name": "res.users"},
            ],
            audit=True,
        )
        spec = _make_spec(
            models=[model],
            security_roles=_make_security_roles(),
        )
        result = _process_audit_patterns(spec)
        enriched = next(m for m in result["models"] if m["name"] == "university.student")

        audit_field_names = {f["name"] for f in enriched["audit_fields"]}
        # Should include name and email
        assert "name" in audit_field_names
        assert "email" in audit_field_names
        # Should NOT include auto-excluded fields
        assert "photo" not in audit_field_names  # Binary
        assert "tag_ids" not in audit_field_names  # Many2many
        assert "enrollment_ids" not in audit_field_names  # One2many
        assert "message_ids" not in audit_field_names  # ALWAYS_EXCLUDE
        assert "activity_ids" not in audit_field_names  # ALWAYS_EXCLUDE
        assert "write_date" not in audit_field_names  # ALWAYS_EXCLUDE
        assert "write_uid" not in audit_field_names  # ALWAYS_EXCLUDE

    def test_audit_exclude_custom_fields(self):
        """Spec with audit_exclude: ['custom_field'] excludes custom_field from audit_fields."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
                {"name": "email", "type": "Char"},
                {"name": "internal_notes", "type": "Text"},
            ],
            audit=True,
            audit_exclude=["internal_notes"],
        )
        spec = _make_spec(
            models=[model],
            security_roles=_make_security_roles(),
        )
        result = _process_audit_patterns(spec)
        enriched = next(m for m in result["models"] if m["name"] == "university.student")

        audit_field_names = {f["name"] for f in enriched["audit_fields"]}
        assert "name" in audit_field_names
        assert "email" in audit_field_names
        assert "internal_notes" not in audit_field_names

    def test_no_audit_returns_unchanged(self):
        """Spec with no audit:true on any model returns spec unchanged, no has_audit_log key."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
            ],
        )
        spec = _make_spec(
            models=[model],
            security_roles=_make_security_roles(),
        )
        result = _process_audit_patterns(spec)

        # No has_audit_log on spec
        assert "has_audit_log" not in result
        # No audit.trail.log model
        model_names = {m["name"] for m in result["models"]}
        assert "audit.trail.log" not in model_names
        # Original model unchanged
        student = next(m for m in result["models"] if m["name"] == "university.student")
        assert "has_audit" not in student

    def test_auditor_role_injected_when_missing(self):
        """Spec with audit:true and no 'auditor' in security_roles injects auditor role."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
            ],
            audit=True,
        )
        spec = _make_spec(
            models=[model],
            security_roles=_make_security_roles(roles=["user", "manager"]),
        )
        result = _process_audit_patterns(spec)

        role_names = [r["name"] for r in result["security_roles"]]
        assert "auditor" in role_names
        # Auditor should imply base.group_user (sibling of lowest, not in hierarchy chain)
        auditor = next(r for r in result["security_roles"] if r["name"] == "auditor")
        assert auditor["implied_ids"] == "base.group_user"

    def test_auditor_role_not_duplicated_when_exists(self):
        """Spec with audit:true and 'auditor' already in security_roles does not duplicate."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
            ],
            audit=True,
        )
        roles_with_auditor = _make_security_roles(roles=["user", "auditor", "manager"])
        spec = _make_spec(
            models=[model],
            security_roles=roles_with_auditor,
        )
        result = _process_audit_patterns(spec)

        auditor_count = sum(1 for r in result["security_roles"] if r["name"] == "auditor")
        assert auditor_count == 1

    def test_audit_log_model_gets_read_only_acl(self):
        """audit.trail.log gets security_acl with read-only for auditor+highest role, no access for others."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
            ],
            audit=True,
        )
        spec = _make_spec(
            models=[model],
            security_roles=_make_security_roles(roles=["user", "manager"]),
        )
        result = _process_audit_patterns(spec)

        audit_model = next(m for m in result["models"] if m["name"] == "audit.trail.log")
        acl = audit_model.get("security_acl", [])
        assert len(acl) > 0, "security_acl not set on audit.trail.log"

        # Build lookup by role
        acl_by_role = {entry["role"]: entry for entry in acl}

        # Auditor should have read-only
        assert "auditor" in acl_by_role
        assert acl_by_role["auditor"]["perm_read"] == 1
        assert acl_by_role["auditor"]["perm_write"] == 0
        assert acl_by_role["auditor"]["perm_create"] == 0
        assert acl_by_role["auditor"]["perm_unlink"] == 0

        # Highest role (manager) should have read-only
        assert "manager" in acl_by_role
        assert acl_by_role["manager"]["perm_read"] == 1
        assert acl_by_role["manager"]["perm_write"] == 0
        assert acl_by_role["manager"]["perm_create"] == 0
        assert acl_by_role["manager"]["perm_unlink"] == 0

        # Other roles (user) should have NO access
        if "user" in acl_by_role:
            assert acl_by_role["user"]["perm_read"] == 0
            assert acl_by_role["user"]["perm_write"] == 0
            assert acl_by_role["user"]["perm_create"] == 0
            assert acl_by_role["user"]["perm_unlink"] == 0

    def test_synthesized_audit_log_metadata_flags(self):
        """Synthesized audit.trail.log has _synthesized=True, _is_audit_log=True, chatter=False."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
            ],
            audit=True,
        )
        spec = _make_spec(
            models=[model],
            security_roles=_make_security_roles(),
        )
        result = _process_audit_patterns(spec)

        audit_model = next(m for m in result["models"] if m["name"] == "audit.trail.log")
        assert audit_model["_synthesized"] is True
        assert audit_model["_is_audit_log"] is True
        assert audit_model["chatter"] is False
        assert audit_model["audit"] is False

    def test_has_audit_log_set_on_spec(self):
        """When any model has audit:true, spec gets has_audit_log=True."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
            ],
            audit=True,
        )
        spec = _make_spec(
            models=[model],
            security_roles=_make_security_roles(),
        )
        result = _process_audit_patterns(spec)
        assert result["has_audit_log"] is True

    def test_pure_function_does_not_mutate_input(self):
        """Preprocessor does not mutate original spec."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
            ],
            audit=True,
        )
        spec = _make_spec(
            models=[model],
            security_roles=_make_security_roles(),
        )
        # Deep snapshot of original models
        original_model_names = [m["name"] for m in spec["models"]]

        _process_audit_patterns(spec)

        # Original spec should be unchanged
        current_model_names = [m["name"] for m in spec["models"]]
        assert current_model_names == original_model_names
        assert "has_audit_log" not in spec

    def test_multiple_audited_models(self):
        """Multiple models with audit:true all get enriched and share one audit.trail.log."""
        model1 = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
                {"name": "email", "type": "Char"},
            ],
            audit=True,
        )
        model2 = _make_model(
            name="university.course",
            fields=[
                {"name": "title", "type": "Char", "required": True},
                {"name": "credits", "type": "Integer"},
            ],
            audit=True,
        )
        spec = _make_spec(
            models=[model1, model2],
            security_roles=_make_security_roles(),
        )
        result = _process_audit_patterns(spec)

        student = next(m for m in result["models"] if m["name"] == "university.student")
        course = next(m for m in result["models"] if m["name"] == "university.course")
        assert student["has_audit"] is True
        assert course["has_audit"] is True

        # Only one audit.trail.log model
        audit_models = [m for m in result["models"] if m["name"] == "audit.trail.log"]
        assert len(audit_models) == 1

    def test_non_audited_model_unchanged(self):
        """Non-audited models are passed through unchanged."""
        audited = _make_model(
            name="university.student",
            fields=[{"name": "name", "type": "Char", "required": True}],
            audit=True,
        )
        non_audited = _make_model(
            name="university.course",
            fields=[{"name": "title", "type": "Char", "required": True}],
        )
        spec = _make_spec(
            models=[audited, non_audited],
            security_roles=_make_security_roles(),
        )
        result = _process_audit_patterns(spec)

        course = next(m for m in result["models"] if m["name"] == "university.course")
        assert "has_audit" not in course
        assert "audit_fields" not in course

    def test_preserves_existing_override_sources(self):
        """Audit preprocessor preserves existing override_sources from prior preprocessors."""
        model = _make_model(
            name="university.student",
            fields=[
                {"name": "name", "type": "Char", "required": True},
            ],
            audit=True,
        )
        # Simulate prior preprocessor having set override_sources
        model["override_sources"] = defaultdict(set)
        model["override_sources"]["write"].add("constraints")
        model["override_sources"]["create"].add("bulk")

        spec = _make_spec(
            models=[model],
            security_roles=_make_security_roles(),
        )
        result = _process_audit_patterns(spec)

        enriched = next(m for m in result["models"] if m["name"] == "university.student")
        # Both "constraints" and "audit" should be in write sources
        assert "constraints" in enriched["override_sources"]["write"]
        assert "audit" in enriched["override_sources"]["write"]
        # Create sources should be preserved
        assert "bulk" in enriched["override_sources"]["create"]
