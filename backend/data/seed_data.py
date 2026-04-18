"""
data/seed_data.py
─────────────────
Generates realistic demo data for the Insider Threat Behavioral Baseline
System.  When executed (or called via ``seed_database()``), it:

1. Creates sample users across multiple departments.
2. Generates a realistic event history for each user spanning several
   days, with *most* events following normal patterns and a handful of
   deliberately anomalous events injected for specific "risky" users.
3. Builds behavioural baselines for every user.
4. Runs anomaly detection on the injected anomalous events so that
   alerts are present in the database for demo / demo‑dashboard use.
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

from database.connection import connect_to_mongo, close_mongo_connection, get_database
from database.models import (
    ALERTS_COLLECTION,
    ANOMALIES_COLLECTION,
    BASELINES_COLLECTION,
    EVENTS_COLLECTION,
    USERS_COLLECTION,
    Department,
    EventType,
    UserModel,
)
from ml.baseline_engine import build_baseline
from services.behavioral_profiler import process_event


# ── Sample user definitions ──────────────────────────────────────────────

SAMPLE_USERS: List[Dict[str, Any]] = [
    {"user_id": "USR001", "username": "alice_chen",     "email": "alice.chen@corp.com",     "department": Department.ENGINEERING, "role": "senior_engineer",   "clearance_level": 3},
    {"user_id": "USR002", "username": "bob_martinez",   "email": "bob.martinez@corp.com",   "department": Department.FINANCE,     "role": "financial_analyst", "clearance_level": 2},
    {"user_id": "USR003", "username": "carol_jones",    "email": "carol.jones@corp.com",    "department": Department.HR,          "role": "hr_manager",        "clearance_level": 3},
    {"user_id": "USR004", "username": "dave_wilson",    "email": "dave.wilson@corp.com",    "department": Department.IT,          "role": "sysadmin",          "clearance_level": 4},
    {"user_id": "USR005", "username": "eve_brown",      "email": "eve.brown@corp.com",      "department": Department.SALES,       "role": "sales_rep",         "clearance_level": 1},
    {"user_id": "USR006", "username": "frank_taylor",   "email": "frank.taylor@corp.com",   "department": Department.ENGINEERING, "role": "junior_developer",  "clearance_level": 2},
    {"user_id": "USR007", "username": "grace_lee",      "email": "grace.lee@corp.com",      "department": Department.LEGAL,       "role": "legal_counsel",     "clearance_level": 4},
    {"user_id": "USR008", "username": "hank_davis",     "email": "hank.davis@corp.com",     "department": Department.EXECUTIVE,   "role": "vp_operations",     "clearance_level": 5},
    {"user_id": "USR009", "username": "irene_garcia",   "email": "irene.garcia@corp.com",   "department": Department.MARKETING,   "role": "content_manager",   "clearance_level": 1},
    {"user_id": "USR010", "username": "jake_miller",    "email": "jake.miller@corp.com",    "department": Department.IT,          "role": "network_engineer",  "clearance_level": 3},
]

# Users that will receive deliberately anomalous events
RISKY_USER_IDS = {"USR002", "USR004", "USR006"}

# ── Normal event patterns ────────────────────────────────────────────────

NORMAL_EVENT_TYPES = [
    EventType.LOGIN, EventType.LOGOUT, EventType.FILE_ACCESS,
    EventType.EMAIL_SENT, EventType.EMAIL_RECEIVED, EventType.WEBSITE_VISIT,
]

INTERNAL_IPS = ["10.0.1.10", "10.0.1.20", "10.0.2.15", "192.168.1.100"]
INTERNAL_RESOURCES = [
    "/shared/reports/q4_summary.pdf",
    "/shared/docs/employee_handbook.docx",
    "/projects/alpha/src/main.py",
    "/intranet/wiki/onboarding",
    "/shared/templates/expense_report.xlsx",
]


# ── Anomalous event templates ────────────────────────────────────────────

def _anomalous_events(user_id: str, base_date: datetime) -> List[Dict[str, Any]]:
    """Return a small batch of deliberately suspicious events."""
    events: List[Dict[str, Any]] = []

    # 1. Large file download at 3 AM
    events.append({
        "event_id": str(uuid.uuid4()),
        "user_id": user_id,
        "event_type": EventType.FILE_DOWNLOAD.value,
        "timestamp": base_date.replace(hour=3, minute=12),
        "source_ip": "10.0.1.20",
        "destination": "45.33.32.156",  # external IP
        "resource": "/confidential/financials/annual_report_2025.xlsx",
        "metadata": {"file_size_mb": 248, "classification": "confidential"},
    })

    # 2. USB device on a weekend
    weekend_date = base_date + timedelta(days=(5 - base_date.weekday()) % 7)
    events.append({
        "event_id": str(uuid.uuid4()),
        "user_id": user_id,
        "event_type": EventType.USB_CONNECTED.value,
        "timestamp": weekend_date.replace(hour=22, minute=45),
        "source_ip": "10.0.1.20",
        "destination": None,
        "resource": "SANDISK_USB_32GB",
        "metadata": {"device_serial": "SN-9938271"},
    })

    # 3. Privilege escalation attempt
    events.append({
        "event_id": str(uuid.uuid4()),
        "user_id": user_id,
        "event_type": EventType.PRIVILEGE_ESCALATION.value,
        "timestamp": base_date.replace(hour=2, minute=30),
        "source_ip": "10.0.1.20",
        "destination": "10.0.0.1",
        "resource": "/admin/user_management",
        "metadata": {"attempted_role": "superadmin"},
    })

    # 4. Burst of emails to external addresses
    for i in range(5):
        events.append({
            "event_id": str(uuid.uuid4()),
            "user_id": user_id,
            "event_type": EventType.EMAIL_SENT.value,
            "timestamp": base_date.replace(hour=1, minute=5 + i),
            "source_ip": "10.0.1.20",
            "destination": f"external_contact_{i}@gmail.com",
            "resource": None,
            "metadata": {"attachment_count": random.randint(1, 4), "subject": "FWD: Internal data"},
        })

    return events


# ── Main seeder ──────────────────────────────────────────────────────────

async def seed_database() -> Dict[str, Any]:
    """Populate the database with demo data.

    Returns a summary dict with counts of inserted documents.
    """
    db = get_database()

    # Clear existing data without dropping schema
    for col_name in [USERS_COLLECTION, EVENTS_COLLECTION, BASELINES_COLLECTION,
                     ANOMALIES_COLLECTION, ALERTS_COLLECTION]:
        await db[col_name].delete_many({})
    print("[SEED] Cleared existing collections (deleted documents).")

    # ── 1. Insert users ───────────────────────────────────────────────
    user_docs = []
    for u in SAMPLE_USERS:
        doc = UserModel(
            user_id=u["user_id"],
            username=u["username"],
            email=u["email"],
            department=u["department"],
            role=u["role"],
            clearance_level=u["clearance_level"],
        ).model_dump()
        user_docs.append(doc)
    await db[USERS_COLLECTION].insert_many(user_docs)
    print(f"[SEED] Inserted {len(user_docs)} users.")

    # ── 2. Generate normal events ─────────────────────────────────────
    now = datetime.utcnow()
    all_events: List[Dict[str, Any]] = []

    for u in SAMPLE_USERS:
        uid = u["user_id"]
        # Generate 7 days of normal activity (8‑20 events / day)
        for day_offset in range(7, 0, -1):
            day = now - timedelta(days=day_offset)
            num_events = random.randint(8, 20)
            for _ in range(num_events):
                hour = random.choice(range(8, 19))  # work hours
                minute = random.randint(0, 59)
                ts = day.replace(hour=hour, minute=minute, second=random.randint(0, 59))

                etype = random.choice(NORMAL_EVENT_TYPES)
                ev = {
                    "event_id": str(uuid.uuid4()),
                    "user_id": uid,
                    "event_type": etype.value,
                    "timestamp": ts,
                    "source_ip": random.choice(INTERNAL_IPS),
                    "destination": random.choice(INTERNAL_RESOURCES) if etype in (
                        EventType.FILE_ACCESS, EventType.WEBSITE_VISIT
                    ) else None,
                    "resource": random.choice(INTERNAL_RESOURCES) if etype == EventType.FILE_ACCESS else None,
                    "metadata": {},
                }
                all_events.append(ev)

    # Sort chronologically before insertion
    all_events.sort(key=lambda e: e["timestamp"])

    if all_events:
        await db[EVENTS_COLLECTION].insert_many(all_events)
    print(f"[SEED] Inserted {len(all_events)} normal events.")

    # ── 3. Build baselines from the normal data ───────────────────────
    for u in SAMPLE_USERS:
        await build_baseline(u["user_id"])
    print("[SEED] Built baselines for all users.")

    # ── 4. Inject anomalous events for risky users ────────────────────
    anomalous_total = 0
    for uid in RISKY_USER_IDS:
        anomalous_events = _anomalous_events(uid, now - timedelta(hours=6))
        for ev in anomalous_events:
            await db[EVENTS_COLLECTION].insert_one(ev)
            # Run through the profiler so anomalies & alerts are created
            await process_event(ev)
            anomalous_total += 1

    print(f"[SEED] Injected and processed {anomalous_total} anomalous events.")

    # ── Summary ───────────────────────────────────────────────────────
    summary = {
        "users_created": len(user_docs),
        "normal_events": len(all_events),
        "anomalous_events": anomalous_total,
        "baselines_built": len(SAMPLE_USERS),
        "total_anomalies": await db[ANOMALIES_COLLECTION].count_documents({}),
        "total_alerts": await db[ALERTS_COLLECTION].count_documents({}),
    }
    print(f"[SEED] Seeding complete: {summary}")
    return summary


# ── CLI entry point ──────────────────────────────────────────────────────

async def _main():
    await connect_to_mongo()
    try:
        await seed_database()
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(_main())