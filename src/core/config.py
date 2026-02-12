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

    # ---------- Quant finance defaults (T006) ----------

    # Risk metrics
    DEFAULT_RISK_LOOKBACK_DAYS = 252  # ~1 year of trading days
    MIN_OBSERVATIONS_RISK = 60  # minimum bars needed for VaR/Sharpe
    DEFAULT_VAR_METHOD = "historical"
    DEFAULT_RISK_FREE_RATE = 0.0  # labeled as 0 by default
    DEFAULT_RETURN_TYPE = "simple"

    # Statistical validation
    DEFAULT_VALIDATION_LOOKBACK_DAYS = 252
    MIN_OBSERVATIONS_VALIDATION = 100  # minimum bars for ADF/Hurst
    ADF_SIGNIFICANCE_LEVEL = 0.05
    HURST_TRENDING_THRESHOLD = 0.6  # H > 0.6 → trending
    HURST_MEAN_REVERTING_THRESHOLD = 0.4  # H < 0.4 → mean-reverting

    # Backtesting
    DEFAULT_BACKTEST_LOOKBACK_YEARS = 5
    DEFAULT_COMMISSION_BPS = 15.0  # EGX typical commission
    DEFAULT_STAMP_DUTY_BPS = 5.0  # EGX stamp duty
    DEFAULT_SLIPPAGE_BPS = 0.0

    # Portfolio optimization
    DEFAULT_PORTFOLIO_LOOKBACK_DAYS = 252
    MIN_OVERLAP_DAYS = 126  # minimum overlapping trading days for covariance
    DEFAULT_SHRINKAGE_ALPHA = 0.1
    DEFAULT_DIAGONAL_LOADING_LAMBDA = 0.0
    MAX_FRONTIER_POINTS = 20

    # Cross-listings / GDR
    CROSS_LISTINGS_PATH = METADATA_DIR / "cross_listings.json"

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
