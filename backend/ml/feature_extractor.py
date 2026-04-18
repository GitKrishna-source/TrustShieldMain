"""
ml/feature_extractor.py
───────────────────────
Extracts numerical feature vectors from raw event documents so that
the baseline engine and anomaly detector can operate on structured
numeric data.

Features extracted per event
----------------------------
* ``hour_of_day``       – 0‑23
* ``day_of_week``       – 0 (Mon) → 6 (Sun)
* ``is_weekend``        – 0 or 1
* ``is_after_hours``    – 1 if hour < 6 or hour > 20
* ``event_type_code``   – ordinal encoding of EventType
* ``has_usb``           – 1 if event involves USB
* ``has_external_dest`` – 1 if destination looks external
* ``metadata_count``    – number of metadata key/value pairs

Aggregate features (per‑user, per‑day window)
----------------------------------------------
* ``events_per_day``
* ``unique_event_types``
* ``after_hours_ratio``
* ``file_download_count``
* ``email_sent_count``
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List

from database.models import EventType


# ── Ordinal mapping for event types ──────────────────────────────────────

EVENT_TYPE_CODES: Dict[str, int] = {et.value: idx for idx, et in enumerate(EventType)}


# ── Single‑event feature extraction ──────────────────────────────────────

def extract_event_features(event: Dict[str, Any]) -> Dict[str, float]:
    """Transform a single event document into a flat numeric feature dict.

    Parameters
    ----------
    event : dict
        A raw event document from MongoDB (or a dict matching EventModel).

    Returns
    -------
    dict[str, float]
        Named numeric features ready for statistical comparison.
    """
    ts: datetime = event.get("timestamp", datetime.utcnow())
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)

    hour = ts.hour
    dow = ts.weekday()
    event_type: str = event.get("event_type", "login")
    destination: str = event.get("destination", "") or ""
    metadata: dict = event.get("metadata", {}) or {}

    features: Dict[str, float] = {
        "hour_of_day": float(hour),
        "day_of_week": float(dow),
        "is_weekend": 1.0 if dow >= 5 else 0.0,
        "is_after_hours": 1.0 if (hour < 6 or hour > 20) else 0.0,
        "event_type_code": float(EVENT_TYPE_CODES.get(event_type, 0)),
        "has_usb": 1.0 if "usb" in event_type else 0.0,
        "has_external_dest": 1.0 if _is_external(destination) else 0.0,
        "metadata_count": float(len(metadata)),
    }
    return features


# ── Aggregate feature extraction (window of events) ─────────────────────

def extract_aggregate_features(events: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute aggregate / summary features over a collection of events.

    These features characterise a user's activity *pattern* over a
    time window rather than a single event.

    Parameters
    ----------
    events : list[dict]
        List of event documents for one user within a time window.

    Returns
    -------
    dict[str, float]
        Aggregate feature dict.
    """
    if not events:
        return {
            "events_per_day": 0.0,
            "unique_event_types": 0.0,
            "after_hours_ratio": 0.0,
            "file_download_count": 0.0,
            "email_sent_count": 0.0,
            "usb_event_count": 0.0,
            "avg_metadata_count": 0.0,
        }

    # Group events by date
    events_by_date: Dict[str, int] = defaultdict(int)
    type_counter: Counter = Counter()
    after_hours = 0
    file_downloads = 0
    emails_sent = 0
    usb_events = 0
    total_metadata = 0

    for ev in events:
        ts = ev.get("timestamp", datetime.utcnow())
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        date_key = ts.strftime("%Y-%m-%d")
        events_by_date[date_key] += 1

        etype = ev.get("event_type", "")
        type_counter[etype] += 1

        hour = ts.hour
        if hour < 6 or hour > 20:
            after_hours += 1

        if etype == EventType.FILE_DOWNLOAD.value:
            file_downloads += 1
        if etype == EventType.EMAIL_SENT.value:
            emails_sent += 1
        if "usb" in etype:
            usb_events += 1
        total_metadata += len(ev.get("metadata", {}))

    n = len(events)
    num_days = max(len(events_by_date), 1)

    return {
        "events_per_day": float(n) / num_days,
        "unique_event_types": float(len(type_counter)),
        "after_hours_ratio": float(after_hours) / n,
        "file_download_count": float(file_downloads),
        "email_sent_count": float(emails_sent),
        "usb_event_count": float(usb_events),
        "avg_metadata_count": float(total_metadata) / n,
    }


# ── Internal helper ──────────────────────────────────────────────────────

def _is_external(destination: str) -> bool:
    """Heuristic: treat a destination as external if it is not a private
    network address or an internal domain.
    """
    if not destination:
        return False
    internal_markers = ("10.", "192.168.", "172.16.", ".internal", ".corp", "localhost")
    return not any(destination.startswith(m) or destination.endswith(m) for m in internal_markers)