# Service & CLI Contracts: Fix Duplicate Tracks in Organized Playlists

**Feature**: `023-fix-organize-duplicate-tracks`
**Date**: 2026-11-23

## 1. `src/services/tidal_service.py` Contracts

### `get_playlist_dedup_key(track) -> str`
Computes the playlist deduplication key for a track object.
- **Input**: Any track object with `.id` and optional `.isrc`.
- **Output**:
  - `f"isrc:{normalize_isrc(raw_isrc)}"` when `raw_isrc` is a non-empty `str` that normalizes to a non-empty value.
  - `f"id:{str(track_id)}"` when ISRC is missing/empty/non-string and `track_id` is not `None` and `str(track_id).strip()` is non-empty.
  - `""` if neither ISRC nor a valid track ID is present.
- **Invariants**:
  - Never treats a `MagicMock` or non-string `.isrc` as a valid ISRC.
  - Two releases of the same recording (same ISRC, different catalog IDs) produce the exact same key.
  - Two distinct recordings (e.g., studio vs. remix/live with different ISRCs) produce distinct keys.

### `get_playlist_tracks(session, playlist_id, max_retries=3, retry_delay=1) -> Optional[list]`
- Preserves existing signature and pagination/retry semantics.
- **Contract update**: The fallback `Track` object constructed when `session.parse_track(item)` fails MUST preserve `"isrc": item.get("isrc")` in addition to `id`, `title`, `artist`, and `item_uuid`.

### `add_tracks_to_playlist(session_or_playlist, playlist_id_or_tracks, track_ids=None, chunk_size=50, max_retries=3, retry_delay=1) -> bool`
- Preserves both existing call signatures.
- **Contract update**: Before chunking and sending `PUT /v2/playlists/{id}/items/add`, deduplicates `str_track_ids` in-place while preserving first-seen order so duplicate track IDs are never sent in a single add operation.

---

## 2. `src/services/genre_organizer_service.py` Contracts

### `calculate_playlist_sync_plan(desired_groups, existing_tracks) -> PlaylistSyncPlan`
Computes the minimal, duplicate-free sync mutations for an existing playlist.
- **Inputs**:
  - `desired_groups`: `list[TrackDedupGroup]` (unique per `dedup_key`).
  - `existing_tracks`: `list[Track]` returned by `get_playlist_tracks`.
- **Outputs**: `PlaylistSyncPlan(to_add_ids, to_remove_items, duplicates_removed)`.
- **Guarantees**:
  1. **Zero duplicates**: At most one existing occurrence is kept per `dedup_key`. Every 2nd, 3rd, … occurrence (whether identical catalog ID or alternate release with same ISRC) is scheduled in `to_remove_items`.
  2. **Zero churn (`FR-003`)**: If an existing playlist already holds any valid catalog release matching a desired `dedup_key`, that existing occurrence is kept rather than swapped for `canonical_track_id`.
  3. **Complete obsolete removal (`FR-007`)**: Every occurrence of a track whose `dedup_key` is not in `desired_groups` is scheduled in `to_remove_items`.
  4. **Surgical UUID removal**: When an existing occurrence has a valid 36-char string `item_uuid`, `item_uuid` is placed in `to_remove_items` so `remove_tracks_from_playlist` removes only that specific slot.
  5. **Degraded non-UUID fallback**: When a surplus duplicate of a qualifying track lacks a valid `item_uuid`, its `track_id` is placed in `to_remove_items` (removing all copies) and `canonical_track_id` is placed in `to_add_ids` (restoring 1 copy).
  6. **Idempotency (`FR-009`)**: Running `calculate_playlist_sync_plan` on the post-sync playlist state returns `to_add_ids == []`, `to_remove_items == []`, `duplicates_removed == 0`.

### `calculate_sync_delta(desired_track_ids: list, existing_track_ids: list) -> tuple[list, list]`
Backward-compatible ID-level helper.
- **Guarantees**:
  - Preserves existing behavior for unique lists (`desired=["1","2","3"], existing=["2","3","4"] -> (["1"], ["4"])`).
  - Normalizes IDs as strings for membership checks so `int` vs `str` mismatches do not cause false add/remove pairs.
  - Detects duplicate entries in `existing_track_ids` (for both desired and undesired IDs) and includes each surplus occurrence in `to_remove`.

---

## 3. CLI & Logging Contract (`tde organize` / `genre-organizer`)

- **CLI flags/arguments**: No breaking changes; all existing options (`--folder`, `--min-genre-size`, `--refresh-genres`, `--wipe-folder`, `--wipe-only`, `--yes`, `--flex`, etc.) remain unchanged.
- **Log output**:
  - When a playlist is updated and duplicate tracks were removed, logs clearly report additions and removals (e.g., `Synced playlist '<name>': +<add> -<remove> tracks (removed <dups> duplicates).` when `dups > 0`, or existing `Synced playlist '<name>': +<add> -<remove> tracks.` when `dups == 0`).
  - When a playlist is already duplicate-free and matches desired tracks, logs `Playlist '<name>' is up to date.`
- **Summary output**: `GenreRunSummary.tracks_added` and `GenreRunSummary.tracks_removed` accurately include added tracks and removed tracks (including removed duplicates).
