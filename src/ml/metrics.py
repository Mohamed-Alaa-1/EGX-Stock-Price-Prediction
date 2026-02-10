"""
ML evaluation metrics.
"""

import numpy as np
from typing import Union


def mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Mean Absolute Error.
    
    Args:
        y_true: True values
        y_pred: Predicted values
        
    Returns:
        MAE value
    """
    return float(np.mean(np.abs(y_true - y_pred)))


def root_mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Root Mean Squared Error.
    
    Args:
        y_true: True values
        y_pred: Predicted values
        
    Returns:
        RMSE value
    """
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mean_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Mean Absolute Percentage Error.
    
    Args:
        y_true: True values 
        y_pred: Predicted values
        
    Returns:
        MAPE value (as percentage)
    """
    # Avoid division by zero
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """
    Calculate all metrics.
    
    Args:
        y_true: True values
        y_pred: Predicted values
        
    Returns:
        Dictionary of metrics
    """
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": root_mean_squared_error(y_true, y_pred),
        "mape": mean_absolute_percentage_error(y_true, y_pred),
    }


def compare_to_baseline(
    model_metrics: dict[str, float],
    baseline_metrics: dict[str, float],
) -> dict[str, float]:
    """
    Compare model metrics to baseline.
    
    Args:
        model_metrics: Model evaluation metrics
        baseline_metrics: Baseline evaluation metrics
        
    Returns:
        Improvement percentages
    """
    improvements = {}
    for metric, baseline_value in baseline_metrics.items():
        if metric in model_metrics:
            model_value = model_metrics[metric]
            if baseline_value != 0:
                improvement = ((baseline_value - model_value) / baseline_value) * 100
                improvements[f"{metric}_improvement"] = improvement
    
    return improvements
