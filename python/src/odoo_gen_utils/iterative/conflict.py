"""Three-way conflict detection for iterative refinement.

Stub -- not yet implemented.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_gen_utils.manifest import GenerationManifest


@dataclass(frozen=True)
class ConflictResult:
    safe_to_overwrite: tuple[str, ...]
    conflicts: tuple[str, ...]
    stub_mergeable: tuple[str, ...]


def detect_conflicts(
    manifest: "GenerationManifest",
    affected_files: list[str],
    module_dir: Path,
    skeleton_dir: Path | None = None,
) -> ConflictResult:
    raise NotImplementedError
