---
phase: 21
slug: template-correctness
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-05
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | python/pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `cd python && uv run pytest tests/test_renderer.py -x -q` |
| **Full suite command** | `cd python && uv run pytest tests/ -x -q --ignore=tests/test_golden_path.py` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd python && uv run pytest tests/test_renderer.py -x -q`
- **After every plan wave:** Run `cd python && uv run pytest tests/ -x -q --ignore=tests/test_golden_path.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-T1 | 01 | 1 | TMPL-01 | unit (RED) | `cd python && uv run pytest tests/test_renderer.py -x -q -k "line_item or chatter_false or parent_already"` | ❌ W0 (TDD) | ⬜ pending |
| 21-01-T2 | 01 | 1 | TMPL-01 | unit (GREEN) | `cd python && uv run pytest tests/test_renderer.py -x -q -k "inherit_list or mail_thread or mail_inherit"` | Partial | ⬜ pending |
| 21-02-T1 | 02 | 2 | TMPL-02, TMPL-03, TMPL-04 | unit (RED+GREEN) | `cd python && uv run pytest tests/test_renderer.py -x -q -k "wizard_api or wizard_acl or display_name"` | ❌ W0 (TDD) | ⬜ pending |
| 21-02-T2 | 02 | 2 | TMPL-02, TMPL-03, TMPL-04 | regression | `cd python && uv run pytest tests/ -x -q --ignore=tests/test_golden_path.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. Wave 0 gaps are addressed by TDD tasks in Plan 01 Task 1 and Plan 02 Task 1 (tests written first).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-05
