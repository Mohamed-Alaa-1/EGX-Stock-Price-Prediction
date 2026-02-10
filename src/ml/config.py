"""
Machine learning training configuration.
"""

from typing import Optional
from pydantic import BaseModel, Field


class TrainingConfig(BaseModel):
    """Configuration for model training."""

    # Data windowing
    sequence_length: int = Field(default=30, description="Input sequence length (days)")
    forecast_horizon: int = Field(default=1, description="Forecast horizon (days ahead)")
    train_split: float = Field(default=0.8, ge=0.0, le=1.0, description="Train/val split ratio")

    # Training hyperparameters
    epochs: int = Field(default=50, ge=1, description="Number of training epochs")
    batch_size: int = Field(default=32, ge=1, description="Batch size")
    learning_rate: float = Field(default=0.001, gt=0, description="Learning rate")

    # Model architecture
    hidden_size: int = Field(default=64, ge=8, description="LSTM hidden size")
    num_layers: int = Field(default=2, ge=1, description="Number of LSTM layers")
    dropout: float = Field(default=0.2, ge=0.0, le=0.5, description="Dropout rate")

    # Features
    features: list[str] = Field(
        default=["close", "open", "high", "low", "volume"],
        description="Feature columns to use from PriceBar",
    )

    # Training behavior
    early_stopping_patience: int = Field(default=10, ge=1, description="Early stopping patience")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")

    # Federated learning
    federated_rounds: int = Field(default=5, ge=1, description="Federated learning rounds")
    local_epochs: int = Field(default=5, ge=1, description="Local epochs per fed round")

    @classmethod
    def get_default(cls) -> "TrainingConfig":
        """Get default configuration."""
        return cls()
