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
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.requests import Request
from starlette.exceptions import HTTPException as StarletteHTTPException

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

app.include_router(events_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


# ── Utility endpoints ────────────────────────────────────────────────────

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Lightweight health probe."""
    return {"status": "healthy"}


@app.post("/api/seed", tags=["Admin"])
async def seed():
    """Populate the database with demo data (clears existing data first)."""
    result = await seed_database()
    return {"message": "Database seeded successfully", "summary": result}


@app.post("/api/rebuild-baselines", tags=["Admin"])
async def rebuild_baselines():
    """Force‑rebuild behavioural baselines for all users."""
    count = await rebuild_all_baselines()
    return {"message": f"Rebuilt baselines for {count} users"}

# ── Static / Frontend Hosting ───────────────────────────────────────────

frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")

# Only mount assets if the directory exists (post-build)
assets_dir = os.path.join(frontend_dist, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "API route not found"})
    
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse(status_code=404, content={"detail": "Frontend route not found. Please run 'npm run build' in the frontend directory."})

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    file_path = os.path.join(frontend_dist, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"detail": "Frontend not built"}


# ── Run with uvicorn ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)