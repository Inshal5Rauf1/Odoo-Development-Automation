---
phase: 21
slug: template-correctness
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 21-01-01 | 01 | 1 | TMPL-01 | unit | `cd python && uv run pytest tests/test_renderer.py -x -q -k "mail_thread"` | Partial | ⬜ pending |
| 21-01-02 | 01 | 1 | TMPL-02 | unit | `cd python && uv run pytest tests/test_renderer.py -x -q -k "wizard_api"` | ❌ W0 | ⬜ pending |
| 21-01-03 | 01 | 1 | TMPL-03 | unit | `cd python && uv run pytest tests/test_renderer.py -x -q -k "wizard_acl"` | ❌ W0 | ⬜ pending |
| 21-01-04 | 01 | 1 | TMPL-04 | unit | `cd python && uv run pytest tests/test_renderer.py -x -q -k "display_name"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_renderer.py` — add tests for TMPL-01 skip cases (line items, config tables, already-inherited models)
- [ ] `tests/test_renderer.py` — add tests for TMPL-02 wizard conditional api import
- [ ] `tests/test_renderer.py` — add tests for TMPL-03 wizard ACL entries in csv
- [ ] `tests/test_renderer.py` — add tests for TMPL-04 display_name assertion for 17.0 and 18.0

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
