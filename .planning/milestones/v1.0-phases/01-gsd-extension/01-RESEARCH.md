# Phase 1: GSD Extension + Odoo Foundation - Research

**Researched:** 2026-03-01
**Domain:** Claude Code extension system, GSD extension patterns, Python package management (uv), Jinja2 template rendering, Odoo 17.0 module structure
**Confidence:** HIGH

## Summary

Phase 1 delivers odoo-gen as a GSD extension that follows the exact same installation and registration patterns GSD itself uses. The core insight from investigating the live GSD installation is that commands are `.md` files in `~/.claude/commands/<namespace>/`, agents are `.md` files in `~/.claude/agents/`, and the extension's core logic lives in `~/.claude/<extension-name>/`. There is no plugin API or registration protocol -- the "extension" pattern is simply placing files in the correct `~/.claude/` subdirectories.

The Python utility package (`odoo-gen-utils`) is a separate concern: a standard Python package installed via `uv pip install -e .` that provides a CLI entry point for Jinja2 template rendering. The agent `.md` files invoke it via Bash tool calls. This clean separation (agent definitions call Python utilities as subprocesses) means the two layers can be developed and tested independently.

For the scaffolding output, Odoo 17.0 modules follow a well-documented OCA directory structure. The Jinja2 templates must produce real, installable content -- not stubs. Key Odoo 17.0 specifics: `attrs` is deprecated (use inline `invisible`/`readonly` expressions), `<tree>` is still valid (renamed to `<list>` only in Odoo 18), version format is `17.0.x.y.z`, and `license` is a required manifest key per pylint-odoo.

**Primary recommendation:** Mirror GSD's installation pattern exactly -- `install.sh` copies command `.md` files to `~/.claude/commands/odoo-gen/`, agent `.md` files to `~/.claude/agents/`, and the extension core to `~/.claude/odoo-gen/`. The Python package installs into a venv managed by `uv`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Full OCA directory structure from the start: `models/`, `views/`, `security/`, `tests/`, `data/`, `demo/`, `i18n/`, `static/description/`, `wizard/` (if needed)
- Split model files: one Python file per model (e.g., `models/inventory_item.py`, `models/stock_move.py`) -- OCA convention
- Jinja2 templates produce real working content, not stubs -- module must install and run on Odoo 17.0 on first scaffold
- Include demo data (`demo/` with sample records) and `README.rst` (module description, usage, credits) from day one -- OCA requires both
- `/odoo-gen:new` accepts an inline argument: `/odoo-gen:new "inventory tracking with stock moves and warehouse locations"`
- System parses the description, infers module spec (name, models, fields), then shows the inferred spec for user confirmation before generating
- Phase-by-phase announcements during scaffolding: "Generating models... Generating views... Generating security... Done! Module at ./my_module/"
- Scaffolded module is created in the current working directory (`./module_name/`)
- Smart Odoo-specific follow-up questions come in Phase 4 (INPT-01..04) -- Phase 1 keeps input simple
- Single install script (`install.sh`): clone repo -> run script -> done
- install.sh checks for GSD at `~/.claude/odoo-gsd/` -- if missing, error with clear message and install URL (does not proceed)
- install.sh requires `uv` (fast Python package manager) -- if missing, error with install link
- install.sh creates a Python venv, installs the utility package via `uv pip install`
- Commands are registered by adding `/odoo-gen:*` skill entries to `~/.claude/commands/odoo-gen/` (same pattern GSD uses)
- GSD handles all orchestration (inherited) -- odoo-gen does not build its own orchestrator
- Each agent is a GSD agent definition (`.md` file with system prompt + tool access)
- `odoo-scaffold` is the single entry-point agent for Phase 1 -- it handles the full scaffold end-to-end
- Specialist agents (odoo-model-gen, odoo-view-gen, odoo-security-gen, odoo-test-gen, odoo-validator) are stubs in Phase 1, activated in Phases 5-6
- Naming convention: `odoo-` prefix for all agents (consistent with GSD naming)
- Agent files live in `~/.claude/odoo-gen/agents/` -- install.sh symlinks or copies them to `~/.claude/agents/`
- Agents call the Python utility package via Bash tool: `odoo-gen-utils render`, `odoo-gen-utils list-templates`, etc.
- Python CLI namespace: `odoo-gen-utils <subcommand>` -- clear, no conflicts

### Claude's Discretion
- Exact Jinja2 template structure and variable naming
- Python package internal architecture (modules, classes)
- install.sh implementation details (color output, progress)
- Agent .md prompt engineering and tool access definitions
- GSD config field defaults and validation logic

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXT-01 | odoo-gen extension installs into `~/.claude/` alongside GSD with a single clone + setup command | GSD installation pattern fully documented: commands in `~/.claude/commands/odoo-gen/`, agents in `~/.claude/agents/`, core in `~/.claude/odoo-gen/`. install.sh script copies files to correct locations. Python venv created via `uv`. |
| EXT-02 | Extension registers all odoo-gen commands with GSD command system | Commands are `.md` files with YAML frontmatter (`name`, `description`, `argument-hint`, optional `agent`, `allowed-tools`). Place in `~/.claude/commands/odoo-gen/` directory. Claude Code auto-discovers them as `/odoo-gen:*` slash commands. |
| EXT-03 | Extension adds Odoo-specific configuration fields (odoo_version, edition, output_dir, api_keys) to GSD config | GSD config is `.planning/config.json`. Extension can add an `odoo` section. Agents read config via `node gsd-tools.cjs state load` or direct file read. |
| EXT-04 | Extension provides Odoo-specific agent definitions that GSD can spawn | Agent `.md` files in `~/.claude/agents/` with frontmatter: `name`, `description`, `tools`, optional `color`. GSD spawns via `Task()` tool referencing the agent. Stub agents need description and minimal prompt. |
| EXT-05 | Extension includes Python utility package (installable via `uv`/`pip`) for template rendering, validation, and search | Python package with `pyproject.toml`, `[project.scripts]` entry point `odoo-gen-utils`, Jinja2 for template rendering. Install via `uv pip install -e .` in a dedicated venv. Phase 1 implements `render` and `list-templates` subcommands. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1.x | Template engine for Odoo module file rendering | Battle-tested, used by Ansible/Cookiecutter for identical scaffolding use cases. Template inheritance for base + customization. `FileSystemLoader` for modular templates. |
| uv | latest | Python package/project manager | 10-100x faster than pip. Creates venvs, installs packages, manages Python versions. Community consensus for new Python projects in 2026. |
| Python | 3.12.x | Runtime for utility package | Maximum Python version Odoo 17.0 supports. 3.13+ breaks Odoo validation. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Click | 8.x | CLI framework for odoo-gen-utils | Lightweight CLI with subcommands. Used directly (not via Typer) since this is a utility CLI, not a user-facing app. |
| tomli | stdlib (3.12) | Read pyproject.toml config | Built-in `tomllib` in Python 3.12. Parse project config if needed. |
| PyYAML | 6.x | Parse YAML frontmatter from agent .md files | Only if install.sh needs to read frontmatter. May not be needed. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Click (CLI) | argparse | argparse works but Click gives cleaner subcommand support with less boilerplate |
| Click (CLI) | Typer | Typer is overkill for a utility CLI with 3-5 subcommands. Click is lighter. |
| Jinja2 (templates) | string.Template | string.Template cannot handle loops, conditionals, or template inheritance. Jinja2 is required for generating real Odoo module content. |
| Jinja2 (templates) | Mako | Jinja2 is the de facto standard for Python scaffolding. Mako allows Python in templates (security risk, harder to maintain). |

**Installation:**
```bash
# In the odoo-gen-utils Python package directory
uv venv ~/.claude/odoo-gen/.venv --python 3.12
source ~/.claude/odoo-gen/.venv/bin/activate
uv pip install -e ~/.claude/odoo-gen/python/
```

## Architecture Patterns

### Recommended Extension Structure
```
~/.claude/odoo-gen/                    # Extension core (cloned repo)
├── install.sh                         # Setup script
├── commands/                          # Command .md files (copied to ~/.claude/commands/odoo-gen/)
│   ├── new.md                         # /odoo-gen:new
│   ├── validate.md                    # /odoo-gen:validate (stub)
│   ├── search.md                      # /odoo-gen:search (stub)
│   ├── research.md                    # /odoo-gen:research (stub)
│   ├── plan.md                        # /odoo-gen:plan (stub)
│   ├── phases.md                      # /odoo-gen:phases (stub)
│   ├── extend.md                      # /odoo-gen:extend (stub)
│   ├── history.md                     # /odoo-gen:history (stub)
│   ├── config.md                      # /odoo-gen:config (wrapper)
│   ├── status.md                      # /odoo-gen:status (wrapper)
│   ├── resume.md                      # /odoo-gen:resume (wrapper)
│   └── help.md                        # /odoo-gen:help
├── agents/                            # Agent .md files (copied to ~/.claude/agents/)
│   ├── odoo-scaffold.md               # Full scaffold agent (Phase 1 active)
│   ├── odoo-model-gen.md              # Model generation (stub)
│   ├── odoo-view-gen.md               # View generation (stub)
│   ├── odoo-security-gen.md           # Security generation (stub)
│   ├── odoo-test-gen.md               # Test generation (stub)
│   └── odoo-validator.md              # Validation agent (stub)
├── workflows/                         # Workflow logic referenced by commands
│   ├── scaffold.md                    # Full scaffold workflow
│   └── help.md                        # Help text content
├── python/                            # Python utility package
│   ├── pyproject.toml                 # Package metadata + entry points
│   ├── src/
│   │   └── odoo_gen_utils/
│   │       ├── __init__.py
│   │       ├── cli.py                 # Click CLI: render, list-templates
│   │       ├── renderer.py            # Jinja2 rendering engine
│   │       └── templates/             # Jinja2 templates
│   │           ├── manifest.py.j2
│   │           ├── model.py.j2
│   │           ├── init_root.py.j2
│   │           ├── init_models.py.j2
│   │           ├── init_tests.py.j2
│   │           ├── view_form.xml.j2
│   │           ├── view_tree.xml.j2
│   │           ├── view_search.xml.j2
│   │           ├── action.xml.j2
│   │           ├── menu.xml.j2
│   │           ├── security_group.xml.j2
│   │           ├── access_csv.j2
│   │           ├── test_model.py.j2
│   │           ├── demo_data.xml.j2
│   │           └── readme.rst.j2
│   └── tests/
│       ├── test_renderer.py
│       └── test_cli.py
└── VERSION                            # Extension version
```

### Pattern 1: GSD Command Entry Point
**What:** Each `/odoo-gen:*` command is a `.md` file with YAML frontmatter and process instructions.
**When to use:** Every command registration.
**Example:**
```markdown
---
name: odoo-gen:new
description: Scaffold a new Odoo module from a natural language description
argument-hint: "<description>"
agent: odoo-scaffold
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Task
---
<objective>
Scaffold a new Odoo 17.0 module from a natural language description.
The user provides a module description as $ARGUMENTS.
</objective>

<execution_context>
@~/.claude/odoo-gen/workflows/scaffold.md
</execution_context>

<process>
Execute the scaffold workflow end-to-end.
</process>
```
**Source:** Live GSD installation at `~/.claude/commands/gsd/plan-phase.md` (verified)

### Pattern 2: Agent Definition with Tool Access
**What:** Agent `.md` files define the system prompt, tools, and role for a spawnable agent.
**When to use:** Every agent (active or stub).
**Example:**
```markdown
---
name: odoo-scaffold
description: Scaffolds a complete Odoo 17.0 module from a natural language description. Parses intent, generates module spec, renders Jinja2 templates, produces installable module.
tools: Read, Write, Bash, Glob, Grep
color: green
---

<role>
You are an Odoo module scaffolding agent. [...]
</role>
```
**Source:** Live GSD agents at `~/.claude/agents/gsd-executor.md` (verified)

### Pattern 3: Python Utility as Subprocess
**What:** Agents call the Python utility package via Bash tool, not via import.
**When to use:** All template rendering and file generation.
**Example (agent calling utility):**
```bash
# Agent uses Bash tool to call:
~/.claude/odoo-gen/.venv/bin/odoo-gen-utils render \
  --template manifest.py.j2 \
  --output ./my_module/__manifest__.py \
  --var "module_name=my_module" \
  --var "version=17.0.1.0.0" \
  --var "depends=base"
```
**Source:** CONTEXT.md decision: "Agents call the Python utility package via Bash tool"

### Pattern 4: install.sh as File Copier
**What:** The install script copies files from the cloned repo to the correct `~/.claude/` locations.
**When to use:** One-time setup.
**Flow:**
1. Check GSD exists at `~/.claude/odoo-gsd/` -- error if missing
2. Check `uv` is available -- error if missing
3. Create Python venv at `~/.claude/odoo-gen/.venv/` using `uv venv`
4. Install Python package: `uv pip install -e ~/.claude/odoo-gen/python/`
5. Copy command `.md` files to `~/.claude/commands/odoo-gen/`
6. Copy agent `.md` files to `~/.claude/agents/`
7. Verify: check that `odoo-gen-utils --version` works
**Source:** CONTEXT.md decision + GSD file manifest pattern (verified)

### Anti-Patterns to Avoid
- **Building custom orchestration:** GSD provides this. Do not build pipeline controllers, state managers, or agent routers. The `/odoo-gen:new` command defines the workflow; GSD handles execution.
- **Modifying GSD files:** Never edit files in `~/.claude/odoo-gsd/`. odoo-gen is an extension, not a fork. Changes to GSD would be overwritten on `npx odoo-gsd-cc@latest`.
- **Importing Python package from agent .md files:** Agents run inside Claude Code's context. They cannot `import` Python. They must use Bash tool to call `odoo-gen-utils` as a subprocess.
- **Single monolithic template:** Do not create one giant template that outputs the entire module. Use one template per output file. This enables per-file regeneration and testing.
- **Hardcoding Odoo version in templates:** Use template variables (`{{ odoo_version }}`) so templates can be reused when Phase 9 adds Odoo 18 support.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Template rendering engine | Custom string formatting | Jinja2 `FileSystemLoader` + `Environment` | Template inheritance, loops, conditionals, filters, includes. Custom string formatting cannot handle multi-model modules. |
| CLI for Python utilities | argparse with manual subcommands | Click with `@click.group()` and `@click.command()` | Click handles help text, argument validation, error formatting. Saves ~100 lines of boilerplate. |
| Package management | pip + manual venv | uv | 10-100x faster, handles venv creation, respects `pyproject.toml` natively. |
| Odoo module directory structure | Manual `os.makedirs()` calls | Jinja2 template rendering + a manifest dict that defines which files to create | The file list should be data-driven (from the module spec), not hardcoded in Python. |
| Command registration | Custom plugin loader | `.md` files in `~/.claude/commands/odoo-gen/` | This is how Claude Code discovers slash commands. No code needed. |

**Key insight:** The extension pattern in Claude Code is file-based, not code-based. You "register" commands by placing `.md` files in the right directory. There is no registration API to call.

## Common Pitfalls

### Pitfall 1: Template Variable Mismatches Between Python and XML
**What goes wrong:** Jinja2 templates for Python files use `{{ model_name }}` but XML templates use a different variable name like `{{ model }}`, causing silent failures where XML views reference non-existent models.
**Why it happens:** Templates are authored independently without a shared schema.
**How to avoid:** Define a single `ModuleSpec` data class (or dict schema) that ALL templates consume. Every template variable must be documented in a schema file. Test template rendering with a fixed spec and verify cross-file references.
**Warning signs:** View XML references `model_my_thing` but Python model uses `_name = "my.thing"`. The dot-to-underscore conversion must be consistent.

### Pitfall 2: Odoo 17.0 Version-Specific Syntax Errors
**What goes wrong:** Templates generate `attrs={'invisible': [('state', '!=', 'draft')]}` (Odoo 16 syntax) instead of `invisible="state != 'draft'"` (Odoo 17 syntax). Module installs but views break.
**Why it happens:** Most Odoo examples online are for older versions. AI models default to the most common patterns from training data, which skew toward Odoo 12-16.
**How to avoid:** Templates MUST use Odoo 17.0 syntax exclusively. Specifically:
- `invisible="expression"` and `readonly="expression"` (NOT `attrs`)
- `<tree>` for list views (still valid in 17.0; `<list>` is Odoo 18+)
- `column_invisible` for hiding columns (new in 17.0)
- Version format: `17.0.x.y.z` (5-part)
- `license` is a required manifest key
**Warning signs:** `attrs` anywhere in generated XML. `<list>` tag in Odoo 17 templates.

### Pitfall 3: install.sh Fails Silently on Missing Prerequisites
**What goes wrong:** install.sh runs partially, creating some files but not others. User gets a broken installation with some commands working and others failing.
**Why it happens:** Shell scripts continue executing after errors by default. Missing `set -e` or missing prerequisite checks.
**How to avoid:** Start install.sh with `set -euo pipefail`. Check every prerequisite BEFORE any file operations: GSD exists, `uv` exists, `python3.12` exists, target directories are writable. Use a verification step at the end that checks all expected files exist.
**Warning signs:** User reports "some commands work, others don't" or "odoo-gen-utils: command not found".

### Pitfall 4: Python Package Venv Path Hardcoded
**What goes wrong:** Agent `.md` files reference `~/.claude/odoo-gen/.venv/bin/odoo-gen-utils` but the path expands differently on different systems (tilde expansion in subprocess vs shell).
**Why it happens:** `~` expands in shell but not in all subprocess invocations. macOS and Linux have different home directory paths.
**How to avoid:** In agent `.md` files, use `$HOME/.claude/odoo-gen/.venv/bin/odoo-gen-utils` or detect the path at runtime. Better: install.sh writes a small wrapper script at a known location that activates the venv and runs the command.
**Warning signs:** "command not found" errors when agents try to call odoo-gen-utils.

### Pitfall 5: ir.model.access.csv Model Reference Format
**What goes wrong:** Template generates `model_id:id` as `model_inventory_item` but the actual model `_name` is `inventory.item`, and Odoo expects the reference format `model_inventory_item` (dots replaced with underscores, prefixed with `model_`). Off-by-one in naming conventions causes "Access Denied" errors.
**Why it happens:** Odoo has a specific naming convention for external IDs of models: the model name with dots replaced by underscores, prefixed with `model_`. This conversion must be done consistently.
**How to avoid:** Template rendering must include a Jinja2 filter or function that converts model names: `inventory.item` -> `model_inventory_item`. Centralize this conversion in one place.
**Warning signs:** Module installs but every action shows "Access Denied".

### Pitfall 6: Demo Data References Non-Existent Records
**What goes wrong:** Demo data XML references `ref('base.partner_demo')` or other records that may or may not exist in the target database, causing install failures when demo data is enabled.
**Why it happens:** Demo data is often the last thing generated and the least tested.
**How to avoid:** Demo data should be self-contained: create its own partner records, its own users. Only reference records from the module's own `depends` list. Use `ref('module_name.xml_id')` format exclusively, never bare `ref('xml_id')`.
**Warning signs:** Module installs without demo data but fails with `--load-demo-data`.

## Code Examples

### Jinja2 Template Rendering Engine
```python
# Source: Jinja2 official docs + best practices for scaffolding tools
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined

def create_renderer(template_dir: Path) -> Environment:
    """Create a Jinja2 environment configured for Odoo module rendering."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,  # Fail on missing variables
        keep_trailing_newline=True,  # Preserve file endings
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # Custom filter: model name to external ID
    env.filters['model_ref'] = lambda name: f"model_{name.replace('.', '_')}"
    # Custom filter: model name to Python class
    env.filters['to_class'] = lambda name: ''.join(
        word.capitalize() for word in name.replace('.', '_').split('_')
    )
    return env

def render_template(
    env: Environment,
    template_name: str,
    output_path: Path,
    context: dict,
) -> Path:
    """Render a single template to a file. Returns the output path."""
    template = env.get_template(template_name)
    content = template.render(**context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    return output_path
```

### Odoo 17.0 `__manifest__.py` Template
```jinja2
{# manifest.py.j2 #}
{
    "name": "{{ module_title }}",
    "version": "{{ odoo_version }}.1.0.0",
    "author": "{{ author }}",
    "website": "{{ website }}",
    "license": "{{ license | default('LGPL-3') }}",
    "category": "{{ category | default('Uncategorized') }}",
    "summary": "{{ summary }}",
    "depends": [
{% for dep in depends %}
        "{{ dep }}",
{% endfor %}
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
{% for view_file in view_files %}
        "views/{{ view_file }}",
{% endfor %}
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "development_status": "Alpha",
    "application": {{ application | default('True') }},
}
```

### Odoo 17.0 Model Template
```jinja2
{# model.py.j2 #}
from odoo import api, fields, models
{% if has_constraints %}
from odoo.exceptions import ValidationError
{% endif %}


class {{ model_name | to_class }}(models.Model):
    _name = "{{ model_name }}"
    _description = "{{ model_description }}"
{% if inherit %}
    _inherit = ["{{ inherit }}"]
{% endif %}

{% for field in fields %}
    {{ field.name }} = fields.{{ field.type }}(
        string="{{ field.string }}",
{% if field.required %}
        required=True,
{% endif %}
{% if field.help %}
        help="{{ field.help }}",
{% endif %}
{% if field.type == 'Selection' %}
        selection=[
{% for key, label in field.selection %}
            ("{{ key }}", "{{ label }}"),
{% endfor %}
        ],
{% endif %}
{% if field.type in ('Many2one', 'One2many', 'Many2many') %}
        comodel_name="{{ field.comodel }}",
{% endif %}
{% if field.type == 'One2many' %}
        inverse_name="{{ field.inverse }}",
{% endif %}
    )
{% endfor %}
```

### ir.model.access.csv Template
```jinja2
{# access_csv.j2 #}
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
{% for model in models %}
access_{{ model.name | replace('.', '_') }}_user,{{ model.name }}.user,{{ model.name | model_ref }},{{ module_technical_name }}.group_{{ module_technical_name }}_user,1,1,1,0
access_{{ model.name | replace('.', '_') }}_manager,{{ model.name }}.manager,{{ model.name | model_ref }},{{ module_technical_name }}.group_{{ module_technical_name }}_manager,1,1,1,1
{% endfor %}
```

### Odoo 17.0 Test Template
```jinja2
{# test_model.py.j2 #}
from odoo.tests.common import TransactionCase


class Test{{ model_name | to_class }}(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.{{ model_name | replace('.', '_') }} = cls.env["{{ model_name }}"].create({
{% for field in required_fields %}
            "{{ field.name }}": {{ field.test_value }},
{% endfor %}
        })

    def test_create(self):
        """Test that a {{ model_description }} record can be created."""
        self.assertTrue(self.{{ model_name | replace('.', '_') }}.id)

    def test_read(self):
        """Test that {{ model_description }} fields are readable."""
        record = self.{{ model_name | replace('.', '_') }}
{% for field in required_fields %}
        self.assertIsNotNone(record.{{ field.name }})
{% endfor %}
```

### pyproject.toml for Python Utility Package
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "odoo-gen-utils"
version = "0.1.0"
description = "Python utilities for odoo-gen GSD extension"
requires-python = ">=3.12,<3.13"
dependencies = [
    "jinja2>=3.1",
    "click>=8.0",
]

[project.scripts]
odoo-gen-utils = "odoo_gen_utils.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/odoo_gen_utils"]

[tool.ruff]
target-version = "py312"
line-length = 120

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Click CLI Entry Point
```python
# Source: Click official docs
import click
import json
from pathlib import Path

@click.group()
@click.version_option(version="0.1.0")
def main():
    """odoo-gen-utils: Python utilities for the odoo-gen GSD extension."""
    pass

@main.command()
@click.option("--template", required=True, help="Template file name (e.g., manifest.py.j2)")
@click.option("--output", required=True, type=click.Path(), help="Output file path")
@click.option("--var", multiple=True, help="Variable in key=value format")
@click.option("--var-file", type=click.Path(exists=True), help="JSON file with template variables")
def render(template, output, var, var_file):
    """Render a Jinja2 template to a file."""
    context = {}
    if var_file:
        context = json.loads(Path(var_file).read_text())
    for v in var:
        key, value = v.split("=", 1)
        context[key] = value
    # ... render template with context ...

@main.command()
def list_templates():
    """List all available Jinja2 templates."""
    # ... list templates in templates/ directory ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pip install -e .` for dev packages | `uv pip install -e .` | 2024-2025 | 10-100x faster, handles venv creation too |
| `setup.py` / `setup.cfg` | `pyproject.toml` with build backend | 2023-2024 | Standard format, every tool supports it |
| `Flake8 + Black + isort` | `Ruff` | 2024-2025 | Single tool, 150x faster, single config |
| `attrs` in Odoo views | Inline `invisible`/`readonly` expressions | Odoo 17.0 (2023) | Simpler syntax, Python expressions in JS |
| `<tree>` for list views | `<tree>` still valid in 17.0, `<list>` in 18.0 | Odoo 18.0 (2024) | Do NOT use `<list>` for Odoo 17 templates |
| `.claude/commands/` only | Unified `.claude/commands/` + `.claude/skills/` | Claude Code 2025-2026 | Both work; commands are simpler for our use case |
| Custom plugin APIs | File-based command discovery | Claude Code 2025 | Place `.md` file in directory = command registered |
| Manual GSD extension | No official extension protocol | Current (Feb 2026) | Follow GSD's own file placement pattern |

**Deprecated/outdated:**
- `attrs` attribute in Odoo 17 XML views -- use inline `invisible`/`readonly`/`required` expressions
- `states` attribute in Odoo 17 XML views -- use `invisible="state != 'draft'"` instead
- `_columns` / `_defaults` in Python models -- ancient Odoo 8 patterns, LLMs hallucinate these
- `@api.one` / `@api.multi` decorators -- removed since Odoo 13
- `openerp` imports -- use `odoo` imports
- `<openerp>` XML tags -- use `<odoo>` tags
- `setup.py` / `setup.cfg` for Python packaging -- use `pyproject.toml`
- `description` key in `__manifest__.py` -- pylint-odoo flags as deprecated; use `README.rst` instead

## Open Questions

1. **Wrapper script vs direct venv path for odoo-gen-utils**
   - What we know: Agents call odoo-gen-utils via Bash tool. The binary lives in `~/.claude/odoo-gen/.venv/bin/odoo-gen-utils`.
   - What's unclear: Should install.sh create a wrapper script at a fixed location (e.g., `~/.claude/odoo-gen/bin/odoo-gen-utils`) that handles venv activation? Or should agents use the full venv path directly?
   - Recommendation: Create a thin wrapper script. It handles path resolution and venv activation consistently across platforms. Agent `.md` files reference the wrapper, not the venv binary directly.

2. **Config field storage: `.planning/config.json` vs separate odoo-gen config**
   - What we know: GSD uses `.planning/config.json`. The user decided Odoo fields go in GSD config.
   - What's unclear: Should we add an `odoo` section to the existing config.json, or create `~/.claude/odoo-gen/config.json` for extension-specific global defaults?
   - Recommendation: Project-specific config goes in `.planning/config.json` under an `odoo` key. Extension-global defaults (like default odoo_version) go in `~/.claude/odoo-gen/defaults.json`. This follows GSD's own pattern (`~/.gsd/defaults.json`).

3. **Symlink vs copy for agent files**
   - What we know: Agent `.md` files need to be in `~/.claude/agents/` for Claude Code to discover them.
   - What's unclear: Should install.sh symlink from `~/.claude/odoo-gen/agents/*.md` to `~/.claude/agents/`, or copy the files?
   - Recommendation: Copy, not symlink. Symlinks can break if the repo is moved. GSD itself copies files (see `gsd-file-manifest.json` tracking copied files by hash). Use a manifest file (`~/.claude/odoo-gen-manifest.json`) to track installed files for clean uninstall/update.

## Sources

### Primary (HIGH confidence)
- Live GSD installation at `~/.claude/` -- command structure, agent format, file manifest pattern (directly examined)
- [Claude Code custom commands docs](https://code.claude.com/docs/en/slash-commands) -- `.md` files in `~/.claude/commands/` directory
- [Odoo 17.0 Module Manifests](https://www.odoo.com/documentation/17.0/developer/reference/backend/module.html) -- manifest keys, version format
- [Odoo 17.0 View Architectures](https://www.odoo.com/documentation/17.0/developer/reference/user_interface/view_architectures.html) -- inline modifiers, `column_invisible`
- [Odoo 17.0 Testing](https://www.odoo.com/documentation/17.0/developer/reference/backend/testing.html) -- TransactionCase, tagging
- [Odoo 17.0 Security Tutorial](https://www.odoo.com/documentation/17.0/developer/tutorials/server_framework_101/04_securityintro.html) -- ir.model.access.csv format
- [OCA pylint-odoo](https://github.com/OCA/pylint-odoo) -- manifest required keys, version format regex
- [OCA maintainer-tools template](https://github.com/OCA/maintainer-tools/blob/master/template/module/__manifest__.py) -- OCA manifest template
- [uv docs](https://docs.astral.sh/uv/) -- package management, venv creation, editable installs
- [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) -- pyproject.toml, console_scripts

### Secondary (MEDIUM confidence)
- [Odoo attrs deprecation forum](https://www.odoo.com/forum/help-1/since-170-the-attrs-and-states-attributes-are-no-longer-used-239190) -- attrs deprecated in 17.0, verified with official docs
- [Cybrosys Odoo 17 Module Structure](https://www.cybrosys.com/odoo/odoo-books/odoo-17-development/creating-odoo-modules/) -- module directory layout, verified against OCA template
- [jinja2-cli PyPI](https://pypi.org/project/jinja2-cli/) -- CLI patterns for Jinja2 rendering
- [Claude Code skills system](https://institute.sfeir.com/en/claude-code/claude-code-custom-commands-and-skills/) -- unified commands/skills in 2026

### Tertiary (LOW confidence)
- None -- all findings verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Jinja2, uv, Click are all mature, well-documented tools with clear use cases
- Architecture: HIGH -- GSD extension pattern directly observed from live installation; command/agent format verified by reading 10+ GSD files
- Odoo 17 specifics: HIGH -- official Odoo docs, OCA pylint-odoo source, OCA template repo all cross-verified
- Pitfalls: MEDIUM-HIGH -- cross-referenced with PITFALLS.md research and official Odoo docs; some template-specific pitfalls are based on Odoo development experience patterns

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stable domain -- Odoo 17 is LTS, GSD structure unlikely to change rapidly)
