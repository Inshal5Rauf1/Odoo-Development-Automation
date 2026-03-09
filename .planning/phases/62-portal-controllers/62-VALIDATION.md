---
phase: 62
slug: portal-controllers
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 62 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | python/pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd python && python -m pytest tests/test_portal_preprocessor.py tests/test_portal_renderer.py tests/test_portal_schema.py tests/test_portal_validation.py -x -q` |
| **Full suite command** | `cd python && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd python && python -m pytest tests/test_portal_preprocessor.py tests/test_portal_renderer.py tests/test_portal_schema.py tests/test_portal_validation.py -x -q`
- **After every plan wave:** Run `cd python && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 62-01-01 | 01 | 1 | PRTL-01 | unit | `cd python && python -m pytest tests/test_portal_schema.py -x -q` | ❌ W0 | ⬜ pending |
| 62-01-02 | 01 | 1 | PRTL-01 | unit | `cd python && python -m pytest tests/test_portal_preprocessor.py -x -q` | ❌ W0 | ⬜ pending |
| 62-01-03 | 01 | 1 | E23 | unit | `cd python && python -m pytest tests/test_portal_validation.py -x -q` | ❌ W0 | ⬜ pending |
| 62-02-01 | 02 | 2 | PRTL-01 | unit | `cd python && python -m pytest tests/test_portal_renderer.py -x -q` | ❌ W0 | ⬜ pending |
| 62-02-02 | 02 | 2 | PRTL-02 | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_qweb_home_counter -x -q` | ❌ W0 | ⬜ pending |
| 62-02-03 | 02 | 2 | PRTL-02 | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_qweb_list_page -x -q` | ❌ W0 | ⬜ pending |
| 62-02-04 | 02 | 2 | PRTL-02 | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_qweb_detail_page -x -q` | ❌ W0 | ⬜ pending |
| 62-02-05 | 02 | 2 | PRTL-02 | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_qweb_editable_detail -x -q` | ❌ W0 | ⬜ pending |
| 62-02-06 | 02 | 2 | PRTL-03 | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_portal_record_rules -x -q` | ❌ W0 | ⬜ pending |
| 62-02-07 | 02 | 2 | PRTL-03 | unit | `cd python && python -m pytest tests/test_portal_renderer.py::test_multihop_ownership -x -q` | ❌ W0 | ⬜ pending |
| 62-03-01 | 03 | 2 | ALL | integration | `cd python && python -m pytest tests/test_portal_renderer.py::test_full_portal_render -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_portal_schema.py` — PortalSpec, PortalPageSpec, PortalActionSpec Pydantic model validation
- [ ] `tests/test_portal_preprocessor.py` — preprocessor order=90, spec enrichment, dependency injection
- [ ] `tests/test_portal_renderer.py` — render_portal() output, controller content, QWeb content, rule content
- [ ] `tests/test_portal_validation.py` — E23 ownership path validation
- [ ] Test fixtures: portal spec fixture (uni_student_portal with 4 pages from CONTEXT.md)

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
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
