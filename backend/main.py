"""
main.py
───────
Application entry‑point for the Insider Threat Behavioral Baseline System.

* Creates the FastAPI application.
* Registers all API routers.
* Wires up MongoDB connect / disconnect lifecycle events.
* Provides a ``/seed`` endpoint for one‑click demo data population.
* Provides a health‑check endpoint.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import alerts_router, dashboard_router, events_router, users_router
from database.connection import close_mongo_connection, connect_to_mongo
from data.seed_data import seed_database
from ml.baseline_engine import rebuild_all_baselines


# ── Application lifecycle ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks for the FastAPI application."""
    # Startup
    await connect_to_mongo()
    print("[APP] Insider Threat Behavioral Baseline System started.")
    yield
    # Shutdown
    await close_mongo_connection()
    print("[APP] Shutdown complete.")


# ── App factory ──────────────────────────────────────────────────────────

app = FastAPI(
    title="Insider Threat Behavioral Baseline System",
    description=(
        "Backend API for user activity logging, behavioural baseline "
        "generation, statistical anomaly detection, risk scoring, "
        "and alert management."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS – allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ─────────────────────────────────────────────────────

app.include_router(events_router)
app.include_router(users_router)
app.include_router(alerts_router)
app.include_router(dashboard_router)


# ── Utility endpoints ────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Health‑check / landing endpoint."""
    return {
        "service": "Insider Threat Behavioral Baseline System",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Lightweight health probe."""
    return {"status": "healthy"}


@app.post("/seed", tags=["Admin"])
async def seed():
    """Populate the database with demo data (clears existing data first)."""
    result = await seed_database()
    return {"message": "Database seeded successfully", "summary": result}


@app.post("/rebuild-baselines", tags=["Admin"])
async def rebuild_baselines():
    """Force‑rebuild behavioural baselines for all users."""
    count = await rebuild_all_baselines()
    return {"message": f"Rebuilt baselines for {count} users"}


# ── Run with uvicorn ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)