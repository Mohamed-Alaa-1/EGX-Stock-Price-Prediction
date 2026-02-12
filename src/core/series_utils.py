"""
Shared PriceSeries → DataFrame helpers for quant modules.

Provides sorted bars, close series, and return calculations.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.schemas import PriceSeries


def to_dataframe(series: PriceSeries) -> pd.DataFrame:
    """
    Convert a PriceSeries to a sorted DataFrame with columns:
    date, open, high, low, close, volume.

    Sorted ascending by date.
    """
    rows = [
        {
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in series.bars
    ]
    df = pd.DataFrame(rows)
    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    return df


def close_series(series: PriceSeries) -> pd.Series:
    """
    Extract a sorted close-price Series indexed by date.
    """
    df = to_dataframe(series)
    return df.set_index("date")["close"]


def simple_returns(series: PriceSeries) -> pd.Series:
    """
    Compute simple (arithmetic) daily returns from close prices.

    r_t = P_t / P_{t-1} - 1
    """
    closes = close_series(series)
    return closes.pct_change().dropna()


def log_returns(series: PriceSeries) -> pd.Series:
    """
    Compute log daily returns from close prices.

    l_t = log(P_t) - log(P_{t-1})
    """
    closes = close_series(series)
    return np.log(closes / closes.shift(1)).dropna()


def get_returns(series: PriceSeries, return_type: str = "simple") -> pd.Series:
    """
    Get returns of the specified type.

    Args:
        series: PriceSeries
        return_type: "simple" or "log"

    Returns:
        pd.Series of returns indexed by date
    """
    if return_type == "log":
        return log_returns(series)
    return simple_returns(series)
