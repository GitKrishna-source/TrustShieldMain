"""
ml package
──────────
Re‑exports the key functions from the ML sub‑modules so that callers
can write ``from ml import detect_anomalies`` etc.
"""

from ml.anomaly_detector import detect_anomalies, get_anomalies_for_user, get_anomalies_for_event
from ml.baseline_engine import build_baseline, get_baseline, rebuild_all_baselines
from ml.feature_extractor import extract_event_features, extract_aggregate_features

__all__ = [
    "detect_anomalies",
    "get_anomalies_for_user",
    "get_anomalies_for_event",
    "build_baseline",
    "get_baseline",
    "rebuild_all_baselines",
    "extract_event_features",
    "extract_aggregate_features",
]
