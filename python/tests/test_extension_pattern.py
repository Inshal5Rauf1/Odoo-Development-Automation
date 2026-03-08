"""Tests for Module Extension Pattern (Phase 59).

Tests cover:
- Pydantic schema validation for extension specs
- Extension preprocessor (depends injection, normalization)
- Extension context builders (model + view)
- Template rendering (extension_model.py.j2, extension_views.xml.j2)
- Renderer integration (render_extensions stage)
- init_models.py.j2 with extension model imports
- Full render_module() pipeline with mixed spec
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def extension_spec() -> dict[str, Any]:
    """Load the full extension spec fixture (hr.employee extension + greenfield model)."""
    with open(FIXTURES_DIR / "extension_spec.json") as f:
        return json.load(f)


@pytest.fixture()
def extension_only_spec() -> dict[str, Any]:
    """Spec with only extensions, no greenfield models."""
    return {
        "module_name": "hr_academic",
        "depends": ["base"],
        "extends": [
            {
                "base_model": "hr.employee",
                "base_module": "hr",
                "add_fields": [
                    {"name": "faculty_id", "type": "Char", "string": "Faculty ID"},
                ],
                "add_computed": [],
                "add_constraints": [],
                "add_methods": [],
                "view_extensions": [],
            }
        ],
    }


# ===========================================================================
# Schema validation tests
# ===========================================================================


class TestExtensionSpecSchema:
    """Test Pydantic schema validates extension specs correctly."""

    def test_extension_spec_schema(self, extension_spec: dict[str, Any]) -> None:
        """ModuleSpec validates a spec dict containing 'extends' array."""
        from odoo_gen_utils.spec_schema import validate_spec

        result = validate_spec(extension_spec)
        assert len(result.extends) == 1
        ext = result.extends[0]
        assert ext.base_model == "hr.employee"
        assert ext.base_module == "hr"
        assert len(ext.add_fields) == 5
        assert len(ext.add_computed) == 1
        assert len(ext.add_constraints) == 1
        assert len(ext.add_methods) == 1
        assert len(ext.view_extensions) == 2
        # Coexistence with models
        assert len(result.models) == 1
        assert result.models[0].name == "uni.faculty.publication"

    def test_extension_spec_schema_mixed(self, extension_spec: dict[str, Any]) -> None:
        """Mixed spec (extends + models) validates without error."""
        from odoo_gen_utils.spec_schema import validate_spec

        result = validate_spec(extension_spec)
        assert result.extends  # has extensions
        assert result.models  # has greenfield models

    def test_extension_spec_schema_rejects_missing_base_model(self) -> None:
        """Missing base_model in extension raises ValidationError."""
        from odoo_gen_utils.spec_schema import ModuleSpec

        spec = {
            "module_name": "test_bad",
            "extends": [
                {
                    "base_module": "hr",
                    "add_fields": [],
                }
            ],
        }
        with pytest.raises(ValidationError):
            ModuleSpec(**spec)

    def test_extension_spec_schema_rejects_missing_base_module(self) -> None:
        """Missing base_module in extension raises ValidationError."""
        from odoo_gen_utils.spec_schema import ModuleSpec

        spec = {
            "module_name": "test_bad",
            "extends": [
                {
                    "base_model": "hr.employee",
                    "add_fields": [],
                }
            ],
        }
        with pytest.raises(ValidationError):
            ModuleSpec(**spec)

    def test_extension_spec_duplicate_base_model_rejected(self) -> None:
        """Duplicate base_model in extends list raises ValidationError."""
        from odoo_gen_utils.spec_schema import ModuleSpec

        spec = {
            "module_name": "test_dup",
            "extends": [
                {
                    "base_model": "hr.employee",
                    "base_module": "hr",
                    "add_fields": [{"name": "x", "type": "Char"}],
                },
                {
                    "base_model": "hr.employee",
                    "base_module": "hr",
                    "add_fields": [{"name": "y", "type": "Char"}],
                },
            ],
        }
        with pytest.raises(ValidationError, match="duplicate"):
            ModuleSpec(**spec)

    def test_extension_field_spec_types(self) -> None:
        """ExtensionFieldSpec accepts various field types."""
        from odoo_gen_utils.spec_schema import ExtensionFieldSpec

        char = ExtensionFieldSpec(name="test", type="Char")
        assert char.name == "test"

        sel = ExtensionFieldSpec(
            name="status", type="Selection",
            selection=[["a", "A"], ["b", "B"]],
        )
        assert len(sel.selection) == 2

        m2o = ExtensionFieldSpec(
            name="partner_id", type="Many2one", comodel="res.partner",
        )
        assert m2o.comodel == "res.partner"


# ===========================================================================
# Preprocessor tests
# ===========================================================================


class TestExtensionPreprocessor:
    """Test the extensions preprocessor."""

    def test_extension_preprocessor(self, extension_spec: dict[str, Any]) -> None:
        """Preprocessor sets has_extensions=True and normalizes entries."""
        from odoo_gen_utils.preprocessors.extensions import _process_extensions

        result = _process_extensions(extension_spec)
        assert result.get("has_extensions") is True
        assert "extension_model_files" in result

    def test_depends_injection(self, extension_spec: dict[str, Any]) -> None:
        """base_module auto-injected into depends list."""
        from odoo_gen_utils.preprocessors.extensions import _process_extensions

        # "hr" is not in the original depends (only "uni_core")
        assert "hr" not in extension_spec["depends"]
        result = _process_extensions(extension_spec)
        assert "hr" in result["depends"]

    def test_depends_no_duplicate(self) -> None:
        """If base_module already in depends, not duplicated."""
        from odoo_gen_utils.preprocessors.extensions import _process_extensions

        spec = {
            "module_name": "test_mod",
            "depends": ["hr", "base"],
            "extends": [
                {
                    "base_model": "hr.employee",
                    "base_module": "hr",
                    "add_fields": [{"name": "x", "type": "Char"}],
                    "add_computed": [],
                    "add_constraints": [],
                    "add_methods": [],
                    "view_extensions": [],
                }
            ],
        }
        result = _process_extensions(spec)
        assert result["depends"].count("hr") == 1

    def test_selection_values_normalized(self) -> None:
        """Preprocessor normalizes 'values' key to 'selection' for Selection fields."""
        from odoo_gen_utils.preprocessors.extensions import _process_extensions

        spec = {
            "module_name": "test_norm",
            "depends": ["base"],
            "extends": [
                {
                    "base_model": "hr.employee",
                    "base_module": "hr",
                    "add_fields": [
                        {
                            "name": "role",
                            "type": "Selection",
                            "values": [["a", "A"], ["b", "B"]],
                        }
                    ],
                    "add_computed": [],
                    "add_constraints": [],
                    "add_methods": [],
                    "view_extensions": [],
                }
            ],
        }
        result = _process_extensions(spec)
        ext = result["extends"][0]
        field = ext["add_fields"][0]
        assert "selection" in field
        assert field["selection"] == [["a", "A"], ["b", "B"]]

    def test_extension_model_files(self, extension_spec: dict[str, Any]) -> None:
        """Preprocessor builds extension_model_files list for init_models."""
        from odoo_gen_utils.preprocessors.extensions import _process_extensions

        result = _process_extensions(extension_spec)
        assert "hr_employee" in result["extension_model_files"]

    def test_no_extends_passthrough(self) -> None:
        """Spec without 'extends' key passes through unchanged."""
        from odoo_gen_utils.preprocessors.extensions import _process_extensions

        spec = {"module_name": "test", "depends": ["base"], "models": []}
        result = _process_extensions(spec)
        assert result.get("has_extensions") is not True
        assert "extension_model_files" not in result


# ===========================================================================
# Context builder tests
# ===========================================================================


class TestExtensionContextBuilder:
    """Test _build_extension_context and _build_extension_view_context."""

    def _get_preprocessed_spec(self, extension_spec: dict[str, Any]) -> dict[str, Any]:
        """Helper: run preprocessor on spec and return first extension."""
        from odoo_gen_utils.preprocessors.extensions import _process_extensions

        return _process_extensions(extension_spec)

    def test_extension_context_builder(self, extension_spec: dict[str, Any]) -> None:
        """_build_extension_context() returns correct dict."""
        from odoo_gen_utils.renderer_context import _build_extension_context

        spec = self._get_preprocessed_spec(extension_spec)
        ext = spec["extends"][0]
        ctx = _build_extension_context(spec, ext)

        assert ctx["base_model"] == "hr.employee"
        assert ctx["base_model_var"] == "hr_employee"
        assert ctx["class_name"] == "HrEmployee"
        assert ctx["module_name"] == "uni_student_hr"
        assert len(ctx["fields"]) == 5
        assert len(ctx["computed_fields"]) == 1
        assert len(ctx["sql_constraints"]) == 1
        assert len(ctx["methods"]) == 1
        assert ctx["needs_api"] is True

    def test_extension_view_context(self, extension_spec: dict[str, Any]) -> None:
        """_build_extension_view_context() returns correct dict for form view."""
        from odoo_gen_utils.renderer_context import _build_extension_view_context

        spec = self._get_preprocessed_spec(extension_spec)
        ext = spec["extends"][0]
        view_ext = ext["view_extensions"][0]
        ctx = _build_extension_view_context(spec, ext, view_ext)

        assert ctx["model_name"] == "hr.employee"
        assert ctx["inherit_id_ref"] == "hr.view_employee_form"
        assert "view_hr_employee_form_inherit_uni_student_hr" == ctx["view_record_id"]
        assert ctx["view_name"] == "hr.employee.form.inherit.uni_student_hr"
        assert len(ctx["insertions"]) == 1
        ins = ctx["insertions"][0]
        assert ins["xpath"] == "//page[@name='public']"
        assert ins["position"] == "after"
        assert ins["content"] == "page"

    def test_extension_view_context_tree(self, extension_spec: dict[str, Any]) -> None:
        """_build_extension_view_context() returns correct dict for tree view."""
        from odoo_gen_utils.renderer_context import _build_extension_view_context

        spec = self._get_preprocessed_spec(extension_spec)
        ext = spec["extends"][0]
        view_ext = ext["view_extensions"][1]  # tree view
        ctx = _build_extension_view_context(spec, ext, view_ext)

        assert "view_hr_employee_tree_inherit_uni_student_hr" == ctx["view_record_id"]
        assert ctx["inherit_id_ref"] == "hr.view_employee_tree"

    def test_mixed_module_context(self, extension_spec: dict[str, Any]) -> None:
        """_build_module_context() includes extension_model_files alongside models."""
        from odoo_gen_utils.renderer_context import _build_module_context

        spec = self._get_preprocessed_spec(extension_spec)
        ctx = _build_module_context(spec, spec["module_name"])

        assert "extension_model_files" in ctx
        assert "hr_employee" in ctx["extension_model_files"]
        assert ctx["has_extensions"] is True
        # Greenfield models are also present
        assert len(ctx["models"]) >= 1
