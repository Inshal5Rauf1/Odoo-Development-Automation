---
phase: 15
slug: odoo-dev-instance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=30 -m "not docker"` |
| **Full suite command** | `uv run pytest tests/ --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=30 -m "not docker"`
- **After every plan wave:** Run `uv run pytest tests/ --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | MCP-01 | integration | `uv run pytest tests/test_dev_instance.py -k "test_compose_up"` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | MCP-01 | integration | `uv run pytest tests/test_dev_instance.py -k "test_xmlrpc_auth"` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | MCP-01 | integration | `uv run pytest tests/test_dev_instance.py -k "test_volume_persistence"` | ❌ W0 | ⬜ pending |
| 15-01-04 | 01 | 1 | MCP-01 | unit | `uv run pytest tests/test_dev_instance.py -k "test_management_script"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dev_instance.py` — stubs for MCP-01 (compose up, XML-RPC auth, persistence, management script)
- [ ] Docker Compose file must exist before integration tests can run

*Note: Integration tests (compose_up, xmlrpc_auth, volume_persistence) require Docker and a running Odoo instance. Unit tests for the management script can run without Docker.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pre-installed modules visible in Odoo UI | MCP-01 | Requires browser/UI check | Start instance, navigate to Apps, verify base/mail/sale/purchase/hr/account installed |

*All other behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
