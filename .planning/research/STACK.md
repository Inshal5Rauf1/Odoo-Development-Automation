# Stack Research

**Domain:** Multi-agent AI orchestration for Odoo module code generation
**Researched:** 2026-03-01
**Confidence:** MEDIUM-HIGH (verified via PyPI, GitHub, official docs; some agent-orchestration patterns are emerging/unstable)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12.x | Runtime language | Odoo 17 supports 3.10-3.12. Python 3.12 is the highest version Odoo 17 supports, gives access to modern features (f-strings in logging, improved error messages, per-interpreter GIL), and is compatible with every library in this stack. Python 3.13+ breaks Odoo 17. **Confidence: HIGH** (verified via Odoo docs and Docker image) |
| uv | latest | Package/project manager | 10-100x faster than pip, replaces pip+poetry+pyenv+virtualenv in one tool. Written in Rust by Astral. Community consensus in 2026 is to use uv for new projects. Uses standard `pyproject.toml`. **Confidence: HIGH** (verified via official docs, massive adoption) |
| Typer | 0.24.x | CLI framework | Built on Click, uses Python type hints for zero-boilerplate command definitions. Auto-generates help text, supports subcommands, shell completion. Cleaner than raw Click for our use case (`odoo-gen describe`, `odoo-gen search`, `odoo-gen generate`). **Confidence: HIGH** (verified via PyPI: 0.24.1, requires Python >=3.10) |
| Rich | 14.3.x | Terminal UI (progress bars, panels, tables) | The standard library for beautiful terminal output in Python. Progress bars for agent execution, panels for checkpoint reviews, tables for search results, syntax highlighting for generated code preview. **Confidence: HIGH** (verified via PyPI: 14.3.3) |
| Pydantic | 2.12.x | Data validation, settings, schemas | Industry standard for Python data validation. Defines module specs, agent configs, search results, checkpoint data as typed models. Used by every major AI framework. **Confidence: HIGH** (verified via PyPI: 2.12.5 stable, 2.13.0b2 pre-release) |

### Agent Orchestration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| asyncio (stdlib) | 3.12 built-in | Async subprocess management | `asyncio.create_subprocess_exec()` spawns Claude Code, Codex CLI, Gemini CLI as independent subprocesses. Native to Python, no dependency. Enables parallel agent execution with timeout control, stdout/stderr streaming, and graceful cancellation. **Confidence: HIGH** (stdlib, well-documented) |
| Custom orchestrator (not CrewAI/LangGraph) | N/A | Agent coordination layer | Build a thin custom orchestrator because: (1) Claude Code, Codex CLI, Gemini CLI are CLI tools spawned as subprocesses, not API-based agents that fit CrewAI/LangGraph models; (2) our orchestration is deterministic (fixed pipeline: search -> scaffold -> models -> views -> security -> tests), not conversational multi-agent debate; (3) avoiding a heavy framework dependency for what is fundamentally "run CLI tools in sequence with checkpoints." MCO validates this subprocess-adapter pattern but is too generic for our domain-specific pipeline. **Confidence: MEDIUM** (pattern validated by MCO, claude-octopus, parallel-code projects) |
| Pydantic-AI | 1.63.x | Structured LLM output parsing | When calling LLM APIs directly (for intent parsing, module spec generation, code review), Pydantic-AI gives type-safe structured outputs with validation. Model-agnostic (supports Anthropic, OpenAI, Gemini). Use this for the "brain" tasks; use subprocess for the "hands" tasks (Claude Code writing files). **Confidence: MEDIUM** (verified via PyPI: 1.63.0, relatively new but backed by Pydantic team) |

### Semantic Search & Matching

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| sentence-transformers | 5.2.x | Embedding generation | State-of-the-art text embedding library. Use `all-MiniLM-L6-v2` model (22MB, 384-dim, 5x faster than alternatives, good quality for our domain). Encodes module descriptions, README content, manifest data into vectors for semantic matching. **Confidence: HIGH** (verified via PyPI: 5.2.3, mature library by Hugging Face) |
| ChromaDB | 1.5.x | Local vector database | Stores and queries module embeddings locally. No external service needed. Persistent storage via Apache Arrow format. Rust-core rewrite in 2025 gives 4x performance. Simple Python API: `collection.add()`, `collection.query()`. Perfect for our scale (thousands of modules, not millions). **Confidence: HIGH** (verified via PyPI: 1.5.2, active development) |
| PyGithub | 2.8.x | GitHub API access | Typed Python interface to GitHub REST API v3. Search repos, read files, clone URLs, read README content. Well-maintained, 6k+ GitHub stars. **Confidence: HIGH** (verified via PyPI: 2.8.1) |

### Odoo Tooling

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Docker (official odoo image) | `odoo:17.0` | Module validation environment | Official Odoo Docker image for installing and testing generated modules. Nightly builds ensure latest patches. Use `docker-compose` with Odoo + PostgreSQL for isolated validation. **Confidence: HIGH** (verified via Docker Hub, actively maintained) |
| docker (Python SDK) | 7.1.x | Programmatic Docker control | Python SDK for Docker Engine API. Build containers, run `odoo -i module_name --test-enable`, stream logs, check exit codes -- all from Python. Preferred over shelling out to `docker` CLI. **Confidence: HIGH** (verified via GitHub: 7.1.0, official Docker project) |
| pylint-odoo | 10.0.x | OCA quality linting | Official OCA pylint plugin. Validates Odoo coding standards, manifest structure, security declarations, i18n patterns. Use with `--valid-odoo-versions=17.0` flag. **Confidence: HIGH** (verified via PyPI: 10.0.1, official OCA tool) |
| Jinja2 | 3.1.x | Module code templating | Template engine for generating Odoo module boilerplate (models, views, security XML, manifests). Template inheritance for base patterns + customization. Battle-tested, used by Ansible/Cookiecutter for similar scaffolding. **Confidence: HIGH** (verified via PyPI: 3.1.6) |

### Testing

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pytest | 9.0.x | Test runner | Standard Python test framework. Fixtures for Docker containers, parameterized tests for different module types, async support. **Confidence: HIGH** (verified via PyPI: 9.0.2) |
| pytest-asyncio | latest | Async test support | Tests for async subprocess orchestration, parallel agent execution. **Confidence: HIGH** (mature pytest plugin) |
| pytest-cov | latest | Coverage reporting | 80% coverage target per project rules. **Confidence: HIGH** |
| pytest-docker | latest | Docker fixture management | Manage Odoo Docker containers in test fixtures. Spin up/teardown per test session. **Confidence: MEDIUM** (useful but may need custom fixtures) |

### Development Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| Ruff | 0.15.x | Linter + formatter | Replaces Flake8+Black+isort. 150-200x faster. Single tool. 2026 style guide. Used by FastAPI, Pandas, SciPy. Run alongside pylint-odoo (Ruff handles Python style, pylint-odoo handles Odoo-specific rules). **Confidence: HIGH** (verified: 0.15.4) |
| mypy | latest | Type checking | Static type checking for the orchestrator codebase. Pydantic models + type hints give strong type safety. **Confidence: HIGH** |
| pre-commit | latest | Git hook management | Run ruff, mypy, pylint-odoo checks before commits. **Confidence: HIGH** |

## Installation

```bash
# Initialize project with uv
uv init odoo-gen
cd odoo-gen

# Set Python version (critical: must be 3.12 for Odoo 17 compat)
uv python pin 3.12

# Core dependencies
uv add typer rich pydantic pydantic-ai
uv add sentence-transformers chromadb
uv add PyGithub docker jinja2
uv add pylint-odoo

# Dev dependencies
uv add --dev pytest pytest-asyncio pytest-cov pytest-docker
uv add --dev ruff mypy pre-commit
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Typer (CLI) | Click | If you need lower-level control over CLI parsing or complex middleware chains. Typer wraps Click, so you can drop down when needed. |
| Typer (CLI) | argparse | Never for this project. Too verbose, no auto-completion, no rich help formatting. |
| ChromaDB (vector DB) | FAISS | If you need pure speed at millions of vectors. ChromaDB is simpler for our scale (thousands of modules) and handles persistence natively. |
| ChromaDB (vector DB) | Qdrant/Milvus | If you need a production search service. Overkill for a local CLI tool. |
| Custom orchestrator | CrewAI | If agents were API-based LLM calls with conversational handoffs. Our agents are CLI subprocesses with deterministic pipelines. CrewAI adds complexity without matching our execution model. |
| Custom orchestrator | LangGraph | If you need complex conditional branching between LLM calls with state machines. Our pipeline is linear with checkpoints, not a graph. |
| Custom orchestrator | MCO | If you wanted a generic multi-agent dispatcher. MCO is a good reference architecture but too generic -- we need domain-specific pipeline logic (search -> scaffold -> models -> views -> etc). |
| Pydantic-AI (structured output) | LangChain | If you needed a full RAG pipeline with memory, chains, retrieval. Massive dependency tree for what we need (structured LLM output). Pydantic-AI is lighter and type-safe. |
| sentence-transformers (embeddings) | OpenAI text-embedding-3-small | If you want API-based embeddings. Adds cost per query and network dependency. Local embeddings are free, fast, and work offline. |
| Ruff (linter/formatter) | Flake8 + Black + isort | Never for new projects in 2026. Ruff does all three, 150x faster, single config. |
| uv (package manager) | Poetry | If publishing a library to PyPI (Poetry has better publishing workflow). For an application/CLI tool, uv is superior in every way. |
| uv (package manager) | pip + venv | Never for new projects. uv is a strict superset with 10-100x speed improvement. |
| Docker Python SDK | subprocess + docker CLI | If you want simpler code at the cost of error handling. SDK gives typed responses, event streaming, and proper error classes. |
| PyGithub (GitHub API) | requests + GitHub REST API | If you need only 1-2 API calls. PyGithub gives typed models, pagination, rate limit handling for comprehensive repo search. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Python 3.13+ | Odoo 17 does not support Python 3.13 or later. Module validation will fail. | Python 3.12.x |
| Python 3.9 or lower | Too old for Typer (>=3.10), sentence-transformers (>=3.10), pydantic-ai (>=3.10) | Python 3.12.x |
| LangChain (for orchestration) | Massive dependency tree (~50+ packages), abstractions designed for RAG/chat not CLI subprocess orchestration, version churn | Pydantic-AI for structured output, asyncio for subprocess management |
| CrewAI / AutoGen | Designed for conversational multi-agent debate patterns, not deterministic CLI tool pipelines | Custom orchestrator with asyncio subprocess |
| n8n / Temporal / Airflow | Workflow engines add infrastructure complexity (servers, databases, UIs) for a CLI tool that runs on a developer's machine | Python asyncio with checkpoint files |
| Pinecone / Weaviate | Cloud vector databases requiring API keys, network calls, and ongoing costs for what can be done locally with ChromaDB | ChromaDB (local, free, sufficient scale) |
| Flake8 + Black + isort | Three separate tools, 150x slower than Ruff, more config files to maintain | Ruff (single tool, single config) |
| Poetry | Slower dependency resolution, heavier than uv, less actively developed | uv |
| setup.py / setup.cfg | Legacy Python packaging formats | pyproject.toml with uv |
| YAML for app config | Security risks with arbitrary code execution, type ambiguity (Norway problem), no built-in Python support | TOML (built-in tomllib in 3.12, safe by design) |

## Stack Patterns by Variant

**If building the "brain" (intent parsing, spec generation, code review):**
- Use Pydantic-AI with structured output models
- Define Pydantic schemas for ModuleSpec, SearchQuery, CodeReviewResult
- Call Anthropic/OpenAI/Gemini APIs with type-safe responses
- Because: need reliable structured data from LLMs, not free-form text

**If building the "hands" (actual code generation):**
- Use asyncio.create_subprocess_exec() to spawn Claude Code / Codex CLI / Gemini CLI
- Pass prompts via stdin or temp files, capture stdout/stderr
- Because: these CLI tools handle file creation, context management, and multi-file editing better than raw API calls

**If building the "validator" (module quality checks):**
- Use Docker Python SDK to manage Odoo containers
- Run `odoo -i module_name --test-enable --stop-after-init` in container
- Run `pylint --load-plugins=pylint_odoo --valid-odoo-versions=17.0` on generated code
- Because: only a real Odoo instance can validate module installation, and pylint-odoo is the OCA standard

**If building the "search" (finding existing modules):**
- Use PyGithub to search GitHub/OCA repos
- Use sentence-transformers + ChromaDB for semantic matching
- Build an index of module manifests (name, description, depends, data files)
- Because: keyword search misses semantic matches ("leave management" should find "hr_holidays")

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Python 3.12 | Odoo 17.0 | Maximum supported version. Do NOT use 3.13+. |
| Python 3.12 | All recommended packages | Every package in this stack supports 3.12. |
| Typer 0.24.x | Click 8.x | Typer wraps Click. Both installed together. |
| Typer 0.24.x | Rich 14.x | Typer uses Rich for help formatting when installed. |
| Pydantic 2.12.x | Pydantic-AI 1.63.x | Pydantic-AI requires Pydantic v2. |
| sentence-transformers 5.2.x | torch 2.x | Requires PyTorch. Large dependency (~2GB). Consider CPU-only install. |
| ChromaDB 1.5.x | sentence-transformers 5.2.x | ChromaDB can use sentence-transformers as embedding function. |
| pylint-odoo 10.0.x | pylint 3.x | Requires specific pylint version range. Check compatibility. |
| Docker SDK 7.1.x | Docker Engine 24+ | Requires Docker daemon running locally. |

## Configuration

```toml
# pyproject.toml (key sections)

[project]
name = "odoo-gen"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
    "typer>=0.24",
    "rich>=14.0",
    "pydantic>=2.12",
    "pydantic-ai>=1.60",
    "sentence-transformers>=5.2",
    "chromadb>=1.5",
    "PyGithub>=2.8",
    "docker>=7.1",
    "jinja2>=3.1",
    "pylint-odoo>=10.0",
]

[project.scripts]
odoo-gen = "odoo_gen.cli:app"

[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "SIM", "TCH"]

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## Dependency Size Warning

sentence-transformers pulls in PyTorch (~2GB for CPU-only). For development this is fine, but for distribution consider:
1. CPU-only PyTorch: `uv add torch --extra-index-url https://download.pytorch.org/whl/cpu`
2. Pre-built embedding index: compute embeddings once, ship the ChromaDB database
3. API-based fallback: offer OpenAI text-embedding-3-small as an alternative for users who want smaller installs

## Sources

- [Odoo 17 Docker Hub](https://hub.docker.com/_/odoo) -- Docker image tags and compatibility (HIGH confidence)
- [Odoo 17 Python compatibility](https://www.vrajatechnologies.com/blog/1/complete-odoo-installation-guide-for-odoo-17-18-19-82) -- Python 3.10-3.12 requirement (HIGH confidence)
- [Typer PyPI](https://pypi.org/project/typer/) -- Version 0.24.1, Python >=3.10 (HIGH confidence)
- [Rich PyPI](https://pypi.org/project/rich/) -- Version 14.3.3 (HIGH confidence)
- [Pydantic PyPI](https://pypi.org/project/pydantic/) -- Version 2.12.5 (HIGH confidence)
- [Pydantic-AI PyPI](https://pypi.org/project/pydantic-ai/) -- Version 1.63.0 (MEDIUM confidence, newer library)
- [sentence-transformers PyPI](https://pypi.org/project/sentence-transformers/) -- Version 5.2.3 (HIGH confidence)
- [ChromaDB PyPI](https://pypi.org/project/chromadb/) -- Version 1.5.2 (HIGH confidence)
- [PyGithub PyPI](https://pypi.org/project/PyGithub/) -- Version 2.8.1 (HIGH confidence)
- [Docker Python SDK GitHub](https://github.com/docker/docker-py) -- Version 7.1.0 (HIGH confidence)
- [pylint-odoo PyPI](https://pypi.org/project/pylint-odoo/) -- Version 10.0.1 (HIGH confidence)
- [Ruff PyPI](https://pypi.org/project/ruff/) -- Version 0.15.4 (HIGH confidence)
- [pytest PyPI](https://pypi.org/project/pytest/) -- Version 9.0.2 (HIGH confidence)
- [uv docs](https://docs.astral.sh/uv/) -- Package manager (HIGH confidence)
- [MCO GitHub](https://github.com/mco-org/mco) -- Subprocess adapter pattern reference (MEDIUM confidence)
- [Jinja2 PyPI](https://pypi.org/project/Jinja2/) -- Version 3.1.6 (HIGH confidence)

---
*Stack research for: Agentic Odoo Module Development Workflow*
*Researched: 2026-03-01*
