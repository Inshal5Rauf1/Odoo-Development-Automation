"""Validation infrastructure for Odoo module quality checks."""

from odoo_gen_utils.validation.docker_runner import (  # noqa: F401
    check_docker_available,
    docker_install_module,
    docker_run_tests,
    get_compose_file,
)
from odoo_gen_utils.validation.error_patterns import (  # noqa: F401
    diagnose_errors,
    load_error_patterns,
)
from odoo_gen_utils.validation.log_parser import (  # noqa: F401
    extract_traceback,
    parse_install_log,
    parse_test_log,
)
from odoo_gen_utils.validation.pylint_runner import (  # noqa: F401
    parse_pylint_output,
    run_pylint_odoo,
)
from odoo_gen_utils.validation.report import (  # noqa: F401
    format_report_json,
    format_report_markdown,
)
from odoo_gen_utils.validation.types import (  # noqa: F401
    InstallResult,
    TestResult,
    ValidationReport,
    Violation,
)

__all__ = [
    "InstallResult",
    "TestResult",
    "ValidationReport",
    "Violation",
    "check_docker_available",
    "diagnose_errors",
    "docker_install_module",
    "docker_run_tests",
    "extract_traceback",
    "format_report_json",
    "format_report_markdown",
    "get_compose_file",
    "load_error_patterns",
    "parse_install_log",
    "parse_pylint_output",
    "parse_test_log",
    "run_pylint_odoo",
]
