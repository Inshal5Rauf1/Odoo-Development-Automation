# Phase 10: Environment & Dependencies - Research

**Researched:** 2026-03-03
**Domain:** GitHub CLI authentication, PyTorch CPU-only install via uv, ChromaDB + sentence-transformers on clean machines
**Confidence:** HIGH

## Summary

Phase 10 resolves two tech debt items: DEBT-01 (GitHub CLI authentication for search/extend) and DEBT-02 (sentence-transformers CPU-only clean install). Both features have working code with 243 passing tests, but the external dependencies (gh auth, PyTorch download, model download, ChromaDB persistence) were never validated on a clean machine.

The existing codebase already handles authentication correctly -- `get_github_token()` checks `GITHUB_TOKEN` env var first, then falls back to `gh auth token`. The `pyproject.toml` already has the correct uv index configuration for CPU-only PyTorch. The main work is verification, documentation, and graceful error handling when these external dependencies are missing or misconfigured.

**Primary recommendation:** Write end-to-end integration tests that exercise the real external dependencies (gh CLI, PyTorch install, model download, ChromaDB persistence) rather than mocking them, and add a setup/troubleshooting guide.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEBT-01 | GitHub CLI is authenticated and search/extend features can query the GitHub API successfully | gh auth patterns documented below; existing `get_github_token()` already implements the correct fallback chain (GITHUB_TOKEN env -> gh auth token); needs end-to-end verification and error message improvements |
| DEBT-02 | sentence-transformers with PyTorch CPU-only installs cleanly in a fresh venv and ChromaDB indexing works end-to-end | uv index config already correct in pyproject.toml; ChromaDB uses ONNX all-MiniLM-L6-v2 by default (not sentence-transformers directly); needs clean venv verification and model download testing |
</phase_requirements>

## Standard Stack

### Core (Already in pyproject.toml)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyGithub | >=2.8 | GitHub API calls for OCA repo crawling | Used by `build_oca_index()` to list repos, get branches, read manifests |
| chromadb | >=1.5 | Vector storage for semantic search | Local persistent vector DB; uses ONNX all-MiniLM-L6-v2 by default |
| sentence-transformers | >=5.2 | Embedding generation | Listed as dependency but ChromaDB may use its own ONNX embedding |
| torch | >=2.6 | PyTorch CPU-only (sentence-transformers dependency) | ~200MB CPU wheel via pytorch-cpu index |
| gitpython | >=3.1 | Git operations for fork/clone | Used by `clone_oca_module()` sparse checkout |
| click | >=8.0 | CLI framework | All CLI commands defined via Click |

### External Tools
| Tool | Purpose | How Used |
|------|---------|----------|
| gh CLI | GitHub authentication + fallback search | `gh auth token` for token retrieval; `gh search repos` for fallback |
| uv | Python package manager | Manages venv creation and package install with CPU-only PyTorch index |
| git | Version control + sparse checkout | Used by gitpython for OCA module cloning |

### No Alternatives Needed
All libraries are locked decisions from v1.0. This phase verifies they work, not replaces them.

**Installation:**
```bash
uv venv
uv pip install -e ".[search,test]"
```

## Architecture Patterns

### Existing Authentication Chain (DO NOT CHANGE)
```python
# Source: python/src/odoo_gen_utils/search/index.py lines 34-56
def get_github_token() -> str | None:
    """Check GITHUB_TOKEN env var first, then gh auth token."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None
```

This is the correct pattern. The chain is: `GITHUB_TOKEN` env var -> `gh auth token` -> `None`.

### gh CLI Authentication Methods (for documentation/setup guide)

| Method | Command | When to Use |
|--------|---------|-------------|
| Interactive browser OAuth | `gh auth login` | Developer machines (recommended) |
| Token via stdin | `echo $TOKEN \| gh auth login --with-token` | CI/automation |
| Environment variable only | `export GH_TOKEN=...` | Headless; gh uses GH_TOKEN directly, no login needed |
| GITHUB_TOKEN env var | `export GITHUB_TOKEN=...` | Our code reads this directly via `get_github_token()` |

**Key insight:** `GH_TOKEN` and `GITHUB_TOKEN` are different. `GH_TOKEN` is what `gh` CLI reads natively. `GITHUB_TOKEN` is what our code reads in `get_github_token()`. Both work because our code checks `GITHUB_TOKEN` first, then falls back to `gh auth token` (which uses `GH_TOKEN` or the stored credential).

### ChromaDB Default Embedding Model

ChromaDB uses its own ONNX-format `all-MiniLM-L6-v2` model by default, NOT sentence-transformers directly. When you call `collection.query(query_texts=[...])` without specifying an embedding function, ChromaDB:

1. Downloads a ~22MB ONNX model from Chroma's S3 bucket (first time only)
2. Caches it locally in `~/.cache/chroma/onnx_models/`
3. Uses onnxruntime (bundled with chromadb) to generate 384-dim embeddings

This means sentence-transformers + torch may be an unnecessary dependency for ChromaDB's default embedding. However, since it is listed in pyproject.toml `[search]` extras and may be used elsewhere, we verify it installs correctly but note this finding.

### ChromaDB Persistence Pattern (Already Correct)
```python
# Used in both index.py and query.py
client = chromadb.PersistentClient(path=db_path)
collection = client.get_or_create_collection(
    name="odoo_modules",
    metadata={"hnsw:space": "cosine"},
)
```

Default path: `~/.local/share/odoo-gen/chromadb/`

### Anti-Patterns to Avoid
- **DO NOT change the auth chain** -- it already handles all scenarios correctly
- **DO NOT remove sentence-transformers from deps** without verifying ChromaDB embedding works without it -- the ONNX default may have edge cases
- **DO NOT use `gh auth login` in tests** -- use `GITHUB_TOKEN` env var for test auth
- **DO NOT test against production OCA org in CI** -- rate limits (10 req/min for search API, 5000/hr for REST API with token)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GitHub token management | Custom token store/keyring | `gh auth token` + `GITHUB_TOKEN` env var | gh CLI handles OAuth, refresh, secure storage |
| PyTorch CPU-only resolution | Manual wheel downloads | uv `[[tool.uv.index]]` with `explicit = true` | uv resolves the correct CPU wheel automatically |
| Embedding generation | Custom ONNX loading | ChromaDB's default embedding function | Already bundles and caches the model |
| SQLite version checking | Manual sqlite3 version check | Python 3.12 ships sqlite3 >= 3.35 | Python 3.12 requirement in pyproject.toml solves this |
| Model caching | Custom download/cache logic | HuggingFace Hub / ChromaDB auto-cache | Both handle download, cache, and versioning |

**Key insight:** The existing code already does the right thing for all of these. Phase 10 is about verification and documentation, not new implementation.

## Common Pitfalls

### Pitfall 1: SQLite3 Version Too Old for ChromaDB
**What goes wrong:** ChromaDB requires sqlite3 >= 3.35.0. Older systems (Debian Bullseye, Ubuntu 20.04) ship with older sqlite3.
**Why it happens:** sqlite3 is compiled into the Python binary, not pip-installable.
**How to avoid:** The project requires Python >=3.12 which ships with sqlite3 3.39+. This is already enforced in pyproject.toml. Document this requirement clearly.
**Warning signs:** Error message: "Your system has an unsupported version of sqlite3. Chroma requires sqlite3 >= 3.35.0"

### Pitfall 2: First Run Downloads ~200MB+ of Models/Packages
**What goes wrong:** First `build-index` or `search-modules` triggers model download (22MB ONNX model) plus PyTorch CPU wheel is ~200MB. Users on slow connections or behind corporate firewalls may time out.
**Why it happens:** Models are lazy-downloaded on first use, not at pip install time.
**How to avoid:** Document expected first-run behavior. Add a `--dry-run` or pre-download step. Ensure error messages mention network requirements.
**Warning signs:** Hangs on first query with no output; timeout errors from HuggingFace/S3.

### Pitfall 3: gh CLI Not Installed vs Not Authenticated
**What goes wrong:** `get_github_token()` returns None for two different reasons: (a) gh not installed (`FileNotFoundError`), (b) gh installed but not authenticated (returncode != 0). The error message should distinguish these.
**Why it happens:** Both cases are caught silently and return None.
**How to avoid:** Improve error messages in CLI commands to distinguish "gh not found -- install from https://cli.github.com/" vs "gh not authenticated -- run: gh auth login".
**Warning signs:** Generic "GitHub token required" message with no actionable guidance.

### Pitfall 4: GH_TOKEN vs GITHUB_TOKEN Confusion
**What goes wrong:** User sets `GH_TOKEN` (what gh CLI reads) but our code checks `GITHUB_TOKEN`. Or vice versa.
**Why it happens:** Two different env var conventions. gh CLI reads `GH_TOKEN`; many tools (including ours) read `GITHUB_TOKEN`.
**How to avoid:** Our `get_github_token()` handles this correctly -- it checks `GITHUB_TOKEN` first, then falls back to `gh auth token` (which reads `GH_TOKEN` or stored creds). Document both options.
**Warning signs:** "Token required" even though user thinks they set it.

### Pitfall 5: ChromaDB PersistentClient Path Permissions
**What goes wrong:** `~/.local/share/odoo-gen/chromadb/` doesn't exist or isn't writable.
**Why it happens:** First run on a clean machine; parent directories may not exist.
**How to avoid:** `PersistentClient` creates the directory, but parent dirs must exist. Verify `Path.home() / ".local" / "share"` exists. Add mkdir -p in setup guide.
**Warning signs:** `OSError: [Errno 2] No such file or directory` or permission denied.

### Pitfall 6: GitHub API Rate Limiting During Index Build
**What goes wrong:** OCA has 200+ repos. Building the full index makes hundreds of API calls and may hit rate limits.
**Why it happens:** GitHub REST API: 5000 req/hr with token, 60/hr without. Search API: 10 req/min.
**How to avoid:** The code uses PyGithub which handles rate limit headers. Ensure token is always provided (never unauthenticated). Build takes 3-5 minutes with token.
**Warning signs:** 403 errors, slow progress, incomplete index.

## Code Examples

### Verifying gh CLI Auth (for integration test)
```python
import subprocess

def check_gh_auth_status() -> dict:
    """Check gh CLI authentication status."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        return {
            "installed": True,
            "authenticated": result.returncode == 0,
            "output": result.stdout + result.stderr,
        }
    except FileNotFoundError:
        return {"installed": False, "authenticated": False, "output": ""}
```

### Clean Venv Install Verification (for integration test)
```bash
# Create fresh venv, install search extras, verify imports
uv venv /tmp/odoo-gen-test-venv
VIRTUAL_ENV=/tmp/odoo-gen-test-venv uv pip install -e ".[search]"
/tmp/odoo-gen-test-venv/bin/python -c "
import chromadb; print(f'chromadb {chromadb.__version__}')
import torch; print(f'torch {torch.__version__}')
from sentence_transformers import SentenceTransformer; print('sentence-transformers OK')
print('All imports successful')
"
```

### End-to-End Index Build + Search Test
```python
import tempfile
from odoo_gen_utils.search.index import build_oca_index, get_index_status, get_github_token

def test_e2e_index_and_search():
    token = get_github_token()
    assert token, "GitHub token required for e2e test"

    with tempfile.TemporaryDirectory() as tmp:
        # Build index (will take 3-5 min with real API)
        count = build_oca_index(token=token, db_path=tmp)
        assert count > 0, "Should index at least some modules"

        status = get_index_status(db_path=tmp)
        assert status.exists
        assert status.module_count > 0

        # Search the index
        from odoo_gen_utils.search.query import search_modules
        results = search_modules("inventory management", db_path=tmp)
        assert len(results) > 0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| chromadb default ONNX embedding | Still current (chromadb >=1.5) | Stable | No sentence-transformers needed for default embedding |
| `gh auth login --with-token` for CI | `GH_TOKEN` env var (no login needed) | gh CLI 2.x | Simpler headless auth |
| Manual PyTorch CPU wheel URLs | uv `[[tool.uv.index]]` with `explicit = true` | uv 0.4+ | Declarative in pyproject.toml |

**Deprecated/outdated:**
- `GITHUB_TOKEN` is the older env var name; `GH_TOKEN` is preferred by gh CLI, but both work through our fallback chain
- ChromaDB `Client(Settings(persist_directory=...))` is the old API; `PersistentClient(path=...)` is current (already used)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | `python/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd python && uv run pytest tests/ -x -q` |
| Full suite command | `cd python && uv run pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBT-01a | `gh auth status` succeeds | integration (manual-only: requires real gh auth) | `gh auth status` | N/A - shell command |
| DEBT-01b | `search-modules` returns results from GitHub API | integration | `cd python && uv run pytest tests/test_e2e_github.py -x` | Wave 0 |
| DEBT-01c | `get_github_token()` error messages are actionable | unit | `cd python && uv run pytest tests/test_search_index.py -x -k github_token` | Partial (existing tests mock subprocess) |
| DEBT-02a | `uv pip install .[search]` in fresh venv | integration (manual-only: requires clean venv) | `uv venv /tmp/test && uv pip install -e ".[search]"` | N/A - shell command |
| DEBT-02b | `build-index` crawls OCA and builds ChromaDB | integration | `cd python && uv run pytest tests/test_e2e_index.py -x` | Wave 0 |
| DEBT-02c | `index-status` reports count > 0 | integration | `cd python && uv run pytest tests/test_e2e_index.py -x -k index_status` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && uv run pytest tests/ -x -q` (existing 243 tests, < 30s)
- **Per wave merge:** `cd python && uv run pytest tests/ -v` (full suite)
- **Phase gate:** Full suite green + manual e2e verification of success criteria

### Wave 0 Gaps
- [ ] `tests/test_e2e_github.py` -- integration test for DEBT-01 (real GitHub API, skipped without token)
- [ ] `tests/test_e2e_index.py` -- integration test for DEBT-02 (real ChromaDB build + query, skipped without token)
- [ ] Mark e2e tests with `@pytest.mark.e2e` and add marker to pytest config so they can be skipped in CI

## Open Questions

1. **Is sentence-transformers actually needed?**
   - What we know: ChromaDB uses its own ONNX all-MiniLM-L6-v2 by default, not sentence-transformers
   - What's unclear: Whether any code path in the project actually uses sentence-transformers directly (vs ChromaDB's built-in)
   - Recommendation: Verify during implementation. If only ChromaDB default embedding is used, sentence-transformers + torch could potentially be dropped from `[search]` extras, saving ~200MB. But this is a v1.2+ optimization, not v1.1 scope.

2. **How long does full OCA index build take?**
   - What we know: OCA has 200+ repos, each requiring multiple API calls
   - What's unclear: Exact time and API call count on a real run
   - Recommendation: Time it during e2e testing. Document in setup guide. Consider indexing a subset (5 repos) for fast integration tests.

## Sources

### Primary (HIGH confidence)
- [gh auth login official docs](https://cli.github.com/manual/gh_auth_login) - authentication methods, --with-token flag
- [gh auth token official docs](https://cli.github.com/manual/gh_auth_token) - token retrieval for scripts
- [uv PyTorch integration guide](https://docs.astral.sh/uv/guides/integration/pytorch/) - CPU-only index configuration
- [ChromaDB Embedding Functions docs](https://docs.trychroma.com/docs/embeddings/embedding-functions) - default ONNX all-MiniLM-L6-v2
- [ChromaDB Troubleshooting docs](https://docs.trychroma.com/troubleshooting) - SQLite3 version, common issues
- Existing codebase: `python/src/odoo_gen_utils/search/index.py`, `query.py`, `cli.py` - verified current implementation

### Secondary (MEDIUM confidence)
- [sentence-transformers/all-MiniLM-L6-v2 on HuggingFace](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) - model size (~22MB), 384-dim output
- [ChromaDB FAQ / Cookbook](https://cookbook.chromadb.dev/faq/) - SQLite3 version workarounds, disk space issues
- [GitHub CLI issue #3799](https://github.com/cli/cli/issues/3799) - GH_TOKEN vs GITHUB_TOKEN behavior

### Tertiary (LOW confidence)
- Full OCA index build time estimate (3-5 minutes) -- based on CLAUDE.md lesson, needs real verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already chosen and in pyproject.toml, verified current versions
- Architecture: HIGH - existing code reviewed, patterns are correct and well-structured
- Pitfalls: HIGH - SQLite3, model download, rate limiting are well-documented issues with clear mitigations
- Auth patterns: HIGH - verified against official gh CLI docs

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (30 days - stable domain, no fast-moving dependencies)
