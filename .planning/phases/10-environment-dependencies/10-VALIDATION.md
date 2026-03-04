---
phase: 10
slug: environment-dependencies
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-03
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 |
| **Config file** | `python/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd python && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd python && uv run pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds (unit), ~60s (e2e subset), ~300s (e2e full) |

---

## Sampling Rate

- **After every task commit:** Run `cd python && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd python && uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-T1 | 01 | 1 | DEBT-02 | unit (regression) | `cd python && uv run pytest tests/ -x -q` | existing | ⬜ pending |
| 10-01-T2 | 01 | 1 | DEBT-01 | e2e | `cd python && uv run pytest tests/test_e2e_github.py -x -q --co` | ❌ W0 | ⬜ pending |
| 10-01-T3 | 01 | 1 | DEBT-02 | e2e | `cd python && uv run pytest tests/test_e2e_index.py -x -q --co` | ❌ W0 | ⬜ pending |
| 10-02-T1 | 02 | 1 | DEBT-01 | unit | `cd python && uv run pytest tests/test_wizard.py -x -v` | ❌ W0 | ⬜ pending |
| 10-02-T2 | 02 | 1 | DEBT-01 | unit (regression) | `cd python && uv run pytest tests/ -x -q` | existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_e2e_github.py` — e2e tests for DEBT-01 (real GitHub API, skipped without token)
- [ ] `tests/test_e2e_index.py` — e2e tests for DEBT-02 (real ChromaDB build + query, skipped without token)
- [ ] Add `e2e` and `e2e_slow` markers to `[tool.pytest.ini_options]`

*Existing unit test infrastructure covers mocked scenarios. Wave 0 adds real-dependency tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `gh auth status` succeeds | DEBT-01 | Requires real gh CLI auth on developer machine | Run `gh auth status` and verify output shows authenticated |
| Fresh venv install completes | DEBT-02 | Requires clean venv creation (not in test harness) | Run `uv venv /tmp/test && uv pip install -e ".[search]"` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test_e2e_github.py, test_e2e_index.py, test_wizard.py, markers)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (planner)
