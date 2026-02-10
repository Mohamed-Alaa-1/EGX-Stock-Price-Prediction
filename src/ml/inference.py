"""
ML model inference engine.
"""

import torch
import numpy as np
from pathlib import Path

from core.schemas import ModelArtifact, PriceSeries
from ml.models.lstm_regressor import LSTMRegressor
from ml.persistence import load_model
from ml.dataset import TimeSeriesDataset


class InferenceEngine:
    """Engine for running ML model inference."""
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    def predict(
        self,
        artifact: ModelArtifact,
        series: PriceSeries,
    ) -> float:
        """
        Generate prediction for next day close.
        
        Args:
            artifact: Model artifact
            series: Historical price data
            
        Returns:
            Predicted closing price
            
        Raises:
            ValueError: If insufficient data or model load fails
        """
        # Load model
        model = load_model(artifact.artifact_id)
        if model is None:
            raise ValueError(f"Failed to load model for artifact {artifact.artifact_id}")
        model = model.to(self.device)
        model.eval()
        
        # Get hyperparams
        config = artifact.hyperparams
        sequence_length = config.get("sequence_length", 30)
        features = config.get("features", ["close"])
        
        # Prepare dataset
        dataset = TimeSeriesDataset(
            series=series,
            sequence_length=sequence_length,
            features=features,
        )
        
        if len(dataset) == 0:
            raise ValueError("Insufficient data for prediction")
        
        # Get last sequence
        last_sequence, _ = dataset[-1]
        last_sequence = last_sequence.detach().clone().float().unsqueeze(0)
        last_sequence = last_sequence.to(self.device)
        
        # Inference
        with torch.no_grad():
            prediction_norm = model(last_sequence)
            prediction_norm = prediction_norm.cpu().numpy()[0, 0]
        
        # Denormalize
        prediction = dataset.denormalize_prediction(prediction_norm)
        
        return float(prediction)
    
    def predict_batch(
        self,
        artifact: ModelArtifact,
        series_list: list[PriceSeries],
    ) -> list[float]:
        """
        Generate predictions for multiple series.
        
        Args:
            artifact: Model artifact
            series_list: List of price series
            
        Returns:
            List of predicted closing prices
        """
        return [self.predict(artifact, series) for series in series_list]
