---
phase: 19
slug: enhancements
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-04
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | python/pyproject.toml |
| **Quick run command** | `cd python && .venv/bin/python -m pytest tests/test_context7.py tests/test_artifact_state.py -x -q` |
| **Full suite command** | `cd python && .venv/bin/python -m pytest tests/ -x -q -m "not docker and not e2e and not e2e_slow"` |
| **Estimated runtime** | ~5 seconds (unit only) |

---

## Sampling Rate

- **After every task commit:** Run `cd python && .venv/bin/python -m pytest tests/test_context7.py tests/test_artifact_state.py -x -q`
- **After every plan wave:** Run `cd python && .venv/bin/python -m pytest tests/ -x -q -m "not docker and not e2e and not e2e_slow"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | MCP-05 | unit | `cd python && .venv/bin/python -m pytest tests/test_context7.py -x -q` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | OBS-01 | unit | `cd python && .venv/bin/python -m pytest tests/test_artifact_state.py -x -q` | ❌ W0 | ⬜ pending |
| 19-02-01 | 02 | 2 | MCP-05 | integration | `cd python && .venv/bin/python -m pytest tests/test_context7.py -x -q -k "integration"` | ❌ W0 | ⬜ pending |
| 19-02-02 | 02 | 2 | OBS-01 | integration | `cd python && .venv/bin/python -m pytest tests/test_artifact_state.py -x -q -k "integration"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `python/tests/test_context7.py` — stubs for MCP-05 (a-f)
- [ ] `python/tests/test_artifact_state.py` — stubs for OBS-01 (a-f)

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Context7 returns real Odoo docs | MCP-05 | Requires live Context7 API key | Set CONTEXT7_API_KEY, run `python -c "from odoo_gen_utils.context7 import ...; print(c.query_docs('mail.thread'))"` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (TDD tasks create tests inline)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (TDD tasks handle inline)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-04
