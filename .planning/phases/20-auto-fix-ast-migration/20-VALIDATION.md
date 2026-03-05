---
phase: 20
slug: auto-fix-ast-migration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ (via venv) |
| **Config file** | `python/pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `cd python && .venv/bin/python -m pytest tests/test_auto_fix.py -x -q` |
| **Full suite command** | `cd python && .venv/bin/python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd python && .venv/bin/python -m pytest tests/test_auto_fix.py -x -q`
- **After every plan wave:** Run `cd python && .venv/bin/python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 0 | AFIX-01 | unit | `pytest tests/test_auto_fix.py -k "multi_line"` | No -- Wave 0 | pending |
| 20-01-02 | 01 | 0 | AFIX-02 | unit | `pytest tests/test_auto_fix.py -k "arbitrary_names"` | No -- Wave 0 | pending |
| 20-01-03 | 01 | 1 | AFIX-01 | unit | `pytest tests/test_auto_fix.py -k "W8113"` | Yes | pending |
| 20-01-04 | 01 | 1 | AFIX-01 | unit | `pytest tests/test_auto_fix.py -k "W8111"` | Yes | pending |
| 20-01-05 | 01 | 1 | AFIX-01 | unit | `pytest tests/test_auto_fix.py -k "C8116"` | Yes | pending |
| 20-01-06 | 01 | 1 | AFIX-01 | unit | `pytest tests/test_auto_fix.py -k "W8150"` | Yes | pending |
| 20-01-07 | 01 | 1 | AFIX-01 | unit | `pytest tests/test_auto_fix.py -k "C8107"` | Yes | pending |
| 20-02-01 | 02 | 1 | AFIX-02 | unit | `pytest tests/test_auto_fix.py -k "unused_import"` | Partial | pending |
| 20-02-02 | 02 | 1 | AFIX-02 | unit | `pytest tests/test_auto_fix.py -k "keeps_used"` | Partial | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_auto_fix.py::TestFixW8113MultiLine` -- test multi-line string= removal
- [ ] `tests/test_auto_fix.py::TestFixW8111MultiLine` -- test multi-line renamed param
- [ ] `tests/test_auto_fix.py::TestFixC8116MultiLineValue` -- test manifest key with multi-line value
- [ ] `tests/test_auto_fix.py::TestUnusedImportsArbitraryNames` -- test arbitrary (non-whitelisted) unused imports detected
- [ ] `tests/test_auto_fix.py::TestUnusedImportsStarImport` -- test star imports preserved
- [ ] `tests/test_auto_fix.py::TestFormattingPreserved` -- test comments/whitespace preserved after AST-based fixes

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
