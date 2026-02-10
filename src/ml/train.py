"""
Model training loop for per-stock models.
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from typing import Optional
import numpy as np

from ml.models.lstm_regressor import LSTMRegressor
from ml.dataset import TimeSeriesDataset, create_train_val_split
from ml.config import TrainingConfig
from ml.metrics import calculate_metrics
from core.schemas import PriceSeries


class TrainingResult:
    """Training result container."""

    def __init__(self):
        self.model: Optional[LSTMRegressor] = None
        self.train_metrics: dict[str, float] = {}
        self.val_metrics: dict[str, float] = {}
        self.history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}
        self.best_epoch: int = 0


def train_per_stock_model(
    series: PriceSeries,
    config: Optional[TrainingConfig] = None,
    progress_callback: Optional[callable] = None,
) -> TrainingResult:
    """
    Train a per-stock LSTM model.

    Args:
        series: Historical price data
        config: Training configuration
        progress_callback: Optional callback(epoch, total_epochs, loss)

    Returns:
        TrainingResult with trained model and metrics
    """
    config = config or TrainingConfig.get_default()
    result = TrainingResult()

    # Set random seed
    if config.seed is not None:
        torch.manual_seed(config.seed)
        np.random.seed(config.seed)

    # Prepare dataset
    dataset = TimeSeriesDataset(
        series=series,
        sequence_length=config.sequence_length,
        forecast_horizon=config.forecast_horizon,
        features=config.features,
    )

    # Log training data info
    sorted_bars = sorted(series.bars, key=lambda b: b.date)
    print(f"[Training] Data: {len(series.bars)} bars, "
          f"{sorted_bars[0].date} to {sorted_bars[-1].date}, "
          f"features={config.features}")

    if len(dataset) < 10:
        raise ValueError(f"Insufficient data: only {len(dataset)} samples")

    train_dataset, val_dataset = create_train_val_split(dataset, config.train_split)

    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=config.batch_size, shuffle=False)

    # Create model
    model = LSTMRegressor(
        input_size=len(dataset.features),
        hidden_size=config.hidden_size,
        num_layers=config.num_layers,
        dropout=config.dropout,
        use_attention=True,
    )

    # Log model architecture
    print(f"[Training] Model: input_size={len(dataset.features)}, "
          f"hidden_size={config.hidden_size}, num_layers={config.num_layers}, "
          f"use_attention=True, dropout={config.dropout}")

    # Loss and optimizer
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)

    # Learning rate scheduler
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', patience=5, factor=0.5,
    )

    # Training loop
    best_val_loss = float('inf')
    patience_counter = 0

    # Denormalization constants as tensors for differentiable denorm
    range_val = float(dataset.range_vals[0, 0])
    min_val = float(dataset.min_vals[0, 0])

    for epoch in range(config.epochs):
        # Training phase
        model.train()
        train_losses = []

        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            predictions = model(X_batch).squeeze()

            # Denormalize predictions differentiably (preserves gradient flow)
            pred_denorm = predictions * range_val + min_val
            loss = criterion(pred_denorm, y_batch)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_losses.append(loss.item())

        avg_train_loss = np.mean(train_losses)
        result.history["train_loss"].append(avg_train_loss)

        # Validation phase
        model.eval()
        val_losses = []

        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                predictions = model(X_batch).squeeze()
                pred_denorm = predictions * range_val + min_val
                loss = criterion(pred_denorm, y_batch)
                val_losses.append(loss.item())

        avg_val_loss = np.mean(val_losses)
        result.history["val_loss"].append(avg_val_loss)

        # Step LR scheduler
        old_lr = optimizer.param_groups[0]['lr']
        scheduler.step(avg_val_loss)
        new_lr = optimizer.param_groups[0]['lr']
        if new_lr != old_lr:
            print(f"[Training] LR reduced: {old_lr:.6f} -> {new_lr:.6f}")

        # Progress callback
        if progress_callback:
            progress_callback(epoch + 1, config.epochs, avg_val_loss)

        # Early stopping check
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            result.best_epoch = epoch
            result.model = model
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= config.early_stopping_patience:
                print(f"Early stopping at epoch {epoch + 1}")
                break

    # Calculate final metrics
    model.eval()
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for X_batch, y_batch in val_loader:
            predictions = model(X_batch).squeeze()
            pred_denorm = (predictions * range_val + min_val).numpy()
            all_preds.append(np.atleast_1d(pred_denorm))
            all_targets.append(np.atleast_1d(y_batch.numpy()))

    all_preds = np.concatenate(all_preds) if all_preds else np.array([])
    all_targets = np.concatenate(all_targets) if all_targets else np.array([])

    if len(all_preds) > 0:
        result.val_metrics = calculate_metrics(all_targets, all_preds)

    print(f"[Training] Complete. Best epoch: {result.best_epoch}, val_metrics: {result.val_metrics}")
    return result
