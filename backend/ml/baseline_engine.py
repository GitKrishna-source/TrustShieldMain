"""
ml/baseline_engine.py
─────────────────────
Builds and maintains per‑user behavioural baselines from historical
event data stored in MongoDB.

A baseline captures:
* **Feature means & standard deviations** – for z‑score anomaly detection.
* **Event‑type distribution** – expected proportions of each activity type.
* **Typical active hours / days** – to flag out‑of‑norm time patterns.
* **Sequence patterns** – bigram transition probabilities so that
  unusual event orderings can be spotted.
* **Daily volume statistics** – mean and std of events per day.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from database.connection import get_database
from database.models import BASELINES_COLLECTION, EVENTS_COLLECTION, BaselineModel
from ml.feature_extractor import extract_event_features


# ─────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────

async def build_baseline(user_id: str) -> Dict[str, Any]:
    """Compute a full behavioural baseline for *user_id* from their event
    history and persist it to the ``baselines`` collection.

    Returns the baseline document as a plain dict.
    """
    db = get_database()
    events_col = db[EVENTS_COLLECTION]

    # Fetch all events for this user, sorted chronologically
    cursor = events_col.find({"user_id": user_id}).sort("timestamp", 1)
    events: List[Dict[str, Any]] = await cursor.to_list(length=None)

    if not events:
        # No history yet → store an empty/default baseline
        baseline = BaselineModel(user_id=user_id).model_dump()
        await _upsert_baseline(baseline)
        return baseline

    # ── 1. Per‑event feature statistics ───────────────────────────────
    feature_matrix: Dict[str, List[float]] = defaultdict(list)
    for ev in events:
        feats = extract_event_features(ev)
        for k, v in feats.items():
            feature_matrix[k].append(v)

    feature_means = {k: float(np.mean(v)) for k, v in feature_matrix.items()}
    feature_stds = {k: float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
                    for k, v in feature_matrix.items()}

    # ── 2. Event‑type distribution ────────────────────────────────────
    type_counter = Counter(ev.get("event_type", "unknown") for ev in events)
    total = sum(type_counter.values())
    event_type_distribution = {k: round(v / total, 4) for k, v in type_counter.items()}

    # ── 3. Typical hours and days ─────────────────────────────────────
    hour_counter: Counter = Counter()
    day_counter: Counter = Counter()
    for ev in events:
        ts = _ensure_datetime(ev.get("timestamp"))
        hour_counter[ts.hour] += 1
        day_counter[ts.weekday()] += 1

    # "Typical" = hours/days that represent ≥5 % of events
    threshold = 0.05 * total
    typical_hours = sorted(h for h, c in hour_counter.items() if c >= threshold)
    typical_days = sorted(d for d, c in day_counter.items() if c >= threshold)

    # ── 4. Daily volume statistics ────────────────────────────────────
    events_per_date: Dict[str, int] = defaultdict(int)
    for ev in events:
        ts = _ensure_datetime(ev.get("timestamp"))
        events_per_date[ts.strftime("%Y-%m-%d")] += 1

    daily_counts = list(events_per_date.values())
    avg_events_per_day = float(np.mean(daily_counts))
    std_events_per_day = float(np.std(daily_counts, ddof=1)) if len(daily_counts) > 1 else 0.0

    # ── 5. Sequence (bigram) transition probabilities ─────────────────
    sequence_patterns = _compute_bigram_probabilities(events)

    # ── 6. Persist ────────────────────────────────────────────────────
    baseline = BaselineModel(
        user_id=user_id,
        feature_means=feature_means,
        feature_stds=feature_stds,
        event_type_distribution=event_type_distribution,
        typical_hours=typical_hours,
        typical_days=typical_days,
        avg_events_per_day=avg_events_per_day,
        std_events_per_day=std_events_per_day,
        sequence_patterns=sequence_patterns,
        total_events_analysed=len(events),
        last_updated=datetime.utcnow(),
    ).model_dump()

    await _upsert_baseline(baseline)
    return baseline


async def get_baseline(user_id: str) -> Dict[str, Any] | None:
    """Retrieve the stored baseline for *user_id*, or ``None``."""
    db = get_database()
    return await db[BASELINES_COLLECTION].find_one(
        {"user_id": user_id}, {"_id": 0}
    )


async def rebuild_all_baselines() -> int:
    """Rebuild baselines for every user that has at least one event.

    Returns the number of baselines rebuilt.
    """
    db = get_database()
    user_ids = await db[EVENTS_COLLECTION].distinct("user_id")
    for uid in user_ids:
        await build_baseline(uid)
    return len(user_ids)


# ─────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────

async def _upsert_baseline(baseline: Dict[str, Any]) -> None:
    db = get_database()
    await db[BASELINES_COLLECTION].update_one(
        {"user_id": baseline["user_id"]},
        {"$set": baseline},
        upsert=True,
    )


def _ensure_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return datetime.utcnow()


def _compute_bigram_probabilities(events: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute event‑type bigram transition probabilities.

    Keys are ``"prev_type→next_type"`` strings; values are probabilities
    in [0, 1].
    """
    if len(events) < 2:
        return {}

    bigram_counter: Counter = Counter()
    prefix_counter: Counter = Counter()

    for i in range(len(events) - 1):
        prev_type = events[i].get("event_type", "unknown")
        next_type = events[i + 1].get("event_type", "unknown")
        bigram_counter[f"{prev_type}→{next_type}"] += 1
        prefix_counter[prev_type] += 1

    probabilities: Dict[str, float] = {}
    for bigram, count in bigram_counter.items():
        prefix = bigram.split("→")[0]
        probabilities[bigram] = round(count / prefix_counter[prefix], 4)

    return probabilities