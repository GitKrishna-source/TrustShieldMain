"""
api/auth.py
───────────
Lightweight JWT authentication for the Insider Threat Behavioral Baseline
System.  Provides login and token-verification endpoints.

Demo credentials are seeded for hackathon use.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

import hashlib
import hmac
import json
import base64
import os

router = APIRouter(prefix="/auth", tags=["Auth"])

# ── Config ───────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv("JWT_SECRET", "trustshield-hackathon-secret-2026")
TOKEN_EXPIRY_HOURS = 24

# ── Demo credentials ────────────────────────────────────────────────────
# In production these would live in a database with hashed passwords.

DEMO_USERS = {
    "admin@corp.com": {
        "password": "admin123",
        "user_id": "ADMIN001",
        "username": "admin",
        "role": "admin",
        "department": "it",
    },
    "alice.chen@corp.com": {
        "password": "password123",
        "user_id": "USR001",
        "username": "alice_chen",
        "role": "employee",
        "department": "engineering",
    },
    "bob.martinez@corp.com": {
        "password": "password123",
        "user_id": "USR002",
        "username": "bob_martinez",
        "role": "employee",
        "department": "finance",
    },
    "dave.wilson@corp.com": {
        "password": "password123",
        "user_id": "USR004",
        "username": "dave_wilson",
        "role": "employee",
        "department": "it",
    },
}


# ── Simple JWT helpers (no external dependency) ─────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _create_token(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, default=str).encode())
    signature = hmac.new(
        SECRET_KEY.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256
    ).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _verify_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        expected_sig = hmac.new(
            SECRET_KEY.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(_b64url_decode(payload_b64))
        # Check expiry
        exp = payload.get("exp")
        if exp and datetime.fromisoformat(exp) < datetime.utcnow():
            return None
        return payload
    except Exception:
        return None


# ── Request/Response schemas ─────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


class UserInfo(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    department: str


# ── Security scheme ──────────────────────────────────────────────────────

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Extract and verify the current user from the Authorization header."""
    if not credentials:
        return None
    payload = _verify_token(credentials.credentials)
    return payload


# ── Routes ───────────────────────────────────────────────────────────────

@router.post("/login")
async def login(payload: LoginRequest):
    """Authenticate with email + password, receive a JWT."""
    user = DEMO_USERS.get(payload.email)
    if not user or user["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token_payload = {
        "user_id": user["user_id"],
        "username": user["username"],
        "email": payload.email,
        "role": user["role"],
        "department": user["department"],
        "exp": (datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)).isoformat(),
    }
    token = _create_token(token_payload)

    return {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": payload.email,
            "role": user["role"],
            "department": user["department"],
        },
    }


@router.get("/me")
async def get_me(user: Optional[dict] = Depends(get_current_user)):
    """Return the current authenticated user's info."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "department": user["department"],
    }
