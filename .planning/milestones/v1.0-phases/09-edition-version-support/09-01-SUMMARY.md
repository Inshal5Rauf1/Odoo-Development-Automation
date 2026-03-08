---
phase: 09-edition-version-support
plan: 01
subsystem: edition-detection
tags: [enterprise, community, oca, registry, edition-check]
dependency_graph:
  requires: []
  provides: [enterprise-registry, edition-checker]
  affects: [spec-validation, cli]
tech_stack:
  added: []
  patterns: [json-registry, module-level-cache]
key_files:
  created:
    - python/src/odoo_gen_utils/data/enterprise_modules.json
    - python/src/odoo_gen_utils/edition.py
    - python/tests/test_edition.py
  modified: []
decisions:
  - JSON data file for Enterprise registry (not hardcoded Python)
  - Module-level caching for registry to avoid repeated file I/O
  - community_alternative as nullable object (null when no OCA equivalent)
metrics:
  duration: 2 min
  completed: "2026-03-03T04:27:00Z"
  tasks_completed: 1
  tasks_total: 1
  test_count: 9
  test_pass: 9
---

# Phase 9 Plan 01: Enterprise Module Registry & Edition Checker Summary

Enterprise module registry JSON with 31 entries and edition-check functions that detect EE dependencies and suggest OCA Community alternatives.

## Tasks Completed

| # | Task | Type | Commit | Key Files |
|---|------|------|--------|-----------|
| 1 | Enterprise module registry JSON + edition.py with tests | auto (TDD) | 80af540 (RED), eacb883 (GREEN) | enterprise_modules.json, edition.py, test_edition.py |

## What Was Built

### Enterprise Module Registry (`data/enterprise_modules.json`)
- 31 Enterprise-only module entries organized by category (Accounting, Services, HR, Manufacturing, Marketing, Websites, Productivity, Customization, Views, Other)
- Each entry has: `display_name`, `category`, `description`, `community_alternative`
- OCA alternatives provided for 9 modules (helpdesk, account_asset, planning, field_service, quality_control, quality, documents, rental, sale_subscription)
- Remaining 22 modules have `community_alternative: null` (no known OCA equivalent)

### Edition Checker (`edition.py`)
- `load_enterprise_registry(registry_path=None)` -- Loads and caches the JSON registry with module-level caching
- `check_enterprise_dependencies(depends, registry_path=None)` -- Checks a dependency list against the registry, returns warning dicts with module name, display name, category, alternative, alternative_repo, and notes

### Test Coverage (`test_edition.py`)
- 9 test cases covering: registry loading, known modules present, required keys validation, EE dep flagging, community alternatives, no-alternative case, clean deps, multiple EE deps, default registry path

## Deviations from Plan

None -- plan executed exactly as written.

## Discovered Issues (Out of Scope)

- Pre-existing test failure in `test_renderer.py::TestRenderModuleWizards::test_wizards_spec_generates_wizards_init` -- caused by templates already being reorganized into version directories (17.0/, 18.0/, shared/) from a prior phase. The test uses `get_template_dir()` which now points to the parent `templates/` directory instead of a version-specific subdirectory. This is NOT caused by Plan 09-01 changes. Will be addressed in Plan 09-02 (template and renderer changes).

## Verification

```
cd python && uv run pytest tests/test_edition.py -x -v
# Result: 9 passed in 0.01s

cd python && uv run pytest tests/ -x -q --ignore=tests/test_renderer.py
# Result: 192 passed (pre-existing renderer test excluded)
```
