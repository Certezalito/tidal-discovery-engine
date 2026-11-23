# Research & Root Cause Analysis: Fix Duplicate Tracks in Organized Playlists

**Feature**: `023-fix-organize-duplicate-tracks`
**Date**: 2026-11-23
**Status**: Complete

## 1. Root Cause Investigation

Inspection of `src/services/genre_organizer_service.py`, `src/services/tidal_service.py`, and production logs (`project.log` from 2026-11-23) identified four interacting defects responsible for repeating tracks and repeated playlist churn in `tde organize`:

1. **Duplicate occurrences in existing playlists are never detected or removed (`calculate_sync_delta`)**:
   - `calculate_sync_delta(desired_track_ids, existing_track_ids)` converts both inputs to sets (`desired_set`, `existing_set`).
   - If an existing playlist already contains `[T1, T1, T2]` while `desired` is `[T1, T2]`, `T1 in desired_set` is `True`, so `to_remove` is `[]` and the duplicate `T1` persists indefinitely.
   - Furthermore, removing by `track_id` via `remove_tracks_from_playlist` resolves **every** `item_uuid` matching that `track_id`, which would delete all copies rather than only surplus copies.

2. **Non-deterministic catalog release selection & ID-only comparison cause `+N -N` churn and duplicate recordings**:
   - In `run_genre_organizer_sync`, `unique_tracks` collapses scanned favorites by `get_track_identity_key(t)` (ISRC when available) and keeps whichever catalog `track_id` appeared first in the paginated favorites response.
   - In production (`project.log`, 2026-11-23), 7,060 scanned tracks collapsed to 5,759 unique identity keys (1,301 duplicate recordings across album/single/compilation releases).
   - Because playlist reconciliation compared only catalog `t.id` (ignoring recording identity / ISRC), any pagination order shift between runs swapped release A (`id=111`) for release B (`id=222`) of the exact same ISRC, producing `+N -N` churn across 123 playlists on an unchanged library.
   - Similarly, if an existing playlist contained two different catalog releases of the same ISRC (e.g., `111` and `222`), `calculate_sync_delta` had no awareness of ISRC equivalence.

3. **Type inconsistency & missing ISRC on fallback track parsing**:
   - `get_playlist_tracks` falls back to a lightweight `Track` object if `session.parse_track(item)` fails, and that fallback object omitted the `isrc` field.
   - Track IDs were compared without normalizing `str(t.id)`, risking `int` vs `str` mismatches between library tracks and playlist items.

4. **Missing defensive deduplication in `add_tracks_to_playlist`**:
   - `add_tracks_to_playlist` forwarded `track_ids` directly to `PUT /v2/playlists/{id}/items/add` without deduplicating the outgoing ID list.

---

## 2. Upstream Dependency Audit (`tidalapi` — Constitution Principle X)

- **Installed version**: `tidalapi 0.8.10` (`pyproject.toml` specifies `"tidalapi"`).
- **Upstream releases checked**: `tidalapi 0.8.11` / `0.9.0`.
- **Capabilities evaluated**:
  - `tidalapi.playlist.UserPlaylist.add(..., allow_duplicates=False)` uses Tidal's legacy **v1** endpoint (`POST playlists/{id}/items` with `onDupes="SKIP"`).
  - `tidalapi.playlist.UserPlaylist.remove_by_indices(indices)` uses Tidal's legacy **v1** endpoint (`DELETE playlists/{id}/items/{indices}` with ETag `If-None-Match`).
  - `tidalapi` does **not** expose v2 playlist item endpoints (`GET /v2/playlists/{id}/items`, `PUT /v2/playlists/{id}/items/add`, `PUT /v2/playlists/{id}/items/remove`).
- **Decision**: Retain the existing Tidal **v2** playlist item endpoints in `src/services/tidal_service.py` and do **not** downgrade/switch playlist syncing to `tidalapi` v1 methods.
- **Rationale**: The project intentionally migrated playlist sync to Tidal v2 endpoints to avoid cross-version v1/v2 replication lag on folder-owned playlists. Crucially, Tidal's v2 `GET /v2/playlists/{id}/items` already returns a unique per-slot `item_uuid` (`entry["id"]`) for every occurrence in a playlist, and `PUT /v2/playlists/{id}/items/remove?itemUuids=...` already supports surgical removal of individual duplicate occurrences without deleting the kept copy.
- **Alternatives considered**:
  - *Switch to `UserPlaylist.remove_by_indices` (v1)*: Rejected because v1 endpoints suffer from replication lag on v2 folder playlists and require index shifting + ETag management.
  - *Pass undocumented `onDupes=SKIP` query param to v2 `items/add`*: Rejected per Constitution Principle I (do not guess unverified API parameters); instead, client-side deduplication + surgical `item_uuid` cleanup guarantees duplicate-free state without relying on undocumented v2 parameters.

---

## 3. Design Decisions

### Decision 1: Playlist Deduplication Key vs. SQLite Cache Key
- **Decision**: Introduce `get_playlist_dedup_key(track)` in `src/services/tidal_service.py`:
  - Returns `f"isrc:{normalized_isrc}"` when `track` has a non-empty string ISRC.
  - Falls back to `f"id:{str(track.id)}"` when ISRC is absent or unavailable.
  - Keep `get_track_identity_key(track)` unchanged for SQLite genre cache lookups and favorites exclusion so existing cached records remain 100% backward-compatible.
- **Rationale**: Satisfies `FR-002` exactly: identical recordings across different releases (same ISRC) collapse to one playlist entry, distinct recordings (remixes, live versions with distinct ISRCs) are preserved, and tracks lacking an ISRC still deduplicate by exact catalog track ID without being silently dropped.
- **Alternatives considered**:
  - *Reuse `get_track_identity_key` (`fallback:title|artist`)*: Rejected because tracks missing ISRC with the same title/artist (e.g., different versions) would be collapsed by title+artist rather than exact catalog ID, and tracks missing title/artist returned `""` and were dropped.

### Decision 2: Deterministic Release Selection & Existing-Copy Preservation
- **Decision**: During library aggregation in `run_genre_organizer_sync`, group all scanned tracks by `dedup_key` into a `TrackDedupGroup` containing:
  - `dedup_key`: canonical dedup key (`isrc:...` or `id:...`)
  - `cache_key`: SQLite cache lookup key (`get_track_identity_key(t)` or fallback `id:...`)
  - `candidate_track_ids`: deduplicated list of `str(t.id)` sorted deterministically (numeric ascending when all digits, else lexicographical ascending)
  - `canonical_track_id`: `candidate_track_ids[0]` (used for new playlists or when no matching copy exists in the playlist)
- When syncing an existing playlist (`calculate_playlist_sync_plan`):
  1. Scan `existing_tracks` in playlist order.
  2. For each existing track, compute its `existing_dedup_key` (via `get_playlist_dedup_key`, plus fallback lookup from catalog ID → `dedup_key` in case an existing playlist item lacks ISRC metadata).
  3. If `existing_dedup_key` is in `desired_groups`:
     - If not yet satisfied: **keep** this existing occurrence (regardless of which catalog release ID of that recording it is — satisfies `FR-003` zero-churn rule!).
     - If already satisfied: mark this surplus occurrence for **removal** by its `item_uuid` (if valid string UUID) or fallback strategy if `item_uuid` is unavailable.
  4. If `existing_dedup_key` is NOT in `desired_groups`:
     - Mark this occurrence for **removal** by its `item_uuid` (if valid string UUID, else `str(t.id)`), removing all copies of non-qualifying tracks (`FR-007`).
  5. For each `desired_group` not satisfied by any kept existing occurrence:
     - Schedule `desired_group.canonical_track_id` in `to_add_ids`.
- **Rationale**: Completely eliminates `+N -N` release-swapping churn across consecutive runs (`SC-003`), repairs existing playlists with 2+ copies in a single sync (`SC-002`), and guarantees deterministic selection for newly created playlists (`FR-003`).
- **Alternatives considered**:
  - *Always replace existing release with `canonical_track_id`*: Rejected because it causes unnecessary initial edits on existing playlists and was explicitly rejected in clarification Q1.
  - *Wipe and recreate playlists with duplicates*: Rejected because it breaks playlist stability, loses playlist creation metadata, and contradicts `User Story 2` / `SC-002`.

### Decision 3: Safe Fallback When `item_uuid` Is Unavailable
- **Decision**: When removing a surplus duplicate of a *qualifying* track:
  - Normal path (Tidal v2 returns 36-char string `item_uuid`): pass only the surplus `item_uuid`s to `remove_tracks_from_playlist`. The kept occurrence stays untouched.
  - Degraded fallback path (`item_uuid` is `None` or non-string, e.g., legacy mock or malformed response): pass `str(track.id)` to `to_remove` (which removes all copies of that ID) AND include `str(track.id)` once in `to_add` (since `sync_playlist_tracks` executes removals before additions, leaving exactly 1 copy).
- **Rationale**: Prevents accidental deletion of all copies when `item_uuid` is missing, while keeping normal v2 syncs minimal and surgical.

### Decision 4: Post-Deduplication Minimum Genre Size Thresholding
- **Decision**: Perform `dedup_key` grouping before populating `genre_groups_norm` and evaluating `len(group_dedup_keys) >= min_genre_size`.
- **Rationale**: Directly enforces `FR-004` — every standalone playlist's track count reflects unique deduplicated tracks only.

### Decision 5: Backward Compatibility of `calculate_sync_delta`
- **Decision**: Retain `calculate_sync_delta(desired_track_ids, existing_track_ids)` as a public helper (preserving its signature and existing test behavior), enhanced so that:
  - IDs are compared as normalized strings while preserving caller types when returning results.
  - Extra duplicate occurrences in `existing_track_ids` are detected and included in `to_remove` (one entry per surplus occurrence).
  - `run_genre_organizer_sync` calls the richer `calculate_playlist_sync_plan(desired_groups, existing_tracks)` for full recording-identity + `item_uuid` reconciliation.
- **Rationale**: Preserves 100% compatibility with existing tests and `genre_playlist_service.py` re-exports while fixing duplicate awareness in both helpers.
