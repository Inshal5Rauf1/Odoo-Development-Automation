---
phase: 16-odoo-mcp-server
plan: "01"
subsystem: mcp-server
tags: [mcp, fastmcp, odoo, xmlrpc, introspection, tdd]
dependency_graph:
  requires: []
  provides: [odoo-mcp-server, odoo-client-wrapper]
  affects: [phase-17-claude-code-integration]
tech_stack:
  added:
    - mcp==1.26.0 (FastMCP server framework)
    - pytest-asyncio==1.3.0 (async test support)
  patterns:
    - FastMCP @mcp.tool() decorator pattern for tool registration
    - Lazy singleton OdooClient with uid caching
    - Error handling via _handle_error() returning ERROR-prefixed strings
    - TDD with pytest-asyncio and FastMCP direct call_tool() testing
key_files:
  created:
    - python/src/odoo_gen_utils/mcp/__init__.py
    - python/src/odoo_gen_utils/mcp/odoo_client.py
    - python/src/odoo_gen_utils/mcp/server.py
    - python/src/odoo_gen_utils/mcp/__main__.py
    - python/tests/test_mcp_server.py
  modified:
    - python/pyproject.toml
decisions:
  - "Used FastMCP direct call_tool()/list_tools() for testing instead of in-memory Client (mcp package has no Client class at top level)"
  - "asyncio_mode=auto in pyproject.toml eliminates per-test async markers"
  - "OdooClient _models attribute (not _object) to match test mock structure"
metrics:
  duration: 4min
  completed: "2026-03-04"
  tasks_completed: 2
  files_created: 5
  files_modified: 1
  tests_written: 29
  tests_passing: 29
---

# Phase 16 Plan 01: Odoo MCP Server Implementation Summary

**One-liner:** FastMCP server with 6 Odoo XML-RPC introspection tools using OdooClient wrapper, mcp>=1.9, and 29 unit tests with mocked XML-RPC responses.

## What Was Built

### OdooClient Wrapper (`python/src/odoo_gen_utils/mcp/odoo_client.py`)

- `OdooConfig` frozen dataclass: url, db, username, api_key (read from env vars)
- `OdooClient` class wrapping `xmlrpc.client.ServerProxy` for two Odoo endpoints:
  - `/xmlrpc/2/common` for authentication and version checks
  - `/xmlrpc/2/object` for model queries via `execute_kw`
- `authenticate()`: calls common.authenticate, caches uid, raises `ConnectionError` on failure
- `uid` property: triggers lazy authentication on first access
- `execute_kw()`: delegates to object endpoint with cached credentials
- `search_read()`: convenience wrapper with optional `limit` kwarg

### FastMCP Server (`python/src/odoo_gen_utils/mcp/server.py`)

- `FastMCP("odoo-introspection")` server instance
- `_client: OdooClient | None = None` module-level lazy singleton
- `_get_client()` reads ODOO_URL/ODOO_DB/ODOO_USER/ODOO_API_KEY env vars, defaults to Phase 15 dev instance values
- `_handle_error(exc)` formats any exception as ERROR-prefixed string
- 6 `@mcp.tool()` registered tools:

| Tool | Purpose | Odoo Source |
|------|---------|-------------|
| `check_connection` | Version + uid verification | `common.version()` + `client.uid` |
| `list_models` | List models with optional filter | `ir.model` search_read |
| `get_model_fields` | Field metadata for a model | `ir.model.fields` search_read |
| `list_installed_modules` | All installed modules + versions | `ir.module.module` search_read |
| `check_module_dependency` | Check if specific module installed | `ir.module.module` search_read |
| `get_view_arch` | XML view architecture | `ir.ui.view` search_read |

- All tools catch `Exception` and return `_handle_error()` string (server never crashes)
- `logging.basicConfig(stream=sys.stderr)` -- no `print()` calls (would corrupt stdio JSON-RPC)
- `main()` calls `mcp.run(transport="stdio")` for Claude Code integration
- `__main__.py` enables `python -m odoo_gen_utils.mcp` invocation

### Test Suite (`python/tests/test_mcp_server.py`)

29 unit tests across two test classes and standalone async tests:

- `TestOdooConfig`: env var reading, defaults
- `TestOdooClient`: authenticate success/failure, uid lazy property, search_read delegation with limit
- `test_list_tools`: server exposes exactly 6 tools by name
- `test_check_connection`: version string + uid in response
- `test_list_models` + filter variant: formatted bullet list
- `test_get_model_fields` + empty variant: field details with relation/required/readonly flags
- `test_list_installed_modules`: names and versions
- `test_check_module_dependency_installed/not_found/not_installed`: all 3 states
- `test_get_view_arch` + type filter + no views: XML arch, inherit_id, view_type filter
- Error tests for all 6 tools: ConnectionRefusedError, OSError, xmlrpc.client.Fault

## TDD Phases

**RED:** Created `test_mcp_server.py` with 29 tests -- all failed (modules didn't exist).
Commit: `c059e62`

**GREEN:** Created `odoo_client.py` and `server.py` -- all 29 tests passed.
Commit: `3652c1c`

**REFACTOR:** Code reviewed for clarity, error handling consistency, and docstring quality. No changes needed -- implementation was already clean from GREEN phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] In-memory MCP Client does not exist in official mcp package**

- **Found during:** Task 2 RED phase setup
- **Issue:** The research noted as Open Question #2 that `from mcp.client import Client` may not work. Testing confirmed the official `mcp` package (v1.26.0) has no top-level `Client` class in `mcp.client`.
- **Fix:** Used FastMCP's built-in `call_tool()` and `list_tools()` methods directly on the server instance, as recommended in the research fallback. This is actually cleaner -- no async context manager overhead, direct Python calls.
- **Pattern used:** `result, _ = await server.call_tool("tool_name", args)` and `tools = await server.list_tools()`
- **Files modified:** `python/tests/test_mcp_server.py`
- **Commits:** `c059e62` (RED), `3652c1c` (GREEN)

## Self-Check: PASSED

All files verified present. All commits verified in git log.

| Check | Result |
|-------|--------|
| python/src/odoo_gen_utils/mcp/__init__.py | FOUND |
| python/src/odoo_gen_utils/mcp/odoo_client.py | FOUND |
| python/src/odoo_gen_utils/mcp/server.py | FOUND |
| python/src/odoo_gen_utils/mcp/__main__.py | FOUND |
| python/tests/test_mcp_server.py | FOUND |
| Commit e175cca (Task 1: chore) | FOUND |
| Commit c059e62 (Task 2 RED: test) | FOUND |
| Commit 3652c1c (Task 2 GREEN: feat) | FOUND |
