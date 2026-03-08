"""Tests for logic_writer.context_builder -- per-stub context assembly."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from odoo_gen_utils.logic_writer.context_builder import (
    StubContext,
    build_stub_context,
)
from odoo_gen_utils.logic_writer.stub_detector import StubInfo
from odoo_gen_utils.registry import ModelRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_stub(**overrides: Any) -> StubInfo:
    """Build a StubInfo with sensible defaults, overridden by *overrides*."""
    defaults: dict[str, Any] = {
        "file": "models/fee.py",
        "line": 10,
        "class_name": "UniFee",
        "model_name": "uni.fee",
        "method_name": "_compute_total",
        "decorator": '@api.depends("amount", "discount")',
        "target_fields": ["total"],
    }
    defaults.update(overrides)
    return StubInfo(**defaults)


def _make_spec(
    models: list[dict[str, Any]] | None = None,
    wizards: list[dict[str, Any]] | None = None,
    cron_jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a minimal spec dict."""
    spec: dict[str, Any] = {"module_name": "uni_fee"}
    if models is not None:
        spec["models"] = models
    else:
        spec["models"] = []
    if wizards is not None:
        spec["wizards"] = wizards
    if cron_jobs is not None:
        spec["cron_jobs"] = cron_jobs
    return spec


def _make_registry(tmp_path: Path) -> ModelRegistry:
    """Create and return a ModelRegistry loaded with known models."""
    reg = ModelRegistry(tmp_path / "registry.json")
    reg.load_known_models()
    return reg


def _make_model_dict(
    name: str = "uni.fee",
    description: str = "University Fee Management",
    fields: list[dict[str, Any]] | None = None,
    complex_constraints: list[dict[str, Any]] | None = None,
    workflow_states: list[dict[str, Any]] | None = None,
    approval_levels: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a minimal model dict matching the spec schema."""
    model: dict[str, Any] = {
        "name": name,
        "_name": name,
        "description": description,
    }
    if fields is not None:
        model["fields"] = fields
    else:
        model["fields"] = [
            {"name": "amount", "type": "Float", "string": "Amount"},
            {"name": "discount", "type": "Float", "string": "Discount"},
            {
                "name": "total",
                "type": "Float",
                "string": "Total",
                "compute": "_compute_total",
                "store": True,
                "depends": ["amount", "discount"],
                "help": "Total is calculated as amount minus discount",
            },
        ]
    if complex_constraints is not None:
        model["complex_constraints"] = complex_constraints
    if workflow_states is not None:
        model["workflow_states"] = workflow_states
    if approval_levels is not None:
        model["approval_levels"] = approval_levels
    return model


# ---------------------------------------------------------------------------
# StubContext frozen dataclass
# ---------------------------------------------------------------------------


class TestStubContextDataclass:
    """StubContext is a frozen dataclass with the correct fields."""

    def test_stub_context_fields(self) -> None:
        ctx = StubContext(
            model_fields={"amount": {"type": "Float"}},
            related_fields={"partner_id": {"name": {"type": "Char"}}},
            business_rules=["Total = amount - discount"],
            registry_source="registry",
        )
        assert ctx.model_fields == {"amount": {"type": "Float"}}
        assert ctx.related_fields == {"partner_id": {"name": {"type": "Char"}}}
        assert ctx.business_rules == ["Total = amount - discount"]
        assert ctx.registry_source == "registry"

    def test_stub_context_is_frozen(self) -> None:
        ctx = StubContext(
            model_fields={},
            related_fields={},
            business_rules=[],
            registry_source=None,
        )
        with pytest.raises(AttributeError):
            ctx.registry_source = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# model_fields extraction
# ---------------------------------------------------------------------------


class TestModelFields:
    """build_stub_context() returns model_fields with type info."""

    def test_model_fields_extracted(self) -> None:
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub()

        ctx = build_stub_context(stub, spec)
        assert "amount" in ctx.model_fields
        assert ctx.model_fields["amount"]["type"] == "Float"
        assert "total" in ctx.model_fields
        assert ctx.model_fields["total"]["compute"] == "_compute_total"

    def test_model_fields_various_types(self) -> None:
        model = _make_model_dict(
            fields=[
                {"name": "name", "type": "Char", "string": "Name"},
                {
                    "name": "partner_id",
                    "type": "Many2one",
                    "string": "Partner",
                    "comodel_name": "res.partner",
                },
                {"name": "active", "type": "Boolean", "string": "Active"},
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=[])

        ctx = build_stub_context(stub, spec)
        assert ctx.model_fields["name"]["type"] == "Char"
        assert ctx.model_fields["partner_id"]["type"] == "Many2one"
        assert ctx.model_fields["partner_id"]["comodel_name"] == "res.partner"
        assert ctx.model_fields["active"]["type"] == "Boolean"


# ---------------------------------------------------------------------------
# related_fields from ModelRegistry
# ---------------------------------------------------------------------------


class TestRelatedFields:
    """build_stub_context() populates related_fields from registry."""

    def test_related_fields_from_registry(self, tmp_path: Path) -> None:
        """When comodel is in the registry, related_fields is populated."""
        reg = ModelRegistry(tmp_path / "registry.json")
        # Register a custom model
        reg.register_module(
            "uni_student",
            {
                "models": [
                    {
                        "_name": "uni.student",
                        "fields": {
                            "name": {"type": "Char"},
                            "gpa": {"type": "Float"},
                        },
                    }
                ],
                "depends": [],
            },
        )

        model = _make_model_dict(
            fields=[
                {
                    "name": "student_id",
                    "type": "Many2one",
                    "string": "Student",
                    "comodel_name": "uni.student",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=[])

        ctx = build_stub_context(stub, spec, registry=reg)
        assert "uni.student" in ctx.related_fields
        assert ctx.related_fields["uni.student"]["name"]["type"] == "Char"
        assert ctx.registry_source == "registry"

    def test_related_fields_from_known_models(self, tmp_path: Path) -> None:
        """When comodel is a standard Odoo model, use known_models."""
        reg = _make_registry(tmp_path)

        model = _make_model_dict(
            fields=[
                {
                    "name": "partner_id",
                    "type": "Many2one",
                    "string": "Partner",
                    "comodel_name": "res.partner",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=[])

        ctx = build_stub_context(stub, spec, registry=reg)
        assert "res.partner" in ctx.related_fields
        assert "name" in ctx.related_fields["res.partner"]
        assert ctx.registry_source == "known_models"

    def test_related_fields_not_found(self, tmp_path: Path) -> None:
        """When comodel is not found anywhere, registry_source is None."""
        reg = ModelRegistry(tmp_path / "registry.json")
        # Empty registry, no known models loaded

        model = _make_model_dict(
            fields=[
                {
                    "name": "custom_id",
                    "type": "Many2one",
                    "string": "Custom",
                    "comodel_name": "unknown.model",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=[])

        ctx = build_stub_context(stub, spec, registry=reg)
        assert ctx.related_fields == {}
        assert ctx.registry_source is None


# ---------------------------------------------------------------------------
# business_rules aggregation
# ---------------------------------------------------------------------------


class TestBusinessRules:
    """build_stub_context() aggregates business_rules from multiple sources."""

    def test_rules_from_description(self) -> None:
        model = _make_model_dict(description="University Fee Management")
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=[])

        ctx = build_stub_context(stub, spec)
        assert any(
            "University Fee Management" in r for r in ctx.business_rules
        )

    def test_rules_from_field_help(self) -> None:
        model = _make_model_dict(
            fields=[
                {
                    "name": "total",
                    "type": "Float",
                    "string": "Total",
                    "help": "Total is calculated as amount minus discount",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=["total"])

        ctx = build_stub_context(stub, spec)
        assert any(
            "amount minus discount" in r for r in ctx.business_rules
        )

    def test_rules_from_complex_constraints(self) -> None:
        model = _make_model_dict(
            complex_constraints=[
                {
                    "name": "temporal_deadline",
                    "type": "temporal",
                    "message": "Fee must be paid before deadline",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=[])

        ctx = build_stub_context(stub, spec)
        assert any(
            "Fee must be paid before deadline" in r
            for r in ctx.business_rules
        )

    def test_rules_from_workflow_states(self) -> None:
        model = _make_model_dict(
            workflow_states=[
                {"name": "draft", "description": "Initial state"},
                {"name": "confirmed", "description": "Fee confirmed"},
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=[])

        ctx = build_stub_context(stub, spec)
        assert any("draft" in r for r in ctx.business_rules)
        assert any("confirmed" in r for r in ctx.business_rules)

    def test_rules_from_approval_levels(self) -> None:
        model = _make_model_dict(
            approval_levels=[
                {"name": "manager", "description": "Manager approval required"},
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=[])

        ctx = build_stub_context(stub, spec)
        assert any("manager" in r for r in ctx.business_rules)

    def test_rules_from_depends(self) -> None:
        model = _make_model_dict(
            fields=[
                {
                    "name": "total",
                    "type": "Float",
                    "string": "Total",
                    "depends": ["amount", "discount"],
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=["total"])

        ctx = build_stub_context(stub, spec)
        assert any("depends" in r.lower() for r in ctx.business_rules)


# ---------------------------------------------------------------------------
# Empty spec model
# ---------------------------------------------------------------------------


class TestEmptySpecModel:
    """build_stub_context() handles empty or missing models gracefully."""

    def test_empty_model_returns_empty_rules(self) -> None:
        model = _make_model_dict(
            description="", fields=[]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=[])

        ctx = build_stub_context(stub, spec)
        assert ctx.business_rules == []
        assert ctx.related_fields == {}

    def test_model_not_in_spec(self) -> None:
        """When stub model is not in spec, return empty context."""
        spec = _make_spec(models=[])
        stub = _make_stub(model_name="nonexistent.model")

        ctx = build_stub_context(stub, spec)
        assert ctx.model_fields == {}
        assert ctx.business_rules == []


# ---------------------------------------------------------------------------
# Wizard stubs
# ---------------------------------------------------------------------------


class TestWizardStubs:
    """build_stub_context() handles wizard stubs from spec['wizards']."""

    def test_wizard_stub_context(self) -> None:
        spec = _make_spec(
            models=[],
            wizards=[
                {
                    "name": "uni.fee.wizard",
                    "_name": "uni.fee.wizard",
                    "description": "Bulk fee payment wizard",
                    "fields": [
                        {
                            "name": "amount",
                            "type": "Float",
                            "string": "Amount",
                        },
                    ],
                }
            ],
        )
        stub = _make_stub(
            model_name="uni.fee.wizard",
            method_name="action_apply",
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert "amount" in ctx.model_fields
        assert any("Bulk fee" in r for r in ctx.business_rules)


# ---------------------------------------------------------------------------
# Registry is None (graceful degradation)
# ---------------------------------------------------------------------------


class TestRegistryNone:
    """build_stub_context() works when registry is None."""

    def test_no_registry_empty_related_fields(self) -> None:
        model = _make_model_dict(
            fields=[
                {
                    "name": "partner_id",
                    "type": "Many2one",
                    "string": "Partner",
                    "comodel_name": "res.partner",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(target_fields=[])

        ctx = build_stub_context(stub, spec, registry=None)
        assert ctx.related_fields == {}
        assert ctx.registry_source is None


# ---------------------------------------------------------------------------
# New fields backward compatibility
# ---------------------------------------------------------------------------


class TestNewFieldsDefaults:
    """New StubContext fields have backward-compatible defaults."""

    def test_new_fields_have_defaults(self) -> None:
        """StubContext can be constructed with only the original 4 fields."""
        ctx = StubContext(
            model_fields={},
            related_fields={},
            business_rules=[],
            registry_source=None,
        )
        assert ctx.method_type == ""
        assert ctx.computation_hint == ""
        assert ctx.constraint_type == ""
        assert ctx.target_field_types == {}
        assert ctx.error_messages == ()

    def test_new_fields_settable(self) -> None:
        """New fields can be set during construction."""
        ctx = StubContext(
            model_fields={},
            related_fields={},
            business_rules=[],
            registry_source=None,
            method_type="compute",
            computation_hint="sum_related",
            constraint_type="",
            target_field_types={"total": {"type": "Float"}},
            error_messages=(),
        )
        assert ctx.method_type == "compute"
        assert ctx.computation_hint == "sum_related"
        assert ctx.target_field_types == {"total": {"type": "Float"}}


# ---------------------------------------------------------------------------
# method_type classification
# ---------------------------------------------------------------------------


class TestMethodType:
    """build_stub_context() classifies method_type from method name patterns."""

    def test_compute_method_type(self) -> None:
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(method_name="_compute_total")

        ctx = build_stub_context(stub, spec)
        assert ctx.method_type == "compute"

    def test_constraint_method_type(self) -> None:
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_amount",
            decorator='@api.constrains("amount")',
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.method_type == "constraint"

    def test_onchange_method_type(self) -> None:
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_onchange_partner",
            decorator='@api.onchange("partner_id")',
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.method_type == "onchange"

    def test_action_method_type(self) -> None:
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="action_confirm",
            decorator="",
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.method_type == "action"

    def test_cron_method_type(self) -> None:
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_cron_cleanup",
            decorator="@api.model",
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.method_type == "cron"

    def test_override_method_type(self) -> None:
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="create",
            decorator="@api.model_create_multi",
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.method_type == "override"

    def test_write_override_method_type(self) -> None:
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="write",
            decorator="",
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.method_type == "override"

    def test_other_method_type(self) -> None:
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_get_report_data",
            decorator="",
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.method_type == "other"


# ---------------------------------------------------------------------------
# computation_hint classification
# ---------------------------------------------------------------------------


class TestComputationHint:
    """build_stub_context() classifies computation_hint for compute methods."""

    def test_sum_related_hint(self) -> None:
        """Dot-path to numeric field on x2many -> sum_related."""
        model = _make_model_dict(
            fields=[
                {
                    "name": "line_ids",
                    "type": "One2many",
                    "string": "Lines",
                    "comodel_name": "uni.fee.line",
                },
                {
                    "name": "total_amount",
                    "type": "Float",
                    "string": "Total Amount",
                    "compute": "_compute_total_amount",
                    "store": True,
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_compute_total_amount",
            decorator='@api.depends("line_ids.amount")',
            target_fields=["total_amount"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.computation_hint == "sum_related"

    def test_count_related_hint(self) -> None:
        """Integer target + x2many depends -> count_related."""
        model = _make_model_dict(
            fields=[
                {
                    "name": "line_ids",
                    "type": "One2many",
                    "string": "Lines",
                    "comodel_name": "uni.fee.line",
                },
                {
                    "name": "line_count",
                    "type": "Integer",
                    "string": "Line Count",
                    "compute": "_compute_line_count",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_compute_line_count",
            decorator='@api.depends("line_ids")',
            target_fields=["line_count"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.computation_hint == "count_related"

    def test_conditional_set_hint(self) -> None:
        """Boolean/Selection target -> conditional_set."""
        model = _make_model_dict(
            fields=[
                {"name": "amount", "type": "Float", "string": "Amount"},
                {
                    "name": "is_paid",
                    "type": "Boolean",
                    "string": "Is Paid",
                    "compute": "_compute_is_paid",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_compute_is_paid",
            decorator='@api.depends("amount")',
            target_fields=["is_paid"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.computation_hint == "conditional_set"

    def test_cross_model_calc_hint(self) -> None:
        """2+ dot-path segments in depends -> cross_model_calc."""
        model = _make_model_dict(
            fields=[
                {
                    "name": "partner_id",
                    "type": "Many2one",
                    "string": "Partner",
                    "comodel_name": "res.partner",
                },
                {
                    "name": "credit_limit",
                    "type": "Float",
                    "string": "Credit Limit",
                    "compute": "_compute_credit_limit",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_compute_credit_limit",
            decorator='@api.depends("partner_id.parent_id.credit_limit")',
            target_fields=["credit_limit"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.computation_hint == "cross_model_calc"

    def test_aggregate_hint(self) -> None:
        """Business rules mention average/weighted -> aggregate."""
        model = _make_model_dict(
            description="Weighted average calculation",
            fields=[
                {"name": "amount", "type": "Float", "string": "Amount"},
                {
                    "name": "weighted_avg",
                    "type": "Float",
                    "string": "Weighted Average",
                    "compute": "_compute_weighted_avg",
                    "help": "weighted average of line amounts",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_compute_weighted_avg",
            decorator='@api.depends("amount")',
            target_fields=["weighted_avg"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.computation_hint == "aggregate"

    def test_lookup_hint(self) -> None:
        """Single dot-path, non-numeric target -> lookup."""
        model = _make_model_dict(
            fields=[
                {
                    "name": "partner_id",
                    "type": "Many2one",
                    "string": "Partner",
                    "comodel_name": "res.partner",
                },
                {
                    "name": "partner_name",
                    "type": "Char",
                    "string": "Partner Name",
                    "compute": "_compute_partner_name",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_compute_partner_name",
            decorator='@api.depends("partner_id.name")',
            target_fields=["partner_name"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.computation_hint == "lookup"

    def test_custom_hint_fallback(self) -> None:
        """No matching pattern -> custom."""
        model = _make_model_dict(
            fields=[
                {"name": "name", "type": "Char", "string": "Name"},
                {
                    "name": "display_name",
                    "type": "Char",
                    "string": "Display Name",
                    "compute": "_compute_display_name",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_compute_display_name",
            decorator='@api.depends("name")',
            target_fields=["display_name"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.computation_hint == "custom"

    def test_non_compute_gets_empty_hint(self) -> None:
        """Non-compute methods get empty computation_hint."""
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_amount",
            decorator='@api.constrains("amount")',
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.computation_hint == ""


# ---------------------------------------------------------------------------
# constraint_type classification
# ---------------------------------------------------------------------------


class TestConstraintType:
    """build_stub_context() classifies constraint_type for constraint methods."""

    def test_range_constraint(self) -> None:
        model = _make_model_dict(
            fields=[
                {
                    "name": "amount",
                    "type": "Float",
                    "string": "Amount",
                    "help": "Amount must be between 0 and 10000",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_amount",
            decorator='@api.constrains("amount")',
            target_fields=["amount"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.constraint_type == "range"

    def test_required_if_constraint(self) -> None:
        model = _make_model_dict(
            fields=[
                {
                    "name": "phone",
                    "type": "Char",
                    "string": "Phone",
                    "help": "Phone is required when contact type is individual",
                },
            ],
            complex_constraints=[
                {"message": "Phone is required when contact type is individual"},
            ],
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_phone",
            decorator='@api.constrains("phone", "contact_type")',
            target_fields=["phone"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.constraint_type == "required_if"

    def test_cross_field_constraint(self) -> None:
        model = _make_model_dict(
            fields=[
                {"name": "start_date", "type": "Date", "string": "Start Date"},
                {"name": "end_date", "type": "Date", "string": "End Date"},
            ],
            complex_constraints=[
                {"message": "End date must be after start date"},
            ],
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_dates",
            decorator='@api.constrains("start_date", "end_date")',
            target_fields=["start_date", "end_date"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.constraint_type == "cross_field"

    def test_format_constraint(self) -> None:
        model = _make_model_dict(
            fields=[
                {
                    "name": "cnic",
                    "type": "Char",
                    "string": "CNIC",
                    "help": "CNIC format must be XXXXX-XXXXXXX-X",
                },
            ],
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_cnic",
            decorator='@api.constrains("cnic")',
            target_fields=["cnic"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.constraint_type == "format"

    def test_unique_constraint(self) -> None:
        model = _make_model_dict(
            complex_constraints=[
                {"message": "Student must be unique per semester"},
            ],
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_unique_enrollment",
            decorator='@api.constrains("student_id", "semester_id")',
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.constraint_type == "unique"

    def test_referential_constraint(self) -> None:
        model = _make_model_dict(
            complex_constraints=[
                {"message": "Course must exist in the department's model catalog"},
            ],
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_course_exists",
            decorator='@api.constrains("course_id")',
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.constraint_type == "referential"

    def test_custom_constraint_fallback(self) -> None:
        model = _make_model_dict(
            complex_constraints=[
                {"message": "Data is valid"},
            ],
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_data",
            decorator='@api.constrains("data")',
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.constraint_type == "custom"

    def test_non_constraint_gets_empty_type(self) -> None:
        """Non-constraint methods get empty constraint_type."""
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(method_name="_compute_total")

        ctx = build_stub_context(stub, spec)
        assert ctx.constraint_type == ""


# ---------------------------------------------------------------------------
# target_field_types
# ---------------------------------------------------------------------------


class TestTargetFieldTypes:
    """build_stub_context() populates target_field_types for compute stubs."""

    def test_basic_type_extraction(self) -> None:
        model = _make_model_dict(
            fields=[
                {
                    "name": "total",
                    "type": "Float",
                    "string": "Total",
                    "store": True,
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_compute_total",
            target_fields=["total"],
        )

        ctx = build_stub_context(stub, spec)
        assert "total" in ctx.target_field_types
        assert ctx.target_field_types["total"]["type"] == "Float"
        assert ctx.target_field_types["total"]["store"] is True

    def test_monetary_type_with_currency(self) -> None:
        model = _make_model_dict(
            fields=[
                {
                    "name": "currency_id",
                    "type": "Many2one",
                    "comodel_name": "res.currency",
                },
                {
                    "name": "total_amount",
                    "type": "Monetary",
                    "string": "Total Amount",
                    "currency_field": "currency_id",
                    "store": True,
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_compute_total_amount",
            target_fields=["total_amount"],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.target_field_types["total_amount"]["type"] == "Monetary"
        assert ctx.target_field_types["total_amount"]["currency_field"] == "currency_id"

    def test_no_none_values(self) -> None:
        """Only keys with actual values are included (no None entries)."""
        model = _make_model_dict(
            fields=[
                {
                    "name": "total",
                    "type": "Float",
                    "string": "Total",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_compute_total",
            target_fields=["total"],
        )

        ctx = build_stub_context(stub, spec)
        # "store" and "currency_field" should not be present if not in spec
        for _key, val in ctx.target_field_types.get("total", {}).items():
            assert val is not None

    def test_non_compute_gets_empty_types(self) -> None:
        """Non-compute methods get empty target_field_types."""
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="action_confirm",
            decorator="",
            target_fields=[],
        )

        ctx = build_stub_context(stub, spec)
        assert ctx.target_field_types == {}


# ---------------------------------------------------------------------------
# error_messages for constraints
# ---------------------------------------------------------------------------


class TestErrorMessages:
    """build_stub_context() generates error_messages for constraint methods."""

    def test_range_constraint_messages(self) -> None:
        model = _make_model_dict(
            fields=[
                {
                    "name": "amount",
                    "type": "Float",
                    "string": "Amount",
                    "help": "Amount must be between 0 and 10000",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_amount",
            decorator='@api.constrains("amount")',
            target_fields=["amount"],
        )

        ctx = build_stub_context(stub, spec)
        assert len(ctx.error_messages) > 0
        msg = ctx.error_messages[0]
        assert "message" in msg
        assert msg["translatable"] is True

    def test_error_messages_use_field_labels(self) -> None:
        model = _make_model_dict(
            fields=[
                {
                    "name": "amount",
                    "type": "Float",
                    "string": "Amount",
                    "help": "Amount must be between 0 and 10000",
                },
            ]
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_amount",
            decorator='@api.constrains("amount")',
            target_fields=["amount"],
        )

        ctx = build_stub_context(stub, spec)
        assert len(ctx.error_messages) > 0
        msg_text = ctx.error_messages[0]["message"]
        # Should use named interpolation
        assert "%(" in msg_text

    def test_non_constraint_gets_empty_messages(self) -> None:
        """Non-constraint methods get empty error_messages."""
        model = _make_model_dict()
        spec = _make_spec(models=[model])
        stub = _make_stub(method_name="_compute_total")

        ctx = build_stub_context(stub, spec)
        assert ctx.error_messages == ()

    def test_error_message_structure(self) -> None:
        """Each error message has condition, message, translatable keys."""
        model = _make_model_dict(
            complex_constraints=[
                {"message": "End date must be after start date"},
            ],
            fields=[
                {"name": "start_date", "type": "Date", "string": "Start Date"},
                {"name": "end_date", "type": "Date", "string": "End Date"},
            ],
        )
        spec = _make_spec(models=[model])
        stub = _make_stub(
            method_name="_check_dates",
            decorator='@api.constrains("start_date", "end_date")',
            target_fields=["start_date", "end_date"],
        )

        ctx = build_stub_context(stub, spec)
        assert len(ctx.error_messages) > 0
        for msg in ctx.error_messages:
            assert "condition" in msg
            assert "message" in msg
            assert "translatable" in msg
            assert msg["translatable"] is True
