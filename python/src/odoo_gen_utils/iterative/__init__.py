"""Iterative refinement subpackage for spec change detection and safe re-generation.

Provides:
- Spec stash management (save/load .odoo-gen-spec.json)
- Spec diff orchestration (compute_spec_diff)
- Diff-to-stage mapping (determine_affected_stages, AffectedStages)
"""

from odoo_gen_utils.iterative.diff import (
    compute_spec_diff,
    load_spec_stash,
    save_spec_stash,
)
from odoo_gen_utils.iterative.affected import (
    AffectedStages,
    determine_affected_stages,
)

__all__ = [
    "save_spec_stash",
    "load_spec_stash",
    "compute_spec_diff",
    "determine_affected_stages",
    "AffectedStages",
]
