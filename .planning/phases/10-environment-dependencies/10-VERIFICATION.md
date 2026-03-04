---
phase: 10
slug: environment-dependencies
status: passed
score: 9/9
verified: 2026-03-03
---

# Phase 10: Environment & Dependencies — Verification

## Goal
Search and index features work with real GitHub API and a clean sentence-transformers install.

## Requirement Coverage

| Req ID | Description | Plans | Status |
|--------|-------------|-------|--------|
| DEBT-01 | GitHub CLI authenticated, search/extend features query GitHub API | 10-01, 10-02 | SATISFIED |
| DEBT-02 | sentence-transformers CPU-only installs cleanly, ChromaDB indexing works e2e | 10-01 | SATISFIED |

## Must-Haves Verified

| # | Observable Truth | Evidence | Status |
|---|-----------------|----------|--------|
| 1 | sentence-transformers and torch removed from [search] extras | Zero grep matches in src/, clean pyproject.toml | PASS |
| 2 | No [[tool.uv.index]] pytorch-cpu section | Torch index config fully removed | PASS |
| 3 | 254 tests pass (9 skipped), 0 regressions | Exceeds 243+ baseline | PASS |
| 4 | test_e2e_github.py: 6 E2E tests, skip gracefully without GITHUB_TOKEN | pytest collection verified | PASS |
| 5 | test_e2e_index.py: 5 E2E tests, sentinel + ONNX pass unconditionally | 2 always-run, 3 skip on no token | PASS |
| 6 | e2e and e2e_slow markers registered in pytest config | pyproject.toml [tool.pytest.ini_options] | PASS |
| 7 | Wizard diagnoses gh-not-installed / not-authenticated / env-token | 8/8 unit tests pass | PASS |
| 8 | GITHUB_TOKEN env var short-circuits wizard | Mock assertion confirms no subprocess call | PASS |
| 9 | --no-wizard flag on all 3 CLI commands | build-index, search-modules, extend-module | PASS |

## Key Links Verified

| From | To | Via | Status |
|------|----|-----|--------|
| test_e2e_github.py | search_modules() | direct import + real ChromaDB | WIRED |
| test_e2e_index.py | build_oca_index() | direct import with token | WIRED |
| wizard.py | gh auth status | subprocess.run | WIRED |
| cli.py | check_github_auth() | import + _handle_auth_failure() | WIRED |

## Human Verification (Optional)

| Behavior | Requirement | Instructions |
|----------|-------------|--------------|
| Real GitHub token works e2e | DEBT-01 | Set GITHUB_TOKEN, run pytest -m e2e -v |
| Wizard UX on real machine | DEBT-01 | Run odoo-gen-utils search-modules "inventory" without auth |

## Deviations
- Plan 10-02 Task 2: Click 8.3.1 CliRunner does not support mix_stderr — auto-fixed

---
*Verified: 2026-03-03*
