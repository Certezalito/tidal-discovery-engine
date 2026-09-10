"""
Backward compatibility shim for genre_playlist_service.
Deprecated: Use src.services.genre_organizer_service instead.
"""
import warnings
from src.services.genre_organizer_service import (
    GenreRunSummary,
    calculate_sync_delta,
    run_genre_organizer_sync,
)

# Re-export run_genre_organizer_sync under legacy name with deprecation notice
def run_genre_playlist_sync(*args, **kwargs):
    warnings.warn(
        "run_genre_playlist_sync is deprecated. Use run_genre_organizer_sync from "
        "src.services.genre_organizer_service instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return run_genre_organizer_sync(*args, **kwargs)

__all__ = [
    "GenreRunSummary",
    "calculate_sync_delta",
    "run_genre_playlist_sync",
    "run_genre_organizer_sync",
]
