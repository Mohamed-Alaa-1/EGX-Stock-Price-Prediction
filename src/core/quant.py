"""
Quantitative finance utilities: VaR, Sharpe, ADF, Hurst.

All computations are local-first and use only free data.
Follows data-model.md schemas and research.md methodology.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from core.config import Config
from core.schemas import (
    HurstRegime,
    ReturnType,
    RiskMetricsSnapshot,
    StatisticalValidationResult,
)
from core.series_utils import PriceSeries, close_series, get_returns

# ---------------------------------------------------------------------------
# VaR + Sharpe (T007)
# ---------------------------------------------------------------------------

def compute_var(
    returns: pd.Series,
    confidence: float = 0.95,
) -> float | None:
    """
    Historical VaR at the given confidence level (as a negative % return).

    Uses the empirical quantile of the return distribution.
    Returns None if insufficient data.
    """
    if len(returns) < Config.MIN_OBSERVATIONS_RISK:
        return None
    quantile = returns.quantile(1 - confidence)
    return float(quantile)


def compute_sharpe(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    annualization_factor: float = 252.0,
) -> float | None:
    """
    Annualized Sharpe ratio.

    Sharpe = (mean_excess_return * sqrt(annualization)) / std(returns)
    Returns None if insufficient data or zero std.
    """
    if len(returns) < Config.MIN_OBSERVATIONS_RISK:
        return None
    daily_rf = risk_free_rate / annualization_factor
    excess = returns - daily_rf
    std = excess.std()
    if std == 0 or np.isnan(std):
        return None
    mean_excess = excess.mean()
    return float((mean_excess / std) * np.sqrt(annualization_factor))


def compute_risk_snapshot(
    series: PriceSeries,
    lookback_days: int = Config.DEFAULT_RISK_LOOKBACK_DAYS,
    return_type: str = Config.DEFAULT_RETURN_TYPE,
    risk_free_rate: float = Config.DEFAULT_RISK_FREE_RATE,
) -> RiskMetricsSnapshot:
    """
    Build a RiskMetricsSnapshot for a single ticker.

    Computes 1-day VaR at 95% and 99%, plus annualized Sharpe.
    """
    warnings: list[str] = []
    closes = close_series(series)
    last_close = float(closes.iloc[-1]) if len(closes) > 0 else None

    # Trim to lookback
    if len(closes) > lookback_days:
        closes = closes.iloc[-lookback_days:]

    returns = get_returns(series, return_type)
    if len(returns) > lookback_days:
        returns = returns.iloc[-lookback_days:]

    as_of = closes.index[-1].date() if len(closes) > 0 else date.today()

    # Compute metrics
    var_95 = compute_var(returns, 0.95)
    var_99 = compute_var(returns, 0.99)
    sharpe = compute_sharpe(returns, risk_free_rate)

    if var_95 is None:
        warnings.append(
            f"Insufficient data for VaR/Sharpe"
            f" ({len(returns)} obs,"
            f" need {Config.MIN_OBSERVATIONS_RISK})"
        )

    # Absolute VaR (in currency units)
    var_95_abs = float(var_95 * last_close) if var_95 is not None and last_close else None
    var_99_abs = float(var_99 * last_close) if var_99 is not None and last_close else None

    return RiskMetricsSnapshot(
        symbol=series.symbol,
        as_of_date=as_of,
        lookback_days=min(lookback_days, len(returns)),
        return_type=ReturnType(return_type),
        var_method=Config.DEFAULT_VAR_METHOD,
        var_95_pct=var_95,
        var_99_pct=var_99,
        var_95_abs=var_95_abs,
        var_99_abs=var_99_abs,
        sharpe=sharpe,
        risk_free_rate=risk_free_rate,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# ADF + Hurst (T008)
# ---------------------------------------------------------------------------

def compute_adf(
    returns: pd.Series,
    regression: str = "c",
    autolag: str = "AIC",
) -> dict:
    """
    Augmented Dickey-Fuller test on the given series.

    Returns a dict with adf_statistic, adf_pvalue, adf_used_lag,
    adf_nobs, adf_critical_values, adf_regression, adf_autolag.
    Returns nulls if insufficient data.
    """
    if len(returns) < Config.MIN_OBSERVATIONS_VALIDATION:
        return {
            "adf_statistic": None,
            "adf_pvalue": None,
            "adf_used_lag": None,
            "adf_nobs": None,
            "adf_critical_values": None,
            "adf_regression": regression,
            "adf_autolag": autolag,
        }

    from statsmodels.tsa.stattools import adfuller

    result = adfuller(returns.dropna().values, regression=regression, autolag=autolag)

    return {
        "adf_statistic": float(result[0]),
        "adf_pvalue": float(result[1]),
        "adf_used_lag": int(result[2]),
        "adf_nobs": int(result[3]),
        "adf_critical_values": {k: float(v) for k, v in result[4].items()},
        "adf_regression": regression,
        "adf_autolag": autolag,
    }


def compute_hurst(returns: pd.Series) -> dict:
    """
    Hurst exponent via aggregated variance (aggvar) method.

    H < 0.4  → mean-reverting
    0.4 ≤ H ≤ 0.6 → random-like
    H > 0.6  → trending

    Returns dict with hurst, hurst_method, hurst_r2, hurst_regime.
    """
    if len(returns) < Config.MIN_OBSERVATIONS_VALIDATION:
        return {
            "hurst": None,
            "hurst_method": "aggvar_increments",
            "hurst_r2": None,
            "hurst_regime": None,
        }

    data = returns.dropna().values
    n = len(data)

    # Build block sizes: powers of 2 up to n/4
    max_k = max(2, n // 4)
    ks = []
    k = 2
    while k <= max_k:
        ks.append(k)
        k *= 2

    if len(ks) < 3:
        return {
            "hurst": None,
            "hurst_method": "aggvar_increments",
            "hurst_r2": None,
            "hurst_regime": None,
        }

    log_k = []
    log_var = []

    for k in ks:
        # Aggregate data into blocks of size k
        n_blocks = n // k
        if n_blocks < 2:
            continue
        blocks = data[: n_blocks * k].reshape(n_blocks, k)
        block_means = blocks.mean(axis=1)
        v = block_means.var(ddof=1)
        if v > 0:
            log_k.append(np.log(k))
            log_var.append(np.log(v))

    if len(log_k) < 3:
        return {
            "hurst": None,
            "hurst_method": "aggvar_increments",
            "hurst_r2": None,
            "hurst_regime": None,
        }

    # OLS fit: log(var) = a + b * log(k) → H = 1 + b/2
    log_k_arr = np.array(log_k)
    log_var_arr = np.array(log_var)
    slope, intercept = np.polyfit(log_k_arr, log_var_arr, 1)

    hurst_val = 1.0 + slope / 2.0
    # Clamp to [0, 1]
    hurst_val = float(np.clip(hurst_val, 0.0, 1.0))

    # R² goodness of fit
    predicted = slope * log_k_arr + intercept
    ss_res = np.sum((log_var_arr - predicted) ** 2)
    ss_tot = np.sum((log_var_arr - log_var_arr.mean()) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else None

    # Classify regime
    if hurst_val < Config.HURST_MEAN_REVERTING_THRESHOLD:
        regime = HurstRegime.MEAN_REVERTING
    elif hurst_val > Config.HURST_TRENDING_THRESHOLD:
        regime = HurstRegime.TRENDING
    else:
        regime = HurstRegime.RANDOM_LIKE

    return {
        "hurst": hurst_val,
        "hurst_method": "aggvar_increments",
        "hurst_r2": r2,
        "hurst_regime": regime,
    }


def compute_validation(
    series: PriceSeries,
    lookback_days: int = Config.DEFAULT_VALIDATION_LOOKBACK_DAYS,
    return_type: str = Config.DEFAULT_RETURN_TYPE,
) -> StatisticalValidationResult:
    """
    Build a StatisticalValidationResult for a single ticker.

    Computes ADF + Hurst on the returns series and flags weak signals.
    """
    warnings: list[str] = []
    closes = close_series(series)

    if len(closes) > lookback_days:
        closes = closes.iloc[-lookback_days:]

    returns = get_returns(series, return_type)
    if len(returns) > lookback_days:
        returns = returns.iloc[-lookback_days:]

    as_of = closes.index[-1].date() if len(closes) > 0 else date.today()

    adf_result = compute_adf(returns)
    hurst_result = compute_hurst(returns)

    # Warnings
    if adf_result["adf_pvalue"] is not None:
        if adf_result["adf_pvalue"] > Config.ADF_SIGNIFICANCE_LEVEL:
            warnings.append(
                f"ADF test does not reject unit root "
                f"(p={adf_result['adf_pvalue']:.4f} "
                f"> {Config.ADF_SIGNIFICANCE_LEVEL}). "
                "Series may be non-stationary; prediction confidence should be cautious."
            )
    else:
        warnings.append("Insufficient data for ADF test.")

    if hurst_result["hurst"] is not None:
        h = hurst_result["hurst"]
        regime = hurst_result["hurst_regime"]
        if regime == HurstRegime.RANDOM_LIKE:
            warnings.append(
                f"Hurst exponent H={h:.3f} suggests random-walk-like behavior. "
                "Predictability may be limited."
            )
    else:
        warnings.append("Insufficient data for Hurst exponent.")

    return StatisticalValidationResult(
        symbol=series.symbol,
        as_of_date=as_of,
        lookback_days=min(lookback_days, len(returns)),
        series_tested=return_type + "_returns",
        **adf_result,
        **hurst_result,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Convenience aliases (001-investment-assistant / T010–T011)
# ---------------------------------------------------------------------------


def calculate_var(
    returns: pd.Series,
    confidence: float = 0.95,
) -> float | None:
    """Alias for :func:`compute_var` – used by StrategyEngine."""
    return compute_var(returns, confidence)


def calculate_hurst(returns: pd.Series) -> dict:
    """Alias for :func:`compute_hurst` – used by StrategyEngine."""
    return compute_hurst(returns)
