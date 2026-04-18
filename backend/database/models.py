"""
database/models.py
──────────────────
Pydantic models that define the shape of every MongoDB document used by
the Insider Threat Behavioral Baseline System.

Collections
-----------
* **users**       – employee / account records
* **events**      – raw activity log entries
* **baselines**   – per‑user behavioural baselines
* **anomalies**   – detected anomalous events
* **alerts**      – risk‑scored alerts surfaced to analysts
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    """Categories of monitored user activity."""
    LOGIN = "login"
    LOGOUT = "logout"
    FILE_ACCESS = "file_access"
    FILE_DOWNLOAD = "file_download"
    FILE_UPLOAD = "file_upload"
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    USB_CONNECTED = "usb_connected"
    USB_DISCONNECTED = "usb_disconnected"
    WEBSITE_VISIT = "website_visit"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    VPN_CONNECTION = "vpn_connection"
    PRINT_JOB = "print_job"
    APPLICATION_INSTALL = "application_install"


class RiskLevel(str, Enum):
    """Risk severity tiers."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Lifecycle states for an alert."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class Department(str, Enum):
    """Departments within the organisation."""
    ENGINEERING = "engineering"
    FINANCE = "finance"
    HR = "hr"
    SALES = "sales"
    MARKETING = "marketing"
    IT = "it"
    LEGAL = "legal"
    EXECUTIVE = "executive"


# ── Document Models ───────────────────────────────────────────────────────

class UserModel(BaseModel):
    """An employee / user account."""
    user_id: str = Field(..., description="Unique employee identifier")
    username: str
    email: str
    department: Department
    role: str = "employee"
    clearance_level: int = Field(1, ge=1, le=5)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EventModel(BaseModel):
    """A single raw activity event."""
    event_id: str = Field(..., description="UUID for this event")
    user_id: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_ip: Optional[str] = None
    destination: Optional[str] = None
    resource: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaselineModel(BaseModel):
    """Behavioural baseline for a single user.

    Stores statistical summaries (mean, std‑dev, counts) of activity
    features so that new events can be compared against the user's
    historical norm.
    """
    user_id: str
    feature_means: Dict[str, float] = Field(default_factory=dict)
    feature_stds: Dict[str, float] = Field(default_factory=dict)
    event_type_distribution: Dict[str, float] = Field(default_factory=dict)
    typical_hours: List[int] = Field(default_factory=list)
    typical_days: List[int] = Field(default_factory=list)
    avg_events_per_day: float = 0.0
    std_events_per_day: float = 0.0
    avg_session_duration_min: float = 0.0
    std_session_duration_min: float = 0.0
    sequence_patterns: Dict[str, float] = Field(default_factory=dict)
    total_events_analysed: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class AnomalyModel(BaseModel):
    """A detected anomaly linked back to a specific event."""
    anomaly_id: str
    event_id: str
    user_id: str
    anomaly_type: str                        # e.g. "z_score", "sequence", "time"
    description: str
    severity_score: float = Field(0.0, ge=0.0, le=1.0)
    z_score: Optional[float] = None
    feature_name: Optional[str] = None
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class AlertModel(BaseModel):
    """A risk‑scored alert surfaced to security analysts."""
    alert_id: str
    user_id: str
    anomaly_ids: List[str] = Field(default_factory=list)
    risk_score: float = Field(0.0, ge=0.0, le=100.0)
    risk_level: RiskLevel = RiskLevel.LOW
    title: str
    description: str
    status: AlertStatus = AlertStatus.OPEN
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


# ── Collection name constants ─────────────────────────────────────────────

USERS_COLLECTION = "users"
EVENTS_COLLECTION = "events"
BASELINES_COLLECTION = "baselines"
ANOMALIES_COLLECTION = "anomalies"
ALERTS_COLLECTION = "alerts"