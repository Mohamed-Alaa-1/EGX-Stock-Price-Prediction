"""
Price data normalization and validation.
"""

from datetime import date
from typing import Optional

from core.schemas import PriceBar, PriceSeries


def normalize_price_series(series: PriceSeries) ->PriceSeries:
    """
    Normalize and validate price series.
    
    - Remove duplicate dates
    - Sort by date
    - Validate OHLC relationships
    
    Args:
        series: Input price series
        
    Returns:
        Normalized price series
        
    Raises:
        ValueError: If series is invalid
    """
    if not series.bars:
        raise ValueError("Price series has no bars")
    
    # Remove duplicates (keep last)
    seen_dates: dict[date, PriceBar] = {}
    for bar in series.bars:
        seen_dates[bar.date] = bar
    
    # Sort by date
    unique_bars = sorted(seen_dates.values(), key=lambda b: b.date)
    
    # Validate each bar (Pydantic already validates OHLC relationships)
    # Just create new PriceSeries to trigger validation
    return PriceSeries(
        symbol=series.symbol,
        bars=unique_bars,
        source=series.source,
        last_updated_at=series.last_updated_at,
    )


def filter_by_date_range(
    series: PriceSeries,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> PriceSeries:
    """
    Filter price series by date range.
    
    Args:
        series: Input price series
        start_date: Optional start date (inclusive)
        end_date: Optional end date (inclusive)
        
    Returns:
        Filtered price series
    """
    filtered_bars = series.bars
    
    if start_date:
        filtered_bars = [b for b in filtered_bars if b.date >= start_date]
    
    if end_date:
        filtered_bars = [b for b in filtered_bars if b.date <= end_date]
    
    if not filtered_bars:
        raise ValueError(f"No data in range {start_date} to {end_date}")
    
    return PriceSeries(
        symbol=series.symbol,
        bars=filtered_bars,
        source=series.source,
        last_updated_at=series.last_updated_at,
    )


def validate_sufficient_history(
    series: PriceSeries,
    minimum_days: int = 30,
) -> bool:
    """
    Check if series has sufficient history.
    
    Args:
        series: Price series to check
        minimum_days: Minimum number of bars required
        
    Returns:
        True if sufficient, False otherwise
    """
    return len(series.bars) >= minimum_days
