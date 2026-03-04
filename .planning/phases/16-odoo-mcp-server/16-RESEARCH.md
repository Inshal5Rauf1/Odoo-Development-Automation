# Phase 16: Odoo MCP Server - Research

**Researched:** 2026-03-04
**Domain:** MCP (Model Context Protocol) server with Odoo XML-RPC introspection
**Confidence:** HIGH

## Summary

Phase 16 builds an MCP server integrated into the odoo-gen Python codebase that exposes 6 tools for querying a live Odoo instance via XML-RPC. The server uses the official MCP Python SDK (`mcp` package, v1.9+) with the built-in `FastMCP` high-level API, which provides decorator-based tool registration, automatic schema generation from type hints/docstrings, and stdio transport for Claude Code integration.

The Odoo introspection layer uses Python stdlib `xmlrpc.client.ServerProxy` to call `execute_kw` on Odoo's `/xmlrpc/2/object` endpoint. Model metadata comes from two sources: (1) `ir.model` for listing models, and (2) `ir.model.fields` via `search_read` for field details (name, ttype, relation, required, readonly). View architecture is retrieved from `ir.ui.view` via `search_read` with the `arch` field. The `fields_get` method on any model provides an alternative introspection path. Module data comes from `ir.module.module`.

Testing uses the in-memory `Client` transport from the MCP SDK, which binds a `Client` directly to the `FastMCP` server instance without subprocess overhead. External XML-RPC calls are mocked with `unittest.mock.patch`. This yields fast, deterministic unit tests.

**Primary recommendation:** Use `mcp` (v1.9+) with `FastMCP` for the server framework, `xmlrpc.client.ServerProxy` for Odoo communication, synchronous tool functions (FastMCP handles the async wrapper), and the in-memory `Client` test pattern for unit tests with mocked XML-RPC.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCP-02 | Odoo MCP Server -- Model Introspection | Full research coverage: FastMCP server framework, 6 tool implementations (list_models, get_model_fields, list_installed_modules, check_module_dependency, get_view_arch, auth check), XML-RPC introspection patterns, error handling, testing strategy, Claude Code integration |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp` | >=1.9 | MCP server framework | Official MCP Python SDK by Anthropic; FastMCP built-in since 1.2; decorator-based tools; auto schema from type hints |
| `xmlrpc.client` (stdlib) | Python 3.12 | Odoo XML-RPC communication | Zero-dependency, Odoo's own docs use it, already proven in Phase 15 verify script |
| `pydantic` | >=2.12 (mcp dep) | Data validation and structured returns | Pulled in by mcp; use for typed tool responses |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | >=8.0 | Test framework | Already in project; used for all tests |
| `pytest-asyncio` | >=0.23 | Async test support | Required for testing FastMCP in-memory Client (async context manager) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `mcp` (official SDK) | `fastmcp` (standalone) | Standalone fastmcp is a superset with extras (v2 features), but the official `mcp` package includes FastMCP built-in and is lighter; use official SDK for stability |
| `xmlrpc.client` | `odoorpc` / `OdooRPC` | Third-party libs add abstraction but also dependency; stdlib is zero-dep, matches Phase 15, and is Odoo-documented |
| Pydantic models for returns | Plain dicts | Pydantic gives validation and clear schemas; tools returning dicts work too, but structured output is better for downstream agents |

**Installation:**
```bash
cd python && pip install "mcp>=1.9" pytest-asyncio
```

Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
mcp = [
    "mcp>=1.9",
]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]
```

## Architecture Patterns

### Recommended Project Structure
```
python/src/odoo_gen_utils/
  mcp/
    __init__.py          # Package init
    server.py            # FastMCP server instance + tool registrations
    odoo_client.py       # OdooClient class wrapping xmlrpc.client
    tools.py             # Tool function implementations (or inline in server.py)
python/tests/
  test_mcp_server.py     # Unit tests with mocked XML-RPC
```

### Pattern 1: OdooClient Wrapper Class
**What:** Encapsulate all XML-RPC communication in a single `OdooClient` class with `authenticate()`, `execute_kw()`, and convenience methods. The MCP server holds a reference to this client.
**When to use:** Always. Separating the XML-RPC layer from the MCP tool layer enables clean mocking in tests and reuse in Phase 17.
**Why:** Direct `xmlrpc.client.ServerProxy` calls scattered across tool functions make mocking painful and create coupling. A single client class is the mock boundary.

**Example:**
```python
# Source: Odoo 17.0 External API docs + project conventions
from __future__ import annotations

import xmlrpc.client
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OdooConfig:
    """Odoo connection configuration from environment variables."""
    url: str
    db: str
    username: str
    api_key: str


class OdooClient:
    """XML-RPC client for Odoo introspection.

    Wraps xmlrpc.client.ServerProxy for /xmlrpc/2/common and /xmlrpc/2/object.
    """

    def __init__(self, config: OdooConfig) -> None:
        self._config = config
        self._uid: int | None = None
        self._common = xmlrpc.client.ServerProxy(
            f"{config.url}/xmlrpc/2/common"
        )
        self._models = xmlrpc.client.ServerProxy(
            f"{config.url}/xmlrpc/2/object"
        )

    def authenticate(self) -> int:
        """Authenticate and cache uid. Raises on failure."""
        uid = self._common.authenticate(
            self._config.db,
            self._config.username,
            self._config.api_key,
            {},
        )
        if not uid:
            msg = (
                f"Authentication failed for {self._config.username}"
                f"@{self._config.db}"
            )
            raise ConnectionError(msg)
        self._uid = uid
        return uid

    @property
    def uid(self) -> int:
        if self._uid is None:
            self.authenticate()
        assert self._uid is not None
        return self._uid

    def execute_kw(
        self,
        model: str,
        method: str,
        args: list,
        kwargs: dict | None = None,
    ) -> object:
        """Call execute_kw on the Odoo object endpoint."""
        return self._models.execute_kw(
            self._config.db,
            self.uid,
            self._config.api_key,
            model,
            method,
            args,
            kwargs or {},
        )

    def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str],
        limit: int = 0,
    ) -> list[dict]:
        """Convenience wrapper for search_read."""
        kwargs: dict = {"fields": fields}
        if limit:
            kwargs["limit"] = limit
        return self.execute_kw(model, "search_read", [domain], kwargs)
```

### Pattern 2: FastMCP Server with Tool Decorators
**What:** Use `@mcp.tool()` decorator to register each introspection function. FastMCP auto-generates tool schemas from function signatures and docstrings.
**When to use:** For all 6 tools.
**Why:** The decorator pattern is the official MCP SDK approach. Type hints become JSON Schema parameters. Docstrings become tool descriptions for the LLM.

**Example:**
```python
# Source: Official MCP SDK docs (modelcontextprotocol.io)
import os
import logging
import sys

from mcp.server.fastmcp import FastMCP

# CRITICAL: Never use print() in stdio servers -- it corrupts JSON-RPC
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("odoo-mcp")

mcp = FastMCP("odoo-introspection")

# OdooClient is initialized lazily on first tool call
_client: OdooClient | None = None

def _get_client() -> OdooClient:
    """Get or create the OdooClient from environment variables."""
    global _client
    if _client is None:
        config = OdooConfig(
            url=os.environ.get("ODOO_URL", "http://localhost:8069"),
            db=os.environ.get("ODOO_DB", "odoo_dev"),
            username=os.environ.get("ODOO_USER", "admin"),
            api_key=os.environ.get("ODOO_API_KEY", "admin"),
        )
        _client = OdooClient(config)
    return _client

@mcp.tool()
def list_models(name_filter: str = "") -> list[dict]:
    """List all Odoo models. Optionally filter by model name substring.

    Args:
        name_filter: Optional substring to filter model names (e.g. 'sale')

    Returns:
        List of dicts with 'model' (technical name) and 'name' (description)
    """
    client = _get_client()
    domain = []
    if name_filter:
        domain = [["model", "ilike", name_filter]]
    return client.search_read(
        "ir.model", domain, ["model", "name"]
    )
```

### Pattern 3: Graceful Error Handling for Odoo Unreachable
**What:** Each tool catches `ConnectionRefusedError`, `xmlrpc.client.Fault`, `OSError`, and `socket.timeout`, returning a structured error message instead of crashing.
**When to use:** Every tool function. Required by MCP-02 acceptance criteria.
**Why:** The MCP server process must not crash when Odoo is down. FastMCP surfaces tool return values to the LLM, so returning an error dict is the standard pattern.

**Example:**
```python
import xmlrpc.client

@mcp.tool()
def list_models(name_filter: str = "") -> str:
    """List all Odoo models..."""
    try:
        client = _get_client()
        domain = [["model", "ilike", name_filter]] if name_filter else []
        results = client.search_read("ir.model", domain, ["model", "name"])
        # Format for LLM consumption
        lines = [f"- {r['model']}: {r['name']}" for r in results]
        return f"Found {len(results)} models:\n" + "\n".join(lines)
    except (ConnectionRefusedError, OSError) as exc:
        return f"ERROR: Cannot connect to Odoo: {exc}"
    except xmlrpc.client.Fault as exc:
        return f"ERROR: Odoo XML-RPC fault: {exc.faultString}"
```

### Pattern 4: Environment Variable Configuration
**What:** Read ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY from environment. Defaults match the Phase 15 dev instance (localhost:8069, odoo_dev, admin, admin).
**When to use:** Always. Required by MCP-02.
**Why:** MCP servers launched via stdio receive env vars from the client configuration (Claude Code's `mcpServers.env` field). This is the standard pattern for MCP credential injection.

### Anti-Patterns to Avoid
- **Using `print()` in stdio server:** Corrupts JSON-RPC protocol. Use `logging` to stderr or `ctx.info()`.
- **Creating ServerProxy per tool call:** Opening XML-RPC connections is not free. Create once in OdooClient, reuse across calls.
- **Exposing raw XML-RPC responses to LLM:** XML-RPC returns Python dicts with integer IDs and nested tuples. Format results as human-readable strings or clean dicts.
- **Not caching authentication:** `authenticate()` is an RPC call. Cache the uid after first call.
- **Mixing async and sync XML-RPC:** `xmlrpc.client` is synchronous. Do not wrap in async without threading. FastMCP handles sync tool functions correctly via `anyio.to_thread`.
- **Hardcoding credentials in source:** Use env vars exclusively. The `OdooConfig` dataclass reads from `os.environ`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP protocol implementation | Custom JSON-RPC over stdio | `mcp` package (FastMCP) | Handles protocol negotiation, schema generation, transport, and error framing |
| Tool schema generation | Manual JSON Schema dicts | FastMCP `@mcp.tool()` with type hints | Decorator auto-generates from function signature and docstring |
| XML-RPC client | Custom HTTP+XML parser | `xmlrpc.client.ServerProxy` (stdlib) | Battle-tested, Odoo-documented, zero dependencies |
| Data validation for tool params | Manual type checking | Pydantic (comes with mcp) or FastMCP type inference | Automatic validation, clear error messages |
| MCP server testing harness | Custom subprocess + socket | FastMCP in-memory `Client` transport | No subprocess overhead, direct Python calls, async context manager |

**Key insight:** The `mcp` package provides everything needed for the server layer. The only custom code is the `OdooClient` wrapper and the 6 tool functions that map Odoo XML-RPC calls to MCP tool responses.

## Common Pitfalls

### Pitfall 1: print() in STDIO Server Corrupts Protocol
**What goes wrong:** Using `print()` writes to stdout, which is the JSON-RPC transport channel. Any stray stdout output corrupts the protocol framing and the client receives malformed JSON.
**Why it happens:** Python defaults `print()` to stdout. Developers add debug prints without thinking about the transport.
**How to avoid:** Use `logging.basicConfig(stream=sys.stderr)` and `logger.info()` for all diagnostics. Or use FastMCP's `Context.info()` / `Context.debug()` methods.
**Warning signs:** Client shows "parse error" or "connection closed"; tools return no results despite server running.

### Pitfall 2: XML-RPC Fault from Missing Model or Permission
**What goes wrong:** Querying a model that doesn't exist (e.g., `hr.employee` in a base-only instance) raises `xmlrpc.client.Fault` with a traceback string, not a clean error.
**Why it happens:** Odoo's `execute_kw` raises `psycopg2.ProgrammingError` or `odoo.exceptions.AccessError` which gets wrapped in an XML-RPC fault.
**How to avoid:** Catch `xmlrpc.client.Fault` in every tool, extract `faultString`, and return a user-readable error. For `list_models`/`get_model_fields`, the models queried (`ir.model`, `ir.model.fields`) are always available because they're part of the `base` module.
**Warning signs:** Tool returns a Python traceback as a string; LLM tries to interpret the traceback as data.

### Pitfall 3: fields_get vs ir.model.fields -- Two Introspection Paths
**What goes wrong:** Using `fields_get` on a model returns field metadata keyed by field name, but the keys/structure differ from `ir.model.fields` records. Mixing the two creates inconsistent data shapes.
**Why it happens:** `fields_get` is a method on every model (returns `{field_name: {type, string, ...}}`). `ir.model.fields` is a separate model where each record has `name`, `ttype`, `relation`, `required`, `readonly` columns.
**How to avoid:** Use `ir.model.fields` via `search_read` for the `get_model_fields` tool. It returns exactly the fields needed (name, ttype, relation, required, readonly) in a consistent tabular format. Use `fields_get` only if you need the field metadata in the context of a specific model instance.
**Warning signs:** Field type key is `type` in fields_get but `ttype` in ir.model.fields; mixing causes KeyError.

### Pitfall 4: ir.ui.view arch Field Contains Combined/Inherited XML
**What goes wrong:** The `arch` field on `ir.ui.view` for inherited views contains the XPATH expressions, not the full rendered view. To get the combined view, you need `get_view()` or `get_views()` on the model, not `search_read` on `ir.ui.view`.
**Why it happens:** Odoo stores view inheritance as XPATH patches in `ir.ui.view` records. The final rendered view is computed at runtime.
**How to avoid:** For `get_view_arch`, use `search_read` on `ir.ui.view` with the `arch` field. This gives the raw view definition (including XPATH for inherited views). This is actually MORE useful for code generation than the combined view, because generators need to know the XPATH structure. Document this in the tool description.
**Warning signs:** View XML contains `<xpath expr="..." position="...">` instead of full form/tree elements.

### Pitfall 5: Lazy Authentication Failure Appears as Tool Error
**What goes wrong:** The OdooClient authenticates lazily on first tool call. If credentials are wrong, the first tool call fails with a confusing error rather than failing at server startup.
**Why it happens:** MCP servers start before any tool is called. If auth happens at startup and fails, the server never starts, which is worse (Claude Code shows "connection closed").
**How to avoid:** Keep lazy auth. Add a dedicated `check_connection` tool that agents call first to verify connectivity. Return a clear error message distinguishing auth failure from connection failure.
**Warning signs:** First tool call returns "Authentication failed" but subsequent calls work after fixing env vars (requires server restart).

### Pitfall 6: Large Result Sets from list_models
**What goes wrong:** An Odoo instance with many modules has 500+ models. Returning all of them as a single tool response can exceed MCP output limits (10K tokens warning, 25K default max).
**Why it happens:** `ir.model` in a fully-loaded Odoo 17 instance with sale, purchase, hr, account has hundreds of models.
**How to avoid:** Add a `name_filter` parameter to `list_models` so agents can narrow results. Also add `limit` parameter with sensible default (100). Document the filtering in the tool description.
**Warning signs:** Tool response triggers MCP output warning; LLM truncates or ignores the response.

## Code Examples

Verified patterns from official sources:

### Complete MCP Server (server.py)
```python
# Source: Official MCP SDK docs + Odoo 17.0 External API
"""Odoo MCP server for model introspection.

Exposes tools for querying model schemas, field definitions,
installed modules, and view architectures from a live Odoo instance.

Transport: stdio (for Claude Code integration)
"""
from __future__ import annotations

import logging
import os
import sys
import xmlrpc.client
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

# Configure logging to stderr (stdout is the JSON-RPC transport)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("odoo-mcp")

mcp = FastMCP("odoo-introspection")


@dataclass(frozen=True)
class OdooConfig:
    url: str
    db: str
    username: str
    api_key: str


class OdooClient:
    """Wraps XML-RPC calls to Odoo. Single mock boundary for tests."""

    def __init__(self, config: OdooConfig) -> None:
        self._config = config
        self._uid: int | None = None
        self._common = xmlrpc.client.ServerProxy(
            f"{config.url}/xmlrpc/2/common"
        )
        self._object = xmlrpc.client.ServerProxy(
            f"{config.url}/xmlrpc/2/object"
        )

    def authenticate(self) -> int:
        uid = self._common.authenticate(
            self._config.db, self._config.username,
            self._config.api_key, {},
        )
        if not uid:
            raise ConnectionError(
                f"Odoo auth failed for {self._config.username}@{self._config.db}"
            )
        self._uid = uid
        return uid

    @property
    def uid(self) -> int:
        if self._uid is None:
            self.authenticate()
        assert self._uid is not None
        return self._uid

    def execute_kw(self, model: str, method: str, args: list,
                   kwargs: dict | None = None) -> object:
        return self._object.execute_kw(
            self._config.db, self.uid, self._config.api_key,
            model, method, args, kwargs or {},
        )

    def search_read(self, model: str, domain: list,
                    fields: list[str], limit: int = 0) -> list[dict]:
        kw: dict = {"fields": fields}
        if limit:
            kw["limit"] = limit
        return self.execute_kw(model, "search_read", [domain], kw)


# -- Client lifecycle -------------------------------------------------

_client: OdooClient | None = None


def _get_client() -> OdooClient:
    global _client
    if _client is None:
        config = OdooConfig(
            url=os.environ.get("ODOO_URL", "http://localhost:8069"),
            db=os.environ.get("ODOO_DB", "odoo_dev"),
            username=os.environ.get("ODOO_USER", "admin"),
            api_key=os.environ.get("ODOO_API_KEY", "admin"),
        )
        _client = OdooClient(config)
        logger.info("OdooClient created for %s", config.url)
    return _client


def _handle_error(exc: Exception) -> str:
    """Format exception as a tool-safe error string."""
    if isinstance(exc, ConnectionRefusedError | OSError):
        return f"ERROR: Cannot connect to Odoo instance: {exc}"
    if isinstance(exc, xmlrpc.client.Fault):
        return f"ERROR: Odoo XML-RPC fault: {exc.faultString}"
    if isinstance(exc, ConnectionError):
        return f"ERROR: {exc}"
    return f"ERROR: Unexpected error: {exc}"


# -- Tools -----------------------------------------------------------

@mcp.tool()
def check_connection() -> str:
    """Check connectivity and authentication to the Odoo instance.

    Returns server version and authenticated user info, or an error message.
    """
    try:
        client = _get_client()
        version = client._common.version()
        uid = client.uid  # triggers auth if needed
        return (
            f"Connected to Odoo {version.get('server_version', '?')} "
            f"at {client._config.url}, authenticated as uid={uid}"
        )
    except Exception as exc:
        return _handle_error(exc)


@mcp.tool()
def list_models(name_filter: str = "", limit: int = 100) -> str:
    """List Odoo models. Optionally filter by model name substring.

    Args:
        name_filter: Substring to filter model technical names (e.g. 'sale')
        limit: Maximum number of models to return (default 100, 0 for all)
    """
    try:
        client = _get_client()
        domain = [["model", "ilike", name_filter]] if name_filter else []
        results = client.search_read("ir.model", domain, ["model", "name"],
                                     limit=limit)
        lines = [f"- {r['model']}: {r['name']}" for r in results]
        return f"Found {len(results)} models:\n" + "\n".join(lines)
    except Exception as exc:
        return _handle_error(exc)


@mcp.tool()
def get_model_fields(model_name: str) -> str:
    """Get field definitions for an Odoo model.

    Args:
        model_name: Technical model name (e.g. 'res.partner', 'sale.order')

    Returns field name, type, relation (for relational fields), required, readonly.
    """
    try:
        client = _get_client()
        fields = client.search_read(
            "ir.model.fields",
            [["model", "=", model_name]],
            ["name", "ttype", "relation", "required", "readonly",
             "field_description"],
        )
        if not fields:
            return f"No fields found for model '{model_name}'. Does it exist?"
        lines = []
        for f in fields:
            rel = f" -> {f['relation']}" if f.get("relation") else ""
            req = " [required]" if f.get("required") else ""
            ro = " [readonly]" if f.get("readonly") else ""
            lines.append(
                f"- {f['name']} ({f['ttype']}{rel}){req}{ro}"
                f"  # {f.get('field_description', '')}"
            )
        return (
            f"Fields for {model_name} ({len(fields)} fields):\n"
            + "\n".join(lines)
        )
    except Exception as exc:
        return _handle_error(exc)


@mcp.tool()
def list_installed_modules() -> str:
    """List all installed Odoo modules with their versions."""
    try:
        client = _get_client()
        modules = client.search_read(
            "ir.module.module",
            [["state", "=", "installed"]],
            ["name", "installed_version", "shortdesc"],
        )
        lines = [
            f"- {m['name']} v{m.get('installed_version', '?')}"
            f"  ({m.get('shortdesc', '')})"
            for m in modules
        ]
        return (
            f"Installed modules ({len(modules)}):\n" + "\n".join(lines)
        )
    except Exception as exc:
        return _handle_error(exc)


@mcp.tool()
def check_module_dependency(module_name: str) -> str:
    """Check if a specific module is installed in the Odoo instance.

    Args:
        module_name: Technical module name (e.g. 'sale', 'hr', 'account')
    """
    try:
        client = _get_client()
        result = client.search_read(
            "ir.module.module",
            [["name", "=", module_name]],
            ["name", "state", "installed_version"],
        )
        if not result:
            return f"Module '{module_name}' not found in the Odoo instance."
        mod = result[0]
        if mod["state"] == "installed":
            return (
                f"Module '{module_name}' is INSTALLED "
                f"(version {mod.get('installed_version', '?')})"
            )
        return (
            f"Module '{module_name}' exists but is NOT installed "
            f"(state: {mod['state']})"
        )
    except Exception as exc:
        return _handle_error(exc)


@mcp.tool()
def get_view_arch(
    model_name: str,
    view_type: str = "",
) -> str:
    """Get XML view architecture for an Odoo model.

    Args:
        model_name: Technical model name (e.g. 'res.partner')
        view_type: Optional view type filter ('form', 'tree', 'kanban', 'search')

    Returns the raw XML architecture from ir.ui.view records.
    For inherited views, this includes XPATH expressions.
    """
    try:
        client = _get_client()
        domain: list = [["model", "=", model_name]]
        if view_type:
            domain.append(["type", "=", view_type])
        views = client.search_read(
            "ir.ui.view", domain,
            ["name", "type", "arch", "inherit_id"],
        )
        if not views:
            return (
                f"No views found for model '{model_name}'"
                + (f" of type '{view_type}'" if view_type else "")
            )
        parts = []
        for v in views:
            inherit = (
                f" (inherits: {v['inherit_id'][1]})"
                if v.get("inherit_id") else ""
            )
            parts.append(
                f"### {v['name']} ({v['type']}{inherit})\n"
                f"```xml\n{v.get('arch', '')}\n```"
            )
        return (
            f"Views for {model_name} ({len(views)} views):\n\n"
            + "\n\n".join(parts)
        )
    except Exception as exc:
        return _handle_error(exc)


# -- Entry point -----------------------------------------------------

def main() -> None:
    """Run the MCP server on stdio transport."""
    logger.info("Starting Odoo MCP server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

### Unit Test with Mocked XML-RPC (test_mcp_server.py)
```python
# Source: FastMCP testing guide (gofastmcp.com/servers/testing)
"""Unit tests for Odoo MCP server with mocked XML-RPC responses."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# Async test configuration
pytestmark = pytest.mark.asyncio(mode="auto")


@pytest.fixture
def mock_client():
    """Create a mock OdooClient that returns canned responses."""
    client = MagicMock()
    client._config = MagicMock()
    client._config.url = "http://localhost:8069"
    client.uid = 2
    client._common = MagicMock()
    client._common.version.return_value = {"server_version": "17.0"}
    return client


@pytest.fixture
def patched_get_client(mock_client):
    """Patch _get_client to return our mock."""
    with patch(
        "odoo_gen_utils.mcp.server._get_client",
        return_value=mock_client,
    ):
        yield mock_client


@pytest.fixture
async def mcp_client(patched_get_client):
    """Create an in-memory MCP client connected to our server."""
    from mcp.client import Client

    # Import AFTER patching so the server module uses the mock
    from odoo_gen_utils.mcp.server import mcp as server

    async with Client(transport=server) as client:
        yield client


async def test_list_tools(mcp_client):
    """Server should expose exactly 6 tools."""
    tools = await mcp_client.list_tools()
    tool_names = {t.name for t in tools}
    assert tool_names == {
        "check_connection",
        "list_models",
        "get_model_fields",
        "list_installed_modules",
        "check_module_dependency",
        "get_view_arch",
    }


async def test_check_connection(mcp_client, mock_client):
    """check_connection should return version and uid info."""
    result = await mcp_client.call_tool("check_connection", {})
    # Result content is a list of TextContent objects
    text = result[0].text
    assert "17.0" in text
    assert "uid=2" in text


async def test_list_models(mcp_client, mock_client):
    """list_models should format ir.model search_read results."""
    mock_client.search_read.return_value = [
        {"model": "res.partner", "name": "Contact"},
        {"model": "sale.order", "name": "Sales Order"},
    ]
    result = await mcp_client.call_tool("list_models", {"name_filter": ""})
    text = result[0].text
    assert "res.partner" in text
    assert "sale.order" in text
    assert "Found 2 models" in text


async def test_get_model_fields(mcp_client, mock_client):
    """get_model_fields should return field details."""
    mock_client.search_read.return_value = [
        {
            "name": "name",
            "ttype": "char",
            "relation": False,
            "required": True,
            "readonly": False,
            "field_description": "Name",
        },
        {
            "name": "partner_id",
            "ttype": "many2one",
            "relation": "res.partner",
            "required": False,
            "readonly": False,
            "field_description": "Partner",
        },
    ]
    result = await mcp_client.call_tool(
        "get_model_fields", {"model_name": "sale.order"}
    )
    text = result[0].text
    assert "name (char)" in text
    assert "partner_id (many2one -> res.partner)" in text
    assert "[required]" in text


async def test_connection_error(mcp_client, mock_client):
    """Tools should return error string when Odoo is unreachable."""
    mock_client.search_read.side_effect = ConnectionRefusedError(
        "Connection refused"
    )
    result = await mcp_client.call_tool("list_models", {})
    text = result[0].text
    assert "ERROR" in text
    assert "Cannot connect" in text
```

### Claude Code Configuration (.mcp.json)
```json
{
  "mcpServers": {
    "odoo-introspection": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "odoo_gen_utils.mcp.server"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "odoo_dev",
        "ODOO_USER": "admin",
        "ODOO_API_KEY": "admin"
      }
    }
  }
}
```

Or via CLI:
```bash
claude mcp add --transport stdio \
  --env ODOO_URL=http://localhost:8069 \
  --env ODOO_DB=odoo_dev \
  --env ODOO_USER=admin \
  --env ODOO_API_KEY=admin \
  odoo-introspection -- python -m odoo_gen_utils.mcp.server
```

### Odoo XML-RPC Introspection Patterns
```python
# Source: Odoo 17.0 External API docs + Odoo forum

# 1. List all models
models_list = client.search_read(
    "ir.model", [], ["model", "name"]
)
# Returns: [{"model": "res.partner", "name": "Contact"}, ...]

# 2. Get fields for a model via ir.model.fields
fields = client.search_read(
    "ir.model.fields",
    [["model", "=", "res.partner"]],
    ["name", "ttype", "relation", "required", "readonly", "field_description"],
)
# Returns: [{"name": "name", "ttype": "char", "relation": False, ...}, ...]
# Note: ttype (not type) -- the column name in ir.model.fields

# 3. Alternative: fields_get on the model directly
fields_meta = client.execute_kw(
    "res.partner", "fields_get", [],
    {"attributes": ["string", "help", "type", "required", "readonly", "relation"]},
)
# Returns: {"name": {"type": "char", "string": "Name", ...}, ...}
# Note: key is "type" (not ttype) when using fields_get

# 4. List installed modules
modules = client.search_read(
    "ir.module.module",
    [["state", "=", "installed"]],
    ["name", "installed_version", "shortdesc"],
)

# 5. Check specific module
result = client.search_read(
    "ir.module.module",
    [["name", "=", "hr"], ["state", "=", "installed"]],
    ["name", "state"],
)
# Returns: [] if not installed, [{"name": "hr", "state": "installed"}] if installed

# 6. Get view architecture
views = client.search_read(
    "ir.ui.view",
    [["model", "=", "res.partner"], ["type", "=", "form"]],
    ["name", "type", "arch", "inherit_id"],
)
# Returns: [{"name": "res.partner.form", "arch": "<form>...</form>", ...}]
# inherit_id is False for root views, (id, name) tuple for inherited views
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Low-level MCP Server class | FastMCP decorator API | 2024 (SDK 1.2) | 10x less boilerplate; auto schema generation |
| Standalone `fastmcp` package | Built into `mcp` package | 2024 (SDK 1.2+) | Single dependency: `pip install mcp` |
| SSE transport for clients | HTTP Streamable transport | 2025-2026 | SSE deprecated; but stdio still recommended for local tools |
| `xmlrpclib` (Python 2) | `xmlrpc.client` (Python 3) | Python 3.0 | Renamed; identical API |
| JSON-RPC for Odoo external API | XML-RPC or JSON-RPC (both supported) | Odoo 8+ | XML-RPC is simpler for Python (stdlib), more documented |
| Custom test harnesses for MCP | In-memory `Client(transport=server)` | FastMCP 1.x | No subprocess, fast, deterministic tests |

**Deprecated/outdated:**
- `fastmcp` standalone package: Still maintained, but for most use cases `mcp` package with built-in FastMCP is sufficient
- SSE transport: Deprecated in favor of HTTP Streamable; stdio remains recommended for local tools
- `xmlrpclib` (Python 2 name): Use `xmlrpc.client`

## Open Questions

1. **Exact mcp package version constraint**
   - What we know: v1.9.4+ has session management fixes; v1.26.0 is latest on PyPI. Requires Python >=3.10.
   - What's unclear: Whether v1.9 is the minimum that reliably supports in-memory Client testing. Need to verify during implementation.
   - Recommendation: Pin `mcp>=1.9` in pyproject.toml. If test issues arise, bump to latest stable.

2. **In-memory Client import path**
   - What we know: FastMCP docs show `from fastmcp.client import Client` (standalone package). Official mcp SDK may use `from mcp.client import Client`.
   - What's unclear: Exact import path for the in-memory testing Client in the official `mcp` package.
   - Recommendation: Try `from mcp.client import Client` first. If not available, fall back to direct function calls on the `mcp` FastMCP instance for testing.

3. **ir.ui.view arch field accessibility via XML-RPC**
   - What we know: The `arch` field is a computed field in Odoo. `search_read` on `ir.ui.view` with `fields=["arch"]` should return the XML.
   - What's unclear: Whether computed fields like `arch` are always readable via XML-RPC external API, or if some security rules block it.
   - Recommendation: Test against the Phase 15 dev instance during implementation. If `arch` is not readable, try `arch_db` (the stored field).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio |
| Config file | `python/pyproject.toml` (existing, add asyncio_mode) |
| Quick run command | `cd python && python -m pytest tests/test_mcp_server.py -x` |
| Full suite command | `cd python && python -m pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-02.1 | MCP server exposes 6 tools | unit (mocked) | `cd python && python -m pytest tests/test_mcp_server.py::test_list_tools -x` | Wave 0 |
| MCP-02.2 | list_models returns model name + description | unit (mocked) | `cd python && python -m pytest tests/test_mcp_server.py::test_list_models -x` | Wave 0 |
| MCP-02.3 | get_model_fields returns name, type, relation, required, readonly | unit (mocked) | `cd python && python -m pytest tests/test_mcp_server.py::test_get_model_fields -x` | Wave 0 |
| MCP-02.4 | list_installed_modules returns names and versions | unit (mocked) | `cd python && python -m pytest tests/test_mcp_server.py::test_list_installed_modules -x` | Wave 0 |
| MCP-02.5 | check_module_dependency verifies installed state | unit (mocked) | `cd python && python -m pytest tests/test_mcp_server.py::test_check_module_dependency -x` | Wave 0 |
| MCP-02.6 | get_view_arch retrieves XML view architecture | unit (mocked) | `cd python && python -m pytest tests/test_mcp_server.py::test_get_view_arch -x` | Wave 0 |
| MCP-02.7 | check_connection returns version and auth info | unit (mocked) | `cd python && python -m pytest tests/test_mcp_server.py::test_check_connection -x` | Wave 0 |
| MCP-02.8 | Graceful error when Odoo unreachable | unit (mocked) | `cd python && python -m pytest tests/test_mcp_server.py::test_connection_error -x` | Wave 0 |
| MCP-02.9 | Auth via env vars (ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY) | unit | `cd python && python -m pytest tests/test_mcp_server.py::test_config_from_env -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && python -m pytest tests/test_mcp_server.py -x` (quick: mocked tests, <5s)
- **Per wave merge:** `cd python && python -m pytest -m "not docker"` (full suite minus Docker)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `python/tests/test_mcp_server.py` -- covers MCP-02 (all 6 tools + auth check + error handling)
- [ ] `pytest-asyncio` dependency -- needed for async MCP client tests
- [ ] `asyncio_mode = "auto"` in pyproject.toml pytest config -- eliminates need for per-test async markers

## Sources

### Primary (HIGH confidence)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - FastMCP built-in, `@mcp.tool()` decorator, stdio transport, testing patterns
- [MCP Build Server Guide](https://modelcontextprotocol.io/docs/develop/build-server) - Complete Python example with FastMCP, server setup, transport configuration
- [Odoo External API Docs](https://odoo-master.readthedocs.io/en/master/api_integration.html) - `fields_get`, `search_read`, `execute_kw`, `ir.model`/`ir.model.fields` introspection, verified Python code examples
- [Claude Code MCP Docs](https://code.claude.com/docs/en/mcp) - stdio configuration, `.mcp.json` format, env vars, scopes
- [mcp PyPI](https://pypi.org/project/mcp/) - v1.26.0, Python >=3.10, MIT license, dependencies (pydantic, anyio, httpx, etc.)
- Phase 15 research and code (already in project) - XML-RPC patterns, OdooClient foundation, verify script

### Secondary (MEDIUM confidence)
- [FastMCP Testing Guide](https://gofastmcp.com/servers/testing) - In-memory `Client(transport=server)` pattern, pytest-asyncio config, assertion strategies
- [ivnvxd/mcp-server-odoo](https://github.com/ivnvxd/mcp-server-odoo) - Reference Odoo MCP server with similar tool set (search_records, get_model_fields, list_models)
- [Odoo Forum: Model Schema via XML-RPC](https://www.odoo.com/forum/help-1/how-to-retrieve-complete-model-schema-via-xml-rpc-for-documentation-288086) - Verified `ir.model.fields` search_read pattern with ttype/relation/required/readonly fields

### Tertiary (LOW confidence)
- In-memory Client import path (`from mcp.client import Client`) - Based on FastMCP docs using standalone package import; official SDK may differ slightly
- `ir.ui.view` arch field accessibility via XML-RPC - Logically should work (it's a stored computed field), but not explicitly verified against Odoo 17 external API restrictions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official MCP SDK is authoritative; xmlrpc.client is stdlib; both well-documented
- Architecture: HIGH - FastMCP decorator pattern is the official documented approach; OdooClient wrapper follows project conventions (matches Phase 15 verify script)
- Pitfalls: HIGH - stdio/print corruption is documented in official MCP guide; ttype vs type confusion is documented in Odoo API; large result sets are a known MCP concern
- Code examples: MEDIUM-HIGH - Server code synthesized from official docs; test code based on FastMCP testing guide (may need import path adjustment)

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (MCP SDK is fast-moving but core FastMCP API is stable; Odoo 17 XML-RPC is in LTS)
