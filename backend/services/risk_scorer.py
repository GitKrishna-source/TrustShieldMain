"""
services/risk_scorer.py
───────────────────────
Computes a composite risk score for a user based on their accumulated
anomalies.  The score is a value in [0, 100] that drives alert
generation and risk‑level classification.

Scoring algorithm
-----------------
1. Gather all recent anomalies for the user (last N or last T hours).
2. For each anomaly, weight its ``severity_score`` by the anomaly type:
   * ``z_score``        → weight 1.0
   * ``temporal_hour``  → weight 0.7
   * ``temporal_day``   → weight 0.5
   * ``volume``         → weight 0.9
   * ``sequence``       → weight 0.8
3. Accumulate weighted severities and normalise into [0, 100].
4. Map to a ``RiskLevel`` enum value.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from database.connection import get_database
from database.models import ANOMALIES_COLLECTION, RiskLevel


# ── Type weights ─────────────────────────────────────────────────────────

ANOMALY_WEIGHTS: Dict[str, float] = {
    "z_score": 1.0,
    "temporal_hour": 0.7,
    "temporal_day": 0.5,
    "volume": 0.9,
    "sequence": 0.8,
}

DEFAULT_WEIGHT: float = 0.6

# Maximum weighted severity sum before the score saturates at 100.
SATURATION_SUM: float = 5.0


# ─────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────

async def compute_risk_score(
    user_id: str,
    lookback_hours: int = 24,
) -> Tuple[float, RiskLevel, List[Dict[str, Any]]]:
    """Compute the current risk score for *user_id*.

    Parameters
    ----------
    user_id : str
        The employee whose risk is being assessed.
    lookback_hours : int
        Only consider anomalies detected within this window.

    Returns
    -------
    tuple[float, RiskLevel, list[dict]]
        ``(risk_score, risk_level, anomalies_used)``
    """
    db = get_database()
    cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)

    cursor = db[ANOMALIES_COLLECTION].find(
        {"user_id": user_id, "detected_at": {"$gte": cutoff}},
        {"_id": 0},
    ).sort("detected_at", -1)
    anomalies: List[Dict[str, Any]] = await cursor.to_list(length=200)

    if not anomalies:
        return 0.0, RiskLevel.LOW, []

    # Weighted severity accumulation
    weighted_sum = 0.0
    for a in anomalies:
        atype = a.get("anomaly_type", "")
        severity = a.get("severity_score", 0.0)
        weight = ANOMALY_WEIGHTS.get(atype, DEFAULT_WEIGHT)
        weighted_sum += severity * weight

    # Normalise to [0, 100]
    score = min((weighted_sum / SATURATION_SUM) * 100.0, 100.0)
    score = round(score, 2)

    level = classify_risk_level(score)
    return score, level, anomalies


def classify_risk_level(score: float) -> RiskLevel:
    """Map a numeric score to a ``RiskLevel``."""
    if score >= 75:
        return RiskLevel.CRITICAL
    if score >= 50:
        return RiskLevel.HIGH
    if score >= 25:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


async def compute_risk_for_anomalies(
    user_id: str,
    anomalies: List[Dict[str, Any]],
) -> Tuple[float, RiskLevel]:
    """Compute a risk score from an explicit list of anomalies (e.g. the
    ones just detected for a single event) without querying the DB.
    """
    if not anomalies:
        return 0.0, RiskLevel.LOW

    weighted_sum = 0.0
    for a in anomalies:
        atype = a.get("anomaly_type", "")
        severity = a.get("severity_score", 0.0)
        weight = ANOMALY_WEIGHTS.get(atype, DEFAULT_WEIGHT)
        weighted_sum += severity * weight

    score = min((weighted_sum / SATURATION_SUM) * 100.0, 100.0)
    score = round(score, 2)
    return score, classify_risk_level(score)