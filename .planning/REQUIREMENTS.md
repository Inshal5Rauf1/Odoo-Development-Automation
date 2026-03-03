# Requirements: v1.1 Tech Debt Cleanup

## Tech Debt Resolution

- [x] **DEBT-01**: GitHub CLI is authenticated and search/extend features can query the GitHub API successfully
- [ ] **DEBT-02**: sentence-transformers with PyTorch CPU-only installs cleanly in a fresh venv and ChromaDB indexing works end-to-end
- [ ] **DEBT-03**: Docker validation runs against a live Odoo 17.0 daemon — module install and test execution verified with real containers (not just mocked subprocess)
- [ ] **DEBT-04**: Python field `string=` parameter translations are extracted by the i18n extractor into the .pot file

## Future Requirements

(Deferred to v1.2+)

## Out of Scope

- New features, commands, or agents — v1.1 is hardening only
- Odoo 18.0 Docker validation — 17.0 first
- Performance optimization — not needed at current scale

## Traceability

| Req | Phase | Plan | Status |
|-----|-------|------|--------|
| DEBT-01 | 10 | — | Pending |
| DEBT-02 | 10 | — | Pending |
| DEBT-03 | 11 | — | Pending |
| DEBT-04 | 11 | — | Pending |
