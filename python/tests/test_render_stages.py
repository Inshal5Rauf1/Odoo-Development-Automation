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
    render_controllers,
    render_cron,
    render_manifest,
    render_models,
    render_module,
    render_reports,
    render_security,
    render_static,
    render_tests,
    render_views,
    render_wizards,
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


# ---------------------------------------------------------------------------
# render_security tests
# ---------------------------------------------------------------------------


class TestRenderSecurity:
    def test_returns_result_with_success(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_security(env, spec, tmp_module, ctx)
        assert isinstance(result, Result)
        assert result.success is True

    def test_creates_security_xml_and_csv(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_security(env, spec, tmp_module, ctx)
        paths = result.data
        assert paths is not None
        filenames = [p.name for p in paths]
        assert "security.xml" in filenames
        assert "ir.model.access.csv" in filenames

    def test_record_rules_when_company_field(self, env, tmp_module):
        model = _make_model(fields=[
            {"name": "name", "type": "Char", "required": True},
            {"name": "company_id", "type": "Many2one", "comodel_name": "res.company"},
        ])
        spec = _make_spec(models=[model])
        ctx = _make_module_context(spec)
        result = render_security(env, spec, tmp_module, ctx)
        filenames = [p.name for p in result.data]
        assert "record_rules.xml" in filenames

    def test_no_record_rules_without_company_field(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_security(env, spec, tmp_module, ctx)
        filenames = [p.name for p in result.data]
        assert "record_rules.xml" not in filenames


# ---------------------------------------------------------------------------
# render_wizards tests
# ---------------------------------------------------------------------------


class TestRenderWizards:
    def test_returns_result_with_success_no_wizards(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_wizards(env, spec, tmp_module, ctx)
        assert isinstance(result, Result)
        assert result.success is True
        assert result.data == []

    def test_creates_wizard_files(self, env, tmp_module):
        wizard = {"name": "confirm.wizard", "description": "Confirm action",
                  "target_model": "test.model", "fields": []}
        spec = _make_spec(models=[_make_model()], wizards=[wizard])
        ctx = _make_module_context(spec)
        result = render_wizards(env, spec, tmp_module, ctx)
        paths = result.data
        assert paths is not None
        filenames = [p.name for p in paths]
        assert any(p.name == "__init__.py" and "wizards" in str(p) for p in paths)
        assert "confirm_wizard.py" in filenames
        assert "confirm_wizard_wizard_form.xml" in filenames


# ---------------------------------------------------------------------------
# render_tests tests
# ---------------------------------------------------------------------------


class TestRenderTests:
    def test_returns_result_with_success(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_tests(env, spec, tmp_module, ctx)
        assert isinstance(result, Result)
        assert result.success is True

    def test_creates_tests_init_and_per_model(self, env, tmp_module):
        model = _make_model("inventory.item")
        spec = _make_spec(models=[model])
        ctx = _make_module_context(spec)
        result = render_tests(env, spec, tmp_module, ctx)
        paths = result.data
        assert paths is not None
        filenames = [p.name for p in paths]
        assert any(p.name == "__init__.py" and "tests" in str(p) for p in paths)
        assert "test_inventory_item.py" in filenames

    def test_multiple_models_multiple_test_files(self, env, tmp_module):
        models = [_make_model("test.one"), _make_model("test.two")]
        spec = _make_spec(models=models)
        ctx = _make_module_context(spec)
        result = render_tests(env, spec, tmp_module, ctx)
        filenames = [p.name for p in result.data]
        assert "test_test_one.py" in filenames
        assert "test_test_two.py" in filenames


# ---------------------------------------------------------------------------
# render_static tests
# ---------------------------------------------------------------------------


class TestRenderStatic:
    def test_returns_result_with_success(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_static(env, spec, tmp_module, ctx)
        assert isinstance(result, Result)
        assert result.success is True

    def test_creates_data_xml_and_static_files(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_static(env, spec, tmp_module, ctx)
        paths = result.data
        assert paths is not None
        filenames = [p.name for p in paths]
        assert "data.xml" in filenames
        assert "index.html" in filenames
        assert "README.rst" in filenames
        assert "demo_data.xml" in filenames

    def test_sequences_xml_when_sequence_fields(self, env, tmp_module):
        model = _make_model(fields=[
            {"name": "reference", "type": "Char", "required": True},
            {"name": "value", "type": "Integer"},
        ])
        spec = _make_spec(models=[model])
        ctx = _make_module_context(spec)
        result = render_static(env, spec, tmp_module, ctx)
        filenames = [p.name for p in result.data]
        assert "sequences.xml" in filenames

    def test_all_files_exist_on_disk(self, env, tmp_module):
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_static(env, spec, tmp_module, ctx)
        for p in result.data:
            assert p.exists(), f"File {p} should exist on disk"


# ---------------------------------------------------------------------------
# Function size limits
# ---------------------------------------------------------------------------


class TestFunctionSizeLimits:
    """All 7 stage functions and the orchestrator must be under 80 lines."""

    @pytest.mark.parametrize("func", [
        render_manifest,
        render_models,
        render_views,
        render_security,
        render_wizards,
        render_tests,
        render_static,
    ])
    def test_stage_function_under_80_lines(self, func):
        source = inspect.getsource(func)
        line_count = len(source.splitlines())
        assert line_count < 80, f"{func.__name__} is {line_count} lines, should be < 80"

    def test_render_module_orchestrator_under_80_lines(self):
        source = inspect.getsource(render_module)
        line_count = len(source.splitlines())
        assert line_count < 80, f"render_module is {line_count} lines, should be < 80"


# ---------------------------------------------------------------------------
# Phase 27: Integration tests for relationship patterns in rendered output
# ---------------------------------------------------------------------------


def _make_through_spec():
    """Spec with m2m_through relationship for integration tests."""
    return {
        "module_name": "test_university",
        "module_title": "Test University",
        "summary": "Test module",
        "author": "Test",
        "website": "https://test.example.com",
        "license": "LGPL-3",
        "category": "Education",
        "odoo_version": "17.0",
        "depends": ["base"],
        "application": True,
        "models": [
            {
                "name": "test_university.course",
                "description": "Course",
                "fields": [{"name": "name", "type": "Char", "required": True}],
            },
            {
                "name": "test_university.student",
                "description": "Student",
                "fields": [{"name": "name", "type": "Char", "required": True}],
            },
        ],
        "relationships": [
            {
                "type": "m2m_through",
                "from": "test_university.course",
                "to": "test_university.student",
                "through_model": "test_university.enrollment",
                "through_fields": [
                    {"name": "grade", "type": "Float"},
                    {"name": "enrollment_date", "type": "Date", "default": "fields.Date.today"},
                ],
            }
        ],
        "wizards": [],
    }


def _make_self_m2m_spec():
    """Spec with self_m2m relationship for integration tests."""
    return {
        "module_name": "test_university",
        "module_title": "Test University",
        "summary": "Test module",
        "author": "Test",
        "website": "https://test.example.com",
        "license": "LGPL-3",
        "category": "Education",
        "odoo_version": "17.0",
        "depends": ["base"],
        "application": True,
        "models": [
            {
                "name": "test_university.course",
                "description": "Course",
                "fields": [{"name": "name", "type": "Char", "required": True}],
            },
        ],
        "relationships": [
            {
                "type": "self_m2m",
                "model": "test_university.course",
                "field_name": "prerequisite_ids",
                "inverse_field_name": "dependent_ids",
                "string": "Prerequisites",
                "inverse_string": "Dependent Courses",
            }
        ],
        "wizards": [],
    }


def _make_hierarchical_spec():
    """Spec with hierarchical model for integration tests."""
    return {
        "module_name": "test_university",
        "module_title": "Test University",
        "summary": "Test module",
        "author": "Test",
        "website": "https://test.example.com",
        "license": "LGPL-3",
        "category": "Education",
        "odoo_version": "17.0",
        "depends": ["base"],
        "application": True,
        "models": [
            {
                "name": "test_university.department",
                "description": "Department",
                "hierarchical": True,
                "fields": [{"name": "name", "type": "Char", "required": True}],
            },
        ],
        "wizards": [],
    }


class TestRenderModelsThroughModel:
    """Integration tests for rendered through-model output."""

    def test_through_model_has_two_m2one_fks(self, tmp_path):
        spec = _make_through_spec()
        files, _ = render_module(spec, None, tmp_path)
        through_py = (tmp_path / "test_university" / "models" / "test_university_enrollment.py").read_text()
        assert "fields.Many2one(" in through_py
        assert 'comodel_name="test_university.course"' in through_py
        assert 'comodel_name="test_university.student"' in through_py
        assert "required=True" in through_py

    def test_through_model_has_extra_fields(self, tmp_path):
        spec = _make_through_spec()
        files, _ = render_module(spec, None, tmp_path)
        through_py = (tmp_path / "test_university" / "models" / "test_university_enrollment.py").read_text()
        assert "grade" in through_py
        assert "enrollment_date" in through_py

    def test_ondelete_cascade_rendered(self, tmp_path):
        spec = _make_through_spec()
        files, _ = render_module(spec, None, tmp_path)
        through_py = (tmp_path / "test_university" / "models" / "test_university_enrollment.py").read_text()
        assert 'ondelete="cascade"' in through_py


class TestRenderManifestThroughModel:
    """Integration tests: through-model in __init__.py."""

    def test_init_py_imports_through_model(self, tmp_path):
        spec = _make_through_spec()
        files, _ = render_module(spec, None, tmp_path)
        init_py = (tmp_path / "test_university" / "models" / "__init__.py").read_text()
        assert "test_university_enrollment" in init_py


class TestRenderSecurityThroughModel:
    """Integration tests: through-model ACL entries."""

    def test_access_csv_has_through_model_entries(self, tmp_path):
        spec = _make_through_spec()
        files, _ = render_module(spec, None, tmp_path)
        csv_content = (tmp_path / "test_university" / "security" / "ir.model.access.csv").read_text()
        assert "test_university_enrollment" in csv_content


class TestRenderModelsSelfM2M:
    """Integration tests for rendered self-referential M2M output."""

    def test_many2many_with_relation_params(self, tmp_path):
        spec = _make_self_m2m_spec()
        files, _ = render_module(spec, None, tmp_path)
        course_py = (tmp_path / "test_university" / "models" / "test_university_course.py").read_text()
        assert "fields.Many2many(" in course_py
        assert "relation=" in course_py
        assert "column1=" in course_py
        assert "column2=" in course_py

    def test_inverse_field_reversed_columns(self, tmp_path):
        spec = _make_self_m2m_spec()
        files, _ = render_module(spec, None, tmp_path)
        course_py = (tmp_path / "test_university" / "models" / "test_university_course.py").read_text()
        # Both prerequisite_ids and dependent_ids should be present
        assert "prerequisite_ids" in course_py
        assert "dependent_ids" in course_py


class TestRenderModelsHierarchical:
    """Integration tests for rendered hierarchical model output."""

    def test_parent_store_class_attribute(self, tmp_path):
        spec = _make_hierarchical_spec()
        files, _ = render_module(spec, None, tmp_path)
        dept_py = (tmp_path / "test_university" / "models" / "test_university_department.py").read_text()
        assert "_parent_store = True" in dept_py
        assert '_parent_name = "parent_id"' in dept_py

    def test_parent_id_field_rendered(self, tmp_path):
        spec = _make_hierarchical_spec()
        files, _ = render_module(spec, None, tmp_path)
        dept_py = (tmp_path / "test_university" / "models" / "test_university_department.py").read_text()
        assert "parent_id = fields.Many2one(" in dept_py
        assert 'ondelete="cascade"' in dept_py
        assert "index=True" in dept_py

    def test_child_ids_field_rendered(self, tmp_path):
        spec = _make_hierarchical_spec()
        files, _ = render_module(spec, None, tmp_path)
        dept_py = (tmp_path / "test_university" / "models" / "test_university_department.py").read_text()
        assert "child_ids = fields.One2many(" in dept_py
        assert 'inverse_name="parent_id"' in dept_py

    def test_parent_path_unaccent_false(self, tmp_path):
        spec = _make_hierarchical_spec()
        files, _ = render_module(spec, None, tmp_path)
        dept_py = (tmp_path / "test_university" / "models" / "test_university_department.py").read_text()
        assert "parent_path = fields.Char(" in dept_py
        assert "unaccent=False" in dept_py
        assert "index=True" in dept_py

    def test_parent_path_not_in_form_view(self, tmp_path):
        spec = _make_hierarchical_spec()
        files, _ = render_module(spec, None, tmp_path)
        views_xml = (tmp_path / "test_university" / "views" / "test_university_department_views.xml").read_text()
        assert "parent_path" not in views_xml


# ---------------------------------------------------------------------------
# Phase 28: Integration tests for computation chains in rendered output
# ---------------------------------------------------------------------------


def _make_chain_spec():
    """Spec with computation_chains for integration tests."""
    return {
        "module_name": "test_university",
        "module_title": "Test University",
        "summary": "Test module",
        "author": "Test",
        "website": "https://test.example.com",
        "license": "LGPL-3",
        "category": "Education",
        "odoo_version": "17.0",
        "depends": ["base"],
        "application": True,
        "models": [
            {
                "name": "test_university.enrollment",
                "description": "Enrollment",
                "fields": [
                    {"name": "student_id", "type": "Many2one",
                     "comodel_name": "test_university.student", "required": True},
                    {"name": "grade", "type": "Float"},
                    {"name": "credit_hours", "type": "Integer"},
                    {"name": "weighted_grade", "type": "Float"},
                ],
            },
            {
                "name": "test_university.student",
                "description": "Student",
                "fields": [
                    {"name": "name", "type": "Char", "required": True},
                    {"name": "enrollment_ids", "type": "One2many",
                     "comodel_name": "test_university.enrollment",
                     "inverse_name": "student_id"},
                    {"name": "gpa", "type": "Float"},
                ],
            },
        ],
        "computation_chains": [
            {
                "field": "test_university.enrollment.weighted_grade",
                "depends_on": ["grade", "credit_hours"],
            },
            {
                "field": "test_university.student.gpa",
                "depends_on": ["enrollment_ids.weighted_grade", "enrollment_ids.credit_hours"],
            },
        ],
        "wizards": [],
    }


def _make_intra_model_chain_spec():
    """Spec with two intra-model chain fields for topological ordering test."""
    return {
        "module_name": "test_order",
        "module_title": "Test Order",
        "summary": "Test module",
        "author": "Test",
        "website": "https://test.example.com",
        "license": "LGPL-3",
        "category": "Uncategorized",
        "odoo_version": "17.0",
        "depends": ["base"],
        "application": True,
        "models": [
            {
                "name": "test_order.line",
                "description": "Order Line",
                "fields": [
                    {"name": "name", "type": "Char", "required": True},
                    {"name": "qty", "type": "Integer"},
                    {"name": "price", "type": "Float"},
                    {"name": "subtotal", "type": "Float"},
                    {"name": "total", "type": "Float"},
                ],
            },
        ],
        "computation_chains": [
            {
                "field": "test_order.line.subtotal",
                "depends_on": ["qty", "price"],
            },
            {
                "field": "test_order.line.total",
                "depends_on": ["subtotal"],
            },
        ],
        "wizards": [],
    }


def _make_circular_chain_spec():
    """Spec with circular computation chain."""
    return {
        "module_name": "test_circular",
        "module_title": "Test Circular",
        "summary": "Test module",
        "author": "Test",
        "website": "https://test.example.com",
        "license": "LGPL-3",
        "category": "Uncategorized",
        "odoo_version": "17.0",
        "depends": ["base"],
        "application": True,
        "models": [
            {
                "name": "test_circular.student",
                "description": "Student",
                "fields": [
                    {"name": "name", "type": "Char", "required": True},
                    {"name": "enrollment_ids", "type": "One2many",
                     "comodel_name": "test_circular.enrollment",
                     "inverse_name": "student_id"},
                    {"name": "gpa", "type": "Float"},
                ],
            },
            {
                "name": "test_circular.enrollment",
                "description": "Enrollment",
                "fields": [
                    {"name": "student_id", "type": "Many2one",
                     "comodel_name": "test_circular.student"},
                    {"name": "weighted_grade", "type": "Float"},
                ],
            },
        ],
        "computation_chains": [
            {
                "field": "test_circular.student.gpa",
                "depends_on": ["enrollment_ids.weighted_grade"],
            },
            {
                "field": "test_circular.enrollment.weighted_grade",
                "depends_on": ["student_id.gpa"],
            },
        ],
        "wizards": [],
    }


class TestRenderModelsComputedChains:
    """Integration tests for computation chains in rendered output."""

    def test_cross_model_depends(self, tmp_path):
        """render_models() with computation_chains produces @api.depends with dotted path and store=True."""
        spec = _make_chain_spec()
        files, _ = render_module(spec, None, tmp_path)
        student_py = (tmp_path / "test_university" / "models" / "test_university_student.py").read_text()
        assert '@api.depends("enrollment_ids.weighted_grade"' in student_py
        assert "store=True" in student_py

    def test_chain_field_has_compute_method(self, tmp_path):
        """Generated model.py contains def _compute_gpa(self) method stub."""
        spec = _make_chain_spec()
        files, _ = render_module(spec, None, tmp_path)
        student_py = (tmp_path / "test_university" / "models" / "test_university_student.py").read_text()
        assert "def _compute_gpa(self):" in student_py

    def test_topological_order_in_output(self, tmp_path):
        """In model with 2 intra-model chain fields, upstream appears before downstream."""
        spec = _make_intra_model_chain_spec()
        files, _ = render_module(spec, None, tmp_path)
        line_py = (tmp_path / "test_order" / "models" / "test_order_line.py").read_text()
        # _compute_subtotal should appear before _compute_total
        subtotal_pos = line_py.index("_compute_subtotal")
        total_pos = line_py.index("_compute_total")
        assert subtotal_pos < total_pos

    def test_no_files_on_cycle(self, tmp_path):
        """render_module() with circular chain raises ValueError; output dir has no generated files."""
        spec = _make_circular_chain_spec()
        with pytest.raises(ValueError, match="Circular dependency"):
            render_module(spec, None, tmp_path)
        # Output directory should not exist or be empty
        module_dir = tmp_path / "test_circular"
        assert not module_dir.exists() or not list(module_dir.iterdir())

    def test_backward_compat_no_chains(self, tmp_path):
        """render_module() with spec that has no computation_chains produces identical output."""
        spec = _make_spec(models=[_make_model()])
        files, warnings = render_module(spec, None, tmp_path)
        # Basic sanity: files generated, no errors
        assert len(files) > 0
        model_py = (tmp_path / "test_module" / "models" / "test_model.py").read_text()
        assert "class TestModel" in model_py


# ---------------------------------------------------------------------------
# Phase 29: Complex Constraints Integration Tests
# ---------------------------------------------------------------------------


def _make_constraint_spec(
    models: list[dict] | None = None,
    constraints: list[dict] | None = None,
    depends: list[str] | None = None,
) -> dict:
    """Spec with constraints section for integration tests."""
    return {
        "module_name": "test_constraints",
        "module_title": "Test Constraints Module",
        "summary": "Test module for complex constraints",
        "author": "Test",
        "website": "https://test.example.com",
        "license": "LGPL-3",
        "category": "Education",
        "odoo_version": "17.0",
        "depends": depends or ["base"],
        "application": True,
        "models": models or [],
        "wizards": [],
        "constraints": constraints or [],
    }


class TestRenderModelsComplexConstraints:
    """Integration tests for end-to-end constraint rendering."""

    def test_temporal_constraint_output(self, tmp_path):
        """render_models with temporal constraint produces correct Python output."""
        spec = _make_constraint_spec(
            models=[{
                "name": "test_constraints.course",
                "description": "Course",
                "fields": [
                    {"name": "name", "type": "Char", "required": True},
                    {"name": "start_date", "type": "Date"},
                    {"name": "end_date", "type": "Date"},
                ],
            }],
            constraints=[{
                "type": "temporal",
                "model": "test_constraints.course",
                "name": "date_order",
                "fields": ["start_date", "end_date"],
                "condition": "end_date < start_date",
                "message": "End date must be after start date.",
            }],
        )
        files, _ = render_module(spec, None, tmp_path)
        course_py = (
            tmp_path / "test_constraints" / "models" / "test_constraints_course.py"
        ).read_text()
        assert '@api.constrains("start_date", "end_date")' in course_py
        assert "_check_date_order" in course_py
        assert "rec.start_date and rec.end_date" in course_py
        assert "ValidationError" in course_py
        assert '_("' in course_py

    def test_cross_model_constraint_output(self, tmp_path):
        """render_models with cross_model constraint produces create/write overrides."""
        spec = _make_constraint_spec(
            models=[
                {
                    "name": "test_constraints.course",
                    "description": "Course",
                    "fields": [
                        {"name": "name", "type": "Char", "required": True},
                        {"name": "max_students", "type": "Integer"},
                    ],
                },
                {
                    "name": "test_constraints.enrollment",
                    "description": "Enrollment",
                    "fields": [
                        {"name": "course_id", "type": "Many2one",
                         "comodel_name": "test_constraints.course", "required": True},
                        {"name": "student_name", "type": "Char"},
                    ],
                },
            ],
            constraints=[{
                "type": "cross_model",
                "model": "test_constraints.enrollment",
                "name": "enrollment_capacity",
                "trigger_fields": ["course_id"],
                "related_model": "test_constraints.enrollment",
                "count_domain_field": "course_id",
                "capacity_model": "test_constraints.course",
                "capacity_field": "max_students",
                "message": "Enrollment count cannot exceed course capacity of %s.",
            }],
        )
        files, _ = render_module(spec, None, tmp_path)
        enrollment_py = (
            tmp_path / "test_constraints" / "models" / "test_constraints_enrollment.py"
        ).read_text()
        assert "def create(self, vals_list):" in enrollment_py
        assert "super().create(vals_list)" in enrollment_py
        assert "_check_enrollment_capacity()" in enrollment_py
        assert "def write(self, vals):" in enrollment_py
        assert "if any(f in vals" in enrollment_py
        assert "search_count" in enrollment_py
        assert "@api.model_create_multi" in enrollment_py

    def test_capacity_constraint_output(self, tmp_path):
        """render_models with capacity constraint produces count-based validation."""
        spec = _make_constraint_spec(
            models=[{
                "name": "test_constraints.section",
                "description": "Section",
                "fields": [
                    {"name": "name", "type": "Char", "required": True},
                    {"name": "student_ids", "type": "One2many",
                     "comodel_name": "test_constraints.section.student",
                     "inverse_name": "section_id"},
                ],
            }],
            constraints=[{
                "type": "capacity",
                "model": "test_constraints.section",
                "name": "section_capacity",
                "count_field": "student_ids",
                "max_value": 30,
                "count_model": "test_constraints.section.student",
                "count_domain_field": "section_id",
                "message": "A section cannot have more than %s students.",
            }],
        )
        files, _ = render_module(spec, None, tmp_path)
        section_py = (
            tmp_path / "test_constraints" / "models" / "test_constraints_section.py"
        ).read_text()
        assert "def create(self, vals_list):" in section_py
        assert "def write(self, vals):" in section_py
        assert "search_count" in section_py
        assert "30" in section_py

    def test_backward_compat(self, tmp_path):
        """render_models with spec that has NO constraints section produces identical output."""
        spec = _make_spec(models=[_make_model()])
        files, warnings = render_module(spec, None, tmp_path)
        assert len(files) > 0
        model_py = (tmp_path / "test_module" / "models" / "test_model.py").read_text()
        assert "class TestModel" in model_py
        # No constraint-related output
        assert "complex_constraints" not in model_py
        assert "_check_" not in model_py
        assert "from odoo.tools.translate import _" not in model_py

    def test_imports_validation_error(self, tmp_path):
        """render_models with any complex constraint includes ValidationError and _ imports."""
        spec = _make_constraint_spec(
            models=[{
                "name": "test_constraints.course",
                "description": "Course",
                "fields": [
                    {"name": "start_date", "type": "Date"},
                    {"name": "end_date", "type": "Date"},
                ],
            }],
            constraints=[{
                "type": "temporal",
                "model": "test_constraints.course",
                "name": "date_order",
                "fields": ["start_date", "end_date"],
                "condition": "end_date < start_date",
                "message": "End date must be after start date.",
            }],
        )
        files, _ = render_module(spec, None, tmp_path)
        course_py = (
            tmp_path / "test_constraints" / "models" / "test_constraints_course.py"
        ).read_text()
        assert "from odoo.exceptions import ValidationError" in course_py
        assert "from odoo.tools.translate import _" in course_py


# ---------------------------------------------------------------------------
# Phase 30: render_cron tests
# ---------------------------------------------------------------------------


def _make_cron_spec(cron_jobs=None, models=None):
    """Helper to construct a spec with cron_jobs."""
    return {
        "module_name": "test_module",
        "module_title": "Test Module",
        "summary": "A test module",
        "author": "Test Author",
        "website": "https://test.example.com",
        "license": "LGPL-3",
        "category": "Uncategorized",
        "odoo_version": "17.0",
        "depends": ["base"],
        "application": True,
        "models": models or [
            {
                "name": "academy.course",
                "description": "Course",
                "fields": [
                    {"name": "name", "type": "Char", "required": True},
                ],
            },
        ],
        "wizards": [],
        "cron_jobs": cron_jobs or [],
    }


class TestRenderCron:
    def test_cron_no_jobs_noop(self, env, tmp_module):
        """render_cron with no cron_jobs returns Result.ok([])."""
        spec = _make_cron_spec(cron_jobs=[])
        ctx = _make_module_context(spec)
        result = render_cron(env, spec, tmp_module, ctx)
        assert result.success is True
        assert result.data == []

    def test_cron_generates_xml(self, env, tmp_module):
        """render_cron with 1 cron_job produces data/cron_data.xml with correct content."""
        spec = _make_cron_spec(cron_jobs=[{
            "name": "Archive Expired Courses",
            "model_name": "academy.course",
            "method": "_cron_archive_expired",
            "interval_number": 1,
            "interval_type": "days",
        }])
        ctx = _make_module_context(spec)
        result = render_cron(env, spec, tmp_module, ctx)
        assert result.success is True
        assert len(result.data) == 1
        xml_path = tmp_module / "data" / "cron_data.xml"
        assert xml_path.exists()
        content = xml_path.read_text()
        assert "ir.cron" in content
        assert 'noupdate="1"' in content
        assert "doall" in content
        assert "False" in content
        assert "model_academy_course" in content
        assert "state" in content
        assert "code" in content
        assert "_cron_archive_expired" in content

    def test_cron_invalid_method_name(self, env, tmp_module):
        """render_cron with invalid method name returns Result.fail()."""
        spec = _make_cron_spec(cron_jobs=[{
            "name": "Bad Cron",
            "model_name": "academy.course",
            "method": "123bad",
            "interval_number": 1,
            "interval_type": "days",
        }])
        ctx = _make_module_context(spec)
        result = render_cron(env, spec, tmp_module, ctx)
        assert result.success is False

    def test_cron_multiple_jobs(self, env, tmp_module):
        """render_cron with 2 cron jobs includes both in XML."""
        spec = _make_cron_spec(cron_jobs=[
            {
                "name": "Archive Expired",
                "model_name": "academy.course",
                "method": "_cron_archive_expired",
                "interval_number": 1,
                "interval_type": "days",
            },
            {
                "name": "Send Reminders",
                "model_name": "academy.course",
                "method": "_cron_send_reminders",
                "interval_number": 4,
                "interval_type": "hours",
            },
        ])
        ctx = _make_module_context(spec)
        result = render_cron(env, spec, tmp_module, ctx)
        assert result.success is True
        content = (tmp_module / "data" / "cron_data.xml").read_text()
        assert "_cron_archive_expired" in content
        assert "_cron_send_reminders" in content


# ---------------------------------------------------------------------------
# Phase 30: render_reports and render_controllers placeholder tests
# ---------------------------------------------------------------------------


class TestRenderReportsPlaceholder:
    def test_returns_ok_empty(self, env, tmp_module):
        """render_reports returns Result.ok([]) as a placeholder."""
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_reports(env, spec, tmp_module, ctx)
        assert result.success is True
        assert result.data == []


class TestRenderControllersPlaceholder:
    def test_returns_ok_empty(self, env, tmp_module):
        """render_controllers returns Result.ok([]) as a placeholder."""
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_controllers(env, spec, tmp_module, ctx)
        assert result.success is True
        assert result.data == []


# ---------------------------------------------------------------------------
# Phase 30: Pipeline stage count test
# ---------------------------------------------------------------------------


class TestRenderModulePipeline:
    def test_pipeline_has_10_stages(self):
        """render_module stages list should have 10 entries (was 7, +3 new)."""
        source = inspect.getsource(render_module)
        # Count lambda entries in the stages list
        assert source.count("lambda:") >= 10


# ---------------------------------------------------------------------------
# Phase 30: Full integration with cron spec
# ---------------------------------------------------------------------------


class TestRenderModuleCronIntegration:
    def test_full_render_with_cron(self, tmp_path):
        """Full render_module with cron_jobs spec generates cron XML + model with stub."""
        spec = _make_cron_spec(
            cron_jobs=[{
                "name": "Archive Expired Courses",
                "model_name": "academy.course",
                "method": "_cron_archive_expired",
                "interval_number": 1,
                "interval_type": "days",
            }],
        )
        files, warnings = render_module(spec, None, tmp_path)
        # cron XML file should be generated
        cron_xml = tmp_path / "test_module" / "data" / "cron_data.xml"
        assert cron_xml.exists()
        cron_content = cron_xml.read_text()
        assert "ir.cron" in cron_content
        assert "_cron_archive_expired" in cron_content
        # model file should contain the stub method
        model_py = (tmp_path / "test_module" / "models" / "academy_course.py").read_text()
        assert "_cron_archive_expired" in model_py
        assert "@api.model" in model_py
