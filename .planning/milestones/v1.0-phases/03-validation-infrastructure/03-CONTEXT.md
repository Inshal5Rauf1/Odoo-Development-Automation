# Phase 3: Validation Infrastructure - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Build validation infrastructure so any Odoo module can be checked against real Odoo 17.0 and OCA quality standards. Delivers: pylint-odoo integration, Docker-based Odoo 17.0 environment for install/test, structured reporting, and pattern-based error diagnosis.

Requirements: QUAL-01, QUAL-02, QUAL-03, QUAL-04, QUAL-05, QUAL-07, QUAL-08

</domain>

<decisions>
## Implementation Decisions

### Docker Environment Setup
- **Ephemeral docker-compose**: Official `odoo:17.0` + `postgres:16` images. Spin up per validation run, tear down after. Clean state prevents false positives from previous runs.
- **Graceful degradation**: If Docker is not available, skip Docker validation and only run pylint-odoo. Warn user but don't block.
- **docker-compose.yml** shipped with the extension at `~/.claude/odoo-gen/docker/`. Module directory is bind-mounted as an addon path.

### Validation Output & Reporting
- **Structured 3-section report**:
  1. pylint-odoo violations: table with file:line, rule code, severity, message
  2. Docker install result: pass/fail + parsed error if failed
  3. Test results: per test case pass/fail
- **Summary header** with pass/fail counts per section
- Agent-readable format so auto-fix loops (Phase 7) can parse and act on results

### pylint-odoo Integration
- **Full OCA ruleset** by default (~80+ rules) — that's the quality bar we set
- **Installed in extension's Python venv** (not Docker) — faster, no container needed for static analysis
- **`.pylintrc-odoo` support**: Users can place a config file in their module directory to override/disable specific rules
- Output parsed into structured format (JSON or table) for agent consumption

### Error Diagnosis Quality
- **Pattern-based diagnosis**: Library of ~20-30 common Odoo error patterns mapped to human-readable explanations and suggested fixes
- Examples: `KeyError: 'field_name'` → "Field referenced in view but not defined in model", `ParseError` → "XML syntax error in view file"
- **Unrecognized errors**: Show raw traceback with relevant file highlighted
- Phase 3 scope: good diagnosis, not perfect. Phase 7 (auto-fix loops) builds on this foundation.

### Claude's Discretion
- Exact docker-compose.yml configuration and volume mounts
- Error pattern library content (which 20-30 patterns to include)
- pylint-odoo output parsing implementation
- Report formatting details (markdown tables, JSON, or custom format)
- Python CLI subcommands for validation (`odoo-gen-utils validate`, `odoo-gen-utils docker-test`)

</decisions>

<specifics>
## Specific Ideas

- The `/odoo-gen:validate` command activates the `odoo-validator` agent (currently a stub from Phase 1) — Phase 3 implements it fully
- Docker startup can be slow (~10-30 seconds) — consider pulling images during install.sh as an optional step
- pylint-odoo needs the module's Python dependencies importable — may need to install the module's requirements in the venv or use Docker for import-dependent checks
- Error pattern library should be a separate data file (JSON/YAML) so it's extensible without code changes
- The validation report becomes input for Phase 7's auto-fix loops — design the format with machine-readability in mind

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-validation-infrastructure*
*Context gathered: 2026-03-02*
