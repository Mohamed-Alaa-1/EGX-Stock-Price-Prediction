"""
CSV import provider for user-supplied data.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from core.config import Config
from core.schemas import DataSourceRecord, PriceBar, PriceSeries
from data.providers.base import BaseProvider


class CSVProvider(BaseProvider):
    """
    CSV import provider.
    
    Looks for CSV files in data/csv_imports/{SYMBOL}.csv
    Expected columns: date, open, high, low, close, [volume], [adjusted_close]
    """
    
    CSV_IMPORTS_DIR = Config.DATA_DIR / "csv_imports"
    
    @property
    def name(self) -> str:
        return "csv_import"
    
    def fetch(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        interval: str = "1d",
    ) -> Optional[PriceSeries]:
        """Load from local CSV file. Interval parameter is accepted but ignored for CSV."""
        csv_path = self.CSV_IMPORTS_DIR / f"{symbol.upper()}.csv"
        
        if not csv_path.exists():
            return None
        
        try:
            df = pd.read_csv(csv_path)
            
            # Normalize column names (case-insensitive)
            df.columns = [col.lower().strip() for col in df.columns]
            
            # Required columns
            required = ["date", "open", "high", "low", "close"]
            missing = [col for col in required if col not in df.columns]
            if missing:
                print(f"CSV for {symbol} missing columns: {missing}")
                return None
            
            # Parse dates
            df["date"] = pd.to_datetime(df["date"]).dt.date
            
            # Filter by date range
            if start_date:
                df = df[df["date"] >= start_date]
            if end_date:
                df = df[df["date"] <= end_date]
            
            if df.empty:
                return None
            
            # Convert to PriceBar objects
            bars = []
            for _, row in df.iterrows():
                try:
                    bar = PriceBar(
                        date=row["date"],
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]) if "volume" in row and pd.notna(row["volume"]) else None,
                        adjusted_close=float(row["adjusted_close"]) if "adjusted_close" in row and pd.notna(row["adjusted_close"]) else None,
                    )
                    bars.append(bar)
                except Exception as e:
                    print(f"Skipping invalid row in CSV for {symbol}: {e}")
                    continue
            
            if not bars:
                return None
            
            # Build source record
            source = DataSourceRecord(
                provider=self.name,
                provider_details={"csv_path": str(csv_path)},
                fetched_at=datetime.now(),
                range_start=min(bar.date for bar in bars),
                range_end=max(bar.date for bar in bars),
            )
            
            return PriceSeries(
                symbol=symbol.upper(),
                bars=bars,
                source=source,
                last_updated_at=datetime.now(),
            )
        
        except Exception as e:
            print(f"CSV import error for {symbol}: {e}")
            return None
    
    def supports_symbol(self, symbol: str) -> bool:
        """Check if CSV file exists."""
        csv_path = self.CSV_IMPORTS_DIR / f"{symbol.upper()}.csv"
        return csv_path.exists()
