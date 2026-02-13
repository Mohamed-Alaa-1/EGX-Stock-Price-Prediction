"""
Stock Sheet Insights Service — batch orchestration for sheet-wide analysis.

Computes Buy/Sell/Hold recommendations for every stock in the user's stock sheet.

Per-Symbol Error/Status Convention:
- OK: Successfully computed insight
- HOLD_FALLBACK: Insufficient/invalid data → default to HOLD with reason
- ERROR: Processing failed → HOLD with error reason

Every StockInsight result includes:
- status: InsightStatus enum
- status_reason: user-readable explanation when not OK
- used_cache_fallback: True if fresh retrieval failed and cached data was used
"""

from datetime import datetime, date
from typing import Optional
import uuid
import traceback

from core.schemas import (
    ForecastMethod,
    InsightStatus,
    InsightBatchRun,
    SheetInsightsRunRequest,
    StockInsight,
    StrategyAction,
)
from ml.config import TrainingConfig
from services.price_service import PriceService
from services.prediction_service import PredictionService
from services.stock_universe_manager import StockUniverseManager
from services.strategy_engine import StrategyEngine
from services.training_service import TrainingService


class StockSheetInsightsService:
    """Batch insights orchestration service."""

    def __init__(self) -> None:
        """Initialize service."""
        self.price_service = PriceService()
        self.prediction_service = PredictionService()
        self.strategy_engine = StrategyEngine()
        self.universe_manager = StockUniverseManager()

    @staticmethod
    def _create_hold_fallback(
        symbol: str,
        reason: str,
        used_cache_fallback: bool = False,
    ) -> StockInsight:
        """
        Create a HOLD fallback insight for error cases.

        Args:
            symbol: Stock symbol
            reason: User-readable reason for HOLD
            used_cache_fallback: Whether cache fallback was attempted

        Returns:
            StockInsight with HOLD action and HOLD_FALLBACK status
        """
        return StockInsight(
            symbol=symbol,
            as_of_date=date.today(),
            computed_at=datetime.now(),
            action=StrategyAction.HOLD,
            conviction=0,
            stop_loss=None,  # N/A for HOLD
            target_exit=None,  # N/A for HOLD
            logic_summary=reason,
            status=InsightStatus.HOLD_FALLBACK,
            status_reason=reason,
            used_cache_fallback=used_cache_fallback,
        )

    def _process_one_symbol(
        self,
        symbol: str,
        forecast_method: str,
        train_models: bool,
        force_refresh: bool,
    ) -> StockInsight:
        """
        Process one symbol with full isolation.

        Args:
            symbol: Stock symbol
            forecast_method: Forecast method (ml, naive, sma)
            train_models: Whether to train/update model
            force_refresh: Whether to force fresh retrieval

        Returns:
            StockInsight (including HOLD fallback on errors)
        """
        symbol = symbol.upper()
        used_cache_fallback = False

        try:
            # 1. Fetch series with force_refresh flag
            print(f"[StockSheetInsights] Processing {symbol} (force_refresh={force_refresh})")
            try:
                series = self.price_service.get_series(symbol, use_cache=not force_refresh)
            except Exception as fetch_error:
                print(f"[StockSheetInsights] Fresh fetch failed for {symbol}: {fetch_error}")
                # Try cache fallback
                try:
                    series = self.price_service.get_series(symbol, use_cache=True)
                    used_cache_fallback = True
                    print(f"[StockSheetInsights] Using cached data for {symbol}")
                except Exception as cache_error:
                    print(f"[StockSheetInsights] Cache fallback also failed for {symbol}: {cache_error}")
                    return self._create_hold_fallback(
                        symbol,
                        f"Data unavailable: {str(fetch_error)[:100]}",
                        used_cache_fallback=False,
                    )

            # 2. Optionally train model
            if train_models:
                print(f"[StockSheetInsights] Training model for {symbol}")
                try:
                    TrainingService.train_per_stock(symbol, series, config=TrainingConfig.get_default())
                except Exception as train_error:
                    print(f"[StockSheetInsights] Training failed for {symbol}: {train_error}")
                    # Continue with old model or baseline

            # 3. Generate forecast
            method_enum = ForecastMethod.ML if forecast_method == "ml" else (
                ForecastMethod.NAIVE if forecast_method == "naive" else ForecastMethod.SMA
            )
            forecast = self.prediction_service.predict(symbol, method=method_enum)

            # 4. Compute recommendation
            recommendation = self.strategy_engine.compute_recommendation(
                series=series,
                forecast=forecast,
            )

            # 5. Build StockInsight
            insight = StockInsight(
                symbol=symbol,
                as_of_date=series.get_latest_bar().date,
                computed_at=datetime.now(),
                action=recommendation.action,
                conviction=recommendation.conviction,
                stop_loss=recommendation.stop_loss,
                target_exit=recommendation.target_exit,
                entry_zone_lower=recommendation.entry_zone_lower,
                entry_zone_upper=recommendation.entry_zone_upper,
                logic_summary=recommendation.logic_summary or "",
                status=InsightStatus.OK,
                status_reason=None,
                used_cache_fallback=used_cache_fallback,
                raw_outputs={
                    "forecast": forecast.model_dump(mode="json") if forecast else None,
                },
                assistant_recommendation=recommendation.model_dump(mode="json"),
            )

            print(f"[StockSheetInsights] ✓ {symbol}: {insight.action.value.upper()} (conviction={insight.conviction})")
            return insight

        except Exception as e:
            # Per-stock isolation: never let one error abort the batch
            print(f"[StockSheetInsights] ERROR processing {symbol}: {e}")
            traceback.print_exc()
            return self._create_hold_fallback(
                symbol,
                f"Processing error: {str(e)[:100]}",
                used_cache_fallback=used_cache_fallback,
            )

    def run_batch_insights(
        self,
        symbols: Optional[list[str]] = None,
        forecast_method: str = "ml",
        train_models: bool = True,
        force_refresh: bool = True,
    ) -> InsightBatchRun:
        """
        Run batch insights for symbols.

        Args:
            symbols: List of symbols (if None, load from sheet)
            forecast_method: Forecast method to use (ml, naive, sma)
            train_models: Whether to train models
            force_refresh: Whether to force fresh retrieval

        Returns:
            InsightBatchRun with results and summary
        """
        import time
        start_time = time.time()

        print("=" * 80)
        print(f"[StockSheetInsights] Starting batch run")
        print(f"[StockSheetInsights]   Forecast method: {forecast_method}")
        print(f"[StockSheetInsights]   Train models: {train_models}")
        print(f"[StockSheetInsights]   Force refresh: {force_refresh}")
        print("=" * 80)

        # Create request object
        request = SheetInsightsRunRequest(
            symbols=symbols,
            forecast_method=forecast_method,
            train_models=train_models,
            force_refresh=force_refresh,
        )

        batch_id = str(uuid.uuid4())[:8]
        print(f"[StockSheetInsights] Batch ID: {batch_id}")

        # Load symbols if not provided
        if symbols is None:
            symbols = self.universe_manager.list_symbols()
            print(f"[StockSheetInsights] Loaded {len(symbols)} symbols from sheet")
        else:
            symbols = [s.upper() for s in symbols]
            print(f"[StockSheetInsights] Processing {len(symbols)} provided symbols")

        # Process each symbol
        results: list[StockInsight] = []
        for i, symbol in enumerate(symbols, 1):
            symbol_start = time.time()
            print(f"\n[StockSheetInsights] [{i}/{len(symbols)}] Processing {symbol}...")
            insight = self._process_one_symbol(symbol, forecast_method, train_models, force_refresh)
            results.append(insight)
            elapsed = time.time() - symbol_start
            print(f"[StockSheetInsights] [{i}/{len(symbols)}] {symbol} complete in {elapsed:.1f}s")

        # Compute summary
        summary = {
            "total": len(results),
            "ok": sum(1 for r in results if r.status == InsightStatus.OK),
            "hold_fallback": sum(1 for r in results if r.status == InsightStatus.HOLD_FALLBACK),
            "error": sum(1 for r in results if r.status == InsightStatus.ERROR),
        }

        total_elapsed = time.time() - start_time
        print("=" * 80)
        print(f"[StockSheetInsights] Batch complete: {summary}")
        print(f"[StockSheetInsights] Total elapsed: {total_elapsed:.1f}s")
        print(f"[StockSheetInsights] Average per symbol: {total_elapsed/len(symbols):.1f}s")
        print("=" * 80)

        return InsightBatchRun(
            batch_id=batch_id,
            computed_at=datetime.now(),
            request=request,
            results=results,
            summary=summary,
        )


