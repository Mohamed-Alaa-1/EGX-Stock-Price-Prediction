"""
Trading calendar utilities for EGX.
"""

from datetime import date, datetime, timedelta
from typing import Optional


class TradingCalendar:
    """
    EGX trading calendar utilities.

    Currently implements weekend-only calendar.
    Future: could load EGX holiday list from config.
    """

    # EGX trades Sunday through Thursday
    EGX_TRADING_DAYS = {6, 0, 1, 2, 3}  # Sun=6, Mon=0, Tue=1, Wed=2, Thu=3

    @classmethod
    def is_trading_day(cls, dt: date) -> bool:
        """
        Check if a given date is a trading day.

        Args:
            dt: Date to check

        Returns:
            True if trading day, False otherwise
        """
        weekday = dt.weekday()
        return weekday in cls.EGX_TRADING_DAYS

    @classmethod
    def next_trading_day(cls, from_date: Optional[date] = None) -> date:
        """
        Get the next trading day after the given date.

        Args:
            from_date: Starting date (default: today)

        Returns:
            Next trading day
        """
        if from_date is None:
            from_date = date.today()

        candidate = from_date + timedelta(days=1)
        while not cls.is_trading_day(candidate):
            candidate += timedelta(days=1)

        return candidate

    @classmethod
    def previous_trading_day(cls, from_date: Optional[date] = None) -> date:
        """
        Get the previous trading day before the given date.

        Args:
            from_date: Starting date (default: today)

        Returns:
            Previous trading day
        """
        if from_date is None:
            from_date = date.today()

        candidate = from_date - timedelta(days=1)
        while not cls.is_trading_day(candidate):
            candidate -= timedelta(days=1)

        return candidate

    @classmethod
    def trading_days_between(cls, start_date: date, end_date: date) -> int:
        """
        Count trading days between two dates (inclusive).

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Number of trading days
        """
        if start_date > end_date:
            return 0

        count = 0
        current = start_date
        while current <= end_date:
            if cls.is_trading_day(current):
                count += 1
            current += timedelta(days=1)

        return count
