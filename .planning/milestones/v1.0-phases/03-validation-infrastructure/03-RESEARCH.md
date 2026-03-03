# Phase 3: Validation Infrastructure - Research

**Researched:** 2026-03-02
**Domain:** Static analysis (pylint-odoo), Docker-based Odoo 17.0 validation, error diagnosis
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Docker Environment Setup**: Ephemeral docker-compose with official `odoo:17.0` + `postgres:16` images. Spin up per validation run, tear down after. Clean state prevents false positives.
- **Graceful degradation**: If Docker not available, skip Docker validation, only run pylint-odoo. Warn user but don't block.
- **docker-compose.yml** shipped with the extension at `~/.claude/odoo-gen/docker/`. Module directory is bind-mounted as addon path.
- **Structured 3-section report**: (1) pylint-odoo violations table, (2) Docker install result pass/fail + parsed error, (3) Test results per test case pass/fail. Summary header with pass/fail counts.
- **Agent-readable format** so auto-fix loops (Phase 7) can parse and act on results.
- **Full OCA ruleset** by default (~80+ rules) -- that's the quality bar.
- **Installed in extension's Python venv** (not Docker) -- faster, no container needed for static analysis.
- **`.pylintrc-odoo` support**: Users can place config in module directory to override/disable specific rules.
- **Pattern-based diagnosis**: Library of ~20-30 common Odoo error patterns mapped to human-readable explanations and suggested fixes.
- **Unrecognized errors**: Show raw traceback with relevant file highlighted.

### Claude's Discretion
- Exact docker-compose.yml configuration and volume mounts
- Error pattern library content (which 20-30 patterns to include)
- pylint-odoo output parsing implementation
- Report formatting details (markdown tables, JSON, or custom format)
- Python CLI subcommands for validation (`odoo-gen-utils validate`, `odoo-gen-utils docker-test`)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUAL-01 | System runs pylint-odoo on all generated Python and XML files | pylint-odoo 10.0.1 with `--load-plugins=pylint_odoo` runs on module directory, supports JSON2 output |
| QUAL-02 | System reports pylint-odoo violations with file, line number, and fix suggestions | JSON2 output format provides `path`, `line`, `column`, `symbol`, `message`, `messageId`, `type` per violation |
| QUAL-03 | System spins up Docker-based Odoo 17.0 + PostgreSQL environment | docker-compose with `odoo:17` + `postgres:16` images, bind-mount module to `/mnt/extra-addons` |
| QUAL-04 | System installs generated module on Docker Odoo and reports install success/failure | `odoo -i module_name -d test_db --stop-after-init` with exit code + log parsing |
| QUAL-05 | System runs generated tests on Docker Odoo and reports pass/fail | `odoo -i module_name -d test_db --test-enable --stop-after-init` with log-level parsing |
| QUAL-07 | System parses Odoo error logs on failure and provides actionable diagnosis | Pattern library maps regex patterns to explanations + fix suggestions |
| QUAL-08 | All validation checks enforce Odoo 17.0 API exclusively | pylint-odoo rules (W8105 attribute-deprecated, W8160 deprecated-odoo-model-method) + custom pattern checks |
</phase_requirements>

## Summary

Phase 3 builds the validation pipeline that verifies any Odoo module against OCA quality standards and real Odoo 17.0 runtime. The pipeline has three stages: (1) static analysis via pylint-odoo running in the extension's Python venv, (2) Docker-based module installation using official `odoo:17` + `postgres:16` images, and (3) test execution on the Docker instance.

**pylint-odoo 10.0.1** (verified installed and tested) is a pylint plugin providing 50+ Odoo-specific rules. It runs via `pylint --load-plugins=pylint_odoo -f json2 module_path` and produces structured JSON output with file paths, line numbers, rule codes, severity levels, and messages. The `--disable=all --enable=odoolint` flag combination isolates Odoo-specific rules from general Python lint. The E0401 `import-error` for `odoo` must be suppressed since we run outside an Odoo environment.

**Docker validation** uses the `odoo:17` image (already present on this system) which exposes `/mnt/extra-addons` as the addon mount point. Module installation is `odoo -i module_name -d test_db --stop-after-init` (exits after init). Tests run with `--test-enable`. Odoo logs test results as INFO/ERROR lines parseable by regex. The entrypoint script handles Postgres connection via environment variables (`HOST`, `PORT`, `USER`, `PASSWORD`).

**Primary recommendation:** Build a `validate` CLI subcommand and a `docker-test` CLI subcommand on the existing `odoo-gen-utils` Click CLI. Validation results are a JSON data structure that can be rendered as markdown for human reading or parsed by Phase 7's auto-fix agent.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pylint-odoo | 10.0.1 | Odoo-specific static analysis | Official OCA tool, 50+ rules, JSON output |
| pylint | 4.0.5 | Underlying lint framework | Required by pylint-odoo |
| docker compose | 2.37.1 | Container orchestration | Official Docker tool, declarative YAML |
| odoo:17 (Docker image) | 17.0 | Runtime validation environment | Official Odoo image, matches target version |
| postgres:16 (Docker image) | 16 | Database for Odoo validation | Matches production Odoo 17 recommendation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| click | >=8.0 | CLI framework (already in project) | Extend existing CLI with validate/docker-test commands |
| subprocess | stdlib | Run pylint, docker compose | All external process invocation |
| json | stdlib | Parse pylint JSON2 output | Result parsing and report generation |
| re | stdlib | Parse Odoo error logs | Pattern matching for error diagnosis |
| shutil | stdlib | Check Docker availability | `shutil.which("docker")` for graceful degradation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pylint JSON2 output | pylint text/parseable output | JSON2 is machine-readable, text requires regex parsing |
| docker compose | docker run with --link | compose is declarative, reproducible, handles networking |
| Pattern library as JSON | Pattern library as Python dict | JSON is editable without code changes, extensible by users |

**Installation:**
```bash
# In extension venv (handled by install.sh update)
uv pip install pylint-odoo
# Docker images (already present, optional pre-pull)
docker pull odoo:17
docker pull postgres:16
```

## Architecture Patterns

### Recommended Project Structure
```
python/src/odoo_gen_utils/
  cli.py                    # Existing -- add validate, docker-test subcommands
  renderer.py               # Existing -- unchanged
  validation/
    __init__.py              # Package init
    pylint_runner.py         # pylint-odoo invocation + JSON2 parsing
    docker_runner.py         # docker compose lifecycle (up, exec, down)
    log_parser.py            # Odoo log parsing (install result, test results)
    error_patterns.py        # Load and match error pattern library
    report.py                # Structured report generation (JSON + markdown)
    types.py                 # Dataclasses for ValidationReport, Violation, TestResult, etc.
  validation/data/
    error_patterns.json      # Error pattern library (20-30 patterns)

docker/
  docker-compose.yml         # Shipped with extension
  odoo.conf                  # Custom Odoo config for validation
```

### Pattern 1: Subprocess-based Tool Invocation
**What:** Run pylint and docker compose as subprocesses, capture output, parse structured results.
**When to use:** Whenever invoking external CLI tools.
**Example:**
```python
import json
import subprocess
from pathlib import Path

def run_pylint_odoo(module_path: Path, pylintrc: Path | None = None) -> dict:
    """Run pylint-odoo on module and return parsed JSON2 results."""
    cmd = [
        "pylint",
        "--load-plugins=pylint_odoo",
        "--output-format=json2",
        "--disable=import-error",  # odoo not importable outside Odoo
        str(module_path),
    ]
    if pylintrc and pylintrc.exists():
        cmd.insert(1, f"--rcfile={pylintrc}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    # pylint returns non-zero on lint findings -- that's expected
    return json.loads(result.stdout) if result.stdout else {"messages": [], "statistics": {}}
```

### Pattern 2: Ephemeral Docker Compose Lifecycle
**What:** Start containers, run validation, tear down. Always clean state.
**When to use:** Docker-based install and test execution.
**Example:**
```python
import subprocess
from pathlib import Path

def docker_validate(module_path: Path, compose_file: Path) -> tuple[int, str]:
    """Run module install in ephemeral Docker environment."""
    module_name = module_path.name
    env = {
        "MODULE_PATH": str(module_path.resolve()),
        "MODULE_NAME": module_name,
    }
    try:
        # Start services
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d", "--wait"],
            env={**os.environ, **env}, check=True, capture_output=True, text=True, timeout=120,
        )
        # Install module
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "exec", "-T", "odoo",
             "odoo", "-i", module_name, "-d", "test_db", "--stop-after-init",
             "--no-http"],
            env={**os.environ, **env}, capture_output=True, text=True, timeout=300,
        )
        return result.returncode, result.stdout + result.stderr
    finally:
        # Always tear down
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down", "-v"],
            env={**os.environ, **env}, capture_output=True, timeout=60,
        )
```

### Pattern 3: Structured Validation Report
**What:** Immutable dataclass-based report with sections for each validation stage.
**When to use:** All validation results.
**Example:**
```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Violation:
    file: str
    line: int
    column: int
    rule_code: str
    symbol: str
    severity: str  # error, warning, convention, refactor
    message: str
    suggestion: str = ""

@dataclass(frozen=True)
class TestResult:
    test_name: str
    passed: bool
    error_message: str = ""
    duration_seconds: float = 0.0

@dataclass(frozen=True)
class ValidationReport:
    module_name: str
    pylint_violations: list[Violation] = field(default_factory=list)
    install_success: bool | None = None  # None = not run (Docker unavailable)
    install_error: str = ""
    test_results: list[TestResult] = field(default_factory=list)
    diagnosis: list[str] = field(default_factory=list)
    docker_available: bool = True
```

### Anti-Patterns to Avoid
- **Running pylint inside Docker:** Unnecessary overhead; pylint-odoo runs fine outside Odoo for static analysis. Only import-dependent checks need Docker.
- **Keeping Docker containers running between validations:** Stale state causes false positives. Always ephemeral.
- **Parsing pylint text output with regex:** Use JSON2 format -- it's structured, reliable, version-stable.
- **Hardcoding error patterns in Python code:** Put them in a JSON data file so users can extend without code changes.
- **Swallowing subprocess errors:** Always capture returncode, stdout, and stderr. Subprocess failures are diagnostic information.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Odoo static analysis | Custom AST-based linter | pylint-odoo 10.0.1 | 50+ maintained rules, OCA-standard, handles Odoo decorators |
| Docker orchestration | Manual docker run/link | docker compose | Networking, volumes, env, lifecycle handled declaratively |
| JSON output parsing | Custom pylint output parser | pylint `json2` format | Official, structured, version-stable output |
| Python subprocess management | Custom process management | subprocess.run() | stdlib, timeout support, capture output |
| Odoo module structure detection | Custom manifest parser | ast.literal_eval on __manifest__.py | Safe eval, handles dict format reliably |

**Key insight:** The entire static analysis pipeline is "configure pylint-odoo + parse its output." The Docker pipeline is "configure docker-compose + parse Odoo logs." We build the orchestration and reporting, not the analysis or runtime.

## Common Pitfalls

### Pitfall 1: pylint import-error for odoo module
**What goes wrong:** pylint reports E0401 `Unable to import 'odoo'` for every Python file because odoo is not installed in the extension venv.
**Why it happens:** pylint tries to resolve imports; odoo package only exists inside Odoo installation.
**How to avoid:** Add `--disable=import-error` to pylint invocation. This suppresses E0401 but keeps all Odoo-specific checks.
**Warning signs:** Every file shows E0401 errors in results.

### Pitfall 2: Docker compose environment variable passing
**What goes wrong:** Module path not correctly mounted because docker-compose.yml uses hardcoded paths.
**Why it happens:** docker-compose.yml is static; module paths vary per invocation.
**How to avoid:** Use environment variable substitution in docker-compose.yml: `${MODULE_PATH}:/mnt/extra-addons/${MODULE_NAME}`. Pass via subprocess env dict.
**Warning signs:** Odoo reports "module not found" during install.

### Pitfall 3: Odoo test result parsing
**What goes wrong:** Tests appear to pass when they actually failed, or vice versa.
**Why it happens:** Odoo logs test results as INFO/ERROR lines mixed with other output. The pattern `odoo.modules.loading: X modules loaded, Y modules updated, Z tests` appears at different points.
**How to avoid:** Parse specific log patterns: `FAIL: test_name` (test failure), `ERROR: test_name` (test error), `odoo.modules.loading: ... tests` (summary). Use `--log-level=test` for focused output.
**Warning signs:** Test count doesn't match expected.

### Pitfall 4: Docker container startup race condition
**What goes wrong:** Odoo tries to connect to PostgreSQL before it's ready.
**Why it happens:** Odoo container starts before Postgres accepts connections.
**How to avoid:** The official Odoo image includes `wait-for-psql.py` in its entrypoint with a 30-second timeout. Use `docker compose up -d --wait` to wait for health checks. Add health check to postgres service in docker-compose.yml.
**Warning signs:** "Connection refused" or "could not connect to server" in logs.

### Pitfall 5: Module name vs directory name mismatch
**What goes wrong:** Odoo can't find the module even though it's mounted.
**Why it happens:** Odoo looks for modules by `__manifest__.py` location. The directory name must match the technical module name.
**How to avoid:** Mount the module's parent directory as the addons path, not the module directory itself. Or mount specifically as `/mnt/extra-addons/{module_name}`.
**Warning signs:** "Module xxx not found" even though files are visible in container.

### Pitfall 6: pylint-odoo needs git repository context
**What goes wrong:** pylint-odoo outputs `fatal: not a git repository` warnings.
**Why it happens:** Some pylint-odoo checks (like E8102 invalid-commit) look for git history.
**How to avoid:** Suppress stderr git warnings. These are non-fatal -- pylint-odoo still runs all other checks. The warnings don't affect results.
**Warning signs:** stderr contains git-related messages.

### Pitfall 7: Docker timeout on first run
**What goes wrong:** First Docker validation takes 60+ seconds because Odoo initializes the database.
**Why it happens:** Fresh database requires Odoo base module installation before custom module install.
**How to avoid:** Set generous timeouts (300s for install, 600s for tests). Document expected first-run time. Consider pre-initializing a base database template.
**Warning signs:** Subprocess timeout errors on first run.

## Code Examples

### Running pylint-odoo with JSON2 output
```python
# Source: Verified locally on this system with pylint-odoo 10.0.1
import json
import subprocess

result = subprocess.run(
    [
        "python", "-m", "pylint",
        "--load-plugins=pylint_odoo",
        "--output-format=json2",
        "--disable=import-error,missing-module-docstring,missing-class-docstring",
        "module_path",
    ],
    capture_output=True, text=True, timeout=120,
)
# Exit code is a bitmask: 1=fatal, 2=error, 4=warning, 8=refactor, 16=convention, 32=usage
data = json.loads(result.stdout) if result.stdout else {"messages": []}
for msg in data["messages"]:
    print(f"{msg['path']}:{msg['line']} [{msg['symbol']}] {msg['message']}")
```

### docker-compose.yml for Odoo validation
```yaml
# Source: Official Odoo Docker documentation + verified odoo:17 image inspection
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
      POSTGRES_DB: postgres
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo"]
      interval: 5s
      timeout: 5s
      retries: 5
    tmpfs:
      - /var/lib/postgresql/data  # RAM-backed for speed

  odoo:
    image: odoo:17
    depends_on:
      db:
        condition: service_healthy
    environment:
      HOST: db
      USER: odoo
      PASSWORD: odoo
    volumes:
      - ${MODULE_PATH}:/mnt/extra-addons/${MODULE_NAME}:ro
```

### Parsing Odoo test results from logs
```python
# Source: Odoo 17 log output format (verified patterns)
import re

TEST_PASS = re.compile(r"^(\d{4}-\d{2}-\d{2} [\d:,]+) \d+ INFO .+ odoo\.addons\.(\S+)\.tests\.(\S+): .*(ok|OK)$")
TEST_FAIL = re.compile(r"^(\d{4}-\d{2}-\d{2} [\d:,]+) \d+ (ERROR|FAIL) .+ odoo\.addons\.(\S+)\.tests\.(\S+)")
TEST_SUMMARY = re.compile(r"Ran (\d+) tests? in ([\d.]+)s")
MODULE_LOADED = re.compile(r"(\d+) modules loaded.*?(\d+) tests")
TRACEBACK_START = re.compile(r"^Traceback \(most recent call last\):")
```

### Error pattern matching
```python
# Pattern library entry example (from error_patterns.json)
{
    "patterns": [
        {
            "id": "field-not-found",
            "regex": "KeyError: '(\\w+)'",
            "context_regex": "odoo\\.models|fields\\..*Field",
            "explanation": "Field '{match_group_1}' is referenced but not defined in the model",
            "suggestion": "Check that field '{match_group_1}' exists in the model definition. Common causes: typo in field name, missing field import, or referencing a field from an inherited model without declaring _inherit.",
            "severity": "error"
        },
        {
            "id": "xml-parse-error",
            "regex": "ParseError|XMLSyntaxError|lxml\\.etree",
            "explanation": "XML syntax error in a view or data file",
            "suggestion": "Check for unclosed tags, mismatched quotes, or invalid XML characters. Use an XML validator on the reported file.",
            "severity": "error"
        }
    ]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pylint-odoo text output | pylint json2 format | pylint 3.0+ | Machine-readable, no regex parsing needed |
| `docker-compose` (v1, Python) | `docker compose` (v2, Go) | 2023 | Built into Docker CLI, faster, compose spec v3+ |
| Odoo `attrs` for conditional visibility | Inline `invisible`/`readonly` expressions | Odoo 17.0 | `attrs` deprecated, pylint-odoo W8105 catches this |
| `<tree>` view element | `<list>` view element | Odoo 17.0 | Syntax change, pylint-odoo doesn't catch this yet |
| `api.one`/`api.multi` decorators | Removed (always multi) | Odoo 13.0+ | Long deprecated, pylint-odoo W8160 catches usage |

**Deprecated/outdated:**
- `docker-compose` (v1 Python tool): Replaced by `docker compose` (v2 Go plugin). Both work but v2 is standard.
- pylint `json` format: Superseded by `json2` which is more structured.

## Open Questions

1. **Pre-initialized database template for faster Docker validation**
   - What we know: First-run Odoo init takes 30-60 seconds to install base module
   - What's unclear: Whether a Docker volume with pre-initialized base DB would be reliable across module validations
   - Recommendation: Start simple (fresh DB each time). Optimize later if validation speed becomes a bottleneck. Phase 3 scope is correctness, not speed.

2. **pylint-odoo custom rule configuration scope**
   - What we know: Users can place `.pylintrc-odoo` in module directory. pylint supports `--rcfile` and also looks for setup.cfg, pyproject.toml.
   - What's unclear: Whether pylint-odoo respects all configuration sources or only `--rcfile`
   - Recommendation: Support `--rcfile` explicitly with a `.pylintrc-odoo` convention. Document that pyproject.toml `[tool.pylint]` also works.

3. **Odoo test log format stability**
   - What we know: Odoo 17 outputs test results as log lines with specific patterns
   - What's unclear: Whether log format changes between minor versions (17.0.x)
   - Recommendation: Use flexible regex patterns, focus on well-known markers (FAIL, ERROR, Ran N tests), gracefully handle unparseable output.

## Sources

### Primary (HIGH confidence)
- **pylint-odoo 10.0.1** - Installed and tested locally. Confirmed rules, JSON2 output format, CLI invocation patterns.
- **odoo:17 Docker image** - Inspected locally. Confirmed entrypoint, odoo.conf, /mnt/extra-addons mount, CLI flags.
- **postgres:16 Docker image** - Present locally, confirmed compatible with odoo:17.
- **Odoo CLI help** - `odoo --help` output from Docker image, confirmed `--init`, `--test-enable`, `--stop-after-init`, `--log-level`, `--no-http`.

### Secondary (MEDIUM confidence)
- **Docker Compose specification** - Environment variable substitution, health checks, tmpfs mounts well-documented in Docker docs.
- **Odoo log format patterns** - Based on standard Odoo 17 logging output patterns, commonly documented in OCA tooling.

### Tertiary (LOW confidence)
- **Pre-initialized DB template approach** - Theoretical optimization, not verified. Flagged as open question.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools installed and tested locally
- Architecture: HIGH - Patterns follow established subprocess + structured output approach
- Pitfalls: HIGH - Several verified empirically during research (import-error, git warnings, JSON2 parsing)

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (30 days - stable tools, unlikely to change)
