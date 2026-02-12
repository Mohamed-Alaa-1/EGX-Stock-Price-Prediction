"""
TradingView data provider using tradingview-ta package.

Provides real-time technical analysis and price data from TradingView
for EGX (Egyptian Exchange) stocks.
"""

from datetime import date, datetime
from typing import Optional

from core.schemas import DataSourceRecord, PriceBar, PriceSeries
from data.providers.base import BaseProvider
from data.symbol_config import get_symbol_config, is_tradingview_supported


# Interval mapping from our format to tradingview-ta format
_INTERVAL_MAP: dict[str, str] = {}

try:
    from tradingview_ta import TA_Handler, Interval

    _INTERVAL_MAP = {
        "1m": Interval.INTERVAL_1_MINUTE,
        "5m": Interval.INTERVAL_5_MINUTES,
        "15m": Interval.INTERVAL_15_MINUTES,
        "1h": Interval.INTERVAL_1_HOUR,
        "4h": Interval.INTERVAL_4_HOURS,
        "1d": Interval.INTERVAL_1_DAY,
        "1wk": Interval.INTERVAL_1_WEEK,
        "1mo": Interval.INTERVAL_1_MONTH,
    }
except ImportError:
    TA_Handler = None  # type: ignore
    Interval = None  # type: ignore


class TradingViewProvider(BaseProvider):
    """
    Provider using tradingview-ta library.

    Fetches current technical analysis snapshot from TradingView
    for EGX stocks (screener='egypt', exchange='EGX').
    """

    @property
    def name(self) -> str:
        return "tradingview"

    def fetch(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        interval: str = "1d",
    ) -> Optional[PriceSeries]:
        """
        Fetch current price data from TradingView.

        Note: tradingview-ta provides a current snapshot (not full history).
        This creates a single PriceBar from the current data.

        Args:
            symbol: Stock symbol (e.g. 'COMI')
            start_date: Ignored (TradingView provides current data only)
            end_date: Ignored
            interval: Interval for analysis

        Returns:
            PriceSeries with current data, or None on failure
        """
        if TA_Handler is None:
            print("[TradingViewProvider] tradingview-ta not installed")
            return None

        # Check if symbol is supported by TradingView
        if not is_tradingview_supported(symbol):
            print(f"[TradingViewProvider] {symbol} not configured for TradingView")
            return None

        tv_interval = _INTERVAL_MAP.get(interval, _INTERVAL_MAP.get("1d"))
        if tv_interval is None:
            print(f"[TradingViewProvider] Unknown interval: {interval}")
            return None

        # Get symbol configuration
        config = get_symbol_config(symbol)
        clean_symbol = symbol.upper().replace(".CA", "").replace(".CAI", "")

        try:
            handler = TA_Handler(
                symbol=config.tv_symbol,
                screener=config.screener,
                exchange=config.exchange,
                interval=tv_interval,
            )

            analysis = handler.get_analysis()

            # Extract price data from indicators
            indicators = analysis.indicators
            current_close = indicators.get("close")
            current_open = indicators.get("open")
            current_high = indicators.get("high")
            current_low = indicators.get("low")
            current_volume = indicators.get("volume")

            if current_close is None:
                print(f"[TradingViewProvider] No close price for {clean_symbol}")
                return None

            # Create a PriceBar from current data
            bar = PriceBar(
                date=datetime.now().date(),
                open=float(current_open) if current_open else float(current_close),
                high=float(current_high) if current_high else float(current_close),
                low=float(current_low) if current_low else float(current_close),
                close=float(current_close),
                volume=float(current_volume) if current_volume else None,
            )

            # Build source record
            source = DataSourceRecord(
                provider=self.name,
                provider_details={
                    "symbol": config.tv_symbol,
                    "screener": config.screener,
                    "exchange": config.exchange,
                    "interval": interval,
                    "recommendation": str(analysis.summary.get("RECOMMENDATION", "N/A")),
                },
                fetched_at=datetime.now(),
                range_start=bar.date,
                range_end=bar.date,
            )

            print(
                f"[TradingViewProvider] {clean_symbol}: close={bar.close}, "
                f"recommendation={analysis.summary.get('RECOMMENDATION', 'N/A')}"
            )

            return PriceSeries(
                symbol=clean_symbol,
                bars=[bar],
                source=source,
                last_updated_at=datetime.now(),
            )

        except Exception as e:
            print(f"[TradingViewProvider] Error fetching {clean_symbol}: {e}")
            return None

    def supports_symbol(self, symbol: str) -> bool:
        """TradingView supports EGX symbols."""
        return True
