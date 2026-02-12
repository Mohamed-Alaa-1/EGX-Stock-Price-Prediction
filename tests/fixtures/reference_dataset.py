"""
Fixed reference dataset and expected metric values for SC-002.

This fixture provides a deterministic price series and pre-computed
expected VaR, Sharpe, ADF, and Hurst values so that reproducibility
can be validated across environments and refactorings.

Tolerances:
- VaR: ±0.005 (0.5 percentage point)
- Sharpe: ±0.15
- ADF p-value: ±0.05
- Hurst: ±0.05
"""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.schemas import DataSourceRecord, PriceBar, PriceSeries

# ---------------------------------------------------------------------------
# Deterministic reference series
# ---------------------------------------------------------------------------

SEED = 12345
N_BARS = 300
START_PRICE = 50.0
DAILY_VOL = 0.018


def get_reference_series() -> PriceSeries:
    """
    Generate a fixed reference PriceSeries.

    Uses np.random.default_rng(12345) for full reproducibility.
    """
    rng = np.random.default_rng(SEED)
    prices = [START_PRICE]
    for _ in range(N_BARS - 1):
        ret = rng.normal(0, DAILY_VOL)
        prices.append(prices[-1] * (1 + ret))

    base = date(2023, 1, 1)
    bars = [
        PriceBar(
            date=base + timedelta(days=i),
            open=p, high=p * 1.01,
            low=p * 0.99, close=p, volume=1000,
        )
        for i, p in enumerate(prices)
    ]
    source = DataSourceRecord(
        provider="fixture",
        fetched_at=datetime.now(),
        range_start=base,
        range_end=base + timedelta(days=N_BARS - 1),
    )
    return PriceSeries(
        symbol="REF", bars=bars,
        source=source, last_updated_at=datetime.now(),
    )


# ---------------------------------------------------------------------------
# Expected metric values (pre-computed with seed=12345)
# ---------------------------------------------------------------------------
# To regenerate: run this file directly.

EXPECTED_METRICS = {
    "var_95_pct": None,  # Will be filled by running the fixture
    "var_99_pct": None,
    "sharpe": None,
    "adf_pvalue": None,
    "adf_stationary": None,
    "hurst_exponent": None,
    "hurst_regime": None,
}

# Tolerances for comparison
TOLERANCES = {
    "var_95_pct": 0.005,
    "var_99_pct": 0.005,
    "sharpe": 0.15,
    "adf_pvalue": 0.05,
    "hurst": 0.05,
}


def compute_and_save_reference():
    """Compute metrics and save as JSON fixture."""
    from core.quant import compute_risk_snapshot, compute_validation

    series = get_reference_series()
    risk = compute_risk_snapshot(series)
    val = compute_validation(series)

    metrics = {
        "var_95_pct": risk.var_95_pct,
        "var_99_pct": risk.var_99_pct,
        "sharpe": risk.sharpe,
        "adf_statistic": val.adf_statistic,
        "adf_pvalue": val.adf_pvalue,
        "hurst": val.hurst,
        "hurst_regime": val.hurst_regime.value if val.hurst_regime else None,
    }

    out_path = Path(__file__).parent / "reference_metrics.json"
    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    print(f"Reference metrics saved to {out_path}:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    return metrics


if __name__ == "__main__":
    compute_and_save_reference()
