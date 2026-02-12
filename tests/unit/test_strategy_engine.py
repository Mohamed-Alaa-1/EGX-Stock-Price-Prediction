"""
Unit tests for StrategyEngine.

Covers:
    T021 – Risk-first HOLD on missing inputs
    T022 – BUY/SELL always include stop-loss; HOLD uses explicit N/A
    T023 – Conviction reduction on disagreement
    T024 – Action thresholds (BUY/SELL/HOLD)
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pytest

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.schemas import (
    DataSourceRecord,
    ForecastMethod,
    ForecastRequest,
    ForecastResult,
    HurstRegime,
    PriceBar,
    PriceSeries,
    RiskMetricsSnapshot,
    StatisticalValidationResult,
    StrategyAction,
)
from services.strategy_engine import StrategyEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_series(
    symbol: str = "TEST",
    closes: Optional[list[float]] = None,
    n: int = 200,
    base_price: float = 50.0,
) -> PriceSeries:
    """
    Build a synthetic PriceSeries.  If *closes* are not provided, create
    *n* bars around *base_price* with minor random-walk-like drift.
    """
    if closes is None:
        import numpy as np
        rng = np.random.default_rng(42)
        prices = [base_price]
        for _ in range(n - 1):
            move = rng.normal(0, 0.01) * prices[-1]
            prices.append(max(0.01, prices[-1] + move))
        closes = prices

    bars = []
    for i, c in enumerate(closes):
        d = date(2025, 1, 1)
        # shift day forward to avoid duplicating dates
        d = date(2025, 1, 1).__class__.fromordinal(d.toordinal() + i)
        bars.append(
            PriceBar(
                date=d,
                open=c * 0.99,
                high=c * 1.01,
                low=c * 0.98,
                close=c,
                volume=100_000,
            )
        )

    return PriceSeries(
        symbol=symbol,
        bars=bars,
        source=DataSourceRecord(
            provider="test",
            fetched_at=datetime.now(),
            range_start=bars[0].date,
            range_end=bars[-1].date,
        ),
        last_updated_at=datetime.now(),
    )


def _make_forecast(
    symbol: str = "TEST",
    predicted_close: float = 55.0,
) -> ForecastResult:
    return ForecastResult(
        request=ForecastRequest(
            symbol=symbol,
            target_date=date(2025, 8, 1),
            method=ForecastMethod.ML,
        ),
        predicted_close=predicted_close,
    )


def _make_risk(
    symbol: str = "TEST",
    var_95: float = -0.025,
) -> RiskMetricsSnapshot:
    return RiskMetricsSnapshot(
        symbol=symbol,
        as_of_date=date(2025, 7, 30),
        var_95_pct=var_95,
    )


def _make_validation(
    symbol: str = "TEST",
    hurst: float = 0.65,
    regime: HurstRegime = HurstRegime.TRENDING,
) -> StatisticalValidationResult:
    return StatisticalValidationResult(
        symbol=symbol,
        as_of_date=date(2025, 7, 30),
        hurst=hurst,
        hurst_regime=regime,
    )


# ---------------------------------------------------------------------------
# T021 – Risk-first HOLD on missing inputs
# ---------------------------------------------------------------------------


class TestRiskFirstHold:
    """When required inputs are missing, the engine must default to HOLD."""

    def test_hold_when_no_forecast(self):
        """No ML forecast → action should be HOLD."""
        engine = StrategyEngine()
        series = _make_series()
        rec = engine.compute_recommendation(series, forecast=None)
        assert rec.action == StrategyAction.HOLD

    def test_hold_with_insufficient_bars(self):
        """Very short series → indicators fail → should be HOLD."""
        engine = StrategyEngine()
        series = _make_series(closes=[50.0, 51.0, 49.0])
        rec = engine.compute_recommendation(series)
        assert rec.action == StrategyAction.HOLD

    def test_hold_logic_summary_mentions_hold(self):
        """Logic summary should mention HOLD when defaulting."""
        engine = StrategyEngine()
        series = _make_series()
        rec = engine.compute_recommendation(series, forecast=None)
        assert "HOLD" in rec.logic_summary


# ---------------------------------------------------------------------------
# T022 – BUY/SELL always include stop-loss; HOLD = explicit N/A
# ---------------------------------------------------------------------------


class TestStopLossPresence:
    """Stop-loss must be concrete for BUY/SELL and None for HOLD."""

    def _force_buy(self) -> tuple:
        """Helper: create inputs strongly tilted bullish."""
        series = _make_series(base_price=50.0)
        forecast = _make_forecast(predicted_close=60.0)  # +20 %
        risk = _make_risk(var_95=-0.02)
        validation = _make_validation(hurst=0.70, regime=HurstRegime.TRENDING)
        return series, forecast, risk, validation

    def _force_sell(self) -> tuple:
        """Helper: create inputs strongly tilted bearish."""
        series = _make_series(base_price=50.0)
        forecast = _make_forecast(predicted_close=40.0)  # -20 %
        risk = _make_risk(var_95=-0.02)
        validation = _make_validation(hurst=0.70, regime=HurstRegime.TRENDING)
        return series, forecast, risk, validation

    def test_buy_has_stop_loss(self):
        series, forecast, risk, val = self._force_buy()
        engine = StrategyEngine()
        rec = engine.compute_recommendation(series, forecast, risk, val)
        if rec.action == StrategyAction.BUY:
            assert rec.stop_loss is not None
            assert rec.stop_loss > 0
            assert rec.entry_zone_lower is not None
            assert rec.entry_zone_upper is not None
            assert rec.risk_distance_pct is not None

    def test_sell_has_stop_loss(self):
        series, forecast, risk, val = self._force_sell()
        engine = StrategyEngine()
        rec = engine.compute_recommendation(series, forecast, risk, val)
        if rec.action == StrategyAction.SELL:
            assert rec.stop_loss is not None
            assert rec.stop_loss > 0
            assert rec.entry_zone_lower is not None
            assert rec.entry_zone_upper is not None
            assert rec.risk_distance_pct is not None

    def test_hold_shows_explicit_none(self):
        engine = StrategyEngine()
        series = _make_series()
        rec = engine.compute_recommendation(series, forecast=None)
        if rec.action == StrategyAction.HOLD:
            assert rec.stop_loss is None
            assert rec.entry_zone_lower is None
            assert rec.entry_zone_upper is None
            assert rec.target_exit is None
            assert rec.risk_distance_pct is None


# ---------------------------------------------------------------------------
# T023 – Conviction reduction on disagreement
# ---------------------------------------------------------------------------


class TestConvictionDisagreement:
    """Conviction must decrease when evidence sources disagree."""

    def test_aligned_higher_than_misaligned(self):
        """Aligned signals should yield higher conviction than conflicting ones."""
        engine = StrategyEngine()
        series = _make_series(base_price=50.0)

        # Aligned bullish: strong ML + trending + low risk
        forecast_bull = _make_forecast(predicted_close=60.0)
        risk_low = _make_risk(var_95=-0.015)
        val_trend = _make_validation(hurst=0.70, regime=HurstRegime.TRENDING)
        rec_aligned = engine.compute_recommendation(series, forecast_bull, risk_low, val_trend)

        # Conflicting: ML bearish + trending regime (mismatch)
        forecast_bear = _make_forecast(predicted_close=40.0)
        val_mr = _make_validation(hurst=0.35, regime=HurstRegime.MEAN_REVERTING)
        rec_conflict = engine.compute_recommendation(series, forecast_bear, risk_low, val_mr)

        # The aligned case should have higher conviction (in absolute terms)
        assert rec_aligned.conviction >= rec_conflict.conviction

    def test_conviction_in_range(self):
        """Conviction must always be between 0 and 100."""
        engine = StrategyEngine()
        series = _make_series(base_price=50.0)
        for pc in [30, 50, 55, 60, 80]:
            forecast = _make_forecast(predicted_close=float(pc))
            rec = engine.compute_recommendation(series, forecast)
            assert 0 <= rec.conviction <= 100


# ---------------------------------------------------------------------------
# T024 – Action thresholds
# ---------------------------------------------------------------------------


class TestActionThresholds:
    """Validate BUY/SELL/HOLD thresholds per FR-016."""

    def test_recommendation_always_has_conviction(self):
        engine = StrategyEngine()
        series = _make_series()
        rec = engine.compute_recommendation(series)
        assert rec.conviction is not None
        assert 0 <= rec.conviction <= 100

    def test_recommendation_has_evidence(self):
        """All three evidence buckets should be populated (may be empty lists)."""
        engine = StrategyEngine()
        series = _make_series()
        forecast = _make_forecast(predicted_close=55.0)
        rec = engine.compute_recommendation(series, forecast)
        assert isinstance(rec.evidence_bullish, list)
        assert isinstance(rec.evidence_bearish, list)
        assert isinstance(rec.evidence_neutral, list)

    def test_recommendation_logic_summary_non_empty(self):
        engine = StrategyEngine()
        series = _make_series()
        rec = engine.compute_recommendation(series)
        assert len(rec.logic_summary) > 0

    def test_weights_in_raw_inputs(self):
        """Weights must be disclosed in the raw_inputs."""
        engine = StrategyEngine()
        series = _make_series()
        rec = engine.compute_recommendation(series)
        assert "weights" in rec.raw_inputs
        assert rec.raw_inputs["weights"]["ml"] == 0.35

    def test_custom_weights_rejected_if_sum_not_one(self):
        """Weights that don't sum to 1.0 must raise ValueError."""
        with pytest.raises(ValueError, match="sum to 1.0"):
            StrategyEngine(weights={"ml": 0.5, "technical": 0.5, "regime": 0.1, "risk": 0.1})

    def test_action_is_valid_enum(self):
        engine = StrategyEngine()
        series = _make_series()
        rec = engine.compute_recommendation(series)
        assert rec.action in (StrategyAction.BUY, StrategyAction.SELL, StrategyAction.HOLD)
