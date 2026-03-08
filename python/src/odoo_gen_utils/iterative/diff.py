"""Spec stash management and diff orchestration for iterative refinement.

Stub — not yet implemented.
"""

from __future__ import annotations

from pathlib import Path

SPEC_STASH_FILENAME = ".odoo-gen-spec.json"


def save_spec_stash(spec: dict, module_path: Path) -> Path:
    raise NotImplementedError


def load_spec_stash(module_path: Path) -> dict | None:
    raise NotImplementedError


def compute_spec_diff(old_spec: dict, new_spec: dict):
    raise NotImplementedError
