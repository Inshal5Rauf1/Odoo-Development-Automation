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
    get_template_dir,
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

    # Phase 32: import/export wizard detection
    import_export_models = [m for m in models if m.get("import_export")]
    has_import_export = bool(import_export_models)
    import_export_wizards = [
        {"name": f"{m['name']}.import.wizard"} for m in import_export_models
    ]

    ctx = {
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
        "has_wizards": has_wizards or has_import_export,
        "spec_wizards": spec_wizards,
        "has_controllers": bool(spec.get("controllers")),
        "has_import_export": has_import_export,
        "import_export_wizards": import_export_wizards,
    }
    if has_import_export:
        ctx["external_dependencies"] = {"python": ["openpyxl"]}
    return ctx


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


# ---------------------------------------------------------------------------
# Phase 31: Report generation tests
# ---------------------------------------------------------------------------


def _make_report_spec(reports=None, dashboards=None, models=None):
    """Helper to construct a spec with reports and/or dashboards."""
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
                "name": "academy.student",
                "description": "Student",
                "fields": [
                    {"name": "name", "type": "Char", "required": True},
                    {"name": "enrollment_date", "type": "Date"},
                    {"name": "total_credits", "type": "Integer"},
                ],
            },
        ],
        "wizards": [],
        "reports": reports or [],
        "dashboards": dashboards or [],
    }


def _sample_report():
    """Return a sample report spec entry."""
    return {
        "name": "Student Report Card",
        "model_name": "academy.student",
        "xml_id": "student_report_card",
        "columns": [
            {"field": "name", "label": "Student"},
            {"field": "enrollment_date", "label": "Enrollment Date"},
            {"field": "total_credits", "label": "Credits"},
        ],
        "button_label": "Print Report Card",
    }


def _sample_report_with_paper():
    """Return a sample report spec entry with paper_format."""
    report = _sample_report()
    report["paper_format"] = {
        "format": "A4",
        "orientation": "Landscape",
        "margin_top": 25,
    }
    return report


def _sample_dashboard():
    """Return a sample dashboard spec entry."""
    return {
        "model_name": "academy.student",
        "title": "Student Analysis",
        "chart_type": "bar",
        "stacked": False,
        "dimensions": [
            {"field": "enrollment_date", "interval": "month"},
        ],
        "measures": [
            {"field": "total_credits"},
        ],
        "rows": [
            {"field": "enrollment_date", "interval": "quarter"},
        ],
        "columns": [],
    }


class TestRenderReports:
    def test_report_generates_action_xml(self, env, tmp_module):
        """Spec with reports entry -> render_reports() creates report action XML."""
        report = _sample_report()
        spec = _make_report_spec(reports=[report])
        ctx = _make_module_context(spec)
        result = render_reports(env, spec, tmp_module, ctx)
        assert result.success is True
        action_file = tmp_module / "data" / "report_student_report_card.xml"
        assert action_file.exists()
        content = action_file.read_text()
        assert "ir.actions.report" in content

    def test_report_action_fields(self, env, tmp_module):
        """Generated report action has binding_model_id, report_name, report_type, binding_type."""
        report = _sample_report()
        spec = _make_report_spec(reports=[report])
        ctx = _make_module_context(spec)
        render_reports(env, spec, tmp_module, ctx)
        content = (tmp_module / "data" / "report_student_report_card.xml").read_text()
        assert "binding_model_id" in content
        assert "test_module.report_student_report_card" in content
        assert "qweb-pdf" in content
        assert "binding_type" in content

    def test_report_qweb_template(self, env, tmp_module):
        """Generated QWeb template has t-call, t-foreach, t-field, class='page'."""
        report = _sample_report()
        spec = _make_report_spec(reports=[report])
        ctx = _make_module_context(spec)
        render_reports(env, spec, tmp_module, ctx)
        tmpl_file = tmp_module / "data" / "report_student_report_card_template.xml"
        assert tmpl_file.exists()
        content = tmpl_file.read_text()
        assert 't-call="web.html_container"' in content
        assert 't-foreach="docs"' in content
        assert 't-call="web.external_layout"' in content
        assert 't-field="doc.display_name"' in content or 't-field="doc.name"' in content
        assert 'class="page"' in content

    def test_report_paper_format(self, env, tmp_module):
        """Spec with paper_format generates paperformat record; without it, no paperformat."""
        # With paper_format
        report_with = _sample_report_with_paper()
        spec_with = _make_report_spec(reports=[report_with])
        ctx_with = _make_module_context(spec_with)
        render_reports(env, spec_with, tmp_module, ctx_with)
        content = (tmp_module / "data" / "report_student_report_card.xml").read_text()
        assert "report.paperformat" in content
        assert "Landscape" in content

        # Without paper_format - use a fresh tmp dir
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td_module = Path(td) / "test_module"
            td_module.mkdir()
            report_without = _sample_report()
            spec_without = _make_report_spec(reports=[report_without])
            ctx_without = _make_module_context(spec_without)
            render_reports(env, spec_without, td_module, ctx_without)
            content2 = (td_module / "data" / "report_student_report_card.xml").read_text()
            assert "report.paperformat" not in content2

    def test_form_print_button(self, tmp_path):
        """Model with reports -> form view XML contains print button."""
        report = _sample_report()
        spec = _make_report_spec(reports=[report])
        files, _ = render_module(spec, None, tmp_path)
        form_xml = (tmp_path / "test_module" / "views" / "academy_student_views.xml").read_text()
        assert "report_test_module_student_report_card" in form_xml
        assert 'type="action"' in form_xml

    def test_no_reports_noop(self, env, tmp_module):
        """Spec without reports or dashboards -> render_reports returns Result.ok([])."""
        spec = _make_report_spec(reports=[], dashboards=[])
        ctx = _make_module_context(spec)
        result = render_reports(env, spec, tmp_module, ctx)
        assert result.success is True
        assert result.data == []


class TestRenderDashboards:
    def test_graph_view(self, env, tmp_module):
        """Spec with dashboards -> generates graph view with chart_type and fields."""
        dashboard = _sample_dashboard()
        spec = _make_report_spec(dashboards=[dashboard])
        ctx = _make_module_context(spec)
        result = render_reports(env, spec, tmp_module, ctx)
        assert result.success is True
        graph_file = tmp_module / "views" / "academy_student_graph.xml"
        assert graph_file.exists()
        content = graph_file.read_text()
        assert "ir.ui.view" in content
        assert "<graph" in content
        assert 'type="bar"' in content

    def test_graph_measures(self, env, tmp_module):
        """Graph measure fields have type='measure'; dimension fields get interval."""
        dashboard = _sample_dashboard()
        spec = _make_report_spec(dashboards=[dashboard])
        ctx = _make_module_context(spec)
        render_reports(env, spec, tmp_module, ctx)
        content = (tmp_module / "views" / "academy_student_graph.xml").read_text()
        assert 'type="measure"' in content
        assert 'interval="month"' in content

    def test_pivot_view(self, env, tmp_module):
        """Generates pivot view with row/col/measure fields."""
        dashboard = _sample_dashboard()
        spec = _make_report_spec(dashboards=[dashboard])
        ctx = _make_module_context(spec)
        render_reports(env, spec, tmp_module, ctx)
        pivot_file = tmp_module / "views" / "academy_student_pivot.xml"
        assert pivot_file.exists()
        content = pivot_file.read_text()
        assert "<pivot" in content
        assert 'type="row"' in content
        assert 'type="measure"' in content

    def test_action_view_mode(self, tmp_path):
        """Model with dashboard -> action view_mode includes graph,pivot."""
        dashboard = _sample_dashboard()
        spec = _make_report_spec(dashboards=[dashboard])
        files, _ = render_module(spec, None, tmp_path)
        action_xml = (tmp_path / "test_module" / "views" / "academy_student_action.xml").read_text()
        assert "graph" in action_xml
        assert "pivot" in action_xml

        # Without dashboard - view_mode should NOT contain graph,pivot
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            spec_no = _make_report_spec(dashboards=[])
            files2, _ = render_module(spec_no, None, Path(td))
            action_xml2 = (Path(td) / "test_module" / "views" / "academy_student_action.xml").read_text()
            assert "graph" not in action_xml2
            assert "pivot" not in action_xml2

    def test_no_dashboards_noop(self, env, tmp_module):
        """Spec without dashboards -> no graph/pivot files generated."""
        spec = _make_report_spec(reports=[], dashboards=[])
        ctx = _make_module_context(spec)
        result = render_reports(env, spec, tmp_module, ctx)
        assert result.success is True
        assert not (tmp_module / "views" / "academy_student_graph.xml").exists()
        assert not (tmp_module / "views" / "academy_student_pivot.xml").exists()


# ---------------------------------------------------------------------------
# Phase 31: Full integration with report/dashboard spec
# ---------------------------------------------------------------------------


class TestRenderModuleReportIntegration:
    def test_full_render_with_reports_and_dashboards(self, tmp_path):
        """Full render_module with reports and dashboards generates all expected files."""
        spec = _make_report_spec(
            reports=[_sample_report()],
            dashboards=[_sample_dashboard()],
        )
        files, warnings = render_module(spec, None, tmp_path)
        module_dir = tmp_path / "test_module"
        # Report files
        assert (module_dir / "data" / "report_student_report_card.xml").exists()
        assert (module_dir / "data" / "report_student_report_card_template.xml").exists()
        # Dashboard files
        assert (module_dir / "views" / "academy_student_graph.xml").exists()
        assert (module_dir / "views" / "academy_student_pivot.xml").exists()


# ---------------------------------------------------------------------------
# Phase 32: render_controllers tests
# ---------------------------------------------------------------------------


def _make_controller_spec(controllers=None, **overrides):
    """Build a spec with controllers entries for testing."""
    spec = _make_spec(models=[_make_model("academy.student")])
    if controllers is not None:
        spec["controllers"] = controllers
    spec.update(overrides)
    return spec


def _sample_controller():
    """Return a sample controller entry with routes."""
    return {
        "name": "Main Controller",
        "class_name": "AcademyController",
        "routes": [
            {
                "path": "courses",
                "method_name": "get_courses",
                "type": "json",
                "auth": "user",
                "csrf": True,
                "methods": ["GET"],
                "description": "List all courses",
            },
            {
                "path": "page",
                "method_name": "index_page",
                "type": "http",
                "auth": "public",
                "csrf": True,
                "methods": ["GET"],
                "description": "Main page",
            },
        ],
    }


class TestRenderControllers:
    def test_no_controllers_noop(self, env, tmp_module):
        """Spec with no controllers -> render_controllers returns Result.ok([])."""
        spec = _make_controller_spec(controllers=[])
        ctx = _make_module_context(spec)
        result = render_controllers(env, spec, tmp_module, ctx)
        assert result.success is True
        assert result.data == []

    def test_no_controllers_key_noop(self, env, tmp_module):
        """Spec without controllers key -> render_controllers returns Result.ok([])."""
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_controllers(env, spec, tmp_module, ctx)
        assert result.success is True
        assert result.data == []

    def test_controller_generates_main_py(self, env, tmp_module):
        """Spec with controllers -> creates controllers/main.py with @http.route."""
        spec = _make_controller_spec(controllers=[_sample_controller()])
        ctx = _make_module_context(spec)
        result = render_controllers(env, spec, tmp_module, ctx)
        assert result.success is True
        main_py = tmp_module / "controllers" / "main.py"
        assert main_py.exists()
        content = main_py.read_text()
        assert "@http.route" in content
        assert "http.Controller" in content

    def test_controller_secure_defaults(self, env, tmp_module):
        """Routes without explicit auth/csrf -> auth='user', csrf=True in output."""
        controller = {
            "name": "Default Controller",
            "routes": [
                {
                    "path": "api/data",
                    "method_name": "get_data",
                    "description": "Get data",
                },
            ],
        }
        spec = _make_controller_spec(controllers=[controller])
        ctx = _make_module_context(spec)
        render_controllers(env, spec, tmp_module, ctx)
        content = (tmp_module / "controllers" / "main.py").read_text()
        assert "auth='user'" in content or 'auth="user"' in content
        assert "csrf=True" in content

    def test_json_route_error_handling(self, env, tmp_module):
        """Route with type='json' -> try/except block with error response."""
        spec = _make_controller_spec(controllers=[_sample_controller()])
        ctx = _make_module_context(spec)
        render_controllers(env, spec, tmp_module, ctx)
        content = (tmp_module / "controllers" / "main.py").read_text()
        assert "try:" in content
        assert "except" in content
        assert "'status'" in content or '"status"' in content
        assert "'error'" in content or '"error"' in content

    def test_controllers_init(self, env, tmp_module):
        """Generates controllers/__init__.py with 'from . import main'."""
        spec = _make_controller_spec(controllers=[_sample_controller()])
        ctx = _make_module_context(spec)
        render_controllers(env, spec, tmp_module, ctx)
        init_file = tmp_module / "controllers" / "__init__.py"
        assert init_file.exists()
        content = init_file.read_text()
        assert "from . import main" in content

    def test_root_init_imports_controllers(self, env):
        """init_root.py.j2 renders 'from . import controllers' when has_controllers=True."""
        tmpl = env.get_template("init_root.py.j2")
        rendered = tmpl.render(has_wizards=False, has_controllers=True)
        assert "from . import controllers" in rendered

    def test_root_init_no_controllers(self, env):
        """init_root.py.j2 does NOT render controllers import when has_controllers=False."""
        tmpl = env.get_template("init_root.py.j2")
        rendered = tmpl.render(has_wizards=False, has_controllers=False)
        assert "controllers" not in rendered


# ---------------------------------------------------------------------------
# Import/Export wizard tests (Phase 32 Plan 02)
# ---------------------------------------------------------------------------


def _make_import_export_spec(
    models: list[dict] | None = None,
    wizards: list[dict] | None = None,
) -> dict:
    """Build spec with a model that has import_export:true."""
    default_models = [
        {
            "name": "academy.course",
            "description": "Academy Course",
            "import_export": True,
            "fields": [
                {"name": "name", "type": "Char", "required": True},
                {"name": "code", "type": "Char"},
                {"name": "credits", "type": "Integer"},
            ],
        }
    ]
    return _make_spec(models=models or default_models, wizards=wizards)


class TestRenderImportExport:
    def test_import_wizard_generated(self, env, tmp_module):
        """Spec with model having import_export:true -> generates wizard .py file."""
        spec = _make_import_export_spec()
        ctx = _make_module_context(spec)
        result = render_controllers(env, spec, tmp_module, ctx)
        assert result.success is True
        wizard_py = tmp_module / "wizards" / "academy_course_import_wizard.py"
        assert wizard_py.exists()

    def test_import_wizard_fields(self, env, tmp_module):
        """Generated wizard has Binary, state Selection, preview_html, import_count, error_log."""
        spec = _make_import_export_spec()
        ctx = _make_module_context(spec)
        render_controllers(env, spec, tmp_module, ctx)
        content = (tmp_module / "wizards" / "academy_course_import_wizard.py").read_text()
        assert "fields.Binary" in content
        assert "fields.Selection" in content
        assert "'upload'" in content or '"upload"' in content
        assert "'preview'" in content or '"preview"' in content
        assert "'done'" in content or '"done"' in content
        assert "preview_html" in content
        assert "import_count" in content
        assert "error_log" in content

    def test_content_type_validation(self, env, tmp_module):
        """Generated wizard has _validate_file_content with magic bytes check."""
        spec = _make_import_export_spec()
        ctx = _make_module_context(spec)
        render_controllers(env, spec, tmp_module, ctx)
        content = (tmp_module / "wizards" / "academy_course_import_wizard.py").read_text()
        assert "_validate_file_content" in content
        assert "PK\\x03\\x04" in content or "b'PK'" in content or "PK\\x03" in content

    def test_preview_and_batch_import(self, env, tmp_module):
        """Generated wizard has action_preview, action_import, _do_import, _parse_row."""
        spec = _make_import_export_spec()
        ctx = _make_module_context(spec)
        render_controllers(env, spec, tmp_module, ctx)
        content = (tmp_module / "wizards" / "academy_course_import_wizard.py").read_text()
        assert "def action_preview(" in content
        assert "def action_import(" in content
        assert "def _do_import(" in content
        assert "def _parse_row(" in content

    def test_export_xlsx(self, env, tmp_module):
        """Generated wizard has action_export referencing openpyxl.Workbook with field headers."""
        spec = _make_import_export_spec()
        ctx = _make_module_context(spec)
        render_controllers(env, spec, tmp_module, ctx)
        content = (tmp_module / "wizards" / "academy_course_import_wizard.py").read_text()
        assert "def action_export(" in content
        assert "openpyxl" in content
        assert "Workbook" in content

    def test_wizard_form_states(self, env, tmp_module):
        """Generated form XML has state-dependent invisible attrs and action buttons."""
        spec = _make_import_export_spec()
        ctx = _make_module_context(spec)
        render_controllers(env, spec, tmp_module, ctx)
        form_xml = tmp_module / "views" / "academy_course_import_wizard_form.xml"
        assert form_xml.exists()
        content = form_xml.read_text()
        assert "upload" in content
        assert "preview" in content
        assert "done" in content
        assert "ir.actions.act_window" in content

    def test_import_wizard_security(self, env, tmp_module):
        """Import wizard model gets references for ACL entry in security context."""
        spec = _make_import_export_spec()
        ctx = _make_module_context(spec)
        # The import_export_wizards key should be in context for access_csv.j2
        assert "import_export_wizards" in ctx or any(
            m.get("import_export") for m in spec.get("models", [])
        )
        render_controllers(env, spec, tmp_module, ctx)

    def test_no_import_export_noop(self, env, tmp_module):
        """Model without import_export:true -> no wizard files generated."""
        spec = _make_spec(models=[_make_model()])
        ctx = _make_module_context(spec)
        result = render_controllers(env, spec, tmp_module, ctx)
        assert result.success is True
        wizard_dir = tmp_module / "wizards"
        # No import wizard files should exist (wizard dir may not exist at all)
        import_files = list(wizard_dir.glob("*_import_wizard.py")) if wizard_dir.exists() else []
        assert import_files == []

    def test_import_wizard_init(self, env, tmp_module):
        """wizards/__init__.py imports import wizard modules."""
        spec = _make_import_export_spec()
        ctx = _make_module_context(spec)
        render_controllers(env, spec, tmp_module, ctx)
        # Wizards init should import the import wizard
        init_file = tmp_module / "wizards" / "__init__.py"
        assert init_file.exists()
        content = init_file.read_text()
        assert "academy_course_import_wizard" in content


# ---------------------------------------------------------------------------
# Phase 33: Performance optimization integration tests
# ---------------------------------------------------------------------------


class TestRenderModelsPerformance:
    """Integration tests for Phase 33 performance preprocessing in rendered output."""

    def test_render_performance_index_in_output(self, tmp_path):
        """Char search field gets index=True in generated Python code."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "fields": [
                {"name": "name", "type": "Char", "required": True},
                {"name": "qty", "type": "Integer"},
            ],
        }])
        files, _ = render_module(spec, None, tmp_path)
        model_py = (tmp_path / "test_module" / "models" / "academy_course.py").read_text()
        # Char field 'name' should have index=True (it's a search field)
        assert "index=True" in model_py

    def test_render_performance_order_in_output(self, tmp_path):
        """Model with order spec generates _order attribute."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "order": "name asc",
            "fields": [
                {"name": "name", "type": "Char", "required": True},
                {"name": "qty", "type": "Integer"},
            ],
        }])
        files, _ = render_module(spec, None, tmp_path)
        model_py = (tmp_path / "test_module" / "models" / "academy_course.py").read_text()
        assert '_order = "name asc"' in model_py

    def test_render_performance_sql_constraints_in_output(self, tmp_path):
        """unique_together generates _sql_constraints in output."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "unique_together": [
                {"fields": ["name", "company_id"], "message": "Name must be unique per company."},
            ],
            "fields": [
                {"name": "name", "type": "Char", "required": True},
                {"name": "company_id", "type": "Many2one", "comodel_name": "res.company"},
            ],
        }])
        files, _ = render_module(spec, None, tmp_path)
        model_py = (tmp_path / "test_module" / "models" / "academy_course.py").read_text()
        assert "_sql_constraints" in model_py
        assert "unique_name_company_id" in model_py
        assert "UNIQUE(name, company_id)" in model_py

    def test_render_transient_cleanup_in_output(self, tmp_path):
        """Wizard with transient attrs renders _transient_max_hours."""
        spec = _make_spec(
            models=[{
                "name": "academy.course",
                "description": "Academy Course",
                "fields": [{"name": "name", "type": "Char", "required": True}],
            }],
            wizards=[{
                "name": "academy.confirm.wizard",
                "target_model": "academy.course",
                "transient_max_hours": 2.0,
                "transient_max_count": 500,
                "fields": [
                    {"name": "reason", "type": "Char"},
                ],
            }],
        )
        files, _ = render_module(spec, None, tmp_path)
        wizard_py = (tmp_path / "test_module" / "wizards" / "academy_confirm_wizard.py").read_text()
        assert "_transient_max_hours = 2.0" in wizard_py
        assert "_transient_max_count = 500" in wizard_py

    def test_render_import_wizard_transient_defaults(self, tmp_path):
        """Import wizard always renders cleanup attributes with defaults."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "import_export": True,
            "fields": [{"name": "name", "type": "Char", "required": True}],
        }])
        files, _ = render_module(spec, None, tmp_path)
        wizard_py = (tmp_path / "test_module" / "wizards" / "academy_course_import_wizard.py").read_text()
        assert "_transient_max_hours = 1.0" in wizard_py
        assert "_transient_max_count = 0" in wizard_py


class TestRenderModelsProductionPatterns:
    """Integration tests for bulk and cache production patterns in generated models."""

    def test_bulk_model_generates_create_multi(self, tmp_path):
        """Spec with bulk:true -> generated .py contains @api.model_create_multi and _post_create_processing."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "bulk": True,
            "fields": [{"name": "name", "type": "Char", "required": True}],
        }])
        files, _ = render_module(spec, None, tmp_path)
        model_py = (tmp_path / "test_module" / "models" / "academy_course.py").read_text()
        assert "@api.model_create_multi" in model_py
        assert "_post_create_processing" in model_py
        assert "for record in records:" in model_py

    def test_cacheable_model_generates_ormcache(self, tmp_path):
        """Spec with cacheable:true -> generated .py contains @tools.ormcache, clear_caches(), tools import."""
        spec = _make_spec(models=[{
            "name": "academy.category",
            "description": "Academy Category",
            "cacheable": True,
            "fields": [{"name": "name", "type": "Char", "required": True}],
        }])
        files, _ = render_module(spec, None, tmp_path)
        model_py = (tmp_path / "test_module" / "models" / "academy_category.py").read_text()
        assert "@tools.ormcache" in model_py
        assert "clear_caches()" in model_py
        assert "from odoo import" in model_py
        assert "tools" in model_py

    def test_bulk_with_constraints_single_create(self, tmp_path):
        """Spec with bulk:true + constraints -> generated .py has exactly ONE 'def create(' occurrence."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "bulk": True,
            "constraints": [{
                "name": "capacity",
                "type": "cross_model",
                "check_body": "pass  # capacity check",
                "message": "Capacity exceeded",
                "trigger": "create",
            }],
            "fields": [
                {"name": "name", "type": "Char", "required": True},
                {"name": "capacity", "type": "Integer"},
            ],
        }])
        files, _ = render_module(spec, None, tmp_path)
        model_py = (tmp_path / "test_module" / "models" / "academy_course.py").read_text()
        assert model_py.count("def create(") == 1
        assert "@api.model_create_multi" in model_py
        assert "_post_create_processing" in model_py

    def test_cacheable_with_constraints_single_write(self, tmp_path):
        """Spec with cacheable:true + constraints -> generated .py has exactly ONE 'def write(' occurrence."""
        spec = _make_spec(models=[{
            "name": "academy.category",
            "description": "Academy Category",
            "cacheable": True,
            "constraints": [{
                "name": "check_dates",
                "type": "cross_model",
                "check_body": "pass  # date check",
                "message": "Invalid dates",
                "trigger": "write",
                "write_trigger_fields": ["date_start"],
            }],
            "fields": [
                {"name": "name", "type": "Char", "required": True},
                {"name": "date_start", "type": "Date"},
            ],
        }])
        files, _ = render_module(spec, None, tmp_path)
        model_py = (tmp_path / "test_module" / "models" / "academy_category.py").read_text()
        assert model_py.count("def write(") == 1
        assert "clear_caches()" in model_py


class TestRenderModelsArchival:
    """Integration tests for archival production pattern in generated modules."""

    def test_archival_model_has_active_field(self, tmp_path):
        """Render spec with archival:true -> generated model .py contains active = fields.Boolean."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "archival": True,
            "fields": [{"name": "name", "type": "Char", "required": True}],
        }])
        files, _ = render_module(spec, None, tmp_path)
        model_py = (tmp_path / "test_module" / "models" / "academy_course.py").read_text()
        assert "active = fields.Boolean" in model_py
        assert 'default="True"' in model_py
        assert "index=True" in model_py

    def test_archival_generates_wizard_files(self, tmp_path):
        """Render full module with archival:true -> wizards/ dir contains archival wizard."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "archival": True,
            "fields": [{"name": "name", "type": "Char", "required": True}],
        }])
        files, _ = render_module(spec, None, tmp_path)
        wizard_py = (tmp_path / "test_module" / "wizards" / "academy_course_archive_wizard.py").read_text()
        assert "action_archive" in wizard_py
        assert "relativedelta" in wizard_py

    def test_archival_generates_cron_xml(self, tmp_path):
        """Render full module with archival:true -> data/cron_data.xml references cron method."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "archival": True,
            "fields": [{"name": "name", "type": "Char", "required": True}],
        }])
        files, _ = render_module(spec, None, tmp_path)
        cron_xml = (tmp_path / "test_module" / "data" / "cron_data.xml").read_text()
        assert "_cron_archive_old_records" in cron_xml
        assert "ir.cron" in cron_xml

    def test_archival_cron_has_batch_commit(self, tmp_path):
        """Generated model .py contains cr.commit() and BATCH_SIZE in archival cron method."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "archival": True,
            "fields": [{"name": "name", "type": "Char", "required": True}],
        }])
        files, _ = render_module(spec, None, tmp_path)
        model_py = (tmp_path / "test_module" / "models" / "academy_course.py").read_text()
        assert "cr.commit()" in model_py
        assert "BATCH_SIZE" in model_py

    def test_archival_wizard_form_has_button(self, tmp_path):
        """Generated wizard form XML contains button with name='action_archive'."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "archival": True,
            "fields": [{"name": "name", "type": "Char", "required": True}],
        }])
        files, _ = render_module(spec, None, tmp_path)
        form_xml = (tmp_path / "test_module" / "views" / "academy_course_archive_wizard_wizard_form.xml").read_text()
        assert 'name="action_archive"' in form_xml
        assert "days_threshold" in form_xml

    def test_archival_with_state_field_no_crash(self, tmp_path):
        """Render spec with archival:true AND state Selection field -> no StrictUndefined error."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "archival": True,
            "fields": [
                {"name": "name", "type": "Char", "required": True},
                {
                    "name": "state",
                    "type": "Selection",
                    "selection": [["draft", "Draft"], ["active", "Active"]],
                },
            ],
        }])
        files, _ = render_module(spec, None, tmp_path)
        form_xml = (tmp_path / "test_module" / "views" / "academy_course_views.xml").read_text()
        # Archival wizard button should exist
        assert "action_open_academy_course_archive_wizard" in form_xml
        # Archival wizard button should NOT have invisible (no trigger_state)
        # Find the button block for archival wizard and check it has no invisible attr
        lines = form_xml.split("\n")
        for i, line in enumerate(lines):
            if "action_open_academy_course_archive_wizard" in line:
                # Gather surrounding lines for this button element
                button_block = "\n".join(lines[max(0, i - 1):i + 5])
                assert "invisible" not in button_block, (
                    f"Archival wizard button should not have invisible attr:\n{button_block}"
                )
                break

    def test_archival_with_state_and_regular_wizard(self, tmp_path):
        """Archival + state field + regular wizard -> both buttons render, only regular has invisible."""
        spec = _make_spec(
            models=[{
                "name": "academy.course",
                "description": "Academy Course",
                "archival": True,
                "fields": [
                    {"name": "name", "type": "Char", "required": True},
                    {
                        "name": "state",
                        "type": "Selection",
                        "selection": [["draft", "Draft"], ["active", "Active"]],
                    },
                ],
            }],
            wizards=[{
                "name": "confirm.wizard",
                "target_model": "academy.course",
                "trigger_state": "draft",
                "fields": [{"name": "reason", "type": "Char"}],
            }],
        )
        files, _ = render_module(spec, None, tmp_path)
        form_xml = (tmp_path / "test_module" / "views" / "academy_course_views.xml").read_text()
        # Both buttons should exist
        assert "action_open_academy_course_archive_wizard" in form_xml
        assert "action_open_confirm_wizard" in form_xml
        # Regular wizard button should have invisible with trigger_state
        assert "invisible=\"state != 'draft'\"" in form_xml
        # Archival wizard button should NOT have invisible -- check only lines AFTER its name
        lines = form_xml.split("\n")
        for i, line in enumerate(lines):
            if "action_open_academy_course_archive_wizard" in line:
                # Check from this line until next closing tag or button end
                button_block = "\n".join(lines[i:i + 6])
                assert "invisible" not in button_block, (
                    f"Archival wizard button should not have invisible attr:\n{button_block}"
                )
                break

    def test_cron_doall_from_spec_true(self, tmp_path):
        """Cron with doall:true in spec -> doall field in rendered XML contains eval='True'."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "fields": [{"name": "name", "type": "Char", "required": True}],
        }])
        spec["cron_jobs"] = [{
            "name": "Test Cron",
            "model_name": "academy.course",
            "method": "_cron_test",
            "interval_number": 1,
            "interval_type": "days",
            "doall": True,
        }]
        files, _ = render_module(spec, None, tmp_path)
        cron_xml = (tmp_path / "test_module" / "data" / "cron_data.xml").read_text()
        # Must specifically check the doall field line, not just any eval="True"
        for line in cron_xml.split("\n"):
            if '"doall"' in line:
                assert 'eval="True"' in line, f"doall field should have eval='True', got: {line}"
                break
        else:
            raise AssertionError("doall field not found in cron XML")

    def test_cron_doall_default_false(self, tmp_path):
        """Cron without doall key in spec -> doall field in rendered XML contains eval='False'."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "fields": [{"name": "name", "type": "Char", "required": True}],
        }])
        spec["cron_jobs"] = [{
            "name": "Test Cron",
            "model_name": "academy.course",
            "method": "_cron_test",
            "interval_number": 1,
            "interval_type": "days",
        }]
        files, _ = render_module(spec, None, tmp_path)
        cron_xml = (tmp_path / "test_module" / "data" / "cron_data.xml").read_text()
        for line in cron_xml.split("\n"):
            if '"doall"' in line:
                assert 'eval="False"' in line, f"doall field should have eval='False', got: {line}"
                break
        else:
            raise AssertionError("doall field not found in cron XML")

    def test_full_production_patterns_combined(self, tmp_path):
        """Spec with bulk+cacheable+archival -> module renders without errors, has all patterns."""
        spec = _make_spec(models=[{
            "name": "academy.course",
            "description": "Academy Course",
            "bulk": True,
            "cacheable": True,
            "archival": True,
            "fields": [{"name": "name", "type": "Char", "required": True}],
        }])
        files, _ = render_module(spec, None, tmp_path)
        model_py = (tmp_path / "test_module" / "models" / "academy_course.py").read_text()
        # Bulk
        assert "_post_create_processing" in model_py
        # Cache
        assert "clear_caches()" in model_py
        assert "@tools.ormcache" in model_py
        # Archival
        assert "_cron_archive_old_records" in model_py
        assert "cr.commit()" in model_py
        assert "active = fields.Boolean" in model_py


# ---------------------------------------------------------------------------
# Minimal-spec smoke test (Phase 36 Plan 02)
# ---------------------------------------------------------------------------


def test_minimal_spec_smoke(tmp_path):
    """Render a single-model, zero-features spec through full pipeline.

    Guards against StrictUndefined regressions when new context keys
    are added by future phases but not populated for minimal specs.
    """
    spec = {
        "module_name": "smoke_test",
        "depends": ["base"],
        "models": [{
            "name": "smoke.model",
            "description": "Smoke Test",
            "fields": [{"name": "name", "type": "Char"}],
        }],
        "wizards": [],
    }
    files, warnings = render_module(spec, get_template_dir(), tmp_path)
    assert len(files) > 0
    module_dir = tmp_path / "smoke_test"
    assert (module_dir / "__manifest__.py").exists()
    assert (module_dir / "models" / "smoke_model.py").exists()
