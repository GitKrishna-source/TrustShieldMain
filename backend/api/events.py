"""
api/events.py
─────────────
FastAPI router for activity‑event ingestion and retrieval.

Routes
------
POST /events/           – log a new user activity event
GET  /events/           – list events (with optional filters)
GET  /events/{event_id} – get a single event by ID
GET  /events/user/{uid} – get events for a specific user
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database.connection import get_database
from database.models import EVENTS_COLLECTION, EventModel, EventType
from services.behavioral_profiler import process_event

router = APIRouter(prefix="/events", tags=["Events"])


# ── Request / Response schemas ───────────────────────────────────────────

class EventCreateRequest(BaseModel):
    """Payload for creating a new event."""
    user_id: str
    event_type: EventType
    source_ip: Optional[str] = None
    destination: Optional[str] = None
    resource: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventResponse(BaseModel):
    """Wrapper returned after event creation."""
    event: Dict[str, Any]
    processing_result: Dict[str, Any]


# ── Routes ───────────────────────────────────────────────────────────────

@router.post("/", response_model=EventResponse, status_code=201)
async def create_event(payload: EventCreateRequest):
    """Log a new activity event and run it through the behavioural
    analysis pipeline (anomaly detection → risk scoring → alerting).
    """
    db = get_database()

    event = EventModel(
        event_id=str(uuid.uuid4()),
        user_id=payload.user_id,
        event_type=payload.event_type,
        timestamp=datetime.utcnow(),
        source_ip=payload.source_ip,
        destination=payload.destination,
        resource=payload.resource,
        metadata=payload.metadata,
    ).model_dump()

    # Persist the event
    await db[EVENTS_COLLECTION].insert_one(event)

    # Run through the behavioural profiler pipeline
    processing_result = await process_event(event)

    return EventResponse(event=event, processing_result=processing_result)


@router.get("/")
async def list_events(
    user_id: Optional[str] = Query(None),
    event_type: Optional[EventType] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve events with optional filtering by user and/or type."""
    db = get_database()
    query: Dict[str, Any] = {}
    if user_id:
        query["user_id"] = user_id
    if event_type:
        query["event_type"] = event_type.value

    cursor = (
        db[EVENTS_COLLECTION]
        .find(query, {"_id": 0})
        .sort("timestamp", -1)
        .skip(offset)
        .limit(limit)
    )
    events = await cursor.to_list(length=limit)
    total = await db[EVENTS_COLLECTION].count_documents(query)

    return {"total": total, "limit": limit, "offset": offset, "events": events}


@router.get("/{event_id}")
async def get_event(event_id: str):
    """Get a single event by its ID."""
    db = get_database()
    event = await db[EVENTS_COLLECTION].find_one(
        {"event_id": event_id}, {"_id": 0}
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/user/{user_id}")
async def get_user_events(
    user_id: str,
    limit: int = Query(50, ge=1, le=500),
):
    """Get the most recent events for a specific user."""
    db = get_database()
    cursor = (
        db[EVENTS_COLLECTION]
        .find({"user_id": user_id}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
    )
    events = await cursor.to_list(length=limit)
    return {"user_id": user_id, "count": len(events), "events": events}