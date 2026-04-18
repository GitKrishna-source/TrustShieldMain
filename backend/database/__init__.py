"""
database package
────────────────
Re‑exports connection helpers and collection‑name constants so that the
rest of the application can simply ``from database import get_database``.
"""

from database.connection import connect_to_mongo, close_mongo_connection, get_database

__all__ = ["connect_to_mongo", "close_mongo_connection", "get_database"]
