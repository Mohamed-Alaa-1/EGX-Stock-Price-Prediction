"""
Training orchestration service.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from core.schemas import ModelArtifact, ModelType, PriceSeries
from ml.baselines import get_baseline
from ml.config import TrainingConfig
from ml.federated_train import train_federated_model
from ml.metrics import compare_to_baseline
from ml.persistence import save_model
from ml.train import train_per_stock_model
from services.artifact_paths import generate_artifact_id
from services.model_registry import get_registry
from services.signal_validation_service import SignalValidationService


class TrainingService:
    """Service for orchestrating model training."""

    @staticmethod
    def train_per_stock(
        symbol: str,
        series: PriceSeries,
        config: TrainingConfig | None = None,
        progress_callback: callable | None = None,
    ) -> ModelArtifact:
        """
        Train a per-stock model.

        Args:
            symbol: Stock symbol
            series: Historical price data
            config: Training configuration
            progress_callback: Progress callback

        Returns:
            Created ModelArtifact

        Raises:
            ValueError: If training fails
        """
        config = config or TrainingConfig.get_default()

        # Statistical validation BEFORE training (constitution mandate)
        validation_result = None
        validation_warnings = []
        try:
            validation_result = SignalValidationService.validate(series)
            validation_warnings = validation_result.warnings
            if validation_warnings:
                print(
                    f"[TrainingService] Signal validation warnings"
                    f" for {symbol}: {validation_warnings}"
                )
        except Exception as e:
            print(f"[TrainingService] Signal validation failed for {symbol}: {e}")
            validation_warnings = [f"Signal validation failed: {e}"]

        # Train model
        result = train_per_stock_model(series, config, progress_callback)

        if not result.model:
            raise ValueError("Training failed to produce a model")

        # Generate artifact ID
        artifact_id = generate_artifact_id(symbol, "per_stock")

        # Save model
        weights_path, config_path = save_model(result.model, artifact_id)

        # Calculate baseline metrics
        baseline_pred = get_baseline(series, method="naive")
        last_close = series.get_latest_close()
        baseline_metrics = {
            "mae": abs(last_close - baseline_pred),
            "rmse": abs(last_close - baseline_pred),
        }

        # Compare to baseline
        improvements = compare_to_baseline(result.val_metrics, baseline_metrics)
        metrics = {
            "model_mae": result.val_metrics.get("mae", 0),
            "model_rmse": result.val_metrics.get("rmse", 0),
            "model_mape": result.val_metrics.get("mape", 0),
            "baseline_mae": baseline_metrics.get("mae", 0),
            "baseline_rmse": baseline_metrics.get("rmse", 0),
            **improvements,
        }

        # Build hyperparams with validation results persisted
        hyperparams = config.model_dump()
        if validation_result:
            hyperparams["signal_validation"] = validation_result.model_dump(mode="json")

        # Create artifact
        artifact = ModelArtifact(
            artifact_id=artifact_id,
            type=ModelType.PER_STOCK,
            covered_symbols=[symbol.upper()],
            created_at=datetime.now(),
            last_trained_at=datetime.now(),
            data_source=series.source,
            training_window_start=min(bar.date for bar in series.bars),
            training_window_end=max(bar.date for bar in series.bars),
            model_version="lstm_v1",
            hyperparams=hyperparams,
            metrics=metrics,
            storage_path=str(weights_path),
        )

        # Register artifact
        registry = get_registry()
        registry.register(artifact)

        return artifact

    @staticmethod
    def train_federated(
        symbols: list[str],
        series_by_symbol: dict[str, PriceSeries],
        config: TrainingConfig | None = None,
        progress_callback: callable | None = None,
    ) -> ModelArtifact:
        """
        Train a federated model.

        Args:
            symbols: List of stock symbols
            series_by_symbol: Price series for each symbol
            config: Training configuration
            progress_callback: Progress callback

        Returns:
            Created ModelArtifact
        """
        config = config or TrainingConfig.get_default()

        # Statistical validation BEFORE training for each symbol (constitution mandate)
        validation_results = {}
        for sym, sym_series in series_by_symbol.items():
            try:
                val = SignalValidationService.validate(sym_series)
                validation_results[sym] = val.model_dump(mode="json")
                if val.warnings:
                    print(f"[TrainingService] Signal validation warnings for {sym}: {val.warnings}")
            except Exception as e:
                print(f"[TrainingService] Signal validation failed for {sym}: {e}")
                validation_results[sym] = {"error": str(e)}

        # Train federated model
        result = train_federated_model(series_by_symbol, config, progress_callback)

        if not result.global_model:
            raise ValueError("Federated training failed")

        # Generate artifact ID
        artifact_id = generate_artifact_id("federated", "federated")

        # Save model
        weights_path, config_path = save_model(result.global_model, artifact_id)

        # Aggregate metrics
        all_metrics = list(result.metrics_per_symbol.values())
        avg_metrics = {}
        if all_metrics:
            for key in all_metrics[0].keys():
                values = [m[key] for m in all_metrics if key in m]
                avg_metrics[f"avg_{key}"] = float(np.mean(values))

        # Use first series for source metadata
        first_symbol = symbols[0]
        source = series_by_symbol[first_symbol].source

        # Create artifact
        artifact = ModelArtifact(
            artifact_id=artifact_id,
            type=ModelType.FEDERATED,
            covered_symbols=[s.upper() for s in symbols],
            created_at=datetime.now(),
            last_trained_at=datetime.now(),
            data_source=source,
            training_window_start=min(
                min(bar.date for bar in series.bars)
                for series in series_by_symbol.values()
            ),
            training_window_end=max(
                max(bar.date for bar in series.bars)
                for series in series_by_symbol.values()
            ),
            model_version="lstm_v1_federated",
            hyperparams={**config.model_dump(), "signal_validation": validation_results},
            metrics=avg_metrics,
            storage_path=str(weights_path),
        )

        # Register artifact
        registry = get_registry()
        registry.register(artifact)

        return artifact
