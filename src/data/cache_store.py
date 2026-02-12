"""
Local cache storage for price data.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from core.config import Config
from core.schemas import DataSourceRecord, PriceBar, PriceSeries


class CacheStore:
    """
    Local cache for historical price data.
    Uses Parquet format for efficient storage.
    """
    
    @staticmethod
    def save(series: PriceSeries) -> None:
        """
        Save price series to cache.
        
        Args:
            series: Price series to cache
        """
        cache_path = Config.get_cache_path(series.symbol)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to DataFrame
        rows = [bar.model_dump() for bar in series.bars]
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        
        # Add metadata columns
        df["_cached_at"] = series.last_updated_at
        df["_provider"] = series.source.provider
        df["_fetched_at"] = series.source.fetched_at
        
        # Save to Parquet
        df.to_parquet(cache_path, index=False)
    
    @staticmethod
    def load(symbol: str) -> Optional[PriceSeries]:
        """
        Load price series from cache.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            PriceSeries if cached, None otherwise
        """
        cache_path = Config.get_cache_path(symbol)
        if not cache_path.exists():
            return None
        
        try:
            df = pd.read_parquet(cache_path)
            
            # Extract metadata
            cached_at = df["_cached_at"].iloc[0]
            provider = df["_provider"].iloc[0]
            fetched_at = df["_fetched_at"].iloc[0]
            
            # Drop metadata columns
            df = df.drop(columns=["_cached_at", "_provider", "_fetched_at"])
            
            # Convert back to PriceBar objects
            df["date"] = pd.to_datetime(df["date"]).dt.date
            bars = [PriceBar.model_validate(row) for row in df.to_dict("records")]
            
            # Build source record
            source = DataSourceRecord(
                provider=provider,
                fetched_at=fetched_at,
                range_start=min(bar.date for bar in bars),
                range_end=max(bar.date for bar in bars),
            )
            
            return PriceSeries(
                symbol=symbol,
                bars=bars,
                source=source,
                last_updated_at=cached_at,
            )
        
        except Exception as e:
            print(f"Warning: Failed to load cache for {symbol}: {e}")
            return None
    
    @staticmethod
    def exists(symbol: str) -> bool:
        """
        Check if symbol has cached data.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if cached, False otherwise
        """
        return Config.get_cache_path(symbol).exists()
    
    @staticmethod
    def clear(symbol: str) -> bool:
        """
        Clear cache for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if deleted, False if not found
        """
        cache_path = Config.get_cache_path(symbol)
        if cache_path.exists():
            cache_path.unlink()
            return True
        return False
    
    @staticmethod
    def clear_all() -> int:
        """
        Clear all cached data.
        
        Returns:
            Number of cache files deleted
        """
        count = 0
        if Config.CACHE_DIR.exists():
            for cache_file in Config.CACHE_DIR.glob("*.parquet"):
                cache_file.unlink()
                count += 1
        return count


def get_cache() -> CacheStore:
    """Get a CacheStore instance."""
    return CacheStore()
