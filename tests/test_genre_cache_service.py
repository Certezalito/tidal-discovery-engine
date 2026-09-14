"""Unit tests for SQLite database setup and GenreCacheService with sub_genres support."""

import sqlite3
import tempfile
from pathlib import Path
import pytest

from src.lib.db import init_db, get_db_connection
from src.services.genre_cache_service import GenreCacheService


@pytest.fixture
def temp_db_path():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "test_genre_cache.db"
        yield db_file


def test_init_db(temp_db_path):
    init_db(temp_db_path)
    conn = get_db_connection(temp_db_path)
    cursor = conn.execute("PRAGMA table_info(track_genre_cache);")
    columns = [row["name"] for row in cursor.fetchall()]
    conn.close()
    assert "track_id" in columns
    assert "primary_genre" in columns
    assert "sub_genres" in columns
    assert "status" in columns


def test_init_db_migration_adds_sub_genres(temp_db_path):
    """Simulates an older DB schema missing sub_genres, ensuring migration adds it."""
    conn = get_db_connection(temp_db_path)
    with conn:
        conn.execute(
            """
            CREATE TABLE track_genre_cache (
                track_id TEXT PRIMARY KEY,
                artist TEXT NOT NULL,
                title TEXT NOT NULL,
                primary_genre TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('CLASSIFIED', 'UNKNOWN')),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    conn.close()

    # Re-running init_db should apply migration
    init_db(temp_db_path)

    conn = get_db_connection(temp_db_path)
    cursor = conn.execute("PRAGMA table_info(track_genre_cache);")
    columns = [row["name"] for row in cursor.fetchall()]
    conn.close()
    assert "sub_genres" in columns


def test_genre_cache_service_crud_with_sub_genres(temp_db_path):
    cache_service = GenreCacheService(db_path=temp_db_path)

    # Initial query on empty DB
    track_ids = ["t1", "t2", "t3"]
    cached, uncached = cache_service.get_cached_genres(track_ids)
    assert cached == {}
    assert set(uncached) == {"t1", "t2", "t3"}

    # Save records (t1: Classified with subgenres, t2: Unknown)
    records = [
        {
            "track_id": "t1",
            "artist": "Foals",
            "title": "Tron",
            "primary_genre": "Math Rock",
            "sub_genres": ["Dance-Punk", "Post-Punk Revival"],
            "status": "CLASSIFIED",
        },
        {
            "track_id": "t2",
            "artist": "Artist 2",
            "title": "Title 2",
            "primary_genre": "Unknown",
            "sub_genres": [],
            "status": "UNKNOWN",
        },
    ]
    cache_service.save_track_genres(records)

    # Query again
    cached, uncached = cache_service.get_cached_genres(track_ids)
    assert "t1" in cached
    assert cached["t1"]["primary_genre"] == "Math Rock"
    assert cached["t1"]["sub_genres"] == ["Dance-Punk", "Post-Punk Revival"]
    assert set(uncached) == {"t2", "t3"}

    # Update t2 from UNKNOWN to CLASSIFIED
    records_update = [
        {
            "track_id": "t2",
            "artist": "Artist 2",
            "title": "Title 2",
            "primary_genre": "Jazz",
            "sub_genres": ["Bop", "Cool Jazz"],
            "status": "CLASSIFIED",
        }
    ]
    cache_service.save_track_genres(records_update)

    cached, uncached = cache_service.get_cached_genres(track_ids)
    assert cached["t1"]["primary_genre"] == "Math Rock"
    assert cached["t2"]["primary_genre"] == "Jazz"
    assert cached["t2"]["sub_genres"] == ["Bop", "Cool Jazz"]
    assert uncached == ["t3"]


def test_genre_cache_service_refresh_genres_flag(temp_db_path):
    cache_service = GenreCacheService(db_path=temp_db_path)

    # Insert one legacy track without sub_genres, and one modern track with sub_genres
    records = [
        {
            "track_id": "legacy_track",
            "artist": "Classic Band",
            "title": "Old Song",
            "primary_genre": "Blues Rock",
            "sub_genres": None,
            "status": "CLASSIFIED",
        },
        {
            "track_id": "modern_track",
            "artist": "New Band",
            "title": "New Song",
            "primary_genre": "Synthwave",
            "sub_genres": ["Darksynth"],
            "status": "CLASSIFIED",
        },
    ]
    cache_service.save_track_genres(records)

    # Without refresh_genres: both are returned as cached
    cached, uncached = cache_service.get_cached_genres(["legacy_track", "modern_track"], refresh_genres=False)
    assert "legacy_track" in cached
    assert cached["legacy_track"]["sub_genres"] == []
    assert "modern_track" in cached
    assert uncached == []

    # With refresh_genres=True: legacy_track lacking sub_genres is marked uncached for backfill
    cached, uncached = cache_service.get_cached_genres(["legacy_track", "modern_track"], refresh_genres=True)
    assert "modern_track" in cached
    assert "legacy_track" not in cached
    assert uncached == ["legacy_track"]
