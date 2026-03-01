# Architecture Research

**Domain:** Multi-agent AI code generation system (Odoo module automation)
**Researched:** 2026-03-01
**Confidence:** MEDIUM -- architecture patterns are well-documented in industry, but this specific combination (multi-LLM orchestration + semantic search + Odoo domain + fork-and-extend workflow) is novel enough that integration patterns need validation during implementation.

## Standard Architecture

### System Overview

```
                            USER INTERFACE LAYER
 ┌──────────────────────────────────────────────────────────────────────┐
 │  CLI (odoo-gen)                                                      │
 │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
 │  │  Command      │  │  Interactive  │  │  Checkpoint Review       │   │
 │  │  Parser       │  │  Questioner   │  │  Interface               │   │
 │  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘   │
 └─────────┼─────────────────┼───────────────────────┼─────────────────┘
           │                 │                       │
           ▼                 ▼                       ▼
                        ORCHESTRATION LAYER
 ┌──────────────────────────────────────────────────────────────────────┐
 │  Pipeline Orchestrator (Python)                                      │
 │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
 │  │  Pipeline     │  │  State        │  │  Human Checkpoint        │   │
 │  │  Controller   │  │  Manager      │  │  Manager                 │   │
 │  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘   │
 │         │                 │                       │                  │
 │  ┌──────┴─────────────────┴───────────────────────┴──────────────┐   │
 │  │                  Agent Router / Dispatcher                     │   │
 │  └──────────────────────────┬────────────────────────────────────┘   │
 └─────────────────────────────┼────────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
                      AGENT EXECUTION LAYER
 ┌──────────────────────────────────────────────────────────────────────┐
 │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
 │  │  Claude Code  │  │  Codex CLI   │  │  Gemini CLI              │   │
 │  │  Adapter      │  │  Adapter     │  │  Adapter                 │   │
 │  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘   │
 │         │                 │                       │                  │
 │  ┌──────┴─────────────────┴───────────────────────┴──────────────┐   │
 │  │              Odoo Domain Skills / Prompts                      │   │
 │  │  (models, views, security, wizards, reports, tests, i18n)      │   │
 │  └───────────────────────────────────────────────────────────────┘   │
 └──────────────────────────────────────────────────────────────────────┘
           │                   │                   │
           ▼                   ▼                   ▼
                       SEARCH & RETRIEVAL LAYER
 ┌──────────────────────────────────────────────────────────────────────┐
 │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
 │  │  GitHub       │  │  OCA          │  │  Embedding               │   │
 │  │  Search       │  │  Search       │  │  Index                   │   │
 │  │  Client       │  │  Client       │  │  (Vector DB)             │   │
 │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
 └──────────────────────────────────────────────────────────────────────┘
           │                   │                   │
           ▼                   ▼                   ▼
                       VALIDATION LAYER
 ┌──────────────────────────────────────────────────────────────────────┐
 │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
 │  │  Docker       │  │  pylint-odoo  │  │  Odoo Install            │   │
 │  │  Manager      │  │  Checker     │  │  + Test Runner           │   │
 │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
 └──────────────────────────────────────────────────────────────────────┘
           │                   │                   │
           ▼                   ▼                   ▼
                        OUTPUT LAYER
 ┌──────────────────────────────────────────────────────────────────────┐
 │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
 │  │  Module       │  │  Git          │  │  Report                  │   │
 │  │  Scaffolder   │  │  Manager     │  │  Generator               │   │
 │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
 └──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **CLI (odoo-gen)** | Parse user commands, present interactive questionnaire, display checkpoint review prompts, show progress | Python CLI with `click` or `typer`, rich terminal output via `rich` |
| **Interactive Questioner** | Gather structured requirements from natural language description via follow-up questions | LLM-powered question generation, schema-validated response collection |
| **Pipeline Controller** | Orchestrate the full generation flow: search -> decide -> generate -> validate -> output | Python async pipeline with defined stage transitions |
| **State Manager** | Persist pipeline state across stages, enable resume-on-failure, track generation artifacts | JSON/SQLite state files in working directory |
| **Human Checkpoint Manager** | Pause pipeline at defined gates, present generated artifacts for review, accept/reject/modify | Terminal-based diff viewer, approval prompts |
| **Agent Router** | Select which AI agent handles each task based on task type and agent strengths | Configuration-driven routing with fallback chains |
| **Claude Code Adapter** | Interface with Claude Code CLI for code generation tasks | Subprocess wrapper around `claude` CLI |
| **Codex CLI Adapter** | Interface with OpenAI Codex CLI for code generation tasks | Subprocess wrapper around `codex` CLI |
| **Gemini CLI Adapter** | Interface with Gemini CLI for code generation tasks | Subprocess wrapper around `gemini` CLI |
| **Odoo Domain Skills** | Encode Odoo-specific patterns: model definitions, XML views, security ACLs, manifest structure | Prompt templates + AGENTS.md / custom instructions per agent |
| **GitHub Search Client** | Search GitHub repos for similar Odoo modules | GitHub API + optional embedding-based re-ranking |
| **OCA Search Client** | Search OCA organization repos specifically | GitHub API scoped to `github.com/OCA/*` repos |
| **Embedding Index** | Semantic similarity search over module descriptions and README content | FAISS or ChromaDB with sentence-transformers embeddings |
| **Docker Manager** | Spin up/tear down Odoo 17.0 containers for validation | Docker SDK for Python, pre-built Odoo 17 image |
| **pylint-odoo Checker** | Run OCA quality checks on generated code | `pylint --load-plugins=pylint_odoo` subprocess |
| **Odoo Install + Test Runner** | Install module in Docker Odoo instance, run unit/integration tests | `odoo -i module_name --test-enable` in container |
| **Module Scaffolder** | Create Odoo module directory structure from template | Jinja2 templates for `__manifest__.py`, models/, views/, security/, etc. |
| **Git Manager** | Fork repos, create branches, manage generated module as git repo | `gitpython` or subprocess git commands |
| **Report Generator** | Produce summary of generation process: what was generated, test results, quality scores | Markdown/HTML report output |

## Recommended Project Structure

```
odoo-gen/
├── src/
│   ├── cli/                    # CLI entry points and commands
│   │   ├── __init__.py
│   │   ├── main.py             # typer/click app, top-level commands
│   │   ├── questioner.py       # Interactive requirement gathering
│   │   └── checkpoint.py       # Human review checkpoint UI
│   │
│   ├── orchestrator/           # Pipeline orchestration
│   │   ├── __init__.py
│   │   ├── pipeline.py         # Main pipeline controller
│   │   ├── state.py            # Pipeline state management
│   │   ├── router.py           # Agent task routing
│   │   └── checkpoints.py      # Checkpoint definitions and handlers
│   │
│   ├── agents/                 # AI agent adapters
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract agent interface
│   │   ├── claude_adapter.py   # Claude Code CLI wrapper
│   │   ├── codex_adapter.py    # Codex CLI wrapper
│   │   ├── gemini_adapter.py   # Gemini CLI wrapper
│   │   └── fallback.py         # Fallback chain logic
│   │
│   ├── search/                 # Search and retrieval
│   │   ├── __init__.py
│   │   ├── github_client.py    # GitHub API search
│   │   ├── oca_client.py       # OCA-specific search
│   │   ├── embeddings.py       # Vector embedding generation
│   │   ├── index.py            # Vector index management
│   │   └── ranker.py           # Result scoring and ranking
│   │
│   ├── generator/              # Code generation logic
│   │   ├── __init__.py
│   │   ├── scaffolder.py       # Module directory scaffolding
│   │   ├── fork_handler.py     # Fork-and-extend workflow
│   │   ├── scratch_handler.py  # Build-from-scratch workflow
│   │   └── tasks/              # Per-file-type generation tasks
│   │       ├── models.py       # ORM model generation
│   │       ├── views.py        # XML view generation
│   │       ├── security.py     # ACL and record rule generation
│   │       ├── wizards.py      # Wizard generation
│   │       ├── reports.py      # QWeb report generation
│   │       ├── controllers.py  # HTTP controller generation
│   │       ├── tests.py        # Test generation
│   │       └── i18n.py         # Internationalization
│   │
│   ├── skills/                 # Odoo domain knowledge
│   │   ├── __init__.py
│   │   ├── prompts/            # Prompt templates per task type
│   │   │   ├── model_prompt.py
│   │   │   ├── view_prompt.py
│   │   │   ├── security_prompt.py
│   │   │   └── ...
│   │   ├── patterns/           # Odoo 17.0 code patterns/examples
│   │   │   ├── model_patterns.py
│   │   │   ├── view_patterns.py
│   │   │   └── ...
│   │   └── validators/         # Odoo-specific validation rules
│   │       ├── manifest.py
│   │       ├── model_lint.py
│   │       └── ...
│   │
│   ├── validation/             # Docker-based validation
│   │   ├── __init__.py
│   │   ├── docker_manager.py   # Container lifecycle
│   │   ├── odoo_runner.py      # Module install and test execution
│   │   ├── pylint_checker.py   # pylint-odoo integration
│   │   └── quality_report.py   # Quality scoring and reporting
│   │
│   ├── output/                 # Output formatting and delivery
│   │   ├── __init__.py
│   │   ├── git_manager.py      # Git operations
│   │   └── report.py           # Generation report
│   │
│   └── config/                 # Configuration
│       ├── __init__.py
│       ├── settings.py         # Global settings, API keys, defaults
│       └── agent_profiles.py   # Agent capability profiles
│
├── templates/                  # Jinja2 templates for scaffolding
│   ├── manifest.py.j2
│   ├── model.py.j2
│   ├── view.xml.j2
│   ├── security.csv.j2
│   └── ...
│
├── skills/                     # AGENTS.md files for each AI agent
│   ├── claude/
│   │   └── AGENTS.md
│   ├── codex/
│   │   └── AGENTS.md
│   └── gemini/
│       └── AGENTS.md
│
├── docker/                     # Docker configurations
│   ├── Dockerfile.odoo17       # Odoo 17.0 validation image
│   └── docker-compose.yml      # Odoo + PostgreSQL stack
│
├── tests/                      # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── pyproject.toml              # Project metadata, dependencies
└── README.md
```

### Structure Rationale

- **src/cli/:** Isolated CLI layer makes it possible to swap the interface later (web UI, API) without touching business logic.
- **src/orchestrator/:** Central pipeline logic separated from agent specifics. The pipeline controller owns the flow; agents are interchangeable execution units.
- **src/agents/:** Adapter pattern for each AI CLI tool. Uniform interface means adding a new LLM is just a new adapter, not a pipeline change.
- **src/search/:** Search and retrieval is its own bounded context. The embedding index, GitHub client, and ranker can evolve independently.
- **src/generator/:** Separates scaffolding (file structure) from generation (file content). The `tasks/` subdirectory maps 1:1 to Odoo module file types.
- **src/skills/:** Odoo domain knowledge externalized from agent logic. Prompts and patterns are data, not code -- easy to iterate without touching the pipeline.
- **src/validation/:** Docker-based validation is isolated because it has different lifecycle concerns (containers, timeouts, cleanup).
- **templates/:** Jinja2 templates for scaffolding are separate from generation prompts. Scaffolding is deterministic; generation is LLM-driven.
- **skills/:** AGENTS.md files give each AI CLI tool Odoo-specific instructions when invoked.

## Architectural Patterns

### Pattern 1: Sequential Pipeline with Checkpoint Gates

**What:** The core generation flow follows a sequential pipeline where each stage produces artifacts consumed by the next stage. Human checkpoints gate transitions between stages.

**When to use:** This is the primary orchestration pattern for the entire system. Every module generation follows this pipeline.

**Trade-offs:** Sequential means slower than full parallelism, but the dependencies between stages (models must exist before views reference them) make this the correct choice. Checkpoints add latency but catch errors before they compound.

**Confidence:** HIGH -- Microsoft Azure Architecture Center documents this as the standard pattern for multi-stage processes with clear linear dependencies. Multiple industry sources confirm.

```
User Input
    │
    ▼
[Requirement Gathering] ──── Interactive questioner fills gaps
    │
    ▼
[Semantic Search] ──── Search GitHub + OCA for similar modules
    │
    ▼
[Decision Gate] ──── Fork-and-extend vs. build-from-scratch
    │
    ├── FORK PATH                    ├── SCRATCH PATH
    │   Clone + analyze base         │   Scaffold from template
    │   Identify deltas              │
    ▼                                ▼
[Model Generation] ◄──── CHECKPOINT 1: Human reviews model design
    │
    ▼
[View Generation] ◄──── CHECKPOINT 2: Human reviews views
    │
    ▼
[Security Generation] ◄──── CHECKPOINT 3: Human reviews ACLs
    │
    ▼
[Logic + Wizard + Report Generation]
    │
    ▼
[Test Generation]
    │
    ▼
[Validation Pipeline] ◄──── CHECKPOINT 4: Human reviews final output
    │
    ├── pylint-odoo check
    ├── Docker install test
    └── Unit/integration test run
    │
    ▼
[Output] ──── Production-ready module + quality report
```

### Pattern 2: Adapter Pattern for Multi-LLM Support

**What:** Each AI CLI tool (Claude Code, Codex, Gemini) is wrapped in an adapter that implements a common interface. The orchestrator interacts only with the interface, never with CLI specifics.

**When to use:** Every agent invocation goes through an adapter. This is foundational.

**Trade-offs:** Slight abstraction overhead, but essential for: (a) swapping agents per task type, (b) fallback chains when one agent fails, (c) adding new agents without pipeline changes.

**Confidence:** HIGH -- the AI-Agents-Orchestrator project on GitHub demonstrates this exact pattern in production with Claude, Codex, Gemini, Copilot, and Ollama adapters behind a unified interface.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class AgentResult:
    content: str
    files_modified: tuple[str, ...]
    success: bool
    agent_name: str
    token_usage: int

class AgentAdapter(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        working_dir: str,
        context_files: tuple[str, ...] = (),
        skills: tuple[str, ...] = (),
    ) -> AgentResult:
        """Generate code via the underlying AI CLI tool."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the agent CLI is available and authenticated."""
        ...

class ClaudeAdapter(AgentAdapter):
    async def generate(self, prompt, working_dir, context_files=(), skills=()):
        # Invoke: claude --print --dangerously-skip-permissions
        # with AGENTS.md loaded as context
        ...

class CodexAdapter(AgentAdapter):
    async def generate(self, prompt, working_dir, context_files=(), skills=()):
        # Invoke: codex --quiet --auto-edit
        # with AGENTS.md loaded as context
        ...
```

### Pattern 3: Maker-Checker Loop for Code Quality

**What:** After each generation stage, the generated code passes through a checker agent (different from the generator) that evaluates quality. If the checker finds issues, it sends feedback to the maker for revision. This loops until acceptance criteria are met or iteration cap is reached.

**When to use:** For every code generation task where quality matters -- which is all of them, given the OCA quality standard.

**Trade-offs:** Doubles or triples LLM API calls per stage. Given unconstrained API budget, this is worthwhile. Cap iterations at 3 to prevent infinite loops.

**Confidence:** MEDIUM -- Microsoft documents this as a standard group chat sub-pattern. The specific application to Odoo code generation is novel but the pattern is well-established.

```
[Generator Agent] ── produces code ──▶ [Checker Agent]
       ▲                                    │
       │                                    │
       │         ◄── feedback ──────────────┘
       │              (if issues found)
       │
       └── revise and resubmit (max 3 iterations)
```

### Pattern 4: Two-Path Decision Router (Fork vs. Scratch)

**What:** After semantic search, a decision node evaluates search results and routes to one of two distinct paths: fork-and-extend (when a good match is found) or build-from-scratch (when no suitable match exists). Each path has different generation strategies.

**When to use:** At the search-to-generation boundary, every time.

**Trade-offs:** Two code paths to maintain, but the workflows are fundamentally different. Trying to unify them would create a confusing abstraction.

**Confidence:** MEDIUM -- the fork-and-extend pattern is established in open-source development. Combining it with AI-assisted adaptation is newer but follows logically.

```python
@dataclass(frozen=True)
class SearchResult:
    repo_url: str
    relevance_score: float  # 0.0 to 1.0
    module_name: str
    description: str

FORK_THRESHOLD = 0.7  # configurable

def route_generation(
    results: tuple[SearchResult, ...],
    threshold: float = FORK_THRESHOLD,
) -> str:
    if results and results[0].relevance_score >= threshold:
        return "fork_and_extend"
    return "build_from_scratch"
```

### Pattern 5: Persistent Pipeline State for Resumability

**What:** Every pipeline stage writes its state (inputs, outputs, decisions, artifacts) to a persistent store. If the pipeline fails or the user stops at a checkpoint, it can resume from the last completed stage.

**When to use:** Always. Module generation can take 30+ minutes. Losing progress to a crash is unacceptable.

**Trade-offs:** Adds I/O overhead for state persistence. Worth it for reliability.

**Confidence:** HIGH -- LangGraph's checkpointing, the PDCA framework for AI code generation, and standard pipeline design all emphasize persistent state as essential for long-running AI workflows.

```python
@dataclass(frozen=True)
class PipelineState:
    stage: str
    requirements: dict  # frozen via immutable pattern
    search_results: tuple[SearchResult, ...]
    generation_path: str  # "fork" or "scratch"
    generated_files: dict[str, str]  # path -> content
    checkpoint_approvals: dict[str, bool]  # stage -> approved
    validation_results: dict  # test results, lint results
    created_at: str
    updated_at: str

    def with_stage(self, new_stage: str) -> "PipelineState":
        """Immutable update -- returns new state with updated stage."""
        return PipelineState(
            stage=new_stage,
            requirements=self.requirements,
            search_results=self.search_results,
            # ... all other fields carried forward
            updated_at=datetime.utcnow().isoformat(),
        )
```

## Data Flow

### Primary Generation Flow

```
User describes module need (natural language)
    │
    ▼
Interactive Questioner (LLM) asks follow-ups
    │  Produces: structured requirements dict
    ▼
Semantic Search
    │  Input: requirements text
    │  Process: embed requirements -> query GitHub API -> query OCA repos
    │           -> re-rank by semantic similarity
    │  Output: ranked list of candidate modules
    ▼
Decision Router
    │  Input: ranked candidates + threshold
    │  Output: "fork_and_extend" or "build_from_scratch"
    │
    ├────────────────────────┐
    ▼                        ▼
Fork Handler             Scratch Handler
    │  Clone repo            │  Generate scaffold
    │  Analyze structure     │  from Jinja2 templates
    │  Identify deltas       │
    ▼                        ▼
    └────────┬───────────────┘
             │  Both paths produce: working directory with base files
             ▼
Agent Router selects agent per task
    │
    ▼
Sequential Generation Tasks (each is a maker-checker loop):
    │
    ├── 1. Models:     Agent generates Python ORM models
    │                  CHECKPOINT: Human reviews model design
    │
    ├── 2. Views:      Agent generates XML views referencing models
    │                  CHECKPOINT: Human reviews view layout
    │
    ├── 3. Security:   Agent generates ir.model.access.csv + record rules
    │                  CHECKPOINT: Human reviews access control
    │
    ├── 4. Logic:      Agent generates business logic, wizards, reports
    │
    ├── 5. Tests:      Agent generates unit + integration tests
    │
    └── 6. i18n:       Agent generates .pot file, translatable strings
             │
             ▼
Validation Pipeline:
    │
    ├── Static: pylint-odoo checks all Python files
    ├── Install: Docker Odoo 17.0 installs module (-i module_name)
    ├── Tests: Docker Odoo runs test suite (--test-enable)
    └── Quality: Score generated, report produced
             │
             ▼  CHECKPOINT: Human reviews final quality report
             │
             ▼
Output: production-ready Odoo module directory + quality report
```

### Agent Invocation Flow

```
Pipeline Controller
    │
    ▼
Agent Router (selects agent based on task type + config)
    │
    ▼
Agent Adapter (e.g., ClaudeAdapter)
    │  Prepares: prompt from skills/prompts/ + context files + AGENTS.md
    │  Invokes: CLI subprocess (e.g., `claude --print ...`)
    │  Captures: stdout, modified files, exit code
    │  Returns: AgentResult (immutable dataclass)
    │
    ▼
Checker Agent (different adapter, reviews output)
    │  If quality insufficient: returns feedback, loop back to generator
    │  If quality sufficient: returns approval
    │
    ▼
Pipeline Controller advances to next stage
```

### Search and Retrieval Flow

```
Requirements Text
    │
    ├── Embedding Model (sentence-transformers)
    │   Produces: 384/768-dim vector
    │
    ├── GitHub API Search
    │   Query: "odoo" + keywords from requirements
    │   Filter: language:Python, topic:odoo
    │   Returns: repos with metadata
    │
    ├── OCA API Search
    │   Query: scoped to github.com/OCA/* repos
    │   Returns: OCA modules with metadata
    │
    ▼
Candidate Pool (GitHub + OCA results merged)
    │
    ▼
Semantic Re-Ranker
    │  For each candidate:
    │    1. Fetch README + __manifest__.py description
    │    2. Generate embedding
    │    3. Cosine similarity vs. requirement embedding
    │  Sort by combined score (API relevance + semantic similarity)
    │
    ▼
Ranked Results (top N candidates with scores)
```

### Key Data Flows

1. **Requirements flow:** User natural language -> LLM-structured questionnaire -> validated requirements dict -> consumed by search, generation, and validation stages.
2. **Search results flow:** Requirements -> GitHub/OCA API queries -> raw results -> embedding-based re-ranking -> scored candidates -> fork/scratch decision.
3. **Generated code flow:** Prompt templates + context + agent invocation -> raw generated files -> checker review -> approved files -> accumulated in working directory.
4. **Validation flow:** Complete module directory -> pylint-odoo subprocess -> Docker container (install + tests) -> quality score -> report.
5. **State flow:** Each stage reads previous state, produces new immutable state, persists to disk. Checkpoints pause state flow until human approval.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-2 modules/week (target) | Single-machine, sequential pipeline. Docker containers spun up/down per validation. No caching needed beyond pip/npm caches in Docker layers. |
| 5-10 modules/week | Pre-warm Docker containers (keep one running). Cache embedding index for OCA repos (refresh weekly). Consider parallel agent invocation for independent tasks within a stage. |
| 20+ modules/week | Queue-based pipeline with persistent workers. Pre-computed embedding index for all OCA repos. Agent pool with load balancing across multiple API keys. This scale is unlikely for an internal team tool. |

### Scaling Priorities

1. **First bottleneck: Docker validation latency.** Odoo module install + test execution in Docker takes 30-120 seconds per run. Pre-warming containers and caching the Odoo database state after base module install eliminates cold-start overhead. Fix: Keep a warm container pool with base Odoo 17.0 pre-installed.
2. **Second bottleneck: LLM API latency for maker-checker loops.** Each generation task involves 2-6 LLM calls (generate + check, potentially with revisions). With 6-8 generation tasks per module, that is 12-48 API calls total. Fix: Parallelize independent tasks (e.g., i18n generation can run alongside test generation). Use faster models for checking (Haiku-class) and stronger models for generation (Opus/Sonnet-class).

## Anti-Patterns

### Anti-Pattern 1: Monolithic Single-Agent Generation

**What people do:** Send the entire module specification to one LLM call and expect a complete, correct Odoo module in one shot.
**Why it is wrong:** Context window limits, hallucination accumulation, no intermediate verification. A single LLM call cannot reliably produce 10-20 interconnected files with correct cross-references (model names in views, security rules referencing correct models, test imports matching actual module structure).
**Do this instead:** Decompose into per-file-type generation tasks with explicit context passing. Each task gets the minimal context it needs (e.g., view generation gets the model definitions as input, not the entire module spec).

### Anti-Pattern 2: Tight Coupling to Specific LLM CLI

**What people do:** Hardcode Claude Code CLI flags and output parsing throughout the pipeline, making it impossible to use Codex or Gemini without rewriting.
**Why it is wrong:** LLM tools change rapidly. Claude Code's CLI interface has changed multiple times. Locking in means painful migrations. Also prevents using the best agent for each task type.
**Do this instead:** Adapter pattern (Pattern 2 above). All agent interaction goes through a common interface. CLI-specific details are isolated in adapter implementations.

### Anti-Pattern 3: No State Persistence Between Stages

**What people do:** Keep pipeline state only in memory. If the process crashes or the user pauses at a checkpoint, all progress is lost.
**Why it is wrong:** Module generation takes 15-60 minutes. Losing progress destroys user trust and wastes API credits.
**Do this instead:** Persist state after every stage transition (Pattern 5). Use JSON files in the working directory for simplicity. Enable `odoo-gen resume` to pick up where it left off.

### Anti-Pattern 4: Skipping Validation Thinking "The LLM Got It Right"

**What people do:** Trust LLM-generated Odoo code without running it in an actual Odoo instance. Ship modules that "look correct" but fail on install.
**Why it is wrong:** Odoo has hundreds of undocumented conventions, XML schema requirements, and ORM quirks. LLMs hallucinate field names, use deprecated APIs, and generate views that reference non-existent fields. The only reliable check is actual installation.
**Do this instead:** Docker-based validation is non-negotiable. Every generated module must install and pass tests before being presented as output.

### Anti-Pattern 5: Embedding All Odoo Knowledge in Prompts

**What people do:** Write enormous system prompts containing every Odoo convention, trying to make the LLM "know" Odoo perfectly.
**Why it is wrong:** Exceeds effective context window. Dilutes attention. Updates require prompt surgery. Different tasks need different knowledge subsets.
**Do this instead:** Task-specific prompts (Pattern 1 decomposition). Each generation task gets a focused prompt with only the relevant Odoo patterns. Use AGENTS.md files to give agents project-level context, and task prompts for stage-level context.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| GitHub API | REST API via `httpx` or `PyGithub` | Rate limits: 5,000 requests/hour (authenticated). Use GraphQL API for batch queries. Search API has separate 30 requests/minute limit. |
| Claude Code CLI | Subprocess invocation | Requires `claude` CLI installed and authenticated. Use `--print` for non-interactive output. AGENTS.md provides Odoo skills. |
| Codex CLI | Subprocess invocation | Requires `codex` CLI installed and authenticated. Use `--quiet --auto-edit` for non-interactive output. AGENTS.md provides Odoo skills. |
| Gemini CLI | Subprocess invocation | Requires `gemini` CLI installed and authenticated. Use non-interactive flags. AGENTS.md provides Odoo skills. |
| Docker Engine | Docker SDK for Python (`docker` package) | Requires Docker daemon running. Use official `odoo:17.0` image as base. Mount generated module as volume. |
| PostgreSQL | Via Docker Compose (Odoo's DB) | No direct integration -- accessed only through Odoo within Docker. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI <-> Orchestrator | Direct Python function calls | Same process. CLI passes validated config to orchestrator. |
| Orchestrator <-> Agents | Async adapter interface | Orchestrator never calls CLI tools directly. Always through adapter. |
| Orchestrator <-> Search | Direct Python function calls | Search returns immutable result objects. Orchestrator decides routing. |
| Orchestrator <-> Validation | Async subprocess + Docker SDK | Validation runs in separate containers. Results returned as structured data. |
| Orchestrator <-> State | File I/O (JSON) | State is persisted after each stage. Read on resume. |
| Search <-> External APIs | HTTP (REST/GraphQL) | All network calls isolated in search layer. Retry logic here. |
| Agents <-> AI CLIs | Subprocess (stdin/stdout) | Adapter handles all subprocess management. Timeout handling critical. |

## Build Order Implications

The following build order respects component dependencies. Each phase produces a usable artifact that the next phase builds upon.

### Phase 1: Foundation (CLI + Scaffold + State)
Build first because everything depends on it:
- CLI skeleton with `typer`/`click`
- Module scaffolder (Jinja2 templates for Odoo 17.0 structure)
- Pipeline state management
- Configuration system

**Produces:** `odoo-gen scaffold` command that creates an empty but valid Odoo module.

### Phase 2: Validation Pipeline
Build second because it is the quality gate everything must pass through:
- Docker manager (container lifecycle)
- pylint-odoo integration
- Odoo install + test runner

**Produces:** `odoo-gen validate` command that checks any Odoo module.

### Phase 3: Single-Agent Generation
Build third because search is harder and less immediately valuable:
- One agent adapter (start with Claude Code, the strongest general coder)
- Odoo domain skills/prompts for each file type
- Sequential generation pipeline (models -> views -> security -> logic -> tests)
- Human checkpoint system

**Produces:** End-to-end module generation from requirements, using one AI agent, validated in Docker.

### Phase 4: Search and Retrieval
Build fourth because it enhances but does not block generation:
- GitHub search client
- OCA search client
- Embedding index for semantic similarity
- Decision router (fork vs. scratch)
- Fork-and-extend handler

**Produces:** Search-first workflow where existing modules are found and adapted.

### Phase 5: Multi-Agent + Maker-Checker
Build fifth because it requires a working pipeline to enhance:
- Additional agent adapters (Codex, Gemini)
- Agent routing logic (which agent for which task)
- Maker-checker loops
- Fallback chains

**Produces:** Multi-LLM generation with quality loops and automatic fallback.

### Build Order Rationale

1. **Foundation first** because CLI, state, and scaffolding are used by every other component.
2. **Validation second** because without validation, you cannot verify that generation works. Building validation early lets you test every subsequent feature against real Odoo 17.0.
3. **Single-agent generation third** because it delivers the core value proposition with minimal complexity. A single agent generating modules that pass validation is already useful.
4. **Search fourth** because it is an enhancement to generation, not a prerequisite. You can generate modules without search; search makes them better by starting from existing code.
5. **Multi-agent fifth** because orchestrating multiple LLMs adds significant complexity. The pipeline must be stable before adding this dimension. Also, the maker-checker pattern requires a working generation pipeline to enhance.

## Sources

- [Microsoft Azure Architecture Center: AI Agent Orchestration Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) -- HIGH confidence, authoritative (updated 2026-02-12)
- [AI-Agents-Orchestrator (GitHub)](https://github.com/hoangsonww/AI-Agents-Orchestrator) -- MEDIUM confidence, real-world multi-LLM orchestration implementation
- [Claude Code Bridge (GitHub)](https://github.com/bfly123/claude_code_bridge) -- LOW confidence, reference architecture for multi-AI collaboration
- [Claude Octopus (GitHub)](https://github.com/nyldn/claude-octopus) -- LOW confidence, multi-agent coordinator reference
- [Parallel Code (GitHub)](https://github.com/johannesjo/parallel-code) -- LOW confidence, worktree-based parallel agent execution reference
- [A Plan-Do-Check-Act Framework for AI Code Generation (InfoQ)](https://www.infoq.com/articles/PDCA-AI-code-generation/) -- MEDIUM confidence, checkpoint-based generation pattern
- [Human-in-the-Loop for AI Agents (Permit.io)](https://www.permit.io/blog/human-in-the-loop-for-ai-agents-best-practices-frameworks-use-cases-and-demo) -- MEDIUM confidence, checkpoint patterns
- [OCA maintainer-quality-tools (GitHub)](https://github.com/OCA/maintainer-quality-tools) -- HIGH confidence, official OCA quality tools
- [OCA pylint-odoo (GitHub)](https://github.com/OCA/pylint-odoo) -- HIGH confidence, official OCA linting plugin
- [odoo-tester Docker container (GitHub)](https://github.com/mcb30/odoo-tester) -- MEDIUM confidence, Docker-based Odoo testing
- [Official Odoo Docker image (Docker Hub)](https://hub.docker.com/_/odoo) -- HIGH confidence, official image
- [CrewAI GithubSearchTool (CrewAI Docs)](https://docs.crewai.com/en/tools/search-research/githubsearchtool) -- MEDIUM confidence, RAG-based GitHub search
- [Multi-Agent Frameworks Explained for Enterprise AI Systems 2026 (adopt.ai)](https://www.adopt.ai/blog/multi-agent-frameworks) -- MEDIUM confidence
- [Agentic Coding Trends Report 2026 (Anthropic)](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf?hsLang=en) -- HIGH confidence, authoritative industry report
- [AI Coding Agents in 2026: Coherence Through Orchestration (Mike Mason)](https://mikemason.ca/writing/ai-coding-agents-jan-2026/) -- MEDIUM confidence
- [Multi-Agent Multi-LLM Systems Guide 2026 (dasroot.net)](https://dasroot.net/posts/2026/02/multi-agent-multi-llm-systems-future-ai-architecture-guide-2026/) -- LOW confidence, single source
- [Semantic Code Search with ZeroEntropy](https://www.zeroentropy.dev/articles/semantic-code-search) -- MEDIUM confidence, semantic search architecture
- [FAISS-based semantic search library (GitHub)](https://github.com/kunci115/semantic-search) -- MEDIUM confidence, implementation reference

---
*Architecture research for: Agentic Odoo Module Development Workflow*
*Researched: 2026-03-01*
