# Phase 22: Validation & Search Fixes - Research

**Researched:** 2026-03-05
**Domain:** Docker validation, GitHub API rate limiting, Python AST analysis
**Confidence:** HIGH

## Summary

Phase 22 addresses three independent bugs: (1) `docker_install_module` uses `exec` which creates a second Odoo process in a running container, causing PostgreSQL serialization failures -- the fix is to switch to `docker compose run --rm` like `docker_run_tests` already does; (2) `build_oca_index` makes GitHub API calls without rate limit awareness, which causes 403/429 failures on large crawls of 200+ OCA repos -- needs header checking and exponential backoff; (3) `_extract_models_from_file` in the AST analyzer only captures models with `_name` assignments, silently ignoring `_inherit`-only model extensions -- needs a new field on `ModuleAnalysis`.

All three fixes are localized, well-understood, and have existing test infrastructure. The `docker_run_tests` function already demonstrates the correct `run --rm` pattern. PyGithub provides `get_rate_limit()` returning a `Rate` object with `remaining`, `limit`, and `reset` attributes, plus `RateLimitExceededException` for catching 403 rate limit responses.

**Primary recommendation:** Three independent changes to three files, each with clear before/after patterns. Split into a single plan with three task groups.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VALD-01 | docker_install_module uses `docker compose run --rm` instead of `docker compose exec` | docker_runner.py already has the correct pattern in `docker_run_tests` (line 230-251). Copy the `run --rm` approach and remove the `up -d --wait` step for the odoo service. |
| SRCH-01 | GitHub API calls check X-RateLimit-Remaining header, sleep until reset when low, retry with exponential backoff on 403/429 | PyGithub provides `Github.get_rate_limit().rate.remaining/reset` and `RateLimitExceededException`. Build a wrapper that checks before each repo iteration and catches exceptions with backoff. |
| SRCH-02 | AST analyzer detects _inherit-only model extensions and records them in ModuleAnalysis.inherited_models | `_extract_models_from_file` already walks AST for `_name`. Add parallel detection of `_inherit` assignments where `_name` is absent. Add `inherited_models` field to frozen `ModuleAnalysis`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyGithub | >=2.8 | GitHub API access with rate limit support | Already in project deps; provides `get_rate_limit()`, `RateLimitExceededException` |
| ast (stdlib) | Python 3.12 | AST parsing for _inherit detection | Already used in analyzer.py for _name extraction |
| subprocess (stdlib) | Python 3.12 | Docker compose command execution | Already used in docker_runner.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| time (stdlib) | Python 3.12 | `time.sleep()` for rate limit wait | When GitHub rate limit is exhausted |
| logging (stdlib) | Python 3.12 | Log rate limit waits and retries | Already configured in both modules |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual rate limit checking | `GithubRetry(secondary_rate_wait=...)` constructor param | GithubRetry handles secondary rate limits automatically but does NOT handle primary rate limits (X-RateLimit-Remaining). Manual checking gives full control and visibility via logging. Use both: GithubRetry for secondary + manual for primary. |

## Architecture Patterns

### Pattern 1: docker compose run --rm (VALD-01)
**What:** Replace `exec` with `run --rm` for module installation, matching existing `docker_run_tests` pattern.
**When to use:** Any time Odoo needs to be invoked for a one-off task (install, test, upgrade).
**Current bug:** `docker_install_module` calls `up -d --wait` (starts Odoo entrypoint server) then `exec` (runs second Odoo process). Both write to same PostgreSQL database, causing `psycopg2.errors.SerializationFailure`.
**Fix pattern:**
```python
# BEFORE (buggy): Two Odoo processes on same DB
_run_compose(compose_file, ["up", "-d", "--wait"], env)  # starts odoo + db
_run_compose(compose_file, ["exec", "-T", "odoo", "odoo", "-i", ...], env)  # second process!

# AFTER (correct): Only db service up, fresh odoo container via run
_run_compose(compose_file, ["up", "-d", "--wait", "db"], env)  # db only
_run_compose(compose_file, ["run", "--rm", "-T", "odoo", "odoo", "-i", ...], env)  # fresh container
```
**Reference:** `docker_run_tests` at line 226-251 of docker_runner.py already uses this exact pattern correctly.

### Pattern 2: Rate Limit Wrapper (SRCH-01)
**What:** Check `remaining` before API-intensive loops, sleep until `reset` when exhausted, catch `RateLimitExceededException` with exponential backoff.
**When to use:** Any bulk GitHub API operation (OCA crawl iterates 200+ repos, each with 3-5 API calls).
**Example:**
```python
import time
from datetime import datetime, timezone
from github import RateLimitExceededException

def _check_rate_limit(gh: Github, min_remaining: int = 10) -> None:
    """Sleep until rate limit resets if remaining calls are low."""
    rate = gh.get_rate_limit().rate
    if rate.remaining < min_remaining:
        reset_time = rate.reset.timestamp()
        now = datetime.now(timezone.utc).timestamp()
        sleep_seconds = max(reset_time - now + 1, 0)
        logger.info(
            "Rate limit low (%d/%d remaining), sleeping %.0fs until reset",
            rate.remaining, rate.limit, sleep_seconds,
        )
        time.sleep(sleep_seconds)

def _retry_on_rate_limit(func, *args, max_retries: int = 3, **kwargs):
    """Retry with exponential backoff on 403/429 rate limit responses."""
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except RateLimitExceededException:
            if attempt == max_retries:
                raise
            wait = 2 ** attempt  # 1s, 2s, 4s
            logger.warning("Rate limited (attempt %d/%d), retrying in %ds",
                          attempt + 1, max_retries, wait)
            time.sleep(wait)
```

### Pattern 3: _inherit Detection in AST (SRCH-02)
**What:** Extend `_extract_models_from_file` to also detect `_inherit = 'model.name'` assignments where no `_name` is present.
**When to use:** Analyzing Odoo modules where classes extend existing models without creating new ones.
**Odoo semantics:**
- `_name = 'x'` + `_inherit = 'x'` = new model inheriting from x (already captured as model with _name)
- `_inherit = 'x'` without `_name` = in-place extension of model x (CURRENTLY MISSED)
- `_inherit = ['x', 'y']` without `_name` = multiple inheritance extension (also missed, but rare)

**Example:**
```python
# _inherit can be a string or list
_inherit_value = None
for item in node.body:
    if (isinstance(item, ast.Assign)
        and len(item.targets) == 1
        and isinstance(item.targets[0], ast.Name)
        and item.targets[0].id == "_inherit"):
        if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
            _inherit_value = item.value.value
        elif isinstance(item.value, ast.List):
            # _inherit = ['model.a', 'model.b']
            _inherit_value = [
                elt.value for elt in item.value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]

# If _inherit present but no _name, it's an in-place extension
if _inherit_value is not None and model_name is None:
    inherited_models.append(_inherit_value)
```

### Anti-Patterns to Avoid
- **exec into running Odoo container:** Two Odoo processes on the same PostgreSQL DB cause serialization failures. Always use `run --rm` for one-off commands.
- **Ignoring rate limit headers:** GitHub returns 403 with no warning. Always check remaining before intensive loops.
- **Polling rate limit on every API call:** `get_rate_limit()` itself costs one API call. Check periodically (e.g., every N repos), not per-call.
- **Assuming _inherit is always a string:** Odoo allows `_inherit = ['model.a', 'model.b']` for multi-parent extensions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GitHub rate limit detection | Custom HTTP header parsing | `Github.get_rate_limit().rate.remaining` | PyGithub already parses X-RateLimit headers into a typed Rate object |
| Rate limit exception catching | Custom 403 status code checking | `RateLimitExceededException` | PyGithub raises this automatically on 403 rate limit responses |
| Secondary rate limit handling | Custom retry logic for abuse detection | `GithubRetry(secondary_rate_wait=60)` in Github constructor | Handles GitHub's "secondary rate limit" (abuse detection) automatically |

## Common Pitfalls

### Pitfall 1: get_rate_limit() Costs an API Call
**What goes wrong:** Calling `gh.get_rate_limit()` on every iteration of a 200-repo loop wastes 200 API calls just checking the limit.
**Why it happens:** Developers assume the rate limit check is free.
**How to avoid:** Check rate limit once per N repos (e.g., every 10), or only after catching `RateLimitExceededException`.
**Warning signs:** Hitting rate limit faster than expected despite checking.

### Pitfall 2: Docker run --rm Still Needs db Service Running
**What goes wrong:** `docker compose run --rm odoo` fails because PostgreSQL is not running.
**Why it happens:** `run` creates a fresh container but `depends_on` health checks are NOT enforced for `run` in all Docker Compose versions.
**How to avoid:** Explicitly start db first: `_run_compose(compose_file, ["up", "-d", "--wait", "db"], env)` before `run`.
**Warning signs:** "Connection refused" errors from Odoo trying to connect to PostgreSQL.

### Pitfall 3: _inherit Can Be a List
**What goes wrong:** Code assumes `_inherit = 'res.partner'` but Odoo also allows `_inherit = ['mail.thread', 'mail.activity.mixin']`.
**Why it happens:** Single-parent inheritance is most common, so developers only handle strings.
**How to avoid:** Check for both `ast.Constant` (string) and `ast.List` (list of strings) in the AST value.
**Warning signs:** Missing inherited models in analysis output for multi-inherit classes.

### Pitfall 4: ModuleAnalysis is Frozen
**What goes wrong:** Adding `inherited_models` field to `ModuleAnalysis` breaks existing tests that construct it without the new field.
**Why it happens:** `@dataclass(frozen=True)` with positional args means all existing callers must be updated.
**How to avoid:** Add `inherited_models` with a default value (`inherited_models: tuple[str, ...] = ()`) so existing callers are unaffected.
**Warning signs:** TypeError in tests: "missing required argument 'inherited_models'".

### Pitfall 5: RateLimitExceededException vs GithubException(403)
**What goes wrong:** Some GitHub 403 responses (e.g., repo access denied) are NOT rate limit issues but get caught by broad exception handling.
**Why it happens:** Both rate limit and permission errors return HTTP 403.
**How to avoid:** Catch `RateLimitExceededException` specifically (it's a subclass of `GithubException`), not generic `GithubException` with status=403.
**Warning signs:** Sleeping on rate limit when the real issue is a private repo or permission problem.

## Code Examples

### docker_install_module Fix (VALD-01)
```python
# Source: Existing docker_run_tests pattern in docker_runner.py lines 226-251
def docker_install_module(
    module_path: Path,
    compose_file: Path | None = None,
    timeout: int = 300,
) -> InstallResult:
    # ... (unchanged preamble) ...
    try:
        # Start ONLY the database service
        _run_compose(compose_file, ["up", "-d", "--wait", "db"], env, timeout=120)

        # Install in a fresh container (no entrypoint server conflict)
        result = _run_compose(
            compose_file,
            [
                "run",
                "--rm",
                "-T",
                "odoo",
                "odoo",
                "-i",
                module_name,
                "-d",
                "test_db",
                "--stop-after-init",
                "--no-http",
                "--log-level=info",
            ],
            env,
            timeout=timeout,
        )
        # ... (unchanged log parsing) ...
```

### Rate Limit Wrapper (SRCH-01)
```python
# Source: PyGithub API - gh.get_rate_limit().rate
import time
from datetime import datetime, timezone
from github import RateLimitExceededException

def _check_rate_limit(gh: Github, min_remaining: int = 10) -> None:
    rate = gh.get_rate_limit().rate
    if rate.remaining < min_remaining:
        reset_ts = rate.reset.timestamp()
        now_ts = datetime.now(timezone.utc).timestamp()
        sleep_secs = max(reset_ts - now_ts + 1, 0)
        logger.info("Rate limit: %d/%d remaining, sleeping %.0fs",
                    rate.remaining, rate.limit, sleep_secs)
        time.sleep(sleep_secs)
```

### Inherited Model Detection (SRCH-02)
```python
# Source: Odoo _inherit semantics + existing _extract_models_from_file pattern
def _extract_inherit_value(node_value: ast.expr) -> str | list[str] | None:
    """Extract _inherit value from AST node (string or list of strings)."""
    if isinstance(node_value, ast.Constant) and isinstance(node_value.value, str):
        return node_value.value
    if isinstance(node_value, ast.List):
        return [
            elt.value for elt in node_value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        ]
    return None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `docker compose exec` for install | `docker compose run --rm` | Known since v1.1 (Mistake #4 in CLAUDE.md) | Eliminates serialization race condition |
| No rate limiting on GitHub API | Check `X-RateLimit-Remaining` + exponential backoff | Standard practice | Enables full OCA crawl (200+ repos) without 403 failures |
| Only detect `_name` models | Also detect `_inherit`-only extensions | Phase 22 | Captures model extensions that add fields/methods to existing models |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | `python/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd python && uv run pytest tests/test_docker_runner.py tests/test_search_index.py tests/test_search_fork.py -x -q` |
| Full suite command | `cd python && uv run pytest tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VALD-01 | docker_install_module uses `run --rm` instead of `exec` | unit (mocked) | `cd python && uv run pytest tests/test_docker_runner.py -x -q` | Exists but needs update |
| SRCH-01 | GitHub API rate limit checking and retry | unit (mocked) | `cd python && uv run pytest tests/test_search_index.py -x -q` | Exists but needs new tests |
| SRCH-02 | AST detects _inherit-only models | unit | `cd python && uv run pytest tests/test_search_fork.py -x -q` | Exists but needs new tests |

### Sampling Rate
- **Per task commit:** `cd python && uv run pytest tests/test_docker_runner.py tests/test_search_index.py tests/test_search_fork.py -x -q`
- **Per wave merge:** `cd python && uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_docker_runner.py` -- update `TestDockerInstallModuleSuccess` to verify `run --rm` args instead of `exec` args
- [ ] `tests/test_search_index.py` -- add tests for rate limit checking (mock `get_rate_limit()` and `RateLimitExceededException`)
- [ ] `tests/test_search_fork.py` -- add tests for `_inherit`-only model detection in `TestAnalyzeModule`

## Open Questions

1. **Rate limit check frequency**
   - What we know: `get_rate_limit()` costs 1 API call. OCA has 200+ repos, each needing 3-5 calls.
   - What's unclear: Optimal check frequency (every repo? every 10 repos?)
   - Recommendation: Check every 10 repos, plus always after catching `RateLimitExceededException`. This balances safety with API budget.

2. **_inherit list normalization**
   - What we know: `_inherit` can be string or list. ModuleAnalysis needs to store both forms.
   - What's unclear: Whether to normalize all to lists or keep the original form.
   - Recommendation: Store as `tuple[str, ...]` in `inherited_models` field. When `_inherit` is a string, wrap in a 1-element tuple. This keeps the dataclass simple and consistent.

## Sources

### Primary (HIGH confidence)
- PyGithub installed version (2.8+) - verified `get_rate_limit().rate.remaining/limit/reset` attributes via live interpreter
- PyGithub `RateLimitExceededException` - verified importable from `github.GithubException`
- PyGithub `GithubRetry` - verified constructor accepts `secondary_rate_wait` parameter
- Existing codebase: `docker_runner.py`, `analyzer.py`, `index.py`, `types.py` - read in full

### Secondary (MEDIUM confidence)
- [PyGithub RateLimit docs](https://pygithub.readthedocs.io/en/latest/github_objects/RateLimit.html) - Rate object structure
- [PyGithub Utilities docs](https://pygithub.readthedocs.io/en/latest/utilities.html) - RateLimitExceededException
- [PyGithub Issue #1319](https://github.com/PyGithub/PyGithub/issues/1319) - community rate limit handling patterns

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project, verified via interpreter
- Architecture: HIGH - `docker_run_tests` already demonstrates the correct Docker pattern; PyGithub rate limit API verified live
- Pitfalls: HIGH - race condition documented in project's own Mistakes Log (#4); _inherit semantics are well-established Odoo convention

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain, no fast-moving dependencies)
