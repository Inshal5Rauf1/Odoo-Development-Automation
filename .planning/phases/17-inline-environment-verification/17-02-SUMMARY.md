---
phase: 17-inline-environment-verification
plan: "02"
subsystem: testing
tags: [integration-tests, docker, verifier, odoo-client, xml-rpc, cli-output]

dependency_graph:
  requires:
    - "python/src/odoo_gen_utils/verifier.py (EnvironmentVerifier, VerificationWarning)"
    - "python/src/odoo_gen_utils/cli.py (render-module command with WARN output)"
    - "http://localhost:8069 (Phase 15 dev instance, Odoo 17 CE)"
  provides:
    - "python/tests/test_verifier_integration.py (4 Docker-marked live Odoo integration tests)"
    - "Human-confirmed: WARN lines visible in CLI output, suggestions actionable, generation not blocked"
  affects:
    - "CI pipeline: integration tests marked docker are excluded from default run"
    - "Developers: WARN output confirmed usable during module development"

tech_stack:
  added: []
  patterns:
    - "pytest.mark.docker to exclude live-Odoo tests from CI (no Docker daemon in CI)"
    - "scope=module fixture for OdooClient: one auth cycle shared across all 4 tests"
    - "OdooConfig url=http://localhost:8069 db=odoo_dev username=admin api_key=admin for dev instance"
    - "Graceful fallback confirmed: generation proceeds (exit 0) even when WARN lines fire"

key_files:
  created:
    - "python/tests/test_verifier_integration.py"
  modified: []

key_decisions:
  - "pytestmark=pytest.mark.docker excludes integration tests from unit suite (no CI regressions)"
  - "scope=module fixture for live_client/live_verifier: one OdooClient auth per test session (not per test)"
  - "CLI warning format confirmed: WARN [check_type] subject: message + Suggestion: ... lines on stderr"
  - "Human checkpoint confirmed: warnings are non-blocking -- generation proceeds (exit 0) with warnings"

patterns_established:
  - "Docker-marked integration pattern: pytestmark = pytest.mark.docker at module level"
  - "Live Odoo fixture pattern: scope=module OdooClient fixture for multi-test scenarios"

requirements_completed:
  - MCP-03
  - MCP-04

metrics:
  duration: "5min"
  completed: "2026-03-04"
  tasks: 2
  files: 1
---

# Phase 17 Plan 02: Docker Integration Tests + CLI Warning Checkpoint Summary

**4 Docker-marked integration tests against live Odoo 17 CE confirming EnvironmentVerifier end-to-end connectivity, plus human-verified CLI WARN output that is actionable and non-blocking.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-04
- **Completed:** 2026-03-04
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 1

## Accomplishments

- Created `test_verifier_integration.py` with 4 Docker-marked live Odoo integration tests proving end-to-end XML-RPC verification
- hr.employee inheritance checks return zero warnings (model exists in dev instance)
- Nonexistent model and field checks return expected VerificationWarnings with correct check_type
- Human confirmed: CLI `render-module` command surfaces WARN lines with actionable suggestion text and generation is NOT blocked (exit 0)
- 381/381 unit tests still green (no regressions from Phase 17 Plan 01 work)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Docker integration tests for live Odoo verification** - `bd5c2e1` (test)
2. **Task 2: Verify CLI warning output is actionable** - Human-verify checkpoint, approved

**Plan metadata:** (final commit — see below)

## Files Created/Modified

- `python/tests/test_verifier_integration.py` - 4 Docker-marked integration tests; module-scoped OdooClient fixture connecting to http://localhost:8069/odoo_dev

## Decisions Made

1. **pytestmark=pytest.mark.docker** at module level excludes all 4 tests from `pytest -m "not docker"` CI run — no Docker daemon required in CI.

2. **scope=module fixture** for `live_client` and `live_verifier`: one OdooClient auth handshake shared across all 4 tests in the session. Faster and matches real usage pattern.

3. **CLI warning format confirmed by human**: `WARN [check_type] subject: message` plus `Suggestion: ...` lines on stderr are readable and point to the right fix.

4. **Non-blocking generation confirmed**: running `render-module` with bad `_inherit` produces WARN lines but exits 0 and creates all module files. Developers get warnings without losing their output.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Integration tests passed on first run against live Odoo dev instance.

## User Setup Required

None - no external service configuration required. (Phase 15 dev instance setup was completed in Plan 15-02.)

## Next Phase Readiness

- Phase 17 complete: MCP-03 and MCP-04 requirements satisfied
- v2.0 Environment-Aware Generation milestone is COMPLETE (Phases 15-17 all done)
- Phase 18 (Auto-Fix Hardening) and Phase 19 (Enhancements) are deferred to v2.1
- No blockers

## Self-Check

Files verified:
- python/tests/test_verifier_integration.py -- FOUND

Commits verified:
- bd5c2e1: test(17-02): add Docker integration tests for live Odoo verification -- FOUND

## Self-Check: PASSED

---
*Phase: 17-inline-environment-verification*
*Completed: 2026-03-04*
