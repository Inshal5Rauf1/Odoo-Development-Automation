"""Tests for renderer.py - Phase 5 extensions.

Tests for _build_model_context() new context keys and render_module() extended capabilities.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from odoo_gen_utils.renderer import (
    MONETARY_FIELD_PATTERNS,
    _build_model_context,
    _is_monetary_field,
    get_template_dir,
    render_module,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEQUENCE_FIELD_NAMES = {"reference", "ref", "number", "code", "sequence"}


def _make_spec(
    models: list[dict] | None = None,
    wizards: list[dict] | None = None,
) -> dict:
    """Helper to construct a minimal spec dict for testing."""
    return {
        "module_name": "test_module",
        "depends": ["base"],
        "models": models or [],
        "wizards": wizards or [],
    }


# ---------------------------------------------------------------------------
# _build_model_context: new keys
# ---------------------------------------------------------------------------


class TestBuildModelContextComputedFields:
    def test_computed_fields_single_compute_field(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "qty", "type": "Integer"},
                {"name": "total", "type": "Float", "compute": "_compute_total", "depends": ["qty"]},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert "computed_fields" in ctx
        assert len(ctx["computed_fields"]) == 1
        assert ctx["computed_fields"][0]["name"] == "total"

    def test_computed_fields_empty_when_no_compute(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "name", "type": "Char"},
                {"name": "qty", "type": "Integer"},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["computed_fields"] == []

    def test_has_computed_true_when_computed_fields_present(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "total", "type": "Float", "compute": "_compute_total", "depends": ["qty"]},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["has_computed"] is True

    def test_has_computed_false_when_no_computed_fields(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "name", "type": "Char"},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["has_computed"] is False


class TestBuildModelContextOnchangeFields:
    def test_onchange_fields_detected(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "name", "type": "Char"},
                {"name": "partner_id", "type": "Many2one", "comodel_name": "res.partner", "onchange": True},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert "onchange_fields" in ctx
        assert len(ctx["onchange_fields"]) == 1
        assert ctx["onchange_fields"][0]["name"] == "partner_id"

    def test_onchange_fields_empty_when_none(self):
        model = {
            "name": "test.model",
            "fields": [{"name": "name", "type": "Char"}],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["onchange_fields"] == []


class TestBuildModelContextConstrainedFields:
    def test_constrained_fields_detected(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "date_start", "type": "Date", "constrains": ["date_start", "date_end"]},
                {"name": "date_end", "type": "Date"},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert "constrained_fields" in ctx
        assert len(ctx["constrained_fields"]) == 1
        assert ctx["constrained_fields"][0]["name"] == "date_start"

    def test_constrained_fields_empty_when_none(self):
        model = {
            "name": "test.model",
            "fields": [{"name": "name", "type": "Char"}],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["constrained_fields"] == []


class TestBuildModelContextSequenceFields:
    def test_sequence_field_reference_required_detected(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "reference", "type": "Char", "required": True},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert "sequence_fields" in ctx
        assert len(ctx["sequence_fields"]) == 1
        assert ctx["sequence_fields"][0]["name"] == "reference"

    @pytest.mark.parametrize("field_name", list(SEQUENCE_FIELD_NAMES))
    def test_all_sequence_field_names_detected(self, field_name):
        model = {
            "name": "test.model",
            "fields": [
                {"name": field_name, "type": "Char", "required": True},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert len(ctx["sequence_fields"]) == 1

    def test_description_char_required_not_in_sequence_fields(self):
        """A Char field named 'description' required=True must NOT be in sequence_fields."""
        model = {
            "name": "test.model",
            "fields": [
                {"name": "description", "type": "Char", "required": True},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["sequence_fields"] == []

    def test_reference_not_required_not_in_sequence_fields(self):
        """A Char field named 'reference' without required=True must NOT be in sequence_fields."""
        model = {
            "name": "test.model",
            "fields": [
                {"name": "reference", "type": "Char", "required": False},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["sequence_fields"] == []

    def test_reference_integer_type_not_in_sequence_fields(self):
        """An Integer field named 'reference' must NOT be in sequence_fields."""
        model = {
            "name": "test.model",
            "fields": [
                {"name": "reference", "type": "Integer", "required": True},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["sequence_fields"] == []

    def test_has_sequence_fields_true(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "reference", "type": "Char", "required": True},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["has_sequence_fields"] is True

    def test_has_sequence_fields_false(self):
        model = {
            "name": "test.model",
            "fields": [{"name": "name", "type": "Char"}],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["has_sequence_fields"] is False

    def test_sequence_field_names_list_in_context(self):
        """sequence_field_names must be a list in context (used by template)."""
        model = {
            "name": "test.model",
            "fields": [{"name": "name", "type": "Char"}],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert "sequence_field_names" in ctx
        assert isinstance(ctx["sequence_field_names"], list)


class TestBuildModelContextStateField:
    def test_state_field_detected(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "state", "type": "Selection", "selection": [["draft", "Draft"], ["done", "Done"]]},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["state_field"] is not None
        assert ctx["state_field"]["name"] == "state"

    def test_status_field_detected(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "status", "type": "Selection", "selection": [["active", "Active"]]},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["state_field"] is not None
        assert ctx["state_field"]["name"] == "status"

    def test_no_state_field_returns_none(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "name", "type": "Char"},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["state_field"] is None

    def test_state_char_field_not_detected_as_state_field(self):
        """A field named 'state' but type 'Char' should NOT be the state_field."""
        model = {
            "name": "test.model",
            "fields": [
                {"name": "state", "type": "Char"},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["state_field"] is None


class TestBuildModelContextWizards:
    def test_wizards_from_spec(self):
        wizards = [
            {"name": "confirm.wizard", "target_model": "test.model", "trigger_state": "draft", "fields": []}
        ]
        model = {"name": "test.model", "fields": [{"name": "name", "type": "Char"}]}
        spec = _make_spec(models=[model], wizards=wizards)
        ctx = _build_model_context(spec, model)
        assert "wizards" in ctx
        assert len(ctx["wizards"]) == 1
        assert ctx["wizards"][0]["name"] == "confirm.wizard"

    def test_wizards_empty_list_when_no_wizards(self):
        model = {"name": "test.model", "fields": [{"name": "name", "type": "Char"}]}
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["wizards"] == []


# ---------------------------------------------------------------------------
# render_module: file generation
# ---------------------------------------------------------------------------


class TestRenderModuleWizards:
    def test_wizards_spec_generates_wizards_init(self):
        spec = {
            "module_name": "test_wiz",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.order",
                    "description": "Test Order",
                    "fields": [
                        {"name": "name", "type": "Char", "required": True},
                        {
                            "name": "state",
                            "type": "Selection",
                            "selection": [["draft", "Draft"], ["done", "Done"]],
                            "default": "draft",
                        },
                    ],
                }
            ],
            "wizards": [
                {
                    "name": "test.wizard",
                    "target_model": "test.order",
                    "trigger_state": "draft",
                    "fields": [{"name": "notes", "type": "Text", "string": "Notes"}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            names = [Path(f).name for f in files]
            assert "__init__.py" in names  # wizards/__init__.py is one of the __init__.py files

            # Check full relative paths for wizard files
            relative_paths = [
                str(Path(f).relative_to(Path(d) / "test_wiz")) for f in files
            ]
            assert any("wizards" in p and "__init__.py" in p for p in relative_paths), (
                f"Missing wizards/__init__.py in {relative_paths}"
            )

    def test_no_wizards_spec_produces_no_wizard_files(self):
        spec = {
            "module_name": "test_nowiz",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.order",
                    "description": "Test Order",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            relative_paths = [
                str(Path(f).relative_to(Path(d) / "test_nowiz")) for f in files
            ]
            assert not any("wizards" in p for p in relative_paths), (
                f"Found unexpected wizard files: {relative_paths}"
            )

    def test_wizard_py_file_created(self):
        spec = {
            "module_name": "test_wiz2",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.order",
                    "description": "Test Order",
                    "fields": [{"name": "name", "type": "Char"}],
                }
            ],
            "wizards": [
                {
                    "name": "confirm.wizard",
                    "target_model": "test.order",
                    "trigger_state": "draft",
                    "fields": [{"name": "notes", "type": "Text", "string": "Notes"}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            relative_paths = [
                str(Path(f).relative_to(Path(d) / "test_wiz2")) for f in files
            ]
            assert any("confirm_wizard.py" in p for p in relative_paths), (
                f"Missing wizards/confirm_wizard.py in {relative_paths}"
            )

    def test_wizard_form_xml_created(self):
        spec = {
            "module_name": "test_wiz3",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.order",
                    "description": "Test Order",
                    "fields": [{"name": "name", "type": "Char"}],
                }
            ],
            "wizards": [
                {
                    "name": "confirm.wizard",
                    "target_model": "test.order",
                    "trigger_state": "draft",
                    "fields": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            names = [Path(f).name for f in files]
            assert "confirm_wizard_wizard_form.xml" in names or any(
                "wizard_form" in n for n in names
            ), f"Missing wizard form xml in {names}"


class TestRenderModuleSequences:
    def test_sequence_field_generates_sequences_xml(self):
        spec = {
            "module_name": "test_seq",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.order",
                    "description": "Test Order",
                    "fields": [
                        {"name": "name", "type": "Char"},
                        {"name": "reference", "type": "Char", "required": True},
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            names = [Path(f).name for f in files]
            assert "sequences.xml" in names, f"Missing sequences.xml. Got: {names}"

    def test_no_sequence_field_no_sequences_xml(self):
        spec = {
            "module_name": "test_noseq",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.order",
                    "description": "Test Order",
                    "fields": [
                        {"name": "name", "type": "Char"},
                        {"name": "description", "type": "Char", "required": True},
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            names = [Path(f).name for f in files]
            assert "sequences.xml" not in names, f"Unexpected sequences.xml in {names}"


class TestRenderModuleDataXml:
    def test_data_xml_always_created(self):
        spec = {
            "module_name": "test_data",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.item",
                    "description": "Test Item",
                    "fields": [{"name": "name", "type": "Char"}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            names = [Path(f).name for f in files]
            assert "data.xml" in names, f"Missing data.xml. Got: {names}"

    def test_data_xml_created_even_with_sequences(self):
        spec = {
            "module_name": "test_data2",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.item",
                    "description": "Test Item",
                    "fields": [
                        {"name": "name", "type": "Char"},
                        {"name": "reference", "type": "Char", "required": True},
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            names = [Path(f).name for f in files]
            assert "data.xml" in names, f"Missing data.xml. Got: {names}"
            assert "sequences.xml" in names, f"Missing sequences.xml. Got: {names}"


# ---------------------------------------------------------------------------
# Phase 6: _build_model_context -- has_company_field detection
# ---------------------------------------------------------------------------


_COMPANY_SPEC = {
    "module_name": "test_company",
    "depends": ["base"],
    "models": [
        {
            "name": "test.order",
            "description": "Test Order",
            "fields": [
                {"name": "name", "type": "Char", "required": True},
                {"name": "company_id", "type": "Many2one", "comodel_name": "res.company"},
            ],
        }
    ],
}


class TestBuildModelContextCompanyField:
    def test_company_field_many2one_sets_has_company_field_true(self):
        """Model with company_id Many2one → has_company_field is True."""
        model = {
            "name": "test.order",
            "fields": [
                {"name": "name", "type": "Char", "required": True},
                {"name": "company_id", "type": "Many2one", "comodel_name": "res.company"},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["has_company_field"] is True

    def test_no_company_field_sets_has_company_field_false(self):
        """Model without company_id field → has_company_field is False."""
        model = {
            "name": "test.order",
            "fields": [
                {"name": "name", "type": "Char"},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["has_company_field"] is False

    def test_company_field_wrong_type_sets_false(self):
        """company_id field with type Char (not Many2one) → has_company_field is False."""
        model = {
            "name": "test.order",
            "fields": [
                {"name": "company_id", "type": "Char"},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["has_company_field"] is False

    def test_company_field_different_name_sets_false(self):
        """Many2one field named 'company' (not 'company_id') → has_company_field is False."""
        model = {
            "name": "test.order",
            "fields": [
                {"name": "company", "type": "Many2one", "comodel_name": "res.company"},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["has_company_field"] is False


# ---------------------------------------------------------------------------
# Phase 6: render_module -- record_rules.xml generation
# ---------------------------------------------------------------------------


class TestRenderModuleRecordRules:
    def test_company_field_model_generates_record_rules_xml(self):
        """spec with Many2one company_id → 'record_rules.xml' appears in generated file names."""
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(_COMPANY_SPEC, get_template_dir(), Path(d))
            names = [Path(f).name for f in files]
            assert "record_rules.xml" in names, (
                f"Expected record_rules.xml in generated files. Got: {names}"
            )

    def test_no_company_field_no_record_rules_xml(self):
        """spec without company_id → 'record_rules.xml' NOT in generated file names."""
        spec = {
            "module_name": "test_nocompany",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.order",
                    "description": "Test Order",
                    "fields": [{"name": "name", "type": "Char"}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            names = [Path(f).name for f in files]
            assert "record_rules.xml" not in names, (
                f"Unexpected record_rules.xml in files without company_id: {names}"
            )

    def test_record_rules_xml_contains_company_ids_domain(self):
        """Content of generated record_rules.xml contains 'company_ids' OCA shorthand."""
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(_COMPANY_SPEC, get_template_dir(), Path(d))
            record_rules_file = next(
                (f for f in files if Path(f).name == "record_rules.xml"), None
            )
            assert record_rules_file is not None, "record_rules.xml was not generated"
            content = Path(record_rules_file).read_text(encoding="utf-8")
            assert "company_ids" in content, (
                f"'company_ids' domain not found in record_rules.xml. Content:\n{content}"
            )

    def test_manifest_includes_record_rules_when_company_field(self):
        """Generated __manifest__.py contains 'security/record_rules.xml' when company_id model present."""
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(_COMPANY_SPEC, get_template_dir(), Path(d))
            manifest_file = next(
                (f for f in files if Path(f).name == "__manifest__.py"), None
            )
            assert manifest_file is not None, "__manifest__.py was not generated"
            content = Path(manifest_file).read_text(encoding="utf-8")
            assert "security/record_rules.xml" in content, (
                f"'security/record_rules.xml' not found in __manifest__.py. Content:\n{content}"
            )


# ---------------------------------------------------------------------------
# Phase 9: Versioned template rendering
# ---------------------------------------------------------------------------


def _make_versioned_spec(
    odoo_version: str = "17.0",
    models: list[dict] | None = None,
    depends: list[str] | None = None,
) -> dict:
    """Helper to construct a spec with odoo_version for version testing."""
    return {
        "module_name": "test_ver",
        "depends": depends or ["base"],
        "odoo_version": odoo_version,
        "models": models or [
            {
                "name": "test.item",
                "description": "Test Item",
                "fields": [
                    {"name": "name", "type": "Char", "required": True},
                    {"name": "description", "type": "Text"},
                ],
            }
        ],
    }


class TestVersionedTemplates:
    """Tests that version-specific templates produce correct output."""

    def test_17_gets_tree_tag(self):
        """render_module with odoo_version=17.0 produces XML containing '<tree'."""
        spec = _make_versioned_spec("17.0")
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            views_file = next(
                (f for f in files if "test_item_views.xml" in str(f)), None
            )
            assert views_file is not None
            content = Path(views_file).read_text(encoding="utf-8")
            assert "<tree" in content, f"Expected <tree in 17.0 views. Got:\n{content}"
            assert "<list" not in content, f"Unexpected <list in 17.0 views. Got:\n{content}"

    def test_18_gets_list_tag(self):
        """render_module with odoo_version=18.0 produces XML containing '<list'."""
        spec = _make_versioned_spec("18.0")
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            views_file = next(
                (f for f in files if "test_item_views.xml" in str(f)), None
            )
            assert views_file is not None
            content = Path(views_file).read_text(encoding="utf-8")
            assert "<list" in content, f"Expected <list in 18.0 views. Got:\n{content}"
            assert "<tree" not in content, f"Unexpected <tree in 18.0 views. Got:\n{content}"

    def test_18_action_uses_list_viewmode(self):
        """18.0 action.xml contains view_mode with 'list,form'."""
        spec = _make_versioned_spec("18.0")
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            action_file = next(
                (f for f in files if "test_item_action.xml" in str(f)), None
            )
            assert action_file is not None
            content = Path(action_file).read_text(encoding="utf-8")
            assert "list,form" in content, f"Expected 'list,form' in 18.0 action. Got:\n{content}"

    def test_17_action_uses_tree_viewmode(self):
        """17.0 action.xml contains view_mode with 'tree,form'."""
        spec = _make_versioned_spec("17.0")
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            action_file = next(
                (f for f in files if "test_item_action.xml" in str(f)), None
            )
            assert action_file is not None
            content = Path(action_file).read_text(encoding="utf-8")
            assert "tree,form" in content, f"Expected 'tree,form' in 17.0 action. Got:\n{content}"

    def test_18_chatter_shorthand(self):
        """18.0 form view uses '<chatter/>' not 'oe_chatter'."""
        spec = _make_versioned_spec("18.0", depends=["base", "mail"])
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            views_file = next(
                (f for f in files if "test_item_views.xml" in str(f)), None
            )
            assert views_file is not None
            content = Path(views_file).read_text(encoding="utf-8")
            assert "<chatter/>" in content, f"Expected <chatter/> in 18.0 form. Got:\n{content}"
            assert "oe_chatter" not in content, f"Unexpected oe_chatter in 18.0 form. Got:\n{content}"

    def test_shared_template_fallback(self):
        """Shared templates (manifest, menu, etc.) resolve correctly for both versions."""
        for version in ("17.0", "18.0"):
            spec = _make_versioned_spec(version)
            with tempfile.TemporaryDirectory() as d:
                files, _ = render_module(spec, get_template_dir(), Path(d))
                names = [Path(f).name for f in files]
                assert "__manifest__.py" in names, f"Missing manifest for {version}"
                assert "menu.xml" in names, f"Missing menu for {version}"
                assert "README.rst" in names, f"Missing README for {version}"


class TestVersionConfig:
    """Tests that odoo_version flows through spec correctly."""

    def test_default_version_is_17(self):
        """render_module with no odoo_version in spec defaults to 17.0."""
        spec = {
            "module_name": "test_default",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.item",
                    "description": "Test Item",
                    "fields": [{"name": "name", "type": "Char"}],
                }
            ],
        }
        # No odoo_version key at all
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            views_file = next(
                (f for f in files if "test_item_views.xml" in str(f)), None
            )
            assert views_file is not None
            content = Path(views_file).read_text(encoding="utf-8")
            assert "<tree" in content, f"Default should produce 17.0 tree tags. Got:\n{content}"

    def test_version_from_spec(self):
        """render_module reads odoo_version from spec dict."""
        spec = _make_versioned_spec("18.0")
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            action_file = next(
                (f for f in files if "test_item_action.xml" in str(f)), None
            )
            assert action_file is not None
            content = Path(action_file).read_text(encoding="utf-8")
            assert "list,form" in content, f"Expected 18.0 view_mode. Got:\n{content}"


class TestRenderModule18:
    """Integration test: full 18.0 module renders without errors."""

    def test_full_18_module_renders(self):
        """Complete render_module with odoo_version=18.0 produces all expected files."""
        spec = {
            "module_name": "test_18_full",
            "depends": ["base", "mail"],
            "odoo_version": "18.0",
            "models": [
                {
                    "name": "project.task",
                    "description": "Project Task",
                    "fields": [
                        {"name": "name", "type": "Char", "required": True},
                        {"name": "description", "type": "Text"},
                        {
                            "name": "state",
                            "type": "Selection",
                            "selection": [["draft", "Draft"], ["done", "Done"]],
                            "default": "draft",
                        },
                        {"name": "partner_id", "type": "Many2one", "comodel_name": "res.partner"},
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            names = [Path(f).name for f in files]
            # All expected file types present
            assert "__manifest__.py" in names
            assert "__init__.py" in names
            assert "project_task.py" in names
            assert "project_task_views.xml" in names
            assert "project_task_action.xml" in names
            assert "menu.xml" in names
            assert "security.xml" in names
            assert "ir.model.access.csv" in names
            assert "README.rst" in names
            # Verify 18.0 markers
            views_file = next(f for f in files if "project_task_views.xml" in str(f))
            content = Path(views_file).read_text(encoding="utf-8")
            assert "<list" in content
            assert "<chatter/>" in content
            assert "<tree" not in content


# ---------------------------------------------------------------------------
# Phase 12: _build_model_context -- inherit_list (TMPL-01)
# ---------------------------------------------------------------------------


class TestBuildModelContextInheritList:
    """Tests that _build_model_context builds inherit_list from mail dependency + explicit inherit."""

    def test_inherit_list_with_mail_dependency(self):
        """spec with depends=["base", "mail"], model with no explicit inherit -> inherit_list has mail mixins."""
        model = {
            "name": "test.model",
            "fields": [{"name": "name", "type": "Char"}],
        }
        spec = _make_spec(models=[model])
        spec["depends"] = ["base", "mail"]
        ctx = _build_model_context(spec, model)
        assert ctx["inherit_list"] == ["mail.thread", "mail.activity.mixin"]

    def test_inherit_list_merges_explicit_inherit(self):
        """spec with mail + model with inherit="portal.mixin" -> inherit_list has all 3."""
        model = {
            "name": "test.model",
            "inherit": "portal.mixin",
            "fields": [{"name": "name", "type": "Char"}],
        }
        spec = _make_spec(models=[model])
        spec["depends"] = ["base", "mail"]
        ctx = _build_model_context(spec, model)
        assert "portal.mixin" in ctx["inherit_list"]
        assert "mail.thread" in ctx["inherit_list"]
        assert "mail.activity.mixin" in ctx["inherit_list"]
        assert len(ctx["inherit_list"]) == 3

    def test_inherit_list_no_mail_empty(self):
        """spec with depends=["base"], model with no inherit -> inherit_list is empty."""
        model = {
            "name": "test.model",
            "fields": [{"name": "name", "type": "Char"}],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["inherit_list"] == []

    def test_inherit_list_no_mail_explicit_inherit(self):
        """spec with depends=["base"], model with inherit="portal.mixin" -> inherit_list has only portal.mixin."""
        model = {
            "name": "test.model",
            "inherit": "portal.mixin",
            "fields": [{"name": "name", "type": "Char"}],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["inherit_list"] == ["portal.mixin"]

    def test_inherit_list_mail_no_duplicates(self):
        """spec with mail + model with inherit="mail.thread" -> mail.thread appears exactly once."""
        model = {
            "name": "test.model",
            "inherit": "mail.thread",
            "fields": [{"name": "name", "type": "Char"}],
        }
        spec = _make_spec(models=[model])
        spec["depends"] = ["base", "mail"]
        ctx = _build_model_context(spec, model)
        assert ctx["inherit_list"].count("mail.thread") == 1
        assert "mail.activity.mixin" in ctx["inherit_list"]

    # Phase 21: Smart mail.thread injection -- skip cases (TMPL-01)

    def test_inherit_list_line_item_no_mail_thread(self):
        """Line item model (required Many2one _id to in-module model) should NOT get mail.thread."""
        parent_model = {
            "name": "sale.order",
            "fields": [{"name": "name", "type": "Char"}],
        }
        line_model = {
            "name": "sale.order.line",
            "fields": [
                {"name": "name", "type": "Char"},
                {
                    "name": "order_id",
                    "type": "Many2one",
                    "comodel_name": "sale.order",
                    "required": True,
                },
            ],
        }
        spec = _make_spec(models=[parent_model, line_model])
        spec["depends"] = ["base", "mail"]
        ctx = _build_model_context(spec, line_model)
        assert ctx["inherit_list"] == [], (
            f"Line item should NOT get mail.thread, got {ctx['inherit_list']}"
        )

    def test_inherit_list_line_item_with_chatter_override(self):
        """Line item with explicit chatter=True should still get mail.thread."""
        parent_model = {
            "name": "sale.order",
            "fields": [{"name": "name", "type": "Char"}],
        }
        line_model = {
            "name": "sale.order.line",
            "chatter": True,
            "fields": [
                {"name": "name", "type": "Char"},
                {
                    "name": "order_id",
                    "type": "Many2one",
                    "comodel_name": "sale.order",
                    "required": True,
                },
            ],
        }
        spec = _make_spec(models=[parent_model, line_model])
        spec["depends"] = ["base", "mail"]
        ctx = _build_model_context(spec, line_model)
        assert "mail.thread" in ctx["inherit_list"], (
            "Line item with chatter=True should get mail.thread"
        )
        assert "mail.activity.mixin" in ctx["inherit_list"]

    def test_inherit_list_chatter_false_skips_mail(self):
        """Top-level model with chatter=False should NOT get mail.thread even with mail in depends."""
        model = {
            "name": "test.config",
            "chatter": False,
            "fields": [{"name": "name", "type": "Char"}],
        }
        spec = _make_spec(models=[model])
        spec["depends"] = ["base", "mail"]
        ctx = _build_model_context(spec, model)
        assert ctx["inherit_list"] == [], (
            f"chatter=False model should NOT get mail.thread, got {ctx['inherit_list']}"
        )

    def test_inherit_list_parent_already_has_mail(self):
        """Model extending in-module parent that gets mail.thread should NOT duplicate mail.thread."""
        parent_model = {
            "name": "base.record",
            "fields": [{"name": "name", "type": "Char"}],
        }
        child_model = {
            "name": "child.record",
            "inherit": "base.record",
            "fields": [{"name": "extra", "type": "Char"}],
        }
        spec = _make_spec(models=[parent_model, child_model])
        spec["depends"] = ["base", "mail"]
        # Parent gets mail.thread automatically. Child inherits from parent,
        # so it should NOT inject mail.thread again.
        ctx = _build_model_context(spec, child_model)
        assert "mail.thread" not in ctx["inherit_list"], (
            "Child of in-module parent should NOT duplicate mail.thread"
        )
        # But explicit inherit should still be there
        assert "base.record" in ctx["inherit_list"]

    def test_inherit_list_top_level_still_gets_mail(self):
        """Top-level model with mail in depends still gets mail.thread (existing behavior preserved)."""
        model = {
            "name": "project.task",
            "fields": [{"name": "name", "type": "Char"}],
        }
        spec = _make_spec(models=[model])
        spec["depends"] = ["base", "mail"]
        ctx = _build_model_context(spec, model)
        assert "mail.thread" in ctx["inherit_list"]
        assert "mail.activity.mixin" in ctx["inherit_list"]

    def test_inherit_list_line_item_detection_non_required_m2o(self):
        """Many2one that is NOT required should not trigger line item detection."""
        parent_model = {
            "name": "sale.order",
            "fields": [{"name": "name", "type": "Char"}],
        }
        model = {
            "name": "sale.order.line",
            "fields": [
                {"name": "name", "type": "Char"},
                {
                    "name": "order_id",
                    "type": "Many2one",
                    "comodel_name": "sale.order",
                    # required is missing/False -- not a line item
                },
            ],
        }
        spec = _make_spec(models=[parent_model, model])
        spec["depends"] = ["base", "mail"]
        ctx = _build_model_context(spec, model)
        assert "mail.thread" in ctx["inherit_list"], (
            "Non-required M2O should NOT trigger line item detection"
        )

    def test_inherit_list_line_item_detection_name_pattern(self):
        """Only Many2one fields ending in _id with comodel in same module count as line item indicators."""
        parent_model = {
            "name": "sale.order",
            "fields": [{"name": "name", "type": "Char"}],
        }
        model = {
            "name": "sale.order.line",
            "fields": [
                {"name": "name", "type": "Char"},
                {
                    "name": "related_order",  # Does NOT end in _id
                    "type": "Many2one",
                    "comodel_name": "sale.order",
                    "required": True,
                },
            ],
        }
        spec = _make_spec(models=[parent_model, model])
        spec["depends"] = ["base", "mail"]
        ctx = _build_model_context(spec, model)
        assert "mail.thread" in ctx["inherit_list"], (
            "M2O not ending in _id should NOT trigger line item detection"
        )


# ---------------------------------------------------------------------------
# Phase 12: _build_model_context -- needs_api (TMPL-02)
# ---------------------------------------------------------------------------


class TestBuildModelContextNeedsApi:
    """Tests that _build_model_context sets needs_api based on decorator usage."""

    def test_needs_api_true_with_computed(self):
        """Model with a computed field -> needs_api is True."""
        model = {
            "name": "test.model",
            "fields": [
                {"name": "total", "type": "Float", "compute": "_compute_total", "depends": ["qty"]},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["needs_api"] is True

    def test_needs_api_true_with_onchange(self):
        """Model with onchange field -> needs_api is True."""
        model = {
            "name": "test.model",
            "fields": [
                {"name": "partner_id", "type": "Many2one", "comodel_name": "res.partner", "onchange": True},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["needs_api"] is True

    def test_needs_api_true_with_constrained(self):
        """Model with constrained field -> needs_api is True."""
        model = {
            "name": "test.model",
            "fields": [
                {"name": "date_start", "type": "Date", "constrains": ["date_start", "date_end"]},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["needs_api"] is True

    def test_needs_api_true_with_sequence(self):
        """Model with sequence field (uses @api.model) -> needs_api is True."""
        model = {
            "name": "test.model",
            "fields": [
                {"name": "reference", "type": "Char", "required": True},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["needs_api"] is True

    def test_needs_api_false_plain_fields(self):
        """Model with only plain Char/Integer fields -> needs_api is False."""
        model = {
            "name": "test.model",
            "fields": [
                {"name": "name", "type": "Char"},
                {"name": "qty", "type": "Integer"},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["needs_api"] is False


# ---------------------------------------------------------------------------
# Phase 12: Template rendering -- mail.thread inheritance (TMPL-01)
# ---------------------------------------------------------------------------


class TestTemplateMailInheritance:
    """Tests that rendered model.py has correct _inherit line when mail is in depends."""

    def test_model_py_has_mail_thread_inherit_when_mail_depends(self):
        """render_module with mail in depends -> model.py contains _inherit = ['mail.thread', 'mail.activity.mixin']."""
        spec = {
            "module_name": "test_mail",
            "depends": ["base", "mail"],
            "models": [
                {
                    "name": "test.record",
                    "description": "Test Record",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            model_file = next(f for f in files if "test_record.py" in str(f) and "test_" not in Path(f).parent.name)
            content = Path(model_file).read_text(encoding="utf-8")
            assert "_inherit = [" in content, f"Expected _inherit list in model.py. Got:\n{content}"
            assert "mail.thread" in content
            assert "mail.activity.mixin" in content

    def test_model_py_no_inherit_when_no_mail(self):
        """render_module without mail -> model.py does NOT contain _inherit."""
        spec = {
            "module_name": "test_nomail",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.record",
                    "description": "Test Record",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            model_file = next(f for f in files if "test_record.py" in str(f) and "test_" not in Path(f).parent.name)
            content = Path(model_file).read_text(encoding="utf-8")
            assert "_inherit" not in content, f"Unexpected _inherit in model.py without mail. Got:\n{content}"


# ---------------------------------------------------------------------------
# Phase 12: Template rendering -- conditional api import (TMPL-02)
# ---------------------------------------------------------------------------


class TestTemplateConditionalApiImport:
    """Tests that rendered model.py conditionally imports api based on decorator usage."""

    def test_model_py_no_api_import_plain_fields(self):
        """render with plain fields only -> model.py does NOT have 'from odoo import api'."""
        spec = {
            "module_name": "test_noapi",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.simple",
                    "description": "Test Simple",
                    "fields": [
                        {"name": "name", "type": "Char", "required": True},
                        {"name": "qty", "type": "Integer"},
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            model_file = next(f for f in files if "test_simple.py" in str(f) and "test_" not in Path(f).parent.name)
            content = Path(model_file).read_text(encoding="utf-8")
            assert "from odoo import api" not in content, f"Unexpected api import in plain model. Got:\n{content}"
            assert "from odoo import fields, models" in content, f"Missing fields/models import. Got:\n{content}"

    def test_model_py_has_api_import_with_computed(self):
        """render with computed field -> model.py has 'from odoo import api, fields, models'."""
        spec = {
            "module_name": "test_withapi",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.computed",
                    "description": "Test Computed",
                    "fields": [
                        {"name": "qty", "type": "Integer"},
                        {"name": "total", "type": "Float", "compute": "_compute_total", "depends": ["qty"]},
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            model_file = next(f for f in files if "test_computed.py" in str(f) and "test_" not in Path(f).parent.name)
            content = Path(model_file).read_text(encoding="utf-8")
            assert "from odoo import api, fields, models" in content, f"Missing api import with computed. Got:\n{content}"


# ---------------------------------------------------------------------------
# Phase 12: Template rendering -- clean manifest (TMPL-03)
# ---------------------------------------------------------------------------


class TestTemplateManifestClean:
    """Tests that rendered __manifest__.py does not contain superfluous defaults."""

    def test_manifest_no_installable_key(self):
        """render module -> __manifest__.py does NOT contain '"installable"'."""
        spec = {
            "module_name": "test_manifest",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.item",
                    "description": "Test Item",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            manifest_file = next(f for f in files if Path(f).name == "__manifest__.py")
            content = Path(manifest_file).read_text(encoding="utf-8")
            assert '"installable"' not in content, f"Unexpected 'installable' key in manifest. Got:\n{content}"

    def test_manifest_no_auto_install_key(self):
        """render module -> __manifest__.py does NOT contain '"auto_install"'."""
        spec = {
            "module_name": "test_manifest2",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.item",
                    "description": "Test Item",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            manifest_file = next(f for f in files if Path(f).name == "__manifest__.py")
            content = Path(manifest_file).read_text(encoding="utf-8")
            assert '"auto_install"' not in content, f"Unexpected 'auto_install' key in manifest. Got:\n{content}"


# ---------------------------------------------------------------------------
# Phase 12: Template rendering -- clean test file (TMPL-04)
# ---------------------------------------------------------------------------


class TestTemplateTestFileClean:
    """Tests that rendered test files import only AccessError, not ValidationError."""

    def test_test_file_no_validation_error_import(self):
        """render module -> test file does NOT contain 'ValidationError'."""
        spec = {
            "module_name": "test_clean",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.item",
                    "description": "Test Item",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            test_file = next(f for f in files if "test_test_item.py" in str(f))
            content = Path(test_file).read_text(encoding="utf-8")
            assert "ValidationError" not in content, f"Unexpected ValidationError in test file. Got:\n{content}"

    def test_test_file_has_access_error_import(self):
        """render module -> test file contains 'AccessError'."""
        spec = {
            "module_name": "test_clean2",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.item",
                    "description": "Test Item",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            files, _ = render_module(spec, get_template_dir(), Path(d))
            test_file = next(f for f in files if "test_test_item.py" in str(f))
            content = Path(test_file).read_text(encoding="utf-8")
            assert "AccessError" in content, f"Missing AccessError in test file. Got:\n{content}"


# ---------------------------------------------------------------------------
# Phase 12: Full render integration test -- all 4 fixes together
# ---------------------------------------------------------------------------


class TestPhase12FullRenderIntegration:
    """Comprehensive integration test: renders a realistic module spec with mail dependency,
    computed fields, and plain models -- then asserts ALL 4 template fixes in a single render pass."""

    @pytest.fixture(autouse=True)
    def setup_render(self, tmp_path):
        """Render a realistic HR training module with mail, computed fields, and plain models."""
        self.spec = {
            "module_name": "hr_training",
            "depends": ["base", "mail", "hr"],
            "models": [
                {
                    "name": "hr.training.course",
                    "description": "Training Course",
                    "fields": [
                        {"name": "name", "type": "Char", "required": True, "string": "Course Name"},
                        {"name": "duration", "type": "Integer", "string": "Duration (Hours)"},
                        {"name": "description", "type": "Text", "string": "Description"},
                        {
                            "name": "total_hours",
                            "type": "Float",
                            "string": "Total Hours",
                            "compute": "_compute_total_hours",
                            "depends": ["duration"],
                        },
                        {
                            "name": "state",
                            "type": "Selection",
                            "string": "Status",
                            "selection": [
                                ["draft", "Draft"],
                                ["confirmed", "Confirmed"],
                                ["done", "Done"],
                            ],
                            "default": "draft",
                        },
                    ],
                },
                {
                    "name": "hr.training.session",
                    "description": "Training Session",
                    "fields": [
                        {"name": "name", "type": "Char", "required": True, "string": "Session Name"},
                        {"name": "date", "type": "Date", "string": "Date"},
                        {"name": "attendee_count", "type": "Integer", "string": "Attendee Count"},
                    ],
                },
            ],
        }
        self.files, _ = render_module(self.spec, get_template_dir(), tmp_path)
        self.module_dir = tmp_path / "hr_training"

    def _read(self, relative_path: str) -> str:
        """Read a file relative to the module directory."""
        return (self.module_dir / relative_path).read_text(encoding="utf-8")

    # -- TMPL-01: mail.thread inheritance on BOTH models --

    def test_course_model_has_mail_inherit(self):
        """hr_training_course model.py has _inherit with mail.thread and mail.activity.mixin."""
        content = self._read("models/hr_training_course.py")
        assert "_inherit = [" in content
        assert "mail.thread" in content
        assert "mail.activity.mixin" in content

    def test_session_model_has_mail_inherit(self):
        """hr_training_session model.py also has _inherit (mail applies to ALL models)."""
        content = self._read("models/hr_training_session.py")
        assert "_inherit = [" in content
        assert "mail.thread" in content
        assert "mail.activity.mixin" in content

    # -- TMPL-02: conditional api import --

    def test_course_model_has_api_import(self):
        """hr_training_course has computed field -> imports api."""
        content = self._read("models/hr_training_course.py")
        assert "from odoo import api, fields, models" in content

    def test_session_model_no_api_import(self):
        """hr_training_session has NO computed/onchange/constrained -> does NOT import api."""
        content = self._read("models/hr_training_session.py")
        assert "from odoo import api" not in content
        assert "from odoo import fields, models" in content

    # -- TMPL-03: clean manifest --

    def test_manifest_no_superfluous_keys(self):
        """__manifest__.py has no installable or auto_install keys."""
        content = self._read("__manifest__.py")
        assert '"installable"' not in content
        assert '"auto_install"' not in content
        # But it still has essential keys
        assert '"name"' in content
        assert '"depends"' in content

    # -- TMPL-04: clean test imports --

    def test_course_test_no_validation_error(self):
        """test_hr_training_course.py has no ValidationError import."""
        content = self._read("tests/test_hr_training_course.py")
        assert "ValidationError" not in content
        assert "AccessError" in content

    def test_session_test_no_validation_error(self):
        """test_hr_training_session.py has no ValidationError import."""
        content = self._read("tests/test_hr_training_session.py")
        assert "ValidationError" not in content
        assert "AccessError" in content


# ---------------------------------------------------------------------------
# TMPL-02: Wizard conditional api import
# ---------------------------------------------------------------------------


class TestWizardApiConditionalImport:
    """TMPL-02: Wizard .py should use conditional api import."""

    def test_wizard_api_conditional_import_with_default_get(self, tmp_path):
        """Wizard with default_get (always present) should import api."""
        spec = {
            "module_name": "test_module",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.model",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                },
            ],
            "wizards": [
                {
                    "name": "test.wizard",
                    "target_model": "test.model",
                    "fields": [{"name": "reason", "type": "Text"}],
                },
            ],
        }
        files, _ = render_module(spec, get_template_dir(), tmp_path)
        wizard_py = (tmp_path / "test_module" / "wizards" / "test_wizard.py").read_text()
        # default_get uses @api.model, so api should be imported
        assert "from odoo import api, fields, models" in wizard_py

    def test_wizard_api_conditional_import_needs_api_in_context(self, tmp_path):
        """Wizard template receives needs_api=True in context (for default_get)."""
        # Render a module with a wizard and verify the rendered .py file has api import
        # This confirms needs_api is being passed through to wizard_ctx
        spec = {
            "module_name": "test_module",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.model",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                },
            ],
            "wizards": [
                {
                    "name": "test.confirm",
                    "target_model": "test.model",
                    "fields": [{"name": "note", "type": "Char"}],
                },
            ],
        }
        files, _ = render_module(spec, get_template_dir(), tmp_path)
        wizard_py = (tmp_path / "test_module" / "wizards" / "test_confirm.py").read_text()
        # The import should be conditional — using the pattern from model.py.j2
        assert "from odoo import api, fields, models" in wizard_py
        assert "@api.model" in wizard_py


# ---------------------------------------------------------------------------
# TMPL-03: Wizard ACL entries in access CSV
# ---------------------------------------------------------------------------


class TestWizardAclEntries:
    """TMPL-03: ir.model.access.csv should include wizard ACL entries."""

    def test_wizard_acl_entries_in_csv(self, tmp_path):
        """Rendered CSV should have a line for each wizard with 1,1,1,1."""
        spec = {
            "module_name": "test_module",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.model",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                },
            ],
            "wizards": [
                {
                    "name": "test.wizard",
                    "target_model": "test.model",
                    "fields": [{"name": "reason", "type": "Text"}],
                },
            ],
        }
        files, _ = render_module(spec, get_template_dir(), tmp_path)
        csv_content = (tmp_path / "test_module" / "security" / "ir.model.access.csv").read_text()
        # Should have a wizard ACL line with full CRUD
        assert "access_test_wizard_user" in csv_content
        assert "test.wizard.user" in csv_content
        assert "model_test_wizard" in csv_content
        assert "1,1,1,1" in csv_content

    def test_wizard_acl_no_manager_line(self, tmp_path):
        """Wizard ACL should have only ONE line per wizard (user with 1,1,1,1), no manager."""
        spec = {
            "module_name": "test_module",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.model",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                },
            ],
            "wizards": [
                {
                    "name": "test.wizard",
                    "target_model": "test.model",
                    "fields": [{"name": "reason", "type": "Text"}],
                },
            ],
        }
        files, _ = render_module(spec, get_template_dir(), tmp_path)
        csv_content = (tmp_path / "test_module" / "security" / "ir.model.access.csv").read_text()
        # Count wizard lines -- should be exactly 1
        wizard_lines = [line for line in csv_content.splitlines() if "test_wizard" in line]
        assert len(wizard_lines) == 1, f"Expected 1 wizard ACL line, got {len(wizard_lines)}: {wizard_lines}"
        # That one line should have 1,1,1,1
        assert wizard_lines[0].endswith("1,1,1,1")

    def test_wizard_acl_multiple_wizards(self, tmp_path):
        """Multiple wizards each get their own ACL line."""
        spec = {
            "module_name": "test_module",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.model",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                },
            ],
            "wizards": [
                {
                    "name": "test.wizard.a",
                    "target_model": "test.model",
                    "fields": [{"name": "reason", "type": "Text"}],
                },
                {
                    "name": "test.wizard.b",
                    "target_model": "test.model",
                    "fields": [{"name": "note", "type": "Char"}],
                },
            ],
        }
        files, _ = render_module(spec, get_template_dir(), tmp_path)
        csv_content = (tmp_path / "test_module" / "security" / "ir.model.access.csv").read_text()
        assert "access_test_wizard_a_user" in csv_content
        assert "access_test_wizard_b_user" in csv_content


# ---------------------------------------------------------------------------
# TMPL-04: display_name instead of deprecated name_get
# ---------------------------------------------------------------------------


class TestDisplayNameVersionGate:
    """TMPL-04: Test template should use display_name with version gate."""

    def test_display_name_v18(self, tmp_path):
        """Odoo 18.0: test should assert display_name, NOT name_get()."""
        spec = {
            "module_name": "test_module",
            "odoo_version": "18.0",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.model",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                },
            ],
            "wizards": [],
        }
        files, _ = render_module(spec, get_template_dir(), tmp_path)
        test_content = (tmp_path / "test_module" / "tests" / "test_test_model.py").read_text()
        assert "test_display_name" in test_content
        assert "display_name" in test_content
        assert "name_get" not in test_content

    def test_display_name_v17(self, tmp_path):
        """Odoo 17.0: test should assert BOTH display_name and name_get()."""
        spec = {
            "module_name": "test_module",
            "odoo_version": "17.0",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.model",
                    "fields": [{"name": "name", "type": "Char", "required": True}],
                },
            ],
            "wizards": [],
        }
        files, _ = render_module(spec, get_template_dir(), tmp_path)
        test_content = (tmp_path / "test_module" / "tests" / "test_test_model.py").read_text()
        assert "test_display_name" in test_content
        assert "display_name" in test_content
        assert "name_get" in test_content

    def test_no_name_field_no_display_test(self, tmp_path):
        """Model without 'name' field should NOT generate test_display_name."""
        spec = {
            "module_name": "test_module",
            "odoo_version": "18.0",
            "depends": ["base"],
            "models": [
                {
                    "name": "test.model",
                    "fields": [{"name": "title", "type": "Char", "required": True}],
                },
            ],
            "wizards": [],
        }
        files, _ = render_module(spec, get_template_dir(), tmp_path)
        test_content = (tmp_path / "test_module" / "tests" / "test_test_model.py").read_text()
        assert "test_display_name" not in test_content
        assert "test_name_get" not in test_content
        assert "name_get" not in test_content


# ---------------------------------------------------------------------------
# Phase 26: Monetary field detection
# ---------------------------------------------------------------------------


class TestMonetaryPatternDetection:
    """Tests for _is_monetary_field() helper."""

    def test_float_amount_is_monetary(self):
        assert _is_monetary_field({"name": "amount", "type": "Float"}) is True

    def test_float_total_price_is_monetary(self):
        assert _is_monetary_field({"name": "total_price", "type": "Float"}) is True

    def test_float_tuition_fee_is_monetary(self):
        assert _is_monetary_field({"name": "tuition_fee", "type": "Float"}) is True

    def test_integer_amount_not_monetary(self):
        assert _is_monetary_field({"name": "amount", "type": "Integer"}) is False

    def test_char_amount_label_not_monetary(self):
        assert _is_monetary_field({"name": "amount_label", "type": "Char"}) is False

    def test_float_amount_opt_out(self):
        assert _is_monetary_field({"name": "amount", "type": "Float", "monetary": False}) is False

    def test_already_typed_monetary(self):
        assert _is_monetary_field({"name": "whatever", "type": "Monetary"}) is True

    def test_float_non_monetary_name(self):
        assert _is_monetary_field({"name": "weight", "type": "Float"}) is False

    @pytest.mark.parametrize("pattern", sorted(MONETARY_FIELD_PATTERNS))
    def test_all_20_patterns_match(self, pattern):
        assert _is_monetary_field({"name": pattern, "type": "Float"}) is True

    @pytest.mark.parametrize("pattern", sorted(MONETARY_FIELD_PATTERNS))
    def test_all_20_patterns_match_as_substring(self, pattern):
        assert _is_monetary_field({"name": f"total_{pattern}_value", "type": "Float"}) is True


class TestBuildModelContextMonetary:
    """Tests for monetary detection in _build_model_context()."""

    def test_float_amount_rewritten_to_monetary(self):
        model = {"name": "test.model", "fields": [{"name": "amount", "type": "Float"}]}
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["fields"][0]["type"] == "Monetary"

    def test_needs_currency_id_true_when_monetary_detected(self):
        model = {"name": "test.model", "fields": [{"name": "amount", "type": "Float"}]}
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["needs_currency_id"] is True

    def test_needs_currency_id_false_when_currency_id_exists(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "amount", "type": "Float"},
                {"name": "currency_id", "type": "Many2one", "comodel_name": "res.currency"},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["needs_currency_id"] is False

    def test_needs_currency_id_false_when_no_monetary(self):
        model = {"name": "test.model", "fields": [{"name": "weight", "type": "Float"}]}
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        assert ctx["needs_currency_id"] is False

    def test_immutability_original_fields_unchanged(self):
        original_fields = [{"name": "amount", "type": "Float"}]
        model = {"name": "test.model", "fields": original_fields}
        spec = _make_spec(models=[model])
        _build_model_context(spec, model)
        assert original_fields[0]["type"] == "Float"

    def test_computed_monetary_field_retains_compute(self):
        model = {
            "name": "test.model",
            "fields": [
                {"name": "total_amount", "type": "Float", "compute": "_compute_total_amount", "depends": ["qty"]},
            ],
        }
        spec = _make_spec(models=[model])
        ctx = _build_model_context(spec, model)
        field = ctx["fields"][0]
        assert field["type"] == "Monetary"
        assert field["compute"] == "_compute_total_amount"
