"""Immutable dataclasses for validation results."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Violation:
    """A single pylint-odoo violation."""

    file: str
    line: int
    column: int
    rule_code: str
    symbol: str
    severity: str
    message: str
    suggestion: str = ""


@dataclass(frozen=True)
class InstallResult:
    """Result of an Odoo module installation attempt."""

    success: bool
    log_output: str
    error_message: str = ""


@dataclass(frozen=True)
class TestResult:
    """Result of a single Odoo test case."""

    test_name: str
    passed: bool
    error_message: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class ValidationReport:
    """Complete validation report for an Odoo module."""

    module_name: str
    pylint_violations: tuple[Violation, ...] = ()
    install_result: InstallResult | None = None
    test_results: tuple[TestResult, ...] = ()
    diagnosis: tuple[str, ...] = ()
    docker_available: bool = True
