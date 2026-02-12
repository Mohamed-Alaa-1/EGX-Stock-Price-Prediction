"""
GDR premium/discount calculation service.

Loads cross-listing mappings, fetches local + GDR + FX price series,
aligns dates, computes premium/discount, and returns a time series
with graceful degradation on missing inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from core.config import Config
from core.schemas import (
    GdrPremiumDiscountPoint,
    GdrPremiumDiscountSeries,
)
from core.series_utils import to_dataframe
from data.providers.registry import get_provider_registry


def _load_mappings(path: Path | None = None) -> list[dict]:
    """Load cross-listing mappings from JSON."""
    path = path or Config.CROSS_LISTINGS_PATH
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("mappings", [])


def get_mapping(local_symbol: str, path: Path | None = None) -> dict | None:
    """Find the cross-listing mapping for a local symbol."""
    for m in _load_mappings(path):
        if m.get("local_symbol", "").upper() == local_symbol.upper():
            return m
    return None


def list_mapped_symbols(path: Path | None = None) -> list[str]:
    """Return list of local symbols that have GDR mappings."""
    return [m["local_symbol"] for m in _load_mappings(path)]


class GdrBridgeService:
    """Compute premium/discount series for cross-listed stocks."""

    @staticmethod
    def compute(
        local_symbol: str,
        mapping_path: Path | None = None,
    ) -> GdrPremiumDiscountSeries:
        """
        Compute premium/discount time series.

        premium_pct = (
            (local_close - gdr_close_fx_adjusted * ratio)
            / (gdr_close_fx_adjusted * ratio) * 100
        )

        Returns a GdrPremiumDiscountSeries with graceful warnings on missing data.
        """
        mapping = get_mapping(local_symbol, mapping_path)
        if mapping is None:
            return GdrPremiumDiscountSeries(
                local_symbol=local_symbol.upper(),
                gdr_symbol="",
                fx_pair="",
                ratio_local_per_gdr=1.0,
                warnings=[f"No cross-listing mapping found for {local_symbol}"],
            )

        gdr_symbol = mapping["gdr_symbol"]
        fx_pair = mapping["fx_pair"]
        ratio = mapping.get("ratio_local_per_gdr", 1.0)

        registry = get_provider_registry()
        warnings: list[str] = []

        # Fetch local series
        local_series = registry.fetch_with_fallback(local_symbol, interval="1d")
        if local_series is None:
            return GdrPremiumDiscountSeries(
                local_symbol=local_symbol.upper(),
                gdr_symbol=gdr_symbol,
                fx_pair=fx_pair,
                ratio_local_per_gdr=ratio,
                warnings=[f"No price data for local symbol {local_symbol}"],
            )

        # Fetch GDR series
        gdr_series = registry.fetch_with_fallback(gdr_symbol, interval="1d")
        if gdr_series is None:
            return GdrPremiumDiscountSeries(
                local_symbol=local_symbol.upper(),
                gdr_symbol=gdr_symbol,
                fx_pair=fx_pair,
                ratio_local_per_gdr=ratio,
                warnings=[f"No price data for GDR symbol {gdr_symbol}"],
            )

        # Fetch FX series
        fx_series = registry.fetch_with_fallback(fx_pair, interval="1d")
        use_imputed_fx = False
        if fx_series is None:
            warnings.append(
                f"No FX data for {fx_pair}; using imputed rate of 1.0 "
                "(premium/discount will not be FX-adjusted)"
            )
            use_imputed_fx = True

        # Build DataFrames
        local_df = to_dataframe(local_series)[["date", "close"]].rename(
            columns={"close": "local_close"},
        )
        gdr_df = to_dataframe(gdr_series)[["date", "close"]].rename(
            columns={"close": "gdr_close"},
        )

        if use_imputed_fx:
            # Create a dummy FX column of 1.0
            merged = pd.merge(local_df, gdr_df, on="date", how="inner")
            merged["fx_rate"] = 1.0
        else:
            fx_df = to_dataframe(fx_series)[["date", "close"]].rename(
                columns={"close": "fx_rate"},
            )
            merged = pd.merge(local_df, gdr_df, on="date", how="inner")
            merged = pd.merge(merged, fx_df, on="date", how="inner")

        if len(merged) == 0:
            return GdrPremiumDiscountSeries(
                local_symbol=local_symbol.upper(),
                gdr_symbol=gdr_symbol,
                fx_pair=fx_pair,
                ratio_local_per_gdr=ratio,
                warnings=warnings + ["No overlapping dates between local, GDR, and FX series"],
            )

        # Compute premium/discount
        # gdr_adjusted = gdr_close * fx_rate * ratio
        merged["gdr_adjusted"] = merged["gdr_close"] * merged["fx_rate"] * ratio
        merged["premium_pct"] = (
            (merged["local_close"] - merged["gdr_adjusted"]) / merged["gdr_adjusted"] * 100
        )

        points = [
            GdrPremiumDiscountPoint(
                date=row["date"].date() if isinstance(row["date"], pd.Timestamp) else row["date"],
                value=round(row["premium_pct"], 4),
                is_imputed_fx=use_imputed_fx,
            )
            for _, row in merged.iterrows()
        ]

        return GdrPremiumDiscountSeries(
            local_symbol=local_symbol.upper(),
            gdr_symbol=gdr_symbol,
            fx_pair=fx_pair,
            ratio_local_per_gdr=ratio,
            points=points,
            warnings=warnings,
        )
