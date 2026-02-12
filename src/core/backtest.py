"""
Vectorized daily backtester with EGX transaction cost model.

Signal-at-t → exposure-on-(t+1)-close convention (no lookahead).
Costs applied via turnover: net_ret = gross_ret - cost_rate * turnover.

Supports RSI, MACD, and EMA crossover strategies.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from core.indicators import calculate_ema, calculate_macd, calculate_rsi
from core.schemas import (
    BacktestRun,
    BacktestStrategy,
    PriceSeries,
    TransactionCostModel,
)
from core.series_utils import to_dataframe

# ---------------------------------------------------------------------------
# Signal generators
# ---------------------------------------------------------------------------


def _rsi_signal(
    df: pd.DataFrame,
    series: PriceSeries,
    params: dict[str, Any],
) -> pd.Series:
    """
    Long when RSI < oversold, flat when RSI > overbought.

    Returns a Series of weights (0 or 1) aligned with df index.
    """
    period = params.get("period", 14)
    oversold = params.get("oversold", 30)
    overbought = params.get("overbought", 70)

    rsi = calculate_rsi(series, period=period)
    # Align rsi (positional) with df index
    rsi = rsi.values[: len(df)]
    rsi_series = pd.Series(rsi, index=df.index)

    # Binary signal: 1 when oversold, 0 when overbought, carry forward otherwise
    signal = pd.Series(np.nan, index=df.index)
    signal[rsi_series < oversold] = 1.0
    signal[rsi_series > overbought] = 0.0
    signal = signal.ffill().fillna(0.0)
    return signal


def _macd_signal(
    df: pd.DataFrame,
    series: PriceSeries,
    params: dict[str, Any],
) -> pd.Series:
    """
    Long when MACD line > signal line (bullish crossover), flat otherwise.
    """
    fast = params.get("fast_period", 12)
    slow = params.get("slow_period", 26)
    sig = params.get("signal_period", 9)

    macd_line, signal_line, _ = calculate_macd(
        series, fast_period=fast, slow_period=slow, signal_period=sig,
    )
    macd_arr = macd_line.values[: len(df)]
    sig_arr = signal_line.values[: len(df)]

    signal = pd.Series(0.0, index=df.index)
    signal[macd_arr > sig_arr] = 1.0
    return signal


def _ema_signal(
    df: pd.DataFrame,
    series: PriceSeries,
    params: dict[str, Any],
) -> pd.Series:
    """
    Long when close > EMA (trend following), flat otherwise.
    """
    period = params.get("period", 20)
    ema = calculate_ema(series, period=period)
    ema_arr = ema.values[: len(df)]

    signal = pd.Series(0.0, index=df.index)
    signal[df["close"].values > ema_arr] = 1.0
    return signal


_SIGNAL_DISPATCH = {
    BacktestStrategy.RSI: _rsi_signal,
    BacktestStrategy.MACD: _macd_signal,
    BacktestStrategy.EMA: _ema_signal,
}


# ---------------------------------------------------------------------------
# Core backtester
# ---------------------------------------------------------------------------


def run_backtest(
    series: PriceSeries,
    strategy: BacktestStrategy,
    strategy_params: dict[str, Any] | None = None,
    cost_model: TransactionCostModel | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> BacktestRun:
    """
    Vectorized backtest of a single-asset long/flat strategy.

    Parameters
    ----------
    series : PriceSeries
        Daily price bars.
    strategy : BacktestStrategy
        Which signal to use (RSI / MACD / EMA).
    strategy_params : dict, optional
        Strategy-specific parameters.
    cost_model : TransactionCostModel, optional
        Commission + stamp duty model.  Defaults to EGX defaults.
    start_date, end_date : date, optional
        Restrict evaluation window.  None = use all available data.

    Returns
    -------
    BacktestRun
        Populated result with gross/net metrics, drawdown, turnover, trade count.
    """
    strategy_params = strategy_params or {}
    cost_model = cost_model or TransactionCostModel()
    warnings: list[str] = []

    # Prepare price DataFrame
    df = to_dataframe(series)

    if start_date is not None:
        df = df[df["date"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        df = df[df["date"] <= pd.Timestamp(end_date)]

    df = df.reset_index(drop=True)

    if len(df) < 30:
        return BacktestRun(
            run_id=str(uuid.uuid4()),
            symbol=series.symbol,
            strategy=strategy,
            strategy_params=strategy_params,
            start_date=df["date"].iloc[0].date() if len(df) else date.today(),
            end_date=df["date"].iloc[-1].date() if len(df) else date.today(),
            cost_model=cost_model,
            warnings=["Insufficient data for backtesting (< 30 bars)"],
        )

    # Generate signal: weight_t ∈ {0, 1}
    gen = _SIGNAL_DISPATCH.get(strategy)
    if gen is None:
        raise ValueError(f"Unknown strategy: {strategy}")

    weight = gen(df, series, strategy_params)

    # Daily returns (close-to-close)
    daily_ret = df["close"].pct_change().fillna(0.0)

    # Gross return: exposure uses YESTERDAY's weight → shift weight by 1
    shifted_weight = weight.shift(1).fillna(0.0)
    gross_daily = shifted_weight * daily_ret

    # Turnover: absolute change in weight
    turnover_daily = shifted_weight.diff().abs().fillna(0.0)

    # Cost per bar
    cost_rate = cost_model.total_cost_rate
    cost_daily = turnover_daily * cost_rate

    # Net return
    net_daily = gross_daily - cost_daily

    # Cumulative
    gross_cum = (1 + gross_daily).cumprod()
    net_cum = (1 + net_daily).cumprod()

    gross_total_return = float(gross_cum.iloc[-1] - 1)
    net_total_return = float(net_cum.iloc[-1] - 1)

    # CAGR
    n_days = len(df)
    years = n_days / 252
    if years > 0:
        gross_cagr = float((1 + gross_total_return) ** (1 / years) - 1)
        net_cagr = float((1 + net_total_return) ** (1 / years) - 1)
    else:
        gross_cagr = None
        net_cagr = None

    # Max drawdown (on net equity curve)
    net_peak = net_cum.cummax()
    drawdown = (net_cum - net_peak) / net_peak
    max_drawdown = float(drawdown.min())

    # Sharpe (annualized, rf=0)
    if gross_daily.std() > 0:
        gross_sharpe = float(gross_daily.mean() / gross_daily.std() * np.sqrt(252))
    else:
        gross_sharpe = None
        warnings.append("Zero volatility in gross returns; Sharpe undefined")

    if net_daily.std() > 0:
        net_sharpe = float(net_daily.mean() / net_daily.std() * np.sqrt(252))
    else:
        net_sharpe = None

    # Turnover & costs
    total_turnover = float(turnover_daily.sum())
    total_costs = float(cost_daily.sum())
    trade_count = int((turnover_daily > 0).sum())

    return BacktestRun(
        run_id=str(uuid.uuid4()),
        symbol=series.symbol,
        strategy=strategy,
        strategy_params=strategy_params,
        start_date=df["date"].iloc[0].date(),
        end_date=df["date"].iloc[-1].date(),
        cost_model=cost_model,
        gross_total_return=gross_total_return,
        net_total_return=net_total_return,
        gross_cagr=gross_cagr,
        net_cagr=net_cagr,
        gross_sharpe=gross_sharpe,
        net_sharpe=net_sharpe,
        max_drawdown=max_drawdown,
        turnover=total_turnover,
        total_costs_paid=total_costs,
        trade_count=trade_count,
        warnings=warnings,
    )
