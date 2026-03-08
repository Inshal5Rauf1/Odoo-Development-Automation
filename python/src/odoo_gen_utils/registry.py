"""Model registry for cross-module model awareness.

Tracks all generated models across modules in a JSON registry,
enabling comodel validation and ``depends`` inference without
requiring a running Odoo instance.

Registry operations live in the CLI layer -- ``render_module()``
has no knowledge of the registry.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelEntry:
    """A single model stored in the registry."""

    module: str
    fields: dict[str, Any]
    inherits: list[str] = field(default_factory=list)
    mixins: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class ValidationResult:
    """Aggregated validation output with three severity tiers."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_RELATIONAL_TYPES = frozenset({"Many2one", "One2many", "Many2many"})


class ModelRegistry:
    """Central model registry for cross-module awareness.

    Persists to a JSON file with three top-level sections:
    ``_meta``, ``models``, and ``dependency_graph``.
    """

    def __init__(self, registry_path: Path) -> None:
        self._path = registry_path
        self._meta: dict[str, Any] = {
            "version": "1.0",
            "last_updated": "",
            "odoo_version": "17.0",
            "modules_registered": 0,
        }
        self._models: dict[str, ModelEntry] = {}
        self._dependency_graph: dict[str, list[str]] = {}
        self._known_models: dict[str, dict[str, Any]] = {}

    # -- Persistence --------------------------------------------------------

    def load(self) -> None:
        """Load registry from JSON file.  No-op if file does not exist."""
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text(encoding="utf-8"))
        self._meta = data.get("_meta", self._meta)
        raw_models = data.get("models", {})
        self._models = {
            name: ModelEntry(
                module=entry["module"],
                fields=entry.get("fields", {}),
                inherits=entry.get("inherits", []),
                mixins=entry.get("mixins", []),
                description=entry.get("description", ""),
            )
            for name, entry in raw_models.items()
        }
        self._dependency_graph = data.get("dependency_graph", {})

    def save(self) -> None:
        """Persist current state to the JSON file."""
        self._meta["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._meta["modules_registered"] = len(self._dependency_graph)
        payload = {
            "_meta": self._meta,
            "models": {name: asdict(entry) for name, entry in self._models.items()},
            "dependency_graph": self._dependency_graph,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # -- Known models -------------------------------------------------------

    def load_known_models(self) -> None:
        """Load the shipped ``known_odoo_models.json`` into memory."""
        data_path = Path(__file__).parent / "data" / "known_odoo_models.json"
        data = json.loads(data_path.read_text(encoding="utf-8"))
        self._known_models = data.get("models", {})

    # -- Module operations --------------------------------------------------

    def register_module(self, module_name: str, spec: dict[str, Any]) -> list[str]:
        """Extract models from *spec* and store them.

        Returns a list of INFO-level messages (e.g. overwrite notices).
        Overwrites all existing entries for *module_name*.
        """
        info_messages: list[str] = []

        # Remove previous entries for this module (overwrite, not merge)
        existing_models = [
            name for name, entry in self._models.items() if entry.module == module_name
        ]
        if existing_models:
            info_messages.append(
                f"INFO: Overwriting {len(existing_models)} model(s) for module '{module_name}'"
            )
            for name in existing_models:
                del self._models[name]

        # Register each model from the spec
        for model in spec.get("models", []):
            model_name: str = model["_name"]
            inherits = model.get("_inherit", [])
            if isinstance(inherits, str):
                inherits = [inherits]

            # Separate mixins from regular inherits
            mixins = [
                inh
                for inh in inherits
                if self._known_models.get(inh, {}).get("is_mixin", False)
            ]
            non_mixin_inherits = [inh for inh in inherits if inh not in mixins]

            self._models[model_name] = ModelEntry(
                module=module_name,
                fields=model.get("fields", {}),
                inherits=non_mixin_inherits,
                mixins=mixins,
                description=model.get("description", ""),
            )

        # Update dependency graph
        self._dependency_graph[module_name] = list(spec.get("depends", []))
        return info_messages

    def remove_module(self, module_name: str) -> None:
        """Remove all models belonging to *module_name*.  No-op if absent."""
        models_to_remove = [
            name for name, entry in self._models.items() if entry.module == module_name
        ]
        for name in models_to_remove:
            del self._models[name]
        self._dependency_graph.pop(module_name, None)

    # -- Validation ---------------------------------------------------------

    def validate_comodels(self, spec: dict[str, Any]) -> ValidationResult:
        """Validate comodel references, inherits, and duplicates.

        Returns a :class:`ValidationResult` with errors, warnings, info.
        """
        result = ValidationResult()
        seen_names: list[str] = []

        for model in spec.get("models", []):
            model_name: str = model["_name"]

            # Duplicate _name check
            if model_name in seen_names:
                result.errors.append(
                    f"ERROR: Duplicate model _name '{model_name}' within module"
                )
            seen_names.append(model_name)

            # Self-inherit check
            inherits = model.get("_inherit", [])
            if isinstance(inherits, str):
                inherits = [inherits]
            if model_name in inherits:
                result.errors.append(
                    f"ERROR: Model '{model_name}' inherits from itself"
                )

            # Comodel validation for relational fields
            for field_name, field_def in model.get("fields", {}).items():
                ftype = field_def.get("type", "")
                comodel = field_def.get("comodel_name")
                if ftype in _RELATIONAL_TYPES and comodel:
                    if not self._is_known_model(comodel, spec):
                        result.warnings.append(
                            f"WARNING: comodel '{comodel}' (field '{model_name}.{field_name}') "
                            f"not in registry or known Odoo models"
                        )

        return result

    def _is_known_model(self, model_name: str, spec: dict[str, Any]) -> bool:
        """Check if *model_name* exists in known models, registry, or current spec."""
        if model_name in self._known_models:
            return True
        if model_name in self._models:
            return True
        # Check models being defined in the current spec
        for model in spec.get("models", []):
            if model["_name"] == model_name:
                return True
        return False

    # -- Depends inference --------------------------------------------------

    def infer_depends(self, spec: dict[str, Any]) -> list[str]:
        """Infer module dependencies from comodel/inherit references.

        Returns module names NOT already in ``spec['depends']``.
        """
        explicit = set(spec.get("depends", []))
        inferred: set[str] = set()

        for model in spec.get("models", []):
            # From inherits / mixins
            inherits = model.get("_inherit", [])
            if isinstance(inherits, str):
                inherits = [inherits]
            for inh in inherits:
                owner = self._find_owning_module(inh)
                if owner and owner not in explicit:
                    inferred.add(owner)

            # From relational field comodels
            for _field_name, field_def in model.get("fields", {}).items():
                ftype = field_def.get("type", "")
                comodel = field_def.get("comodel_name")
                if ftype in _RELATIONAL_TYPES and comodel:
                    owner = self._find_owning_module(comodel)
                    if owner and owner not in explicit:
                        inferred.add(owner)

        return sorted(inferred)

    def _find_owning_module(self, model_name: str) -> str | None:
        """Return the module that owns *model_name*, or ``None``."""
        known = self._known_models.get(model_name)
        if known:
            return known["module"]
        registered = self._models.get(model_name)
        if registered:
            return registered.module
        return None

    # -- Cycle detection ----------------------------------------------------

    def detect_cycles(self) -> list[str]:
        """Detect circular dependencies in the module dependency graph.

        Returns a list of error messages (empty if no cycles).
        Uses :class:`graphlib.TopologicalSorter`.
        """
        graph: dict[str, set[str]] = {
            mod: set(deps) for mod, deps in self._dependency_graph.items()
        }
        try:
            ts = TopologicalSorter(graph)
            list(ts.static_order())
        except CycleError as exc:
            cycle_nodes = exc.args[1]
            cycle_str = " -> ".join(str(n) for n in cycle_nodes)
            return [
                f"ERROR: Circular dependency detected: {cycle_str}. "
                f"Break the cycle by removing one dependency."
            ]
        return []

    # -- Query helpers ------------------------------------------------------

    def list_modules(self) -> dict[str, list[str]]:
        """Return ``{module_name: [model_names]}``."""
        result: dict[str, list[str]] = {}
        for model_name, entry in self._models.items():
            result.setdefault(entry.module, []).append(model_name)
        return result

    def show_model(self, model_name: str) -> ModelEntry | None:
        """Look up a model by name.  Returns ``None`` if not found."""
        return self._models.get(model_name)
