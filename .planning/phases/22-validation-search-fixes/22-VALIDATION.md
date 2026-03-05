---
phase: 22
slug: validation-search-fixes
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-05
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | python/pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `cd python && uv run pytest tests/test_docker_runner.py tests/test_search_index.py tests/test_search_fork.py -x -q` |
| **Full suite command** | `cd python && uv run pytest tests/ -x -q --ignore=tests/test_golden_path.py` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd python && uv run pytest tests/test_docker_runner.py tests/test_search_index.py tests/test_search_fork.py -x -q`
- **After every plan wave:** Run `cd python && uv run pytest tests/ -x -q --ignore=tests/test_golden_path.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-T1 | TBD | TBD | VALD-01 | unit (mocked) | `cd python && uv run pytest tests/test_docker_runner.py -x -q -k "install"` | Needs update (TDD) | ⬜ pending |
| 22-T2 | TBD | TBD | SRCH-01 | unit (mocked) | `cd python && uv run pytest tests/test_search_index.py -x -q -k "rate_limit"` | ❌ (TDD) | ⬜ pending |
| 22-T3 | TBD | TBD | SRCH-02 | unit | `cd python && uv run pytest tests/test_search_fork.py -x -q -k "inherit"` | ❌ (TDD) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. Wave 0 gaps are addressed by TDD tasks (tests written first).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-05
