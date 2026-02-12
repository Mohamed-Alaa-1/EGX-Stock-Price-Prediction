"""
Signal validation orchestration service.

Computes ADF + Hurst + warnings from PriceSeries.
"""

from __future__ import annotations

from core.config import Config
from core.quant import compute_validation
from core.schemas import PriceSeries, StatisticalValidationResult


class SignalValidationService:
    """Service for computing statistical validation (ADF + Hurst)."""

    @staticmethod
    def validate(
        series: PriceSeries,
        lookback_days: int = Config.DEFAULT_VALIDATION_LOOKBACK_DAYS,
        return_type: str = Config.DEFAULT_RETURN_TYPE,
    ) -> StatisticalValidationResult:
        """
        Compute ADF + Hurst for a single ticker.

        Args:
            series: Historical price data.
            lookback_days: Rolling lookback window.
            return_type: "simple" or "log".

        Returns:
            StatisticalValidationResult with computed metrics or nulls + warnings.
        """
        return compute_validation(
            series,
            lookback_days=lookback_days,
            return_type=return_type,
        )
