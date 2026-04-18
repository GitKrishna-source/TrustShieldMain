"""
api package
───────────
Re‑exports all FastAPI routers so that ``main.py`` can register them
with a single import.
"""

from api.events import router as events_router
from api.users import router as users_router
from api.alerts import router as alerts_router
from api.dashboard import router as dashboard_router

__all__ = [
    "events_router",
    "users_router",
    "alerts_router",
    "dashboard_router",
]
