"""
Tier 2 ML — practical models (XGBoost, Kalman, HMM, Thompson Sampling).
These are the primary working models for the hackathon demo.
"""
import logging

logger = logging.getLogger("eraya.ml.tier2")

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
    logger.debug("XGBoost %s available", xgb.__version__)
except ImportError:
    XGB_AVAILABLE = False

try:
    from filterpy.kalman import KalmanFilter  # noqa: F401
    KALMAN_AVAILABLE = True
except ImportError:
    KALMAN_AVAILABLE = False

try:
    from hmmlearn import hmm  # noqa: F401
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False

try:
    import river  # noqa: F401
    RIVER_AVAILABLE = True
except ImportError:
    RIVER_AVAILABLE = False

__all__ = ["XGB_AVAILABLE", "KALMAN_AVAILABLE", "HMM_AVAILABLE", "RIVER_AVAILABLE"]
