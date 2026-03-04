# Phase 17: Inline Environment Verification - Research

**Researched:** 2026-03-04
**Domain:** Python decorator/hook pattern over existing Jinja2 template renderer; OdooClient XML-RPC integration; warning emission vs blocking
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCP-03 | Inline Verification -- Model Generation | Verify `_inherit` base models and relational field comodel targets exist via OdooClient before `render_module()` writes files; warn on mismatch, degrade gracefully when MCP unavailable |
| MCP-04 | Inline Verification -- View Generation | Verify `<field name="X">` references in rendered XML views against live Odoo model schema; verify inherited view targets exist; warn on mismatch, degrade gracefully when MCP unavailable |
</phase_requirements>

## Summary

Phase 17 adds inline environment verification to the existing Jinja2 module generation pipeline. The pipeline lives in `python/src/odoo_gen_utils/renderer.py`, specifically in `render_module()` which drives all model and view file creation from a `spec` dictionary. The MCP server (`python/src/odoo_gen_utils/mcp/`) already provides the `OdooClient` XML-RPC wrapper with a `search_read` helper. This phase wires those two systems together by adding a `verifier.py` module that calls `OdooClient` directly (bypassing FastMCP stdio transport entirely -- the verifier calls the Python class, not the MCP tool protocol) and reports `VerificationWarning` objects back to the caller.

The key design insight is that the verifier is a **pure Python layer** that imports `OdooClient` directly. There is no need to spawn a subprocess or speak the MCP JSON-RPC protocol. The MCP server is only for Claude Code tool calls; the verifier is a library function. This eliminates transport overhead and simplifies testing: unit tests mock `OdooClient.search_read`, not the full MCP stack.

Verification is **non-blocking**: `render_module()` returns normally even when mismatches are found. Warnings are accumulated in a result object or returned as a list alongside the created files. When `OdooClient` raises any exception (Odoo unreachable, auth failure, network error), the verifier catches it and falls back to no-op behaviour -- generation proceeds as if the verifier were absent.

**Primary recommendation:** Add `python/src/odoo_gen_utils/verifier.py` with a `EnvironmentVerifier` class that holds an optional `OdooClient`, exposes `verify_model_spec()` and `verify_view_spec()` methods returning `list[VerificationWarning]`, and is wired into `render_module()` via an optional `verifier=` parameter. Keep all existing call sites unchanged (parameter defaults to `None`).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `odoo_gen_utils.mcp.odoo_client.OdooClient` | project | Direct XML-RPC to Odoo | Already built, tested (29 tests), single mock boundary -- reuse as-is |
| `dataclasses` (stdlib) | Python 3.12 | `VerificationWarning` dataclass | Zero-dependency; `@dataclass(frozen=True)` matches project immutability style |
| `logging` (stdlib) | Python 3.12 | Emit verification events to stderr | Consistent with MCP server pattern; no new dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest.mock` | Python 3.12 | Mock `OdooClient` in unit tests | Already used in `test_mcp_server.py`; same pattern here |
| `pytest` | >=8.0 | Test framework | Already installed (`python/.venv`) |
| `pytest-asyncio` | >=0.23 | Async test support | Already installed; keep `asyncio_mode=auto` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct `OdooClient` import | Call MCP tools via subprocess | Subprocess adds 200-500ms latency per check, requires server running; direct import is O(1) and testable |
| `VerificationWarning` dataclass | Plain `dict` | Dataclass gives type checking, immutability, structured fields; matches project coding-style.md |
| Accumulate warnings in list | Raise on first failure | List accumulation lets generation proceed (non-blocking requirement); raising blocks generation |

**Installation:** No new packages needed. All dependencies already present in `python/.venv`.

## Architecture Patterns

### Recommended Project Structure

```
python/src/odoo_gen_utils/
  verifier.py                  # NEW: EnvironmentVerifier + VerificationWarning
  renderer.py                  # MODIFY: wire verifier into render_module()
  mcp/
    odoo_client.py             # UNCHANGED: OdooClient reused directly
    server.py                  # UNCHANGED: MCP tools unchanged
python/tests/
  test_verifier.py             # NEW: unit tests for verifier (mocked OdooClient)
  test_renderer_verify.py      # NEW: integration tests for render_module + verifier
```

### Pattern 1: VerificationWarning Dataclass
**What:** An immutable dataclass capturing one mismatch found during verification.
**When to use:** Every time a check fails (model not found, field missing, etc.).
**Why:** Structured data enables the planner to filter, log, or format warnings differently. Immutable matches the project's coding-style.md.

```python
# Source: project coding-style.md + dataclasses stdlib
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationWarning:
    """One mismatch found during inline environment verification.

    Attributes:
        check_type: Category of check ('model_inherit', 'field_comodel',
                    'field_override', 'view_field', 'view_inherit_target').
        subject: The item being checked (model name, field name, etc.).
        message: Human-readable description of the mismatch.
        suggestion: Optional correction hint for the agent/user.
    """
    check_type: str
    subject: str
    message: str
    suggestion: str = ""
```

### Pattern 2: EnvironmentVerifier Class
**What:** A class that holds a (possibly None) `OdooClient` reference and exposes two verify methods. When client is None or raises, all methods return `[]` immediately.
**When to use:** Instantiate once per `render_module()` call, or share a singleton across calls if the same Odoo instance is used.
**Why:** The class encapsulates the graceful-degradation pattern in one place. Callers never need to guard against Odoo being unavailable.

```python
# Source: project conventions + MCP-03/04 requirements
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_gen_utils.mcp.odoo_client import OdooClient

logger = logging.getLogger("odoo-gen.verifier")


class EnvironmentVerifier:
    """Verifies spec declarations against the live Odoo instance.

    When the Odoo instance is unavailable, all methods return [] immediately
    (graceful degradation). Never raises -- all errors are caught and logged.

    Usage:
        verifier = EnvironmentVerifier(client)  # client may be None
        warnings = verifier.verify_model_spec(model_dict)
        warnings += verifier.verify_view_spec(model_name, field_names)
    """

    def __init__(self, client: "OdooClient | None" = None) -> None:
        self._client = client

    def _is_available(self) -> bool:
        """Return True if the Odoo client is configured and reachable."""
        return self._client is not None

    def verify_model_spec(self, model: dict) -> list[VerificationWarning]:
        """Verify model inheritance and relational field targets.

        Checks:
          - If model has _inherit: verify base model exists in ir.model
          - For each Many2one/One2many/Many2many field: verify comodel_name exists
          - If field overrides exist: verify original field exists with matching ttype

        Args:
            model: Single model dict from spec['models'] (as passed to renderer).

        Returns:
            List of VerificationWarning (empty list = all checks passed or MCP unavailable).
        """
        if not self._is_available():
            return []
        warnings: list[VerificationWarning] = []
        try:
            warnings.extend(self._check_inherit(model))
            warnings.extend(self._check_relational_comodels(model))
        except Exception as exc:
            logger.warning("MCP verification failed (degrading gracefully): %s", exc)
            return []
        return warnings

    def verify_view_spec(
        self,
        model_name: str,
        field_names: list[str],
        inherited_view_target: str | None = None,
    ) -> list[VerificationWarning]:
        """Verify view field references against live model schema.

        Checks:
          - Each field_name in field_names exists on model_name in Odoo
          - If inherited_view_target is given: verify that view XML id/model exists

        Args:
            model_name: Technical model name the view is for.
            field_names: List of field names referenced in the view XML.
            inherited_view_target: Optional view model name to verify exists.

        Returns:
            List of VerificationWarning (empty list = all checks passed or MCP unavailable).
        """
        if not self._is_available():
            return []
        warnings: list[VerificationWarning] = []
        try:
            warnings.extend(self._check_view_fields(model_name, field_names))
            if inherited_view_target:
                warnings.extend(self._check_view_target(inherited_view_target))
        except Exception as exc:
            logger.warning("MCP view verification failed (degrading gracefully): %s", exc)
            return []
        return warnings
```

### Pattern 3: Wiring into render_module()
**What:** Pass an optional `verifier` parameter to `render_module()`. Before writing each model file and each view file, call the verifier and accumulate warnings. Return warnings alongside the created file list.
**When to use:** Always in the new signature. Backward-compatible: existing callers that don't pass a verifier get the original behaviour (verifier defaults to None, all checks skipped).
**Why:** Minimal change to existing code. `render_module()` signature change is backward-compatible. No behaviour change for callers that don't opt in.

```python
# Source: renderer.py existing interface + Phase 17 requirements
def render_module(
    spec: dict[str, Any],
    template_dir: Path,
    output_dir: Path,
    verifier: "EnvironmentVerifier | None" = None,
) -> tuple[list[Path], list[VerificationWarning]]:
    """Render a complete Odoo module, optionally verifying against live Odoo.

    Returns:
        Tuple of (created_files, verification_warnings).
        verification_warnings is empty when verifier is None or Odoo unavailable.
    """
    ...
    all_warnings: list[VerificationWarning] = []

    for model in models:
        if verifier:
            all_warnings.extend(verifier.verify_model_spec(model))
        # existing render_template calls unchanged
        ...
        field_names = [f["name"] for f in model.get("fields", [])]
        if verifier:
            all_warnings.extend(
                verifier.verify_view_spec(model["name"], field_names)
            )

    return created_files, all_warnings
```

**NOTE:** The CLI (`cli.py` `render_module_cmd`) currently calls `render_module()` and unpacks only the file list. The CLI must be updated to handle the new tuple return. For CLI output, log warnings to stderr.

### Pattern 4: Creating OdooClient from Environment for render_module()
**What:** Factory function that reads env vars and returns an `OdooClient | None`. Returns `None` when ODOO_URL is not set or when client construction fails.
**When to use:** At CLI call site or wherever `render_module()` is invoked with verifier support.
**Why:** Keeps MCP availability opt-in. If the dev hasn't set ODOO_URL, verification silently skips.

```python
# Source: server.py _get_client() pattern adapted for verifier
import os
from odoo_gen_utils.mcp.odoo_client import OdooClient, OdooConfig


def build_verifier_from_env() -> "EnvironmentVerifier":
    """Build an EnvironmentVerifier from environment variables.

    Returns an EnvironmentVerifier with a connected OdooClient when ODOO_URL
    is set, or an EnvironmentVerifier with no client (no-op) otherwise.
    """
    url = os.environ.get("ODOO_URL")
    if not url:
        return EnvironmentVerifier(client=None)

    config = OdooConfig(
        url=url,
        db=os.environ.get("ODOO_DB", "odoo_dev"),
        username=os.environ.get("ODOO_USER", "admin"),
        api_key=os.environ.get("ODOO_API_KEY", "admin"),
    )
    try:
        client = OdooClient(config)
        return EnvironmentVerifier(client=client)
    except Exception:
        return EnvironmentVerifier(client=None)
```

### Pattern 5: Model Verification Implementation
**What:** Check `_inherit` and relational `comodel_name` values against `ir.model` via `search_read`.
**When to use:** Inside `verify_model_spec()`.
**Why:** `ir.model` is always present (base module), so these queries never fail due to missing tables. The search domain `[['model', '=', model_name]]` is an exact match -- either 1 result (exists) or 0 (doesn't exist).

```python
# Source: Odoo 17.0 External API + ir.model table structure
def _check_inherit(self, model: dict) -> list[VerificationWarning]:
    """Check that _inherit base models exist in the live Odoo instance."""
    warnings = []
    inherit = model.get("inherit")
    if not inherit:
        return []
    # inherit can be a string or already processed into inherit_list
    inherits = [inherit] if isinstance(inherit, str) else inherit
    for base_model in inherits:
        # Skip Odoo standard mixins (they're always present)
        if base_model in ("mail.thread", "mail.activity.mixin"):
            continue
        result = self._client.search_read(
            "ir.model",
            [["model", "=", base_model]],
            ["model", "name"],
            limit=1,
        )
        if not result:
            warnings.append(VerificationWarning(
                check_type="model_inherit",
                subject=base_model,
                message=(
                    f"Base model '{base_model}' not found in live Odoo instance. "
                    f"Ensure the module that defines '{base_model}' is installed."
                ),
                suggestion=(
                    f"Add the module that provides '{base_model}' to `depends` "
                    f"in __manifest__.py and install it in the dev instance."
                ),
            ))
        else:
            logger.info("MCP-03: _inherit check PASS: %s exists", base_model)
    return warnings


def _check_relational_comodels(self, model: dict) -> list[VerificationWarning]:
    """Check that relational field comodel_name targets exist."""
    warnings = []
    relational_types = {"Many2one", "One2many", "Many2many"}
    for field in model.get("fields", []):
        if field.get("type") not in relational_types:
            continue
        comodel = field.get("comodel_name")
        if not comodel:
            continue
        result = self._client.search_read(
            "ir.model",
            [["model", "=", comodel]],
            ["model"],
            limit=1,
        )
        if not result:
            warnings.append(VerificationWarning(
                check_type="field_comodel",
                subject=f"{model['name']}.{field['name']}",
                message=(
                    f"Relational field '{field['name']}' targets '{comodel}' "
                    f"which was not found in the live Odoo instance."
                ),
                suggestion=(
                    f"Verify the module providing '{comodel}' is listed in "
                    f"`depends` and installed in the dev instance."
                ),
            ))
        else:
            logger.info(
                "MCP-03: comodel check PASS: %s.%s -> %s exists",
                model["name"], field["name"], comodel,
            )
    return warnings
```

### Pattern 6: View Verification Implementation
**What:** Fetch model fields from `ir.model.fields` and diff against the field names in the spec. Return warnings for any fields in the spec that don't exist in Odoo.
**When to use:** Inside `verify_view_spec()`.
**Why:** `ir.model.fields` returns the exact set of fields on a model. The spec drives what field names appear in view XML. Diffing them catches typos and missing field additions.

```python
# Source: Odoo External API + ir.model.fields structure (same as get_model_fields tool)
def _check_view_fields(
    self, model_name: str, field_names: list[str]
) -> list[VerificationWarning]:
    """Check that field names referenced in views exist on the model."""
    warnings = []
    if not field_names:
        return []
    # Fetch all real fields for the model
    real_fields_data = self._client.search_read(
        "ir.model.fields",
        [["model", "=", model_name]],
        ["name"],
    )
    real_field_names = {f["name"] for f in real_fields_data}
    if not real_field_names:
        # Model doesn't exist in Odoo -- already caught by model verify
        return []
    for field_name in field_names:
        if field_name not in real_field_names:
            warnings.append(VerificationWarning(
                check_type="view_field",
                subject=f"{model_name}.{field_name}",
                message=(
                    f"View references field '{field_name}' on model '{model_name}' "
                    f"but that field was not found in the live Odoo instance."
                ),
                suggestion=(
                    f"Check that '{field_name}' is defined in the model spec "
                    f"and that the field exists in Odoo (correct spelling, correct model)."
                ),
            ))
        else:
            logger.info(
                "MCP-04: view field check PASS: %s.%s exists",
                model_name, field_name,
            )
    return warnings


def _check_view_target(self, target_model: str) -> list[VerificationWarning]:
    """Check that an inherited view target model has views in ir.ui.view."""
    result = self._client.search_read(
        "ir.ui.view",
        [["model", "=", target_model]],
        ["name"],
        limit=1,
    )
    if not result:
        return [VerificationWarning(
            check_type="view_inherit_target",
            subject=target_model,
            message=(
                f"Inherited view target model '{target_model}' has no views "
                f"in the live Odoo instance."
            ),
            suggestion=(
                f"Ensure the module providing '{target_model}' views is installed."
            ),
        )]
    return []
```

### Anti-Patterns to Avoid
- **Calling MCP tools via subprocess:** The verifier directly imports `OdooClient`, it does NOT spawn `python -m odoo_gen_utils.mcp.server`. Subprocess adds latency and requires the MCP server to be running separately.
- **Blocking generation on verification failure:** Return warnings in a list, never raise. The spec says "warnings, not blocks" (MCP-03, MCP-04).
- **Verifying mail.thread / mail.activity.mixin:** These are always present in any Odoo instance with `mail` installed. Skip them explicitly to avoid spurious warnings in base-only instances.
- **Using `fields_get` instead of `ir.model.fields`:** `fields_get` returns `{field_name: {type: ...}}` where the key is `type`, not `ttype`. `ir.model.fields` via `search_read` returns the consistent tabular format already used by `get_model_fields` MCP tool. Use `ir.model.fields` for consistency.
- **Re-authenticating per verification call:** `OdooClient` caches `uid` after first auth. Share one `OdooClient` instance across the entire `render_module()` call. Do not construct a new client per model.
- **Mutating the spec dict during verification:** Verification is read-only. Never mutate `model`, `field`, or `spec` dicts. Project coding-style.md mandates immutability.
- **Changing the `render_module()` return type to a new namedtuple without backward compat:** The CLI (`render_module_cmd`) currently unpacks the return value. Update CLI carefully or return `(list[Path], list[VerificationWarning])` tuple with a clear comment.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Odoo XML-RPC queries | Custom `xmlrpc.client.ServerProxy` calls in verifier | `OdooClient.search_read()` (already in mcp/odoo_client.py) | Already tested 29 times, handles auth, caching, error formatting |
| "Model exists" check | Query `ir.model` with raw ServerProxy | `OdooClient.search_read("ir.model", [["model", "=", name]], ["model"])` | OdooClient already wraps this pattern; don't duplicate |
| Warning data structure | `dict` with string keys | `@dataclass(frozen=True) VerificationWarning` | Type safety, immutability, structured fields for formatting |
| Graceful degradation | Try/except scattered throughout caller | Central `_is_available()` check + outer try/except in each verify method | Single responsibility; callers never need to guard |
| Test mocking | Spawn real Odoo for unit tests | `unittest.mock.MagicMock()` replacing `OdooClient` | Same pattern as `test_mcp_server.py` -- 0ms, deterministic |

**Key insight:** This phase is fundamentally a bridge module. `OdooClient` (Phase 16) + `renderer.py` (Phase 5) already exist. Phase 17 adds only the wiring between them in a thin `verifier.py` layer.

## Common Pitfalls

### Pitfall 1: Verifier Causes render_module() Signature Break
**What goes wrong:** `render_module()` currently returns `list[Path]`. Changing it to return `tuple[list[Path], list[VerificationWarning]]` breaks every existing call site, including `cli.py render_module_cmd` and all tests.
**Why it happens:** Python doesn't enforce return types at runtime; callers that unpack `for f in render_module(...)` will silently iterate over the tuple instead of the paths.
**How to avoid:** Update `cli.py render_module_cmd` and all test call sites in the same plan wave as the signature change. Run the full test suite (`cd python && python -m pytest`) after each change to catch breakage immediately.
**Warning signs:** Tests with `for f in render_module(...)` start failing with `AttributeError` or wrong types.

### Pitfall 2: Verifying New Module's Own Models Against Odoo
**What goes wrong:** The module being generated doesn't exist in Odoo yet. Verifying that the new model `my_custom.model` exists will always return a warning because it's not installed.
**Why it happens:** The requirement says verify TARGETS of `_inherit` and `comodel_name`, not the model being defined. But a naive implementation might also check the new model itself.
**How to avoid:** Only verify: (a) `_inherit` values, (b) `comodel_name` targets of relational fields. Never verify `model["name"]` (the model being defined). For view verification, only verify field names against the model that already exists in Odoo (for `_inherit` scenarios where the base model has known fields).
**Warning signs:** Every `render_module()` call returns a warning for the model being defined.

### Pitfall 3: View Field Verification for New Models
**What goes wrong:** When generating views for a completely new model (not inheriting), `_check_view_fields` queries `ir.model.fields` for the new model name. Since the new model isn't installed yet, `real_field_names` is empty, and `_check_view_fields` returns nothing (empty set diff). This is correct but easy to confuse with a model-not-found situation.
**Why it happens:** The verifier can't distinguish "model exists but has no fields" from "model doesn't exist" from `ir.model.fields` returning empty.
**How to avoid:** In `_check_view_fields`, if `real_field_names` is empty, skip ALL field checks (return []). Document this: "If the model doesn't exist in Odoo yet, we can't verify fields -- skip silently." View field verification is most valuable for `_inherit` scenarios where the base model fields are already known.
**Warning signs:** View field checks return [] for all models -- check that OdooClient is connected and that the base model is installed.

### Pitfall 4: Integration Tests Require Live Odoo
**What goes wrong:** Integration tests that call `verify_model_spec()` with a real `OdooClient` against the Phase 15 dev instance are Docker-dependent. If run in CI without the dev instance, they fail.
**Why it happens:** The Phase 15 dev instance is a local Docker service. CI typically doesn't have it running.
**How to avoid:** Mark integration tests with `@pytest.mark.docker` (existing marker). Unit tests use `MagicMock` only. Two separate test files: `test_verifier.py` (unit, no Docker) and optionally `test_verifier_integration.py` (docker, live instance).
**Warning signs:** CI fails with `ConnectionRefusedError: [Errno 111] Connection refused` on integration tests.

### Pitfall 5: Mocking OdooClient in verifier tests vs MCP tests
**What goes wrong:** In `test_mcp_server.py`, the mock patches `_get_client` in the server module. In `test_verifier.py`, the mock directly replaces the client passed to `EnvironmentVerifier.__init__`. These are different mock strategies and easy to confuse.
**Why it happens:** The verifier accepts an `OdooClient` instance directly -- no global singleton to patch. Pass a `MagicMock` as the `client` argument.
**How to avoid:** Use the constructor injection pattern (pass `MagicMock()` as `client=`). Don't try to patch `_get_client` in verifier tests -- it doesn't exist there.
**Warning signs:** Tests pass but don't actually test the verifier logic (mock is attached to the wrong object).

### Pitfall 6: Warning Deduplication
**What goes wrong:** If a `comodel_name` target is referenced by multiple fields in the same spec and doesn't exist, the verifier emits one warning per field. A spec with 5 Many2one fields pointing to the same missing model generates 5 near-identical warnings.
**Why it happens:** The per-field loop checks each field independently.
**How to avoid:** Collect already-checked model names in a set within `_check_relational_comodels`. Skip the MCP query if the model was already checked in this call.
**Warning signs:** Warning output is very long with duplicated messages for the same missing model.

## Code Examples

Verified patterns from official sources:

### Complete verifier.py (skeleton)
```python
# Source: Phase 16 OdooClient patterns + requirements MCP-03/04
"""Inline environment verifier for Odoo module generation.

Checks model inheritance, relational field targets, and view field references
against the live Odoo instance via OdooClient. Non-blocking: all errors return
VerificationWarning objects, never raise.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_gen_utils.mcp.odoo_client import OdooClient

logger = logging.getLogger("odoo-gen.verifier")

# Standard Odoo mixins always present when 'mail' module is installed.
# Skip inheritance checks for these to avoid spurious warnings on base-only instances.
_ALWAYS_PRESENT_MIXINS: frozenset[str] = frozenset({
    "mail.thread",
    "mail.activity.mixin",
})


@dataclass(frozen=True)
class VerificationWarning:
    """One mismatch found during inline environment verification."""
    check_type: str  # 'model_inherit' | 'field_comodel' | 'view_field' | 'view_inherit_target'
    subject: str     # model name, field name, or "model.field"
    message: str     # Human-readable description
    suggestion: str = ""  # Suggested correction


class EnvironmentVerifier:
    """Verifies spec declarations against the live Odoo instance.

    Pass client=None or omit to get a no-op verifier (all methods return []).
    All exceptions from OdooClient are caught; never raises.
    """

    def __init__(self, client: "OdooClient | None" = None) -> None:
        self._client = client

    def verify_model_spec(self, model: dict) -> list[VerificationWarning]:
        """Verify _inherit and relational field comodel_name targets."""
        if self._client is None:
            return []
        try:
            warnings = []
            warnings.extend(self._check_inherit(model))
            warnings.extend(self._check_relational_comodels(model))
            return warnings
        except Exception as exc:
            logger.warning("MCP-03 verification error (degrading): %s", exc)
            return []

    def verify_view_spec(
        self,
        model_name: str,
        field_names: list[str],
        inherited_view_target: str | None = None,
    ) -> list[VerificationWarning]:
        """Verify view field references against live model schema."""
        if self._client is None:
            return []
        try:
            warnings = []
            warnings.extend(self._check_view_fields(model_name, field_names))
            if inherited_view_target:
                warnings.extend(self._check_view_target(inherited_view_target))
            return warnings
        except Exception as exc:
            logger.warning("MCP-04 verification error (degrading): %s", exc)
            return []

    def _check_inherit(self, model: dict) -> list[VerificationWarning]:
        inherit = model.get("inherit")
        if not inherit:
            return []
        inherits = [inherit] if isinstance(inherit, str) else list(inherit)
        warnings = []
        for base_model in inherits:
            if base_model in _ALWAYS_PRESENT_MIXINS:
                continue
            result = self._client.search_read(
                "ir.model", [["model", "=", base_model]], ["model"], limit=1
            )
            if not result:
                warnings.append(VerificationWarning(
                    check_type="model_inherit",
                    subject=base_model,
                    message=f"Base model '{base_model}' not found in live Odoo instance.",
                    suggestion=f"Install the module that provides '{base_model}'.",
                ))
            else:
                logger.info("MCP-03 _inherit PASS: %s", base_model)
        return warnings

    def _check_relational_comodels(self, model: dict) -> list[VerificationWarning]:
        checked: set[str] = set()
        warnings = []
        for f in model.get("fields", []):
            if f.get("type") not in ("Many2one", "One2many", "Many2many"):
                continue
            comodel = f.get("comodel_name")
            if not comodel or comodel in checked:
                continue
            checked.add(comodel)
            result = self._client.search_read(
                "ir.model", [["model", "=", comodel]], ["model"], limit=1
            )
            if not result:
                warnings.append(VerificationWarning(
                    check_type="field_comodel",
                    subject=f"{model['name']}.{f['name']}",
                    message=f"Relational field '{f['name']}' targets '{comodel}' which was not found.",
                    suggestion=f"Install the module that provides '{comodel}'.",
                ))
            else:
                logger.info("MCP-03 comodel PASS: %s -> %s", f["name"], comodel)
        return warnings

    def _check_view_fields(
        self, model_name: str, field_names: list[str]
    ) -> list[VerificationWarning]:
        if not field_names:
            return []
        real_data = self._client.search_read(
            "ir.model.fields", [["model", "=", model_name]], ["name"]
        )
        real_names = {r["name"] for r in real_data}
        if not real_names:
            # Model not yet in Odoo -- skip (new model being generated)
            return []
        warnings = []
        for name in field_names:
            if name not in real_names:
                warnings.append(VerificationWarning(
                    check_type="view_field",
                    subject=f"{model_name}.{name}",
                    message=f"Field '{name}' not found on model '{model_name}' in live Odoo.",
                    suggestion=f"Check field spelling or ensure field is defined in the model.",
                ))
            else:
                logger.info("MCP-04 view field PASS: %s.%s", model_name, name)
        return warnings

    def _check_view_target(self, target_model: str) -> list[VerificationWarning]:
        result = self._client.search_read(
            "ir.ui.view", [["model", "=", target_model]], ["name"], limit=1
        )
        if not result:
            return [VerificationWarning(
                check_type="view_inherit_target",
                subject=target_model,
                message=f"Inherited view target '{target_model}' has no views in live Odoo.",
                suggestion=f"Install the module that provides views for '{target_model}'.",
            )]
        return []
```

### Unit Test Pattern for EnvironmentVerifier (test_verifier.py)
```python
# Source: test_mcp_server.py constructor-injection pattern adapted for EnvironmentVerifier
"""Unit tests for EnvironmentVerifier with mocked OdooClient."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest
from odoo_gen_utils.verifier import EnvironmentVerifier, VerificationWarning


@pytest.fixture
def mock_client():
    """Bare MagicMock substituting for OdooClient."""
    client = MagicMock()
    client.search_read.return_value = []
    return client


@pytest.fixture
def verifier(mock_client):
    return EnvironmentVerifier(client=mock_client)


class TestVerifierNoClient:
    """When client=None, all methods return []."""

    def test_no_client_verify_model_returns_empty(self):
        v = EnvironmentVerifier(client=None)
        result = v.verify_model_spec({"name": "my.model", "inherit": "hr.employee"})
        assert result == []

    def test_no_client_verify_view_returns_empty(self):
        v = EnvironmentVerifier(client=None)
        result = v.verify_view_spec("my.model", ["name", "employee_id"])
        assert result == []


class TestModelInheritCheck:
    def test_inherit_exists_returns_no_warnings(self, verifier, mock_client):
        mock_client.search_read.return_value = [{"model": "hr.employee"}]
        result = verifier.verify_model_spec({"name": "my.model", "inherit": "hr.employee"})
        assert result == []

    def test_inherit_missing_returns_warning(self, verifier, mock_client):
        mock_client.search_read.return_value = []
        result = verifier.verify_model_spec({"name": "my.model", "inherit": "missing.model"})
        assert len(result) == 1
        assert result[0].check_type == "model_inherit"
        assert "missing.model" in result[0].message

    def test_mail_thread_always_skipped(self, verifier, mock_client):
        result = verifier.verify_model_spec({
            "name": "my.model",
            "inherit": "mail.thread",
        })
        assert result == []
        mock_client.search_read.assert_not_called()


class TestRelationalComodelCheck:
    def test_many2one_comodel_exists(self, verifier, mock_client):
        mock_client.search_read.return_value = [{"model": "res.partner"}]
        model = {
            "name": "sale.order",
            "fields": [{"name": "partner_id", "type": "Many2one", "comodel_name": "res.partner"}],
        }
        result = verifier.verify_model_spec(model)
        assert result == []

    def test_many2one_comodel_missing(self, verifier, mock_client):
        mock_client.search_read.return_value = []
        model = {
            "name": "my.model",
            "fields": [{"name": "ref_id", "type": "Many2one", "comodel_name": "missing.model"}],
        }
        result = verifier.verify_model_spec(model)
        assert len(result) == 1
        assert result[0].check_type == "field_comodel"

    def test_duplicate_comodel_queried_once(self, verifier, mock_client):
        mock_client.search_read.return_value = [{"model": "res.partner"}]
        model = {
            "name": "my.model",
            "fields": [
                {"name": "partner_id", "type": "Many2one", "comodel_name": "res.partner"},
                {"name": "partner_id2", "type": "Many2one", "comodel_name": "res.partner"},
            ],
        }
        verifier.verify_model_spec(model)
        # search_read called only once for ir.model (de-duplicated)
        assert mock_client.search_read.call_count == 1


class TestViewFieldCheck:
    def test_all_fields_exist(self, verifier, mock_client):
        mock_client.search_read.return_value = [{"name": "name"}, {"name": "partner_id"}]
        result = verifier.verify_view_spec("sale.order", ["name", "partner_id"])
        assert result == []

    def test_missing_field_returns_warning(self, verifier, mock_client):
        mock_client.search_read.return_value = [{"name": "name"}]
        result = verifier.verify_view_spec("sale.order", ["name", "nonexistent_field"])
        assert len(result) == 1
        assert result[0].check_type == "view_field"
        assert "nonexistent_field" in result[0].message

    def test_model_not_in_odoo_skips_field_check(self, verifier, mock_client):
        """When model is new (not in Odoo), ir.model.fields returns [] -- skip silently."""
        mock_client.search_read.return_value = []
        result = verifier.verify_view_spec("new.model", ["name", "description"])
        assert result == []

    def test_odoo_error_degrades_gracefully(self, verifier, mock_client):
        mock_client.search_read.side_effect = ConnectionRefusedError("Odoo down")
        result = verifier.verify_view_spec("sale.order", ["name"])
        assert result == []


class TestIntegrationWithRenderModule:
    """Integration tests: render_module with a verifier -- mocked OdooClient."""

    def test_render_module_with_verifier_returns_warnings(self, tmp_path, mock_client):
        from odoo_gen_utils.renderer import render_module, get_template_dir
        mock_client.search_read.return_value = []  # all missing

        spec = {
            "module_name": "test_verify",
            "models": [{
                "name": "my.model",
                "inherit": "hr.employee",
                "fields": [{"name": "name", "type": "Char", "string": "Name"}],
            }],
        }
        verifier = EnvironmentVerifier(client=mock_client)
        files, warnings = render_module(spec, get_template_dir(), tmp_path, verifier=verifier)
        assert len(files) > 0  # generation proceeded
        assert any(w.check_type == "model_inherit" for w in warnings)

    def test_render_module_without_verifier_backward_compat(self, tmp_path):
        """render_module() without verifier still returns (files, []) tuple."""
        from odoo_gen_utils.renderer import render_module, get_template_dir
        spec = {
            "module_name": "test_noverify",
            "models": [{"name": "simple.model", "fields": []}],
        }
        files, warnings = render_module(spec, get_template_dir(), tmp_path)
        assert len(files) > 0
        assert warnings == []
```

### Integration Test: hr.employee Scenario (test_verifier_integration.py)
```python
# Source: MCP-03 acceptance criteria: "Integration test: generate model inheriting hr.employee -> verify MCP checks fire"
"""Integration test with live Odoo dev instance. Requires Docker dev instance running."""
import pytest
from odoo_gen_utils.mcp.odoo_client import OdooClient, OdooConfig
from odoo_gen_utils.verifier import EnvironmentVerifier, VerificationWarning


pytestmark = pytest.mark.docker


@pytest.fixture(scope="module")
def live_client():
    """OdooClient connected to Phase 15 dev instance."""
    config = OdooConfig(
        url="http://localhost:8069",
        db="odoo_dev",
        username="admin",
        api_key="admin",
    )
    return OdooClient(config)


@pytest.fixture(scope="module")
def live_verifier(live_client):
    return EnvironmentVerifier(client=live_client)


def test_hr_employee_inherit_passes(live_verifier):
    """MCP-03: Generating a model inheriting hr.employee fires MCP checks and passes."""
    model = {
        "name": "my.employee.extension",
        "inherit": "hr.employee",
        "fields": [{"name": "department_id", "type": "Many2one", "comodel_name": "hr.department"}],
    }
    warnings = live_verifier.verify_model_spec(model)
    # hr.employee and hr.department should exist in the dev instance
    assert warnings == [], f"Unexpected warnings: {warnings}"


def test_missing_model_inherit_fires_warning(live_verifier):
    """MCP-03: _inherit of nonexistent model produces model_inherit warning."""
    model = {
        "name": "my.model",
        "inherit": "definitely.nonexistent.model.xyz",
        "fields": [],
    }
    warnings = live_verifier.verify_model_spec(model)
    assert any(w.check_type == "model_inherit" for w in warnings)


def test_view_nonexistent_field_fires_warning(live_verifier):
    """MCP-04: View referencing nonexistent field on hr.employee raises warning."""
    warnings = live_verifier.verify_view_spec(
        "hr.employee",
        ["name", "totally_nonexistent_field_xyz_abc"],
    )
    assert any(w.check_type == "view_field" for w in warnings)


def test_view_existing_fields_pass(live_verifier):
    """MCP-04: View referencing known hr.employee fields produces no warnings."""
    # name and job_id are always on hr.employee in Odoo 17 CE
    warnings = live_verifier.verify_view_spec("hr.employee", ["name", "job_id"])
    assert warnings == []
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static Jinja2 generation (no live check) | Inline MCP-backed verification | Phase 17 (now) | Errors caught during generation, not during Docker validation |
| Verification via MCP tool protocol (JSON-RPC) | Direct OdooClient import | Phase 17 design decision | No subprocess, no latency, standard Python module import |
| All errors block generation | Warnings accumulate, generation proceeds | Phase 17 design decision | Respects MCP-03/04 "warnings not blocks" requirement |

**No deprecated patterns to navigate here.** The patterns from Phase 16 (OdooClient, `ir.model.fields`, `ir.model`) are all current.

## Open Questions

1. **render_module() return type change affects CLI**
   - What we know: `cli.py render_module_cmd` calls `render_module()` and iterates the result as a file list. Changing the return to a tuple will break this.
   - What's unclear: How to best surface warnings in the CLI -- print to stderr? Add a `--verify` flag?
   - Recommendation: In `render_module_cmd`, update to unpack `files, warnings = render_module(...)`. Print warnings to stderr with a `WARN:` prefix. Gate verifier construction on `ODOO_URL` env var presence.

2. **Field names extracted from view template vs spec**
   - What we know: `view_form.xml.j2` generates `<field name="{{ field.name }}"/>` for every field in `spec["models"][n]["fields"]`. So `field_names` for view verification = all field names in the model spec.
   - What's unclear: Whether view verification should check the rendered XML output (parse XML) or the spec dict directly (simpler).
   - Recommendation: Verify from the spec dict (field names from `model["fields"]`). This avoids XML parsing overhead and is simpler. The spec is the source of truth for what the view will contain.

3. **Verifier reuse across multiple models in one spec**
   - What we know: `render_module()` iterates over multiple models. One `OdooClient` connection is shared.
   - What's unclear: Whether to pass the verifier per-model or create it once outside the loop.
   - Recommendation: Create one `EnvironmentVerifier` before the model loop. Pass it into the loop. `OdooClient` caches auth; reusing it is correct and efficient.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio |
| Config file | `python/pyproject.toml` (existing, `asyncio_mode=auto`) |
| Quick run command | `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest tests/test_verifier.py -x` |
| Full suite command | `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest -m "not docker and not e2e"` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-03.1 | Before `_inherit`: verify base model exists via MCP | unit (mocked) | `cd python && python -m pytest tests/test_verifier.py::TestModelInheritCheck -x` | Wave 0 |
| MCP-03.2 | Before relational field: verify comodel_name exists | unit (mocked) | `cd python && python -m pytest tests/test_verifier.py::TestRelationalComodelCheck -x` | Wave 0 |
| MCP-03.3 | Verification results logged pass/fail per check | unit (mocked) | `cd python && python -m pytest tests/test_verifier.py -x -s` (check log output) | Wave 0 |
| MCP-03.4 | Generation proceeds with warnings (not blocking) | unit + integration | `cd python && python -m pytest tests/test_verifier.py::TestIntegrationWithRenderModule -x` | Wave 0 |
| MCP-03.5 | Graceful degradation when MCP unavailable | unit (mocked) | `cd python && python -m pytest tests/test_verifier.py::TestVerifierNoClient -x` | Wave 0 |
| MCP-03.6 | Integration: generate model inheriting hr.employee -> MCP checks fire | integration (docker) | `cd python && python -m pytest tests/test_verifier_integration.py::test_hr_employee_inherit_passes -x` | Wave 0 |
| MCP-04.1 | Before view: fetch model fields via MCP | unit (mocked) | `cd python && python -m pytest tests/test_verifier.py::TestViewFieldCheck -x` | Wave 0 |
| MCP-04.2 | Verify `<field name="X">` references real field | unit (mocked) | `cd python && python -m pytest tests/test_verifier.py::TestViewFieldCheck::test_missing_field_returns_warning -x` | Wave 0 |
| MCP-04.3 | Verify inherited view targets exist | unit (mocked) | `cd python && python -m pytest tests/test_verifier.py -k "view_target" -x` | Wave 0 |
| MCP-04.4 | Report mismatches as warnings with suggested corrections | unit (mocked) | `cd python && python -m pytest tests/test_verifier.py -x` (assert suggestion field) | Wave 0 |
| MCP-04.5 | Graceful degradation when MCP unavailable | unit (mocked) | `cd python && python -m pytest tests/test_verifier.py::TestViewFieldCheck::test_odoo_error_degrades_gracefully -x` | Wave 0 |
| MCP-04.6 | Integration: generate view referencing non-existent field -> warning raised | integration (docker) | `cd python && python -m pytest tests/test_verifier_integration.py::test_view_nonexistent_field_fires_warning -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest tests/test_verifier.py -x` (unit tests only, <10s)
- **Per wave merge:** `cd /home/inshal-rauf/Odoo_module_automation/python && python -m pytest -m "not docker and not e2e"` (full suite minus Docker and e2e)
- **Phase gate:** Full suite green (including docker integration tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `python/tests/test_verifier.py` -- covers MCP-03 and MCP-04 unit tests (all mocked)
- [ ] `python/tests/test_verifier_integration.py` -- covers MCP-03.6 and MCP-04.6 (docker-marked)
- [ ] `python/src/odoo_gen_utils/verifier.py` -- the module being tested

*(No framework gaps: pytest, pytest-asyncio, asyncio_mode=auto all already configured in pyproject.toml)*

## Sources

### Primary (HIGH confidence)
- Phase 16 RESEARCH.md (this project) - OdooClient, `ir.model.fields`, `ir.model`, `ir.ui.view` XML-RPC patterns, all verified against live Odoo 17 CE
- Phase 16 SUMMARY 01 (this project) - Confirmed `OdooClient.search_read()` works; 29 tests passing; lazy uid caching; `_models` attribute name
- `python/src/odoo_gen_utils/renderer.py` (this project, read directly) - `render_module()` existing signature, model context structure, field iteration patterns
- `python/src/odoo_gen_utils/templates/17.0/model.py.j2` (this project) - Confirms field types that need comodel checking: `Many2one`, `One2many`, `Many2many` use `comodel_name`
- `python/src/odoo_gen_utils/templates/17.0/view_form.xml.j2` (this project) - Confirms view field names come directly from `fields` list in spec
- `python/pyproject.toml` (this project) - `asyncio_mode=auto` already set, pytest markers already defined (`docker`)
- REQUIREMENTS.md (this project) - Exact acceptance criteria for MCP-03 and MCP-04

### Secondary (MEDIUM confidence)
- [Odoo 17.0 External API docs](https://odoo-master.readthedocs.io/en/master/api_integration.html) - `ir.model`, `ir.model.fields`, `ir.ui.view` queryable via external XML-RPC API (verified against live instance in Phase 16 Summary 02)

### Tertiary (LOW confidence)
- None -- all claims in this research are backed by either project source code or Phase 16 verified findings.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Direct reuse of Phase 16 OdooClient (29 tests, live-verified). No new dependencies.
- Architecture: HIGH - `render_module()` and template structures read directly from source. No assumptions.
- Pitfalls: HIGH - Derived from reading actual code (signature, field names, test patterns). Not theoretical.
- Test patterns: HIGH - Copied from existing `test_mcp_server.py` constructor-injection approach.

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (project-internal -- OdooClient stable, renderer stable, both in this repo)
