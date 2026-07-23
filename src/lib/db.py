"""SQLite database helper module and connection management for Tidal Discovery Engine."""

import os
import sqlite3
from pathlib import Path
from typing import Union


DEFAULT_DB_PATH = os.getenv("GENRE_CACHE_DB_PATH", "data/genre_cache.db")


def get_db_connection(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Creates and returns a sqlite3 Connection to the specified database path.
    
    Ensures parent directories exist before connecting.
    """
    path = Path(db_path)
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> None:
    """Initializes the SQLite database schema for genre caching."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS track_genre_cache (
                    track_id TEXT PRIMARY KEY,
                    artist TEXT NOT NULL,
                    title TEXT NOT NULL,
                    primary_genre TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('CLASSIFIED', 'UNKNOWN')),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_track_genre_status ON track_genre_cache(status);"
            )
    finally:
        conn.close()
