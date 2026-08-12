# Phase 0: Research

## 1. TidalAPI Folder Pagination
- **Problem**: `get_playlists_in_folder` currently calls `folder.items()` without parameters.
- **Findings**: `tidalapi.playlist.Folder.items(self, offset: int = 0, limit: int = 50)` supports pagination.
- **Decision**: We need to implement a loop in `get_playlists_in_folder` to fetch items in batches of 50 (or maximum limit) until `total_number_of_items` is reached or the returned list is empty.

## 2. Duplicate Playlist Handling
- **Problem**: The system maps existing playlists by `name.lower()`, which overwrites duplicates in the dictionary and leaves them untouched in Tidal.
- **Findings**: The spec requires keeping one playlist (the oldest) and deleting the rest. When paginating, `tidalapi` usually returns items in order of addition (oldest first or newest first). We can sort existing playlists by `created` date (if available) or just keep the first one encountered and queue the rest for deletion.
- **Decision**: Update `genre_playlist_service.py` to group existing playlists by name. For any name with multiple playlists, keep the one with the earliest `created` date (or just the first one if dates aren't available) and delete the others using `delete_playlist`.

## 3. Track Replacement vs Delta Sync
- **Problem**: The spec clarification states to "Completely replace all tracks".
- **Findings**: Option A was chosen over Option B (Merge). The current `calculate_sync_delta` method already calculates the exact difference (removing what's missing, adding what's new), which effectively replaces the state while minimizing API calls.
- **Decision**: Retain `calculate_sync_delta` for efficient syncing (as it fulfills the "replace" requirement efficiently compared to deleting all tracks and re-adding them), but ensure that after the duplicate playlist cleanup, the remaining playlist is correctly synced.
