"""Diff-to-stage mapping for iterative refinement.

Stub — not yet implemented.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AffectedStages:
    stages: frozenset[str]
    diff_summary: dict


def determine_affected_stages(spec_diff) -> AffectedStages:
    raise NotImplementedError
