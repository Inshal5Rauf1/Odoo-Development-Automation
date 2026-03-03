"""Tests for renderer.py - Phase 5 extensions.

Tests for _build_model_context() new context keys and render_module() extended capabilities.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from odoo_gen_utils.renderer import (
    _build_model_context,
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(_COMPANY_SPEC, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
            names = [Path(f).name for f in files]
            assert "record_rules.xml" not in names, (
                f"Unexpected record_rules.xml in files without company_id: {names}"
            )

    def test_record_rules_xml_contains_company_ids_domain(self):
        """Content of generated record_rules.xml contains 'company_ids' OCA shorthand."""
        with tempfile.TemporaryDirectory() as d:
            files = render_module(_COMPANY_SPEC, get_template_dir(), Path(d))
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
            files = render_module(_COMPANY_SPEC, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
                files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
            files = render_module(spec, get_template_dir(), Path(d))
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
