"""
Technical indicator calculations.
"""

import numpy as np
import pandas as pd

from core.schemas import PriceSeries


def calculate_rsi(series: PriceSeries, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        series: Price series
        period: RSI period
        
    Returns:
        Pandas Series with RSI values
    """
    closes = [bar.close for bar in sorted(series.bars, key=lambda b: b.date)]
    df = pd.DataFrame({"close": closes})
    
    # Calculate price changes
    delta = df["close"].diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Calculate average gain/loss
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(
    series: PriceSeries,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        series: Price series
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line EMA period
        
    Returns:
        Tuple of (MACD line, signal line, histogram)
    """
    closes = [bar.close for bar in sorted(series.bars, key=lambda b: b.date)]
    df = pd.DataFrame({"close": closes})
    
    # Calculate EMAs
    fast_ema = df["close"].ewm(span=fast_period, adjust=False).mean()
    slow_ema = df["close"].ewm(span=slow_period, adjust=False).mean()
    
    # MACD line
    macd_line = fast_ema - slow_ema
    
    # Signal line
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    
    # Histogram
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_ema(series: PriceSeries, period: int = 20) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    
    Args:
        series: Price series
        period: EMA period
        
    Returns:
        Pandas Series with EMA values
    """
    closes = [bar.close for bar in sorted(series.bars, key=lambda b: b.date)]
    df = pd.DataFrame({"close": closes})
    
    ema = df["close"].ewm(span=period, adjust=False).mean()
    
    return ema


def get_indicator_series(series: PriceSeries, indicator: str, **kwargs) -> pd.Series:
    """
    Get indicator series by name.
    
    Args:
        series: Price series
        indicator: Indicator name ("rsi", "macd", "ema")
        **kwargs: Indicator-specific parameters
        
    Returns:
        Pandas Series with indicator values
    """
    if indicator == "rsi":
        return calculate_rsi(series, period=kwargs.get("period", 14))
    elif indicator == "ema":
        return calculate_ema(series, period=kwargs.get("period", 20))
    elif indicator == "macd":
        macd_line, signal, histogram = calculate_macd(series)
        return macd_line
    else:
        raise ValueError(f"Unknown indicator: {indicator}")
