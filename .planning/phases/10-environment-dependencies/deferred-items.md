# Phase 10: Deferred Items

## Pre-existing Issues (Out of Scope)

1. **test_wizard.py collection error**: `tests/test_wizard.py` imports `odoo_gen_utils.search.wizard` which does not exist yet. This module is planned for Plan 10-02 (auth setup wizard). The test file was committed before its implementation module. All test runs must use `--ignore=tests/test_wizard.py` until Plan 10-02 is complete.
