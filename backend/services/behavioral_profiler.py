"""
services/behavioral_profiler.py
───────────────────────────────
High‑level orchestration service that ties together event ingestion,
baseline updates, anomaly detection, risk scoring, and alert generation.

This is the **main entry point** called by the API layer whenever a
new event is created.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.connection import get_database
from database.models import (
    ALERTS_COLLECTION,
    EVENTS_COLLECTION,
    AlertModel,
    AlertStatus,
    RiskLevel,
)
from ml.anomaly_detector import detect_anomalies
from ml.baseline_engine import build_baseline, get_baseline
from services.risk_scorer import compute_risk_for_anomalies


# ── Alert‑generation thresholds ──────────────────────────────────────────

ALERT_SCORE_THRESHOLD: float = 20.0  # minimum risk score to create an alert
BASELINE_REBUILD_INTERVAL: int = 50  # rebuild baseline every N events


# ─────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────

async def process_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Full event‑processing pipeline.

    1. Retrieve the user's previous event (for sequence analysis).
    2. Count today's events for volume analysis.
    3. Run anomaly detection.
    4. If anomalies are found, compute a risk score and potentially
       generate an alert.
    5. Periodically rebuild the user's baseline.

    Parameters
    ----------
    event : dict
        A fully formed event document (already inserted into the events
        collection by the API layer).

    Returns
    -------
    dict
        Processing result containing anomalies, risk score, and any
        generated alert.
    """
    user_id = event["user_id"]
    db = get_database()

    # ── Fetch context for detectors ───────────────────────────────────
    previous_event = await _get_previous_event(db, user_id, event.get("event_id"))
    daily_count = await _get_daily_event_count(db, user_id)

    # ── Run anomaly detection ─────────────────────────────────────────
    anomalies = await detect_anomalies(
        event=event,
        previous_event=previous_event,
        daily_event_count=daily_count,
    )

    result: Dict[str, Any] = {
        "event_id": event.get("event_id"),
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
        "risk_score": 0.0,
        "risk_level": RiskLevel.LOW.value,
        "alert_generated": False,
        "alert": None,
    }

    # ── Risk scoring & alert generation ───────────────────────────────
    if anomalies:
        score, level = await compute_risk_for_anomalies(user_id, anomalies)
        result["risk_score"] = score
        result["risk_level"] = level.value

        if score >= ALERT_SCORE_THRESHOLD:
            alert = await _generate_alert(user_id, anomalies, score, level)
            result["alert_generated"] = True
            result["alert"] = alert

    # ── Periodic baseline rebuild ─────────────────────────────────────
    total = await db[EVENTS_COLLECTION].count_documents({"user_id": user_id})
    if total % BASELINE_REBUILD_INTERVAL == 0:
        await build_baseline(user_id)

    return result


async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Return a composite profile for a user: baseline + recent anomalies
    + current risk posture.
    """
    from ml.anomaly_detector import get_anomalies_for_user
    from services.risk_scorer import compute_risk_score

    baseline = await get_baseline(user_id)

    anomalies = await get_anomalies_for_user(user_id, limit=20)

    score, level, _ = await compute_risk_score(user_id, lookback_hours=24)

    return {
        "user_id": user_id,
        "baseline": baseline,
        "recent_anomalies": anomalies,
        "risk_score": score,
        "risk_level": level.value,
    }


# ─────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────

async def _get_previous_event(
    db, user_id: str, current_event_id: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Return the user's most recent event before the current one."""
    query: Dict[str, Any] = {"user_id": user_id}
    if current_event_id:
        query["event_id"] = {"$ne": current_event_id}
    doc = await (
        db[EVENTS_COLLECTION]
        .find(query, {"_id": 0})
        .sort("timestamp", -1)
        .limit(1)
        .to_list(length=1)
    )
    return doc[0] if doc else None


async def _get_daily_event_count(db, user_id: str) -> int:
    """Count how many events the user has generated today (UTC)."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return await db[EVENTS_COLLECTION].count_documents(
        {"user_id": user_id, "timestamp": {"$gte": today}}
    )


async def _generate_alert(
    user_id: str,
    anomalies: List[Dict[str, Any]],
    score: float,
    level: RiskLevel,
) -> Dict[str, Any]:
    """Create and persist a new alert document."""
    anomaly_ids = [a.get("anomaly_id", "") for a in anomalies]
    descriptions = [a.get("description", "") for a in anomalies]

    alert = AlertModel(
        alert_id=str(uuid.uuid4()),
        user_id=user_id,
        anomaly_ids=anomaly_ids,
        risk_score=score,
        risk_level=level,
        title=f"{level.value.upper()} risk alert for user {user_id}",
        description="Anomalies detected: " + " | ".join(descriptions[:3]),
        status=AlertStatus.OPEN,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ).model_dump()

    db = get_database()
    await db[ALERTS_COLLECTION].insert_one(alert)
    return alert
