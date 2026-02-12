"""
Portfolio orchestration service.

Aligns multi-symbol return windows, computes mu/cov,
calls ml.portfolio optimizers, returns PortfolioOptimizationResult.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from core.config import Config
from core.schemas import (
    PortfolioOptimizationResult,
    PriceSeries,
    ReturnType,
)
from core.series_utils import get_returns
from ml.portfolio import (
    efficient_frontier,
    min_variance_portfolio,
    risk_parity_portfolio,
    stabilize_covariance,
    variance_contributions,
)


class PortfolioService:
    """High-level portfolio optimization API consumed by the UI layer."""

    @staticmethod
    def optimize(
        series_by_symbol: dict[str, PriceSeries],
        lookback_days: int | None = None,
        return_type: str = "simple",
        shrinkage_alpha: float | None = None,
        diagonal_loading_lambda: float | None = None,
        max_frontier_points: int | None = None,
        w_max: float = 1.0,
    ) -> PortfolioOptimizationResult:
        """
        Run MPT + risk parity on a set of symbols.

        Parameters
        ----------
        series_by_symbol : dict mapping symbol → PriceSeries
        lookback_days : trailing window (default from Config)
        return_type : "simple" or "log"
        shrinkage_alpha : covariance shrinkage intensity
        diagonal_loading_lambda : ridge term
        max_frontier_points : frontier grid size
        w_max : max weight per asset

        Returns
        -------
        PortfolioOptimizationResult
        """
        lookback_days = lookback_days or Config.DEFAULT_PORTFOLIO_LOOKBACK_DAYS
        shrinkage_alpha = (
            shrinkage_alpha
            if shrinkage_alpha is not None
            else Config.DEFAULT_SHRINKAGE_ALPHA
        )
        diagonal_loading_lambda = (
            diagonal_loading_lambda
            if diagonal_loading_lambda is not None
            else Config.DEFAULT_DIAGONAL_LOADING_LAMBDA
        )
        max_frontier_points = max_frontier_points or Config.MAX_FRONTIER_POINTS
        min_overlap = Config.MIN_OVERLAP_DAYS

        warnings: list[str] = []
        symbols = sorted(series_by_symbol.keys())

        if len(symbols) < 2:
            raise ValueError("Portfolio optimization requires at least 2 symbols")

        # Build aligned returns matrix (inner join on dates)
        returns_map: dict[str, pd.Series] = {}
        for sym in symbols:
            ret = get_returns(series_by_symbol[sym], return_type=return_type)
            # Trim to lookback
            if len(ret) > lookback_days:
                ret = ret.iloc[-lookback_days:]
            returns_map[sym] = ret

        # Inner join
        ret_df = pd.DataFrame(returns_map)
        ret_df = ret_df.dropna()

        if len(ret_df) < min_overlap:
            raise ValueError(
                f"Insufficient overlap: {len(ret_df)} days (need ≥ {min_overlap}). "
                f"Check date ranges for: {', '.join(symbols)}"
            )

        if len(ret_df) < lookback_days:
            warnings.append(
                f"Only {len(ret_df)} overlapping days available "
                f"(requested {lookback_days})"
            )

        returns_matrix = ret_df.values  # (T, N)
        mu = returns_matrix.mean(axis=0)  # (N,)

        # Stabilize covariance
        cov = stabilize_covariance(
            returns_matrix,
            shrinkage_alpha=shrinkage_alpha,
            diagonal_loading_lambda=diagonal_loading_lambda,
        )

        # MPT minimum-variance
        mv_result = min_variance_portfolio(cov, w_max=w_max)
        mpt_weights = dict(zip(symbols, mv_result["weights"].tolist()))

        if not mv_result["success"]:
            warnings.append("Min-variance optimizer did not converge; using equal weights")

        # Efficient frontier
        frontier_raw = efficient_frontier(
            mu, cov, n_points=max_frontier_points, w_max=w_max,
        )
        # Convert to list of dicts with symbol-keyed weights
        frontier: list[dict] = []
        for pt in frontier_raw:
            frontier.append({
                "target_return": pt["target_return"],
                "weights": dict(zip(symbols, pt["weights"])),
                "volatility": pt["volatility"],
                "expected_return": pt["expected_return"],
                "sharpe": pt["sharpe"],
            })

        # Risk parity
        rp_result = risk_parity_portfolio(cov, w_max=w_max)
        rp_weights = dict(zip(symbols, rp_result["weights"].tolist()))
        risk_contribs = dict(
            zip(symbols, rp_result["pct_risk_contributions"].tolist()),
        )

        if not rp_result["success"]:
            warnings.append("Risk parity optimizer did not converge; using equal weights")

        # Portfolio volatility (on min-var weights)
        _, port_var = variance_contributions(mv_result["weights"], cov)

        as_of = ret_df.index[-1]
        if isinstance(as_of, pd.Timestamp):
            as_of = as_of.date()
        elif not isinstance(as_of, date):
            as_of = date.today()

        return PortfolioOptimizationResult(
            symbols=symbols,
            as_of_date=as_of,
            lookback_days=len(ret_df),
            return_type=ReturnType(return_type),
            constraints={"w_max": w_max, "long_only": True},
            mu=dict(zip(symbols, mu.tolist())),
            cov_method=f"sample+diagonal_shrinkage(alpha={shrinkage_alpha})",
            shrinkage_alpha=shrinkage_alpha,
            mpt_min_variance_weights=mpt_weights,
            mpt_frontier=frontier,
            risk_parity_weights=rp_weights,
            risk_contributions=risk_contribs,
            portfolio_volatility=float(np.sqrt(port_var)),
            warnings=warnings,
        )
