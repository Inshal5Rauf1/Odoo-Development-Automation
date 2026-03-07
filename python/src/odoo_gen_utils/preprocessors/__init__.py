"""Preprocessor package -- temporary shim for Task 1 (TDD registry tests).

Re-exports all names from the legacy monolith so existing tests keep passing.
This file will be replaced with the full auto-discovery version in Task 2.
"""

from __future__ import annotations

# Re-export everything from the legacy monolith for backward compatibility
from odoo_gen_utils.preprocessors_legacy import *  # noqa: F401,F403
from odoo_gen_utils.preprocessors_legacy import (  # noqa: F401,E402
    _build_audit_log_model,
    _enrich_model_performance,
    _enrich_self_referential_m2m,
    _inject_legacy_security,
    _inject_one2many_links,
    _parse_crud,
    _process_approval_patterns,
    _process_audit_patterns,
    _process_computation_chains,
    _process_constraints,
    _process_notification_patterns,
    _process_performance,
    _process_production_patterns,
    _process_relationships,
    _process_security_patterns,
    _process_webhook_patterns,
    _resolve_comodel,
    _resolve_recipient,
    _security_auto_fix_views,
    _security_build_acl_matrix,
    _security_build_roles,
    _security_detect_record_rule_scopes,
    _security_enrich_fields,
    _security_validate_spec,
    _select_body_fields,
    _synthesize_through_model,
    _validate_no_cycles,
)
