"""
Artifact filesystem path utilities.
"""

from pathlib import Path
from datetime import datetime

from core.config import Config


def generate_artifact_id(symbol: str, model_type: str) -> str:
    """
    Generate unique artifact ID.

    Args:
        symbol: Stock symbol (or "federated" for federated models)
        model_type: "per_stock" or "federated"

    Returns:
        Unique artifact ID
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if model_type == "per_stock":
        return f"{symbol.upper()}_{timestamp}"
    else:
        return f"FED_{timestamp}"


def get_model_weights_path(artifact_id: str) -> Path:
    """
    Get path to model weights file.

    Args:
        artifact_id: Artifact identifier

    Returns:
        Path to weights file
    """
    return Config.get_model_path(artifact_id)


def get_model_config_path(artifact_id: str) -> Path:
    """
    Get path to model config JSON.

    Args:
        artifact_id: Artifact identifier

    Returns:
        Path to config file
    """
    return Config.get_model_config_path(artifact_id)


def ensure_model_directory() -> None:
    """Ensure models directory exists."""
    Config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
