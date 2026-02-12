"""Unit tests for VaR + Sharpe computations in src/core/quant.py."""

# We test the pure functions, not services
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from datetime import date, datetime, timedelta

from core.quant import compute_risk_snapshot, compute_sharpe, compute_var
from core.schemas import (
    DataSourceRecord,
    PriceBar,
    PriceSeries,
    RiskMetricsSnapshot,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_series(
    n: int = 300,
    start_price: float = 100.0,
    daily_vol: float = 0.02,
    seed: int = 42,
) -> PriceSeries:
    """Generate a synthetic PriceSeries with known volatility."""
    rng = np.random.default_rng(seed)
    prices = [start_price]
    for _ in range(n - 1):
        ret = rng.normal(0, daily_vol)
        prices.append(prices[-1] * (1 + ret))

    bars = []
    base_date = date(2023, 1, 1)
    for i, p in enumerate(prices):
        d = base_date + timedelta(days=i)
        bars.append(PriceBar(
            date=d, open=p, high=p * 1.01,
            low=p * 0.99, close=p, volume=1000,
        ))
    source = DataSourceRecord(
        provider="test",
        fetched_at=datetime.now(),
        range_start=base_date,
        range_end=base_date + timedelta(days=n - 1),
    )
    return PriceSeries(
        symbol="TEST", bars=bars,
        source=source, last_updated_at=datetime.now(),
    )


# ---------------------------------------------------------------------------
# VaR tests
# ---------------------------------------------------------------------------

class TestComputeVaR:
    """Tests for compute_var."""

    def test_var_95_on_known_returns(self):
        """VaR at 95% on a normal distribution should be near the 5th pctile."""
        rng = np.random.default_rng(0)
        returns = pd.Series(rng.normal(0, 0.02, 500))
        var_95 = compute_var(returns, confidence=0.95)
        assert var_95 is not None
        # Historical VaR is the 5th-percentile return (negative for losses)
        assert var_95 < 0, "VaR should be negative (left tail quantile)"
        # For N(0, 0.02), 5th pctile ≈ -1.645 * 0.02 ≈ -0.0329
        assert abs(var_95 + 0.0329) < 0.01

    def test_var_99_greater_than_var_95(self):
        """VaR at 99% should be more negative than VaR at 95%."""
        rng = np.random.default_rng(1)
        returns = pd.Series(rng.normal(0, 0.02, 500))
        var_95 = compute_var(returns, confidence=0.95)
        var_99 = compute_var(returns, confidence=0.99)
        # 99% VaR is deeper in the left tail → more negative
        assert var_99 < var_95

    def test_var_insufficient_data(self):
        """VaR returns None when insufficient observations."""
        returns = pd.Series([0.01, -0.01, 0.005])
        var = compute_var(returns, confidence=0.95)
        assert var is None

    def test_var_zero_volatility(self):
        """VaR on constant returns should be ~0."""
        returns = pd.Series([0.0] * 100)
        var = compute_var(returns, confidence=0.95)
        assert var is not None
        assert abs(var) < 1e-10


# ---------------------------------------------------------------------------
# Sharpe tests
# ---------------------------------------------------------------------------

class TestComputeSharpe:
    """Tests for compute_sharpe."""

    def test_sharpe_positive_drift(self):
        """Positive mean returns → positive Sharpe."""
        # Use a strong drift (0.005) relative to vol (0.02) to ensure
        # the sample mean is reliably positive.
        rng = np.random.default_rng(2)
        returns = pd.Series(rng.normal(0.005, 0.02, 500))
        sharpe = compute_sharpe(returns, risk_free_rate=0.0)
        assert sharpe is not None
        assert sharpe > 0

    def test_sharpe_zero_returns(self):
        """Zero-mean returns → Sharpe near 0."""
        rng = np.random.default_rng(3)
        returns = pd.Series(rng.normal(0.0, 0.02, 500))
        sharpe = compute_sharpe(returns, risk_free_rate=0.0)
        assert sharpe is not None
        assert abs(sharpe) < 1.0  # Should be near 0

    def test_sharpe_with_risk_free_rate(self):
        """Non-zero risk-free rate reduces Sharpe."""
        rng = np.random.default_rng(4)
        returns = pd.Series(rng.normal(0.001, 0.02, 300))
        s0 = compute_sharpe(returns, risk_free_rate=0.0)
        s1 = compute_sharpe(returns, risk_free_rate=0.05)
        assert s1 < s0

    def test_sharpe_insufficient_data(self):
        """Sharpe returns None when too few observations."""
        returns = pd.Series([0.01, -0.01])
        sharpe = compute_sharpe(returns)
        assert sharpe is None


# ---------------------------------------------------------------------------
# Risk snapshot integration
# ---------------------------------------------------------------------------

class TestRiskSnapshot:
    """Integration test for compute_risk_snapshot."""

    def test_snapshot_with_sufficient_data(self):
        """Snapshot with enough data populates all fields."""
        series = _make_series(n=300)
        snap = compute_risk_snapshot(series)
        assert isinstance(snap, RiskMetricsSnapshot)
        assert snap.var_95_pct is not None
        assert snap.var_99_pct is not None
        assert snap.sharpe is not None
        # VaR is negative (left tail quantile)
        assert snap.var_95_pct < 0
        # 99% VaR is more negative than 95% VaR
        assert snap.var_99_pct < snap.var_95_pct

    def test_snapshot_with_short_history(self):
        """Snapshot with short history triggers warnings."""
        series = _make_series(n=20)
        snap = compute_risk_snapshot(series)
        assert len(snap.warnings) > 0
        assert snap.var_95_pct is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
