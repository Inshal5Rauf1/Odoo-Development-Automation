"""Tests for semantic validation module (E1-E6 errors, W1-W4 warnings)."""

from __future__ import annotations

import textwrap
import time
from pathlib import Path

import pytest

from odoo_gen_utils.validation.semantic import (
    SemanticValidationResult,
    ValidationIssue,
    print_validation_report,
    semantic_validate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    """Write *content* to *path*, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _make_valid_module(root: Path, module_name: str = "test_module") -> Path:
    """Scaffold a minimal valid module at *root/module_name*."""
    mod = root / module_name
    _write(mod / "__manifest__.py", """\
        {
            'name': 'Test Module',
            'version': '17.0.1.0.0',
            'depends': ['base'],
            'data': [
                'security/ir.model.access.csv',
                'views/partner_views.xml',
            ],
        }
    """)
    _write(mod / "__init__.py", "from . import models\n")
    _write(mod / "models" / "__init__.py", "from . import partner\n")
    _write(mod / "models" / "partner.py", """\
        from odoo import api, fields, models

        class ResPartnerExt(models.Model):
            _name = 'res.partner.ext'
            _description = 'Partner Extension'

            name = fields.Char(string='Name')
            code = fields.Char(string='Code')
            amount = fields.Float(string='Amount')
    """)
    _write(mod / "security" / "ir.model.access.csv", """\
        id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
        access_partner_ext,partner.ext,model_res_partner_ext,base.group_user,1,1,1,1
    """)
    _write(mod / "views" / "partner_views.xml", """\
        <?xml version="1.0" encoding="utf-8"?>
        <odoo>
            <record id="view_partner_ext_form" model="ir.ui.view">
                <field name="name">partner.ext.form</field>
                <field name="model">res.partner.ext</field>
                <field name="arch" type="xml">
                    <form>
                        <field name="name"/>
                        <field name="code"/>
                        <field name="amount"/>
                    </form>
                </field>
            </record>
        </odoo>
    """)
    return mod


# ===========================================================================
# E1: Python Syntax
# ===========================================================================


class TestE1PythonSyntax:
    """E1: ast.parse() catches Python syntax errors."""

    def test_valid_python_no_issues(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        result = semantic_validate(mod)
        e1 = [i for i in result.errors if i.code == "E1"]
        assert e1 == []

    def test_syntax_error_reported(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "models" / "broken.py", "def foo(\n")
        result = semantic_validate(mod)
        e1 = [i for i in result.errors if i.code == "E1"]
        assert len(e1) == 1
        assert "broken.py" in e1[0].file
        assert e1[0].severity == "error"


# ===========================================================================
# E2: XML Well-Formedness
# ===========================================================================


class TestE2XmlWellFormedness:
    """E2: xml.etree catches malformed XML."""

    def test_valid_xml_no_issues(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        result = semantic_validate(mod)
        e2 = [i for i in result.errors if i.code == "E2"]
        assert e2 == []

    def test_malformed_xml_reported(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "views" / "bad.xml", "<odoo><record></odoo>")
        result = semantic_validate(mod)
        e2 = [i for i in result.errors if i.code == "E2"]
        assert len(e2) == 1
        assert "bad.xml" in e2[0].file
        assert e2[0].severity == "error"


# ===========================================================================
# E3: View Field References
# ===========================================================================


class TestE3FieldReferences:
    """E3: view field refs that don't exist on model are errors."""

    def test_valid_field_refs_no_issues(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        result = semantic_validate(mod)
        e3 = [i for i in result.errors if i.code == "E3"]
        assert e3 == []

    def test_missing_field_ref_error_with_suggestion(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        # Reference 'amont' which doesn't exist but is close to 'amount'
        _write(mod / "views" / "partner_views.xml", """\
            <?xml version="1.0" encoding="utf-8"?>
            <odoo>
                <record id="view_partner_ext_form" model="ir.ui.view">
                    <field name="name">partner.ext.form</field>
                    <field name="model">res.partner.ext</field>
                    <field name="arch" type="xml">
                        <form>
                            <field name="amont"/>
                        </form>
                    </field>
                </record>
            </odoo>
        """)
        result = semantic_validate(mod)
        e3 = [i for i in result.errors if i.code == "E3"]
        assert len(e3) == 1
        assert "amont" in e3[0].message
        assert e3[0].suggestion is not None
        assert "amount" in e3[0].suggestion

    def test_inherited_fields_recognized(self, tmp_path: Path) -> None:
        """Fields from _inherit (e.g., mail.thread -> message_ids) are valid."""
        mod = _make_valid_module(tmp_path)
        _write(mod / "models" / "partner.py", """\
            from odoo import fields, models

            class ResPartnerExt(models.Model):
                _name = 'res.partner.ext'
                _inherit = ['mail.thread']
                _description = 'Partner Extension'

                name = fields.Char(string='Name')
        """)
        _write(mod / "views" / "partner_views.xml", """\
            <?xml version="1.0" encoding="utf-8"?>
            <odoo>
                <record id="view_partner_ext_form" model="ir.ui.view">
                    <field name="name">partner.ext.form</field>
                    <field name="model">res.partner.ext</field>
                    <field name="arch" type="xml">
                        <form>
                            <field name="name"/>
                            <field name="message_ids"/>
                        </form>
                    </field>
                </record>
            </odoo>
        """)
        result = semantic_validate(mod)
        e3 = [i for i in result.errors if i.code == "E3"]
        assert e3 == []

    def test_view_metadata_fields_not_checked(self, tmp_path: Path) -> None:
        """Top-level view fields (name, model, arch, priority) are NOT model fields."""
        mod = _make_valid_module(tmp_path)
        result = semantic_validate(mod)
        # 'name', 'model', 'arch' appear as <field name="..."> but outside <form>
        e3 = [i for i in result.errors if i.code == "E3"]
        assert e3 == []


# ===========================================================================
# E4: ACL References
# ===========================================================================


class TestE4AclReferences:
    """E4: ACL CSV entries referencing non-existent model XML IDs."""

    def test_valid_acl_no_issues(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        result = semantic_validate(mod)
        e4 = [i for i in result.errors if i.code == "E4"]
        assert e4 == []

    def test_unknown_model_ref_error(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "security" / "ir.model.access.csv", """\
            id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
            access_bad,bad.access,model_nonexistent_model,base.group_user,1,1,1,1
        """)
        result = semantic_validate(mod)
        e4 = [i for i in result.errors if i.code == "E4"]
        assert len(e4) == 1
        assert "nonexistent" in e4[0].message.lower() or "model_nonexistent_model" in e4[0].message

    def test_module_prefixed_group_handled(self, tmp_path: Path) -> None:
        """group_id:id with module prefix (e.g., base.group_user) works."""
        mod = _make_valid_module(tmp_path)
        result = semantic_validate(mod)
        e4 = [i for i in result.errors if i.code == "E4"]
        assert e4 == []


# ===========================================================================
# E5: XML ID Uniqueness
# ===========================================================================


class TestE5XmlIdUniqueness:
    """E5: Duplicate XML IDs across data files."""

    def test_unique_ids_no_issues(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        result = semantic_validate(mod)
        e5 = [i for i in result.errors if i.code == "E5"]
        assert e5 == []

    def test_duplicate_id_error(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "views" / "extra_views.xml", """\
            <?xml version="1.0" encoding="utf-8"?>
            <odoo>
                <record id="view_partner_ext_form" model="ir.ui.view">
                    <field name="name">duplicate</field>
                    <field name="model">res.partner.ext</field>
                    <field name="arch" type="xml">
                        <form><field name="name"/></form>
                    </field>
                </record>
            </odoo>
        """)
        result = semantic_validate(mod)
        e5 = [i for i in result.errors if i.code == "E5"]
        assert len(e5) >= 1
        assert "view_partner_ext_form" in e5[0].message


# ===========================================================================
# E6: Manifest Depends
# ===========================================================================


class TestE6ManifestDepends:
    """E6: Missing manifest depends for cross-module imports."""

    def test_complete_depends_no_issues(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        result = semantic_validate(mod)
        e6 = [i for i in result.errors if i.code == "E6"]
        assert e6 == []

    def test_missing_import_dep_error(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "models" / "partner.py", """\
            from odoo import fields, models
            from odoo.addons.sale import something

            class ResPartnerExt(models.Model):
                _name = 'res.partner.ext'
                _description = 'Partner Extension'
                name = fields.Char()
        """)
        result = semantic_validate(mod)
        e6 = [i for i in result.errors if i.code == "E6"]
        assert len(e6) == 1
        assert "sale" in e6[0].message

    def test_xml_ref_dep_checked(self, tmp_path: Path) -> None:
        """XML ref="" attributes referencing external modules need depends."""
        mod = _make_valid_module(tmp_path)
        _write(mod / "views" / "partner_views.xml", """\
            <?xml version="1.0" encoding="utf-8"?>
            <odoo>
                <record id="view_partner_ext_form" model="ir.ui.view">
                    <field name="name">partner.ext.form</field>
                    <field name="model">res.partner.ext</field>
                    <field name="arch" type="xml">
                        <form>
                            <field name="name"/>
                        </form>
                    </field>
                    <field name="inherit_id" ref="sale.view_order_form"/>
                </record>
            </odoo>
        """)
        result = semantic_validate(mod)
        e6 = [i for i in result.errors if i.code == "E6"]
        assert len(e6) == 1
        assert "sale" in e6[0].message


# ===========================================================================
# W1: Comodel References
# ===========================================================================


class TestW1Comodel:
    """W1: comodel_name checked against registry and known models."""

    def test_known_comodel_no_warning(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "models" / "partner.py", """\
            from odoo import fields, models

            class ResPartnerExt(models.Model):
                _name = 'res.partner.ext'
                _description = 'Partner Extension'
                partner_id = fields.Many2one('res.partner')
        """)
        result = semantic_validate(mod)
        w1 = [i for i in result.warnings if i.code == "W1"]
        assert w1 == []

    def test_unknown_comodel_warning(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "models" / "partner.py", """\
            from odoo import fields, models

            class ResPartnerExt(models.Model):
                _name = 'res.partner.ext'
                _description = 'Partner Extension'
                weird_id = fields.Many2one('completely.unknown.model')
        """)
        result = semantic_validate(mod)
        w1 = [i for i in result.warnings if i.code == "W1"]
        assert len(w1) == 1
        assert "completely.unknown.model" in w1[0].message


# ===========================================================================
# W2: Computed Field Depends
# ===========================================================================


class TestW2ComputedDepends:
    """W2: @api.depends references validated as warnings."""

    def test_valid_depends_no_warning(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "models" / "partner.py", """\
            from odoo import api, fields, models

            class ResPartnerExt(models.Model):
                _name = 'res.partner.ext'
                _description = 'Partner Extension'
                name = fields.Char()
                upper_name = fields.Char(compute='_compute_upper')

                @api.depends('name')
                def _compute_upper(self):
                    for rec in self:
                        rec.upper_name = rec.name.upper() if rec.name else ''
        """)
        result = semantic_validate(mod)
        w2 = [i for i in result.warnings if i.code == "W2"]
        assert w2 == []

    def test_invalid_depends_warning(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "models" / "partner.py", """\
            from odoo import api, fields, models

            class ResPartnerExt(models.Model):
                _name = 'res.partner.ext'
                _description = 'Partner Extension'
                name = fields.Char()
                upper_name = fields.Char(compute='_compute_upper')

                @api.depends('nonexistent_field')
                def _compute_upper(self):
                    pass
        """)
        result = semantic_validate(mod)
        w2 = [i for i in result.warnings if i.code == "W2"]
        assert len(w2) == 1
        assert "nonexistent_field" in w2[0].message

    def test_dot_notation_only_first_segment(self, tmp_path: Path) -> None:
        """Dot-notation depends ('partner_id.name') validates first segment only."""
        mod = _make_valid_module(tmp_path)
        _write(mod / "models" / "partner.py", """\
            from odoo import api, fields, models

            class ResPartnerExt(models.Model):
                _name = 'res.partner.ext'
                _description = 'Partner Extension'
                partner_id = fields.Many2one('res.partner')
                display = fields.Char(compute='_compute_display')

                @api.depends('partner_id.name')
                def _compute_display(self):
                    pass
        """)
        result = semantic_validate(mod)
        w2 = [i for i in result.warnings if i.code == "W2"]
        assert w2 == []


# ===========================================================================
# W3: Security Group References
# ===========================================================================


class TestW3GroupRefs:
    """W3: groups= in XML views validated as warnings."""

    def test_known_group_no_warning(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "views" / "partner_views.xml", """\
            <?xml version="1.0" encoding="utf-8"?>
            <odoo>
                <record id="view_partner_ext_form" model="ir.ui.view">
                    <field name="name">partner.ext.form</field>
                    <field name="model">res.partner.ext</field>
                    <field name="arch" type="xml">
                        <form>
                            <field name="name" groups="base.group_user"/>
                        </form>
                    </field>
                </record>
            </odoo>
        """)
        result = semantic_validate(mod)
        w3 = [i for i in result.warnings if i.code == "W3"]
        assert w3 == []

    def test_unknown_group_warning(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "views" / "partner_views.xml", """\
            <?xml version="1.0" encoding="utf-8"?>
            <odoo>
                <record id="view_partner_ext_form" model="ir.ui.view">
                    <field name="name">partner.ext.form</field>
                    <field name="model">res.partner.ext</field>
                    <field name="arch" type="xml">
                        <form>
                            <field name="name" groups="fake_module.nonexistent_group"/>
                        </form>
                    </field>
                </record>
            </odoo>
        """)
        result = semantic_validate(mod)
        w3 = [i for i in result.warnings if i.code == "W3"]
        assert len(w3) == 1
        assert "fake_module.nonexistent_group" in w3[0].message


# ===========================================================================
# W4: Record Rule Domain Field References
# ===========================================================================


class TestW4RuleDomain:
    """W4: ir.rule domain_force field references validated."""

    def test_valid_domain_no_warning(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "security" / "rules.xml", """\
            <?xml version="1.0" encoding="utf-8"?>
            <odoo>
                <record id="rule_partner_ext" model="ir.rule">
                    <field name="name">Partner Ext Rule</field>
                    <field name="model_id" ref="model_res_partner_ext"/>
                    <field name="domain_force">[('name', '!=', False)]</field>
                </record>
            </odoo>
        """)
        result = semantic_validate(mod)
        w4 = [i for i in result.warnings if i.code == "W4"]
        assert w4 == []

    def test_invalid_domain_field_warning(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "security" / "rules.xml", """\
            <?xml version="1.0" encoding="utf-8"?>
            <odoo>
                <record id="rule_partner_ext" model="ir.rule">
                    <field name="name">Partner Ext Rule</field>
                    <field name="model_id" ref="model_res_partner_ext"/>
                    <field name="domain_force">[('nonexistent_field', '=', True)]</field>
                </record>
            </odoo>
        """)
        result = semantic_validate(mod)
        w4 = [i for i in result.warnings if i.code == "W4"]
        assert len(w4) == 1
        assert "nonexistent_field" in w4[0].message


# ===========================================================================
# Short-Circuit
# ===========================================================================


class TestShortCircuit:
    """Short-circuit skips cross-ref checks when E1/E2 fails."""

    def test_e1_failure_skips_field_checks(self, tmp_path: Path) -> None:
        """E1 failure on a .py file skips E3/W1/W2 for that file."""
        mod = _make_valid_module(tmp_path)
        # Break the only model file - should not get E3 errors for missing fields
        _write(mod / "models" / "partner.py", "def broken(\n")
        result = semantic_validate(mod)
        e1 = [i for i in result.errors if i.code == "E1"]
        assert len(e1) >= 1
        # Should NOT have E3 errors since models couldn't be parsed
        e3 = [i for i in result.errors if i.code == "E3"]
        assert e3 == []

    def test_e2_failure_skips_xml_checks(self, tmp_path: Path) -> None:
        """E2 failure on .xml file skips E3/E5/W3/W4 for that file."""
        mod = _make_valid_module(tmp_path)
        _write(mod / "views" / "partner_views.xml", "<odoo><broken></odoo>")
        result = semantic_validate(mod)
        e2 = [i for i in result.errors if i.code == "E2"]
        assert len(e2) >= 1
        # Should NOT have E5 errors for this file
        e5 = [i for i in result.errors if i.code == "E5"]
        # Any E5 should not reference the broken file
        for issue in e5:
            assert "partner_views.xml" not in issue.file


# ===========================================================================
# Performance
# ===========================================================================


class TestPerformance:
    """Performance: 10-model module validates under 2 seconds."""

    def test_validation_under_2_seconds(self, tmp_path: Path) -> None:
        mod = tmp_path / "perf_module"
        models_code = ["from odoo import fields, models\n"]
        for i in range(10):
            models_code.append(f"""
class Model{i}(models.Model):
    _name = 'perf.model.{i}'
    _description = 'Perf Model {i}'
    name = fields.Char()
    value = fields.Integer()
    active = fields.Boolean(default=True)
""")
        _write(mod / "__manifest__.py", """\
            {
                'name': 'Perf Module',
                'version': '17.0.1.0.0',
                'depends': ['base'],
                'data': [],
            }
        """)
        _write(mod / "__init__.py", "from . import models\n")
        _write(mod / "models" / "__init__.py", "from . import perf\n")
        _write(mod / "models" / "perf.py", "\n".join(models_code))

        start = time.perf_counter()
        result = semantic_validate(mod)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"Validation took {elapsed:.2f}s (budget: 2s)"
        assert result.duration_ms < 2000


# ===========================================================================
# Result structure
# ===========================================================================


class TestResultStructure:
    """Verify result dataclass properties."""

    def test_has_errors_property(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        result = semantic_validate(mod)
        assert result.has_errors is False

    def test_has_errors_true_on_error(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        _write(mod / "models" / "broken.py", "def x(\n")
        result = semantic_validate(mod)
        assert result.has_errors is True

    def test_duration_ms_set(self, tmp_path: Path) -> None:
        mod = _make_valid_module(tmp_path)
        result = semantic_validate(mod)
        assert result.duration_ms >= 0

    def test_print_validation_report(self, tmp_path: Path, capsys) -> None:
        mod = _make_valid_module(tmp_path)
        result = semantic_validate(mod)
        print_validation_report(result)
        captured = capsys.readouterr()
        assert "Semantic Validation" in captured.out or "validation" in captured.out.lower()


# ===========================================================================
# E2E: CLI Integration
# ===========================================================================


class TestE2ECliIntegration:
    """E2E tests for CLI render-module + semantic validation pipeline."""

    def test_full_module_validation(self, tmp_path: Path) -> None:
        """Render a valid module scaffold and validate it -- zero errors expected."""
        mod = _make_valid_module(tmp_path, "my_module")
        result = semantic_validate(mod)
        assert result.has_errors is False, (
            f"Valid module produced errors: {[e.message for e in result.errors]}"
        )

    def test_cli_skip_validation_flag_exists(self) -> None:
        """--skip-validation flag is accepted by the render-module CLI command."""
        from click.testing import CliRunner

        from odoo_gen_utils.cli import main

        runner = CliRunner()
        # Invoke with --help to verify the flag is listed (no spec needed)
        result = runner.invoke(main, ["render-module", "--help"])
        assert result.exit_code == 0
        assert "--skip-validation" in result.output

    def test_validation_gates_registry(self, tmp_path: Path) -> None:
        """Semantic errors block registry update: introduce bad field, confirm has_errors."""
        mod = _make_valid_module(tmp_path)
        # Introduce a deliberate error: reference non-existent field in view
        _write(mod / "views" / "partner_views.xml", """\
            <?xml version="1.0" encoding="utf-8"?>
            <odoo>
                <record id="view_partner_ext_form" model="ir.ui.view">
                    <field name="name">partner.ext.form</field>
                    <field name="model">res.partner.ext</field>
                    <field name="arch" type="xml">
                        <form>
                            <field name="nonexistent_field_xyz"/>
                        </form>
                    </field>
                </record>
            </odoo>
        """)
        result = semantic_validate(mod)
        assert result.has_errors is True
        e3 = [i for i in result.errors if i.code == "E3"]
        assert len(e3) >= 1
        assert "nonexistent_field_xyz" in e3[0].message
