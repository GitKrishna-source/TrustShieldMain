"""
api/dashboard.py
────────────────
FastAPI router for dashboard / analytics endpoints.

Routes
------
GET /dashboard/overview     – high‑level KPIs
GET /dashboard/risk-summary – risk distribution across all users
GET /dashboard/activity     – recent activity timeline
GET /dashboard/top-risks    – users with the highest risk scores
GET /dashboard/anomaly-trends – anomaly counts over time
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Query

from database.connection import get_database
from database.models import (
    ALERTS_COLLECTION,
    ANOMALIES_COLLECTION,
    BASELINES_COLLECTION,
    EVENTS_COLLECTION,
    USERS_COLLECTION,
    AlertStatus,
    RiskLevel,
)
from services.risk_scorer import compute_risk_score

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ── Routes ───────────────────────────────────────────────────────────────

@router.get("/overview")
async def overview():
    """Return top‑level KPIs for the dashboard home screen."""
    db = get_database()

    total_users = await db[USERS_COLLECTION].count_documents({})
    active_users = await db[USERS_COLLECTION].count_documents({"is_active": True})
    total_events = await db[EVENTS_COLLECTION].count_documents({})
    total_anomalies = await db[ANOMALIES_COLLECTION].count_documents({})
    total_alerts = await db[ALERTS_COLLECTION].count_documents({})
    open_alerts = await db[ALERTS_COLLECTION].count_documents({"status": AlertStatus.OPEN.value})

    # Events in the last 24 h
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    events_24h = await db[EVENTS_COLLECTION].count_documents(
        {"timestamp": {"$gte": cutoff_24h}}
    )
    anomalies_24h = await db[ANOMALIES_COLLECTION].count_documents(
        {"detected_at": {"$gte": cutoff_24h}}
    )

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_events": total_events,
        "total_anomalies": total_anomalies,
        "total_alerts": total_alerts,
        "open_alerts": open_alerts,
        "events_last_24h": events_24h,
        "anomalies_last_24h": anomalies_24h,
    }


@router.get("/risk-summary")
async def risk_summary():
    """Return the number of users at each risk level."""
    db = get_database()
    user_ids = await db[USERS_COLLECTION].distinct("user_id")

    distribution: Dict[str, int] = {level.value: 0 for level in RiskLevel}
    user_risks: List[Dict[str, Any]] = []

    for uid in user_ids:
        score, level, _ = await compute_risk_score(uid, lookback_hours=24)
        distribution[level.value] += 1
        user_risks.append({"user_id": uid, "risk_score": score, "risk_level": level.value})

    return {"distribution": distribution, "users": user_risks}


@router.get("/activity")
async def recent_activity(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=1000),
):
    """Return a timeline of recent events."""
    db = get_database()
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    cursor = (
        db[EVENTS_COLLECTION]
        .find({"timestamp": {"$gte": cutoff}}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
    )
    events = await cursor.to_list(length=limit)
    return {"hours": hours, "count": len(events), "events": events}


@router.get("/top-risks")
async def top_risks(
    limit: int = Query(10, ge=1, le=50),
):
    """Return the users with the highest current risk scores."""
    db = get_database()
    user_ids = await db[USERS_COLLECTION].distinct("user_id")

    scored: List[Dict[str, Any]] = []
    for uid in user_ids:
        score, level, anomalies = await compute_risk_score(uid, lookback_hours=24)
        scored.append({
            "user_id": uid,
            "risk_score": score,
            "risk_level": level.value,
            "anomaly_count": len(anomalies),
        })

    # Sort descending by score and take top N
    scored.sort(key=lambda x: x["risk_score"], reverse=True)
    return {"users": scored[:limit]}


@router.get("/anomaly-trends")
async def anomaly_trends(
    days: int = Query(7, ge=1, le=30),
):
    """Return daily anomaly counts for the last *days* days."""
    db = get_database()

    trends: List[Dict[str, Any]] = []
    for offset in range(days):
        day_start = (datetime.utcnow() - timedelta(days=offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)
        count = await db[ANOMALIES_COLLECTION].count_documents(
            {"detected_at": {"$gte": day_start, "$lt": day_end}}
        )
        trends.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "anomaly_count": count,
        })

    # Chronological order (oldest first)
    trends.reverse()
    return {"days": days, "trends": trends}