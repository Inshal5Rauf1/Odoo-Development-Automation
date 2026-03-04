---
phase: 17
slug: inline-environment-verification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | python/pyproject.toml |
| **Quick run command** | `cd python && .venv/bin/python -m pytest tests/test_verifier.py -x -q` |
| **Full suite command** | `cd python && .venv/bin/python -m pytest tests/ -x -q -m "not docker and not e2e and not e2e_slow"` |
| **Estimated runtime** | ~3 seconds (unit only, mocked OdooClient) |

---

## Sampling Rate

- **After every task commit:** Run `cd python && .venv/bin/python -m pytest tests/test_verifier.py -x -q`
- **After every plan wave:** Run `cd python && .venv/bin/python -m pytest tests/ -x -q -m "not docker and not e2e and not e2e_slow"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | MCP-03 | unit | `cd python && .venv/bin/python -m pytest tests/test_verifier.py::TestModelVerification -x -q` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | MCP-04 | unit | `cd python && .venv/bin/python -m pytest tests/test_verifier.py::TestViewVerification -x -q` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 2 | MCP-03, MCP-04 | integration | `cd python && .venv/bin/python -m pytest tests/test_verifier_integration.py -x -q -m docker` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `python/tests/test_verifier.py` — stubs for MCP-03 (model verification) and MCP-04 (view verification)
- [ ] `python/tests/test_verifier_integration.py` — stubs for Docker integration tests

*Existing infrastructure (pytest, pyproject.toml, OdooClient) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Verification warnings surface in CLI output | MCP-03, MCP-04 | Requires visual inspection of CLI output format | Run `validate` on a module with known mismatches, verify warnings printed to stderr |
| MCP unavailable graceful fallback | MCP-03, MCP-04 | Requires stopping Odoo dev instance mid-generation | Stop Docker, run generation, verify no errors and files still created |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
