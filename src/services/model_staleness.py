"""
Model staleness detection and management.
"""

from datetime import datetime, timedelta
from typing import Optional

from core.schemas import ModelArtifact
from core.config import Config


def is_model_stale(
    artifact: ModelArtifact,
    threshold_days: Optional[int] = None,
) -> bool:
    """
    Check if model is stale.

    Args:
        artifact: Model artifact to check
        threshold_days: Staleness threshold (default: from config)

    Returns:
        True if stale, False otherwise
    """
    threshold = threshold_days or Config.MODEL_STALE_DAYS
    age = datetime.now() - artifact.last_trained_at
    return age > timedelta(days=threshold)


def get_staleness_message(artifact: ModelArtifact) -> str:
    """
    Get human-readable staleness message.

    Args:
        artifact: Model artifact

    Returns:
        Staleness message
    """
    age = datetime.now() - artifact.last_trained_at
    age_days = age.days

    if not is_model_stale(artifact):
        return f"Model is fresh (trained {age_days} day{'s' if age_days != 1 else ''} ago)"
    else:
        return f"Model is stale (trained {age_days} days ago, recommended: every {Config.MODEL_STALE_DAYS} days)"


def should_prompt_retrain(artifact: ModelArtifact) -> bool:
    """
    Check if user should be prompted to retrain.

    Args:
        artifact: Model artifact

    Returns:
        True if should prompt, False otherwise
    """
    return is_model_stale(artifact)
