"""
Model registry for tracking saved model artifacts.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config
from core.schemas import ModelArtifact, ModelType


class ModelRegistry:
    """
    Registry for managing model artifacts.
    Persists metadata to JSON file.
    """

    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize registry.

        Args:
            registry_path: Path to registry JSON file (default: from config)
        """
        self.registry_path = registry_path or Config.MODEL_REGISTRY_PATH
        self._artifacts: dict[str, ModelArtifact] = {}
        self._load()

    def _load(self) -> None:
        """Load registry from disk."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._artifacts = {
                        aid: ModelArtifact.model_validate(record)
                        for aid, record in data.items()
                    }
            except Exception as e:
                print(f"Warning: Failed to load model registry: {e}")
                self._artifacts = {}
        else:
            self._artifacts = {}

    def _save(self) -> None:
        """Save registry to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w", encoding="utf-8") as f:
            data = {
                aid: artifact.model_dump(mode="json")
                for aid, artifact in self._artifacts.items()
            }
            json.dump(data, f, indent=2, default=str)

    def register(self, artifact: ModelArtifact) -> None:
        """
        Register a new or updated model artifact.

        Args:
            artifact: Model artifact to register
        """
        self._artifacts[artifact.artifact_id] = artifact
        self._save()

    def get(self, artifact_id: str) -> Optional[ModelArtifact]:
        """
        Get artifact by ID.

        Args:
            artifact_id: Artifact identifier

        Returns:
            ModelArtifact if found, None otherwise
        """
        return self._artifacts.get(artifact_id)

    def list_all(self) -> list[ModelArtifact]:
        """
        List all registered artifacts.

        Returns:
            List of all model artifacts
        """
        return list(self._artifacts.values())

    def list_by_symbol(self, symbol: str) -> list[ModelArtifact]:
        """
        List artifacts covering a specific symbol.

        Args:
            symbol: Stock symbol

        Returns:
            List of artifacts that cover this symbol
        """
        symbol = symbol.upper()
        return [
            artifact
            for artifact in self._artifacts.values()
            if symbol in artifact.covered_symbols
        ]

    def list_by_type(self, model_type: ModelType) -> list[ModelArtifact]:
        """
        List artifacts of a specific type.

        Args:
            model_type: Model training type

        Returns:
            List of artifacts of this type
        """
        return [
            artifact
            for artifact in self._artifacts.values()
            if artifact.type == model_type
        ]

    def get_latest_for_symbol(
        self, symbol: str, model_type: Optional[ModelType] = None
    ) -> Optional[ModelArtifact]:
        """
        Get most recently trained model for a symbol.

        Args:
            symbol: Stock symbol
            model_type: Optional filter by model type

        Returns:
            Most recent artifact if found, None otherwise
        """
        candidates = self.list_by_symbol(symbol)
        if model_type:
            candidates = [a for a in candidates if a.type == model_type]

        if not candidates:
            return None

        return max(candidates, key=lambda a: a.last_trained_at)

    def delete(self, artifact_id: str) -> bool:
        """
        Remove artifact from registry.

        Args:
            artifact_id: Artifact identifier

        Returns:
            True if deleted, False if not found
        """
        if artifact_id in self._artifacts:
            del self._artifacts[artifact_id]
            self._save()
            return True
        return False


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """Get global model registry instance."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
