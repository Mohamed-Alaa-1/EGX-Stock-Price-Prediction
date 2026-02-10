"""
Price data service for UI components.
"""

from typing import Optional
from core.schemas import PriceSeries
from data.providers.registry import get_provider_registry
from data.cache_store import CacheStore


class PriceService:
    """Service for fetching price data."""

    def __init__(self):
        self.cache = CacheStore()
        self.provider_registry = get_provider_registry()

    def get_series(self, symbol: str, use_cache: bool = True, interval: str = "1d") -> PriceSeries:
        """
        Get price series for symbol.

        Args:
            symbol: Stock symbol
            use_cache: Whether to use cached data
            interval: Data interval (1d, 1wk, 1mo)

        Returns:
            PriceSeries

        Raises:
            ValueError: If no data available for symbol
        """
        symbol = symbol.upper()
        print(f"[PriceService] get_series({symbol}, use_cache={use_cache}, interval={interval})")

        # Try cache first
        if use_cache:
            cached = self.cache.load(symbol)
            if cached:
                print(f"[PriceService] Cache hit for {symbol} ({len(cached.bars)} bars)")
                return cached
            print(f"[PriceService] Cache miss for {symbol}")

        # Fetch from providers
        series = self.provider_registry.fetch_with_fallback(symbol, interval=interval)

        if series is None:
            print(f"[PriceService] ERROR: No data available for {symbol}")
            raise ValueError(f"No price data available for {symbol}. Check data providers.")

        print(f"[PriceService] Fetched {len(series.bars)} bars for {symbol}")

        # Cache result
        self.cache.save(series)

        return series
