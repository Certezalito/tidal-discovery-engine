"""Unit tests for SQLite database setup and GenreCacheService."""

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
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='track_genre_cache';"
    )
    table = cursor.fetchone()
    conn.close()
    assert table is not None
    assert table["name"] == "track_genre_cache"


def test_genre_cache_service_crud(temp_db_path):
    cache_service = GenreCacheService(db_path=temp_db_path)

    # Initial query on empty DB
    track_ids = ["t1", "t2", "t3"]
    cached, uncached = cache_service.get_cached_genres(track_ids)
    assert cached == {}
    assert set(uncached) == {"t1", "t2", "t3"}

    # Save records (t1: Classified, t2: Unknown)
    records = [
        {
            "track_id": "t1",
            "artist": "Artist 1",
            "title": "Title 1",
            "primary_genre": "Rock",
            "status": "CLASSIFIED",
        },
        {
            "track_id": "t2",
            "artist": "Artist 2",
            "title": "Title 2",
            "primary_genre": "Unknown",
            "status": "UNKNOWN",
        },
    ]
    cache_service.save_track_genres(records)

    # Query again
    cached, uncached = cache_service.get_cached_genres(track_ids)
    assert cached == {"t1": "Rock"}
    assert set(uncached) == {"t2", "t3"}

    # Update t2 from UNKNOWN to CLASSIFIED
    records_update = [
        {
            "track_id": "t2",
            "artist": "Artist 2",
            "title": "Title 2",
            "primary_genre": "Jazz",
            "status": "CLASSIFIED",
        }
    ]
    cache_service.save_track_genres(records_update)

    cached, uncached = cache_service.get_cached_genres(track_ids)
    assert cached == {"t1": "Rock", "t2": "Jazz"}
    assert uncached == ["t3"]
