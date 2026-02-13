"""
Core domain schemas using Pydantic.
"""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Shared quant types (used by risk, validation, backtest, portfolio, GDR)
# ---------------------------------------------------------------------------

class ReturnType(str, Enum):
    """Return convention."""
    SIMPLE = "simple"
    LOG = "log"


class PriceField(str, Enum):
    """Which price field to use."""
    CLOSE = "close"
    ADJUSTED_CLOSE = "adjusted_close"


class HurstRegime(str, Enum):
    """Hurst exponent regime classification."""
    MEAN_REVERTING = "mean_reverting"
    RANDOM_LIKE = "random_like"
    TRENDING = "trending"


class BacktestStrategy(str, Enum):
    """Supported backtest strategies."""
    RSI = "rsi"
    MACD = "macd"
    EMA = "ema"


# ---------------------------------------------------------------------------
# Original schemas
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Quant finance schemas (T003–T005)
# ---------------------------------------------------------------------------

class RiskMetricsSnapshot(BaseModel):
    """Per-ticker risk companion alongside predictions (FR-001..FR-003)."""
    symbol: str
    as_of_date: date
    lookback_days: int = 252
    return_type: ReturnType = ReturnType.SIMPLE
    var_method: str = "historical"
    var_95_pct: Optional[float] = None
    var_99_pct: Optional[float] = None
    var_95_abs: Optional[float] = None
    var_99_abs: Optional[float] = None
    sharpe: Optional[float] = None
    risk_free_rate: float = Field(default=0.0, description="Assumed risk-free rate (labeled)")
    warnings: list[str] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper()


class StatisticalValidationResult(BaseModel):
    """ADF + Hurst diagnostics prior to training (FR-004..FR-006)."""
    symbol: str
    as_of_date: date
    lookback_days: int = 252
    series_tested: str = "returns"

    # ADF
    adf_statistic: Optional[float] = None
    adf_pvalue: Optional[float] = None
    adf_used_lag: Optional[int] = None
    adf_nobs: Optional[int] = None
    adf_critical_values: Optional[dict[str, float]] = None
    adf_regression: str = "c"
    adf_autolag: str = "AIC"

    # Hurst
    hurst: Optional[float] = None
    hurst_method: str = "aggvar_increments"
    hurst_r2: Optional[float] = None
    hurst_regime: Optional[HurstRegime] = None

    warnings: list[str] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper()


class TransactionCostModel(BaseModel):
    """User-configurable EGX cost assumptions (FR-010..FR-011)."""
    commission_bps: float = Field(default=15.0, description="Commission in basis points")
    stamp_duty_bps: float = Field(default=5.0, description="Stamp duty in basis points")
    slippage_bps: float = Field(default=0.0, description="Slippage in basis points")
    notes: Optional[str] = None

    @property
    def total_cost_rate(self) -> float:
        """Total one-way cost as a decimal fraction."""
        return (self.commission_bps + self.stamp_duty_bps + self.slippage_bps) / 10000.0


class BacktestRun(BaseModel):
    """Stored definition of a strategy evaluation (FR-009..FR-011)."""
    run_id: str = ""
    symbol: str
    strategy: BacktestStrategy
    strategy_params: dict[str, Any] = Field(default_factory=dict)
    start_date: date
    end_date: date
    cost_model: TransactionCostModel = Field(default_factory=TransactionCostModel)

    # Outputs
    gross_total_return: float = 0.0
    net_total_return: float = 0.0
    gross_cagr: Optional[float] = None
    net_cagr: Optional[float] = None
    gross_sharpe: Optional[float] = None
    net_sharpe: Optional[float] = None
    max_drawdown: Optional[float] = None
    turnover: Optional[float] = None
    total_costs_paid: Optional[float] = None
    trade_count: int = 0
    warnings: list[str] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper()


class PortfolioOptimizationResult(BaseModel):
    """Federated-mode allocation suggestions (FR-012..FR-014)."""
    symbols: list[str]
    as_of_date: date
    lookback_days: int = 252
    return_type: ReturnType = ReturnType.SIMPLE
    constraints: dict[str, Any] = Field(default_factory=lambda: {
        "long_only": True, "min_weight": 0.0, "max_weight": 1.0, "sum_to_one": True,
    })

    # Inputs summary
    mu: Optional[dict[str, float]] = None
    cov_method: str = "shrunk_diag"
    shrinkage_alpha: float = 0.1

    # Outputs
    mpt_min_variance_weights: Optional[dict[str, float]] = None
    mpt_frontier: list[dict[str, Any]] = Field(default_factory=list)
    risk_parity_weights: Optional[dict[str, float]] = None
    risk_contributions: Optional[dict[str, float]] = None
    portfolio_volatility: Optional[float] = None
    warnings: list[str] = Field(default_factory=list)


class GdrPremiumDiscountPoint(BaseModel):
    """Single premium/discount data point."""
    date: date
    value: float
    is_imputed_fx: bool = False


class GdrPremiumDiscountSeries(BaseModel):
    """Leading indicator for cross-listed stocks (FR-015..FR-016)."""
    local_symbol: str
    gdr_symbol: str
    fx_pair: str
    ratio_local_per_gdr: float
    points: list[GdrPremiumDiscountPoint] = Field(default_factory=list)
    definition: str = "(local_close - gdr_close_fx_adjusted * ratio) / gdr_close_fx_adjusted * 100"
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Investment-assistant schemas (001-investment-assistant / T007)
# ---------------------------------------------------------------------------


class StrategyAction(str, Enum):
    """Recommendation action."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class EvidenceSource(str, Enum):
    """Signal source feeding the strategy engine."""
    ML_FORECAST = "ml_forecast"
    RSI = "rsi"
    MACD = "macd"
    EMA = "ema"
    VAR = "var"
    HURST = "hurst"
    ADF = "adf"


class EvidenceDirection(str, Enum):
    """Directional classification for a single signal."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class EvidenceSignal(BaseModel):
    """One explainable contribution to a recommendation."""
    source: EvidenceSource
    direction: EvidenceDirection
    weight: float = Field(..., description="Blending weight for the source-group (disclosed)")
    score: float = Field(..., ge=-1.0, le=1.0, description="Normalized signal in [-1, +1]")
    summary: str = Field(..., description="Short reason shown in UI")
    raw_value: Optional[Any] = Field(default=None, description="Optional raw metric (e.g. RSI=72)")


class StrategyRecommendation(BaseModel):
    """Assistant-produced strategy guidance for a symbol at a point in time."""
    symbol: str
    as_of_date: date
    action: StrategyAction
    conviction: int = Field(..., ge=0, le=100)
    regime: Optional[HurstRegime] = None
    entry_zone_lower: Optional[float] = None
    entry_zone_upper: Optional[float] = None
    target_exit: Optional[float] = None
    stop_loss: Optional[float] = None
    risk_distance_pct: Optional[float] = None
    evidence_bullish: list[EvidenceSignal] = Field(default_factory=list)
    evidence_bearish: list[EvidenceSignal] = Field(default_factory=list)
    evidence_neutral: list[EvidenceSignal] = Field(default_factory=list)
    logic_summary: str = ""
    raw_inputs: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper()


# ---------------------------------------------------------------------------
# Trade journal / performance schemas (001-investment-assistant / T008)
# ---------------------------------------------------------------------------


class TradeJournalEntry(BaseModel):
    """An immutable log of a user action triggered from the Strategy Dashboard."""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    created_at: datetime = Field(default_factory=datetime.now)
    symbol: str
    event_type: str = Field(..., description="entry | exit")
    side: str = Field(..., description="long | short")
    price: float = Field(..., gt=0)
    recommendation_snapshot: dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper()


class PerformanceSummary(BaseModel):
    """Aggregated analytics computed from closed simulated positions."""
    as_of_date: date
    symbol: Optional[str] = None
    closed_trade_count: int = 0
    open_trade_count: int = 0
    win_rate: Optional[float] = None
    avg_return_pct: Optional[float] = None
    stop_loss_hit_rate: Optional[float] = None
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stock Sheet Insights (batch training + analysis)
# ---------------------------------------------------------------------------


class InsightStatus(str, Enum):
    """Per-stock processing outcome."""
    OK = "ok"
    HOLD_FALLBACK = "hold_fallback"
    ERROR = "error"


class StrategyAction(str, Enum):
    """Recommendation action."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class SheetInsightsRunRequest(BaseModel):
    """Parameters for a batch insights run."""
    symbols: Optional[list[str]] = Field(default=None, description="Symbols to analyze (None = all)")
    forecast_method: str = Field(default="ml", description="Forecast method: ml, naive, sma")
    train_models: bool = Field(default=True, description="Whether to train/update models")
    force_refresh: bool = Field(default=True, description="Attempt fresh retrieval (no-cache)")

    @field_validator("symbols")
    @classmethod
    def symbols_uppercase(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Normalize symbols to uppercase."""
        if v is None:
            return None
        return [s.upper() for s in v]


class StockInsight(BaseModel):
    """Computed insight for one stock at a point in time."""
    symbol: str
    as_of_date: date
    computed_at: datetime
    action: StrategyAction
    conviction: int = Field(..., ge=0, le=100, description="Conviction score 0-100")
    stop_loss: Optional[float] = Field(default=None, gt=0, description="Stop-loss price (None = N/A)")
    target_exit: Optional[float] = Field(default=None, gt=0, description="Target exit price (None = N/A)")
    entry_zone_lower: Optional[float] = Field(default=None, gt=0)
    entry_zone_upper: Optional[float] = Field(default=None, gt=0)
    logic_summary: str = Field(default="", description="Short explanation")
    status: InsightStatus
    status_reason: Optional[str] = Field(default=None, description="User-readable reason when not OK")
    used_cache_fallback: bool = Field(default=False, description="True if fresh retrieval failed")
    raw_outputs: Optional[dict[str, Any]] = Field(default=None, description="Raw forecast + baseline + risk")
    assistant_recommendation: Optional[dict[str, Any]] = Field(default=None, description="StrategyEngine output")

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper()


class InsightBatchRun(BaseModel):
    """One batch run across many symbols."""
    batch_id: str
    computed_at: datetime
    request: SheetInsightsRunRequest
    results: list[StockInsight] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict, description="Counts: total, ok, hold_fallback, error")

