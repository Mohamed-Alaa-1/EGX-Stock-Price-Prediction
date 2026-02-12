"""Unit tests for quant.py convenience aliases (T012)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.quant import calculate_hurst, calculate_var, compute_hurst, compute_var  # noqa: E402


@pytest.fixture()
def sample_returns() -> pd.Series:
    """Generate a reproducible returns series for testing."""
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(0.0005, 0.02, 300))


def test_calculate_var_delegates_to_compute_var(sample_returns: pd.Series):
    alias_result = calculate_var(sample_returns, confidence=0.95)
    direct_result = compute_var(sample_returns, confidence=0.95)
    assert alias_result == direct_result


def test_calculate_hurst_delegates_to_compute_hurst(sample_returns: pd.Series):
    alias_result = calculate_hurst(sample_returns)
    direct_result = compute_hurst(sample_returns)
    assert alias_result == direct_result


def test_calculate_var_returns_float(sample_returns: pd.Series):
    result = calculate_var(sample_returns)
    assert isinstance(result, float)
    assert result < 0  # VaR should be negative (loss)


def test_calculate_hurst_returns_dict(sample_returns: pd.Series):
    result = calculate_hurst(sample_returns)
    assert isinstance(result, dict)
    assert "hurst" in result
    assert "hurst_regime" in result
