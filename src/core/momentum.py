"""
Momentum calculation for technical signals.
"""

from typing import Optional
from core.schemas import PriceSeries


def calculate_momentum(
    series: PriceSeries,
    periods: int = 10,
) -> Optional[float]:
    """
    Calculate price momentum.

    Momentum = (Current - N periods ago) / N periods ago * 100

    Args:
        series: Price series
        periods: Lookback periods

    Returns:
        Momentum percentage or None if insufficient data
    """
    if len(series.bars) < periods + 1:
        return None

    current = series.bars[-1].close
    past = series.bars[-(periods + 1)].close

    momentum = ((current - past) / past) * 100
    return momentum


def get_momentum_signal(momentum: Optional[float]) -> str:
    """
    Get momentum signal interpretation.

    Args:
        momentum: Momentum percentage

    Returns:
        Signal string: "Strong Bullish", "Bullish", "Neutral", "Bearish", "Strong Bearish"
    """
    if momentum is None:
        return "Unknown"

    if momentum > 5:
        return "Strong Bullish"
    elif momentum > 2:
        return "Bullish"
    elif momentum > -2:
        return "Neutral"
    elif momentum > -5:
        return "Bearish"
    else:
        return "Strong Bearish"
