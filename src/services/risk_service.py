"""
Risk snapshot orchestration service.

Builds RiskMetricsSnapshot from PriceSeries + Config defaults.
"""

from __future__ import annotations

from core.config import Config
from core.quant import compute_risk_snapshot
from core.schemas import PriceSeries, RiskMetricsSnapshot


class RiskService:
    """Service for computing per-ticker risk metrics."""

    @staticmethod
    def compute(
        series: PriceSeries,
        lookback_days: int = Config.DEFAULT_RISK_LOOKBACK_DAYS,
        return_type: str = Config.DEFAULT_RETURN_TYPE,
        risk_free_rate: float = Config.DEFAULT_RISK_FREE_RATE,
    ) -> RiskMetricsSnapshot:
        """
        Compute risk snapshot (VaR 95/99, Sharpe) for a single ticker.

        Args:
            series: Historical price data.
            lookback_days: Rolling lookback window.
            return_type: "simple" or "log".
            risk_free_rate: Assumed risk-free rate (default 0, labeled).

        Returns:
            RiskMetricsSnapshot with computed metrics or nulls + warnings.
        """
        return compute_risk_snapshot(
            series,
            lookback_days=lookback_days,
            return_type=return_type,
            risk_free_rate=risk_free_rate,
        )
