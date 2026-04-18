"""
api/alerts.py
─────────────
FastAPI router for security alert management.

Routes
------
GET    /alerts/                – list alerts with filters
GET    /alerts/{alert_id}      – single alert detail
PUT    /alerts/{alert_id}/status – update alert status
GET    /alerts/user/{user_id}  – alerts for a specific user
GET    /alerts/stats            – aggregate alert statistics
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database.connection import get_database
from database.models import (
    ALERTS_COLLECTION,
    ANOMALIES_COLLECTION,
    AlertStatus,
    RiskLevel,
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# ── Request schemas ──────────────────────────────────────────────────────

class AlertStatusUpdateRequest(BaseModel):
    """Payload for changing an alert's lifecycle status."""
    status: AlertStatus
    resolved_by: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────

@router.get("/")
async def list_alerts(
    status: Optional[AlertStatus] = Query(None),
    risk_level: Optional[RiskLevel] = Query(None),
    user_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve alerts with optional filtering by status, risk level,
    or user.
    """
    db = get_database()
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status.value
    if risk_level:
        query["risk_level"] = risk_level.value
    if user_id:
        query["user_id"] = user_id

    cursor = (
        db[ALERTS_COLLECTION]
        .find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    alerts = await cursor.to_list(length=limit)
    total = await db[ALERTS_COLLECTION].count_documents(query)

    return {"total": total, "limit": limit, "offset": offset, "alerts": alerts}


@router.get("/stats")
async def alert_stats():
    """Return aggregate statistics about alerts (counts by status,
    risk level, etc.).
    """
    db = get_database()
    col = db[ALERTS_COLLECTION]

    total = await col.count_documents({})

    # Count by status
    status_counts: Dict[str, int] = {}
    for s in AlertStatus:
        status_counts[s.value] = await col.count_documents({"status": s.value})

    # Count by risk level
    risk_counts: Dict[str, int] = {}
    for r in RiskLevel:
        risk_counts[r.value] = await col.count_documents({"risk_level": r.value})

    # Average risk score
    pipeline = [{"$group": {"_id": None, "avg_score": {"$avg": "$risk_score"}}}]
    agg = await col.aggregate(pipeline).to_list(length=1)
    avg_score = round(agg[0]["avg_score"], 2) if agg and agg[0]["avg_score"] else 0.0

    return {
        "total_alerts": total,
        "by_status": status_counts,
        "by_risk_level": risk_counts,
        "average_risk_score": avg_score,
    }


@router.get("/{alert_id}")
async def get_alert(alert_id: str):
    """Return full details for a single alert, including its linked
    anomalies.
    """
    db = get_database()
    alert = await db[ALERTS_COLLECTION].find_one(
        {"alert_id": alert_id}, {"_id": 0}
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Attach the anomaly details
    anomaly_ids = alert.get("anomaly_ids", [])
    if anomaly_ids:
        cursor = db[ANOMALIES_COLLECTION].find(
            {"anomaly_id": {"$in": anomaly_ids}}, {"_id": 0}
        )
        anomalies = await cursor.to_list(length=None)
    else:
        anomalies = []

    alert["anomaly_details"] = anomalies
    return alert


@router.put("/{alert_id}/status")
async def update_alert_status(alert_id: str, payload: AlertStatusUpdateRequest):
    """Transition an alert to a new lifecycle status."""
    db = get_database()

    updates: Dict[str, Any] = {
        "status": payload.status.value,
        "updated_at": datetime.utcnow(),
    }
    if payload.status in (AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE):
        updates["resolved_at"] = datetime.utcnow()
        if payload.resolved_by:
            updates["resolved_by"] = payload.resolved_by

    result = await db[ALERTS_COLLECTION].update_one(
        {"alert_id": alert_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")

    updated = await db[ALERTS_COLLECTION].find_one(
        {"alert_id": alert_id}, {"_id": 0}
    )
    return {"message": "Alert status updated", "alert": updated}


@router.get("/user/{user_id}")
async def get_user_alerts(
    user_id: str,
    limit: int = Query(50, ge=1, le=500),
):
    """Return alerts associated with a specific user."""
    db = get_database()
    cursor = (
        db[ALERTS_COLLECTION]
        .find({"user_id": user_id}, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    alerts = await cursor.to_list(length=limit)
    return {"user_id": user_id, "count": len(alerts), "alerts": alerts}