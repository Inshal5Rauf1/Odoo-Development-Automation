---
phase: 11
slug: live-integration-testing-i18n
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-03
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 |
| **Config file** | `python/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd python && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd python && uv run pytest tests/ -v` |
| **Docker tests only** | `cd python && uv run pytest tests/ -m docker -v` |
| **Estimated runtime** | ~30s unit, ~60-120s Docker integration |

---

## Sampling Rate

- **After every task commit:** Run `cd python && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd python && uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds (unit), 120 seconds (Docker)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | DEBT-03 | integration (Docker) | `cd python && uv run pytest tests/ -m docker -v` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DEBT-04 | unit | `cd python && uv run pytest tests/test_i18n_extractor.py -x -v` | partial | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_docker_integration.py` — live Docker tests for DEBT-03 (skipped without Docker)
- [ ] `tests/fixtures/docker_test_module/` — fixture module for Docker + i18n testing
- [ ] Add `docker` marker to `[tool.pytest.ini_options]`

*Existing unit test infrastructure covers mocked scenarios.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker containers start and stop cleanly | DEBT-03 | Requires Docker daemon running | Run `pytest -m docker -v` on machine with Docker |
| Generated .pot file has correct format | DEBT-04 | Visual inspection of .pot output | Run `odoo-gen-utils extract-i18n <module>`, check .pot |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
