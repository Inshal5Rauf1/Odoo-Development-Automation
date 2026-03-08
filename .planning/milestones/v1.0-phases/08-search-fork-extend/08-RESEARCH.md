# Phase 8: Search & Fork-Extend - Research

**Researched:** 2026-03-03
**Domain:** Semantic search over Odoo module repositories, vector indexing, fork-and-extend workflow
**Confidence:** MEDIUM-HIGH

## Summary

Phase 8 adds two new commands (`/odoo-gen:search` and `/odoo-gen:extend`) backed by a local ChromaDB vector index of OCA/GitHub module metadata. The index is built by crawling OCA organization repos via PyGithub, extracting `__manifest__.py` fields (name, summary, description, depends, category) plus README fragments, and embedding them with sentence-transformers `all-MiniLM-L6-v2`. Search queries encode user descriptions into the same vector space and retrieve the top-N matches via cosine similarity. Gap analysis is performed by the LLM agent comparing the user's structured spec against the matched module's manifest/README -- this is NOT a vector operation but a structured reasoning task that the AI coding assistant handles natively.

The fork-and-extend workflow uses git sparse checkout to clone individual module directories from OCA repos (since OCA repos contain 10-20+ modules each), then the existing `odoo-scaffold` agent analyzes the forked module structure and generates delta code using Odoo's `_inherit` pattern. The delta module depends on the forked module and adds only new fields, views, and security rules.

**Primary recommendation:** Use ChromaDB 1.5.x + sentence-transformers 5.2.x with CPU-only PyTorch (~185MB wheel instead of ~2GB GPU) via uv's explicit index pinning. Use PyGithub for OCA repo crawling (not gh CLI for bulk operations). Gap analysis and delta code generation are LLM tasks delegated to agents, not vector operations.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SRCH-01 | System semantically searches GitHub repositories for Odoo modules similar to user's description | ChromaDB + sentence-transformers vector search; PyGithub for live GitHub fallback |
| SRCH-02 | System semantically searches OCA repositories for similar modules | OCA org crawl via PyGithub `get_organization('OCA').get_repos()`; manifest extraction |
| SRCH-03 | System scores and ranks candidate modules by relevance to user's intent | ChromaDB cosine similarity distance returns ranked results with scores |
| SRCH-04 | System presents top matches with relevance scores, feature overlap, gap analysis | LLM agent compares spec JSON vs matched module manifest+README for gap analysis |
| SRCH-05 | User can select a match to fork-and-extend, or choose to build from scratch | search.md workflow presents results; user picks action |
| REFN-01 | User can adjust module specification based on what already exists | Existing spec workflow (Phase 4) re-entered with pre-populated data |
| REFN-02 | System highlights which parts of spec are covered vs need building | LLM-based structured comparison: spec fields vs manifest depends/data/models |
| REFN-03 | Adjusted spec replaces original for downstream generation | Spec JSON file overwrite; same contract as Phase 4 output |
| FORK-01 | System clones selected matching module into output directory | Git sparse checkout for OCA modules (multi-module repos); git clone for standalone repos |
| FORK-02 | System analyzes forked module structure (models, views, security, data) | Python AST + file tree analysis; manifest data file listing |
| FORK-03 | System generates delta code to extend forked module to match refined spec | LLM agent generates `_inherit` models, xpath view extensions, additional security rules |
| FORK-04 | System maintains local vector index of OCA/GitHub module descriptions | ChromaDB persistent storage at `~/.local/share/odoo-gen/chromadb/`; build-index CLI command |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| chromadb | 1.5.x | Local vector database | Persistent local storage, cosine similarity, built-in sentence-transformers integration. Default embedding function IS all-MiniLM-L6-v2. Active development (1.5.2 released Feb 2026). |
| sentence-transformers | 5.2.x | Text embedding generation | Hugging Face standard. all-MiniLM-L6-v2 (22MB model, 384-dim, 5x faster than larger models). ChromaDB's default -- zero extra config. |
| torch (CPU-only) | >=2.6 | ML runtime for sentence-transformers | Required by sentence-transformers. CPU-only wheel ~185MB vs ~2GB with CUDA. Install via PyTorch CPU index. |
| PyGithub | 2.8.x | GitHub API access | Typed Python interface. Pagination, rate limit handling, organization listing. Used for OCA crawl and live search fallback. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gitpython | 3.1.x | Git operations from Python | Sparse checkout, clone, branch checkout for fork workflow. Could also use subprocess git directly. |
| click | 8.x (existing) | CLI commands | Already in the project. New CLI commands: `build-index`, `search`, `index-status`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ChromaDB | FAISS | FAISS is faster at millions of vectors but has no persistence, no metadata filtering, harder API. ChromaDB sufficient at our scale (thousands of modules). |
| all-MiniLM-L6-v2 | voyage-code-3 | voyage-code-3 is better for code similarity, but our matching is against natural language descriptions/summaries, not source code. MiniLM is ideal for text similarity and is ChromaDB's default. |
| PyGithub | gh CLI | gh CLI has 10 req/min code search limit and is designed for interactive use, not bulk crawling. PyGithub uses REST API at 5000 req/hr authenticated. |
| PyGithub | requests + GitHub API | PyGithub handles pagination, rate limiting, typed responses. No reason to hand-roll. |
| gitpython | subprocess git | gitpython is cleaner for programmatic use. Either works. subprocess is simpler if only doing clone + sparse checkout. |
| Local ChromaDB | OpenAI embeddings API | Adds cost per query, network dependency, API key requirement. Local is free, fast, offline. |

**Installation (uv pyproject.toml additions):**

```toml
# In [project] dependencies, add:
[project.optional-dependencies]
search = [
    "chromadb>=1.5",
    "sentence-transformers>=5.2",
    "torch>=2.6",
    "PyGithub>=2.8",
    "gitpython>=3.1",
]

# CPU-only PyTorch configuration:
[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.uv.sources]
torch = [
    { index = "pytorch-cpu" },
]
```

**Install command:**
```bash
cd ~/.claude/odoo-gen/python
uv pip install -e ".[search]"
```

## Architecture Patterns

### Recommended Project Structure

New files for Phase 8 (added to existing `python/src/odoo_gen_utils/`):

```
python/src/odoo_gen_utils/
├── search/                    # NEW: Search & index package
│   ├── __init__.py            # Public API: search_modules, build_index
│   ├── index_builder.py       # OCA crawl + ChromaDB index population
│   ├── searcher.py            # Query encoding + ChromaDB search + result ranking
│   ├── manifest_parser.py     # Parse __manifest__.py safely (ast.literal_eval)
│   ├── github_client.py       # PyGithub wrapper: OCA org crawl, rate limit handling
│   └── types.py               # SearchResult, IndexEntry, GapAnalysis dataclasses
├── fork/                      # NEW: Fork & extend package
│   ├── __init__.py            # Public API: clone_module, analyze_module
│   ├── cloner.py              # Git sparse checkout / clone operations
│   └── analyzer.py            # Module structure analysis (models, views, security)
python/tests/
├── test_index_builder.py      # Index building tests
├── test_searcher.py           # Search query tests
├── test_manifest_parser.py    # Manifest parsing tests
├── test_github_client.py      # GitHub API mock tests
├── test_cloner.py             # Clone/sparse checkout tests
├── test_analyzer.py           # Module analysis tests
```

New GSD extension files:

```
agents/
├── odoo-search.md             # NEW: Search agent system prompt
├── odoo-extend.md             # NEW: Fork-and-extend agent system prompt
commands/
├── search.md                  # UPDATED: Activate search workflow
├── extend.md                  # UPDATED: Activate extend workflow
├── index.md                   # UPDATED: Activate index build
workflows/
├── search.md                  # NEW: Search workflow steps
├── extend.md                  # NEW: Fork-and-extend workflow steps
```

### Pattern 1: Index Build Pipeline

**What:** Crawl OCA repos, extract manifest data, embed and store in ChromaDB
**When to use:** Initial index build and periodic refresh

```python
# Source: ChromaDB docs + PyGithub docs
import ast
import chromadb
from github import Github

def build_oca_index(github_token: str, db_path: str) -> int:
    """Build ChromaDB index from OCA organization repos."""
    g = Github(github_token)
    org = g.get_organization("OCA")

    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(
        name="odoo_modules",
        metadata={"hnsw:space": "cosine"},
    )

    count = 0
    for repo in org.get_repos():
        # Only index repos with a 17.0 branch
        try:
            branch = repo.get_branch("17.0")
        except Exception:
            continue

        # List module directories (those containing __manifest__.py)
        contents = repo.get_contents("", ref="17.0")
        for item in contents:
            if item.type != "dir":
                continue
            try:
                manifest_file = repo.get_contents(
                    f"{item.path}/__manifest__.py", ref="17.0"
                )
            except Exception:
                continue

            manifest = _parse_manifest(manifest_file.decoded_content.decode())
            if not manifest or not manifest.get("installable", True):
                continue

            # Build searchable text from manifest fields
            doc_text = _build_document_text(manifest, item.name)

            collection.upsert(
                ids=[f"oca/{repo.name}/{item.name}"],
                documents=[doc_text],
                metadatas=[{
                    "repo": repo.name,
                    "module": item.name,
                    "org": "OCA",
                    "category": manifest.get("category", ""),
                    "depends": ",".join(manifest.get("depends", [])),
                    "version": manifest.get("version", ""),
                    "license": manifest.get("license", ""),
                    "summary": manifest.get("summary", ""),
                    "url": f"https://github.com/OCA/{repo.name}/tree/17.0/{item.name}",
                }],
            )
            count += 1

    return count


def _parse_manifest(content: str) -> dict | None:
    """Safely parse __manifest__.py using ast.literal_eval."""
    try:
        return ast.literal_eval(content)
    except (ValueError, SyntaxError):
        return None


def _build_document_text(manifest: dict, module_name: str) -> str:
    """Build searchable text from manifest fields."""
    parts = [
        manifest.get("name", module_name),
        manifest.get("summary", ""),
        manifest.get("description", ""),
        f"Category: {manifest.get('category', 'Uncategorized')}",
        f"Depends on: {', '.join(manifest.get('depends', []))}",
    ]
    return " | ".join(p for p in parts if p)
```

### Pattern 2: Semantic Search Query Flow

**What:** Encode user query, search ChromaDB, return ranked results with metadata
**When to use:** Every `/odoo-gen:search` invocation

```python
# Source: ChromaDB docs
import chromadb
from dataclasses import dataclass

@dataclass(frozen=True)
class SearchResult:
    module_id: str
    module_name: str
    repo_name: str
    org: str
    summary: str
    category: str
    depends: tuple[str, ...]
    url: str
    relevance_score: float  # 0.0 to 1.0 (cosine similarity)
    document_text: str


def search_modules(
    query: str,
    db_path: str,
    n_results: int = 10,
) -> tuple[SearchResult, ...]:
    """Search ChromaDB index for modules matching query."""
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection(name="odoo_modules")

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    search_results = []
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity: 1 - (distance / 2)
        similarity = 1.0 - (distance / 2.0)

        search_results.append(SearchResult(
            module_id=doc_id,
            module_name=meta.get("module", ""),
            repo_name=meta.get("repo", ""),
            org=meta.get("org", ""),
            summary=meta.get("summary", ""),
            category=meta.get("category", ""),
            depends=tuple(meta.get("depends", "").split(",")),
            url=meta.get("url", ""),
            relevance_score=round(similarity, 4),
            document_text=results["documents"][0][i],
        ))

    return tuple(sorted(search_results, key=lambda r: r.relevance_score, reverse=True))
```

### Pattern 3: Git Sparse Checkout for OCA Modules

**What:** Clone only a single module directory from a multi-module OCA repo
**When to use:** FORK-01 when user selects an OCA module to fork

```python
# Source: git sparse-checkout docs (Git 2.25+)
import subprocess
from pathlib import Path

def clone_oca_module(
    repo_name: str,
    module_name: str,
    output_dir: Path,
    branch: str = "17.0",
) -> Path:
    """Clone a single OCA module using git sparse checkout.

    OCA repos contain 10-20+ modules each. Sparse checkout
    downloads only the target module directory.
    """
    repo_url = f"https://github.com/OCA/{repo_name}.git"
    clone_dir = output_dir / module_name

    # Step 1: Clone with no checkout and blob filter
    subprocess.run(
        ["git", "clone", "--no-checkout", "--filter=blob:none",
         "--sparse", "-b", branch, repo_url, str(clone_dir)],
        check=True, capture_output=True,
    )

    # Step 2: Set sparse checkout to target module only
    subprocess.run(
        ["git", "-C", str(clone_dir), "sparse-checkout", "set", module_name],
        check=True, capture_output=True,
    )

    # Step 3: Checkout the branch
    subprocess.run(
        ["git", "-C", str(clone_dir), "checkout", branch],
        check=True, capture_output=True,
    )

    return clone_dir / module_name
```

### Pattern 4: Gap Analysis (LLM-Based, Not Vector)

**What:** Compare user's spec against a matched module's capabilities
**When to use:** SRCH-04, REFN-02 after search results are retrieved

Gap analysis is a structured reasoning task, NOT a vector similarity task. The approach:

1. Extract structured data from the matched module: parse `__manifest__.py` for depends/data files, scan `models/` for field names/types, scan `views/` for view types, scan `security/` for groups
2. Present this structured extraction alongside the user's spec JSON to the LLM agent
3. Agent produces a structured gap analysis:

```
Covered by existing module:
  - Model: hr.employee (fields: name, department_id, job_id)
  - Views: form, list, search for hr.employee
  - Security: User/Manager groups

Gaps (need to build):
  - Model: hr.employee needs additional fields (skill_level, certification_date)
  - View: hr.employee form needs skill tab
  - New model: hr.skill (not in original module)
  - Security: record rules for multi-company
```

This is delegated to the `odoo-extend` agent, which receives:
- The user's spec JSON (from Phase 4)
- The module analysis output (from FORK-02)
- Knowledge base context (from Phase 2)

### Pattern 5: Delta Code Generation (Inheritance-Based)

**What:** Generate an extension module that `_inherit`s the forked module's models
**When to use:** FORK-03 when generating code to extend a forked module

For Odoo, "delta code" means a **new companion module** that:
- Has `depends` including the forked module
- Uses `_inherit` to add fields to existing models
- Uses `xpath` view inheritance to extend existing views
- Adds new `ir.model.access.csv` rows for new models only
- Adds new security groups/record rules only for new functionality

This is NOT modifying the forked module's files. It is generating a separate module.

```python
# Example: extension module manifest
{
    "name": "HR Employee Skills Extension",
    "version": "17.0.1.0.0",
    "depends": ["hr_employee_firstname"],  # the forked module
    "data": [
        "security/ir.model.access.csv",
        "views/hr_employee_views.xml",     # xpath extensions
        "views/hr_skill_views.xml",        # new model views
    ],
}
```

```python
# Example: model inheritance
from odoo import fields, models

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    skill_level = fields.Selection(
        selection=[("junior", "Junior"), ("senior", "Senior")],
        string="Skill Level",
    )
    certification_date = fields.Date(string="Certification Date")
```

```xml
<!-- Example: xpath view inheritance -->
<record id="view_employee_form_inherit_skills" model="ir.ui.view">
    <field name="name">hr.employee.form.skills</field>
    <field name="model">hr.employee</field>
    <field name="inherit_id" ref="hr.view_employee_form"/>
    <field name="arch" type="xml">
        <xpath expr="//page[@name='public']" position="after">
            <page name="skills" string="Skills">
                <group>
                    <field name="skill_level"/>
                    <field name="certification_date"/>
                </group>
            </page>
        </xpath>
    </field>
</record>
```

### Anti-Patterns to Avoid

- **Modifying forked module files directly:** NEVER edit the original module. Always create a companion extension module with `_inherit`. This preserves upstream updateability.
- **Using vector similarity for gap analysis:** Cosine similarity tells you "this module is 72% similar" but cannot tell you WHICH specific fields/views are missing. Gap analysis requires structured comparison.
- **Cloning entire OCA repos:** OCA repos contain 10-20+ modules and can be large. Use sparse checkout to get only the target module.
- **Real-time GitHub API search as primary:** 10 req/min code search limit makes this impractical for interactive use. Use local ChromaDB index as primary, GitHub API as fallback/discovery.
- **Building a web scraper for OCA:** PyGithub + the GitHub API is the correct tool. Do not scrape GitHub HTML.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector similarity search | Custom HNSW/ANN implementation | ChromaDB | ChromaDB handles indexing, persistence, HNSW graph, distance computation, metadata filtering |
| Text embeddings | Custom word2vec or TF-IDF | sentence-transformers + all-MiniLM-L6-v2 | Pre-trained on 1B sentence pairs, 384-dim, ChromaDB default, zero config |
| GitHub API pagination | Manual page counting + URL parsing | PyGithub PaginatedList | Handles pagination, rate limits, typed responses automatically |
| Rate limit backoff | Custom retry loops | PyGithub's built-in rate limit handling | Catches RateLimitExceededException, provides reset timestamps |
| Git operations | subprocess chains for clone+sparse | subprocess (but use the sparse checkout pattern) | Git sparse checkout is the correct tool; no library needed beyond subprocess |
| Manifest parsing | Regex or exec() on __manifest__.py | ast.literal_eval() | Safe evaluation of Python dict literal. Never exec() untrusted code. |
| Gap analysis | Vector distance as gap metric | LLM agent structured reasoning | Gap analysis requires understanding WHAT is missing, not HOW SIMILAR the texts are |
| Delta code generation | AST diff tools | LLM agent with Odoo inheritance knowledge | Odoo's `_inherit` + xpath pattern is domain-specific; LLM with knowledge base handles it |

**Key insight:** The search index and similarity scoring are mechanical (ChromaDB). The gap analysis and code generation are reasoning tasks (LLM agents). Do not try to make vector operations do reasoning, or reasoning do vector operations.

## Common Pitfalls

### Pitfall 1: PyTorch GPU Dependencies Bloating Install
**What goes wrong:** Default `pip install sentence-transformers` pulls ~2GB PyTorch with CUDA support
**Why it happens:** PyPI's default torch wheel includes GPU support
**How to avoid:** Install torch from CPU-only index FIRST, then sentence-transformers. In uv, use explicit index pinning to `https://download.pytorch.org/whl/cpu`. CPU-only torch wheel is ~185MB.
**Warning signs:** Install takes >5 minutes or uses >2GB disk space

### Pitfall 2: GitHub API Rate Limits During Index Build
**What goes wrong:** Building index from 200+ OCA repos with 1000+ modules hits the 5000 req/hr limit
**Why it happens:** Each repo requires: 1 branch check + 1 contents listing + N manifest fetches. For 200 repos with avg 10 modules = 2200+ API calls minimum.
**How to avoid:** (1) Authenticate with a personal access token (5000/hr vs 60/hr unauthenticated). (2) Cache intermediate results. (3) Use conditional requests (ETag/If-Modified-Since). (4) Build index incrementally -- skip repos already indexed.
**Warning signs:** 403 responses, `RateLimitExceededException` from PyGithub

### Pitfall 3: gh CLI Not Authenticated
**What goes wrong:** All GitHub API operations fail with auth errors
**Why it happens:** gh CLI requires `gh auth login` before any authenticated operation. This is a known blocker from STATE.md.
**How to avoid:** (1) Detect auth status at startup via `gh auth status`. (2) Provide clear error message with `gh auth login` instructions. (3) PyGithub can use a PAT directly via `Github(token)` -- does not require gh CLI auth. Use PyGithub for programmatic access, gh CLI only for user-interactive operations.
**Warning signs:** `You are not logged into any GitHub hosts` from gh CLI

### Pitfall 4: Stale Index with No Update Strategy
**What goes wrong:** Index becomes outdated as OCA repos get updated; new modules not found
**Why it happens:** No automatic refresh mechanism
**How to avoid:** (1) Store index build timestamp. (2) `odoo-gen-utils build-index --update` checks Last-Modified headers and only re-indexes changed repos. (3) CLI shows index age: "Index built 14 days ago (1247 modules)". (4) Default index lifetime: 30 days before suggesting refresh.
**Warning signs:** User searches for a module that exists on GitHub but is not found

### Pitfall 5: Model Download on First Run
**What goes wrong:** First search query takes 30+ seconds as sentence-transformers downloads the 22MB model
**Why it happens:** Model is downloaded lazily on first use
**How to avoid:** (1) Download model during `build-index` command (first use is always index build). (2) Show progress message: "Downloading embedding model (22MB, one-time)...". (3) Cache model in `~/.cache/torch/sentence_transformers/` (default location).
**Warning signs:** First search hangs with no output

### Pitfall 6: OCA Multi-Module Repo Structure
**What goes wrong:** Treating OCA repos as single-module repos (they contain 10-20+ modules each)
**Why it happens:** Common GitHub repos are 1 repo = 1 project. OCA repos are 1 repo = 1 domain (hr, account, stock) with many modules inside.
**How to avoid:** Always iterate directories within each repo, check for `__manifest__.py` in each subdirectory. Index at module level, not repo level.
**Warning signs:** Search returns repo names instead of module names

### Pitfall 7: Unsafe Manifest Parsing
**What goes wrong:** Using `eval()` or `exec()` on untrusted `__manifest__.py` content
**Why it happens:** `__manifest__.py` is a Python file, tempting to `eval()` it
**How to avoid:** ALWAYS use `ast.literal_eval()`. It only evaluates Python literals (dicts, lists, strings, numbers, booleans, None). Raises ValueError on anything else. NEVER use `eval()` or `exec()` on code from GitHub.
**Warning signs:** Security warnings, arbitrary code execution risk

### Pitfall 8: Fork >40% Modification Threshold
**What goes wrong:** User forks a module but needs to change so much that extension becomes harder than building from scratch
**Why it happens:** Odoo inheritance (`_inherit` + xpath) adds complexity; when most of the module needs changing, the extension module is more complex than a standalone one
**How to avoid:** (1) Surface this in gap analysis: "This module covers 35% of your spec. Recommendation: build from scratch." (2) Use 40% coverage threshold as guidance -- below 40%, building from scratch is typically easier. (3) Let user decide -- present both options with tradeoff explanation.
**Warning signs:** Gap analysis shows >60% of spec fields are gaps

## Code Examples

### CLI Command: build-index

```python
# Addition to cli.py
@main.command("build-index")
@click.option("--token", envvar="GITHUB_TOKEN", help="GitHub personal access token")
@click.option("--db-path", default=None, help="ChromaDB storage path")
@click.option("--update", is_flag=True, help="Only update changed repos")
def build_index(token: str | None, db_path: str | None, update: bool) -> None:
    """Build or update the local ChromaDB index of OCA modules."""
    if not token:
        click.echo("Error: GitHub token required. Set GITHUB_TOKEN or use --token.", err=True)
        click.echo("Generate a token at: https://github.com/settings/tokens", err=True)
        sys.exit(1)

    resolved_path = db_path or str(
        Path.home() / ".local" / "share" / "odoo-gen" / "chromadb"
    )

    click.echo(f"Building index at: {resolved_path}")
    count = build_oca_index(token, resolved_path, incremental=update)
    click.echo(f"Indexed {count} modules from OCA")
```

### CLI Command: search

```python
@main.command("search")
@click.argument("query")
@click.option("--limit", default=10, help="Number of results")
@click.option("--db-path", default=None, help="ChromaDB storage path")
@click.option("--json", "json_output", is_flag=True, help="Output JSON")
def search(query: str, limit: int, db_path: str | None, json_output: bool) -> None:
    """Search the local index for Odoo modules matching a description."""
    resolved_path = db_path or str(
        Path.home() / ".local" / "share" / "odoo-gen" / "chromadb"
    )

    results = search_modules(query, resolved_path, n_results=limit)

    if json_output:
        click.echo(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for i, r in enumerate(results, 1):
            score_pct = f"{r.relevance_score * 100:.1f}%"
            click.echo(f"{i}. [{score_pct}] {r.module_name} ({r.org}/{r.repo_name})")
            click.echo(f"   {r.summary}")
            click.echo(f"   {r.url}")
            click.echo()
```

### Manifest Parsing (Safe)

```python
# Source: Python ast module docs
import ast

def parse_manifest_safe(content: str) -> dict | None:
    """Parse __manifest__.py content safely using ast.literal_eval.

    NEVER use eval() or exec() on untrusted code from GitHub.
    ast.literal_eval only evaluates Python literals.
    """
    try:
        result = ast.literal_eval(content)
        if not isinstance(result, dict):
            return None
        return result
    except (ValueError, SyntaxError):
        return None
```

### ChromaDB Collection Setup

```python
# Source: ChromaDB official docs (docs.trychroma.com)
import chromadb

def get_or_create_module_collection(db_path: str) -> chromadb.Collection:
    """Get or create the Odoo modules collection.

    Uses ChromaDB's default embedding function (all-MiniLM-L6-v2)
    with cosine similarity for text matching.
    """
    client = chromadb.PersistentClient(path=db_path)
    return client.get_or_create_collection(
        name="odoo_modules",
        metadata={"hnsw:space": "cosine"},
    )
```

### Module Structure Analysis

```python
# For FORK-02: analyzing a cloned module's structure
import ast
from pathlib import Path
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ModuleAnalysis:
    module_name: str
    manifest: dict
    model_names: tuple[str, ...]
    model_fields: dict  # {model_name: [field_name, ...]}
    view_types: dict    # {model_name: [form, list, search, ...]}
    security_groups: tuple[str, ...]
    data_files: tuple[str, ...]
    has_wizards: bool
    has_tests: bool


def analyze_module(module_path: Path) -> ModuleAnalysis:
    """Analyze an Odoo module's structure for gap analysis."""
    manifest = parse_manifest_safe(
        (module_path / "__manifest__.py").read_text()
    )

    # Scan models/ for _name definitions
    model_names = []
    model_fields = {}
    models_dir = module_path / "models"
    if models_dir.is_dir():
        for py_file in models_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "_name":
                            if isinstance(node.value, ast.Constant):
                                model_names.append(node.value.value)

    # ... similar scanning for views, security, etc.

    return ModuleAnalysis(
        module_name=module_path.name,
        manifest=manifest or {},
        model_names=tuple(model_names),
        model_fields=model_fields,
        view_types={},
        security_groups=(),
        data_files=tuple(manifest.get("data", [])) if manifest else (),
        has_wizards=(module_path / "wizards").is_dir(),
        has_tests=(module_path / "tests").is_dir(),
    )
```

## Odoo-Specific Patterns

### OCA Repository Organization

OCA uses a domain-based repository structure where each repo covers one functional area:

| Repo Pattern | Example | Typical Module Count |
|--------------|---------|---------------------|
| `hr` | HR modules (employee, contract, leave) | 20+ |
| `account-*` | Accounting modules | 15+ |
| `stock-logistics-*` | Warehouse/logistics | 10+ |
| `web` | Web/frontend modules | 15+ |
| `server-tools` | Admin/technical tools | 20+ |
| `l10n-*` | Localization (country-specific) | Varies |

OCA has 200+ repositories. Most have a `17.0` branch. Each repo contains multiple independent Odoo modules (each with its own `__manifest__.py`).

### __manifest__.py Fields Useful for Indexing

| Field | Type | Index Use |
|-------|------|-----------|
| `name` | str | Primary searchable text (human-readable module name) |
| `summary` | str | Brief description -- high semantic value for matching |
| `description` | str | Extended description -- additional search context |
| `category` | str | Faceted filtering (e.g., "Human Resources", "Accounting") |
| `depends` | list[str] | Dependency graph -- shows what Odoo domains are involved |
| `version` | str | Filter by Odoo version prefix (17.0.x.y.z) |
| `license` | str | Filter (most OCA is AGPL-3 or LGPL-3) |
| `installable` | bool | MUST be True to include in index |
| `application` | bool | Flag for top-level apps vs utility modules |
| `author` | str | Metadata -- "Odoo Community Association (OCA)" for OCA modules |
| `website` | str | URL back to GitHub repo |
| `development_status` | str | OCA-specific: Alpha/Beta/Production/Stable/Mature |

### Standard OCA Module Layout

```
module_name/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── model_name.py
├── views/
│   └── model_name_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── model_name_security.xml
├── data/
│   └── data.xml
├── wizards/                    # Optional
│   ├── __init__.py
│   └── wizard_name.py
├── tests/
│   ├── __init__.py
│   └── test_model_name.py
├── static/                     # Optional
│   └── description/
│       └── icon.png
├── i18n/
│   └── module_name.pot
└── readme/                     # OCA-specific fragments
    ├── DESCRIPTION.rst
    ├── USAGE.rst
    ├── CONFIGURE.rst
    └── CONTRIBUTORS.rst
```

This is the SAME structure our generated modules already use (Phases 5-7), which means the analysis and delta generation code can reuse existing patterns.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GitHub code search API as primary search | Local vector index with GitHub as fallback | 2024-2025 (rate limit awareness) | 10 req/min code search makes real-time search impractical; local index is instant |
| TF-IDF / keyword matching | Sentence-transformer embeddings | 2022-2023 | Semantic matching ("leave management" finds "hr_holidays") |
| `eval()` on manifest files | `ast.literal_eval()` | Always (security best practice) | Safe parsing of Python literals without code execution risk |
| Full repo clone for single module | Git sparse checkout (`git clone --sparse --filter=blob:none`) | Git 2.25+ (2020) | Downloads only target module directory, not entire multi-module repo |
| ChromaDB with DuckDB backend | ChromaDB 1.x with Rust-core HNSW | 2025 | 4x performance improvement; `PersistentClient` API simplified |
| PyTorch default install (~2GB) | CPU-only index install (~185MB) | Always available, better documented 2024+ | Dramatically smaller install for CPU-only embedding inference |

**Deprecated/outdated:**
- ChromaDB `Settings(chroma_db_impl="duckdb+parquet")` -- replaced by `PersistentClient(path=...)` in ChromaDB 1.x
- `chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction` explicit import -- ChromaDB 1.x uses it as default automatically
- GitHub code search REST API v1 -- replaced by code search API v2 (same rate limits but better results)

## Open Questions

1. **Exact OCA repo count with 17.0 branches**
   - What we know: OCA has 200+ repos; most major repos have 17.0 branches
   - What's unclear: Exact count needed to estimate index build time and API calls
   - Recommendation: During index build, log the count. Estimate ~200 repos x ~10 modules avg = ~2000 modules for index sizing

2. **Index refresh strategy: full rebuild vs incremental**
   - What we know: PyGithub supports `repo.updated_at` for change detection; ChromaDB supports `upsert`
   - What's unclear: How much metadata changes between builds; whether Git commit SHAs or repo timestamps are better freshness signals
   - Recommendation: Use `repo.pushed_at` timestamp; skip repos not pushed since last build; upsert individual modules. Store build metadata in ChromaDB collection metadata.

3. **Non-OCA GitHub module search scope**
   - What we know: SRCH-01 says "GitHub repositories" (not just OCA). There are thousands of Odoo modules on GitHub outside OCA.
   - What's unclear: How to scope non-OCA search. Indexing all of GitHub is impractical.
   - Recommendation: Phase 1: OCA-only index (reliable, well-structured). Phase 2: Add `gh search repos` as live fallback for non-OCA with clear "unindexed result" labeling. This satisfies SRCH-01 without requiring a full GitHub index.

4. **README fragment inclusion in index**
   - What we know: OCA modules have `readme/DESCRIPTION.rst` fragments with rich descriptions
   - What's unclear: Whether manifest fields alone provide enough semantic signal, or if README adds meaningful search quality
   - Recommendation: Start with manifest fields only (name + summary + description + category + depends). If search quality is insufficient, add DESCRIPTION.rst in a follow-up. Each additional file fetch is an API call during indexing.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (existing in project) |
| Config file | `python/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd python && .venv/bin/python -m pytest tests/ -x -q` |
| Full suite command | `cd python && .venv/bin/python -m pytest tests/ -v --tb=short` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRCH-01 | Search GitHub repos for similar modules | integration | `pytest tests/test_searcher.py -x` | No -- Wave 0 |
| SRCH-02 | Search OCA repos for similar modules | integration | `pytest tests/test_searcher.py::test_oca_search -x` | No -- Wave 0 |
| SRCH-03 | Score and rank by relevance | unit | `pytest tests/test_searcher.py::test_ranking -x` | No -- Wave 0 |
| SRCH-04 | Present gap analysis | unit | `pytest tests/test_searcher.py::test_result_format -x` | No -- Wave 0 |
| SRCH-05 | User selects match or build-from-scratch | integration | Manual -- workflow interaction | N/A (agent workflow) |
| REFN-01 | Adjust spec based on matches | integration | Manual -- agent workflow | N/A (agent workflow) |
| REFN-02 | Highlight covered vs gaps | unit | `pytest tests/test_analyzer.py::test_gap_analysis -x` | No -- Wave 0 |
| REFN-03 | Adjusted spec replaces original | unit | `pytest tests/test_searcher.py::test_spec_update -x` | No -- Wave 0 |
| FORK-01 | Clone selected module | integration | `pytest tests/test_cloner.py::test_sparse_checkout -x` | No -- Wave 0 |
| FORK-02 | Analyze forked module structure | unit | `pytest tests/test_analyzer.py -x` | No -- Wave 0 |
| FORK-03 | Generate delta code | integration | Manual -- agent workflow (LLM generates _inherit code) | N/A (agent workflow) |
| FORK-04 | Maintain local vector index | unit | `pytest tests/test_index_builder.py -x` | No -- Wave 0 |

### Sampling Rate

- **Per task commit:** `cd python && .venv/bin/python -m pytest tests/ -x -q`
- **Per wave merge:** `cd python && .venv/bin/python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `python/tests/test_index_builder.py` -- covers FORK-04, SRCH-01/02 index building
- [ ] `python/tests/test_searcher.py` -- covers SRCH-01/02/03/04, REFN-03
- [ ] `python/tests/test_manifest_parser.py` -- covers safe manifest parsing
- [ ] `python/tests/test_github_client.py` -- covers PyGithub wrapper with mocked responses
- [ ] `python/tests/test_cloner.py` -- covers FORK-01 git sparse checkout
- [ ] `python/tests/test_analyzer.py` -- covers FORK-02, REFN-02 module analysis
- [ ] `sentence-transformers[cpu]` + `chromadb` added to `[project.optional-dependencies]` in pyproject.toml
- [ ] torch CPU-only index configured in `[tool.uv.index]`

## Sources

### Primary (HIGH confidence)
- [ChromaDB PyPI](https://pypi.org/project/chromadb/) - Version 1.5.2, Feb 2026
- [ChromaDB Docs - Embedding Functions](https://docs.trychroma.com/docs/embeddings/embedding-functions) - Default SentenceTransformer integration
- [ChromaDB Docs - Collections](https://docs.trychroma.com/docs/collections/configure) - HNSW config, distance functions
- [sentence-transformers PyPI](https://pypi.org/project/sentence-transformers/) - Version 5.2.3
- [Hugging Face all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) - Model specs: 22MB, 384-dim, 256 token limit
- [PyGithub Docs](https://pygithub.readthedocs.io/en/latest/) - Organization, Repository, PaginatedList
- [Odoo 17.0 Module Manifests](https://www.odoo.com/documentation/17.0/developer/reference/backend/module.html) - Official manifest field reference
- [OCA Manifest Template](https://github.com/OCA/maintainer-tools/blob/master/template/module/__manifest__.py) - OCA-specific fields
- [GitHub Rate Limits Docs](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) - 5000/hr authenticated, 10/min code search
- [uv PyTorch Integration](https://docs.astral.sh/uv/guides/integration/pytorch/) - CPU-only index configuration
- [Git Sparse Checkout Docs](https://git-scm.com/docs/git-sparse-checkout) - Cone mode, partial clone filter
- [Odoo 17.0 Inheritance Tutorial](https://www.odoo.com/documentation/17.0/developer/tutorials/server_framework_101/12_inheritance.html) - _inherit and xpath patterns

### Secondary (MEDIUM confidence)
- [OCA Readme Structure](https://odoo-community.org/readme-structure) - Fragment-based README generation
- [OCA HR Repo (17.0)](https://github.com/OCA/hr/tree/17.0) - Example: 22 modules in one repo (verified via WebFetch)
- [gh CLI search repos](https://cli.github.com/manual/gh_search_repos) - gh search command reference
- [gh CLI search code](https://cli.github.com/manual/gh_search_code) - Code search rate: 10 req/min

### Tertiary (LOW confidence)
- OCA total repo count estimate (~200+): based on GitHub org page, not counted programmatically. Needs validation during index build.
- 40% modification threshold for fork-vs-scratch: from project CLAUDE.md lessons learned, not empirically tested for this specific use case.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - ChromaDB, sentence-transformers, PyGithub all verified via PyPI with current versions
- Architecture: MEDIUM-HIGH - Index build pipeline is standard pattern; gap analysis approach (LLM-based) is sound but untested in this specific domain
- Pitfalls: HIGH - Rate limits, PyTorch size, OCA structure all verified from official docs and project experience
- Odoo patterns: HIGH - Inheritance, manifest fields, OCA layout verified from official Odoo 17.0 docs
- Fork workflow: MEDIUM - Sparse checkout is verified; delta-as-companion-module pattern is standard Odoo but LLM quality of generated xpath/inherit code is untested

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (30 days -- stable libraries, no fast-moving concerns)
