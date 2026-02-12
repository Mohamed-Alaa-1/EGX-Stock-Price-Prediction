"""
Base provider interface for historical price data.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from core.schemas import PriceSeries


class BaseProvider(ABC):
    """Abstract base class for price data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    def fetch(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        interval: str = "1d",
    ) -> Optional[PriceSeries]:
        """
        Fetch historical price data.

        Args:
            symbol: Stock symbol
            start_date: Optional start date
            end_date: Optional end date
            interval: Data interval (1d, 1wk, 1mo)

        Returns:
            PriceSeries if successful, None on failure
        """
        pass

    @abstractmethod
    def supports_symbol(self, symbol: str) -> bool:
        """
        Check if provider supports a given symbol.

        Args:
            symbol: Stock symbol

        Returns:
            True if supported, False otherwise
        """
        pass
