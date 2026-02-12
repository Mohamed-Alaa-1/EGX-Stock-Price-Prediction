"""Unit tests for EGX cost model and backtest accounting."""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.backtest import run_backtest
from core.schemas import (
    BacktestStrategy,
    DataSourceRecord,
    PriceBar,
    PriceSeries,
    TransactionCostModel,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_series(
    n: int = 200,
    start: float = 100.0,
    seed: int = 42,
) -> PriceSeries:
    """Synthetic price series."""
    rng = np.random.default_rng(seed)
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + rng.normal(0.0005, 0.015)))
    base = date(2023, 1, 1)
    bars = [
        PriceBar(
            date=base + timedelta(days=i),
            open=p, high=p * 1.01,
            low=p * 0.99, close=p, volume=1000,
        )
        for i, p in enumerate(prices)
    ]
    source = DataSourceRecord(
        provider="test",
        fetched_at=datetime.now(),
        range_start=base,
        range_end=base + timedelta(days=n - 1),
    )
    return PriceSeries(
        symbol="TEST", bars=bars,
        source=source, last_updated_at=datetime.now(),
    )


# ---------------------------------------------------------------------------
# TransactionCostModel tests
# ---------------------------------------------------------------------------

class TestTransactionCostModel:
    """Tests for TransactionCostModel."""

    def test_default_egx_costs(self):
        """Default model uses commission=15bp, stamp_duty=5bp."""
        model = TransactionCostModel()
        assert model.commission_bps == 15.0
        assert model.stamp_duty_bps == 5.0
        assert model.slippage_bps == 0.0

    def test_total_cost_rate(self):
        """total_cost_rate = (commission + stamp + slippage) / 10000."""
        model = TransactionCostModel(
            commission_bps=15.0,
            stamp_duty_bps=5.0,
            slippage_bps=0.0,
        )
        expected = (15.0 + 5.0 + 0.0) / 10000.0
        assert abs(model.total_cost_rate - expected) < 1e-12

    def test_custom_costs(self):
        """Custom cost model should compute correctly."""
        model = TransactionCostModel(
            commission_bps=20.0,
            stamp_duty_bps=10.0,
            slippage_bps=5.0,
        )
        expected = 35.0 / 10000.0
        assert abs(model.total_cost_rate - expected) < 1e-12


# ---------------------------------------------------------------------------
# Backtest gross vs net tests
# ---------------------------------------------------------------------------

class TestBacktestGrossVsNet:
    """Backtest always reports both gross and net of costs."""

    def test_net_return_less_than_gross(self):
        """Net return should always be ≤ gross return."""
        series = _make_series(n=200, seed=1)
        result = run_backtest(
            series,
            strategy=BacktestStrategy.EMA,
            cost_model=TransactionCostModel(),
        )
        assert result.net_total_return <= result.gross_total_return

    def test_zero_cost_gross_equals_net(self):
        """With zero costs, gross = net."""
        series = _make_series(n=200, seed=2)
        zero_cost = TransactionCostModel(
            commission_bps=0, stamp_duty_bps=0, slippage_bps=0,
        )
        result = run_backtest(
            series,
            strategy=BacktestStrategy.RSI,
            cost_model=zero_cost,
        )
        assert abs(
            result.gross_total_return - result.net_total_return
        ) < 1e-10

    def test_total_costs_paid_positive(self):
        """Total costs paid should be ≥ 0."""
        series = _make_series(n=200, seed=3)
        result = run_backtest(
            series,
            strategy=BacktestStrategy.MACD,
        )
        assert result.total_costs_paid is not None
        assert result.total_costs_paid >= 0

    def test_trade_count_nonnegative(self):
        """Trade count ≥ 0."""
        series = _make_series(n=200, seed=4)
        result = run_backtest(
            series, strategy=BacktestStrategy.RSI,
        )
        assert result.trade_count >= 0

    def test_insufficient_data_warning(self):
        """Very short series produces warning."""
        series = _make_series(n=10, seed=5)
        result = run_backtest(
            series, strategy=BacktestStrategy.EMA,
        )
        assert len(result.warnings) > 0


# ---------------------------------------------------------------------------
# Commission + stamp duty arithmetic
# ---------------------------------------------------------------------------

class TestCostArithmetic:
    """Verify cost drag scales with turnover and cost rate."""

    def test_higher_costs_lower_net(self):
        """Higher costs → lower net return."""
        series = _make_series(n=200, seed=6)
        low = TransactionCostModel(
            commission_bps=5, stamp_duty_bps=2,
        )
        high = TransactionCostModel(
            commission_bps=50, stamp_duty_bps=20,
        )
        r_low = run_backtest(
            series, strategy=BacktestStrategy.EMA, cost_model=low,
        )
        r_high = run_backtest(
            series, strategy=BacktestStrategy.EMA, cost_model=high,
        )
        assert r_high.net_total_return <= r_low.net_total_return

    def test_cost_model_persisted_in_result(self):
        """BacktestRun should capture the cost model used."""
        series = _make_series(n=200, seed=7)
        custom = TransactionCostModel(
            commission_bps=25.0, stamp_duty_bps=8.0,
        )
        result = run_backtest(
            series, strategy=BacktestStrategy.RSI, cost_model=custom,
        )
        assert result.cost_model.commission_bps == 25.0
        assert result.cost_model.stamp_duty_bps == 8.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
