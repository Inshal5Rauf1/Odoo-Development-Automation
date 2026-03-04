---
phase: 15-odoo-dev-instance
plan: 01
subsystem: infra
tags: [docker, docker-compose, odoo-17, postgresql-16, xml-rpc, bash, python]

# Dependency graph
requires:
  - phase: 14-cleanup-debug
    provides: "v1.2 complete, stable codebase for v2.0 extension"
provides:
  - "Persistent Odoo 17 CE + PostgreSQL 16 Docker Compose dev instance"
  - "Management script (scripts/odoo-dev.sh) for start/stop/status/reset/logs"
  - "XML-RPC smoke test script (scripts/verify-odoo-dev.py)"
  - "Dev instance documentation in README.md"
affects: [15-02-PLAN, phase-16-mcp-server, phase-17-inline-verification]

# Tech tracking
tech-stack:
  added: [odoo:17.0 Docker image, postgres:16 Docker image, xmlrpc.client stdlib]
  patterns: [two-phase-init, separate-compose-files, python-healthcheck, env-var-configuration]

key-files:
  created:
    - docker/dev/docker-compose.yml
    - docker/dev/odoo.conf
    - docker/dev/.env
    - scripts/odoo-dev.sh
    - scripts/verify-odoo-dev.py
  modified:
    - README.md

key-decisions:
  - "Python3 urllib for healthcheck instead of curl (curl may not be in official Odoo image)"
  - "docker compose run --rm for module init (not exec, avoids serialization failures)"
  - "Separate docker/dev/ directory to avoid conflicts with existing validation compose"

patterns-established:
  - "Two-phase init: detect DB existence via psql query, install modules only on first run"
  - "Named volumes (odoo-dev-db, odoo-dev-data) for data persistence across restarts"
  - "Environment variable configuration with sensible defaults for all connection params"

requirements-completed: [MCP-01]

# Metrics
duration: 3min
completed: 2026-03-04
---

# Phase 15 Plan 01: Odoo Dev Instance Summary

**Persistent Odoo 17 CE + PostgreSQL 16 dev environment with Docker Compose, lifecycle management script, and XML-RPC smoke test**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-04T12:35:38Z
- **Completed:** 2026-03-04T12:38:42Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Created fully validated Docker Compose config for persistent Odoo 17 CE dev instance with PostgreSQL 16
- Built lifecycle management script (odoo-dev.sh) with two-phase init pattern using `run --rm` (not exec)
- Created XML-RPC smoke test that verifies authentication, model queries, and required module installation
- Documented dev instance setup, access credentials, and verification steps in README.md

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Docker Compose dev environment config** - `3a771cd` (feat)
2. **Task 2: Create management script and XML-RPC smoke test** - `8568ee2` (feat)
3. **Task 3: Document dev instance in README.md** - `d843303` (docs)

## Files Created/Modified

- `docker/dev/docker-compose.yml` - Persistent Odoo 17 CE + PostgreSQL 16 with named volumes, python3 healthcheck
- `docker/dev/odoo.conf` - Dev instance Odoo config with XML-RPC enabled, list_db=False, db_name=odoo_dev
- `docker/dev/.env` - Default environment variables (port, db, user, password)
- `scripts/odoo-dev.sh` - Lifecycle management: start, stop, status, reset, logs subcommands
- `scripts/verify-odoo-dev.py` - XML-RPC connectivity smoke test (auth + model query + module check)
- `README.md` - Added Dev Instance section with prerequisites, quick start, access, verification, modules

## Decisions Made

- **Python3 urllib healthcheck** - The official `odoo:17.0` Docker image may not include `curl`, but Python3 is always available. Using `python3 -c "import urllib.request; ..."` for the container healthcheck.
- **`run --rm` for module initialization** - Per CLAUDE.md mistake #4, `docker compose exec` causes serialization failures when a second Odoo process writes to the same DB. Using `run --rm` creates a fresh container.
- **Separate docker/dev/ directory** - Completely independent from existing `docker/docker-compose.yml` (ephemeral validation) to prevent port conflicts, volume collisions, and accidental data loss.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Docker images are pulled automatically on first run.

## Next Phase Readiness

- Dev instance config ready for Plan 15-02 (unit tests + Docker integration tests)
- All scripts syntactically validated and executable
- XML-RPC smoke test ready for live instance verification in 15-02
- Phase 16 (Odoo MCP Server) can connect to this instance via XML-RPC at localhost:8069

## Self-Check: PASSED

All 6 created files verified on disk. All 3 task commits verified in git log.

---
*Phase: 15-odoo-dev-instance*
*Completed: 2026-03-04*
