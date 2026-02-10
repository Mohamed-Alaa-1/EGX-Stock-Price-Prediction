"""
Dataset preparation for time series prediction.
"""

import numpy as np
import torch
from torch.utils.data import Dataset
from typing import Optional

from core.schemas import PriceSeries


class TimeSeriesDataset(Dataset):
    """
    PyTorch Dataset for time series prediction.

    Creates windowed sequences from price data for LSTM training.
    """

    def __init__(
        self,
        series: PriceSeries,
        sequence_length: int = 30,
        forecast_horizon: int = 1,
        features: Optional[list[str]] = None,
    ):
        """
        Initialize dataset.

        Args:
            series: Price series
            sequence_length: Input sequence length (days)
            forecast_horizon: Prediction horizon (days ahead)
            features: Feature columns to use (default: ["close"])
        """
        self.series = series
        self.sequence_length = sequence_length
        self.forecast_horizon = forecast_horizon
        self.features = features or ["close", "open", "high", "low", "volume"]

        # Sort bars by date
        sorted_bars = sorted(series.bars, key=lambda b: b.date)

        # Extract features as numpy array
        data = []
        for bar in sorted_bars:
            row = []
            for feature in self.features:
                value = getattr(bar, feature)
                if value is None:
                    value = 0.0
                row.append(float(value))
            data.append(row)

        self.data = np.array(data, dtype=np.float32)

        # Normalize features (simple min-max per feature)
        self.min_vals = self.data.min(axis=0, keepdims=True)
        self.max_vals = self.data.max(axis=0, keepdims=True)

        # Avoid division by zero
        self.range_vals = self.max_vals - self.min_vals
        self.range_vals[self.range_vals == 0] = 1.0

        self.data_normalized = (self.data - self.min_vals) / self.range_vals

        # Create windows
        self.X = []
        self.y = []

        for i in range(len(self.data_normalized) - sequence_length - forecast_horizon + 1):
            X_window = self.data_normalized[i : i + sequence_length]
            y_target = self.data[i + sequence_length + forecast_horizon - 1, 0]  # Close price

            self.X.append(X_window)
            self.y.append(y_target)

        self.X = np.array(self.X, dtype=np.float32)
        self.y = np.array(self.y, dtype=np.float32)

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return torch.tensor(self.X[idx]), torch.tensor(self.y[idx])

    def denormalize_prediction(self, normalized_value):
        """
        Denormalize a prediction back to original scale.

        Args:
            normalized_value: Normalized prediction (scalar or array)

        Returns:
            Denormalized value (same type as input)
        """
        # Close is the first feature (index 0)
        result = normalized_value * self.range_vals[0, 0] + self.min_vals[0, 0]
        if np.ndim(result) == 0:
            return float(result)
        return result


def create_train_val_split(
    dataset: TimeSeriesDataset,
    train_ratio: float = 0.8,
) -> tuple[torch.utils.data.Dataset, torch.utils.data.Dataset]:
    """
    Split dataset into train and validation sets.

    Args:
        dataset: Time series dataset
        train_ratio: Ratio of data for training

    Returns:
        Tuple of (train_dataset, val_dataset)
    """
    train_size = int(len(dataset) * train_ratio)
    val_size = len(dataset) - train_size

    return torch.utils.data.random_split(dataset, [train_size, val_size])
