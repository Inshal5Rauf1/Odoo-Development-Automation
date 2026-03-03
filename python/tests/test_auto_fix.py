"""Tests for auto_fix.py -- pylint and Docker auto-fix logic.

Tests cover:
- Pylint auto-fix for 5 fixable codes (W8113, W8111, C8116, W8150, C8107)
- Non-fixable code returns is_fixed=False
- Batch fix_pylint_violations returns (fixed_count, remaining)
- run_pylint_fix_loop enforces max 2 cycles
- Docker auto-fix pattern identification for 4 fixable patterns
- Escalation format grouping by file with line + suggestion
"""

from __future__ import annotations

import tempfile
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from odoo_gen_utils.auto_fix import (
    FIXABLE_DOCKER_PATTERNS,
    FIXABLE_PYLINT_CODES,
    MAX_FIX_CYCLES,
    _DOCKER_PATTERN_KEYWORDS,
    fix_missing_mail_thread,
    fix_pylint_violation,
    fix_pylint_violations,
    fix_unused_imports,
    format_escalation,
    identify_docker_fix,
    is_fixable_pylint,
    run_pylint_fix_loop,
)
from odoo_gen_utils.validation.types import Violation


# ---------------------------------------------------------------------------
# Constants validation
# ---------------------------------------------------------------------------


class TestConstants:
    def test_fixable_pylint_codes_contains_exactly_five(self):
        assert len(FIXABLE_PYLINT_CODES) == 5
        assert FIXABLE_PYLINT_CODES == frozenset({"W8113", "W8111", "C8116", "W8150", "C8107"})

    def test_fixable_docker_patterns_contains_exactly_four(self):
        assert len(FIXABLE_DOCKER_PATTERNS) == 4
        assert FIXABLE_DOCKER_PATTERNS == frozenset({
            "xml_parse_error", "missing_acl", "missing_import", "manifest_load_order",
        })

    def test_max_fix_cycles_is_two(self):
        assert MAX_FIX_CYCLES == 2


# ---------------------------------------------------------------------------
# is_fixable_pylint
# ---------------------------------------------------------------------------


class TestIsFixablePylint:
    def test_fixable_code_w8113(self):
        v = Violation(file="models/m.py", line=10, column=0, rule_code="W8113",
                      symbol="redundant-string", severity="warning", message="redundant string=")
        assert is_fixable_pylint(v) is True

    def test_non_fixable_code(self):
        v = Violation(file="models/m.py", line=10, column=0, rule_code="E8103",
                      symbol="missing-description", severity="error", message="missing _description")
        assert is_fixable_pylint(v) is False


# ---------------------------------------------------------------------------
# fix_pylint_violation -- individual code fixes
# ---------------------------------------------------------------------------


class TestFixPylintViolationW8113:
    """W8113: redundant string= parameter on field."""

    def test_removes_string_param_double_quotes(self):
        src = textwrap.dedent('''\
            from odoo import fields, models

            class TestModel(models.Model):
                _name = "test.model"
                name = fields.Char(string="Name", required=True)
        ''')
        with tempfile.TemporaryDirectory() as d:
            mod = Path(d)
            model_file = mod / "models" / "test_model.py"
            model_file.parent.mkdir(parents=True)
            model_file.write_text(src, encoding="utf-8")

            v = Violation(file="models/test_model.py", line=5, column=0,
                          rule_code="W8113", symbol="redundant-string",
                          severity="warning", message='Redundant string= on field "name"')
            result = fix_pylint_violation(v, mod)
            assert result is True

            content = model_file.read_text(encoding="utf-8")
            assert 'string="Name"' not in content
            assert "required=True" in content

    def test_removes_string_param_single_quotes(self):
        src = textwrap.dedent("""\
            from odoo import fields, models

            class TestModel(models.Model):
                _name = "test.model"
                name = fields.Char(string='Name', required=True)
        """)
        with tempfile.TemporaryDirectory() as d:
            mod = Path(d)
            model_file = mod / "models" / "test_model.py"
            model_file.parent.mkdir(parents=True)
            model_file.write_text(src, encoding="utf-8")

            v = Violation(file="models/test_model.py", line=5, column=0,
                          rule_code="W8113", symbol="redundant-string",
                          severity="warning", message='Redundant string= on field "name"')
            result = fix_pylint_violation(v, mod)
            assert result is True

            content = model_file.read_text(encoding="utf-8")
            assert "string='Name'" not in content


class TestFixPylintViolationW8111:
    """W8111: renamed field parameter."""

    def test_renames_track_visibility_to_tracking(self):
        src = textwrap.dedent('''\
            from odoo import fields, models

            class TestModel(models.Model):
                _name = "test.model"
                state = fields.Selection(track_visibility="onchange")
        ''')
        with tempfile.TemporaryDirectory() as d:
            mod = Path(d)
            model_file = mod / "models" / "test_model.py"
            model_file.parent.mkdir(parents=True)
            model_file.write_text(src, encoding="utf-8")

            v = Violation(file="models/test_model.py", line=5, column=0,
                          rule_code="W8111", symbol="renamed-field-parameter",
                          severity="warning",
                          message='"track_visibility" has been renamed to "tracking"')
            result = fix_pylint_violation(v, mod)
            assert result is True

            content = model_file.read_text(encoding="utf-8")
            assert "track_visibility" not in content
            assert "tracking" in content


class TestFixPylintViolationC8116:
    """C8116: superfluous manifest key."""

    def test_removes_superfluous_key(self):
        src = textwrap.dedent("""\
            {
                "name": "Test Module",
                "version": "17.0.1.0.0",
                "description": "A test module",
                "depends": ["base"],
            }
        """)
        with tempfile.TemporaryDirectory() as d:
            mod = Path(d)
            manifest = mod / "__manifest__.py"
            manifest.write_text(src, encoding="utf-8")

            v = Violation(file="__manifest__.py", line=4, column=0,
                          rule_code="C8116", symbol="manifest-deprecated-key",
                          severity="convention",
                          message='Deprecated key "description" in manifest file')
            result = fix_pylint_violation(v, mod)
            assert result is True

            content = manifest.read_text(encoding="utf-8")
            assert '"description"' not in content
            assert '"name"' in content
            assert '"depends"' in content


class TestFixPylintViolationW8150:
    """W8150: absolute import should be relative."""

    def test_converts_absolute_to_relative_import(self):
        src = textwrap.dedent("""\
            from odoo.addons.my_module import models
        """)
        with tempfile.TemporaryDirectory() as d:
            mod = Path(d)
            py_file = mod / "models" / "test_model.py"
            py_file.parent.mkdir(parents=True)
            py_file.write_text(src, encoding="utf-8")

            v = Violation(file="models/test_model.py", line=1, column=0,
                          rule_code="W8150", symbol="odoo-addons-relative-import",
                          severity="warning",
                          message="Use relative import `from . import models`")
            result = fix_pylint_violation(v, mod)
            assert result is True

            content = py_file.read_text(encoding="utf-8")
            assert "from odoo.addons.my_module" not in content
            assert "from ." in content


class TestFixPylintViolationC8107:
    """C8107: missing required manifest key."""

    def test_adds_missing_license_key(self):
        src = textwrap.dedent("""\
            {
                "name": "Test Module",
                "version": "17.0.1.0.0",
                "depends": ["base"],
            }
        """)
        with tempfile.TemporaryDirectory() as d:
            mod = Path(d)
            manifest = mod / "__manifest__.py"
            manifest.write_text(src, encoding="utf-8")

            v = Violation(file="__manifest__.py", line=1, column=0,
                          rule_code="C8107", symbol="manifest-required-key",
                          severity="convention",
                          message='Missing required key "license" in manifest file')
            result = fix_pylint_violation(v, mod)
            assert result is True

            content = manifest.read_text(encoding="utf-8")
            assert '"license"' in content


class TestFixPylintViolationNonFixable:
    """Non-fixable code returns False."""

    def test_non_fixable_returns_false(self):
        with tempfile.TemporaryDirectory() as d:
            mod = Path(d)
            model_file = mod / "models" / "test_model.py"
            model_file.parent.mkdir(parents=True)
            model_file.write_text("# some code\n", encoding="utf-8")

            v = Violation(file="models/test_model.py", line=1, column=0,
                          rule_code="E8103", symbol="missing-description",
                          severity="error", message="Model _description missing")
            result = fix_pylint_violation(v, mod)
            assert result is False


# ---------------------------------------------------------------------------
# fix_pylint_violations -- batch processing
# ---------------------------------------------------------------------------


class TestFixPylintViolations:
    def test_processes_list_returns_counts(self):
        src = textwrap.dedent('''\
            from odoo import fields, models

            class TestModel(models.Model):
                _name = "test.model"
                name = fields.Char(string="Name", required=True)
        ''')
        with tempfile.TemporaryDirectory() as d:
            mod = Path(d)
            model_file = mod / "models" / "test_model.py"
            model_file.parent.mkdir(parents=True)
            model_file.write_text(src, encoding="utf-8")

            violations = (
                Violation(file="models/test_model.py", line=5, column=0,
                          rule_code="W8113", symbol="redundant-string",
                          severity="warning", message='Redundant string= on field "name"'),
                Violation(file="models/test_model.py", line=10, column=0,
                          rule_code="E8103", symbol="missing-description",
                          severity="error", message="Model _description missing"),
            )
            fixed_count, remaining = fix_pylint_violations(violations, mod)
            assert fixed_count == 1
            assert len(remaining) == 1
            assert remaining[0].rule_code == "E8103"


# ---------------------------------------------------------------------------
# run_pylint_fix_loop -- max 2 cycles
# ---------------------------------------------------------------------------


class TestRunPylintFixLoop:
    def test_max_two_cycles(self):
        """Should run at most 2 cycles and return remaining violations."""
        cycle_count = 0
        fixable_v = Violation(
            file="models/m.py", line=5, column=0,
            rule_code="W8113", symbol="redundant-string",
            severity="warning", message='Redundant string= on field "name"',
        )
        non_fixable_v = Violation(
            file="models/m.py", line=10, column=0,
            rule_code="E8103", symbol="missing-description",
            severity="error", message="Model _description missing",
        )

        def mock_run_pylint(*args, **kwargs):
            nonlocal cycle_count
            cycle_count += 1
            # Always return both a fixable and non-fixable violation
            return (fixable_v, non_fixable_v)

        with tempfile.TemporaryDirectory() as d:
            mod = Path(d)
            model_file = mod / "models" / "m.py"
            model_file.parent.mkdir(parents=True)
            model_file.write_text(
                'from odoo import fields, models\n\n'
                'class M(models.Model):\n'
                '    _name = "m"\n'
                '    name = fields.Char(string="Name")\n',
                encoding="utf-8",
            )

            with patch("odoo_gen_utils.auto_fix.run_pylint_odoo", side_effect=mock_run_pylint):
                total_fixed, remaining = run_pylint_fix_loop(mod)

            assert cycle_count == 2
            assert total_fixed >= 1
            assert any(v.rule_code == "E8103" for v in remaining)

    def test_skips_cycle_2_when_no_fixable(self):
        """If cycle 1 produces 0 fixable violations, skip cycle 2."""
        cycle_count = 0
        non_fixable_v = Violation(
            file="models/m.py", line=10, column=0,
            rule_code="E8103", symbol="missing-description",
            severity="error", message="Model _description missing",
        )

        def mock_run_pylint(*args, **kwargs):
            nonlocal cycle_count
            cycle_count += 1
            return (non_fixable_v,)

        with tempfile.TemporaryDirectory() as d:
            mod = Path(d)
            with patch("odoo_gen_utils.auto_fix.run_pylint_odoo", side_effect=mock_run_pylint):
                total_fixed, remaining = run_pylint_fix_loop(mod)

            assert cycle_count == 1
            assert total_fixed == 0
            assert len(remaining) == 1


# ---------------------------------------------------------------------------
# identify_docker_fix
# ---------------------------------------------------------------------------


class TestIdentifyDockerFix:
    def test_xml_parse_error_identified(self):
        diagnosis = "[ERROR] An XML file has syntax errors. This can be a mismatched tag"
        result = identify_docker_fix(diagnosis)
        assert result == "xml_parse_error"

    def test_missing_acl_identified(self):
        diagnosis = "[ERROR] No access control list (ACL) entry exists for a model. ir.model.access"
        result = identify_docker_fix(diagnosis)
        assert result == "missing_acl"

    def test_missing_import_identified(self):
        diagnosis = "[ERROR] A Python module or Odoo addon could not be imported. No module named"
        result = identify_docker_fix(diagnosis)
        assert result == "missing_import"

    def test_manifest_load_order_identified(self):
        diagnosis = "[ERROR] A menu item or button references an action (ir.actions.act_window) that does not exist"
        result = identify_docker_fix(diagnosis)
        assert result == "manifest_load_order"

    def test_unknown_error_returns_none(self):
        diagnosis = "[ERROR] Some completely unknown error that does not match any pattern"
        result = identify_docker_fix(diagnosis)
        assert result is None


# ---------------------------------------------------------------------------
# format_escalation
# ---------------------------------------------------------------------------


class TestFormatEscalation:
    def test_groups_by_file_with_line_and_suggestion(self):
        violations = (
            Violation(file="models/sale_order.py", line=42, column=0,
                      rule_code="E8103", symbol="missing-description",
                      severity="error", message="Model _description missing",
                      suggestion='Add `_description = "Sales Order"` to the model class'),
            Violation(file="models/sale_order.py", line=10, column=0,
                      rule_code="C8101", symbol="manifest-missing-key",
                      severity="convention", message="Missing key in manifest"),
            Violation(file="__manifest__.py", line=1, column=0,
                      rule_code="C8101", symbol="manifest-missing-key",
                      severity="convention", message='Missing key "author" in manifest',
                      suggestion='Add `"author": "Your Name"` to __manifest__.py'),
        )
        result = format_escalation(violations)
        assert "Auto-fix exhausted" in result
        assert "models/sale_order.py" in result
        assert "__manifest__.py" in result
        assert ":42" in result
        assert ":10" in result
        assert "E8103" in result

    def test_empty_violations_returns_no_issues(self):
        result = format_escalation(())
        assert result == "No remaining issues."


# ---------------------------------------------------------------------------
# fix_missing_mail_thread -- AFIX-01
# ---------------------------------------------------------------------------


class TestFixMissingMailThread:
    """Detects chatter XML references and adds _inherit to model.py."""

    def _make_module(self, tmp_path: Path, model_content: str, xml_content: str) -> Path:
        """Helper: create a minimal module directory with models/ and views/."""
        module_dir = tmp_path / "test_module"
        (module_dir / "models").mkdir(parents=True)
        (module_dir / "views").mkdir(parents=True)
        (module_dir / "models" / "model.py").write_text(
            textwrap.dedent(model_content), encoding="utf-8"
        )
        (module_dir / "views" / "model_views.xml").write_text(
            textwrap.dedent(xml_content), encoding="utf-8"
        )
        return module_dir

    def test_adds_inherit_when_oe_chatter_present(self, tmp_path: Path):
        model_content = """\
            from odoo import fields, models

            class HrTraining(models.Model):
                _name = "hr.training"
                _description = "HR Training"

                name = fields.Char(string="Name", required=True)
        """
        xml_content = """\
            <odoo>
                <record id="view_hr_training_form" model="ir.ui.view">
                    <field name="arch" type="xml">
                        <form>
                            <sheet><group><field name="name"/></group></sheet>
                            <div class="oe_chatter">
                                <field name="message_follower_ids"/>
                                <field name="message_ids"/>
                            </div>
                        </form>
                    </field>
                </record>
            </odoo>
        """
        module_dir = self._make_module(tmp_path, model_content, xml_content)
        result = fix_missing_mail_thread(module_dir)
        assert result is True

        content = (module_dir / "models" / "model.py").read_text(encoding="utf-8")
        assert "_inherit = ['mail.thread', 'mail.activity.mixin']" in content

    def test_adds_inherit_when_chatter_tag_present(self, tmp_path: Path):
        model_content = """\
            from odoo import fields, models

            class HrTraining(models.Model):
                _name = "hr.training"
                _description = "HR Training"

                name = fields.Char(string="Name", required=True)
        """
        xml_content = """\
            <odoo>
                <record id="view_hr_training_form" model="ir.ui.view">
                    <field name="arch" type="xml">
                        <form>
                            <sheet><group><field name="name"/></group></sheet>
                            <chatter/>
                        </form>
                    </field>
                </record>
            </odoo>
        """
        module_dir = self._make_module(tmp_path, model_content, xml_content)
        result = fix_missing_mail_thread(module_dir)
        assert result is True

        content = (module_dir / "models" / "model.py").read_text(encoding="utf-8")
        assert "_inherit = ['mail.thread', 'mail.activity.mixin']" in content

    def test_adds_inherit_when_message_ids_present(self, tmp_path: Path):
        model_content = """\
            from odoo import fields, models

            class HrTraining(models.Model):
                _name = "hr.training"
                _description = "HR Training"

                name = fields.Char(string="Name", required=True)
        """
        xml_content = """\
            <odoo>
                <record id="view_hr_training_form" model="ir.ui.view">
                    <field name="arch" type="xml">
                        <form>
                            <sheet><group><field name="name"/></group></sheet>
                            <field name="message_ids"/>
                        </form>
                    </field>
                </record>
            </odoo>
        """
        module_dir = self._make_module(tmp_path, model_content, xml_content)
        result = fix_missing_mail_thread(module_dir)
        assert result is True

        content = (module_dir / "models" / "model.py").read_text(encoding="utf-8")
        assert "_inherit = ['mail.thread', 'mail.activity.mixin']" in content

    def test_no_change_when_inherit_already_present(self, tmp_path: Path):
        model_content = """\
            from odoo import fields, models

            class HrTraining(models.Model):
                _name = "hr.training"
                _inherit = ['mail.thread', 'mail.activity.mixin']
                _description = "HR Training"

                name = fields.Char(string="Name", required=True)
        """
        xml_content = """\
            <odoo>
                <record id="view_hr_training_form" model="ir.ui.view">
                    <field name="arch" type="xml">
                        <form>
                            <sheet><group><field name="name"/></group></sheet>
                            <div class="oe_chatter">
                                <field name="message_follower_ids"/>
                                <field name="message_ids"/>
                            </div>
                        </form>
                    </field>
                </record>
            </odoo>
        """
        module_dir = self._make_module(tmp_path, model_content, xml_content)
        result = fix_missing_mail_thread(module_dir)
        assert result is False

    def test_no_change_when_no_chatter_xml(self, tmp_path: Path):
        model_content = """\
            from odoo import fields, models

            class HrTraining(models.Model):
                _name = "hr.training"
                _description = "HR Training"

                name = fields.Char(string="Name", required=True)
        """
        xml_content = """\
            <odoo>
                <record id="view_hr_training_form" model="ir.ui.view">
                    <field name="arch" type="xml">
                        <form>
                            <sheet><group><field name="name"/></group></sheet>
                        </form>
                    </field>
                </record>
            </odoo>
        """
        module_dir = self._make_module(tmp_path, model_content, xml_content)
        result = fix_missing_mail_thread(module_dir)
        assert result is False

    def test_inherit_inserted_after_description(self, tmp_path: Path):
        model_content = """\
            from odoo import fields, models

            class HrTraining(models.Model):
                _name = "hr.training"
                _description = "HR Training"

                name = fields.Char(string="Name", required=True)
        """
        xml_content = """\
            <odoo>
                <record id="view_hr_training_form" model="ir.ui.view">
                    <field name="arch" type="xml">
                        <form>
                            <sheet><group><field name="name"/></group></sheet>
                            <div class="oe_chatter">
                                <field name="message_follower_ids"/>
                                <field name="message_ids"/>
                            </div>
                        </form>
                    </field>
                </record>
            </odoo>
        """
        module_dir = self._make_module(tmp_path, model_content, xml_content)
        fix_missing_mail_thread(module_dir)

        content = (module_dir / "models" / "model.py").read_text(encoding="utf-8")
        lines = content.split("\n")
        desc_idx = next(i for i, line in enumerate(lines) if "_description" in line)
        inherit_idx = next(i for i, line in enumerate(lines) if "_inherit" in line)
        assert inherit_idx == desc_idx + 1


# ---------------------------------------------------------------------------
# fix_unused_imports -- AFIX-02
# ---------------------------------------------------------------------------


class TestFixUnusedImports:
    """Detects and removes unused imports in generated Python files."""

    def test_removes_unused_validation_error(self, tmp_path: Path):
        src = textwrap.dedent("""\
            from odoo import fields, models
            from odoo.exceptions import ValidationError

            class TestModel(models.Model):
                _name = "test.model"
                _description = "Test Model"

                name = fields.Char(string="Name", required=True)
        """)
        py_file = tmp_path / "test_model.py"
        py_file.write_text(src, encoding="utf-8")

        result = fix_unused_imports(py_file)
        assert result is True

        content = py_file.read_text(encoding="utf-8")
        assert "ValidationError" not in content

    def test_removes_unused_api(self, tmp_path: Path):
        src = textwrap.dedent("""\
            from odoo import api, fields, models

            class TestModel(models.Model):
                _name = "test.model"
                _description = "Test Model"

                name = fields.Char(string="Name", required=True)
        """)
        py_file = tmp_path / "test_model.py"
        py_file.write_text(src, encoding="utf-8")

        result = fix_unused_imports(py_file)
        assert result is True

        content = py_file.read_text(encoding="utf-8")
        assert "api" not in content
        assert "from odoo import fields, models" in content

    def test_keeps_used_imports(self, tmp_path: Path):
        src = textwrap.dedent("""\
            from odoo import api, fields, models
            from odoo.exceptions import AccessError, ValidationError

            class TestModel(models.Model):
                _name = "test.model"
                _description = "Test Model"

                name = fields.Char(string="Name", required=True)

                @api.constrains("name")
                def _check_name(self):
                    for record in self:
                        if not record.name:
                            raise ValidationError("Name is required")
                        if not self.env.user.has_group("base.group_user"):
                            raise AccessError("Not allowed")
        """)
        py_file = tmp_path / "test_model.py"
        py_file.write_text(src, encoding="utf-8")

        result = fix_unused_imports(py_file)
        assert result is False

    def test_removes_only_unused_from_multi_import(self, tmp_path: Path):
        src = textwrap.dedent("""\
            from odoo import fields, models
            from odoo.exceptions import AccessError, ValidationError

            class TestModel(models.Model):
                _name = "test.model"
                _description = "Test Model"

                name = fields.Char(string="Name", required=True)

                def check_access(self):
                    if not self.env.user.has_group("base.group_user"):
                        raise AccessError("Not allowed")
        """)
        py_file = tmp_path / "test_model.py"
        py_file.write_text(src, encoding="utf-8")

        result = fix_unused_imports(py_file)
        assert result is True

        content = py_file.read_text(encoding="utf-8")
        assert "ValidationError" not in content
        assert "AccessError" in content

    def test_no_change_empty_file(self, tmp_path: Path):
        py_file = tmp_path / "empty.py"
        py_file.write_text("", encoding="utf-8")

        result = fix_unused_imports(py_file)
        assert result is False


# ---------------------------------------------------------------------------
# Updated constants -- missing_mail_thread in Docker patterns
# ---------------------------------------------------------------------------


class TestUpdatedConstants:
    """Verify FIXABLE_DOCKER_PATTERNS updated to include missing_mail_thread."""

    def test_fixable_docker_patterns_contains_five(self):
        assert len(FIXABLE_DOCKER_PATTERNS) == 5
        assert "missing_mail_thread" in FIXABLE_DOCKER_PATTERNS

    def test_docker_pattern_keywords_has_mail_thread(self):
        assert "missing_mail_thread" in _DOCKER_PATTERN_KEYWORDS

    def test_identify_docker_fix_mail_thread(self):
        result = identify_docker_fix("missing mail.thread inheritance")
        assert result == "missing_mail_thread"

    def test_identify_docker_fix_oe_chatter(self):
        result = identify_docker_fix(
            "oe_chatter div found but model lacks mail.thread"
        )
        assert result == "missing_mail_thread"
