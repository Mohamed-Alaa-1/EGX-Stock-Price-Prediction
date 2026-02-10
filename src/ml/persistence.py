"""
Model persistence (save/load).
"""

import json
import torch
from pathlib import Path
from typing import Optional

from ml.models.lstm_regressor import LSTMRegressor, create_model
from services.artifact_paths import (
    get_model_weights_path,
    get_model_config_path,
    ensure_model_directory,
)


def save_model(model: LSTMRegressor, artifact_id: str) -> tuple[Path, Path]:
    """
    Save model weights and configuration.
    
    Args:
        model: Trained model
        artifact_id: Unique artifact identifier
        
    Returns:
        Tuple of (weights_path, config_path)
    """
    ensure_model_directory()
    
    weights_path = get_model_weights_path(artifact_id)
    config_path = get_model_config_path(artifact_id)
    
    # Save weights
    torch.save(model.state_dict(), weights_path)
    
    # Save config
    config = model.get_config()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    
    return weights_path, config_path


def load_model(artifact_id: str) -> Optional[LSTMRegressor]:
    """
    Load model from disk.
    
    Args:
        artifact_id: Unique artifact identifier
        
    Returns:
        Loaded model or None if not found
    """
    weights_path = get_model_weights_path(artifact_id)
    config_path = get_model_config_path(artifact_id)
    
    if not weights_path.exists() or not config_path.exists():
        return None
    
    try:
        # Load config
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Create model
        model = create_model(config)
        
        # Load weights
        model.load_state_dict(torch.load(weights_path, weights_only=True))
        model.eval()
        
        return model
    
    except Exception as e:
        print(f"Failed to load model {artifact_id}: {e}")
        return None


def delete_model_files(artifact_id: str) -> bool:
    """
    Delete model files from disk.
    
    Args:
        artifact_id: Unique artifact identifier
        
    Returns:
        True if deleted, False if not found
    """
    weights_path = get_model_weights_path(artifact_id)
    config_path = get_model_config_path(artifact_id)
    
    deleted = False
    
    if weights_path.exists():
        weights_path.unlink()
        deleted = True
    
    if config_path.exists():
        config_path.unlink()
        deleted = True
    
    return deleted
