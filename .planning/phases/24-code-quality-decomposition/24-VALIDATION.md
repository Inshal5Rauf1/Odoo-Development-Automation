---
phase: 24
slug: code-quality-decomposition
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-05
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | python/pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `cd python && uv run pytest tests/test_renderer.py tests/test_cli_validate.py tests/test_docker_runner.py -x -q` |
| **Full suite command** | `cd python && uv run pytest tests/ -x -q --ignore=tests/test_golden_path.py` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 24-T1 | TBD | TBD | QUAL-01 | unit | `cd python && uv run pytest tests/test_cli_validate.py -x -q` | ✅ | ⬜ pending |
| 24-T2 | TBD | TBD | QUAL-02 | unit | `cd python && uv run pytest tests/test_renderer.py -x -q` | ✅ | ⬜ pending |
| 24-T3 | TBD | TBD | QUAL-03 | unit | `cd python && uv run pytest tests/test_docker_runner.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. Wave 0 gaps are addressed by TDD tasks.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-05
