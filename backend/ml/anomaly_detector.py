"""
ml/anomaly_detector.py
──────────────────────
Statistical anomaly detection using deviation‑based methods:

1. **Z‑score analysis** – flags individual features whose z‑score
   (relative to the user's baseline) exceeds a configurable threshold.
2. **Temporal deviation** – detects activity outside the user's typical
   hours / days.
3. **Volume deviation** – flags days with unusually high or low event
   counts.
4. **Sequence deviation** – flags event‑type transitions that are rare
   or unseen in the user's historical bigram distribution.

All detections produce ``AnomalyModel``‑compatible dicts that are
persisted to the ``anomalies`` collection.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from database.connection import get_database
from database.models import ANOMALIES_COLLECTION, AnomalyModel
from ml.baseline_engine import get_baseline
from ml.feature_extractor import extract_event_features


# ── Configurable thresholds ──────────────────────────────────────────────

Z_SCORE_THRESHOLD: float = 2.5         # flag features with |z| > 2.5
SEQUENCE_RARITY_THRESHOLD: float = 0.02  # bigram prob < 2 % → anomaly
VOLUME_Z_THRESHOLD: float = 2.0        # daily event count z‑score


# ─────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────

async def detect_anomalies(
    event: Dict[str, Any],
    previous_event: Optional[Dict[str, Any]] = None,
    daily_event_count: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Run all anomaly detectors against a single event.

    Parameters
    ----------
    event : dict
        The incoming event document.
    previous_event : dict | None
        The user's immediately preceding event (for sequence analysis).
    daily_event_count : int | None
        The number of events the user has generated today so far.

    Returns
    -------
    list[dict]
        A (possibly empty) list of anomaly documents ready for DB insertion.
    """
    user_id: str = event.get("user_id", "")
    baseline = await get_baseline(user_id)

    if baseline is None or baseline.get("total_events_analysed", 0) < 5:
        # Not enough history to compare against – skip
        return []

    anomalies: List[Dict[str, Any]] = []

    # 1. Z‑score on per‑event features
    anomalies.extend(_zscore_check(event, baseline))

    # 2. Temporal deviation
    anomalies.extend(_temporal_check(event, baseline))

    # 3. Volume deviation
    if daily_event_count is not None:
        anomalies.extend(_volume_check(event, baseline, daily_event_count))

    # 4. Sequence deviation
    if previous_event is not None:
        anomalies.extend(_sequence_check(event, previous_event, baseline))

    # Persist all detected anomalies
    if anomalies:
        db = get_database()
        await db[ANOMALIES_COLLECTION].insert_many(anomalies)

    return anomalies


async def get_anomalies_for_user(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Return the most recent anomalies for a given user."""
    db = get_database()
    cursor = (
        db[ANOMALIES_COLLECTION]
        .find({"user_id": user_id}, {"_id": 0})
        .sort("detected_at", -1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def get_anomalies_for_event(event_id: str) -> List[Dict[str, Any]]:
    """Return all anomalies associated with a specific event."""
    db = get_database()
    cursor = db[ANOMALIES_COLLECTION].find({"event_id": event_id}, {"_id": 0})
    return await cursor.to_list(length=None)


# ─────────────────────────────────────────────────────────────────────────
# Detector implementations
# ─────────────────────────────────────────────────────────────────────────

def _zscore_check(event: Dict[str, Any], baseline: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flag features whose z‑score exceeds the threshold."""
    features = extract_event_features(event)
    means = baseline.get("feature_means", {})
    stds = baseline.get("feature_stds", {})

    anomalies: List[Dict[str, Any]] = []

    for feat_name, value in features.items():
        mean = means.get(feat_name)
        std = stds.get(feat_name)
        if mean is None or std is None or std == 0:
            continue

        z = (value - mean) / std
        if abs(z) > Z_SCORE_THRESHOLD:
            severity = min(abs(z) / 5.0, 1.0)  # normalise to [0, 1]
            anomalies.append(_make_anomaly(
                event=event,
                anomaly_type="z_score",
                description=(
                    f"Feature '{feat_name}' has z‑score {z:.2f} "
                    f"(value={value:.2f}, mean={mean:.2f}, std={std:.2f})"
                ),
                severity=round(severity, 3),
                z_score=round(z, 3),
                feature_name=feat_name,
                expected_value=mean,
                actual_value=value,
            ))

    return anomalies


def _temporal_check(event: Dict[str, Any], baseline: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flag events outside the user's typical hours or days."""
    ts = event.get("timestamp", datetime.utcnow())
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)

    typical_hours: List[int] = baseline.get("typical_hours", [])
    typical_days: List[int] = baseline.get("typical_days", [])

    anomalies: List[Dict[str, Any]] = []

    if typical_hours and ts.hour not in typical_hours:
        anomalies.append(_make_anomaly(
            event=event,
            anomaly_type="temporal_hour",
            description=(
                f"Activity at hour {ts.hour} is outside typical hours "
                f"{typical_hours}"
            ),
            severity=0.5,
            feature_name="hour_of_day",
            expected_value=float(np.mean(typical_hours)),
            actual_value=float(ts.hour),
        ))

    if typical_days and ts.weekday() not in typical_days:
        anomalies.append(_make_anomaly(
            event=event,
            anomaly_type="temporal_day",
            description=(
                f"Activity on weekday {ts.weekday()} is outside typical days "
                f"{typical_days}"
            ),
            severity=0.4,
            feature_name="day_of_week",
            expected_value=float(np.mean(typical_days)),
            actual_value=float(ts.weekday()),
        ))

    return anomalies


def _volume_check(
    event: Dict[str, Any],
    baseline: Dict[str, Any],
    daily_count: int,
) -> List[Dict[str, Any]]:
    """Flag if the day's event count is unusually high."""
    avg = baseline.get("avg_events_per_day", 0)
    std = baseline.get("std_events_per_day", 0)
    if std == 0 or avg == 0:
        return []

    z = (daily_count - avg) / std
    if abs(z) > VOLUME_Z_THRESHOLD:
        severity = min(abs(z) / 5.0, 1.0)
        return [_make_anomaly(
            event=event,
            anomaly_type="volume",
            description=(
                f"Daily event count ({daily_count}) deviates from baseline "
                f"(mean={avg:.1f}, std={std:.1f}, z={z:.2f})"
            ),
            severity=round(severity, 3),
            z_score=round(z, 3),
            feature_name="events_per_day",
            expected_value=avg,
            actual_value=float(daily_count),
        )]
    return []


def _sequence_check(
    event: Dict[str, Any],
    previous_event: Dict[str, Any],
    baseline: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Flag event‑type transitions that are rare or unseen."""
    prev_type = previous_event.get("event_type", "unknown")
    curr_type = event.get("event_type", "unknown")
    bigram_key = f"{prev_type}→{curr_type}"

    patterns = baseline.get("sequence_patterns", {})
    prob = patterns.get(bigram_key, 0.0)

    if prob < SEQUENCE_RARITY_THRESHOLD:
        severity = 0.6 if prob == 0.0 else 0.35
        return [_make_anomaly(
            event=event,
            anomaly_type="sequence",
            description=(
                f"Transition '{bigram_key}' has probability {prob:.4f} "
                f"(threshold={SEQUENCE_RARITY_THRESHOLD})"
            ),
            severity=severity,
            feature_name="sequence_transition",
            expected_value=SEQUENCE_RARITY_THRESHOLD,
            actual_value=prob,
        )]
    return []


# ─────────────────────────────────────────────────────────────────────────
# Factory helper
# ─────────────────────────────────────────────────────────────────────────

def _make_anomaly(
    event: Dict[str, Any],
    anomaly_type: str,
    description: str,
    severity: float,
    z_score: Optional[float] = None,
    feature_name: Optional[str] = None,
    expected_value: Optional[float] = None,
    actual_value: Optional[float] = None,
) -> Dict[str, Any]:
    """Construct a dict that matches ``AnomalyModel``."""
    return AnomalyModel(
        anomaly_id=str(uuid.uuid4()),
        event_id=event.get("event_id", ""),
        user_id=event.get("user_id", ""),
        anomaly_type=anomaly_type,
        description=description,
        severity_score=severity,
        z_score=z_score,
        feature_name=feature_name,
        expected_value=expected_value,
        actual_value=actual_value,
        detected_at=datetime.utcnow(),
    ).model_dump()