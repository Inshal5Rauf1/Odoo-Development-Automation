"""Migration generator module: produce Odoo pre-migrate.py and post-migrate.py scripts.

Consumes diff_specs() output from spec_differ.py and generates per-change helper
functions using raw SQL (cr.execute) following Odoo migration conventions.

Provides:
- generate_migration(): Main entry point returning MigrationResult dict
- MigrationResult: TypedDict for the result structure
- _model_to_table(): Convert dot-separated model name to Odoo table name
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# Type Definitions
# ---------------------------------------------------------------------------

class MigrationResult(TypedDict):
    pre_migrate_code: str
    post_migrate_code: str
    migration_required: bool
    version: str


# ---------------------------------------------------------------------------
# Table Name Conversion
# ---------------------------------------------------------------------------

_FIELD_TYPE_TO_PG: dict[str, str] = {
    "Char": "VARCHAR",
    "Text": "TEXT",
    "Integer": "INTEGER",
    "Float": "DOUBLE PRECISION",
    "Monetary": "NUMERIC",
    "Boolean": "BOOLEAN",
    "Date": "DATE",
    "Datetime": "TIMESTAMP",
    "Binary": "BYTEA",
    "Selection": "VARCHAR",
    "Many2one": "INTEGER",
    "Html": "TEXT",
}


def _field_type_to_pg(field_type: str) -> str:
    """Map an Odoo field type to a PostgreSQL column type for backup columns."""
    return _FIELD_TYPE_TO_PG.get(field_type, "VARCHAR")


def _model_to_table(model_name: str) -> str:
    """Convert dot-separated Odoo model name to underscore table name.

    Example: "fee.invoice" -> "fee_invoice"
    """
    return model_name.replace(".", "_")


# ---------------------------------------------------------------------------
# Helper Generation: Pre-Migrate
# ---------------------------------------------------------------------------

def _generate_pre_helpers(diff_result: dict) -> list[dict]:
    """Generate pre-migrate helper dicts from diff result.

    For each destructive/possibly-destructive change, produces a helper with:
    - name: function name
    - docstring: descriptive with DESTRUCTIVE:/POSSIBLY DESTRUCTIVE: prefix
    - body: list of code lines (cr.execute statements + logging)

    Returns:
        List of helper dicts, each with 'name', 'docstring', 'body' keys.
    """
    helpers: list[dict] = []
    changes = diff_result.get("changes", {})
    models = changes.get("models", {})

    # Model removals: backup all data
    for model in models.get("removed", []):
        model_name = model["name"]
        table = _model_to_table(model_name)
        helpers.append({
            "name": f"_backup_model_{table}",
            "docstring": f'DESTRUCTIVE: Backup all data from {model_name} before model removal.',
            "body": [
                f'cr.execute("SELECT COUNT(*) FROM {table}")',
                'count = cr.fetchone()[0]',
                f'_logger.info("Table {table} has %s rows to backup", count)',
                'if count > 0:',
                f'    cr.execute(',
                f'        "CREATE TABLE IF NOT EXISTS {table}_backup AS SELECT * FROM {table}"',
                f'    )',
                f'    _logger.info("Backed up %s rows from {table}", count)',
            ],
        })

    # Field-level changes in modified models
    for model_name, model_data in models.get("modified", {}).items():
        table = _model_to_table(model_name)
        fields_data = model_data.get("fields", {})

        # Removed fields: backup data
        for field in fields_data.get("removed", []):
            field_name = field["name"]
            field_type = field.get("type", "Char")
            pg_type = _field_type_to_pg(field_type)
            helpers.append({
                "name": f"_backup_{field_name}",
                "docstring": (
                    f"DESTRUCTIVE: Backup column '{field_name}' from {model_name} "
                    f"before field removal."
                ),
                "body": [
                    f'cr.execute(',
                    f'    "ALTER TABLE {table} ADD COLUMN IF NOT EXISTS'
                    f' {field_name}_backup {pg_type}"',
                    f')',
                    f'cr.execute(',
                    f'    "UPDATE {table} SET {field_name}_backup = {field_name}'
                    f' WHERE {field_name} IS NOT NULL"',
                    f')',
                    f'_logger.info(',
                    f'    "Backed up %s rows of {field_name} in {table}", cr.rowcount',
                    f')',
                ],
            })

        # Modified fields
        for field in fields_data.get("modified", []):
            field_name = field["name"]
            field_changes = field.get("changes", {})
            severity = field.get("severity", "non_destructive")

            if severity == "non_destructive":
                continue

            # Type change: backup column
            if "type" in field_changes:
                old_type = field_changes["type"]["old"]
                new_type = field_changes["type"]["new"]
                pg_type = _field_type_to_pg(old_type)
                prefix = "DESTRUCTIVE" if severity == "always_destructive" else "POSSIBLY DESTRUCTIVE"
                helpers.append({
                    "name": f"_backup_{field_name}",
                    "docstring": (
                        f"{prefix}: Backup column '{field_name}' in {model_name} "
                        f"before type change {old_type} -> {new_type}."
                    ),
                    "body": [
                        f'cr.execute(',
                        f'    "ALTER TABLE {table} ADD COLUMN IF NOT EXISTS'
                        f' {field_name}_backup {pg_type}"',
                        f')',
                        f'cr.execute(',
                        f'    "UPDATE {table} SET {field_name}_backup = {field_name}'
                        f' WHERE {field_name} IS NOT NULL"',
                        f')',
                        f'_logger.info(',
                        f'    "Backed up %s rows of {field_name} in {table}", cr.rowcount',
                        f')',
                    ],
                })

            # Required false -> true: validation query
            elif "required" in field_changes:
                req_change = field_changes["required"]
                if req_change.get("old") is False and req_change.get("new") is True:
                    helpers.append({
                        "name": f"_validate_{field_name}",
                        "docstring": (
                            f"POSSIBLY DESTRUCTIVE: Check for NULL values in '{field_name}' "
                            f"of {model_name} before making it required."
                        ),
                        "body": [
                            f'cr.execute(',
                            f'    "SELECT COUNT(*) FROM {table}'
                            f' WHERE {field_name} IS NULL"',
                            f')',
                            'null_count = cr.fetchone()[0]',
                            f'_logger.info(',
                            f'    "Found %s NULL values in {table}.{field_name}", null_count',
                            f')',
                            'if null_count > 0:',
                            f'    _logger.warning(',
                            f'        "{table}.{field_name} has %s NULL rows, backfilling with safe default",',
                            f'        null_count,',
                            f'    )',
                            f'    cr.execute(',
                            f'        "UPDATE {table} SET {field_name} = CURRENT_DATE'
                            f' WHERE {field_name} IS NULL"',
                            f'    )',
                            f'    _logger.info("Backfilled %s rows in {table}.{field_name}", cr.rowcount)',
                        ],
                    })

            # Selection options removed: validation
            elif "selection" in field_changes:
                sel_change = field_changes["selection"]
                removed_opts = sel_change.get("options_removed", [])
                if removed_opts:
                    removed_str = ", ".join(f"'{o}'" for o in removed_opts)
                    helpers.append({
                        "name": f"_validate_{field_name}_selection",
                        "docstring": (
                            f"POSSIBLY DESTRUCTIVE: Check for invalid selection values "
                            f"in '{field_name}' of {model_name} after options removed: "
                            f"{', '.join(removed_opts)}."
                        ),
                        "body": [
                            f'cr.execute(',
                            f'    "SELECT COUNT(*) FROM {table}'
                            f" WHERE {field_name} IN ({removed_str})\"",
                            f')',
                            'invalid_count = cr.fetchone()[0]',
                            f'_logger.info(',
                            f'    "Found %s rows with removed selection values in'
                            f' {table}.{field_name}", invalid_count',
                            f')',
                            'if invalid_count > 0:',
                            f'    _logger.warning(',
                            f'        "{table}.{field_name} has %s rows with removed values,'
                            f' review needed",',
                            f'        invalid_count,',
                            f'    )',
                        ],
                    })

    return helpers


# ---------------------------------------------------------------------------
# Helper Generation: Post-Migrate
# ---------------------------------------------------------------------------

def _generate_post_helpers(diff_result: dict) -> list[dict]:
    """Generate post-migrate helper dicts from diff result.

    For each destructive change, produces a restore/cleanup helper.

    Returns:
        List of helper dicts, each with 'name', 'docstring', 'body' keys.
    """
    helpers: list[dict] = []
    changes = diff_result.get("changes", {})
    models = changes.get("models", {})

    # Model removals: drop table (Odoo may have already, but be safe)
    for model in models.get("removed", []):
        model_name = model["name"]
        table = _model_to_table(model_name)
        helpers.append({
            "name": f"_drop_model_{table}",
            "docstring": f'DESTRUCTIVE: Drop table {table} after model {model_name} removal.',
            "body": [
                f'cr.execute("DROP TABLE IF EXISTS {table} CASCADE")',
                f'_logger.info("Dropped table {table} (rowcount=%s)", cr.rowcount)',
            ],
        })

    # Field-level changes in modified models
    for model_name, model_data in models.get("modified", {}).items():
        table = _model_to_table(model_name)
        fields_data = model_data.get("fields", {})

        # Removed fields: drop backup column
        for field in fields_data.get("removed", []):
            field_name = field["name"]
            helpers.append({
                "name": f"_drop_backup_{field_name}",
                "docstring": (
                    f"DESTRUCTIVE: Drop backup column '{field_name}_backup' from {model_name} "
                    f"after field removal verified."
                ),
                "body": [
                    f'cr.execute(',
                    f'    "ALTER TABLE {table} DROP COLUMN IF EXISTS {field_name}_backup"',
                    f')',
                    f'_logger.info(',
                    f'    "Dropped backup column {field_name}_backup from {table}'
                    f' (rowcount=%s)", cr.rowcount',
                    f')',
                ],
            })

        # Modified fields
        for field in fields_data.get("modified", []):
            field_name = field["name"]
            field_changes = field.get("changes", {})
            severity = field.get("severity", "non_destructive")

            if severity == "non_destructive":
                continue

            # Type change: restore from backup + drop backup
            if "type" in field_changes:
                old_type = field_changes["type"]["old"]
                new_type = field_changes["type"]["new"]
                prefix = "DESTRUCTIVE" if severity == "always_destructive" else "POSSIBLY DESTRUCTIVE"
                helpers.append({
                    "name": f"_restore_{field_name}",
                    "docstring": (
                        f"{prefix}: Restore '{field_name}' in {model_name} from backup "
                        f"after type change {old_type} -> {new_type}, then drop backup."
                    ),
                    "body": [
                        f'cr.execute(',
                        f'    "UPDATE {table} SET {field_name} = {field_name}_backup'
                        f' WHERE {field_name}_backup IS NOT NULL"',
                        f')',
                        f'_logger.info(',
                        f'    "Restored %s rows of {field_name} in {table}", cr.rowcount',
                        f')',
                        f'cr.execute(',
                        f'    "ALTER TABLE {table} DROP COLUMN IF EXISTS {field_name}_backup"',
                        f')',
                        f'_logger.info(',
                        f'    "Dropped backup column {field_name}_backup from {table}'
                        f' (rowcount=%s)", cr.rowcount',
                        f')',
                    ],
                })

    return helpers


# ---------------------------------------------------------------------------
# Script Rendering
# ---------------------------------------------------------------------------

def _render_script(script_type: str, helpers: list[dict], version: str) -> str:
    """Render a complete migration script as a Python source string.

    Args:
        script_type: Either "pre" or "post".
        helpers: List of helper dicts with 'name', 'docstring', 'body'.
        version: Migration version string.

    Returns:
        Complete Python script as a string.
    """
    lines: list[str] = []

    # Module docstring
    label = "pre" if script_type == "pre" else "post"
    lines.append(f'"""{label}-migrate script for version {version}.')
    lines.append("")
    lines.append(f"Auto-generated by odoo-gen-utils migration generator.")
    lines.append(f'Runs {"BEFORE" if label == "pre" else "AFTER"} Odoo ORM updates the schema.')
    lines.append('"""')
    lines.append("")

    # Imports
    lines.append("import logging")
    lines.append("")
    lines.append("_logger = logging.getLogger(__name__)")
    lines.append("")
    lines.append("")

    # Helper functions
    for helper in helpers:
        lines.append(f"def {helper['name']}(cr):")
        lines.append(f'    """{helper["docstring"]}"""')
        for body_line in helper["body"]:
            lines.append(f"    {body_line}")
        lines.append("")
        lines.append("")

    # migrate() entry point
    lines.append("def migrate(cr, version):")
    lines.append(f'    """Main migration entry point for version {version}."""')
    if helpers:
        lines.append(f'    _logger.info("Running {label}-migrate for version %s", version)')
        for helper in helpers:
            lines.append(f"    {helper['name']}(cr)")
    else:
        lines.append(f'    _logger.info("No {label}-migration actions for version %s", version)')
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def generate_migration(
    diff_result: dict,
    version: str,
    output_dir: str | Path | None = None,
) -> MigrationResult:
    """Generate Odoo migration scripts from spec diff output.

    Consumes the output of diff_specs() and generates pre-migrate.py and
    post-migrate.py with per-change helper functions using raw SQL.

    Args:
        diff_result: Output from spec_differ.diff_specs().
        version: Migration version string (e.g., "17.0.1.1.0").
        output_dir: Optional directory to write migration files to.
            Creates {output_dir}/migrations/{version}/ with pre-migrate.py
            and post-migrate.py.

    Returns:
        MigrationResult with pre_migrate_code, post_migrate_code,
        migration_required boolean, and version string.
    """
    migration_required = diff_result.get("migration_required", False)

    # Generate helpers
    pre_helpers = _generate_pre_helpers(diff_result)
    post_helpers = _generate_post_helpers(diff_result)

    # Render scripts
    pre_code = _render_script("pre", pre_helpers, version)
    post_code = _render_script("post", post_helpers, version)

    # Write files if output_dir specified
    if output_dir is not None:
        out_path = Path(output_dir) / "migrations" / version
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "pre-migrate.py").write_text(pre_code, encoding="utf-8")
        (out_path / "post-migrate.py").write_text(post_code, encoding="utf-8")

    return {
        "pre_migrate_code": pre_code,
        "post_migrate_code": post_code,
        "migration_required": migration_required,
        "version": version,
    }
