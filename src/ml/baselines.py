"""
Baseline forecasting methods.
"""

from core.schemas import PriceSeries


def naive_last_close(series: PriceSeries) -> float:
    """
    Naive baseline: predict next close = last close.

    Args:
        series: Historical price series

    Returns:
        Last closing price
    """
    return series.get_latest_close()


def sma_baseline(series: PriceSeries, window: int = 5) -> float:
    """
    Simple moving average baseline.

    Args:
        series: Historical price series
        window: SMA window size

    Returns:
        SMA of last N closes
    """
    closes = [bar.close for bar in sorted(series.bars, key=lambda b: b.date)]
    if len(closes) < window:
        return closes[-1]

    return sum(closes[-window:]) / window


def get_baseline(series: PriceSeries, method: str = "naive", **kwargs) -> float:
    """
    Get baseline forecast using specified method.

    Args:
        series: Historical price series
        method: Baseline method ("naive" or "sma")

    Returns:
        Baseline prediction
    """
    if method == "naive":
        return naive_last_close(series)
    elif method == "sma":
        window = kwargs.get("window", 5)
        return sma_baseline(series, window=window)
    else:
        return naive_last_close(series)
