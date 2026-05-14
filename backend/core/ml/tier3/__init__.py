"""
Tier 3 ML — featherweight models (CVXPY, tabular Q-learning, circuit breakers).
These ALWAYS work. No external deps beyond scipy.
"""
import logging

logger = logging.getLogger("eraya.ml.tier3")

try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
    logger.debug("CVXPY %s available", cp.__version__)
except ImportError:
    CVXPY_AVAILABLE = False
    logger.warning("CVXPY not installed — tier 3 optimization disabled")

__all__ = ["CVXPY_AVAILABLE"]
