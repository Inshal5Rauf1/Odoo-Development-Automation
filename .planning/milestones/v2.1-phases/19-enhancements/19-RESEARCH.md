# Phase 19: Enhancements - Research

**Researched:** 2026-03-04
**Domain:** Context7 MCP integration + artifact state tracking for code generation pipeline
**Confidence:** MEDIUM-HIGH

## Summary

Phase 19 covers two independent enhancements: (1) MCP-05 -- integrating Context7 MCP for on-demand Odoo API documentation queries, and (2) OBS-01 -- tracked artifact state metadata for the generation pipeline. These are architecturally independent features that can be planned and implemented in parallel.

For MCP-05, Context7 provides a REST API (`GET https://context7.com/api/v2/libs/search` and `GET https://context7.com/api/v2/context`) that can be called from Python using only `urllib.request` (stdlib). This avoids adding new dependencies. The integration should be a thin client class that wraps Context7 REST calls, with the knowledge base remaining the primary source and Context7 supplementing it. Graceful fallback when Context7 is unavailable is mandatory -- the system must work without it configured.

For OBS-01, artifact state tracking (pending/generated/validated/approved) should be stored as a JSON sidecar file alongside the generated module, following the immutable read-transform-write pattern established in the project's auto-fix code. The state tracker should be a standalone module with no coupling to the generation pipeline, making it safe to fail without blocking generation.

**Primary recommendation:** Use Context7 REST API via stdlib `urllib.request` (no new dependencies); store artifact state in a single JSON sidecar file per module with dataclass-backed state transitions.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCP-05 | Agents query Odoo 17.0/18.0 API docs on demand via Context7 MCP; knowledge base primary, Context7 supplements; works without Context7 (graceful fallback) | Context7 REST API documented; Python client pattern established; graceful fallback follows EnvironmentVerifier pattern |
| OBS-01 | Each artifact (model, view, security, test) has tracked state (pending, generated, validated, approved) stored as structured metadata; visible via CLI output or log; state tracking does not block generation if it fails | JSON sidecar pattern researched; dataclass state model matches project conventions; Click CLI output pattern established |
</phase_requirements>

## Standard Stack

### Core (No new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| urllib.request (stdlib) | Python 3.12 | HTTP client for Context7 REST API | Zero-dependency approach; avoids adding httpx/requests for 2 HTTP calls |
| json (stdlib) | Python 3.12 | Parse Context7 API responses; serialize artifact state | Already used throughout codebase |
| dataclasses (stdlib) | Python 3.12 | ArtifactState dataclass, frozen immutable records | Project convention (OdooConfig, VerificationWarning, Violation) |
| logging (stdlib) | Python 3.12 | State transitions and Context7 query logging | Project convention |
| pathlib (stdlib) | Python 3.12 | Sidecar file paths for state tracking | Project convention |
| click | >=8.0 | CLI output for artifact state display | Already a core dependency |

### Supporting (Already in project)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.0 | Unit tests for both features | All new code |
| unittest.mock | stdlib | Mock Context7 HTTP responses | Test isolation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| urllib.request | httpx or requests | Adds dependency for 2 HTTP calls; overkill for simple GET requests |
| urllib.request | mcp Python SDK (ClientSession) | Requires running Context7 as stdio subprocess; heavier than REST API; mcp is optional dep |
| JSON sidecar file | SQLite database | Overkill for per-module state; adds complexity; JSON is human-readable |
| JSON sidecar file | YAML metadata | Would require PyYAML dependency; JSON is already used everywhere |
| Single JSON file | Per-artifact files | More file clutter; single file is atomic and easier to manage |

**Installation:**
```bash
# No new dependencies needed. Both features use stdlib only.
# Existing: jinja2>=3.1, click>=8.0, pylint-odoo>=10.0
```

## Architecture Patterns

### Recommended Project Structure

```
python/src/odoo_gen_utils/
├── context7.py              # Context7 REST API client (MCP-05)
├── artifact_state.py        # Artifact state tracker (OBS-01)
├── cli.py                   # Extended with state display commands
├── renderer.py              # Extended to emit state transitions
├── knowledge/               # Existing - remains primary source
├── mcp/                     # Existing MCP server (XML-RPC to Odoo)
│   ├── server.py            # Unchanged
│   └── odoo_client.py       # Unchanged
└── ...

python/tests/
├── test_context7.py         # Context7 client unit tests
├── test_artifact_state.py   # State tracker unit tests
└── ...
```

### Pattern 1: Context7 REST Client (MCP-05)

**What:** A thin Python class that queries Context7's REST API for Odoo documentation, returning structured results.

**When to use:** During module generation, when agents need supplementary Odoo API documentation beyond the static knowledge base.

**Example:**
```python
# Source: Context7 REST API docs (https://context7.com/docs/api-guide)
import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass

logger = logging.getLogger("odoo-gen.context7")

@dataclass(frozen=True)
class Context7Config:
    """Configuration for Context7 REST API access."""
    api_key: str = ""
    base_url: str = "https://context7.com/api/v2"
    timeout: int = 10  # seconds

@dataclass(frozen=True)
class DocSnippet:
    """A single documentation snippet from Context7."""
    title: str
    content: str
    source_url: str = ""

class Context7Client:
    """REST client for Context7 documentation API.

    Provides on-demand Odoo API documentation lookups.
    All methods return empty results on failure (never raise).
    """

    def __init__(self, config: Context7Config | None = None) -> None:
        self._config = config or Context7Config()
        self._odoo_library_id: str | None = None  # cached after first resolve

    @property
    def is_configured(self) -> bool:
        """Whether Context7 API key is set."""
        return bool(self._config.api_key)

    def resolve_odoo_library(self) -> str | None:
        """Resolve the Odoo library ID from Context7.

        Returns the Context7 library ID (e.g., '/odoo/odoo') or None.
        Caches result after first successful call.
        """
        if self._odoo_library_id is not None:
            return self._odoo_library_id
        # Call resolve API
        # Cache and return

    def query_docs(self, query: str) -> list[DocSnippet]:
        """Query Odoo documentation from Context7.

        Returns empty list on any failure (graceful fallback).
        """
        try:
            library_id = self.resolve_odoo_library()
            if not library_id:
                return []
            # Call context API, parse response
            return snippets
        except Exception as exc:
            logger.warning("Context7 query failed (degrading gracefully): %s", exc)
            return []

def build_context7_from_env() -> Context7Client:
    """Build Context7Client from CONTEXT7_API_KEY env var.

    Returns a client (possibly unconfigured) -- never raises.
    """
    import os
    api_key = os.environ.get("CONTEXT7_API_KEY", "")
    config = Context7Config(api_key=api_key)
    return Context7Client(config)
```

### Pattern 2: Artifact State Tracker (OBS-01)

**What:** A module that tracks the lifecycle state of each generated artifact (model, view, security, test) as structured JSON metadata.

**When to use:** During and after module generation, to provide observability into what has been generated, validated, and approved.

**Example:**
```python
# Source: Project convention (dataclass pattern from verifier.py, validation/types.py)
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

logger = logging.getLogger("odoo-gen.state")

class ArtifactKind(str, Enum):
    """Types of artifacts tracked in the generation pipeline."""
    MODEL = "model"
    VIEW = "view"
    SECURITY = "security"
    TEST = "test"
    MANIFEST = "manifest"
    DATA = "data"

class ArtifactStatus(str, Enum):
    """Lifecycle states for a generated artifact."""
    PENDING = "pending"
    GENERATED = "generated"
    VALIDATED = "validated"
    APPROVED = "approved"

@dataclass(frozen=True)
class ArtifactState:
    """Immutable state record for a single artifact."""
    kind: str          # ArtifactKind value
    name: str          # e.g., "inventory.item" or "ir.model.access.csv"
    file_path: str     # relative to module root
    status: str        # ArtifactStatus value
    updated_at: str    # ISO 8601 timestamp
    error: str = ""    # error message if validation failed

@dataclass
class ModuleState:
    """Mutable collection of artifact states for a module."""
    module_name: str
    artifacts: list[ArtifactState] = field(default_factory=list)

    def transition(self, kind: str, name: str, file_path: str,
                   new_status: str, error: str = "") -> "ModuleState":
        """Return a new ModuleState with the artifact transitioned.

        Immutable pattern: creates new list, does not mutate.
        """
        now = datetime.now(timezone.utc).isoformat()
        new_artifact = ArtifactState(
            kind=kind, name=name, file_path=file_path,
            status=new_status, updated_at=now, error=error,
        )
        # Replace existing or append
        new_artifacts = [
            a for a in self.artifacts
            if not (a.kind == kind and a.name == name)
        ]
        new_artifacts.append(new_artifact)
        return ModuleState(
            module_name=self.module_name,
            artifacts=new_artifacts,
        )

def save_state(state: ModuleState, module_path: Path) -> Path:
    """Write module state to .odoo-gen-state.json sidecar file."""
    state_path = module_path / ".odoo-gen-state.json"
    data = {
        "module_name": state.module_name,
        "artifacts": [asdict(a) for a in state.artifacts],
    }
    state_path.write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    return state_path

def load_state(module_path: Path) -> ModuleState | None:
    """Load module state from sidecar file, or None if not found."""
    state_path = module_path / ".odoo-gen-state.json"
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return ModuleState(
            module_name=data["module_name"],
            artifacts=[ArtifactState(**a) for a in data["artifacts"]],
        )
    except Exception as exc:
        logger.warning("Failed to load state (continuing without): %s", exc)
        return None
```

### Pattern 3: Graceful Fallback (Both Features)

**What:** Both MCP-05 and OBS-01 must degrade gracefully -- the existing generation pipeline must work unchanged when these features fail or are unconfigured.

**When to use:** Always. This is a mandatory architectural constraint.

**Example (follows existing EnvironmentVerifier pattern):**
```python
# Source: python/src/odoo_gen_utils/verifier.py (existing pattern)

# Context7 fallback: build client, check if configured, skip if not
c7 = build_context7_from_env()
if c7.is_configured:
    snippets = c7.query_docs("how to define mail.thread inheritance")
    # Use snippets to supplement knowledge base
else:
    # Knowledge base is the sole source -- no error, no warning
    pass

# State tracker fallback: wrap all state operations in try/except
try:
    state = state.transition("model", model_name, file_path, "generated")
    save_state(state, module_path)
except Exception as exc:
    logger.warning("State tracking failed (continuing): %s", exc)
    # Generation continues unblocked
```

### Anti-Patterns to Avoid

- **Making Context7 a required dependency:** Context7 is supplementary. The system MUST work without it. Never raise exceptions when Context7 is unavailable.
- **Blocking generation on state tracking failure:** OBS-01 explicitly states "state tracking does not block generation if it fails." Never put state operations in the critical path without try/except.
- **Storing state in the generated module's Python code:** State metadata belongs in a sidecar file, not inline comments or Python variables. Generated code should be clean Odoo code.
- **Adding async to the state tracker:** The existing codebase is synchronous. Don't introduce async for state tracking -- use synchronous JSON file I/O.
- **Using the MCP Python SDK to call Context7:** Context7 has a simple REST API. Don't add the complexity of spawning a Node.js subprocess via stdio transport. Use `urllib.request` GET calls directly.
- **Caching Context7 responses permanently:** Documentation changes. Cache the library ID (stable), but fetch fresh docs each time.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client for REST API | Custom socket/SSL handling | `urllib.request.urlopen` with `json.loads` | stdlib handles SSL, redirects, timeouts |
| State serialization | Custom file format parser | `json.dumps`/`json.loads` with `dataclasses.asdict` | JSON is human-readable, debuggable, and the project standard |
| ISO 8601 timestamps | Manual string formatting | `datetime.now(timezone.utc).isoformat()` | stdlib handles timezone and formatting correctly |
| Enum validation | Manual string checking | `str(Enum)` pattern with `ArtifactStatus`/`ArtifactKind` | Type-safe, catches typos at definition time |
| CLI state display | Manual print formatting | Click's `click.echo()` with formatted strings | Consistent with existing CLI commands |

**Key insight:** Both features are thin wrappers over stdlib capabilities. The complexity is in the integration points (where to call Context7, where to emit state transitions), not in the implementation of the features themselves.

## Common Pitfalls

### Pitfall 1: Context7 API Key Not Set = Silent Failure

**What goes wrong:** Developer expects Context7 docs but gets empty results because `CONTEXT7_API_KEY` is not set.
**Why it happens:** Context7 requires an API key from context7.com/dashboard. Unlike ODOO_URL which has obvious localhost defaults, there's no sensible default.
**How to avoid:** Log a clear INFO message at startup when Context7 is not configured: "Context7 not configured (CONTEXT7_API_KEY not set) -- using knowledge base only." Never log at WARNING level for expected unconfigured state.
**Warning signs:** Empty documentation results despite knowing Context7 has Odoo docs.

### Pitfall 2: Context7 Rate Limiting (HTTP 429)

**What goes wrong:** Context7 returns 429 Too Many Requests during heavy generation.
**Why it happens:** Context7 has rate limits, especially without an API key. Multiple rapid queries during module generation could hit the limit.
**How to avoid:** Cache the library ID resolution (it's stable). For doc queries, implement simple exponential backoff with max 2 retries. On persistent 429, fall back gracefully to knowledge base only.
**Warning signs:** Intermittent empty results from Context7 that work on retry.

### Pitfall 3: State File Corruption on Concurrent Access

**What goes wrong:** Two parallel generation processes write to the same `.odoo-gen-state.json` and corrupt it.
**Why it happens:** JSON read-modify-write is not atomic.
**How to avoid:** The project is single-user workflow (stated in OUT OF SCOPE). For safety, use `load_state() -> modify -> save_state()` with the entire file rewritten (not appended). If the file is corrupted on load, log a warning and start fresh.
**Warning signs:** JSON parse errors on load.

### Pitfall 4: Context7 Odoo Library ID Resolution Failure

**What goes wrong:** `resolve_odoo_library()` returns no match because the search term doesn't match Context7's index.
**Why it happens:** Context7 indexes libraries from GitHub. The Odoo library might be indexed under different names (e.g., "/odoo/odoo", "/odoo/documentation").
**How to avoid:** Try multiple search terms: "odoo", "odoo framework", "odoo development". Cache the first successful result. If all fail, log and fall back.
**Warning signs:** `resolve_odoo_library()` returning None despite Context7 being configured.

### Pitfall 5: State Transitions Out of Order

**What goes wrong:** An artifact jumps from "pending" to "approved" without going through "generated" and "validated".
**Why it happens:** The state machine has no enforced transition rules.
**How to avoid:** Define allowed transitions: pending -> generated -> validated -> approved. Log warnings (not errors) for out-of-order transitions but allow them (OBS-01 says "does not block generation"). The state is informational, not a gate.
**Warning signs:** State file shows "approved" artifacts that were never "validated".

### Pitfall 6: Mixing Sync and Async Code

**What goes wrong:** Developer uses `async def` for Context7 client because MCP server is async.
**Why it happens:** The existing MCP server uses FastMCP which is async. Context7 is conceptually similar.
**How to avoid:** The Context7 client is NOT an MCP server. It's a REST client used by the synchronous CLI and renderer. Keep it synchronous with `urllib.request`. The MCP server (mcp/server.py) is a separate concern.
**Warning signs:** `asyncio.run()` calls appearing in non-async code paths.

## Code Examples

### Context7 REST API Call (verified from official docs)

```python
# Source: https://context7.com/docs/api-guide
import json
import urllib.request
import urllib.error

def _context7_get(url: str, api_key: str, timeout: int = 10) -> dict | list | None:
    """Make a GET request to Context7 REST API.

    Returns parsed JSON or None on any failure.
    """
    req = urllib.request.Request(url)
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
            TimeoutError, OSError):
        return None

# Step 1: Resolve library ID
search_url = (
    "https://context7.com/api/v2/libs/search"
    "?libraryName=odoo&query=odoo+framework+development"
)
libraries = _context7_get(search_url, api_key="your-key")
# Returns list of dicts with 'id', 'name', 'description', etc.

# Step 2: Query docs
if libraries:
    library_id = libraries[0]["id"]  # e.g., "/odoo/odoo"
    context_url = (
        f"https://context7.com/api/v2/context"
        f"?libraryId={library_id}&query=mail.thread+inheritance"
    )
    docs = _context7_get(context_url, api_key="your-key")
    # Returns list of doc snippets with 'title', 'content', 'sourceUrl'
```

### Artifact State JSON Format

```json
{
  "module_name": "library_management",
  "artifacts": [
    {
      "kind": "model",
      "name": "library.book",
      "file_path": "models/library_book.py",
      "status": "generated",
      "updated_at": "2026-03-04T18:30:00+00:00",
      "error": ""
    },
    {
      "kind": "view",
      "name": "library.book",
      "file_path": "views/library_book_views.xml",
      "status": "generated",
      "updated_at": "2026-03-04T18:30:01+00:00",
      "error": ""
    },
    {
      "kind": "security",
      "name": "ir.model.access.csv",
      "file_path": "security/ir.model.access.csv",
      "status": "validated",
      "updated_at": "2026-03-04T18:31:00+00:00",
      "error": ""
    },
    {
      "kind": "test",
      "name": "library.book",
      "file_path": "tests/test_library_book.py",
      "status": "pending",
      "updated_at": "2026-03-04T18:29:00+00:00",
      "error": ""
    }
  ]
}
```

### CLI State Display Pattern

```python
# Source: Follows existing CLI patterns in python/src/odoo_gen_utils/cli.py
@main.command("show-state")
@click.argument("module_path", type=click.Path(exists=True))
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_state(module_path: str, json_output: bool) -> None:
    """Show artifact generation state for a module."""
    from odoo_gen_utils.artifact_state import load_state

    mod_path = Path(module_path).resolve()
    state = load_state(mod_path)

    if state is None:
        click.echo("No state file found. Module has not been tracked.")
        return

    if json_output:
        # ... JSON output
        return

    click.echo(f"Module: {state.module_name}")
    click.echo(f"Artifacts: {len(state.artifacts)}")
    click.echo()

    for artifact in sorted(state.artifacts, key=lambda a: a.kind):
        status_icon = {
            "pending": "[ ]",
            "generated": "[G]",
            "validated": "[V]",
            "approved": "[A]",
        }.get(artifact.status, "[?]")
        click.echo(f"  {status_icon} {artifact.kind:10s} {artifact.name}")
        if artifact.error:
            click.echo(f"       ERROR: {artifact.error}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MCP via stdio subprocess | Context7 REST API (v2) | 2025 | Simpler integration -- no Node.js subprocess needed |
| SSE transport for MCP | Streamable HTTP transport | 2025-06 | SSE being deprecated in favor of streamable HTTP |
| Ad-hoc file tracking | Structured JSON metadata | N/A (new to project) | Enables observability without workflow changes |
| Static knowledge base only | KB + live docs supplement | v2.1 (this phase) | Agents get up-to-date Odoo API info |

**Deprecated/outdated:**
- SSE transport in MCP: Being superseded by Streamable HTTP. Not relevant since we use REST API, not MCP transport.
- Context7 Node.js-only: Context7 now has a REST API (v2), so no need for npx or Node.js.

## Open Questions

1. **What is the exact Context7 library ID for Odoo?**
   - What we know: Context7 has an Odoo page (https://context7.com/odoo) and a resolve-library-id endpoint.
   - What's unclear: The exact library ID (could be "/odoo/odoo", "/odoo/documentation", or something else). Need to call the resolve API to discover.
   - Recommendation: During implementation, call `resolve-library-id` with "odoo" and inspect results. Cache the best match. Include a fallback list of known IDs to try.

2. **Does Context7 have Odoo 17.0-specific documentation?**
   - What we know: Context7 supports version-specific docs. A blog post mentions Odoo 17 docs.
   - What's unclear: Whether 17.0 and 18.0 are separate library entries or version-filtered.
   - Recommendation: Test during implementation. If version-specific, resolve both 17.0 and 18.0 library IDs.

3. **Should artifact state file be gitignored?**
   - What we know: `.odoo-gen-state.json` is runtime metadata, not source code.
   - What's unclear: Whether users would want to commit state for audit trail.
   - Recommendation: Add to `.gitignore` by default. Users can remove if they want to track it.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 |
| Config file | python/pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `cd python && .venv/bin/python -m pytest tests/test_context7.py tests/test_artifact_state.py -x` |
| Full suite command | `cd python && .venv/bin/python -m pytest -x` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-05a | Context7 client resolves Odoo library ID | unit | `pytest tests/test_context7.py::test_resolve_odoo_library -x` | No -- Wave 0 |
| MCP-05b | Context7 client queries docs and returns snippets | unit | `pytest tests/test_context7.py::test_query_docs_success -x` | No -- Wave 0 |
| MCP-05c | Context7 graceful fallback when unconfigured | unit | `pytest tests/test_context7.py::test_query_docs_unconfigured -x` | No -- Wave 0 |
| MCP-05d | Context7 graceful fallback on HTTP error | unit | `pytest tests/test_context7.py::test_query_docs_http_error -x` | No -- Wave 0 |
| MCP-05e | Context7 graceful fallback on timeout | unit | `pytest tests/test_context7.py::test_query_docs_timeout -x` | No -- Wave 0 |
| MCP-05f | Knowledge base remains primary, Context7 supplements | integration | `pytest tests/test_context7.py::test_kb_primary_context7_supplementary -x` | No -- Wave 0 |
| OBS-01a | ArtifactState transitions (pending->generated->validated->approved) | unit | `pytest tests/test_artifact_state.py::test_state_transitions -x` | No -- Wave 0 |
| OBS-01b | ModuleState save/load roundtrip | unit | `pytest tests/test_artifact_state.py::test_save_load_roundtrip -x` | No -- Wave 0 |
| OBS-01c | State tracking failure does not block generation | unit | `pytest tests/test_artifact_state.py::test_failure_does_not_block -x` | No -- Wave 0 |
| OBS-01d | CLI show-state command displays artifact states | unit | `pytest tests/test_artifact_state.py::test_cli_show_state -x` | No -- Wave 0 |
| OBS-01e | State file handles corruption gracefully | unit | `pytest tests/test_artifact_state.py::test_corrupted_state_file -x` | No -- Wave 0 |
| OBS-01f | State integrated into render_module pipeline | integration | `pytest tests/test_artifact_state.py::test_render_module_emits_state -x` | No -- Wave 0 |

### Sampling Rate

- **Per task commit:** `cd python && .venv/bin/python -m pytest tests/test_context7.py tests/test_artifact_state.py -x`
- **Per wave merge:** `cd python && .venv/bin/python -m pytest -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_context7.py` -- covers MCP-05 (a-f)
- [ ] `tests/test_artifact_state.py` -- covers OBS-01 (a-f)
- [ ] No framework install needed -- pytest already configured

## Sources

### Primary (HIGH confidence)

- Context7 REST API documentation: https://context7.com/docs/api-guide -- verified API endpoints, parameters, authentication
- Context7 GitHub repository: https://github.com/upstash/context7 -- tool definitions, configuration
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk -- client patterns (decided NOT to use for Context7)
- Existing project codebase (verifier.py, auto_fix.py, cli.py, mcp/server.py) -- established patterns for graceful fallback, dataclasses, CLI

### Secondary (MEDIUM confidence)

- Context7 Odoo page: https://context7.com/odoo -- confirms Odoo docs exist in Context7, exact library IDs unverified
- Blog post on Context7 + Odoo: https://jortdevreeze.com/blog/odoo-2/improving-your-odoo-development-workflow-with-context7-s-mcp-integration-31 -- confirms Odoo 17 docs available
- Real Python MCP client guide: https://realpython.com/python-mcp-client/ -- client patterns (reference only, not used)

### Tertiary (LOW confidence)

- Exact Context7 library ID for Odoo: Needs runtime verification via resolve-library-id API call
- Context7 rate limits: Documentation says "higher limits with API key" but specific numbers not published

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib-only approach is low-risk, all libraries already in project
- Architecture: HIGH - both features follow established project patterns (EnvironmentVerifier for fallback, dataclasses for state)
- Context7 API: MEDIUM - REST API endpoints verified via official docs, but Odoo-specific library IDs need runtime validation
- Pitfalls: MEDIUM-HIGH - based on general REST API and JSON file I/O experience, Context7-specific rate limits unverified

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable -- stdlib approach, unlikely to change)
