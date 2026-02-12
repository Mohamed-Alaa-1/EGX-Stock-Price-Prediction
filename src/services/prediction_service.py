"""
Prediction orchestration service.
"""

from datetime import datetime, date
from typing import Optional

from core.schemas import (
    ForecastRequest,
    ForecastResult,
    ForecastMethod,
    PriceSeries,
    Stock,
)
from core.config import Config
from core.trading_calendar import TradingCalendar
from ml.inference import InferenceEngine
from ml.baselines import get_baseline
from services.model_registry import get_registry
from services.model_staleness import is_model_stale
from services.risk_service import RiskService
from services.signal_validation_service import SignalValidationService
from data.providers.registry import get_provider_registry
from data.cache_store import CacheStore


class PredictionService:
    """Service for orchestrating predictions."""

    def __init__(self):
        self.inference_engine = InferenceEngine()
        self.cache = CacheStore()
        self.registry = get_registry()
        self.provider_registry = get_provider_registry()

    def predict(
        self,
        symbol: str,
        target_date: Optional[date] = None,
        method: ForecastMethod = ForecastMethod.ML,
    ) -> ForecastResult:
        """
        Generate prediction for a stock.

        Args:
            symbol: Stock symbol
            target_date: Prediction date (default: next trading day)
            method: Forecast method

        Returns:
            ForecastResult

        Raises:
            ValueError: If no model available for ML prediction
        """
        symbol = symbol.upper()
        print(f"[PredictionService] predict({symbol}, target_date={target_date}, method={method.value})")

        # Determine target date
        if target_date is None:
            target_date = TradingCalendar.next_trading_day()
            print(f"[PredictionService] Target date resolved to {target_date}")

        # Fetch historical data
        series = self._get_series(symbol)

        # Generate prediction based on method
        if method == ForecastMethod.ML:
            result = self._predict_ml(symbol, series, target_date)
        elif method == ForecastMethod.NAIVE:
            result = self._predict_naive(symbol, series, target_date)
        elif method == ForecastMethod.SMA:
            result = self._predict_sma(symbol, series, target_date)
        else:
            raise ValueError(f"Unknown forecast method: {method}")

        # Enrich with risk companion + baseline (constitution mandate)
        result = self._enrich_with_risk_and_baseline(result, series)
        return result

    def _get_series(self, symbol: str) -> PriceSeries:
        """Fetch historical price data."""
        print(f"[PredictionService] _get_series({symbol})")

        # Try cache first
        cached = self.cache.load(symbol)
        if cached:
            print(f"[PredictionService] Cache hit for {symbol}")
            return cached

        # Fetch from providers
        series = self.provider_registry.fetch_with_fallback(symbol)

        if series is None:
            print(f"[PredictionService] ERROR: No data available for {symbol}")
            raise ValueError(f"No price data available for {symbol}. Check data providers.")

        print(f"[PredictionService] Fetched {len(series.bars)} bars for {symbol}")

        # Cache result
        self.cache.save(series)

        return series

    def _predict_ml(
        self,
        symbol: str,
        series: PriceSeries,
        target_date: date,
    ) -> ForecastResult:
        """Generate ML prediction."""
        # Find suitable model
        artifact = self.registry.get_latest_for_symbol(symbol)

        if not artifact:
            raise ValueError(f"No trained model found for {symbol}")

        # Check staleness
        stale = is_model_stale(artifact)

        # Generate prediction
        prediction = self.inference_engine.predict(artifact, series)

        return ForecastResult(
            request=ForecastRequest(
                symbol=symbol,
                target_date=target_date,
                method=ForecastMethod.ML,
            ),
            predicted_close=prediction,
            generated_at=datetime.now(),
            model_artifact_id=artifact.artifact_id,
            is_model_stale=stale,
            confidence_interval=None,
            model_features={},
        )

    def _predict_naive(
        self,
        symbol: str,
        series: PriceSeries,
        target_date: date,
    ) -> ForecastResult:
        """Generate naive baseline prediction."""
        prediction = get_baseline(series, method="naive")

        return ForecastResult(
            request=ForecastRequest(
                symbol=symbol,
                target_date=target_date,
                method=ForecastMethod.NAIVE,
            ),
            predicted_close=prediction,
            generated_at=datetime.now(),
            model_artifact_id=None,
            is_model_stale=False,
            confidence_interval=None,
            model_features={},
        )

    def _predict_sma(
        self,
        symbol: str,
        series: PriceSeries,
        target_date: date,
    ) -> ForecastResult:
        """Generate SMA baseline prediction."""
        prediction = get_baseline(series, method="sma", window=20)

        return ForecastResult(
            request=ForecastRequest(
                symbol=symbol,
                target_date=target_date,
                method=ForecastMethod.SMA,
            ),
            predicted_close=prediction,
            generated_at=datetime.now(),
            model_artifact_id=None,
            is_model_stale=False,
            confidence_interval=None,
            model_features={},
        )

    def has_model(self, symbol: str) -> bool:
        """Check if ML model exists for symbol."""
        artifact = self.registry.get_latest_for_symbol(symbol)
        return artifact is not None

    def _enrich_with_risk_and_baseline(
        self,
        result: ForecastResult,
        series: PriceSeries,
    ) -> ForecastResult:
        """
        Attach risk companion (VaR+Sharpe), validation (ADF+Hurst),
        and baseline ("naive: last close") to the forecast result.

        Constitution mandates:
        - Risk companion on every prediction (VaR 95/99 + assumptions)
        - Baseline (naive last close) alongside model prediction
        """
        try:
            risk = RiskService.compute(series)
            result.model_features["risk"] = risk.model_dump()
        except Exception as e:
            result.model_features["risk"] = {"error": str(e)}

        try:
            validation = SignalValidationService.validate(series)
            result.model_features["validation"] = validation.model_dump()
        except Exception as e:
            result.model_features["validation"] = {"error": str(e)}

        # Baseline (naive: last close) — constitution requirement
        try:
            baseline_close = get_baseline(series, method="naive")
            result.model_features["baseline"] = {
                "method": "naive (last close)",
                "predicted_close": baseline_close,
            }
        except Exception as e:
            result.model_features["baseline"] = {"error": str(e)}

        return result
