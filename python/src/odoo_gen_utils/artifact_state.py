"""Artifact state tracker for the Odoo module generation pipeline.

Tracks each artifact's lifecycle state (pending/generated/validated/approved)
as structured JSON metadata.  State tracking is observability-only and must
never block generation — all I/O operations handle errors gracefully.

Requirement: OBS-01
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

logger = logging.getLogger("odoo-gen.state")

STATE_FILENAME = ".odoo-gen-state.json"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ArtifactKind(str, Enum):
    """Kind of artifact tracked in a module's generation pipeline."""

    MODEL = "model"
    VIEW = "view"
    SECURITY = "security"
    TEST = "test"
    MANIFEST = "manifest"
    DATA = "data"


class ArtifactStatus(str, Enum):
    """Lifecycle status of a generated artifact."""

    PENDING = "pending"
    GENERATED = "generated"
    VALIDATED = "validated"
    APPROVED = "approved"


# Valid transition map — out-of-order transitions log a warning but proceed.
VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["generated"],
    "generated": ["validated", "approved"],
    "validated": ["approved"],
    "approved": [],
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArtifactState:
    """Immutable snapshot of a single artifact's state."""

    kind: str
    name: str
    file_path: str
    status: str
    updated_at: str
    error: str = ""


@dataclass
class ModuleState:
    """Mutable container tracking all artifact states for a module.

    Although the container itself is mutable, ``transition()`` follows an
    immutable pattern — it returns a *new* ``ModuleState`` with the updated
    artifact list and never mutates the current instance.
    """

    module_name: str
    artifacts: list[ArtifactState] = field(default_factory=list)

    def transition(
        self,
        kind: str,
        name: str,
        file_path: str,
        new_status: str,
        error: str = "",
    ) -> ModuleState:
        """Return a new ``ModuleState`` with the artifact transitioned.

        If an artifact with the same *kind* + *name* already exists it is
        replaced; otherwise a new entry is appended.  Invalid transitions
        (e.g. pending -> approved) log a warning but are **not** blocked so
        that state tracking never interferes with generation.
        """
        # Check transition validity for existing artifact
        existing = next(
            (a for a in self.artifacts if a.kind == kind and a.name == name),
            None,
        )
        if existing is not None:
            old_status = existing.status
            allowed = VALID_TRANSITIONS.get(old_status, [])
            if new_status not in allowed:
                logger.warning(
                    "Invalid transition for %s '%s': %s -> %s "
                    "(allowed: %s). Proceeding anyway.",
                    kind,
                    name,
                    old_status,
                    new_status,
                    allowed or "none",
                )

        timestamp = datetime.now(tz=timezone.utc).isoformat()

        new_artifact = ArtifactState(
            kind=kind,
            name=name,
            file_path=file_path,
            status=new_status,
            updated_at=timestamp,
            error=error,
        )

        # Filter out the old entry (if any) and append the new one
        kept = [a for a in self.artifacts if not (a.kind == kind and a.name == name)]
        kept.append(new_artifact)

        return ModuleState(module_name=self.module_name, artifacts=kept)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_state(state: ModuleState, module_path: Path) -> Path:
    """Write *state* as JSON to ``module_path / .odoo-gen-state.json``.

    Returns the path to the written file.
    """
    state_file = module_path / STATE_FILENAME
    data = asdict(state)
    state_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return state_file


def load_state(module_path: Path) -> ModuleState | None:
    """Load a ``ModuleState`` from the JSON sidecar file.

    Returns ``None`` when the file is missing, empty, or contains invalid
    JSON — a warning is logged but no exception is raised.
    """
    state_file = module_path / STATE_FILENAME

    if not state_file.exists():
        return None

    raw = state_file.read_text(encoding="utf-8").strip()
    if not raw:
        logger.warning("State file is empty: %s", state_file)
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse state file %s: %s", state_file, exc)
        return None

    try:
        artifacts = [
            ArtifactState(**artifact_data) for artifact_data in data.get("artifacts", [])
        ]
        return ModuleState(module_name=data["module_name"], artifacts=artifacts)
    except (KeyError, TypeError) as exc:
        logger.warning("Invalid state file structure %s: %s", state_file, exc)
        return None


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

_STATUS_ICONS: dict[str, str] = {
    "pending": "[ ]",
    "generated": "[G]",
    "validated": "[V]",
    "approved": "[A]",
}


def format_state_table(state: ModuleState) -> str:
    """Format artifact states as a human-readable table with status icons.

    Icons: ``[ ]`` pending, ``[G]`` generated, ``[V]`` validated,
    ``[A]`` approved, ``[?]`` unknown.
    """
    lines: list[str] = [f"Module: {state.module_name}", ""]

    if not state.artifacts:
        lines.append("  No artifacts tracked.")
        return "\n".join(lines)

    # Sort by kind for stable output
    sorted_artifacts = sorted(state.artifacts, key=lambda a: a.kind)

    for artifact in sorted_artifacts:
        icon = _STATUS_ICONS.get(artifact.status, "[?]")
        lines.append(f"  {icon} {artifact.kind}: {artifact.name}  ({artifact.file_path})")
        if artifact.error:
            lines.append(f"       ERROR: {artifact.error}")

    return "\n".join(lines)
