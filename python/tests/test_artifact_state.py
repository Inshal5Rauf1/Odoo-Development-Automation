"""Unit tests for artifact state tracker (OBS-01 a-f)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from odoo_gen_utils.artifact_state import (
    ArtifactKind,
    ArtifactState,
    ArtifactStatus,
    ModuleState,
    format_state_table,
    load_state,
    save_state,
)


# ---------------------------------------------------------------------------
# Enum value tests
# ---------------------------------------------------------------------------


class TestArtifactKind:
    """Tests for ArtifactKind enum values."""

    def test_artifact_kind_values(self) -> None:
        """ArtifactKind has model, view, security, test, manifest, data values."""
        expected = {"model", "view", "security", "test", "manifest", "data"}
        actual = {kind.value for kind in ArtifactKind}
        assert actual == expected


class TestArtifactStatus:
    """Tests for ArtifactStatus enum values."""

    def test_artifact_status_values(self) -> None:
        """ArtifactStatus has pending, generated, validated, approved values."""
        expected = {"pending", "generated", "validated", "approved"}
        actual = {status.value for status in ArtifactStatus}
        assert actual == expected


# ---------------------------------------------------------------------------
# ArtifactState frozen dataclass tests
# ---------------------------------------------------------------------------


class TestArtifactState:
    """Tests for ArtifactState frozen dataclass."""

    def test_artifact_state_frozen(self) -> None:
        """ArtifactState is immutable (frozen dataclass)."""
        state = ArtifactState(
            kind="model",
            name="library.book",
            file_path="models/library_book.py",
            status="generated",
            updated_at="2026-03-04T18:30:00+00:00",
        )
        with pytest.raises(AttributeError):
            state.status = "validated"  # type: ignore[misc]

    def test_artifact_state_default_error(self) -> None:
        """ArtifactState error defaults to empty string."""
        state = ArtifactState(
            kind="model",
            name="library.book",
            file_path="models/library_book.py",
            status="generated",
            updated_at="2026-03-04T18:30:00+00:00",
        )
        assert state.error == ""


# ---------------------------------------------------------------------------
# ModuleState transition tests
# ---------------------------------------------------------------------------


class TestModuleStateTransition:
    """Tests for ModuleState.transition() method."""

    def test_module_state_transition_adds_new(self) -> None:
        """ModuleState.transition() adds a new artifact when none exists with that kind+name."""
        ms = ModuleState(module_name="library_management")
        new_ms = ms.transition(
            kind="model",
            name="library.book",
            file_path="models/library_book.py",
            new_status="pending",
        )
        assert len(new_ms.artifacts) == 1
        assert new_ms.artifacts[0].kind == "model"
        assert new_ms.artifacts[0].name == "library.book"
        assert new_ms.artifacts[0].status == "pending"

    def test_module_state_transition_replaces_existing(self) -> None:
        """ModuleState.transition() replaces artifact with same kind+name (immutable -- returns new ModuleState)."""
        ms = ModuleState(
            module_name="library_management",
            artifacts=[
                ArtifactState(
                    kind="model",
                    name="library.book",
                    file_path="models/library_book.py",
                    status="pending",
                    updated_at="2026-03-04T18:00:00+00:00",
                ),
            ],
        )
        new_ms = ms.transition(
            kind="model",
            name="library.book",
            file_path="models/library_book.py",
            new_status="generated",
        )
        # Original unchanged
        assert ms.artifacts[0].status == "pending"
        # New state has updated status
        assert len(new_ms.artifacts) == 1
        assert new_ms.artifacts[0].status == "generated"

    def test_module_state_transition_preserves_others(self) -> None:
        """transition() keeps other artifacts unchanged."""
        ms = ModuleState(
            module_name="library_management",
            artifacts=[
                ArtifactState(
                    kind="model",
                    name="library.book",
                    file_path="models/library_book.py",
                    status="generated",
                    updated_at="2026-03-04T18:00:00+00:00",
                ),
                ArtifactState(
                    kind="view",
                    name="library.book.form",
                    file_path="views/library_book_views.xml",
                    status="pending",
                    updated_at="2026-03-04T18:00:00+00:00",
                ),
            ],
        )
        new_ms = ms.transition(
            kind="model",
            name="library.book",
            file_path="models/library_book.py",
            new_status="validated",
        )
        assert len(new_ms.artifacts) == 2
        # View artifact unchanged
        view_artifacts = [a for a in new_ms.artifacts if a.kind == "view"]
        assert len(view_artifacts) == 1
        assert view_artifacts[0].status == "pending"

    def test_module_state_transition_sets_timestamp(self) -> None:
        """transition() sets updated_at to ISO 8601 UTC timestamp."""
        ms = ModuleState(module_name="library_management")
        fixed_dt = "2026-03-04T19:00:00+00:00"
        with patch(
            "odoo_gen_utils.artifact_state.datetime"
        ) as mock_dt:
            mock_dt.now.return_value.isoformat.return_value = fixed_dt
            new_ms = ms.transition(
                kind="model",
                name="library.book",
                file_path="models/library_book.py",
                new_status="pending",
            )
        assert new_ms.artifacts[0].updated_at == fixed_dt

    def test_module_state_transition_with_error(self) -> None:
        """transition() with error string stores it on the ArtifactState."""
        ms = ModuleState(module_name="library_management")
        new_ms = ms.transition(
            kind="model",
            name="library.book",
            file_path="models/library_book.py",
            new_status="generated",
            error="Template rendering failed",
        )
        assert new_ms.artifacts[0].error == "Template rendering failed"

    def test_valid_transitions_warns_on_skip(self, caplog: pytest.LogCaptureFixture) -> None:
        """Transitioning from pending directly to approved logs a warning but succeeds."""
        ms = ModuleState(
            module_name="library_management",
            artifacts=[
                ArtifactState(
                    kind="model",
                    name="library.book",
                    file_path="models/library_book.py",
                    status="pending",
                    updated_at="2026-03-04T18:00:00+00:00",
                ),
            ],
        )
        with caplog.at_level(logging.WARNING, logger="odoo-gen.state"):
            new_ms = ms.transition(
                kind="model",
                name="library.book",
                file_path="models/library_book.py",
                new_status="approved",
            )
        # Transition succeeds despite being invalid
        assert new_ms.artifacts[0].status == "approved"
        # Warning was logged
        assert any("approved" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# save_state / load_state tests
# ---------------------------------------------------------------------------


class TestSaveLoadState:
    """Tests for save_state() and load_state() persistence."""

    def test_save_state_creates_file(self, tmp_path: Path) -> None:
        """save_state() writes .odoo-gen-state.json in module_path."""
        ms = ModuleState(module_name="library_management")
        result_path = save_state(ms, tmp_path)
        assert result_path.exists()
        assert result_path.name == ".odoo-gen-state.json"

    def test_save_state_json_format(self, tmp_path: Path) -> None:
        """Written JSON has module_name and artifacts keys with correct structure."""
        ms = ModuleState(
            module_name="library_management",
            artifacts=[
                ArtifactState(
                    kind="model",
                    name="library.book",
                    file_path="models/library_book.py",
                    status="generated",
                    updated_at="2026-03-04T18:30:00+00:00",
                ),
            ],
        )
        save_state(ms, tmp_path)
        state_file = tmp_path / ".odoo-gen-state.json"
        data = json.loads(state_file.read_text())
        assert "module_name" in data
        assert "artifacts" in data
        assert data["module_name"] == "library_management"
        assert len(data["artifacts"]) == 1
        artifact = data["artifacts"][0]
        assert artifact["kind"] == "model"
        assert artifact["name"] == "library.book"
        assert artifact["file_path"] == "models/library_book.py"
        assert artifact["status"] == "generated"
        assert artifact["updated_at"] == "2026-03-04T18:30:00+00:00"
        assert artifact["error"] == ""

    def test_load_state_roundtrip(self, tmp_path: Path) -> None:
        """save_state() then load_state() returns equivalent ModuleState."""
        original = ModuleState(
            module_name="library_management",
            artifacts=[
                ArtifactState(
                    kind="model",
                    name="library.book",
                    file_path="models/library_book.py",
                    status="generated",
                    updated_at="2026-03-04T18:30:00+00:00",
                ),
                ArtifactState(
                    kind="view",
                    name="library.book.form",
                    file_path="views/library_book_views.xml",
                    status="pending",
                    updated_at="2026-03-04T18:31:00+00:00",
                    error="Missing field",
                ),
            ],
        )
        save_state(original, tmp_path)
        loaded = load_state(tmp_path)
        assert loaded is not None
        assert loaded.module_name == original.module_name
        assert len(loaded.artifacts) == len(original.artifacts)
        for orig, loaded_art in zip(original.artifacts, loaded.artifacts):
            assert orig.kind == loaded_art.kind
            assert orig.name == loaded_art.name
            assert orig.file_path == loaded_art.file_path
            assert orig.status == loaded_art.status
            assert orig.updated_at == loaded_art.updated_at
            assert orig.error == loaded_art.error

    def test_load_state_missing_file(self, tmp_path: Path) -> None:
        """load_state() returns None when no state file exists."""
        result = load_state(tmp_path)
        assert result is None

    def test_load_state_corrupted_json(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load_state() returns None and logs warning when file has invalid JSON."""
        state_file = tmp_path / ".odoo-gen-state.json"
        state_file.write_text("{invalid json content!!")
        with caplog.at_level(logging.WARNING, logger="odoo-gen.state"):
            result = load_state(tmp_path)
        assert result is None
        assert any("warning" in record.levelname.lower() or "corrupt" in record.message.lower() or "parse" in record.message.lower() or "invalid" in record.message.lower() or "error" in record.message.lower() or "failed" in record.message.lower() for record in caplog.records)

    def test_load_state_empty_file(self, tmp_path: Path) -> None:
        """load_state() returns None when file is empty."""
        state_file = tmp_path / ".odoo-gen-state.json"
        state_file.write_text("")
        result = load_state(tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# format_state_table tests
# ---------------------------------------------------------------------------


class TestFormatStateTable:
    """Tests for format_state_table() display formatting."""

    def test_format_state_table_output(self) -> None:
        """format_state_table() returns formatted string with status icons [ ], [G], [V], [A]."""
        ms = ModuleState(
            module_name="library_management",
            artifacts=[
                ArtifactState(
                    kind="model",
                    name="library.book",
                    file_path="models/library_book.py",
                    status="pending",
                    updated_at="2026-03-04T18:00:00+00:00",
                ),
                ArtifactState(
                    kind="view",
                    name="library.book.form",
                    file_path="views/library_book_views.xml",
                    status="generated",
                    updated_at="2026-03-04T18:01:00+00:00",
                ),
                ArtifactState(
                    kind="security",
                    name="ir.model.access",
                    file_path="security/ir.model.access.csv",
                    status="validated",
                    updated_at="2026-03-04T18:02:00+00:00",
                ),
                ArtifactState(
                    kind="test",
                    name="test_library",
                    file_path="tests/test_library.py",
                    status="approved",
                    updated_at="2026-03-04T18:03:00+00:00",
                ),
            ],
        )
        output = format_state_table(ms)
        assert "[ ]" in output  # pending
        assert "[G]" in output  # generated
        assert "[V]" in output  # validated
        assert "[A]" in output  # approved
        assert "library.book" in output
        assert "library_management" in output

    def test_format_state_table_with_errors(self) -> None:
        """format_state_table() includes ERROR lines for artifacts with error field."""
        ms = ModuleState(
            module_name="library_management",
            artifacts=[
                ArtifactState(
                    kind="model",
                    name="library.book",
                    file_path="models/library_book.py",
                    status="generated",
                    updated_at="2026-03-04T18:00:00+00:00",
                    error="Template rendering failed",
                ),
            ],
        )
        output = format_state_table(ms)
        assert "ERROR" in output
        assert "Template rendering failed" in output

    def test_format_state_table_empty(self) -> None:
        """format_state_table() handles ModuleState with no artifacts."""
        ms = ModuleState(module_name="library_management")
        output = format_state_table(ms)
        assert "library_management" in output
        # Should not crash
        assert isinstance(output, str)


# ---------------------------------------------------------------------------
# Integration tests: render_module emits artifact states
# ---------------------------------------------------------------------------


class TestRenderModuleStateIntegration:
    """Integration tests: render_module emits artifact states."""

    def test_render_module_creates_state_file(self, tmp_path: Path) -> None:
        """render_module() creates .odoo-gen-state.json sidecar."""
        spec = {
            "module_name": "test_state_mod",
            "models": [{"name": "test.model", "fields": []}],
        }
        from odoo_gen_utils.renderer import get_template_dir, render_module

        template_dir = get_template_dir()
        files, warnings = render_module(spec, template_dir, tmp_path)
        state_file = tmp_path / "test_state_mod" / ".odoo-gen-state.json"
        assert state_file.exists(), "State sidecar file should be created"
        data = json.loads(state_file.read_text())
        assert data["module_name"] == "test_state_mod"
        assert len(data["artifacts"]) > 0
        # Check at least model and manifest artifacts tracked
        kinds = {a["kind"] for a in data["artifacts"]}
        assert "model" in kinds
        assert "manifest" in kinds

    def test_render_module_state_failure_does_not_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If state tracking fails, render_module still succeeds."""
        import odoo_gen_utils.artifact_state as ast_mod

        def _exploding_transition(self: object, *args: object, **kwargs: object) -> None:
            raise RuntimeError("State tracking exploded")

        monkeypatch.setattr(ast_mod.ModuleState, "transition", _exploding_transition)

        spec = {
            "module_name": "test_no_block",
            "models": [{"name": "test.model", "fields": []}],
        }
        from odoo_gen_utils.renderer import get_template_dir, render_module

        template_dir = get_template_dir()
        # Must not raise
        files, warnings = render_module(spec, template_dir, tmp_path)
        assert len(files) > 0, "Module files should still be created"
