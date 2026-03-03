"""Click CLI for odoo-gen-utils: render templates and scaffold Odoo modules."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from odoo_gen_utils import __version__
from odoo_gen_utils.auto_fix import format_escalation, run_pylint_fix_loop
from odoo_gen_utils.i18n_extractor import extract_translatable_strings, generate_pot
from odoo_gen_utils.kb_validator import validate_kb_directory, validate_kb_file
from odoo_gen_utils.search import build_oca_index, get_github_token, get_index_status
from odoo_gen_utils.search.analyzer import analyze_module, format_analysis_text
from odoo_gen_utils.search.fork import clone_oca_module, setup_companion_dir
from odoo_gen_utils.search.index import DEFAULT_DB_PATH
from odoo_gen_utils.search.query import (
    format_results_json,
    format_results_text,
    search_modules,
)
from odoo_gen_utils.edition import check_enterprise_dependencies
from odoo_gen_utils.renderer import (
    create_renderer,
    create_versioned_renderer,
    get_template_dir,
    render_module,
    render_template,
)
from odoo_gen_utils.validation import (  # noqa: F401
    ValidationReport,
    check_docker_available,
    diagnose_errors,
    docker_install_module,
    docker_run_tests,
    format_report_json,
    format_report_markdown,
    run_pylint_odoo,
)


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """odoo-gen-utils: Python utilities for the odoo-gen GSD extension."""


@main.command()
@click.option("--template", required=True, help="Template file name (e.g., manifest.py.j2)")
@click.option("--output", required=True, type=click.Path(), help="Output file path")
@click.option("--var", multiple=True, help="Variable in key=value format (repeatable)")
@click.option("--var-file", type=click.Path(exists=True), help="JSON file with template variables")
def render(template: str, output: str, var: tuple[str, ...], var_file: str | None) -> None:
    """Render a single Jinja2 template to a file."""
    context: dict = {}

    if var_file:
        try:
            context = json.loads(Path(var_file).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            click.echo(f"Error reading var-file: {exc}", err=True)
            sys.exit(1)

    for v in var:
        if "=" not in v:
            click.echo(f"Invalid --var format (expected key=value): {v}", err=True)
            sys.exit(1)
        key, value = v.split("=", 1)
        # Attempt to parse JSON values for non-string types
        try:
            context[key] = json.loads(value)
        except json.JSONDecodeError:
            context[key] = value

    # Version-aware renderer: if --var odoo_version=18.0 is provided, use
    # the versioned renderer for that Odoo version.
    odoo_version = context.get("odoo_version")
    if odoo_version:
        env = create_versioned_renderer(odoo_version)
    else:
        template_dir = get_template_dir()
        env = create_renderer(template_dir)

    try:
        output_path = render_template(env, template, Path(output), context)
        click.echo(str(output_path))
    except Exception as exc:
        click.echo(f"Error rendering template: {exc}", err=True)
        sys.exit(1)


@main.command("list-templates")
@click.option("--version", "odoo_version", default=None, help="Odoo version to list templates for (e.g., 17.0, 18.0)")
def list_templates(odoo_version: str | None) -> None:
    """List all available Jinja2 templates.

    Lists templates from shared/ plus version-specific directories. Use --version
    to filter to a specific Odoo version.
    """
    template_dir = get_template_dir()

    if not template_dir.is_dir():
        click.echo(f"Templates directory not found: {template_dir}", err=True)
        sys.exit(1)

    # Collect templates from version directories and shared/
    shared_dir = template_dir / "shared"
    all_templates: list[tuple[str, Path]] = []

    if odoo_version:
        # Show only the specified version + shared
        version_dir = template_dir / odoo_version
        if version_dir.is_dir():
            for tmpl in sorted(version_dir.glob("*.j2")):
                all_templates.append((f"[{odoo_version}]", tmpl))
        if shared_dir.is_dir():
            for tmpl in sorted(shared_dir.glob("*.j2")):
                all_templates.append(("[shared]", tmpl))
    else:
        # Show all version dirs and shared
        for subdir in sorted(template_dir.iterdir()):
            if subdir.is_dir():
                label = f"[{subdir.name}]"
                for tmpl in sorted(subdir.glob("*.j2")):
                    all_templates.append((label, tmpl))

    # Fallback: try flat directory (pre-reorganization layout)
    if not all_templates:
        flat_templates = sorted(template_dir.glob("*.j2"))
        for tmpl in flat_templates:
            all_templates.append(("", tmpl))

    if not all_templates:
        click.echo("No templates found.", err=True)
        sys.exit(1)

    for label, tmpl in all_templates:
        description = _extract_template_description(tmpl)
        prefix = f"{label:10s} " if label else ""
        if description:
            click.echo(f"{prefix}{tmpl.name:30s} {description}")
        else:
            click.echo(f"{prefix}{tmpl.name}")


def _extract_template_description(template_path: Path) -> str:
    """Extract the description from a Jinja2 template's first comment.

    Looks for pattern: {# template_name.j2 -- description #}

    Args:
        template_path: Path to the .j2 template file.

    Returns:
        The description string, or empty string if not found.
    """
    try:
        first_line = template_path.read_text(encoding="utf-8").split("\n", maxsplit=1)[0]
        if first_line.startswith("{#") and first_line.endswith("#}"):
            # Strip comment markers and extract after the dash separator
            content = first_line[2:-2].strip()
            parts = content.split(" -- ", maxsplit=1)
            if len(parts) == 2:
                return parts[1].strip()
            # Try single dash separator
            parts = content.split(" - ", maxsplit=1)
            if len(parts) == 2:
                return parts[1].strip()
    except OSError:
        pass
    return ""


@main.command("render-module")
@click.option("--spec-file", required=True, type=click.Path(exists=True), help="JSON file with module specification")
@click.option("--output-dir", required=True, type=click.Path(), help="Directory to create module in")
def render_module_cmd(spec_file: str, output_dir: str) -> None:
    """Render a complete Odoo module from a JSON specification file."""
    try:
        spec = json.loads(Path(spec_file).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error reading spec file: {exc}", err=True)
        sys.exit(1)

    # Validate required spec fields
    required_fields = ["module_name"]
    missing = [f for f in required_fields if f not in spec]
    if missing:
        click.echo(f"Missing required fields in spec: {', '.join(missing)}", err=True)
        sys.exit(1)

    template_dir = get_template_dir()
    output_path = Path(output_dir)

    try:
        created_files = render_module(spec, template_dir, output_path)
        for f in created_files:
            click.echo(str(f))
    except Exception as exc:
        click.echo(f"Error rendering module: {exc}", err=True)
        sys.exit(1)


def _resolve_kb_path() -> Path:
    """Resolve the knowledge base directory path.

    Checks the installed location first (``~/.claude/odoo-gen/knowledge/``),
    then falls back to a development location (``./knowledge/``).

    Returns:
        Path to the knowledge base directory.

    Raises:
        click.ClickException: If no knowledge base directory is found.
    """
    installed = Path.home() / ".claude" / "odoo-gen" / "knowledge"
    if installed.is_dir():
        return installed

    dev = Path.cwd() / "knowledge"
    if dev.is_dir():
        return dev

    raise click.ClickException(
        "Knowledge base not found. Checked:\n"
        f"  - {installed}\n"
        f"  - {dev}\n"
        "Run install.sh or cd to the odoo-gen project directory."
    )


def _print_file_result(filename: str, result: dict) -> None:
    """Print validation results for a single file."""
    status = "VALID" if result["valid"] else "INVALID"
    icon = "+" if result["valid"] else "x"
    click.echo(f"  [{icon}] {filename}: {status}")
    for error in result["errors"]:
        click.echo(f"      ERROR: {error}")
    for warning in result["warnings"]:
        click.echo(f"      WARN:  {warning}")


@main.command("validate-kb")
@click.option("--custom", "scope", flag_value="custom", default=True, help="Validate only custom/ directory (default)")
@click.option("--all", "scope", flag_value="all", help="Validate all knowledge base files (shipped + custom)")
def validate_kb(scope: str) -> None:
    """Validate knowledge base rule files for correct markdown structure.

    By default, validates the custom/ subdirectory. Use --all to validate
    all shipped and custom knowledge base files.

    Checks format only: headings, code blocks, line count. Does not validate
    the semantic correctness of rule content.
    """
    kb_path = _resolve_kb_path()

    has_errors = False

    if scope == "all":
        # Validate shipped (root) files
        click.echo(f"Validating shipped rules: {kb_path}/")
        shipped_result = validate_kb_directory(kb_path)
        if shipped_result["files"]:
            for filename, result in shipped_result["files"].items():
                _print_file_result(filename, result)
            summary = shipped_result["summary"]
            click.echo(
                f"  Shipped: {summary['valid']} valid, "
                f"{summary['invalid']} invalid, "
                f"{summary['warnings']} with warnings"
            )
            if not shipped_result["valid"]:
                has_errors = True
        else:
            click.echo("  No shipped .md files found.")
        click.echo()

    # Always validate custom/ directory
    custom_path = kb_path / "custom"
    click.echo(f"Validating custom rules: {custom_path}/")

    if not custom_path.is_dir():
        click.echo("  No custom/ directory found. Nothing to validate.")
    else:
        custom_result = validate_kb_directory(custom_path)
        if custom_result["files"]:
            for filename, result in custom_result["files"].items():
                _print_file_result(filename, result)
            summary = custom_result["summary"]
            click.echo(
                f"  Custom: {summary['valid']} valid, "
                f"{summary['invalid']} invalid, "
                f"{summary['warnings']} with warnings"
            )
            if not custom_result["valid"]:
                has_errors = True
        else:
            click.echo("  No custom .md rule files found (README.md is skipped).")

    if has_errors:
        raise SystemExit(1)


@main.command("extract-i18n")
@click.argument("module_path", type=click.Path(exists=True))
def extract_i18n(module_path: str) -> None:
    """Extract translatable strings and generate i18n .pot file.

    Scans Python files for _() calls and XML files for string= attributes.
    Writes MODULE_NAME.pot to MODULE_PATH/i18n/.
    """
    mod_path = Path(module_path).resolve()
    module_name = mod_path.name

    try:
        strings = extract_translatable_strings(mod_path)
        pot_content = generate_pot(module_name, strings)

        i18n_dir = mod_path / "i18n"
        i18n_dir.mkdir(parents=True, exist_ok=True)
        pot_path = i18n_dir / f"{module_name}.pot"
        pot_path.write_text(pot_content, encoding="utf-8")

        click.echo(f"Extracted {len(strings)} translatable strings to {pot_path}")
    except Exception as exc:
        click.echo(f"Error extracting i18n strings: {exc}", err=True)
        sys.exit(1)


@main.command("check-edition")
@click.argument("spec_file", type=click.Path(exists=True))
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def check_edition(spec_file: str, json_output: bool) -> None:
    """Check a module spec for Enterprise-only dependencies.

    Reads the depends list from a spec JSON file and reports any
    Enterprise-only modules with Community alternatives.

    Exit code is always 0 -- warnings are informational (Decision B).
    """
    try:
        spec = json.loads(Path(spec_file).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error reading spec file: {exc}", err=True)
        sys.exit(1)

    depends = spec.get("depends", ["base"])
    warnings = check_enterprise_dependencies(depends)

    if not warnings:
        click.echo("All dependencies are Community-compatible.")
        return

    if json_output:
        click.echo(json.dumps(warnings, indent=2))
        return

    click.echo(f"Found {len(warnings)} Enterprise-only dependency(ies):\n")
    for w in warnings:
        click.echo(f"  * {w['module']} ({w['display_name']}) [{w['category']}]")
        if w.get("alternative"):
            click.echo(f"    Community alternative: {w['alternative']} ({w['alternative_repo']})")
            if w.get("notes"):
                click.echo(f"    Notes: {w['notes']}")
        else:
            click.echo("    No known Community alternative.")
        click.echo()


@main.command()
@click.argument("module_path", type=click.Path(exists=True))
@click.option("--pylint-only", is_flag=True, help="Run only pylint-odoo (skip Docker)")
@click.option("--auto-fix", is_flag=True, help="Attempt to auto-fix pylint violations (max 2 cycles)")
@click.option("--json", "json_output", is_flag=True, help="Output JSON report (machine-readable)")
@click.option("--pylintrc", type=click.Path(exists=True), help="Path to .pylintrc-odoo config file")
def validate(
    module_path: str,
    pylint_only: bool,
    auto_fix: bool,
    json_output: bool,
    pylintrc: str | None,
) -> None:
    """Validate an Odoo module against OCA quality standards.

    Runs pylint-odoo static analysis and optionally Docker-based installation
    and test execution. Produces a structured report with violations, install
    result, test results, and actionable error diagnosis.

    With --auto-fix, attempts to mechanically fix known pylint violations
    (up to 2 cycles) before reporting remaining issues.
    """
    mod_path = Path(module_path).resolve()

    # Validate manifest exists
    manifest = mod_path / "__manifest__.py"
    if not manifest.exists():
        click.echo(f"Error: No __manifest__.py found in {mod_path}", err=True)
        sys.exit(1)

    module_name = mod_path.name

    # Auto-detect .pylintrc-odoo in module directory if not provided
    pylintrc_path = Path(pylintrc) if pylintrc else None
    if pylintrc_path is None:
        candidate = mod_path / ".pylintrc-odoo"
        if candidate.exists():
            pylintrc_path = candidate

    # Step 1: Run pylint-odoo (with optional auto-fix loop)
    if auto_fix:
        total_fixed, violations = run_pylint_fix_loop(mod_path, pylintrc_path=pylintrc_path)
        if total_fixed > 0:
            click.echo(f"Auto-fix: fixed {total_fixed} pylint violations")
        if violations:
            click.echo(format_escalation(violations))
    else:
        violations = run_pylint_odoo(mod_path, pylintrc_path=pylintrc_path)

    install_result = None
    test_results: tuple = ()
    docker_available = True
    diagnosis: tuple[str, ...] = ()
    error_logs: list[str] = []

    if not pylint_only:
        # Step 2: Check Docker and run install
        docker_available = check_docker_available()
        if docker_available:
            install_result = docker_install_module(mod_path)
            if install_result.log_output:
                error_logs.append(install_result.log_output)

            # Step 3: Run tests if install succeeded
            if install_result.success:
                test_results = docker_run_tests(mod_path)

            # Step 4: Diagnose any error logs
            combined_logs = "\n".join(error_logs)
            if combined_logs.strip():
                diagnosis = diagnose_errors(combined_logs)

    # Build report
    report = ValidationReport(
        module_name=module_name,
        pylint_violations=violations,
        install_result=install_result,
        test_results=test_results,
        diagnosis=diagnosis,
        docker_available=docker_available,
    )

    # Output
    if json_output:
        click.echo(json.dumps(format_report_json(report), indent=2))
    else:
        click.echo(format_report_markdown(report))

    # Exit code: 0 if clean, 1 if any issues
    has_issues = bool(violations) or (
        install_result is not None and not install_result.success
    ) or any(not tr.passed for tr in test_results)

    if has_issues:
        sys.exit(1)


@main.command("build-index")
@click.option("--token", envvar="GITHUB_TOKEN", default=None, help="GitHub personal access token")
@click.option("--db-path", default=None, help="ChromaDB storage path (default: ~/.local/share/odoo-gen/chromadb/)")
@click.option("--update", is_flag=True, help="Only re-index repos pushed since last build")
def build_index(token: str | None, db_path: str | None, update: bool) -> None:
    """Build or update the local ChromaDB index of OCA Odoo modules.

    Crawls all OCA GitHub repositories with a 17.0 branch, extracts module
    metadata from __manifest__.py files, and stores embeddings in a local
    ChromaDB database for semantic search.
    """
    if token is None:
        token = get_github_token()

    if not token:
        click.echo(
            "Index build requires GitHub authentication.\n"
            "Run: gh auth login\n"
            "Or set: export GITHUB_TOKEN=your_token\n"
            "Then re-run your search."
        )
        sys.exit(1)

    resolved_path = db_path or str(DEFAULT_DB_PATH)

    def _progress(done: int, total: int) -> None:
        click.echo(f"Indexing OCA repos... {done}/{total}", nl=False)
        click.echo("\r", nl=False)

    click.echo("Building OCA module index...")
    count = build_oca_index(
        token=token,
        db_path=resolved_path,
        incremental=update,
        progress_callback=_progress,
    )
    click.echo(f"Indexed {count} modules from OCA")


@main.command("index-status")
@click.option("--db-path", default=None, help="ChromaDB storage path")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def index_status(db_path: str | None, json_output: bool) -> None:
    """Show the status of the local OCA module search index.

    Reports whether the index exists, how many modules are indexed,
    when it was last built, and the storage location.
    """
    status = get_index_status(db_path)

    if json_output:
        import dataclasses

        click.echo(json.dumps(dataclasses.asdict(status), indent=2))
    else:
        if status.exists:
            click.echo(f"Index exists: yes")
            click.echo(f"Modules indexed: {status.module_count}")
            click.echo(f"Last built: {status.last_built or 'unknown'}")
            click.echo(f"Storage path: {status.db_path}")
            click.echo(f"Size: {status.size_bytes} bytes")
        else:
            click.echo("Index exists: no")
            click.echo(f"Storage path: {status.db_path}")
            click.echo("Run 'odoo-gen-utils build-index' to create the index.")


@main.command("search-modules")
@click.argument("query")
@click.option("--limit", default=5, help="Number of results (default: 5)")
@click.option("--db-path", default=None, help="ChromaDB storage path")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.option(
    "--github",
    "github_fallback",
    is_flag=True,
    help="Fall back to GitHub search if no OCA results found",
)
def search_modules_cmd(
    query: str,
    limit: int,
    db_path: str | None,
    json_output: bool,
    github_fallback: bool,
) -> None:
    """Semantically search for Odoo modules matching a natural language query.

    Searches the local ChromaDB index for OCA modules, sorted by relevance.
    With --github, falls back to live GitHub search when no OCA results found.
    Auto-builds the index on first use if it does not exist.
    """
    resolved_path = db_path or str(DEFAULT_DB_PATH)

    # Auto-build index on first use (Decision B)
    status = get_index_status(resolved_path)
    if not status.exists or status.module_count == 0:
        token = get_github_token()
        if not token:
            click.echo(
                "No index found. Building requires GitHub authentication.\n"
                "Run: gh auth login\n"
                "Or set: export GITHUB_TOKEN=your_token\n"
                "Then re-run your search.",
                err=True,
            )
            sys.exit(1)

        click.echo("No index found. Building index first (this takes ~3-5 minutes)...")

        def _progress(done: int, total: int) -> None:
            click.echo(f"Indexing OCA repos... {done}/{total}", nl=False)
            click.echo("\r", nl=False)

        build_oca_index(
            token=token,
            db_path=resolved_path,
            progress_callback=_progress,
        )
        click.echo("Index built successfully.\n")

    # Run search
    try:
        results = search_modules(
            query,
            db_path=resolved_path,
            n_results=limit,
            github_fallback=github_fallback,
        )
    except ValueError as exc:
        click.echo(f"Search error: {exc}", err=True)
        sys.exit(1)

    # Auto-fallback: if OCA returned 0 results and --github not set, retry with fallback
    if not results and not github_fallback:
        results = search_modules(
            query,
            db_path=resolved_path,
            n_results=limit,
            github_fallback=True,
        )

    if not results:
        click.echo("No results found.")
        sys.exit(1)

    if json_output:
        click.echo(format_results_json(results))
    else:
        click.echo(format_results_text(results))


@main.command("extend-module")
@click.argument("module_name")
@click.option("--repo", required=True, help="OCA repo name (e.g., sale-workflow)")
@click.option(
    "--output-dir",
    default=".",
    type=click.Path(),
    help="Output directory for cloned + companion modules",
)
@click.option(
    "--spec-file",
    type=click.Path(exists=True),
    help="Refined spec JSON for the extension module",
)
@click.option("--branch", default="17.0", help="Git branch to clone (default: 17.0)")
@click.option("--json", "json_output", is_flag=True, help="Output analysis as JSON")
def extend_module_cmd(
    module_name: str,
    repo: str,
    output_dir: str,
    spec_file: str | None,
    branch: str,
    json_output: bool,
) -> None:
    """Clone an OCA module and set up a companion extension module.

    Performs git sparse checkout to clone only the target module from an OCA
    repository, analyzes its structure (models, fields, views, security),
    and creates a companion {module}_ext directory for delta code.

    If --spec-file is provided, copies the refined spec to both
    {module}_ext/spec.json and overwrites the original spec.json path
    (REFN-03: refined spec is the new source of truth).
    """
    out_path = Path(output_dir).resolve()

    # Step 1: Clone the module via sparse checkout
    click.echo(f"Cloning {repo}/{module_name} (branch {branch})...")
    try:
        cloned_path = clone_oca_module(repo, module_name, out_path, branch=branch)
    except Exception as exc:
        click.echo(f"Error cloning module: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Cloned to: {cloned_path}")

    # Step 2: Analyze the module structure
    click.echo("Analyzing module structure...")
    try:
        analysis = analyze_module(cloned_path)
    except FileNotFoundError as exc:
        click.echo(f"Error analyzing module: {exc}", err=True)
        sys.exit(1)

    # Step 3: Set up companion directory
    companion_path = setup_companion_dir(cloned_path)
    click.echo(f"Companion module: {companion_path}")

    # Step 4: Handle spec file (REFN-03)
    if spec_file:
        spec_path = Path(spec_file).resolve()
        spec_content = spec_path.read_text(encoding="utf-8")

        # Save to companion module
        ext_spec = companion_path / "spec.json"
        ext_spec.write_text(spec_content, encoding="utf-8")
        click.echo(f"Spec saved to: {ext_spec}")

        # Overwrite original spec.json (REFN-03: refined spec is source of truth)
        spec_path.write_text(spec_content, encoding="utf-8")
        click.echo(f"Original spec overwritten: {spec_path}")

    # Step 5: Print analysis
    if json_output:
        import dataclasses

        analysis_dict = dataclasses.asdict(analysis)
        # Convert tuples to lists for JSON serialization
        analysis_dict["model_names"] = list(analysis.model_names)
        for model, field_names in analysis_dict["model_fields"].items():
            analysis_dict["model_fields"][model] = list(field_names)
        analysis_dict["security_groups"] = list(analysis.security_groups)
        analysis_dict["data_files"] = list(analysis.data_files)
        for model, types in analysis_dict["view_types"].items():
            analysis_dict["view_types"][model] = list(types)
        click.echo(json.dumps(analysis_dict, indent=2))
    else:
        click.echo("")
        click.echo(format_analysis_text(analysis))

    # Step 6: Print output paths
    click.echo("")
    click.echo("Output:")
    click.echo(f"  Original module: {cloned_path}")
    click.echo(f"  Companion module: {companion_path}")
