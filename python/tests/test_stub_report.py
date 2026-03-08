"""Tests for logic_writer.report -- JSON stub report generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from odoo_gen_utils.logic_writer.report import StubReport, generate_stub_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_py(tmp_path: Path, rel: str, source: str) -> Path:
    """Write *source* to *tmp_path / rel* and return the file path."""
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(source, encoding="utf-8")
    return p


def _minimal_spec(module_name: str = "test_module") -> dict[str, Any]:
    """Build a minimal spec dict matching a simple model."""
    return {
        "module_name": module_name,
        "models": [
            {
                "name": "test.order",
                "fields": [
                    {
                        "name": "amount",
                        "type": "Float",
                        "string": "Amount",
                    },
                    {
                        "name": "total",
                        "type": "Float",
                        "string": "Total",
                        "compute": "_compute_total",
                        "depends": ["amount"],
                    },
                    {
                        "name": "partner_id",
                        "type": "Many2one",
                        "comodel_name": "res.partner",
                        "string": "Partner",
                    },
                ],
            },
        ],
    }


_SIMPLE_COMPUTE_PY = '''\
from odoo import models, fields, api


class TestOrder(models.Model):
    _name = "test.order"
    _description = "Test Order"

    amount = fields.Float(string="Amount")
    total = fields.Float(string="Total", compute="_compute_total")

    @api.depends("amount")
    def _compute_total(self):
        for rec in self:
            rec.total = 0.0
'''

_QUALITY_STUBS_PY = '''\
from odoo import models, fields, api


class TestOrder(models.Model):
    _name = "test.order"
    _description = "Test Order"

    amount = fields.Float(string="Amount")
    total = fields.Float(string="Total", compute="_compute_total")
    tax = fields.Float(string="Tax", compute="_compute_total")
    partner_id = fields.Many2one("res.partner", string="Partner")
    state = fields.Selection(selection=[("draft", "Draft"), ("confirmed", "Confirmed")])

    @api.depends("partner_id.discount")
    def _compute_total(self):
        for rec in self:
            rec.total = 0.0
            rec.tax = 0.0

    def action_confirm(self):
        pass

    def create(self, vals_list):
        pass
'''


_EMPTY_MODULE_PY = '''\
from odoo import models


class EmptyModel(models.Model):
    _name = "empty.model"
    _description = "Empty Model"

    def real_method(self):
        return True
'''


# ---------------------------------------------------------------------------
# Test: Report file creation
# ---------------------------------------------------------------------------


class TestReportFileCreation:
    """generate_stub_report() produces .odoo-gen-stubs.json in module dir."""

    def test_report_file_created(self, tmp_path: Path) -> None:
        mod = tmp_path / "test_module"
        mod.mkdir()
        _write_py(mod, "models/test.py", _SIMPLE_COMPUTE_PY)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = _minimal_spec()
        result = generate_stub_report(mod, spec)

        report_file = mod / ".odoo-gen-stubs.json"
        assert report_file.exists(), "Report file should be created"

    def test_report_is_valid_json(self, tmp_path: Path) -> None:
        mod = tmp_path / "test_module"
        mod.mkdir()
        _write_py(mod, "models/test.py", _SIMPLE_COMPUTE_PY)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = _minimal_spec()
        generate_stub_report(mod, spec)

        report_file = mod / ".odoo-gen-stubs.json"
        data = json.loads(report_file.read_text(encoding="utf-8"))
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Test: JSON schema compliance
# ---------------------------------------------------------------------------


class TestSchemaCompliance:
    """Generated JSON matches the locked schema from CONTEXT.md."""

    def test_meta_fields_present(self, tmp_path: Path) -> None:
        mod = tmp_path / "test_module"
        mod.mkdir()
        _write_py(mod, "models/test.py", _SIMPLE_COMPUTE_PY)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = _minimal_spec()
        generate_stub_report(mod, spec)

        data = json.loads(
            (mod / ".odoo-gen-stubs.json").read_text(encoding="utf-8")
        )
        meta = data["_meta"]
        assert meta["generator"] == "odoo-gen-utils"
        assert "generated_at" in meta
        assert meta["module"] == "test_module"
        assert isinstance(meta["total_stubs"], int)
        assert isinstance(meta["budget_count"], int)
        assert isinstance(meta["quality_count"], int)

    def test_stubs_array_present(self, tmp_path: Path) -> None:
        mod = tmp_path / "test_module"
        mod.mkdir()
        _write_py(mod, "models/test.py", _SIMPLE_COMPUTE_PY)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = _minimal_spec()
        generate_stub_report(mod, spec)

        data = json.loads(
            (mod / ".odoo-gen-stubs.json").read_text(encoding="utf-8")
        )
        assert "stubs" in data
        assert isinstance(data["stubs"], list)
        assert len(data["stubs"]) == 1  # one stub in simple compute

    def test_stub_entry_has_all_required_fields(self, tmp_path: Path) -> None:
        mod = tmp_path / "test_module"
        mod.mkdir()
        _write_py(mod, "models/test.py", _SIMPLE_COMPUTE_PY)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = _minimal_spec()
        generate_stub_report(mod, spec)

        data = json.loads(
            (mod / ".odoo-gen-stubs.json").read_text(encoding="utf-8")
        )
        stub = data["stubs"][0]
        required_keys = {
            "id", "file", "line", "class", "model", "method",
            "decorator", "target_fields", "complexity", "context",
        }
        assert required_keys.issubset(stub.keys()), (
            f"Missing keys: {required_keys - stub.keys()}"
        )

    def test_context_has_all_subfields(self, tmp_path: Path) -> None:
        mod = tmp_path / "test_module"
        mod.mkdir()
        _write_py(mod, "models/test.py", _SIMPLE_COMPUTE_PY)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = _minimal_spec()
        generate_stub_report(mod, spec)

        data = json.loads(
            (mod / ".odoo-gen-stubs.json").read_text(encoding="utf-8")
        )
        ctx = data["stubs"][0]["context"]
        assert "model_fields" in ctx
        assert "related_fields" in ctx
        assert "business_rules" in ctx
        assert "registry_source" in ctx


# ---------------------------------------------------------------------------
# Test: Stub ID format
# ---------------------------------------------------------------------------


class TestStubIdFormat:
    """Stub id format is "{model_name}__{method_name}" with double underscore."""

    def test_id_uses_double_underscore(self, tmp_path: Path) -> None:
        mod = tmp_path / "test_module"
        mod.mkdir()
        _write_py(mod, "models/test.py", _SIMPLE_COMPUTE_PY)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = _minimal_spec()
        generate_stub_report(mod, spec)

        data = json.loads(
            (mod / ".odoo-gen-stubs.json").read_text(encoding="utf-8")
        )
        stub = data["stubs"][0]
        assert stub["id"] == "test.order___compute_total"
        assert "__" in stub["id"]


# ---------------------------------------------------------------------------
# Test: StubReport dataclass return
# ---------------------------------------------------------------------------


class TestStubReportReturn:
    """generate_stub_report() returns a StubReport dataclass."""

    def test_returns_stub_report(self, tmp_path: Path) -> None:
        mod = tmp_path / "test_module"
        mod.mkdir()
        _write_py(mod, "models/test.py", _SIMPLE_COMPUTE_PY)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = _minimal_spec()
        result = generate_stub_report(mod, spec)

        assert isinstance(result, StubReport)
        assert result.total_stubs == 1
        assert result.budget_count == 1
        assert result.quality_count == 0
        assert result.report_path == mod / ".odoo-gen-stubs.json"

    def test_quality_stubs_counted(self, tmp_path: Path) -> None:
        mod = tmp_path / "test_module"
        mod.mkdir()
        _write_py(mod, "models/test.py", _QUALITY_STUBS_PY)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = _minimal_spec()
        result = generate_stub_report(mod, spec)

        assert result.total_stubs == 3  # _compute_total, action_confirm, create
        assert result.quality_count == 3  # all quality triggers
        assert result.budget_count == 0


# ---------------------------------------------------------------------------
# Test: Empty module (no stubs)
# ---------------------------------------------------------------------------


class TestEmptyModule:
    """Module with 0 stubs writes JSON with empty stubs array."""

    def test_zero_stubs_produces_empty_array(self, tmp_path: Path) -> None:
        mod = tmp_path / "test_module"
        mod.mkdir()
        _write_py(mod, "models/test.py", _EMPTY_MODULE_PY)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = _minimal_spec()
        result = generate_stub_report(mod, spec)

        assert result.total_stubs == 0
        assert result.budget_count == 0
        assert result.quality_count == 0

        data = json.loads(
            (mod / ".odoo-gen-stubs.json").read_text(encoding="utf-8")
        )
        assert data["stubs"] == []
        assert data["_meta"]["total_stubs"] == 0


# ---------------------------------------------------------------------------
# Integration test: end-to-end realistic stubs
# ---------------------------------------------------------------------------


class TestEndToEndIntegration:
    """Full pipeline from .py files -> JSON report with realistic stubs."""

    def test_mixed_complexity_stubs(self, tmp_path: Path) -> None:
        """Module with both budget and quality stubs."""
        mod = tmp_path / "test_module"
        mod.mkdir()

        mixed_py = '''\
from odoo import models, fields, api


class SaleOrder(models.Model):
    _name = "sale.order"
    _description = "Sale Order"

    amount = fields.Float(string="Amount")
    total = fields.Float(string="Total", compute="_compute_total")
    partner_id = fields.Many2one("res.partner", string="Partner")
    state = fields.Selection([("draft", "Draft"), ("confirmed", "Confirmed")])

    @api.depends("amount")
    def _compute_total(self):
        for rec in self:
            rec.total = 0.0

    @api.depends("partner_id.credit_limit")
    def _compute_credit_check(self):
        for rec in self:
            rec.total = 0.0

    def action_confirm(self):
        pass
'''
        _write_py(mod, "models/sale.py", mixed_py)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = {
            "module_name": "test_module",
            "models": [
                {
                    "name": "sale.order",
                    "fields": [
                        {"name": "amount", "type": "Float"},
                        {
                            "name": "total",
                            "type": "Float",
                            "compute": "_compute_total",
                            "depends": ["amount"],
                        },
                        {
                            "name": "partner_id",
                            "type": "Many2one",
                            "comodel_name": "res.partner",
                        },
                    ],
                },
            ],
        }

        result = generate_stub_report(mod, spec)

        assert result.total_stubs == 3
        # _compute_total: budget (simple depends, 1 target field)
        # _compute_credit_check: quality (cross-model depends)
        # action_confirm: quality (action_ prefix)
        assert result.budget_count == 1
        assert result.quality_count == 2

        data = json.loads(
            (mod / ".odoo-gen-stubs.json").read_text(encoding="utf-8")
        )
        stubs_by_method = {s["method"]: s for s in data["stubs"]}

        assert stubs_by_method["_compute_total"]["complexity"] == "budget"
        assert stubs_by_method["_compute_credit_check"]["complexity"] == "quality"
        assert stubs_by_method["action_confirm"]["complexity"] == "quality"

        # Check context is populated for the budget stub
        ctx = stubs_by_method["_compute_total"]["context"]
        assert "amount" in ctx["model_fields"]
        assert isinstance(ctx["business_rules"], list)

    def test_report_trailing_newline(self, tmp_path: Path) -> None:
        """JSON report should end with a trailing newline."""
        mod = tmp_path / "test_module"
        mod.mkdir()
        _write_py(mod, "models/test.py", _SIMPLE_COMPUTE_PY)
        _write_py(mod, "__init__.py", "")
        _write_py(mod, "models/__init__.py", "")

        spec = _minimal_spec()
        generate_stub_report(mod, spec)

        raw = (mod / ".odoo-gen-stubs.json").read_text(encoding="utf-8")
        assert raw.endswith("\n"), "JSON should end with trailing newline"
