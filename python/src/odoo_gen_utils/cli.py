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
from odoo_gen_utils.search.index import DEFAULT_DB_PATH
from odoo_gen_utils.renderer import (
    create_renderer,
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

    template_dir = get_template_dir()
    env = create_renderer(template_dir)

    try:
        output_path = render_template(env, template, Path(output), context)
        click.echo(str(output_path))
    except Exception as exc:
        click.echo(f"Error rendering template: {exc}", err=True)
        sys.exit(1)


@main.command("list-templates")
def list_templates() -> None:
    """List all available Jinja2 templates."""
    template_dir = get_template_dir()

    if not template_dir.is_dir():
        click.echo(f"Templates directory not found: {template_dir}", err=True)
        sys.exit(1)

    templates = sorted(template_dir.glob("*.j2"))

    if not templates:
        click.echo("No templates found.", err=True)
        sys.exit(1)

    for tmpl in templates:
        # Extract description from first Jinja2 comment if present
        description = _extract_template_description(tmpl)
        if description:
            click.echo(f"{tmpl.name:30s} {description}")
        else:
            click.echo(tmpl.name)


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
