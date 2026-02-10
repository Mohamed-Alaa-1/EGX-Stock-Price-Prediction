"""
Application configuration and paths.
"""

from pathlib import Path
from typing import Optional


class Config:
    """Global application configuration."""

    # Project root (parent of src/)
    PROJECT_ROOT = Path(__file__).parent.parent.parent

    # Data directories
    DATA_DIR = PROJECT_ROOT / "data"
    CACHE_DIR = DATA_DIR / "cache"
    MODELS_DIR = DATA_DIR / "models"

    # Metadata storage
    METADATA_DIR = DATA_DIR / "metadata"
    MODEL_REGISTRY_PATH = METADATA_DIR / "model_registry.json"

    # Stock universe
    EGX_STOCKS_PATH = DATA_DIR / "egx_stocks.csv"

    # Model training defaults
    DEFAULT_TRAINING_WINDOW_DAYS = 730  # 2 years
    DEFAULT_EPOCHS = 50
    DEFAULT_BATCH_SIZE = 32
    DEFAULT_LEARNING_RATE = 0.001

    # Model staleness threshold (days)
    MODEL_STALE_DAYS = 14

    # Provider settings
    DEFAULT_PROVIDER = "yfinance"
    FALLBACK_PROVIDER = "csv_import"

    @classmethod
    def ensure_directories(cls) -> None:
        """Create all required directories if they don't exist."""
        for directory in [
            cls.DATA_DIR,
            cls.CACHE_DIR,
            cls.MODELS_DIR,
            cls.METADATA_DIR,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_cache_path(cls, symbol: str) -> Path:
        """Get cache file path for a stock symbol."""
        return cls.CACHE_DIR / f"{symbol.upper()}.parquet"

    @classmethod
    def get_model_path(cls, artifact_id: str) -> Path:
        """Get model weights file path."""
        return cls.MODELS_DIR / f"{artifact_id}.pt"

    @classmethod
    def get_model_config_path(cls, artifact_id: str) -> Path:
        """Get model config file path."""
        return cls.MODELS_DIR / f"{artifact_id}_config.json"


# Initialize directories on import
Config.ensure_directories()
