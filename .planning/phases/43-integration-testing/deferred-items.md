# Deferred Items - Phase 43

## 1. Security render stage fails when audit model present alongside approval record rules

**Discovered during:** Task 1 (kitchen sink rendering exploration)
**Severity:** Medium
**Scope:** Pre-existing bug in render pipeline

**Description:** When audit is enabled (which synthesizes an `audit.trail.log` companion model), the security render stage (`render_security`) fails with:
```
render_security failed: 'dict object' has no attribute 'record_rule_scopes'
```

The audit preprocessor adds `audit.trail.log` to `spec["models"]` AFTER the security preprocessor has already run. The security preprocessor enriches models with `record_rule_scopes`, but the audit log model is added later and never gets this attribute. The `record_rules.xml.j2` template then tries to access `model.record_rule_scopes` on the unenriched audit model, causing the failure.

**Impact:** When audit is enabled alongside approval, `record_rules.xml`, `data/mail_template_data.xml`, `data/data.xml`, `demo/demo_data.xml`, `tests/`, and `static/` are NOT generated because the pipeline stops at the security stage. The manifest still references these missing files.

**Workaround used in tests:** Pairwise tests that need these files (approval+notifications, security+approval) do NOT include audit, so the security stage succeeds and all files are generated correctly.

**Fix suggestion:** Either (a) move audit model synthesis before security preprocessing, or (b) add `record_rule_scopes: []` as a default to the synthesized audit log model dict.
