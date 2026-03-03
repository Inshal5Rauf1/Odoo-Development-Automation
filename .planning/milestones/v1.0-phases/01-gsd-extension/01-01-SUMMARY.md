---
phase: 01-gsd-extension
plan: 01
subsystem: infra
tags: [bash, installer, odoo, agents, gsd-extension, jinja2, uv, python-venv]

# Dependency graph
requires: []
provides:
  - Extension installer script (install.sh) with prerequisite checks and venv setup
  - Odoo-specific config defaults (defaults.json) for odoo_version, edition, output_dir, api_keys
  - Version tracking file (VERSION 0.1.0)
  - 6 agent definitions (1 active scaffold agent, 5 stubs for future phases)
  - Wrapper script pattern for venv-isolated Python CLI
affects: [01-02, 01-03, 01-04, 02-knowledge-base, 03-validation, 05-code-generation, 06-security-test]

# Tech tracking
tech-stack:
  added: [bash, uv, python-3.12-venv]
  patterns: [gsd-agent-frontmatter, extension-installer, symlink-agents, wrapper-script-venv]

key-files:
  created:
    - install.sh
    - VERSION
    - defaults.json
    - agents/odoo-scaffold.md
    - agents/odoo-model-gen.md
    - agents/odoo-view-gen.md
    - agents/odoo-security-gen.md
    - agents/odoo-test-gen.md
    - agents/odoo-validator.md
  modified: []

key-decisions:
  - "Symlinks for agents (ln -sf) instead of copy -- agents stay in extension dir, discoverable via ~/.claude/agents/"
  - "Wrapper script at bin/odoo-gen-utils resolves venv path portably across platforms"
  - "defaults.json api_keys uses $ENV_VAR references resolved at runtime -- never stores secrets"
  - "odoo-scaffold agent includes comprehensive Odoo 17.0 specifics to prevent version-specific syntax errors"

patterns-established:
  - "GSD agent frontmatter: name, description, tools, color fields in YAML"
  - "Extension installer pattern: prereq checks -> venv -> install -> register -> verify"
  - "Agent symlink pattern: source in extension dir, symlink in ~/.claude/agents/"
  - "Manifest tracking: odoo-gen-manifest.json records all installed files for clean uninstall"

requirements-completed: [EXT-01, EXT-03, EXT-04]

# Metrics
duration: 4min
completed: 2026-03-01
---

# Phase 1 Plan 1: Extension Structure and Agent Definitions Summary

**install.sh with GSD/uv/Python 3.12 prerequisite checks, Odoo config defaults, and 6 agent definitions (scaffold agent with full Odoo 17.0 system prompt + 5 phase-gated stubs)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-01T18:11:50Z
- **Completed:** 2026-03-01T18:16:26Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- install.sh handles complete extension lifecycle: prerequisite checks (GSD, uv, Python 3.12), venv creation, package installation, command registration, agent symlinking, manifest writing, and post-install verification
- defaults.json provides Odoo-specific configuration with env var references for API keys (no hardcoded secrets)
- odoo-scaffold agent has comprehensive system prompt covering spec inference from natural language, user confirmation, template rendering via odoo-gen-utils, and Odoo 17.0 version-specific rules
- 5 stub agents each document their purpose, activation phase, and suggest available alternatives

## Task Commits

Each task was committed atomically:

1. **Task 1: Create extension directory structure, install.sh, VERSION, and defaults.json** - `d6684c1` (feat) -- pre-existing commit from prior execution attempt; files verified to match plan exactly
2. **Task 2: Create all 6 Odoo agent definitions** - `0c20435` (feat)

## Files Created/Modified
- `install.sh` - Extension installer with prerequisite checks, venv setup, command/agent registration, manifest writing
- `VERSION` - Extension version tracking (0.1.0)
- `defaults.json` - Odoo-specific global defaults (odoo_version, edition, output_dir, license, api_keys)
- `agents/odoo-scaffold.md` - Full scaffold agent with Odoo 17.0 system prompt
- `agents/odoo-model-gen.md` - Stub model generation agent (Phase 5)
- `agents/odoo-view-gen.md` - Stub view generation agent (Phase 5)
- `agents/odoo-security-gen.md` - Stub security generation agent (Phase 6)
- `agents/odoo-test-gen.md` - Stub test generation agent (Phase 6)
- `agents/odoo-validator.md` - Stub validation agent (Phase 3)

## Decisions Made
- Used symlinks (`ln -sf`) for agent registration instead of copying -- keeps agents in extension directory for easier updates while remaining discoverable by Claude Code
- Created wrapper script at `bin/odoo-gen-utils` that resolves venv path portably -- solves tilde expansion and cross-platform path issues (Research Pitfall 4)
- Stored API key references as `$ENV_VAR` strings in defaults.json -- resolved at runtime by Python utility, never containing actual secrets
- Included comprehensive Odoo 17.0 specifics in scaffold agent prompt (tree vs list, inline modifiers vs attrs, version format, required manifest keys) to prevent the most common LLM hallucination patterns for Odoo code

## Deviations from Plan

None - plan executed exactly as written. Task 1 files were found to already exist from a prior partial execution attempt (commit d6684c1) with identical content matching the plan specification.

## Issues Encountered
- Task 1 files (install.sh, VERSION, defaults.json) already existed in git from a previous partial execution (commits d6684c1, 3acfe4b). Verified content matches plan exactly, so no re-commit was needed. Task 2 (agent files) was the only new work.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Extension structure established; install.sh ready for end-to-end testing once Python package exists
- Agent files ready for symlinking; odoo-scaffold provides complete system prompt for module scaffolding
- Plan 01-02 (commands) can proceed to register slash commands
- Plan 01-03 (Python package) can proceed to implement odoo-gen-utils CLI
- Plan 01-04 (templates) can proceed to create Jinja2 templates

## Self-Check: PASSED

All 10 files verified as existing on disk. Both commit hashes (d6684c1, 0c20435) verified in git history.

---
*Phase: 01-gsd-extension*
*Completed: 2026-03-01*
