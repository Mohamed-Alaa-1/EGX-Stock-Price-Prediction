"""
Core domain schemas using Pydantic.
"""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class StockStatus(str, Enum):
    """Stock listing status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELISTED = "delisted"
    UNKNOWN = "unknown"


class Stock(BaseModel):
    """EGX-listed stock."""
    symbol: str = Field(..., description="Exchange symbol")
    company_name: str = Field(..., description="Company name")
    sector: str = Field(default="Unknown", description="Sector")
    exchange: str = Field(default="EGX", description="Exchange code")
    status: StockStatus = Field(default=StockStatus.UNKNOWN, description="Listing status")

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        """Ensure symbol is uppercase."""
        return v.upper()


class PriceBar(BaseModel):
    """Single OHLCV price bar."""
    date: date
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: Optional[float] = Field(default=None, ge=0)
    adjusted_close: Optional[float] = Field(default=None, gt=0)

    @field_validator("high")
    @classmethod
    def validate_high(cls, v: float, info) -> float:
        """Validate high >= max(open, close, low)."""
        values = info.data
        if "open" in values and "close" in values and "low" in values:
            if v < max(values["open"], values["close"], values["low"]):
                raise ValueError("high must be >= max(open, close, low)")
        return v

    @field_validator("low")
    @classmethod
    def validate_low(cls, v: float, info) -> float:
        """Validate low <= min(open, close, high)."""
        values = info.data
        if "open" in values and "close" in values and "high" in values:
            if v > min(values["open"], values["close"], values["high"]):
                raise ValueError("low must be <= min(open, close, high)")
        return v


class DataSourceRecord(BaseModel):
    """Data provenance and caching metadata."""
    provider: str = Field(..., description="Provider name (yfinance, csv_import, etc)")
    provider_details: dict[str, Any] = Field(default_factory=dict, description="Provider-specific metadata")
    fetched_at: datetime = Field(..., description="When data was fetched")
    range_start: date = Field(..., description="Data range start")
    range_end: date = Field(..., description="Data range end")


class PriceSeries(BaseModel):
    """Collection of price bars for a stock."""
    symbol: str
    bars: list[PriceBar] = Field(..., min_length=1)
    source: DataSourceRecord
    last_updated_at: datetime

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        """Ensure symbol is uppercase."""
        return v.upper()

    def get_latest_bar(self) -> PriceBar:
        """Get the most recent price bar."""
        return max(self.bars, key=lambda b: b.date)

    def get_latest_close(self) -> float:
        """Get the most recent close price."""
        return self.get_latest_bar().close


class IndicatorSelection(BaseModel):
    """User's indicator toggle state."""
    rsi_enabled: bool = False
    macd_enabled: bool = False
    ema_enabled: bool = False
    support_resistance_enabled: bool = False


class ModelType(str, Enum):
    """Model training type."""
    PER_STOCK = "per_stock"
    FEDERATED = "federated"


class ModelArtifact(BaseModel):
    """Saved trained model metadata."""
    artifact_id: str = Field(..., description="Unique artifact identifier")
    type: ModelType = Field(..., description="Training type")
    covered_symbols: list[str] = Field(..., min_length=1, description="Symbols covered by this model")
    created_at: datetime = Field(..., description="First creation time")
    last_trained_at: datetime = Field(..., description="Last training time")
    data_source: DataSourceRecord = Field(..., description="Training data source")
    training_window_start: date = Field(..., description="Training data start date")
    training_window_end: date = Field(..., description="Training data end date")
    model_version: str = Field(default="lstm_v1", description="Model architecture version")
    hyperparams: dict[str, Any] = Field(default_factory=dict, description="Hyperparameters")
    metrics: dict[str, float] = Field(default_factory=dict, description="Evaluation metrics")
    storage_path: str = Field(..., description="Path to model weights")

    def is_stale(self, threshold_days: int = 14) -> bool:
        """Check if model is stale based on last_trained_at."""
        age = datetime.now() - self.last_trained_at
        return age > timedelta(days=threshold_days)


class MomentumLabel(str, Enum):
    """Momentum classification."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ForecastMethod(str, Enum):
    """Forecast method selection."""
    ML = "ml"
    NAIVE = "naive"
    SMA = "sma"


class ForecastRequest(BaseModel):
    """User prediction request."""
    symbol: str
    target_date: date = Field(..., description="Target trading day for prediction")
    requested_at: datetime = Field(default_factory=datetime.now)
    method: ForecastMethod = Field(default=ForecastMethod.ML, description="Forecast method")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        """Ensure symbol is uppercase."""
        return v.upper()


class ForecastResult(BaseModel):
    """Prediction output."""
    request: ForecastRequest = Field(..., description="Original forecast request")
    predicted_close: float = Field(..., gt=0)
    generated_at: datetime = Field(default_factory=datetime.now)
    model_artifact_id: Optional[str] = Field(default=None, description="Model artifact used")
    is_model_stale: bool = Field(default=False)
    confidence_interval: Optional[dict[str, float]] = Field(default=None)
    model_features: dict[str, Any] = Field(default_factory=dict)
