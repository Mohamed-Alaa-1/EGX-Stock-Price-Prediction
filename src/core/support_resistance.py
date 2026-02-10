"""
Support and resistance level detection.
"""

from typing import NamedTuple

import numpy as np

from core.schemas import PriceSeries


class SupportResistanceLevel(NamedTuple):
    """Support or resistance level."""
    price: float
    type: str  # "support" or "resistance"
    strength: int  # Number of touches


def find_support_resistance_levels(
    series: PriceSeries,
    window: int = 20,
    tolerance: float = 0.02,
) -> list[SupportResistanceLevel]:
    """
    Find support and resistance levels using local extrema.
    
    Simple heuristic:
    - Find local minima (support) and maxima (resistance)
    - Cluster nearby levels within tolerance
    - Return strongest levels
    
    Args:
        series: Price series
        window: Rolling window for extrema detection
        tolerance: Price tolerance for clustering (as fraction of price)
        
    Returns:
        List of support/resistance levels
    """
    if len(series.bars) < window:
        return []
    
    sorted_bars = sorted(series.bars, key=lambda b: b.date)
    lows = np.array([bar.low for bar in sorted_bars])
    highs = np.array([bar.high for bar in sorted_bars])
    
    levels = []
    
    # Find local minima (support)
    for i in range(window, len(lows) - window):
        window_lows = lows[i - window : i + window + 1]
        if lows[i] == window_lows.min():
            levels.append((lows[i], "support"))
    
    # Find local maxima (resistance)
    for i in range(window, len(highs) - window):
        window_highs = highs[i - window : i + window + 1]
        if highs[i] == window_highs.max():
            levels.append((highs[i], "resistance"))
    
    if not levels:
        return []
    
    # Cluster nearby levels
    clustered = []
    for price, level_type in levels:
        # Find existing cluster
        found_cluster = False
        for cluster in clustered:
            if cluster["type"] == level_type:
                cluster_price = cluster["price"]
                if abs(price - cluster_price) / cluster_price < tolerance:
                    # Add to cluster
                    cluster["prices"].append(price)
                    cluster["count"] += 1
                    cluster["price"] = sum(cluster["prices"]) / len(cluster["prices"])
                    found_cluster = True
                    break
        
        # Create new cluster
        if not found_cluster:
            clustered.append({
                "price": price,
                "type": level_type,
                "prices": [price],
                "count": 1,
            })
    
    # Convert to SupportResistanceLevel
    result = [
        SupportResistanceLevel(
            price=cluster["price"],
            type=cluster["type"],
            strength=cluster["count"],
        )
        for cluster in clustered
    ]
    
    # Sort by strength (descending)
    result.sort(key=lambda lvl: lvl.strength, reverse=True)
    
    # Return top levels
    return result[:10]
