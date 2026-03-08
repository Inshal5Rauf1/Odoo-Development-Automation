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
