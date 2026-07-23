"""GenreCacheService managing persistent SQLite database caching for track genre classifications."""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from src.lib.db import DEFAULT_DB_PATH, get_db_connection, init_db


class GenreCacheService:
    """Service to interact with the track genre SQLite cache database."""

    def __init__(self, db_path: Union[str, Path] = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def get_cached_genres(
        self, track_ids: List[str]
    ) -> Tuple[Dict[str, str], List[str]]:
        """Given a list of track IDs, returns a tuple of:
        - Dict[track_id, primary_genre] for tracks with status 'CLASSIFIED'
        - List[track_id] for tracks uncached or with status 'UNKNOWN' (requiring Gemini lookup)
        """
        if not track_ids:
            return {}, []

        cached_classified: Dict[str, str] = {}
        uncached_or_unknown: set[str] = set(track_ids)

        conn = get_db_connection(self.db_path)
        try:
            placeholders = ",".join("?" for _ in track_ids)
            query = f"SELECT track_id, primary_genre, status FROM track_genre_cache WHERE track_id IN ({placeholders})"
            cursor = conn.execute(query, track_ids)
            
            for row in cursor.fetchall():
                t_id = row["track_id"]
                genre = row["primary_genre"]
                status = row["status"]

                if status == "CLASSIFIED" and genre and genre != "Unknown":
                    cached_classified[t_id] = genre
                    uncached_or_unknown.discard(t_id)
        finally:
            conn.close()

        return cached_classified, list(uncached_or_unknown)

    def save_track_genres(
        self, track_genre_records: List[Dict[str, str]]
    ) -> None:
        """Upserts a list of track genre records into SQLite cache.
        Each record should contain:
        - track_id (str)
        - artist (str)
        - title (str)
        - primary_genre (str)
        - status (str: 'CLASSIFIED' or 'UNKNOWN')
        """
        if not track_genre_records:
            return

        conn = get_db_connection(self.db_path)
        try:
            with conn:
                conn.executemany(
                    """
                    INSERT INTO track_genre_cache (track_id, artist, title, primary_genre, status, updated_at)
                    VALUES (:track_id, :artist, :title, :primary_genre, :status, CURRENT_TIMESTAMP)
                    ON CONFLICT(track_id) DO UPDATE SET
                        artist=excluded.artist,
                        title=excluded.title,
                        primary_genre=excluded.primary_genre,
                        status=excluded.status,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    track_genre_records,
                )
        finally:
            conn.close()
