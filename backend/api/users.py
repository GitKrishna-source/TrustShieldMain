"""
api/users.py
────────────
FastAPI router for user (employee) management.

Routes
------
POST /users/             – create a new user
GET  /users/             – list all users
GET  /users/{user_id}    – get user details
PUT  /users/{user_id}    – update user fields
GET  /users/{user_id}/profile – full behavioural profile
POST /users/{user_id}/baseline – rebuild the user's baseline
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database.connection import get_database
from database.models import USERS_COLLECTION, Department, UserModel
from ml.baseline_engine import build_baseline, get_baseline
from services.behavioral_profiler import get_user_profile

router = APIRouter(prefix="/users", tags=["Users"])


# ── Request schemas ──────────────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    """Payload for registering a new user / employee."""
    user_id: str
    username: str
    email: str
    department: Department
    role: str = "employee"
    clearance_level: int = Field(1, ge=1, le=5)


class UserUpdateRequest(BaseModel):
    """Fields that can be updated on an existing user."""
    username: Optional[str] = None
    email: Optional[str] = None
    department: Optional[Department] = None
    role: Optional[str] = None
    clearance_level: Optional[int] = Field(None, ge=1, le=5)
    is_active: Optional[bool] = None


# ── Routes ───────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def create_user(payload: UserCreateRequest):
    """Register a new employee in the system."""
    db = get_database()

    # Check for duplicate
    existing = await db[USERS_COLLECTION].find_one({"user_id": payload.user_id})
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")

    user = UserModel(
        user_id=payload.user_id,
        username=payload.username,
        email=payload.email,
        department=payload.department,
        role=payload.role,
        clearance_level=payload.clearance_level,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ).model_dump()

    await db[USERS_COLLECTION].insert_one(user)
    return {"message": "User created", "user": user}


@router.get("/")
async def list_users(
    department: Optional[Department] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List users with optional department / active‑status filtering."""
    db = get_database()
    query: Dict[str, Any] = {}
    if department:
        query["department"] = department.value
    if is_active is not None:
        query["is_active"] = is_active

    cursor = (
        db[USERS_COLLECTION]
        .find(query, {"_id": 0})
        .skip(offset)
        .limit(limit)
    )
    users = await cursor.to_list(length=limit)
    total = await db[USERS_COLLECTION].count_documents(query)

    return {"total": total, "limit": limit, "offset": offset, "users": users}


@router.get("/{user_id}")
async def get_user(user_id: str):
    """Return a single user record."""
    db = get_database()
    user = await db[USERS_COLLECTION].find_one(
        {"user_id": user_id}, {"_id": 0}
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}")
async def update_user(user_id: str, payload: UserUpdateRequest):
    """Partially update user fields."""
    db = get_database()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.utcnow()

    result = await db[USERS_COLLECTION].update_one(
        {"user_id": user_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    updated = await db[USERS_COLLECTION].find_one(
        {"user_id": user_id}, {"_id": 0}
    )
    return {"message": "User updated", "user": updated}


@router.get("/{user_id}/profile")
async def user_profile(user_id: str):
    """Return the full behavioural profile for a user (baseline, recent
    anomalies, risk posture).
    """
    db = get_database()
    user = await db[USERS_COLLECTION].find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = await get_user_profile(user_id)
    return profile


@router.post("/{user_id}/baseline")
async def rebuild_user_baseline(user_id: str):
    """Force a baseline rebuild for the given user."""
    db = get_database()
    user = await db[USERS_COLLECTION].find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    baseline = await build_baseline(user_id)
    return {"message": "Baseline rebuilt", "baseline": baseline}