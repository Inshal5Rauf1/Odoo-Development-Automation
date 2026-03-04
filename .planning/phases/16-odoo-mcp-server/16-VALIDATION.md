---
phase: 16
slug: odoo-mcp-server
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | python/pyproject.toml |
| **Quick run command** | `cd python && python -m pytest tests/test_mcp_server.py -x -q` |
| **Full suite command** | `cd python && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~2 seconds (unit only, mocked XML-RPC) |

---

## Sampling Rate

- **After every task commit:** Run `cd python && python -m pytest tests/test_mcp_server.py -x -q`
- **After every plan wave:** Run `cd python && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | MCP-02 | unit | `cd python && python -m pytest tests/test_mcp_server.py::TestOdooClient -x -q` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | MCP-02 | unit | `cd python && python -m pytest tests/test_mcp_server.py::TestMCPTools -x -q` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 2 | MCP-02 | unit | `cd python && python -m pytest tests/test_mcp_server.py -x -q` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 2 | MCP-02 | integration | `cd python && python -m pytest tests/test_mcp_server.py -m docker -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `python/tests/test_mcp_server.py` — stubs for MCP-02 (OdooClient, 6 tools, error handling)
- [ ] `mcp>=1.9` added to dependencies (pyproject.toml or requirements)
- [ ] `pytest-asyncio` added to test dependencies

*Existing infrastructure (pytest, pyproject.toml) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MCP server responds in Claude Code | MCP-02 | Requires Claude Code MCP client config | Configure in `.claude.json`, invoke tool, verify response |
| Live Odoo XML-RPC data accuracy | MCP-02 | Requires running Docker instance | Start dev instance, run verify script, check tool output matches actual models |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
