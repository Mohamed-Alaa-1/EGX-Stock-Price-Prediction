"""Unit tests for ADF + Hurst computations in src/core/quant.py."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from datetime import date, datetime, timedelta

from core.quant import compute_adf, compute_hurst, compute_validation
from core.schemas import (
    DataSourceRecord,
    HurstRegime,
    PriceBar,
    PriceSeries,
    StatisticalValidationResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _returns_series(
    n: int = 300,
    mean: float = 0.0,
    std: float = 0.02,
    seed: int = 42,
) -> pd.Series:
    """Generate random normally distributed returns."""
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(mean, std, n))


def _make_price_series(n: int = 300, seed: int = 42) -> PriceSeries:
    """Generate a synthetic PriceSeries."""
    rng = np.random.default_rng(seed)
    prices = [100.0]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + rng.normal(0, 0.02)))
    base_date = date(2023, 1, 1)
    bars = [
        PriceBar(
            date=base_date + timedelta(days=i),
            open=p, high=p * 1.01,
            low=p * 0.99, close=p, volume=1000,
        )
        for i, p in enumerate(prices)
    ]
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
# ADF tests
# ---------------------------------------------------------------------------

class TestComputeAdf:
    """Tests for compute_adf."""

    def test_adf_on_stationary_series(self):
        """IID returns should be stationary (low p-value)."""
        returns = _returns_series(n=500, seed=10)
        result = compute_adf(returns)
        assert "adf_statistic" in result
        assert "adf_pvalue" in result
        assert result["adf_pvalue"] < 0.05  # Should reject unit root

    def test_adf_on_random_walk(self):
        """Cumulative sum (random walk) should be non-stationary."""
        rng = np.random.default_rng(20)
        walk = pd.Series(np.cumsum(rng.normal(0, 1, 500)))
        result = compute_adf(walk)
        # p-value should be high (fail to reject unit root)
        assert result["adf_pvalue"] > 0.05

    def test_adf_insufficient_data(self):
        """ADF on too few observations returns None values."""
        returns = _returns_series(n=10)
        result = compute_adf(returns)
        assert result["adf_statistic"] is None
        assert result["adf_pvalue"] is None

    def test_adf_records_metadata(self):
        """ADF result should include nobs and critical values."""
        returns = _returns_series(n=300)
        result = compute_adf(returns)
        assert "adf_nobs" in result
        assert "adf_critical_values" in result


# ---------------------------------------------------------------------------
# Hurst tests
# ---------------------------------------------------------------------------

class TestComputeHurst:
    """Tests for compute_hurst."""

    def test_hurst_random_series(self):
        """IID returns should have Hurst ~0.5 (random-like)."""
        returns = _returns_series(n=500, seed=30)
        result = compute_hurst(returns)
        assert "hurst" in result
        h = result["hurst"]
        assert h is not None
        # Should be in the random-like range [0.3, 0.7]
        assert 0.3 < h < 0.7

    def test_hurst_trending_series(self):
        """Cumulative trending series should have H > 0.5."""
        # Create a trending series (persistent)
        rng = np.random.default_rng(40)
        n = 500
        increments = np.zeros(n)
        for i in range(1, n):
            # Positive autocorrelation
            increments[i] = 0.7 * increments[i - 1] + rng.normal(0, 1)
        result = compute_hurst(pd.Series(increments))
        h = result["hurst"]
        assert h is not None
        assert h > 0.5  # Should show trending behavior

    def test_hurst_insufficient_data(self):
        """Hurst on very short series returns None."""
        returns = _returns_series(n=15)
        result = compute_hurst(returns)
        assert result["hurst"] is None

    def test_hurst_regime_classification(self):
        """Regime should match exponent thresholds."""
        returns = _returns_series(n=500, seed=50)
        result = compute_hurst(returns)
        h = result["hurst"]
        regime = result["hurst_regime"]
        if h < 0.4:
            assert regime == HurstRegime.MEAN_REVERTING
        elif h > 0.6:
            assert regime == HurstRegime.TRENDING
        else:
            assert regime == HurstRegime.RANDOM_LIKE

    def test_hurst_fit_diagnostics(self):
        """Hurst result should include R² fit diagnostic."""
        returns = _returns_series(n=300, seed=60)
        result = compute_hurst(returns)
        assert "hurst_r2" in result
        r2 = result["hurst_r2"]
        assert r2 is not None
        assert 0.0 <= r2 <= 1.0


# ---------------------------------------------------------------------------
# Validation integration
# ---------------------------------------------------------------------------

class TestComputeValidation:
    """Integration test for compute_validation."""

    def test_validation_with_sufficient_data(self):
        """Full validation with enough data populates all fields."""
        series = _make_price_series(n=300)
        result = compute_validation(series)
        assert isinstance(result, StatisticalValidationResult)
        assert result.adf_pvalue is not None
        assert result.hurst is not None
        assert result.hurst_regime in [
            HurstRegime.MEAN_REVERTING,
            HurstRegime.RANDOM_LIKE,
            HurstRegime.TRENDING,
        ]

    def test_validation_with_short_history(self):
        """Validation with short history triggers warnings."""
        series = _make_price_series(n=30)
        result = compute_validation(series)
        assert len(result.warnings) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
