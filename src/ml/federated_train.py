"""
Federated learning simulation for multi-stock training.
"""

import torch
import numpy as np
from typing import Optional
from copy import deepcopy

from ml.models.lstm_regressor import LSTMRegressor
from ml.train import train_per_stock_model
from ml.config import TrainingConfig
from core.schemas import PriceSeries


class FederatedTrainingResult:
    """Federated training result."""

    def __init__(self):
        self.global_model: Optional[LSTMRegressor] = None
        self.metrics_per_symbol: dict[str, dict] = {}
        self.rounds_completed: int = 0


def fedavg_aggregate(models: list[LSTMRegressor]) -> LSTMRegressor:
    """
    Aggregate model weights using FedAvg.

    Simple averaging of all client model parameters.

    Args:
        models: List of client models

    Returns:
        Aggregated global model
    """
    if not models:
        raise ValueError("No models to aggregate")

    # Create a new model with same architecture
    global_model = deepcopy(models[0])
    global_dict = global_model.state_dict()

    # Average all parameters
    for key in global_dict.keys():
        global_dict[key] = torch.stack([
            model.state_dict()[key].float() for model in models
        ]).mean(0)

    global_model.load_state_dict(global_dict)
    return global_model


def train_federated_model(
    series_by_symbol: dict[str, PriceSeries],
    config: Optional[TrainingConfig] = None,
    progress_callback: Optional[callable] = None,
) -> FederatedTrainingResult:
    """
    Train federated model across multiple stocks.

    Implements FedAvg:
    1. Initialize global model
    2. For each round:
       - Distribute global model to clients
       - Each client trains locally
       - Aggregate client models

    Args:
        series_by_symbol: Dict mapping symbol to price series
        config: Training configuration
        progress_callback: Optional callback(round, total_rounds, symbol)

    Returns:
        FederatedTrainingResult
    """
    config = config or TrainingConfig.get_default()
    result = FederatedTrainingResult()

    if len(series_by_symbol) < 2:
        raise ValueError("Federated learning requires at least 2 stocks")

    # Set seed
    if config.seed is not None:
        torch.manual_seed(config.seed)
        np.random.seed(config.seed)

    # Initialize global model
    # Use first stock to get dataset shape
    first_symbol = list(series_by_symbol.keys())[0]
    from ml.dataset import TimeSeriesDataset
    sample_dataset = TimeSeriesDataset(
        series=series_by_symbol[first_symbol],
        sequence_length=config.sequence_length,
    )

    global_model = LSTMRegressor(
        input_size=len(sample_dataset.features),
        hidden_size=config.hidden_size,
        num_layers=config.num_layers,
        dropout=config.dropout,
    )

    # Federated training rounds
    for round_idx in range(config.federated_rounds):
        client_models = []

        # Train each client independently
        for symbol, series in series_by_symbol.items():
            if progress_callback:
                progress_callback(round_idx + 1, config.federated_rounds, symbol)

            try:
                # Create local config with local epochs
                local_config = TrainingConfig(
                    sequence_length=config.sequence_length,
                    forecast_horizon=config.forecast_horizon,
                    train_split=config.train_split,
                    epochs=config.local_epochs,
                    batch_size=config.batch_size,
                    learning_rate=config.learning_rate,
                    hidden_size=config.hidden_size,
                    num_layers=config.num_layers,
                    dropout=config.dropout,
                    early_stopping_patience=config.early_stopping_patience,
                    seed=config.seed,
                )

                # Train locally
                train_result = train_per_stock_model(series, local_config)

                if train_result.model:
                    client_models.append(train_result.model)
                    result.metrics_per_symbol[symbol] = train_result.val_metrics

            except Exception as e:
                print(f"Failed to train client {symbol}: {e}")
                continue

        # Aggregate models
        if client_models:
            global_model = fedavg_aggregate(client_models)
            result.rounds_completed = round_idx + 1
        else:
            print(f"Round {round_idx + 1}: No successful client trainings")
            break

    result.global_model = global_model
    return result
