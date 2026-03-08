"""Unit tests for odoo_gen_utils.manifest module.

Tests cover: Pydantic models (StageResult, ArtifactEntry, GenerationManifest),
SHA256 helpers, manifest persistence (save/load), and GenerationSession.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# TestStageResult
# ---------------------------------------------------------------------------


class TestStageResult:
    """StageResult Pydantic model tests."""

    def test_round_trip_complete(self):
        """StageResult with status='complete' round-trips through dump/validate."""
        from odoo_gen_utils.manifest import StageResult

        original = StageResult(status="complete", duration_ms=42)
        data = original.model_dump()
        restored = StageResult.model_validate(data)
        assert restored.status == "complete"
        assert restored.duration_ms == 42

    def test_default_status_pending(self):
        """Default status is 'pending'."""
        from odoo_gen_utils.manifest import StageResult

        result = StageResult()
        assert result.status == "pending"
        assert result.duration_ms == 0

    def test_invalid_status_rejected(self):
        """Literal validation rejects invalid status like 'bogus'."""
        from odoo_gen_utils.manifest import StageResult

        with pytest.raises(ValidationError):
            StageResult(status="bogus")

    def test_optional_fields(self):
        """Reason and error are optional (None by default)."""
        from odoo_gen_utils.manifest import StageResult

        result = StageResult(status="failed", error="Something broke")
        assert result.error == "Something broke"
        assert result.reason is None

    def test_artifacts_default_empty(self):
        """Artifacts list defaults to empty."""
        from odoo_gen_utils.manifest import StageResult

        result = StageResult()
        assert result.artifacts == []

    def test_artifacts_stores_paths(self):
        """Artifacts list stores relative paths."""
        from odoo_gen_utils.manifest import StageResult

        result = StageResult(status="complete", artifacts=["models/foo.py", "views/bar.xml"])
        assert len(result.artifacts) == 2
        assert "models/foo.py" in result.artifacts


# ---------------------------------------------------------------------------
# TestArtifactEntry
# ---------------------------------------------------------------------------


class TestArtifactEntry:
    """ArtifactEntry Pydantic model tests."""

    def test_round_trip(self):
        """ArtifactEntry round-trips through dump/validate."""
        from odoo_gen_utils.manifest import ArtifactEntry

        entry = ArtifactEntry(path="models/foo.py", sha256="abc123")
        data = entry.model_dump()
        restored = ArtifactEntry.model_validate(data)
        assert restored.path == "models/foo.py"
        assert restored.sha256 == "abc123"

    def test_both_fields_required(self):
        """Both path and sha256 are required -- ValidationError on missing."""
        from odoo_gen_utils.manifest import ArtifactEntry

        with pytest.raises(ValidationError):
            ArtifactEntry(path="models/foo.py")

        with pytest.raises(ValidationError):
            ArtifactEntry(sha256="abc123")

        with pytest.raises(ValidationError):
            ArtifactEntry()


# ---------------------------------------------------------------------------
# TestGenerationManifest
# ---------------------------------------------------------------------------


class TestGenerationManifest:
    """GenerationManifest Pydantic model tests."""

    def test_full_manifest_round_trip(self):
        """Full manifest with nested models round-trips through dump/validate."""
        from odoo_gen_utils.manifest import (
            ArtifactEntry,
            ArtifactInfo,
            GenerationManifest,
            PreprocessingInfo,
            StageResult,
            ValidationInfo,
        )

        manifest = GenerationManifest(
            module="my_module",
            spec_sha256="deadbeef",
            generated_at="2026-03-08T12:00:00Z",
            generator_version="0.1.0",
            preprocessing=PreprocessingInfo(
                preprocessors_run=["normalize:10", "validate:20"],
                duration_ms=50,
            ),
            stages={
                "models": StageResult(status="complete", duration_ms=100),
                "views": StageResult(status="skipped", reason="no views defined"),
            },
            artifacts=ArtifactInfo(
                files=[ArtifactEntry(path="models/foo.py", sha256="abc123")],
                total_files=1,
                total_lines=42,
            ),
            validation=ValidationInfo(semantic_errors=0, semantic_warnings=1, duration_ms=10),
            models_registered=["my.model"],
        )

        data = manifest.model_dump()
        restored = GenerationManifest.model_validate(data)
        assert restored.module == "my_module"
        assert restored.stages["models"].status == "complete"
        assert restored.artifacts.files[0].path == "models/foo.py"
        assert restored.validation.semantic_warnings == 1
        assert restored.models_registered == ["my.model"]

    def test_exclude_none_omits_none_fields(self):
        """exclude_none=True omits None fields from dump."""
        from odoo_gen_utils.manifest import GenerationManifest

        manifest = GenerationManifest(
            module="test",
            spec_sha256="abc",
            generated_at="2026-01-01T00:00:00Z",
            generator_version="0.1.0",
        )
        data = manifest.model_dump(exclude_none=True)
        assert "validation" not in data

    def test_protected_namespaces_set(self):
        """All models use ConfigDict(protected_namespaces=())."""
        from odoo_gen_utils.manifest import (
            ArtifactEntry,
            ArtifactInfo,
            GenerationManifest,
            PreprocessingInfo,
            StageResult,
            ValidationInfo,
        )

        for model_cls in [
            StageResult,
            ArtifactEntry,
            PreprocessingInfo,
            ArtifactInfo,
            ValidationInfo,
            GenerationManifest,
        ]:
            config = model_cls.model_config
            assert config.get("protected_namespaces") == (), (
                f"{model_cls.__name__} missing protected_namespaces=()"
            )


# ---------------------------------------------------------------------------
# TestSHA256
# ---------------------------------------------------------------------------


class TestSHA256:
    """SHA256 helper tests."""

    def test_compute_file_sha256(self, tmp_path: Path):
        """compute_file_sha256 returns expected hex digest for known content."""
        from odoo_gen_utils.manifest import compute_file_sha256

        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello world")
        # Known SHA256 of b"hello world"
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert compute_file_sha256(test_file) == expected

    def test_compute_spec_sha256_canonical(self):
        """compute_spec_sha256 returns same hash regardless of key order or whitespace."""
        from odoo_gen_utils.manifest import compute_spec_sha256

        spec_a = {"module": "test", "version": "1.0", "models": []}
        spec_b = {"version": "1.0", "models": [], "module": "test"}

        hash_a = compute_spec_sha256(spec_a)
        hash_b = compute_spec_sha256(spec_b)
        assert hash_a == hash_b
        assert len(hash_a) == 64  # SHA256 hex digest length

    def test_compute_spec_sha256_deterministic(self):
        """Same spec dict produces same hash on repeated calls."""
        from odoo_gen_utils.manifest import compute_spec_sha256

        spec = {"module": "my_module", "models": [{"name": "res.partner"}]}
        assert compute_spec_sha256(spec) == compute_spec_sha256(spec)


# ---------------------------------------------------------------------------
# TestManifestPersistence
# ---------------------------------------------------------------------------


class TestManifestPersistence:
    """save_manifest / load_manifest tests."""

    def test_save_and_load_round_trip(self, tmp_path: Path):
        """save_manifest writes file; load_manifest reads back identical manifest."""
        from odoo_gen_utils.manifest import (
            GenerationManifest,
            MANIFEST_FILENAME,
            load_manifest,
            save_manifest,
        )

        original = GenerationManifest(
            module="test_module",
            spec_sha256="abcdef",
            generated_at="2026-01-01T00:00:00Z",
            generator_version="0.1.0",
            models_registered=["test.model"],
        )

        written_path = save_manifest(original, tmp_path)
        assert written_path == tmp_path / MANIFEST_FILENAME
        assert written_path.exists()

        loaded = load_manifest(tmp_path)
        assert loaded is not None
        assert loaded.module == original.module
        assert loaded.spec_sha256 == original.spec_sha256
        assert loaded.models_registered == ["test.model"]

    def test_load_manifest_missing_file(self, tmp_path: Path):
        """load_manifest returns None for missing file."""
        from odoo_gen_utils.manifest import load_manifest

        assert load_manifest(tmp_path) is None

    def test_load_manifest_corrupt_json(self, tmp_path: Path, caplog):
        """load_manifest returns None for corrupt JSON (logs warning)."""
        from odoo_gen_utils.manifest import MANIFEST_FILENAME, load_manifest

        corrupt_file = tmp_path / MANIFEST_FILENAME
        corrupt_file.write_text("{not valid json", encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="odoo-gen.manifest"):
            result = load_manifest(tmp_path)

        assert result is None
        assert any("Failed to parse" in r.message or "corrupt" in r.message.lower() or "Invalid" in r.message for r in caplog.records)

    def test_save_manifest_excludes_none(self, tmp_path: Path):
        """save_manifest uses exclude_none=True so None fields are omitted."""
        from odoo_gen_utils.manifest import (
            GenerationManifest,
            MANIFEST_FILENAME,
            save_manifest,
        )

        manifest = GenerationManifest(
            module="test",
            spec_sha256="abc",
            generated_at="2026-01-01T00:00:00Z",
            generator_version="0.1.0",
        )
        save_manifest(manifest, tmp_path)
        data = json.loads((tmp_path / MANIFEST_FILENAME).read_text(encoding="utf-8"))
        assert "validation" not in data


# ---------------------------------------------------------------------------
# TestGenerationSession
# ---------------------------------------------------------------------------


class TestGenerationSession:
    """GenerationSession dataclass tests."""

    def test_record_stage_stores_result(self):
        """record_stage stores StageResult accessible via to_manifest."""
        from odoo_gen_utils.manifest import GenerationSession, StageResult

        session = GenerationSession(module_name="test", spec_sha256="abc")
        session.record_stage("models", StageResult(status="complete", duration_ms=100))

        manifest = session.to_manifest(generated_at="2026-01-01T00:00:00Z")
        assert "models" in manifest.stages
        assert manifest.stages["models"].status == "complete"

    def test_is_stage_complete_true_only_for_complete(self):
        """is_stage_complete returns True only for status='complete'."""
        from odoo_gen_utils.manifest import GenerationSession, StageResult

        session = GenerationSession(module_name="test", spec_sha256="abc")
        session.record_stage("models", StageResult(status="complete"))
        session.record_stage("views", StageResult(status="skipped"))
        session.record_stage("security", StageResult(status="failed"))

        assert session.is_stage_complete("models") is True
        assert session.is_stage_complete("views") is False
        assert session.is_stage_complete("security") is False
        assert session.is_stage_complete("nonexistent") is False

    def test_to_manifest_produces_valid_manifest(self):
        """to_manifest() produces valid GenerationManifest with all recorded stages."""
        from odoo_gen_utils.manifest import (
            ArtifactInfo,
            GenerationManifest,
            GenerationSession,
            PreprocessingInfo,
            StageResult,
        )

        session = GenerationSession(
            module_name="my_module",
            spec_sha256="deadbeef",
            generator_version="0.1.0",
        )
        session.record_stage("models", StageResult(status="complete", duration_ms=100))
        session.record_stage("views", StageResult(status="complete", duration_ms=50))

        manifest = session.to_manifest(
            generated_at="2026-03-08T12:00:00Z",
            preprocessing=PreprocessingInfo(preprocessors_run=["normalize:10"]),
            artifacts=ArtifactInfo(total_files=5, total_lines=100),
            models_registered=["my.model"],
        )

        assert isinstance(manifest, GenerationManifest)
        assert manifest.module == "my_module"
        assert manifest.spec_sha256 == "deadbeef"
        assert len(manifest.stages) == 2
        assert manifest.preprocessing.preprocessors_run == ["normalize:10"]
        assert manifest.artifacts.total_files == 5
        assert manifest.models_registered == ["my.model"]

    def test_duplicate_record_stage_overwrites(self):
        """Duplicate record_stage for same stage overwrites previous."""
        from odoo_gen_utils.manifest import GenerationSession, StageResult

        session = GenerationSession(module_name="test", spec_sha256="abc")
        session.record_stage("models", StageResult(status="pending"))
        session.record_stage("models", StageResult(status="complete", duration_ms=200))

        manifest = session.to_manifest(generated_at="2026-01-01T00:00:00Z")
        assert manifest.stages["models"].status == "complete"
        assert manifest.stages["models"].duration_ms == 200

    def test_to_manifest_default_generated_at(self):
        """to_manifest() generates ISO 8601 UTC timestamp if not provided."""
        from odoo_gen_utils.manifest import GenerationSession

        session = GenerationSession(module_name="test", spec_sha256="abc")
        manifest = session.to_manifest()
        # Should be an ISO 8601 string
        assert "T" in manifest.generated_at
        assert manifest.generated_at.endswith("Z") or "+" in manifest.generated_at
