"""GenreCacheService managing persistent SQLite database caching for track genre classifications."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.lib.db import DEFAULT_DB_PATH, get_db_connection, init_db


class GenreCacheService:
    """Service to interact with the track genre SQLite cache database."""

    def __init__(self, db_path: Union[str, Path] = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def get_cached_genres(
        self, track_ids: List[str], refresh_genres: bool = False
    ) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
        """Given a list of track IDs, returns a tuple of:
        - Dict[track_id, {"primary_genre": str, "sub_genres": list[str]}] for tracks with status 'CLASSIFIED'
        - List[track_id] for tracks uncached or with status 'UNKNOWN' (requiring Gemini lookup)

        If refresh_genres is True, tracks that lack sub_genres are treated as uncached so that
        sub-genres can be backfilled via Gemini.
        """
        if not track_ids:
            return {}, []

        cached_classified: Dict[str, Dict[str, Any]] = {}
        uncached_or_unknown: set[str] = set(track_ids)

        conn = get_db_connection(self.db_path)
        try:
            placeholders = ",".join("?" for _ in track_ids)
            query = f"SELECT track_id, primary_genre, sub_genres, status FROM track_genre_cache WHERE track_id IN ({placeholders})"
            cursor = conn.execute(query, track_ids)

            for row in cursor.fetchall():
                t_id = row["track_id"]
                genre = row["primary_genre"]
                status = row["status"]
                sub_genres_raw = row["sub_genres"]

                sub_genres: List[str] = []
                if sub_genres_raw:
                    try:
                        parsed = json.loads(sub_genres_raw)
                        if isinstance(parsed, list):
                            sub_genres = [s for s in parsed if isinstance(s, str)]
                    except Exception:
                        pass

                if status == "CLASSIFIED" and genre and genre != "Unknown":
                    if refresh_genres and not sub_genres:
                        # Existing cached track lacks sub_genres; treat as uncached to backfill
                        continue

                    cached_classified[t_id] = {
                        "primary_genre": genre,
                        "sub_genres": sub_genres,
                    }
                    uncached_or_unknown.discard(t_id)
        finally:
            conn.close()

        return cached_classified, list(uncached_or_unknown)

    def save_track_genres(
        self, track_genre_records: List[Dict[str, Any]]
    ) -> None:
        """Upserts a list of track genre records into SQLite cache.
        Each record should contain:
        - track_id (str)
        - artist (str)
        - title (str)
        - primary_genre (str)
        - sub_genres (list[str] or JSON string, optional)
        - status (str: 'CLASSIFIED' or 'UNKNOWN')
        """
        if not track_genre_records:
            return

        formatted_records = []
        for r in track_genre_records:
            sub_genres_val = r.get("sub_genres")
            if isinstance(sub_genres_val, list):
                sub_genres_str = json.dumps(sub_genres_val)
            elif isinstance(sub_genres_val, str):
                sub_genres_str = sub_genres_val
            else:
                sub_genres_str = None

            formatted_records.append({
                "track_id": r["track_id"],
                "artist": r.get("artist", ""),
                "title": r.get("title", ""),
                "primary_genre": r.get("primary_genre", ""),
                "sub_genres": sub_genres_str,
                "status": r.get("status", "CLASSIFIED"),
            })

        conn = get_db_connection(self.db_path)
        try:
            with conn:
                conn.executemany(
                    """
                    INSERT INTO track_genre_cache (track_id, artist, title, primary_genre, sub_genres, status, updated_at)
                    VALUES (:track_id, :artist, :title, :primary_genre, :sub_genres, :status, CURRENT_TIMESTAMP)
                    ON CONFLICT(track_id) DO UPDATE SET
                        artist=excluded.artist,
                        title=excluded.title,
                        primary_genre=excluded.primary_genre,
                        sub_genres=excluded.sub_genres,
                        status=excluded.status,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    formatted_records,
                )
        finally:
            conn.close()

