"""Tests for decomposed renderer stage functions.

Each stage function returns Result[list[Path]] and is independently testable.
Tests verify correct file creation, Result success/failure, and function size limits.
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import pytest

from odoo_gen_utils.renderer import (
    create_versioned_renderer,
    render_manifest,
    render_models,
    render_views,
)
from odoo_gen_utils.validation.types import Result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_spec(
    models: list[dict] | None = None,
    wizards: list[dict] | None = None,
    depends: list[str] | None = None,
) -> dict:
    """Helper to construct a minimal spec dict for testing."""
    return {
        "module_name": "test_module",
        "module_title": "Test Module",
        "summary": "A test module",
        "author": "Test Author",
        "website": "https://test.example.com",
        "license": "LGPL-3",
        "category": "Uncategorized",
        "odoo_version": "17.0",
        "depends": depends or ["base"],
        "application": True,
        "models": models or [],
        "wizards": wizards or [],
    }


def _make_model(name: str = "test.model", fields: list[dict] | None = None) -> dict:
    """Helper to construct a minimal model dict."""
    return {
        "name": name,
        "description": f"Test {name}",
        "fields": fields or [
            {"name": "name", "type": "Char", "required": True},
            {"name": "value", "type": "Integer"},
        ],
    }


def _make_module_context(spec: dict) -> dict:
    """Build shared module context from spec (mirrors render_module setup)."""
    from odoo_gen_utils.renderer import _compute_view_files, _to_python_var, _to_xml_id

    module_name = spec["module_name"]
    models = spec.get("models", [])
    spec_wizards = spec.get("wizards", [])
    has_wizards = bool(spec_wizards)

    from odoo_gen_utils.renderer import SEQUENCE_FIELD_NAMES

    models_with_sequences = [
        m for m in models
        if any(
            f.get("type") == "Char"
            and f.get("name") in SEQUENCE_FIELD_NAMES
            and f.get("required")
            for f in m.get("fields", [])
        )
    ]
    has_sequences = bool(models_with_sequences)

    models_with_company_field = [
        m for m in models
        if any(
            f.get("name") == "company_id" and f.get("type") == "Many2one"
            for f in m.get("fields", [])
        )
    ]
    has_company_modules = bool(models_with_company_field)

    data_files: list[str] = []
    if has_sequences:
        data_files.append("data/sequences.xml")
    data_files.append("data/data.xml")

    wizard_view_files: list[str] = []
    for wizard in spec_wizards:
        wizard_xml_id = _to_xml_id(wizard["name"])
        wizard_view_files.append(f"views/{wizard_xml_id}_wizard_form.xml")

    from odoo_gen_utils.renderer import _compute_manifest_data
    all_manifest_files = _compute_manifest_data(
        spec, data_files, wizard_view_files, has_company_modules=has_company_modules
    )

    return {
        "module_name": module_name,
        "module_title": spec.get("module_title", module_name.replace("_", " ").title()),
        "module_technical_name": module_name,
        "summary": spec.get("summary", ""),
        "author": spec.get("author", ""),
        "website": spec.get("website", ""),
        "license": spec.get("license", "LGPL-3"),
        "category": spec.get("category", "Uncategorized"),
        "odoo_version": spec.get("odoo_version", "17.0"),
        "depends": spec.get("depends", ["base"]),
        "application": spec.get("application", True),
        "models": models,
        "view_files": _compute_view_files(spec),
        "manifest_files": all_manifest_files,
        "has_wizards": has_wizards,
        "spec_wizards": spec_wizards,
    }


@pytest.fixture
def env():
    """Create a versioned Jinja2 renderer."""
    return create_versioned_renderer("17.0")


@pytest.fixture
def tmp_module(tmp_path):
    """Create a temporary module directory."""
    module_dir = tmp_path / "test_module"
    module_dir.mkdir()
    return module_dir


# ---------------------------------------------------------------------------
# render_manifest tests
# ---------------------------------------------------------------------------


class TestRenderManifest:
    def test_returns_result_with_success(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_manifest(env, spec, tmp_module, ctx)
        assert isinstance(result, Result)
        assert result.success is True

    def test_creates_manifest_init_and_models_init(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_manifest(env, spec, tmp_module, ctx)
        paths = result.data
        assert paths is not None
        filenames = [p.name for p in paths]
        assert "__manifest__.py" in filenames
        assert "__init__.py" in filenames
        # models/__init__.py
        assert any(p.name == "__init__.py" and "models" in str(p) for p in paths)

    def test_all_files_exist_on_disk(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_manifest(env, spec, tmp_module, ctx)
        for p in result.data:
            assert p.exists(), f"File {p} should exist on disk"


# ---------------------------------------------------------------------------
# render_models tests
# ---------------------------------------------------------------------------


class TestRenderModels:
    def test_returns_result_with_success(self, env, tmp_module):
        model = _make_model()
        spec = _make_spec(models=[model])
        ctx = _make_module_context(spec)
        result = render_models(env, spec, tmp_module, ctx)
        assert isinstance(result, Result)
        assert result.success is True

    def test_creates_model_py_and_views(self, env, tmp_module):
        model = _make_model("inventory.item")
        spec = _make_spec(models=[model])
        ctx = _make_module_context(spec)
        result = render_models(env, spec, tmp_module, ctx)
        paths = result.data
        assert paths is not None
        filenames = [p.name for p in paths]
        assert "inventory_item.py" in filenames
        assert "inventory_item_views.xml" in filenames
        assert "inventory_item_action.xml" in filenames

    def test_multiple_models(self, env, tmp_module):
        models = [_make_model("test.one"), _make_model("test.two")]
        spec = _make_spec(models=models)
        ctx = _make_module_context(spec)
        result = render_models(env, spec, tmp_module, ctx)
        paths = result.data
        filenames = [p.name for p in paths]
        assert "test_one.py" in filenames
        assert "test_two.py" in filenames

    def test_empty_models_returns_empty_list(self, env, tmp_module):
        spec = _make_spec(models=[])
        ctx = _make_module_context(spec)
        result = render_models(env, spec, tmp_module, ctx)
        assert result.success is True
        assert result.data == []

    def test_verifier_warnings_collected(self, env, tmp_module):
        """When verifier is passed, warnings should be collected."""
        model = _make_model()
        spec = _make_spec(models=[model])
        ctx = _make_module_context(spec)
        # Without verifier, no warnings
        result = render_models(env, spec, tmp_module, ctx, verifier=None)
        assert result.success is True


# ---------------------------------------------------------------------------
# render_views tests
# ---------------------------------------------------------------------------


class TestRenderViews:
    def test_returns_result_with_success(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_views(env, spec, tmp_module, ctx)
        assert isinstance(result, Result)
        assert result.success is True

    def test_creates_menu_xml(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_views(env, spec, tmp_module, ctx)
        paths = result.data
        assert paths is not None
        filenames = [p.name for p in paths]
        assert "menu.xml" in filenames

    def test_menu_file_exists(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_views(env, spec, tmp_module, ctx)
        for p in result.data:
            assert p.exists()


# ---------------------------------------------------------------------------
# Function size limits
# ---------------------------------------------------------------------------


class TestFunctionSizeLimits:
    """Each extracted stage function must be under 80 lines."""

    def test_render_manifest_under_80_lines(self):
        source = inspect.getsource(render_manifest)
        line_count = len(source.splitlines())
        assert line_count < 80, f"render_manifest is {line_count} lines, should be < 80"

    def test_render_models_under_80_lines(self):
        source = inspect.getsource(render_models)
        line_count = len(source.splitlines())
        assert line_count < 80, f"render_models is {line_count} lines, should be < 80"

    def test_render_views_under_80_lines(self):
        source = inspect.getsource(render_views)
        line_count = len(source.splitlines())
        assert line_count < 80, f"render_views is {line_count} lines, should be < 80"
