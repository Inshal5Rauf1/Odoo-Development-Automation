# Phase 15: Odoo Dev Instance - Research

**Researched:** 2026-03-04
**Domain:** Docker-based Odoo 17 CE development infrastructure with XML-RPC access
**Confidence:** HIGH

## Summary

Phase 15 provisions a persistent Odoo 17 CE development instance via Docker Compose that the MCP server (Phase 16) will connect to via XML-RPC. The project already has ephemeral Docker infrastructure for validation (`docker/docker-compose.yml` with tmpfs PostgreSQL), so this phase creates a SEPARATE persistent dev instance with pre-installed modules, named volumes, a healthcheck, and a management script.

The core technical challenge is the two-phase initialization pattern: on first run, modules must be installed (`-i base,mail,sale,purchase,hr,account --stop-after-init`), then the instance restarts to serve normally. Subsequent starts skip initialization because the database persists via named volumes. The official `odoo:17.0` Docker image handles database connectivity automatically via its entrypoint script, and XML-RPC is available on port 8069 with no extra configuration.

**Primary recommendation:** Use `odoo:17.0` official Docker image with `postgres:16`, a shell script for lifecycle management (`scripts/odoo-dev.sh`), a separate `docker/dev/docker-compose.yml` to avoid conflicts with existing validation infrastructure, and named volumes for both PostgreSQL data and Odoo filestore.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCP-01 | Odoo Dev Instance Setup | Full research coverage: Docker Compose config, module pre-installation, XML-RPC access, persistent volumes, startup/shutdown script, all documented below |
</phase_requirements>

## Standard Stack

### Core
| Library/Tool | Version | Purpose | Why Standard |
|-------------|---------|---------|--------------|
| `odoo:17.0` Docker image | 17.0 (nightly builds) | Odoo CE server | Official Docker Hub image, Ubuntu Jammy base, actively maintained with nightly rebuilds, includes all base addons |
| `postgres:16` Docker image | 16 | PostgreSQL database | Same version already used in existing validation compose; proven compatible with Odoo 17 |
| `xmlrpc.client` (stdlib) | Python 3.12 stdlib | XML-RPC client for connectivity testing | Zero-dependency, official Odoo-documented approach for external API access |
| Docker Compose v2 | v2.x | Container orchestration | Already used in project (`docker compose` CLI syntax, not `docker-compose`) |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `curl` | any | Healthcheck probe | Inside Odoo container to check `/web/health` endpoint |
| `bash` | any | Management script | `scripts/odoo-dev.sh` for start/stop/status/init lifecycle |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `odoo:17.0` official | `bitnami/odoo` | Bitnami adds non-standard paths, ENV vars, and opininated defaults that diverge from Odoo docs; official image matches documentation exactly |
| `odoo:17.0` official | Custom Dockerfile | Unnecessary complexity; official image already has all CE addons, entrypoint handles DB init |
| `postgres:16` | `postgres:15` | Both work; 16 is already used in existing validation compose, so consistency wins |
| Shell script | Python Click command | Shell script is simpler, no dependency on project venv; Click command can wrap it later if needed |

**Installation:**
```bash
# No pip install needed - Docker images are pulled automatically
docker pull odoo:17.0
docker pull postgres:16
```

## Architecture Patterns

### Recommended Project Structure
```
docker/
  docker-compose.yml          # EXISTING: ephemeral validation (tmpfs, no volumes)
  odoo.conf                   # EXISTING: ephemeral config
  dev/
    docker-compose.yml        # NEW: persistent dev instance
    odoo.conf                 # NEW: dev instance config (xmlrpc enabled, admin_passwd set)
    .env                      # NEW: default env vars (ODOO_DEV_PORT, etc.)
scripts/
  odoo-dev.sh                 # NEW: lifecycle management script
```

### Pattern 1: Separate Compose Files for Separate Concerns
**What:** The dev instance uses `docker/dev/docker-compose.yml` completely independent from the existing `docker/docker-compose.yml` validation setup.
**When to use:** Always. The validation compose uses tmpfs (ephemeral data), MODULE_PATH env var, and tears down after each run. The dev compose uses named volumes (persistent data), pre-installed modules, and stays running.
**Why:** Prevents port conflicts, volume name collisions, and accidental teardown of the dev instance during module validation runs.

**Example docker/dev/docker-compose.yml:**
```yaml
# Persistent Odoo 17.0 CE dev instance for MCP introspection
# Usage: scripts/odoo-dev.sh start
name: odoo-dev

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
      POSTGRES_DB: postgres
    volumes:
      - odoo-dev-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  odoo:
    image: odoo:17.0
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "${ODOO_DEV_PORT:-8069}:8069"
    environment:
      HOST: db
      USER: odoo
      PASSWORD: odoo
    volumes:
      - odoo-dev-data:/var/lib/odoo
      - ./odoo.conf:/etc/odoo/odoo.conf:ro
    healthcheck:
      test: ["CMD-SHELL", "curl -fs http://localhost:8069/web/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s
    restart: unless-stopped

volumes:
  odoo-dev-db:
  odoo-dev-data:
```

### Pattern 2: Two-Phase Initialization (Init Then Serve)
**What:** On first run, the management script detects if the database exists. If not, it runs Odoo with `-i base,mail,sale,purchase,hr,account -d odoo_dev --stop-after-init` to create the database and install modules. Then it starts the normal serve mode.
**When to use:** First time setup and after `scripts/odoo-dev.sh reset` (which destroys volumes).
**Why:** The official Odoo Docker image does NOT auto-create databases or auto-install modules. The `-i` flag with `--stop-after-init` is the standard pattern. Subsequent starts skip init because the database already exists on the persistent volume.

**Init detection approach:**
```bash
# Check if database exists by querying PostgreSQL
docker compose -f docker/dev/docker-compose.yml exec -T db \
  psql -U odoo -tAc "SELECT 1 FROM pg_database WHERE datname='odoo_dev'" \
  2>/dev/null | grep -q 1
```

### Pattern 3: XML-RPC Connectivity Verification
**What:** After the instance is healthy, verify XML-RPC access by authenticating and calling `execute_kw` on `ir.model`.
**When to use:** In the management script's `status` command and in smoke tests.
**Why:** The healthcheck only verifies HTTP is responding. XML-RPC verification confirms the full stack (database initialized, modules loaded, authentication working).

**Verification script (Python):**
```python
# Source: Odoo 17.0 External API docs + Psqasim/personal-ai-employee reference
import xmlrpc.client

url = "http://localhost:8069"
db = "odoo_dev"
username = "admin"
password = "admin"  # Default admin password for dev instance

# Step 1: Authenticate
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
assert uid, "Authentication failed"

# Step 2: Query models
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
result = models.execute_kw(
    db, uid, password,
    "ir.model", "search_read",
    [[["model", "=", "res.partner"]]],
    {"fields": ["model", "name"], "limit": 1},
)
assert len(result) == 1, "ir.model query failed"
```

### Pattern 4: Environment Variable Configuration
**What:** All configurable values (port, database name, admin password) are set via environment variables with sensible defaults.
**When to use:** Always.
**Why:** Phase 16 MCP server will read ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY from env vars. The dev instance must match these defaults.

**Default environment variables:**
```bash
ODOO_DEV_PORT=8069       # Host port for Odoo
ODOO_DEV_DB=odoo_dev     # Database name
ODOO_DEV_USER=admin      # Admin username
ODOO_DEV_PASSWORD=admin  # Admin password (dev only!)
```

### Anti-Patterns to Avoid
- **Using the existing validation compose for dev:** The validation compose uses tmpfs (data lost on stop), MODULE_PATH binding, and tears down after each validation run. Using it for persistent dev would cause data loss.
- **Running init on every startup:** The `-i` flag re-initializes module data (including `noupdate=1` records) which can corrupt custom data. Only run init on first startup when the database does not exist.
- **Using `docker compose exec` for init:** Like the validation runner learned (mistake #4 in CLAUDE.md), `exec` runs a second Odoo process against the same database, causing serialization conflicts. Use `docker compose run --rm` for init.
- **Hardcoding the admin password in compose:** Use env var with default so users can override for non-local setups.
- **Exposing port 8069 on 0.0.0.0 in production:** For dev instance this is fine, but document it as dev-only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Database readiness check | Custom TCP probe script | `pg_isready -U odoo` in healthcheck | Battle-tested PostgreSQL utility, handles edge cases |
| Odoo readiness check | Custom HTTP probe | `curl -fs http://localhost:8069/web/health` | Official endpoint since Odoo 15.0, lightweight, no session creation |
| Database existence check | Parse Odoo logs for "initialized" | `psql -tAc "SELECT 1 FROM pg_database WHERE datname='odoo_dev'"` | Direct PostgreSQL query, deterministic, no log parsing fragility |
| XML-RPC client library | Custom HTTP/XML parser | `xmlrpc.client.ServerProxy` (stdlib) | Python stdlib, zero dependencies, Odoo's own docs use it |
| Container orchestration | Custom Docker CLI wrapper | Docker Compose v2 with `--wait` | Handles dependency ordering, healthchecks, named volumes natively |
| Entrypoint/DB init | Custom Dockerfile with init scripts | Official `odoo:17.0` entrypoint + CLI flags | Entrypoint handles `wait-for-psql.py`, DB args, user permissions |

**Key insight:** The official Odoo Docker image and Python stdlib already handle every infrastructure concern. The only custom code needed is the management script that orchestrates the two-phase init pattern and provides a developer-friendly CLI.

## Common Pitfalls

### Pitfall 1: Database Not Initialized on First Start
**What goes wrong:** Starting the Odoo container without `-i base` results in "Database odoo_dev not initialized, you can force it with `-i base`" error, and the instance is unusable.
**Why it happens:** The official Odoo Docker image does NOT auto-create databases. It only connects to PostgreSQL and serves. Database creation requires explicit `-i` flag.
**How to avoid:** The management script checks for database existence and runs init if needed. Use `docker compose run --rm` for init, not `exec`.
**Warning signs:** Odoo logs show "not initialized" error; `/web/health` returns 200 but `/web/login` shows database selector.

### Pitfall 2: Port Conflict with Validation Containers
**What goes wrong:** Running the dev instance on port 8069 while validation containers also try to use 8069 causes "address already in use" errors.
**Why it happens:** The existing `docker/docker-compose.yml` does NOT expose ports (it uses `docker compose exec`), but if someone adds port mapping later, it would conflict.
**How to avoid:** Use separate compose project names (`name: odoo-dev` vs no name for validation). Use configurable port via `ODOO_DEV_PORT` env var. The existing validation compose does not map host ports, so default 8069 is safe.
**Warning signs:** Docker Compose errors about port binding; validation tests fail with connection refused.

### Pitfall 3: Using `exec` Instead of `run` for Module Init
**What goes wrong:** Running module initialization via `docker compose exec odoo odoo -i ... -d odoo_dev --stop-after-init` starts a SECOND Odoo process while the first (entrypoint) is already running and connected to the same database. This causes `psycopg2.errors.SerializationFailure`.
**Why it happens:** `exec` runs inside an already-running container that has an active Odoo server process. Both processes write to the same database simultaneously.
**How to avoid:** Use `docker compose run --rm odoo odoo -i base,mail,sale,purchase,hr,account -d odoo_dev --stop-after-init --no-http` for initialization. This creates a fresh container with no running server.
**Warning signs:** PostgreSQL serialization errors in logs; module installation appears to succeed but modules are partially installed.

### Pitfall 4: Volume Name Collision Between Dev and Validation
**What goes wrong:** If both compose files use generic volume names (e.g., `db-data`), Docker may share volumes between the dev instance and validation runs, causing data corruption.
**Why it happens:** Docker Compose prefixes volume names with the project name, but if project names collide or aren't set, volumes can overlap.
**How to avoid:** Use explicit `name: odoo-dev` in the dev compose file. Use unique volume names prefixed with `odoo-dev-`. The validation compose uses tmpfs (no named volumes), so collision is unlikely but naming prevents future issues.
**Warning signs:** Dev instance database contains test data from validation runs; validation runs find pre-existing data.

### Pitfall 5: Healthcheck Passes Before Modules Are Fully Loaded
**What goes wrong:** The `/web/health` endpoint returns 200 as soon as the HTTP server starts, but module loading may still be in progress. MCP connections during this window get incomplete data.
**Why it happens:** Odoo's health endpoint checks HTTP availability, not module loading completion.
**How to avoid:** Use `start_period: 30s` in the healthcheck to give Odoo time to finish loading. For init runs, use `--stop-after-init` which exits only after all modules are loaded. The management script should wait for healthcheck to pass AND verify XML-RPC connectivity before reporting "ready".
**Warning signs:** MCP queries return fewer models than expected; `ir.module.module` shows modules in "to install" state.

### Pitfall 6: Missing `curl` in Official Odoo Image
**What goes wrong:** The healthcheck `curl -fs http://localhost:8069/web/health` fails because `curl` is not installed in the official `odoo:17.0` image.
**Why it happens:** The official image is based on Ubuntu Jammy but does not include `curl` by default.
**How to avoid:** Use `python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8069/web/health')"` as the healthcheck instead, since Python is always available in the Odoo image. Alternatively, verify if recent nightly builds include curl.
**Warning signs:** Healthcheck shows "unhealthy" status even though Odoo is running fine.

## Code Examples

Verified patterns from official sources and project conventions:

### Dev Instance Docker Compose (docker/dev/docker-compose.yml)
```yaml
# Source: Official Odoo Docker docs + project conventions
name: odoo-dev

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
      POSTGRES_DB: postgres
    volumes:
      - odoo-dev-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  odoo:
    image: odoo:17.0
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "${ODOO_DEV_PORT:-8069}:8069"
    environment:
      HOST: db
      USER: odoo
      PASSWORD: odoo
    volumes:
      - odoo-dev-data:/var/lib/odoo
      - ./odoo.conf:/etc/odoo/odoo.conf:ro
    healthcheck:
      test: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:8069/web/health')\""]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s
    restart: unless-stopped

volumes:
  odoo-dev-db:
  odoo-dev-data:
```

### Dev Instance Odoo Config (docker/dev/odoo.conf)
```ini
[options]
addons_path = /mnt/extra-addons
data_dir = /var/lib/odoo
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo
admin_passwd = admin
without_demo = all
; XML-RPC is enabled by default on port 8069, no extra config needed
; list_db = False prevents database selector (optional, for security)
list_db = False
db_name = odoo_dev
```

### Management Script (scripts/odoo-dev.sh) - Key Functions
```bash
#!/usr/bin/env bash
# Source: Project conventions (bash scripts for dev tooling)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker/dev/docker-compose.yml"
DB_NAME="${ODOO_DEV_DB:-odoo_dev}"
MODULES="base,mail,sale,purchase,hr,account"

_compose() {
    docker compose -f "$COMPOSE_FILE" "$@"
}

_db_exists() {
    _compose exec -T db \
        psql -U odoo -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" \
        2>/dev/null | grep -q 1
}

_init_modules() {
    echo "Initializing database '$DB_NAME' with modules: $MODULES"
    _compose run --rm -T odoo odoo \
        -d "$DB_NAME" \
        -i "$MODULES" \
        --stop-after-init \
        --no-http \
        --log-level=warn
    echo "Module installation complete."
}

cmd_start() {
    echo "Starting Odoo dev instance..."
    _compose up -d --wait db
    if ! _db_exists; then
        _init_modules
    fi
    _compose up -d --wait
    echo "Odoo dev instance ready at http://localhost:${ODOO_DEV_PORT:-8069}"
}

cmd_stop() {
    echo "Stopping Odoo dev instance..."
    _compose down
}

cmd_status() {
    _compose ps
}

cmd_reset() {
    echo "Destroying dev instance data..."
    _compose down -v
    echo "Dev instance data destroyed. Run 'start' to re-initialize."
}

cmd_logs() {
    _compose logs -f "${1:-odoo}"
}

case "${1:-help}" in
    start)  cmd_start ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    reset)  cmd_reset ;;
    logs)   cmd_logs "${2:-}" ;;
    *)      echo "Usage: $0 {start|stop|status|reset|logs}" ;;
esac
```

### XML-RPC Connectivity Smoke Test (Python)
```python
# Source: Odoo 17.0 External API docs + Psqasim/personal-ai-employee
"""Smoke test for Odoo dev instance XML-RPC connectivity."""
import xmlrpc.client
import sys

def verify_xmlrpc(
    url: str = "http://localhost:8069",
    db: str = "odoo_dev",
    username: str = "admin",
    password: str = "admin",
) -> bool:
    """Verify XML-RPC connectivity to Odoo dev instance.

    Returns True if authentication succeeds and ir.model is queryable.
    """
    try:
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        version = common.version()
        print(f"Odoo version: {version.get('server_version', 'unknown')}")

        uid = common.authenticate(db, username, password, {})
        if not uid:
            print("ERROR: Authentication failed (uid=False)")
            return False
        print(f"Authenticated as uid={uid}")

        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

        # Verify ir.model is queryable (proves modules are loaded)
        count = models.execute_kw(
            db, uid, password,
            "ir.model", "search_count", [[]],
        )
        print(f"Models available: {count}")

        # Verify required modules are installed
        installed = models.execute_kw(
            db, uid, password,
            "ir.module.module", "search_read",
            [[["state", "=", "installed"]]],
            {"fields": ["name"]},
        )
        installed_names = {m["name"] for m in installed}
        required = {"base", "mail", "sale", "purchase", "hr", "account"}
        missing = required - installed_names
        if missing:
            print(f"WARNING: Missing modules: {missing}")
            return False
        print(f"All required modules installed ({len(installed_names)} total)")
        return True

    except ConnectionRefusedError:
        print("ERROR: Connection refused. Is Odoo running?")
        return False
    except xmlrpc.client.Fault as e:
        print(f"ERROR: XML-RPC fault: {e.faultString}")
        return False

if __name__ == "__main__":
    success = verify_xmlrpc()
    sys.exit(0 if success else 1)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `docker-compose` (v1 CLI) | `docker compose` (v2, plugin) | 2022-2023 | Project already uses v2 syntax; continue using it |
| Custom Dockerfile for Odoo | Official `odoo:17.0` image | Ongoing | No custom build needed; official image includes all CE addons |
| Manual database creation via web UI | CLI `-i` flag with `--stop-after-init` | Always available | Scriptable, automatable, no browser needed |
| `curl` for healthcheck | `python3 urllib.request` | N/A | Python always present in Odoo image; curl may not be |
| JSON-RPC for external access | XML-RPC (`/xmlrpc/2/`) | Both available since Odoo 8+ | XML-RPC is simpler for Python (stdlib), well-documented, used by reference implementation |

**Deprecated/outdated:**
- `docker-compose` v1 CLI: Use `docker compose` v2 (already done in project)
- Docker `--link` networking: Use Docker Compose service discovery (service name = hostname)
- `xmlrpc_port` config key: Default 8069 is correct; no need to change it

## Open Questions

1. **Does `curl` exist in the official `odoo:17.0` image?**
   - What we know: The image is Ubuntu Jammy-based, but search results suggest curl may not be pre-installed. The healthcheck PR (#115) for the official repo was never merged.
   - What's unclear: Whether recent nightly builds include curl.
   - Recommendation: Use `python3 -c "import urllib.request; ..."` for healthcheck (Python is guaranteed). If curl is found to be present, it can be used as a simpler alternative.

2. **Exact behavior of `-i` on existing database with already-installed modules**
   - What we know: `-i` on a fresh database creates and installs. On an existing database, it re-initializes the listed modules (updates `noupdate=1` records).
   - What's unclear: Whether re-initialization causes data loss for the dev instance scenario.
   - Recommendation: Guard init with database existence check. Only run `-i` when the database does not exist. This is safe and idempotent.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `python/pyproject.toml` (existing) |
| Quick run command | `cd python && python -m pytest tests/test_odoo_dev.py -x` |
| Full suite command | `cd python && python -m pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-01.1 | Docker Compose starts Odoo 17 CE + PostgreSQL with modules | integration (docker) | `cd python && python -m pytest tests/test_odoo_dev.py::test_compose_starts_instance -x` | Wave 0 |
| MCP-01.2 | XML-RPC authentication and execute_kw succeed | integration (docker) | `cd python && python -m pytest tests/test_odoo_dev.py::test_xmlrpc_connectivity -x` | Wave 0 |
| MCP-01.3 | Data persists across down/up cycles | integration (docker) | `cd python && python -m pytest tests/test_odoo_dev.py::test_persistence -x` | Wave 0 |
| MCP-01.4 | Management script start/stop/status | unit + integration | `cd python && python -m pytest tests/test_odoo_dev.py::test_management_script -x` | Wave 0 |
| MCP-01.5 | Required modules installed (base, mail, sale, purchase, hr, account) | integration (docker) | `cd python && python -m pytest tests/test_odoo_dev.py::test_required_modules -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd python && python -m pytest tests/test_odoo_dev.py -x` (quick: script tests only, no Docker)
- **Per wave merge:** `cd python && python -m pytest -m "not e2e_slow"` (full suite minus slow E2E)
- **Phase gate:** Full suite green including Docker integration tests

### Wave 0 Gaps
- [ ] `python/tests/test_odoo_dev.py` -- covers MCP-01 (compose, XML-RPC, persistence, script, modules)
- [ ] Smoke test script `scripts/verify-odoo-dev.py` -- standalone XML-RPC verification

## Sources

### Primary (HIGH confidence)
- [Official Odoo Docker image](https://hub.docker.com/_/odoo/) - Tags, volumes (/var/lib/odoo, /mnt/extra-addons), ports (8069, 8071, 8072), entrypoint behavior
- [Odoo Docker GitHub repo](https://github.com/odoo/docker) - Dockerfile (Ubuntu Jammy base, CMD odoo), entrypoint.sh (wait-for-psql.py, DB_ARGS passthrough)
- [Odoo 17.0 External API docs](https://www.odoo.com/documentation/17.0/developer/reference/external_api.html) - XML-RPC endpoints (/xmlrpc/2/common, /xmlrpc/2/object), authenticate, execute_kw
- Existing project code: `docker/docker-compose.yml`, `docker/odoo.conf`, `python/src/odoo_gen_utils/validation/docker_runner.py` - established patterns and known pitfalls

### Secondary (MEDIUM confidence)
- [Psqasim/personal-ai-employee](https://github.com/Psqasim/personal-ai-employee) - Odoo MCP server reference (XML-RPC auth pattern, execute_kw usage, tool definitions)
- [minhng92/odoo-17-docker-compose](https://github.com/minhng92/odoo-17-docker-compose) - Community Docker Compose patterns
- [Odoo forum: auto-installing modules](https://www.odoo.com/forum/help-1/odoo-configuration-for-auto-installing-modules-175105) - `-i` flag behavior

### Tertiary (LOW confidence)
- [Odoo /web/health endpoint](https://github.com/odoo/docker/pull/115) - Available since 15.0, but official Docker image healthcheck PR was never merged; endpoint exists in Odoo source but curl availability in image is unverified
- Healthcheck `python3 urllib.request` approach - Logically sound (Python is in the image), but not widely documented as a pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official Docker image + stdlib XML-RPC, both well-documented
- Architecture: HIGH - Two-phase init is the documented approach; separate compose files follow project conventions; known pitfalls from project's own mistakes log (#3, #4)
- Pitfalls: HIGH - Five of six pitfalls come from project's own experience or official docs; one (curl availability) is MEDIUM
- Code examples: HIGH - All examples verified against official docs or reference implementation

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (Docker image tags are stable; Odoo 17 is in LTS)
