"""Tests for Pydantic v2 spec schema validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from odoo_gen_utils.spec_schema import (
    ApprovalLevelSpec,
    ApprovalSpec,
    ConstraintSpec,
    CronJobSpec,
    FieldSpec,
    ModelSpec,
    ModuleSpec,
    ReportSpec,
    SecurityACLSpec,
    SecurityBlockSpec,
    VALID_FIELD_TYPES,
    WebhookSpec,
    format_validation_errors,
    validate_spec,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# TestValidateSpec
# ---------------------------------------------------------------------------
class TestValidateSpec:
    """Test validate_spec() entry point."""

    def test_valid_spec_v1(self):
        """Valid spec_v1.json returns ModuleSpec instance."""
        raw = _load_fixture("spec_v1.json")
        result = validate_spec(raw)
        assert isinstance(result, ModuleSpec)
        assert result.module_name == "uni_fee"

    def test_valid_spec_v2(self):
        """Valid spec_v2.json returns ModuleSpec instance."""
        raw = _load_fixture("spec_v2.json")
        result = validate_spec(raw)
        assert isinstance(result, ModuleSpec)
        assert result.module_name == "uni_fee"

    def test_missing_module_name(self):
        """Missing required field 'module_name' raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_spec({"models": []})
        errors = exc_info.value.errors()
        locs = [tuple(e["loc"]) for e in errors]
        assert ("module_name",) in locs

    def test_optional_defaults(self):
        """Optional fields get correct defaults."""
        result = validate_spec({"module_name": "test_mod"})
        assert result.odoo_version == "17.0"
        assert result.license == "LGPL-3"
        assert result.depends == ["base"]
        assert result.application is True
        assert result.category == "Uncategorized"
        assert result.models == []
        assert result.cron_jobs == []
        assert result.reports == []


# ---------------------------------------------------------------------------
# TestFieldTypeValidation
# ---------------------------------------------------------------------------
class TestFieldTypeValidation:
    """Test @field_validator for field types."""

    def test_valid_types_accepted(self):
        """All 16 valid Odoo field types are accepted."""
        for ftype in sorted(VALID_FIELD_TYPES):
            field = FieldSpec(name="test_field", type=ftype)
            assert field.type == ftype

    def test_invalid_type_rejected(self):
        """Invalid field type 'Strig' raises ValidationError with valid types."""
        with pytest.raises(ValidationError) as exc_info:
            FieldSpec(name="bad_field", type="Strig")
        error_msg = str(exc_info.value)
        assert "Strig" in error_msg
        # Should mention at least some valid types
        assert "Char" in error_msg or "valid" in error_msg.lower()

    def test_valid_types_count(self):
        """There are exactly 16 valid field types."""
        assert len(VALID_FIELD_TYPES) == 16


# ---------------------------------------------------------------------------
# TestExtraAllow
# ---------------------------------------------------------------------------
class TestExtraAllow:
    """Test extra='allow' preserves unknown keys."""

    def test_unknown_keys_preserved(self):
        """Unknown extra keys are preserved through validate -> model_dump."""
        raw = {
            "module_name": "test_mod",
            "custom_key": "custom_value",
            "another_extra": 42,
        }
        result = validate_spec(raw)
        dumped = result.model_dump()
        assert dumped["custom_key"] == "custom_value"
        assert dumped["another_extra"] == 42

    def test_roundtrip_fidelity(self):
        """model_dump() output matches original spec dict for known keys."""
        raw = _load_fixture("spec_v1.json")
        result = validate_spec(raw)
        dumped = result.model_dump()
        assert dumped["module_name"] == raw["module_name"]
        assert dumped["odoo_version"] == raw["odoo_version"]
        assert dumped["version"] == raw["version"]
        assert dumped["depends"] == raw["depends"]
        assert len(dumped["models"]) == len(raw["models"])
        assert len(dumped["cron_jobs"]) == len(raw["cron_jobs"])
        assert len(dumped["reports"]) == len(raw["reports"])


# ---------------------------------------------------------------------------
# TestCrossRefValidators
# ---------------------------------------------------------------------------
class TestCrossRefValidators:
    """Test cross-reference model validators on ModuleSpec."""

    def test_approval_role_not_in_security_roles(self):
        """Approval role not in security.roles raises ValidationError."""
        raw = {
            "module_name": "test_mod",
            "models": [
                {
                    "name": "test.model",
                    "fields": [{"name": "name", "type": "Char"}],
                    "security": {
                        "roles": ["viewer", "editor"],
                        "acl": {},
                    },
                    "approval": {
                        "levels": [
                            {"name": "submitted", "role": "nonexistent_role"},
                        ],
                    },
                },
            ],
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_spec(raw)
        error_msg = str(exc_info.value)
        assert "nonexistent_role" in error_msg

    def test_audit_exclude_field_not_in_model(self):
        """audit_exclude field not in model fields raises ValidationError."""
        raw = {
            "module_name": "test_mod",
            "models": [
                {
                    "name": "test.model",
                    "fields": [
                        {"name": "name", "type": "Char"},
                        {"name": "value", "type": "Float"},
                    ],
                    "audit": True,
                    "audit_exclude": ["nonexistent_field"],
                },
            ],
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_spec(raw)
        error_msg = str(exc_info.value)
        assert "nonexistent_field" in error_msg


# ---------------------------------------------------------------------------
# TestFormatErrors
# ---------------------------------------------------------------------------
class TestFormatErrors:
    """Test format_validation_errors() output."""

    def test_format_single_error(self):
        """format_validation_errors() with single error is human-readable."""
        try:
            validate_spec({"module_name": "bad_mod", "models": [
                {"name": "m", "fields": [{"name": "f", "type": "Strig"}]}
            ]})
            pytest.fail("Should have raised ValidationError")
        except ValidationError as e:
            output = format_validation_errors(e, "bad_mod")
            assert "Spec validation failed for bad_mod:" in output
            assert "Strig" in output

    def test_format_multiple_errors(self):
        """format_validation_errors() with multiple errors lists all paths."""
        try:
            ModuleSpec(
                module_name="bad_mod",
                models=[
                    {
                        "name": "m1",
                        "fields": [
                            {"name": "f1", "type": "Strig"},
                            {"name": "f2", "type": "Integre"},
                        ],
                    }
                ],
            )
            pytest.fail("Should have raised ValidationError")
        except ValidationError as e:
            output = format_validation_errors(e, "bad_mod")
            assert "Spec validation failed for bad_mod:" in output
            assert "Strig" in output
            assert "Integre" in output


# ---------------------------------------------------------------------------
# TestFixtureCompat
# ---------------------------------------------------------------------------
class TestFixtureCompat:
    """Test that real fixture files validate without modification."""

    def test_spec_v1_validates(self):
        """spec_v1.json validates via validate_spec()."""
        raw = _load_fixture("spec_v1.json")
        result = validate_spec(raw)
        assert result.module_name == "uni_fee"
        assert len(result.models) == 2
        assert result.models[0].name == "fee.invoice"
        assert len(result.models[0].fields) == 8

    def test_spec_v2_validates(self):
        """spec_v2.json validates via validate_spec()."""
        raw = _load_fixture("spec_v2.json")
        result = validate_spec(raw)
        assert result.module_name == "uni_fee"
        assert len(result.models) == 3
        assert result.models[2].name == "fee.penalty"


# ---------------------------------------------------------------------------
# TestSubModels
# ---------------------------------------------------------------------------
class TestSubModels:
    """Test individual sub-model specs."""

    def test_security_acl(self):
        """SecurityACLSpec correctly parses boolean CRUD permissions."""
        acl = SecurityACLSpec(create=False, read=True, write=False, unlink=False)
        assert acl.create is False
        assert acl.read is True
        assert acl.write is False
        assert acl.unlink is False

    def test_security_acl_defaults(self):
        """SecurityACLSpec defaults all permissions to True."""
        acl = SecurityACLSpec()
        assert acl.create is True
        assert acl.read is True
        assert acl.write is True
        assert acl.unlink is True

    def test_approval_spec(self):
        """ApprovalSpec with levels validates correctly."""
        approval = ApprovalSpec(
            levels=[
                ApprovalLevelSpec(name="submitted", role="editor"),
                ApprovalLevelSpec(name="approved", role="manager"),
            ],
            on_reject="draft",
        )
        assert len(approval.levels) == 2
        assert approval.levels[0].name == "submitted"
        assert approval.levels[0].role == "editor"
        assert approval.on_reject == "draft"

    def test_cron_job_defaults(self):
        """CronJobSpec with defaults validates correctly."""
        cron = CronJobSpec(name="test_cron", method="_cron_test")
        assert cron.interval_number == 1
        assert cron.interval_type == "days"
        assert cron.model == ""

    def test_report_spec(self):
        """ReportSpec validates correctly, xml_id defaults to empty string."""
        report = ReportSpec(name="test_report")
        assert report.xml_id == ""
        assert report.report_type == "qweb-pdf"
        assert report.model == ""
        assert report.template == ""

    def test_constraint_spec(self):
        """ConstraintSpec validates with defaults."""
        constraint = ConstraintSpec(name="check_positive", type="check")
        assert constraint.expression == ""
        assert constraint.message == ""

    def test_webhook_spec(self):
        """WebhookSpec validates with defaults."""
        webhook = WebhookSpec()
        assert webhook.watched_fields == []
        assert webhook.on_create is False
        assert webhook.on_write == []
        assert webhook.on_unlink is False
