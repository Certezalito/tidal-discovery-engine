# Data Model: Fix Duplicate Tracks in Organized Playlists

**Feature**: `023-fix-organize-duplicate-tracks`
**Date**: 2026-11-23

## Overview

No SQLite schema migrations are required. The local `genre_cache.db` schema and `track_id` cache keys (`isrc:<ISRC>` / `fallback:<title>|<artist>`) remain fully backward-compatible. All new structures are in-memory value objects used during `run_genre_organizer_sync` to ensure recording-level deduplication, deterministic release selection, and surgical duplicate removal.

---

## Entities

### 1. `TrackDedupGroup` (In-Memory Value Object)
Represents a single unique musical recording (or catalog track when ISRC is unavailable) aggregated from one or more entries in the user's scanned Tidal library.

| Field | Type | Constraints / Rules |
|-------|------|---------------------|
| `dedup_key` | `str` | Required, unique per library scan. Format: `isrc:<UPPER_ALNUM_ISRC>` if valid ISRC exists, else `id:<str(track.id)>`. |
| `cache_key` | `str` | Lookup key for `GenreCacheService` (`get_track_identity_key(representative_track)`). |
| `representative_track` | `Track` | The library track object corresponding to `canonical_track_id` (used for Gemini metadata when uncached). |
| `candidate_track_ids` | `list[str]` | Non-empty, deduplicated list of stringified Tidal catalog track IDs sharing this `dedup_key`, sorted deterministically (numeric ascending if all digits, else lexicographical ascending). |
| `canonical_track_id` | `str` | Equal to `candidate_track_ids[0]`. Deterministic default ID used for new playlists or when no matching copy exists in an existing playlist. |

**Validation Rules**:
- Every scanned favorite track with a non-empty `id` belongs to exactly one `TrackDedupGroup`.
- `len(candidate_track_ids) >= 1` and contains zero duplicates.
- Ordering of `candidate_track_ids` is independent of Tidal favorites API pagination order.

---

### 2. `PlaylistTrackOccurrence` (Existing Tidal Playlist Item)
Represents one slot/position in an existing Tidal genre playlist returned by `get_playlist_tracks`.

| Field | Type | Constraints / Rules |
|-------|------|---------------------|
| `track_id` | `str` | Stringified Tidal catalog track ID (`str(track.id)`). |
| `isrc` | `str` | Normalized uppercase alphanumeric ISRC if present on track (`isinstance(raw, str)`), else `""`. |
| `item_uuid` | `Optional[str]` | 36-character UUID identifying this exact playlist slot (from Tidal v2 `entry["id"]`), or `None` if absent/non-string. |
| `dedup_key` | `str` | Resolved via `get_playlist_dedup_key(track)`; if ISRC is missing on the playlist item, falls back to matching `track_id` against known library `TrackDedupGroup`s before defaulting to `id:<track_id>`. |

---

### 3. `PlaylistSyncPlan` (Sync Reconciliation Output)
Represents the exact minimal mutations needed to reconcile an existing genre playlist against its desired `TrackDedupGroup`s.

| Field | Type | Constraints / Rules |
|-------|------|---------------------|
| `to_add_ids` | `list[str]` | Unique catalog track IDs to add (one per unsatisfied desired `TrackDedupGroup`, plus re-add IDs only in degraded non-UUID duplicate fallback). Zero duplicates. |
| `to_remove_items` | `list[str]` | Playlist `item_uuid`s (preferred) or catalog track IDs (fallback when `item_uuid` is unavailable) to remove. Includes all occurrences of non-qualifying tracks and all surplus (2nd, 3rd, …) occurrences of qualifying tracks. |
| `duplicates_removed` | `int` | Count of surplus duplicate occurrences scheduled for removal (subset of `len(to_remove_items)`), used for clear diagnostic logging. |

---

## State Transitions (Per Existing Playlist Sync)

```text
Existing Playlist State
  │
  ├── [No changes: every desired dedup_key appears once, 0 extra/obsolete items]
  │     → to_add_ids = [], to_remove_items = []
  │     → Log "Playlist '<name>' is up to date." (0 API writes)
  │
  ├── [Has surplus duplicates (same ID or same ISRC) and/or obsolete/missing tracks]
  │     → Keep 1st matching occurrence per desired dedup_key (zero release-swap churn)
  │     → Queue surplus duplicate item_uuids + all obsolete item_uuids in to_remove_items
  │     → Queue canonical_track_id for each missing desired dedup_key in to_add_ids
  │     → Execute remove_tracks_from_playlist(...) THEN add_tracks_to_playlist(...)
  │     → Result: Exactly 1 occurrence per desired dedup_key, 0 duplicates, 0 obsolete tracks
  │
  └── [Subsequent run on unchanged library]
        → All desired dedup_keys matched 1:1 by kept occurrences
        → to_add_ids = [], to_remove_items = [] (Idempotent / Zero Churn)
```

---

## Relationships

- **Library Scan (1) → `TrackDedupGroup` (N)**: 1-to-many; deduplicates scanned library tracks before genre grouping and thresholding.
- **`TrackDedupGroup` (N) ↔ Genre Group (M)**: Many-to-many (a single recording can belong to 1 primary genre + up to 3 sub-genres); within any single Genre Group, each `dedup_key` appears at most once.
- **Genre Group (1) → `PlaylistSyncPlan` (1)**: Each qualifying genre (`len(unique_dedup_keys) >= min_genre_size`, plus `"Others"` / `"Unknown"`) produces one `PlaylistSyncPlan` against its target Tidal playlist.
