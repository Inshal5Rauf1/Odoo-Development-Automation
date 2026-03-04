---
phase: 18
slug: auto-fix-hardening
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-04
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | python/pyproject.toml |
| **Quick run command** | `cd python && .venv/bin/python -m pytest tests/test_auto_fix.py -x -q` |
| **Full suite command** | `cd python && .venv/bin/python -m pytest tests/ -x -q -m "not docker and not e2e and not e2e_slow"` |
| **Estimated runtime** | ~5 seconds (unit only) |

---

## Sampling Rate

- **After every task commit:** Run `cd python && .venv/bin/python -m pytest tests/test_auto_fix.py -x -q`
- **After every plan wave:** Run `cd python && .venv/bin/python -m pytest tests/ -x -q -m "not docker and not e2e and not e2e_slow"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | DFIX-01 | unit | `cd python && .venv/bin/python -m pytest tests/test_auto_fix.py -x -q -k "docker_fix"` | ✅ | ⬜ pending |
| 18-01-02 | 01 | 1 | AFIX-01 | unit | `cd python && .venv/bin/python -m pytest tests/test_auto_fix.py -x -q -k "iteration_cap"` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 2 | AFIX-02 | integration | `cd python && .venv/bin/python -m pytest tests/test_auto_fix_integration.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `python/tests/test_auto_fix_integration.py` — stubs for AFIX-02 CLI integration test

*Existing test_auto_fix.py covers DFIX-01 and AFIX-01 test infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cap reached escalation message is actionable | AFIX-01 | Requires visual inspection of CLI output format | Run `validate --auto-fix` on a module with unfixable errors, verify message says what to do |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (TDD tasks create tests inline)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (TDD tasks handle inline)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-04
