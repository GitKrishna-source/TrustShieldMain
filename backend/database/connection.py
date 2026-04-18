"""
database/connection.py
──────────────────────
Async MongoDB connection manager using Motor.
Provides a singleton database handle that is initialised once at
application startup and closed on shutdown.
"""

from motor.motor_asyncio import AsyncIOMotorClient

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Module‑level state
# ---------------------------------------------------------------------------
MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DATABASE_NAME: str = os.getenv("DATABASE_NAME", "insider_threat_db")

_client: AsyncIOMotorClient | None = None
_db = None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

async def connect_to_mongo() -> None:
    """Open the Motor client and select the default database."""
    global _client, _db
    _client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    
    # Ensure topology is discovered and connection is stable before continuing
    await _client.admin.command('ping')
    
    _db = _client[DATABASE_NAME]
    print(f"[DB] Connected to MongoDB at {MONGO_URL}/{DATABASE_NAME}")


async def close_mongo_connection() -> None:
    """Gracefully close the Motor client."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        print("[DB] MongoDB connection closed.")


def get_database():
    """Return the active database handle.

    Raises
    ------
    RuntimeError
        If called before ``connect_to_mongo`` has been awaited.
    """
    if _db is None:
        raise RuntimeError(
            "Database not initialised. Call 'connect_to_mongo()' first."
        )
    return _db