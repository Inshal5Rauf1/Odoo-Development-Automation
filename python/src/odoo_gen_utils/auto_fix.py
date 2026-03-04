"""Pylint-odoo and Docker auto-fix loops with escalation.

Mechanically fixes known pylint-odoo violation codes and Docker error
patterns, re-validates, and escalates remaining issues in a grouped
file:line + suggestion format.

QUAL-09: pylint auto-fix (5 fixable codes, configurable iterations)
QUAL-10: Docker auto-fix (5 fixable patterns, configurable iterations)
AFIX-01: missing mail.thread auto-fix
AFIX-02: unused import auto-fix
DFIX-01: 3 new Docker fix functions (xml_parse_error, missing_acl, manifest_load_order)
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path

from odoo_gen_utils.validation.pylint_runner import run_pylint_odoo
from odoo_gen_utils.validation.types import Violation

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------

FIXABLE_PYLINT_CODES: frozenset[str] = frozenset({
    "W8113",  # redundant string= parameter on field
    "W8111",  # renamed field parameter
    "C8116",  # superfluous manifest key
    "W8150",  # absolute import should be relative
    "C8107",  # missing required manifest key
})

DEFAULT_MAX_FIX_ITERATIONS: int = 5

FIXABLE_DOCKER_PATTERNS: frozenset[str] = frozenset({
    "xml_parse_error",
    "missing_acl",
    "missing_import",
    "manifest_load_order",
    "missing_mail_thread",
})

# Map of renamed field parameters (old -> new) for W8111
_RENAMED_PARAMS: dict[str, str | None] = {
    "track_visibility": "tracking",
    "oldname": None,  # removed entirely
    "digits_compute": "digits",
    "select": "index",
}

# Default values for missing manifest keys (C8107)
_MANIFEST_KEY_DEFAULTS: dict[str, str] = {
    "license": "LGPL-3",
    "author": "",
    "website": "",
    "category": "Uncategorized",
    "version": "17.0.1.0.0",
    "application": "False",
    "installable": "True",
}

# Docker diagnosis text -> pattern ID mapping keywords
_DOCKER_PATTERN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "xml_parse_error": ("xml", "syntax error", "parse", "xmlsyntaxerror", "mismatched tag"),
    "missing_acl": ("access control", "acl", "ir.model.access", "access rights", "no access rule"),
    "missing_import": ("no module named", "importerror", "modulenotfounderror", "could not be imported"),
    "manifest_load_order": ("action", "act_window", "does not exist", "external id not found"),
    "missing_mail_thread": ("mail.thread", "oe_chatter", "chatter", "mail.activity.mixin", "message_follower_ids"),
}


# -------------------------------------------------------------------------
# Pylint auto-fix
# -------------------------------------------------------------------------


def is_fixable_pylint(violation: Violation) -> bool:
    """Check whether a pylint violation can be mechanically auto-fixed."""
    return violation.rule_code in FIXABLE_PYLINT_CODES


def fix_pylint_violation(violation: Violation, module_path: Path) -> bool:
    """Apply a mechanical fix for a single pylint violation.

    Reads the source file, applies the fix based on the rule_code,
    and writes the corrected content back. Uses immutable patterns:
    read content -> create new content -> write back.

    Args:
        violation: The Violation to fix.
        module_path: Root path of the Odoo module.

    Returns:
        True if fix was applied, False if not applicable or failed.
    """
    if violation.rule_code not in FIXABLE_PYLINT_CODES:
        return False

    file_path = module_path / violation.file
    if not file_path.exists():
        return False

    handlers = {
        "W8113": _fix_w8113_redundant_string,
        "W8111": _fix_w8111_renamed_parameter,
        "C8116": _fix_c8116_superfluous_manifest_key,
        "W8150": _fix_w8150_absolute_import,
        "C8107": _fix_c8107_missing_manifest_key,
    }

    handler = handlers.get(violation.rule_code)
    if handler is None:
        return False

    return handler(violation, file_path)


def _fix_w8113_redundant_string(violation: Violation, file_path: Path) -> bool:
    """W8113: Remove redundant string= parameter from field definition."""
    content = file_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    line_idx = violation.line - 1

    if line_idx < 0 or line_idx >= len(lines):
        return False

    original_line = lines[line_idx]
    # Remove string="..." or string='...' with optional trailing comma and space
    new_line = re.sub(
        r"""\s*string\s*=\s*(?:"[^"]*"|'[^']*')\s*,?\s*""",
        "",
        original_line,
    )

    # If we removed the string= at the end but there's a trailing comma before ), clean up
    new_line = re.sub(r",\s*\)", ")", new_line)
    # If we removed string= but left (,  other_param), clean up leading comma after (
    new_line = re.sub(r"\(\s*,\s*", "(", new_line)

    if new_line == original_line:
        return False

    new_lines = list(lines)
    new_lines[line_idx] = new_line
    new_content = "\n".join(new_lines)
    file_path.write_text(new_content, encoding="utf-8")
    return True


def _fix_w8111_renamed_parameter(violation: Violation, file_path: Path) -> bool:
    """W8111: Rename deprecated field parameter to its replacement."""
    content = file_path.read_text(encoding="utf-8")

    # Extract old parameter name from the violation message
    # Message format: '"track_visibility" has been renamed to "tracking"'
    match = re.search(r'"(\w+)"\s+has been renamed', violation.message)
    if not match:
        return False

    old_param = match.group(1)
    new_param = _RENAMED_PARAMS.get(old_param)

    if new_param is None and old_param in _RENAMED_PARAMS:
        # Parameter removed entirely -- remove the param=value segment
        new_content = re.sub(
            rf"""\s*{re.escape(old_param)}\s*=\s*(?:"[^"]*"|'[^']*'|\w+)\s*,?\s*""",
            "",
            content,
        )
    elif new_param is not None:
        new_content = content.replace(old_param, new_param)
    else:
        return False

    if new_content == content:
        return False

    file_path.write_text(new_content, encoding="utf-8")
    return True


def _fix_c8116_superfluous_manifest_key(violation: Violation, file_path: Path) -> bool:
    """C8116: Remove a superfluous/deprecated key from __manifest__.py."""
    content = file_path.read_text(encoding="utf-8")

    # Extract key name from message: 'Deprecated key "description" in manifest file'
    match = re.search(r'"(\w+)"', violation.message)
    if not match:
        return False

    key_name = match.group(1)

    # Remove the key-value line from the manifest dict literal
    # Handles: "key": "value", or "key": value,
    new_content = re.sub(
        rf"""^\s*"{re.escape(key_name)}"\s*:.*,?\n""",
        "",
        content,
        flags=re.MULTILINE,
    )

    if new_content == content:
        return False

    file_path.write_text(new_content, encoding="utf-8")
    return True


def _fix_w8150_absolute_import(violation: Violation, file_path: Path) -> bool:
    """W8150: Convert absolute odoo.addons import to relative import."""
    content = file_path.read_text(encoding="utf-8")

    # Replace "from odoo.addons.module_name import X" with "from . import X"
    # and "from odoo.addons.module_name.sub import X" with "from .sub import X"
    new_content = re.sub(
        r"from\s+odoo\.addons\.\w+(\.\w+)*\s+import\s+",
        lambda m: "from . import " if not m.group(1) else f"from .{m.group(1)[1:]} import ",
        content,
    )

    if new_content == content:
        return False

    file_path.write_text(new_content, encoding="utf-8")
    return True


def _fix_c8107_missing_manifest_key(violation: Violation, file_path: Path) -> bool:
    """C8107: Add a missing required key to __manifest__.py."""
    content = file_path.read_text(encoding="utf-8")

    # Extract missing key name: 'Missing required key "license" in manifest file'
    match = re.search(r'"(\w+)"', violation.message)
    if not match:
        return False

    key_name = match.group(1)
    default_value = _MANIFEST_KEY_DEFAULTS.get(key_name, "")

    # Check if key already exists
    if re.search(rf'"{re.escape(key_name)}"\s*:', content):
        return False

    # Add the key after the opening brace of the dict
    # Find the first line with a key-value pair and insert before it
    if default_value in ("True", "False"):
        insert_line = f'    "{key_name}": {default_value},\n'
    else:
        insert_line = f'    "{key_name}": "{default_value}",\n'

    # Insert after the opening { line
    new_content = re.sub(
        r"(\{\s*\n)",
        rf"\1{insert_line}",
        content,
        count=1,
    )

    if new_content == content:
        return False

    file_path.write_text(new_content, encoding="utf-8")
    return True


def fix_pylint_violations(
    violations: tuple[Violation, ...],
    module_path: Path,
) -> tuple[int, tuple[Violation, ...]]:
    """Process a batch of violations, fixing what can be fixed.

    Args:
        violations: All violations to process.
        module_path: Root path of the Odoo module.

    Returns:
        Tuple of (fixed_count, remaining_violations) where remaining
        includes non-fixable violations and failed fixes.
    """
    fixed_count = 0
    remaining: list[Violation] = []

    for violation in violations:
        if is_fixable_pylint(violation):
            if fix_pylint_violation(violation, module_path):
                fixed_count += 1
            else:
                remaining.append(violation)
        else:
            remaining.append(violation)

    return fixed_count, tuple(remaining)


def run_pylint_fix_loop(
    module_path: Path,
    pylintrc_path: Path | None = None,
    max_iterations: int = DEFAULT_MAX_FIX_ITERATIONS,
) -> tuple[int, tuple[Violation, ...]]:
    """Run pylint-odoo with up to max_iterations auto-fix cycles.

    Each cycle: run pylint -> fix fixable violations -> count.
    If a cycle produces 0 fixable violations, stop early.

    Args:
        module_path: Root path of the Odoo module.
        pylintrc_path: Optional path to .pylintrc-odoo config file.
        max_iterations: Maximum number of fix cycles (default 5).

    Returns:
        Tuple of (total_fixed, remaining_violations) after all cycles.
    """
    total_fixed = 0
    remaining: tuple[Violation, ...] = ()

    for _cycle in range(max_iterations):
        violations = run_pylint_odoo(module_path, pylintrc_path=pylintrc_path)

        if not violations:
            break

        # Handle W0611 (unused-import) via fix_unused_imports
        w0611_violations = [v for v in violations if v.rule_code == "W0611"]
        non_w0611 = tuple(v for v in violations if v.rule_code != "W0611")

        w0611_applied = False
        if w0611_violations:
            w0611_files = {v.file for v in w0611_violations}
            for rel_file in w0611_files:
                file_path = module_path / rel_file
                if file_path.exists():
                    if fix_unused_imports(file_path):
                        w0611_applied = True
                        total_fixed += sum(
                            1 for v in w0611_violations if v.file == rel_file
                        )

        # Check if any remaining are fixable by pylint fixer
        has_fixable = any(is_fixable_pylint(v) for v in non_w0611)
        if not has_fixable:
            remaining = non_w0611
            if w0611_applied:
                # W0611 fixes shifted line numbers; re-run pylint to get
                # updated violations that may now be fixable
                continue
            break

        cycle_fixed, remaining = fix_pylint_violations(non_w0611, module_path)
        total_fixed += cycle_fixed

        if cycle_fixed == 0 and not w0611_applied:
            break

    return total_fixed, remaining


# -------------------------------------------------------------------------
# Docker auto-fix identification
# -------------------------------------------------------------------------


def identify_docker_fix(diagnosis: str) -> str | None:
    """Identify whether a Docker error diagnosis matches a fixable pattern.

    Matches diagnosis text against known fixable Docker error patterns
    using keyword matching against the error_patterns.json taxonomy.

    Args:
        diagnosis: A diagnosis string from diagnose_errors().

    Returns:
        The pattern ID string if fixable, None if not.
    """
    diagnosis_lower = diagnosis.lower()

    for pattern_id, keywords in _DOCKER_PATTERN_KEYWORDS.items():
        if any(kw in diagnosis_lower for kw in keywords):
            return pattern_id

    return None


# -------------------------------------------------------------------------
# Escalation formatting
# -------------------------------------------------------------------------


def format_escalation(violations: tuple[Violation, ...]) -> str:
    """Format remaining violations as a grouped escalation report.

    Groups violations by file, includes file:line reference and
    one fix suggestion per violation per CONTEXT.md Decision E.

    Args:
        violations: Remaining violations after auto-fix exhausted.

    Returns:
        Formatted escalation string, or "No remaining issues." if empty.
    """
    if not violations:
        return "No remaining issues."

    grouped: dict[str, list[Violation]] = defaultdict(list)
    for v in violations:
        grouped[v.file].append(v)

    lines: list[str] = ["Auto-fix exhausted. Remaining violations:", ""]

    for file_path in sorted(grouped.keys()):
        file_violations = sorted(grouped[file_path], key=lambda v: v.line)
        for v in file_violations:
            lines.append(f"[{v.file}:{v.line}] {v.rule_code}: {v.message}")
            if v.suggestion:
                lines.append(f"  -> {v.suggestion}")

    return "\n".join(lines)


# -------------------------------------------------------------------------
# Module-level auto-fix: missing mail.thread (AFIX-01)
# -------------------------------------------------------------------------

# Chatter indicators in XML view files
_CHATTER_INDICATORS: tuple[str, ...] = (
    "oe_chatter",
    "<chatter",
    "message_follower_ids",
    "message_ids",
)


def _has_chatter_references(module_path: Path) -> bool:
    """Check whether any XML file in views/ contains chatter indicators."""
    views_dir = module_path / "views"
    if not views_dir.is_dir():
        return False

    for xml_file in views_dir.glob("*.xml"):
        content = xml_file.read_text(encoding="utf-8")
        if any(indicator in content for indicator in _CHATTER_INDICATORS):
            return True

    return False


def _has_mail_thread_inherit(model_content: str) -> bool:
    """Check whether model content already contains mail.thread inheritance."""
    return "mail.thread" in model_content


def _find_model_file(module_path: Path) -> Path | None:
    """Find the first .py file in models/ that defines _name."""
    models_dir = module_path / "models"
    if not models_dir.is_dir():
        return None

    for py_file in sorted(models_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        if "_name" in content and "_name =" in content:
            return py_file

    return None


def fix_missing_mail_thread(module_path: Path) -> bool:
    """Detect and fix missing mail.thread inheritance when chatter XML exists.

    Scans XML files in views/ for chatter indicators (oe_chatter, <chatter/>,
    message_follower_ids, message_ids). If found, checks whether the model
    already inherits from mail.thread. If not, inserts the _inherit line
    after _description.

    Args:
        module_path: Root path of the Odoo module.

    Returns:
        True if fix was applied, False if not needed or not applicable.
    """
    if not _has_chatter_references(module_path):
        return False

    model_file = _find_model_file(module_path)
    if model_file is None:
        return False

    content = model_file.read_text(encoding="utf-8")

    if _has_mail_thread_inherit(content):
        return False

    # Insert _inherit after _description line
    lines = content.split("\n")
    description_idx: int | None = None

    for idx, line in enumerate(lines):
        if "_description" in line and "=" in line:
            description_idx = idx
            break

    if description_idx is None:
        return False

    # Detect the indentation from the _description line
    desc_line = lines[description_idx]
    indent = ""
    for ch in desc_line:
        if ch in (" ", "\t"):
            indent += ch
        else:
            break

    inherit_line = f"{indent}_inherit = ['mail.thread', 'mail.activity.mixin']"

    new_lines = list(lines)
    new_lines.insert(description_idx + 1, inherit_line)
    new_content = "\n".join(new_lines)

    model_file.write_text(new_content, encoding="utf-8")
    return True


# -------------------------------------------------------------------------
# Module-level auto-fix: XML parse error (fix mismatched tags)
# -------------------------------------------------------------------------


def fix_xml_parse_error(module_path: Path, error_output: str) -> bool:
    """Detect and fix mismatched closing tags in XML view files.

    Parses the error output to find the file and the mismatched tag details.
    Common pattern from lxml: "Opening and ending tag mismatch: X line N and Y"
    This means the opening tag is X but the closing tag is Y (a typo).

    Args:
        module_path: Root path of the Odoo module.
        error_output: Error text from Docker validation.

    Returns:
        True if fix was applied, False if not applicable or XML is well-formed.
    """
    import xml.etree.ElementTree as ET

    # Try to find referenced XML files in the error output
    xml_files: list[Path] = []

    # Pattern: "(filename, line N)" or "File "...filename""
    file_matches = re.findall(
        r'(?:(?:\(|File\s+["\'])([^)"\']+\.xml))', error_output
    )
    for fname in file_matches:
        candidate = module_path / fname
        if candidate.exists():
            xml_files.append(candidate)

    # If no specific file found, scan all XML files in views/
    if not xml_files:
        views_dir = module_path / "views"
        if views_dir.is_dir():
            xml_files = sorted(views_dir.glob("*.xml"))

    if not xml_files:
        return False

    # Extract mismatch info from error output
    # Pattern: "Opening and ending tag mismatch: OPEN line N and CLOSE"
    mismatch_match = re.search(
        r"(?:Opening and ending tag mismatch|Mismatched tag):\s*(\w+)\s+line\s+\d+\s+and\s+(\w+)",
        error_output,
    )

    any_fixed = False

    for xml_file in xml_files:
        content = xml_file.read_text(encoding="utf-8")

        # First, try to parse -- if it parses fine, no fix needed
        try:
            ET.fromstring(content)
            continue  # Well-formed, skip
        except ET.ParseError:
            pass  # Has errors, try to fix

        if mismatch_match:
            open_tag = mismatch_match.group(1)
            close_tag = mismatch_match.group(2)

            # Replace the wrong closing tag with the correct one
            wrong_close = f"</{close_tag}>"
            right_close = f"</{open_tag}>"

            if wrong_close in content:
                new_content = content.replace(wrong_close, right_close, 1)
                if new_content != content:
                    xml_file.write_text(new_content, encoding="utf-8")
                    any_fixed = True
                    continue

        # Fallback: try heuristic detection of common mismatched tags
        # Look for closing tags that don't have matching opening tags
        opening_tags = re.findall(r"<(\w+)[\s>]", content)
        closing_tags = re.findall(r"</(\w+)>", content)

        open_counts: dict[str, int] = {}
        for tag in opening_tags:
            open_counts[tag] = open_counts.get(tag, 0) + 1

        close_counts: dict[str, int] = {}
        for tag in closing_tags:
            close_counts[tag] = close_counts.get(tag, 0) + 1

        # Find tags that appear in closing but not in opening (likely typos)
        new_content = content
        for close_tag_name in close_counts:
            if close_tag_name not in open_counts:
                # This closing tag has no matching opener -- find the best match
                # by looking for an opener with more opens than closes
                for open_tag_name in open_counts:
                    open_excess = open_counts.get(open_tag_name, 0) - close_counts.get(
                        open_tag_name, 0
                    )
                    if open_excess > 0:
                        wrong = f"</{close_tag_name}>"
                        right = f"</{open_tag_name}>"
                        new_content = new_content.replace(wrong, right, 1)
                        break

        if new_content != content:
            xml_file.write_text(new_content, encoding="utf-8")
            any_fixed = True

    return any_fixed


# -------------------------------------------------------------------------
# Module-level auto-fix: missing ACL (create ir.model.access.csv)
# -------------------------------------------------------------------------


def _extract_model_names(module_path: Path) -> tuple[str, ...]:
    """Scan models/ directory for all Python files defining _name.

    Returns:
        Tuple of model technical names found (e.g., ("my.model", "my.other")).
    """
    models_dir = module_path / "models"
    if not models_dir.is_dir():
        return ()

    model_names: list[str] = []
    for py_file in sorted(models_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        # Match _name = "model.name" or _name = 'model.name'
        matches = re.findall(r"""_name\s*=\s*["']([^"']+)["']""", content)
        model_names.extend(matches)

    return tuple(model_names)


def _build_acl_line(model_name: str) -> str:
    """Build a single ACL CSV line for a model.

    Format: access_{underscored},access.{dotted},model_{underscored},base.group_user,1,1,1,0
    """
    model_underscore = model_name.replace(".", "_")
    return (
        f"access_{model_underscore},"
        f"access.{model_name},"
        f"model_{model_underscore},"
        f"base.group_user,1,1,1,0"
    )


def fix_missing_acl(module_path: Path, error_output: str) -> bool:
    """Create or update security/ir.model.access.csv for all models.

    Scans models/ for _name definitions, checks if CSV exists with entries
    for each model, and creates/updates as needed. Also ensures __manifest__.py
    includes the CSV path in its data list.

    Args:
        module_path: Root path of the Odoo module.
        error_output: Error text from Docker validation.

    Returns:
        True if fix was applied, False if all models already have ACL entries.
    """
    model_names = _extract_model_names(module_path)
    if not model_names:
        return False

    csv_path = module_path / "security" / "ir.model.access.csv"
    header = "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink"

    existing_content = ""
    if csv_path.exists():
        existing_content = csv_path.read_text(encoding="utf-8")

    # Find which models are missing from the CSV
    missing_models: list[str] = []
    for model_name in model_names:
        model_underscore = model_name.replace(".", "_")
        if f"model_{model_underscore}" not in existing_content:
            missing_models.append(model_name)

    if not missing_models:
        return False

    # Build new CSV content (immutable: create new string, don't mutate)
    if existing_content.strip():
        # Append to existing CSV
        lines = existing_content.rstrip("\n").split("\n")
        new_lines = list(lines)
        for model_name in missing_models:
            new_lines.append(_build_acl_line(model_name))
        new_csv_content = "\n".join(new_lines) + "\n"
    else:
        # Create new CSV
        csv_lines = [header]
        for model_name in missing_models:
            csv_lines.append(_build_acl_line(model_name))
        new_csv_content = "\n".join(csv_lines) + "\n"

    # Create security/ directory if needed
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(new_csv_content, encoding="utf-8")

    # Update __manifest__.py to include the CSV path if not already there
    manifest_path = module_path / "__manifest__.py"
    if manifest_path.exists():
        manifest_content = manifest_path.read_text(encoding="utf-8")
        csv_ref = "security/ir.model.access.csv"
        if csv_ref not in manifest_content:
            # Insert into the 'data' list using AST for safe parsing
            try:
                tree = ast.parse(manifest_content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Dict):
                        for key_node, value_node in zip(node.keys, node.values):
                            if (
                                isinstance(key_node, ast.Constant)
                                and key_node.value == "data"
                                and isinstance(value_node, ast.List)
                            ):
                                # Found the data list -- insert CSV reference
                                # Use string manipulation to add it
                                new_manifest = manifest_content.replace(
                                    '"data": [',
                                    f'"data": [\n        "{csv_ref}",',
                                )
                                if new_manifest == manifest_content:
                                    # Try alternate formatting
                                    new_manifest = manifest_content.replace(
                                        "'data': [",
                                        f"'data': [\n        '{csv_ref}',",
                                    )
                                if new_manifest != manifest_content:
                                    manifest_path.write_text(new_manifest, encoding="utf-8")
                                break
            except SyntaxError:
                pass  # Cannot parse manifest, skip update

    return True


# -------------------------------------------------------------------------
# Module-level auto-fix: manifest load order (reorder data files)
# -------------------------------------------------------------------------


def _is_action_definer(file_path: Path) -> bool:
    """Check if an XML file defines actions (ir.actions.act_window or <act_window>)."""
    if not file_path.exists():
        return False
    content = file_path.read_text(encoding="utf-8")
    return bool(
        "ir.actions.act_window" in content
        or "<act_window" in content
    )


def _is_action_reference(file_path: Path) -> bool:
    """Check if an XML file references actions (action= attribute in menus)."""
    if not file_path.exists():
        return False
    content = file_path.read_text(encoding="utf-8")
    return bool(re.search(r'\baction\s*=\s*["\']', content))


def fix_manifest_load_order(module_path: Path, error_output: str) -> bool:
    """Reorder manifest data list so action definitions precede action references.

    Reads __manifest__.py, identifies files that define actions and files that
    reference actions, and reorders so definitions come first.

    Args:
        module_path: Root path of the Odoo module.
        error_output: Error text from Docker validation.

    Returns:
        True if fix was applied, False if order is already correct.
    """
    manifest_path = module_path / "__manifest__.py"
    if not manifest_path.exists():
        return False

    manifest_content = manifest_path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(manifest_content)
    except SyntaxError:
        return False

    # Find the 'data' list in the manifest dict
    data_list: list[str] | None = None
    data_node: ast.List | None = None

    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key_node, value_node in zip(node.keys, node.values):
                if (
                    isinstance(key_node, ast.Constant)
                    and key_node.value == "data"
                    and isinstance(value_node, ast.List)
                ):
                    data_list = []
                    data_node = value_node
                    for elt in value_node.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            data_list.append(elt.value)
                    break

    if data_list is None or len(data_list) < 2:
        return False

    # Classify each file
    definers: list[str] = []
    referencers: list[str] = []
    others: list[str] = []

    for file_ref in data_list:
        file_path = module_path / file_ref
        if _is_action_definer(file_path):
            definers.append(file_ref)
        elif _is_action_reference(file_path):
            referencers.append(file_ref)
        else:
            others.append(file_ref)

    if not definers or not referencers:
        return False

    # Check if order is already correct: all definers before all referencers
    first_referencer_idx = min(data_list.index(r) for r in referencers)
    last_definer_idx = max(data_list.index(d) for d in definers)

    if last_definer_idx < first_referencer_idx:
        # Already in correct order
        return False

    # Build new order: others first, then definers, then referencers
    # Preserve relative order within each group
    reordered = others + definers + referencers

    # Rebuild the manifest content with the new data list
    # Get the source text segment for the old data list and replace it
    assert data_node is not None
    # Build new list repr
    new_list_items = ", ".join(f'"{item}"' for item in reordered)
    new_list_str = f"[{new_list_items}]"

    # Extract old data list string from source
    # Use line/col info from AST
    lines = manifest_content.split("\n")
    # Find "data": [...] and replace the list portion
    new_manifest = re.sub(
        r'("data"\s*:\s*)\[.*?\]',
        rf'\1{new_list_str}',
        manifest_content,
        flags=re.DOTALL,
    )

    if new_manifest == manifest_content:
        return False

    manifest_path.write_text(new_manifest, encoding="utf-8")
    return True


# -------------------------------------------------------------------------
# Docker auto-fix dispatch loop
# -------------------------------------------------------------------------

# Additional keyword patterns for pylint-reported unused imports
_DOCKER_UNUSED_IMPORT_KEYWORDS: tuple[str, ...] = (
    "unused-import",
    "unused import",
    "w0611",
)


def _dispatch_docker_fix(
    module_path: Path,
    error_output: str,
) -> bool:
    """Dispatch a single Docker fix based on error pattern identification.

    Internal helper used by run_docker_fix_loop. Identifies the error pattern
    and dispatches to the appropriate fix function.

    Args:
        module_path: Root path of the Odoo module.
        error_output: The error text from Docker validation.

    Returns:
        True if a fix was applied, False otherwise.
    """
    import logging

    logger = logging.getLogger(__name__)

    if not error_output or not error_output.strip():
        return False

    # Check for unused-import pattern first (not in Docker patterns)
    error_lower = error_output.lower()
    if any(kw in error_lower for kw in _DOCKER_UNUSED_IMPORT_KEYWORDS):
        logger.info("run_docker_fix_loop: detected unused-import pattern")
        models_dir = module_path / "models"
        if models_dir.is_dir():
            applied = False
            for py_file in sorted(models_dir.glob("*.py")):
                if py_file.name == "__init__.py":
                    continue
                if fix_unused_imports(py_file):
                    logger.info("run_docker_fix_loop: fixed unused imports in %s", py_file)
                    applied = True
            if applied:
                return True

    # Standard Docker pattern identification
    pattern_id = identify_docker_fix(error_output)

    if pattern_id is None:
        logger.debug("run_docker_fix_loop: no fixable pattern identified")
        return False

    logger.info("run_docker_fix_loop: detected pattern '%s'", pattern_id)

    # Dispatch dict: pattern_id -> (fix_function, needs_error_output)
    # missing_mail_thread only needs module_path; the 3 new functions
    # also need error_output for context-aware fixing.
    dispatch: dict[str, tuple[object, bool]] = {
        "xml_parse_error": (fix_xml_parse_error, True),
        "missing_acl": (fix_missing_acl, True),
        "manifest_load_order": (fix_manifest_load_order, True),
        "missing_mail_thread": (fix_missing_mail_thread, False),
    }

    entry = dispatch.get(pattern_id)
    if entry is None:
        logger.debug("run_docker_fix_loop: no fix function for pattern '%s'", pattern_id)
        return False

    fix_func, needs_error = entry
    if needs_error:
        result = fix_func(module_path, error_output)  # type: ignore[operator]
    else:
        result = fix_func(module_path)  # type: ignore[operator]
    logger.info("run_docker_fix_loop: fix for '%s' returned %s", pattern_id, result)
    return result


def run_docker_fix_loop(
    module_path: Path,
    error_output: str,
    max_iterations: int = DEFAULT_MAX_FIX_ITERATIONS,
    revalidate_fn: object | None = None,
) -> tuple[bool, str]:
    """Run Docker error fixes in a loop with configurable iteration cap.

    Each iteration: identify error pattern -> dispatch fix -> if fix applied
    and revalidate_fn provided, call it to get new error_output -> repeat.
    If no revalidate_fn, runs a single pass.

    Args:
        module_path: Root path of the Odoo module.
        error_output: The error text from Docker validation.
        max_iterations: Maximum fix iterations (default 5).
        revalidate_fn: Optional callable returning InstallResult for re-validation.
            When provided, enables multi-iteration fixing.

    Returns:
        Tuple of (any_fix_applied, remaining_error_output).
        When iteration cap is reached, remaining output includes escalation message.
    """
    import logging

    logger = logging.getLogger(__name__)

    any_fix_applied = False
    current_error = error_output

    for iteration in range(max_iterations):
        logger.debug("run_docker_fix_loop: iteration %d/%d", iteration + 1, max_iterations)

        fixed = _dispatch_docker_fix(module_path, current_error)

        if not fixed:
            logger.debug("run_docker_fix_loop: no fix applied in iteration %d", iteration + 1)
            break

        any_fix_applied = True

        if revalidate_fn is None:
            # Single-pass mode (no re-validation)
            break

        # Re-validate to get new error output
        revalidation_result = revalidate_fn()  # type: ignore[operator]
        if revalidation_result.success:
            logger.info("run_docker_fix_loop: re-validation succeeded after iteration %d", iteration + 1)
            current_error = ""
            break

        current_error = revalidation_result.log_output or revalidation_result.error_message
        if not current_error or not current_error.strip():
            break
    else:
        # Loop completed without breaking -> cap reached
        if any_fix_applied and revalidate_fn is not None:
            cap_msg = (
                f"Iteration cap ({max_iterations}) reached. "
                "Remaining errors require manual review."
            )
            current_error = f"{current_error}\n{cap_msg}" if current_error else cap_msg
            logger.warning("run_docker_fix_loop: %s", cap_msg)

    return any_fix_applied, current_error


# -------------------------------------------------------------------------
# Module-level auto-fix: unused imports (AFIX-02)
# -------------------------------------------------------------------------

# Known import names to check for usage -- targeted at template patterns
_IMPORT_USAGE_PATTERNS: dict[str, tuple[str, ...]] = {
    "api": ("@api.", "api."),
    "ValidationError": ("ValidationError",),
    "AccessError": ("AccessError",),
    "_": ("_(",),
}


def fix_unused_imports(file_path: Path) -> bool:
    """Detect and remove unused imports in a generated Python file.

    Targeted at common template patterns: unused ValidationError, unused api,
    unused _. Uses AST to find import statements, then scans file text for
    usage of each imported name.

    Args:
        file_path: Path to the Python file to check.

    Returns:
        True if any imports were removed, False if no changes needed.
    """
    content = file_path.read_text(encoding="utf-8")
    if not content.strip():
        return False

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False

    changes_made = False
    lines = content.split("\n")

    # Process import statements in reverse order to preserve line numbers
    import_nodes: list[ast.ImportFrom] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            import_nodes.append(node)

    # Sort by line number descending so we can modify lines without shifting
    import_nodes.sort(key=lambda n: n.lineno, reverse=True)

    for node in import_nodes:
        if not node.names:
            continue

        line_idx = node.lineno - 1
        if line_idx < 0 or line_idx >= len(lines):
            continue

        original_line = lines[line_idx]

        # Build the text after import lines (everything except the import line itself)
        # to check for usage
        text_after_import = "\n".join(
            line for i, line in enumerate(lines) if i != line_idx
        )

        names_to_keep: list[str] = []
        names_to_remove: list[str] = []

        for alias in node.names:
            name = alias.asname if alias.asname else alias.name

            # Check usage: look for the name in the rest of the file
            if name in _IMPORT_USAGE_PATTERNS:
                patterns = _IMPORT_USAGE_PATTERNS[name]
                is_used = any(pattern in text_after_import for pattern in patterns)
            else:
                # For unknown names, assume used (conservative)
                is_used = True

            if is_used:
                names_to_keep.append(name)
            else:
                names_to_remove.append(name)

        if not names_to_remove:
            continue

        changes_made = True

        if not names_to_keep:
            # Remove the entire import line
            lines[line_idx] = ""
        else:
            # Rebuild the import line with only kept names
            module = node.module or ""
            new_import = f"from {module} import {', '.join(names_to_keep)}"
            # Preserve leading indentation
            leading_space = ""
            for ch in original_line:
                if ch in (" ", "\t"):
                    leading_space += ch
                else:
                    break
            lines[line_idx] = leading_space + new_import

    if not changes_made:
        return False

    # Clean up empty lines left by removed imports (remove consecutive blank lines)
    new_lines: list[str] = []
    prev_empty = False
    for line in lines:
        is_empty = line.strip() == ""
        if is_empty and prev_empty:
            continue
        new_lines.append(line)
        prev_empty = is_empty

    new_content = "\n".join(new_lines)
    file_path.write_text(new_content, encoding="utf-8")
    return True
