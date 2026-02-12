"""
YFinance provider for free market data.
"""

from datetime import date, datetime
from typing import Optional

import yfinance as yf
import pandas as pd

from core.schemas import DataSourceRecord, PriceBar, PriceSeries
from data.providers.base import BaseProvider


class YFinanceProvider(BaseProvider):
    """
    Provider using yfinance library.

    Note: EGX coverage may be limited. Symbols might need suffix like .CA (Cairo).
    """

    @property
    def name(self) -> str:
        return "yfinance"

    def fetch(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        interval: str = "1d",
    ) -> Optional[PriceSeries]:
        """Fetch from yfinance."""
        try:
            # Special handling for forex/commodity symbols
            if symbol.upper() == "XAUUSD":
                ticker_symbols = ["GC=F", "XAUUSD=X"]  # Gold futures or forex pair
            else:
                # Try with .CA suffix for EGX
                ticker_symbols = [symbol, f"{symbol}.CA", f"{symbol}.CAI"]

            for ticker_symbol in ticker_symbols:
                try:
                    ticker = yf.Ticker(ticker_symbol)

                    # Fetch historical data
                    df = ticker.history(
                        start=start_date or "2020-01-01",
                        end=end_date or datetime.now().date(),
                        interval=interval,
                        auto_adjust=False,
                    )

                    if df.empty:
                        continue

                    # Normalize column names
                    df = df.rename(columns={
                        "Open": "open",
                        "High": "high",
                        "Low": "low",
                        "Close": "close",
                        "Volume": "volume",
                        "Adj Close": "adjusted_close",
                    })

                    # Convert to PriceBar objects
                    df = df.reset_index()
                    df["Date"] = pd.to_datetime(df["Date"]).dt.date

                    bars = []
                    for _, row in df.iterrows():
                        try:
                            bar = PriceBar(
                                date=row["Date"],
                                open=float(row["open"]),
                                high=float(row["high"]),
                                low=float(row["low"]),
                                close=float(row["close"]),
                                volume=float(row["volume"]) if pd.notna(row["volume"]) else None,
                                adjusted_close=float(row["adjusted_close"]) if pd.notna(row.get("adjusted_close")) else None,
                            )
                            bars.append(bar)
                        except Exception as e:
                            # Skip invalid rows
                            print(f"Skipping invalid row for {symbol}: {e}")
                            continue

                    if not bars:
                        continue

                    # Build source record
                    source = DataSourceRecord(
                        provider=self.name,
                        provider_details={"ticker_symbol": ticker_symbol},
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
                    print(f"Failed to fetch {ticker_symbol}: {e}")
                    continue

            print(f"yfinance: No data found for {symbol} with any suffix")
            return None

        except Exception as e:
            print(f"yfinance error for {symbol}: {e}")
            return None

    def supports_symbol(self, symbol: str) -> bool:
        """yfinance attempts all symbols."""
        return True
