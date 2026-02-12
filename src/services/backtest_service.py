"""
Backtest orchestration service.

Fetches the price series, delegates to core.backtest, and returns a BacktestRun.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from core.backtest import run_backtest
from core.schemas import BacktestRun, BacktestStrategy, TransactionCostModel
from data.providers.registry import get_provider_registry


class BacktestService:
    """High-level backtest API consumed by the UI layer."""

    @staticmethod
    def run(
        symbol: str,
        strategy: BacktestStrategy,
        strategy_params: dict[str, Any] | None = None,
        cost_model: TransactionCostModel | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> BacktestRun:
        """
        Run a backtest for a single symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol.
        strategy : BacktestStrategy
            RSI / MACD / EMA.
        strategy_params : dict, optional
            Strategy-specific parameters.
        cost_model : TransactionCostModel, optional
            EGX cost assumptions.
        start_date, end_date : date, optional
            Date window filter.

        Returns
        -------
        BacktestRun
        """
        registry = get_provider_registry()
        series = registry.fetch_with_fallback(symbol, interval="1d")

        if series is None:
            raise ValueError(f"No data available for {symbol}")

        return run_backtest(
            series=series,
            strategy=strategy,
            strategy_params=strategy_params,
            cost_model=cost_model,
            start_date=start_date,
            end_date=end_date,
        )
