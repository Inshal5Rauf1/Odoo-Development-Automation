"""Tests for the preprocessor decorator-based registry.

Phase 45: Registry mechanics, auto-discovery, ordering, and count tests.
"""

from __future__ import annotations

from typing import Any

import pytest

from odoo_gen_utils.preprocessors._registry import (
    PreprocessorFn,
    clear_registry,
    get_registered_preprocessors,
    register_preprocessor,
)


@pytest.fixture(autouse=True)
def _isolated_registry():
    """Clear registry before and after each test to prevent cross-contamination."""
    clear_registry()
    yield
    clear_registry()


# ---------------------------------------------------------------------------
# Registry mechanics tests
# ---------------------------------------------------------------------------


def test_register_adds_to_registry():
    """Registering a function makes it appear in get_registered_preprocessors."""

    @register_preprocessor(order=10)
    def _dummy(spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    entries = get_registered_preprocessors()
    assert len(entries) == 1
    assert entries[0][2] is _dummy


def test_ordering_by_order_param():
    """Entries are returned sorted by their order parameter."""

    @register_preprocessor(order=30)
    def _third(spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    @register_preprocessor(order=10)
    def _first(spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    @register_preprocessor(order=20)
    def _second(spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    entries = get_registered_preprocessors()
    assert len(entries) == 3
    orders = [e[0] for e in entries]
    assert orders == [10, 20, 30]
    assert entries[0][2] is _first
    assert entries[1][2] is _second
    assert entries[2][2] is _third


def test_clear_registry():
    """clear_registry empties the registry."""

    @register_preprocessor(order=1)
    def _dummy(spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    assert len(get_registered_preprocessors()) == 1
    clear_registry()
    assert len(get_registered_preprocessors()) == 0


def test_default_name_uses_function_name():
    """Without name= argument, the entry name is the function's __name__."""

    @register_preprocessor(order=1)
    def _my_preprocessor(spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    entries = get_registered_preprocessors()
    assert entries[0][1] == "_my_preprocessor"


def test_custom_name_overrides():
    """Providing name= overrides the default function name."""

    @register_preprocessor(order=1, name="custom_name")
    def _my_preprocessor(spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    entries = get_registered_preprocessors()
    assert entries[0][1] == "custom_name"


def test_decorator_returns_original_function():
    """The decorator is transparent -- returns the original function unchanged."""

    @register_preprocessor(order=1)
    def _my_fn(spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    # _my_fn should still be the original function object
    assert callable(_my_fn)
    result = _my_fn({"key": "value"})
    assert result == {"key": "value"}


def test_duplicate_orders_both_kept():
    """Duplicate order values are both kept (no deduplication)."""

    @register_preprocessor(order=10)
    def _first(spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    @register_preprocessor(order=10)
    def _second(spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    entries = get_registered_preprocessors()
    assert len(entries) == 2
