"""Integration tests for EnvironmentVerifier with live Odoo dev instance.

Requires Phase 15 Docker dev instance running:
    cd /home/inshal-rauf/Odoo_module_automation/docker/dev && docker compose up -d

These tests are excluded from the normal CI suite via `pytest.mark.docker`.
Run with: pytest tests/test_verifier_integration.py -x -q -m docker

Source: MCP-03 acceptance criteria: "Integration test: generate model inheriting
hr.employee -> verify MCP checks fire and return no warnings (hr.employee exists)"
"""
from __future__ import annotations

import pytest

from odoo_gen_utils.mcp.odoo_client import OdooClient, OdooConfig
from odoo_gen_utils.verifier import EnvironmentVerifier, VerificationWarning


pytestmark = pytest.mark.docker


@pytest.fixture(scope="module")
def live_client():
    """OdooClient connected to Phase 15 dev instance.

    Uses module scope so one auth handshake serves all tests in this file.
    OdooConfig matches Phase 15 Docker Compose setup (db=odoo_dev, admin/admin).
    """
    config = OdooConfig(
        url="http://localhost:8069",
        db="odoo_dev",
        username="admin",
        api_key="admin",
    )
    return OdooClient(config)


@pytest.fixture(scope="module")
def live_verifier(live_client: OdooClient) -> EnvironmentVerifier:
    """EnvironmentVerifier backed by live Odoo dev instance."""
    return EnvironmentVerifier(client=live_client)


def test_hr_employee_inherit_passes(live_verifier: EnvironmentVerifier) -> None:
    """MCP-03: Generating a model inheriting hr.employee fires MCP checks and passes.

    hr.employee and hr.department should both exist in the Odoo 17 CE dev instance
    because the hr module is installed in the Phase 15 base setup.
    """
    model = {
        "name": "my.employee.extension",
        "inherit": "hr.employee",
        "fields": [
            {"name": "department_id", "type": "Many2one", "comodel_name": "hr.department"},
        ],
    }
    warnings = live_verifier.verify_model_spec(model)
    assert warnings == [], f"Unexpected warnings for hr.employee inherit: {warnings}"


def test_missing_model_inherit_fires_warning(live_verifier: EnvironmentVerifier) -> None:
    """MCP-03: _inherit of a definitely nonexistent model produces a model_inherit warning.

    'definitely.nonexistent.model.xyz' will never exist in any Odoo instance,
    so this must always produce a warning.
    """
    model = {
        "name": "my.model",
        "inherit": "definitely.nonexistent.model.xyz",
        "fields": [],
    }
    warnings = live_verifier.verify_model_spec(model)
    assert any(
        w.check_type == "model_inherit" for w in warnings
    ), f"Expected model_inherit warning; got: {warnings}"


def test_view_nonexistent_field_fires_warning(live_verifier: EnvironmentVerifier) -> None:
    """MCP-04: View referencing a nonexistent field on hr.employee raises a view_field warning.

    hr.employee is a real model in the dev instance, but
    'totally_nonexistent_field_xyz_abc' is not a field on it, so verifier
    must return a view_field warning.
    """
    warnings = live_verifier.verify_view_spec(
        "hr.employee",
        ["name", "totally_nonexistent_field_xyz_abc"],
    )
    assert any(
        w.check_type == "view_field" for w in warnings
    ), f"Expected view_field warning; got: {warnings}"


def test_view_existing_fields_pass(live_verifier: EnvironmentVerifier) -> None:
    """MCP-04: View referencing known hr.employee fields produces no warnings.

    'name' and 'job_id' are always present on hr.employee in Odoo 17 CE.
    """
    warnings = live_verifier.verify_view_spec("hr.employee", ["name", "job_id"])
    assert warnings == [], f"Unexpected warnings for hr.employee fields: {warnings}"
