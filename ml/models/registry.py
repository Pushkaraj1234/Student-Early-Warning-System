"""File-based model registry: ``<root>/<model_version>/{model.joblib, metadata.json}`` plus an
``active_model.json`` pointer naming the version used when a request does not specify one."""

from __future__ import annotations

import json
from pathlib import Path

from ml.models.artifact import MODEL_VERSION_RE, ArtifactError, ModelArtifact

ACTIVE_FILE = "active_model.json"


class InvalidModelVersionError(ValueError):
    """The model version string is not a valid identifier."""


class ModelNotFoundError(LookupError):
    """No artifact exists for the requested model version."""


class ModelRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._cache: dict[str, ModelArtifact] = {}

    def path_for(self, model_version: str) -> Path:
        if not isinstance(model_version, str) or not MODEL_VERSION_RE.fullmatch(model_version):
            raise InvalidModelVersionError(f"invalid model version: {model_version!r}")
        return self.root / model_version

    def available_versions(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(
            p.name
            for p in self.root.iterdir()
            if p.is_dir() and MODEL_VERSION_RE.fullmatch(p.name) and (p / "metadata.json").is_file()
        )

    def active_version(self) -> str:
        pointer = self.root / ACTIVE_FILE
        if not pointer.is_file():
            raise ModelNotFoundError("no active model has been set")
        try:
            version = json.loads(pointer.read_text(encoding="utf-8"))["model_version"]
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ModelNotFoundError(f"invalid active model pointer: {exc}") from exc
        self.path_for(version)
        return str(version)

    def set_active(self, model_version: str) -> None:
        if not (self.path_for(model_version) / "metadata.json").is_file():
            raise ModelNotFoundError(f"model version not found: {model_version}")
        (self.root / ACTIVE_FILE).write_text(
            json.dumps({"model_version": model_version}, indent=2), encoding="utf-8"
        )

    def load(self, model_version: str) -> ModelArtifact:
        """Load (and cache) an artifact. Raises InvalidModelVersionError / ModelNotFoundError /
        ArtifactError."""
        path = self.path_for(model_version)
        if model_version in self._cache:
            return self._cache[model_version]
        if not path.is_dir():
            raise ModelNotFoundError(f"model version not found: {model_version}")
        artifact = ModelArtifact.load(path)
        if artifact.metadata.model_version != model_version:
            raise ArtifactError("artifact directory name does not match its metadata model_version")
        self._cache[model_version] = artifact
        return artifact
