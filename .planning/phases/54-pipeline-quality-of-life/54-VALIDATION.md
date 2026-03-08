---
phase: 54
slug: pipeline-quality-of-life
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 54 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `python/pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `python -m pytest tests/test_manifest.py tests/test_hooks.py -x -q --tb=short` |
| **Full suite command** | `python -m pytest --tb=short -q` |
| **Estimated runtime** | ~3 seconds (manifest+hooks), ~25 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_manifest.py tests/test_hooks.py -x -q --tb=short`
- **After every plan wave:** Run `python -m pytest --tb=short -q`
- **Before `/gsd:verify-work`:** Full suite must be green (0 failures, 0 errors, skips OK)
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 54-01-01 | 01 | 1 | ARCH-04a | unit | `pytest tests/test_manifest.py::TestGenerationManifest -x -q` | No W0 | pending |
| 54-01-02 | 01 | 1 | ARCH-04b | unit | `pytest tests/test_manifest.py::TestStageResult -x -q` | No W0 | pending |
| 54-01-03 | 01 | 1 | ARCH-04c | unit | `pytest tests/test_manifest.py::TestManifestPersistence -x -q` | No W0 | pending |
| 54-01-04 | 01 | 1 | ARCH-04d | unit | `pytest tests/test_manifest.py::TestSHA256 -x -q` | No W0 | pending |
| 54-01-05 | 01 | 1 | ARCH-05a | unit | `pytest tests/test_hooks.py::TestRenderHookProtocol -x -q` | No W0 | pending |
| 54-01-06 | 01 | 1 | ARCH-05b | unit | `pytest tests/test_hooks.py::TestLoggingHook -x -q` | No W0 | pending |
| 54-01-07 | 01 | 1 | ARCH-05c | unit | `pytest tests/test_hooks.py::TestManifestHook -x -q` | No W0 | pending |
| 54-01-08 | 01 | 1 | ARCH-06a | unit | `pytest tests/test_manifest.py::TestGenerationSession -x -q` | No W0 | pending |
| 54-01-09 | 01 | 1 | ARCH-06b | unit | `pytest tests/test_manifest.py::TestSessionToManifest -x -q` | No W0 | pending |
| 54-02-01 | 02 | 2 | ARCH-04e | integration | `pytest tests/test_manifest.py::TestRenderModuleManifest -x -q` | No W0 | pending |
| 54-02-02 | 02 | 2 | ARCH-05d | integration | `pytest tests/test_hooks.py::TestHookExceptionIsolation -x -q` | No W0 | pending |
| 54-02-03 | 02 | 2 | ARCH-05e | unit | `pytest tests/test_hooks.py::TestZeroOverhead -x -q` | No W0 | pending |
| 54-02-04 | 02 | 2 | ARCH-06c | integration | `pytest tests/test_manifest.py::TestResumeFromStage -x -q` | No W0 | pending |
| 54-02-05 | 02 | 2 | ARCH-06d | integration | `pytest tests/test_manifest.py::TestResumeSpecChanged -x -q` | No W0 | pending |
| 54-02-06 | 02 | 2 | ARCH-06e | integration | `pytest tests/test_manifest.py::TestResumeIntegrityCheck -x -q` | No W0 | pending |
| 54-02-07 | 02 | 2 | ARCH-06f | integration | `pytest tests/test_manifest.py::TestCLIResume -x -q` | No W0 | pending |
| 54-02-08 | 02 | 2 | COMPAT-01 | integration | `pytest tests/test_manifest.py::TestShowStateManifest -x -q` | No W0 | pending |
| 54-02-09 | 02 | 2 | COMPAT-02 | regression | `pytest tests/test_artifact_state.py -x -q` | Yes | pending |
| 54-FULL | -- | -- | ALL | full | `pytest --tb=short -q` | Yes | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `python/tests/test_manifest.py` — stubs for ARCH-04a through ARCH-04d, ARCH-06a through ARCH-06f, COMPAT-01
- [ ] `python/tests/test_hooks.py` — stubs for ARCH-05a through ARCH-05e

*Existing infrastructure (pytest) covers framework needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 25s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
