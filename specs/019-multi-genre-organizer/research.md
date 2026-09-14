# Research: Multi-Genre Track Organization & Folder Wipe

**Feature**: `019-multi-genre-organizer`  
**Date**: 2026-09-10 (Revised: 2026-09-14)

---

## 1. AI Prompt & Schema Design for Primary and Sub-Genres

### Decision
Update the Gemini structured JSON classification schema ([`GenreClassificationResult`](file:///home/ec2-user/github/tidal-discovery-engine/src/services/gemini_service.py#L30-L35)) to:
```python
class GenreClassificationResult(BaseModel):
    isrc: str | None = None
    title: str | None = None
    artist: str | None = None
    primary_genre: str | None = None
    sub_genres: list[str] = Field(default_factory=list, description="Up to 3 specific sub-genres. Exclude broad genres.")
```
Update the prompt in [`classify_tracks_genres`](file:///home/ec2-user/github/tidal-discovery-engine/src/services/gemini_service.py#L385) to:
- Identify exactly ONE specific `primary_genre` (e.g., "Math Rock", "Synthwave", "Trip Hop").
- Identify up to 3 specific `sub_genres` (e.g., ["Dance-Punk", "Post-Punk Revival", "Art Punk"]).
- Explicitly prohibit broad umbrella categories (e.g., "Rock", "Pop", "Alternative", "Electronic", "Music").

### Rationale
- Aligns strictly with user requirements ("pull the primary and sub genres, not the broad genres").
- Enforces Constitution Principle VI (Token Efficiency) by bounding sub-genres to at most 3 per song.
- Pydantic schema validation ensures strict JSON output without parsing failures.

### Alternatives Considered
- *Comma-separated single string*: Prone to inconsistent delimiter formatting (e.g. slashes, commas, dashes).
- *Returning broad parent genres*: Explicitly forbidden by user request.
- *Unbounded list of sub-genres*: Causes token bloat and playlist proliferation.

---

## 2. Database Schema Migration and Cache Storage

### Decision
Extend the existing SQLite table `track_genre_cache` in [`src/lib/db.py`](file:///home/ec2-user/github/tidal-discovery-engine/src/lib/db.py) by adding a new column:
```sql
ALTER TABLE track_genre_cache ADD COLUMN sub_genres TEXT;
```
`sub_genres` stores a JSON-encoded list of strings (e.g., `'["Dance-Punk", "Post-Punk Revival", "Art Punk"]'`).
Existing rows without `sub_genres` read as `None` or `'[]'`.

Update [`GenreCacheService`](file:///home/ec2-user/github/tidal-discovery-engine/src/services/genre_cache_service.py):
- `get_cached_genres`: Returns dict with `'primary_genre'` and `'sub_genres'`.
- `save_track_genres`: Serializes `sub_genres` list as JSON string on insert/update.

### Rationale
- Zero migration downtime; SQLite `ALTER TABLE ADD COLUMN` is non-destructive and instantaneous.
- Fully backwards compatible with existing cached data.
- Storing JSON in a `TEXT` column avoids joining auxiliary tables and maintains high read/write throughput for batch lookups.

### Alternatives Considered
- *Creating a normalized `track_sub_genres` table*: Adds JOIN complexity and migration overhead with no performance benefit for a local single-user cache.
- *Rebuilding cache from scratch*: Discards user's existing classifications, wasting previously spent API tokens.

---

## 3. Cache Refresh Strategy (`--refresh-genres`)

### Decision
Add a `--refresh-genres` flag to the `organize` CLI command in [`src/cli/main.py`](file:///home/ec2-user/github/tidal-discovery-engine/src/cli/main.py):
- When `--refresh-genres` is **False** (default):
  - Tracks found in the cache with `status == 'CLASSIFIED'` are accepted as-is. If an existing cached track has no `sub_genres` stored, it is assigned only to its `primary_genre` playlist.
- When `--refresh-genres` is **True**:
  - The cache lookup filters out or invalidates rows where `sub_genres` is NULL or empty, queuing those tracks to be re-classified by Gemini in batches.

### Rationale
- Fulfills Clarification Session 2026-09-10 (Option A).
- Protects user from accidental large API token consumption on regular automated runs.
- Conforms to Constitution Principle VII (Local Caching) & Principle IX (Sensible Defaults).

---

## 4. Multi-Playlist Grouping, Thresholding & Idempotency

### Decision
In [`genre_organizer_service.py`](file:///home/ec2-user/github/tidal-discovery-engine/src/services/genre_organizer_service.py):
1. **Multi-Genre Placement**:
   For each track, canonicalize its `primary_genre` and each of its `sub_genres` using `normalize_genre_name()`.
   Add the track ID to each genre bucket:
   ```python
   all_genres = {primary_genre} | set(sub_genres)
   for genre in all_genres:
       genre_groups[genre].append(track_id)
   ```
2. **Thresholding (`--min-genre-size 5`)**:
   - Primary genres with $< 5$ tracks are routed to `"Others"`.
   - Sub-genres with $< 5$ tracks are suppressed completely from playlist creation.
   - Dedicated playlists are created only for qualifying primary and sub-genres with $\ge 5$ tracks.
3. **Idempotent Sync**:
   Tracks are synchronized using existing set-diff logic (`tracks_to_add` and `tracks_to_delete`), ensuring clean updates without duplicate tracks.

### Rationale
- Guarantees that "Foals - Tron" appears in its primary genre playlist ("Math Rock") and all qualifying sub-genre playlists ("Dance-Punk", "Post-Punk Revival") without creating clutter from sparse 1-2 track sub-genres.

---

## 5. Folder Deletion Mechanics: Tidal GUI vs. API Research

### Research Findings
- **GUI Behavior**: In the Tidal web and desktop applications, attempting to delete a playlist folder that contains playlists is blocked or rejected. The user must first delete or move all playlists out of the folder before Tidal allows the folder container itself to be deleted.
- **API Behavior**:
  - In the Tidal API (`tidalapi.playlist.Folder.remove()`, which sends `PUT my-collection/playlists/folders/remove`), the server enforces the exact same constraint: attempting to remove a folder that still contains playlist items fails with an HTTP error (400 Bad Request / 409 Conflict).
  - However, user playlists can *always* be deleted individually via [`tidalapi.playlist.UserPlaylist.delete()`](file:///home/ec2-user/github/tidal-discovery-engine/src/services/tidal_service.py#L403-L413) (which sends `DELETE my-collection/playlists/{id}` or `session.user.delete_playlist(id)`). This deletion succeeds immediately regardless of whether the playlist resides at root level or inside a folder.

### Decision
1. **Wipe Strategy (Emptying the Folder Container)**:
   - When `--wipe-folder` is requested:
     1. Retrieve all playlists currently inside the folder via [`get_playlists_in_folder(session, folder_id)`](file:///home/ec2-user/github/tidal-discovery-engine/src/services/tidal_service.py#L311).
     2. Delete each contained playlist individually using [`delete_playlist(session, playlist_id)`](file:///home/ec2-user/github/tidal-discovery-engine/src/services/tidal_service.py#L403).
     3. Track and log each deletion, incrementing `summary.playlists_wiped`.
     4. **Retain the empty folder container**: Reusing the existing folder container avoids deleting and recreating the folder, preventing race conditions, avoiding transient folder name duplication (e.g., "Genres (1)"), and preserving the persistent folder URL link (`https://tidal.com/browse/folder/{folder_id}`).
     5. Proceed with generating and synchronizing fresh genre playlists into the clean folder.
2. **Interactive Confirmation & Non-Interactive Override**:
   - Because playlist deletion is irreversible in Tidal, when `--wipe-folder` or `--wipe-only` is invoked in an interactive terminal session (`sys.stdin.isatty()`), prompt the user:
     ```text
     Are you sure you want to delete all {count} playlists in folder '{folder}'? [y/N]:
     ```
     If declined, abort cleanly with code 0.
   - When `--yes` / `-y` is passed (or when running non-interactively in scripts/cron jobs), the confirmation prompt is bypassed.
3. **Standalone `--wipe-only` Mode**:
   - When `--wipe-only` is passed (e.g., `organize --wipe-only` or `organize --wipe-folder --wipe-only`), execute the folder playlist wipe and then exit immediately without fetching tracks from Tidal, without querying Gemini, and without creating any playlists.

### Rationale
- Completely avoids the Tidal API limitation where non-empty folders cannot be removed.
- Prevents accidental loss of playlists through interactive confirmation, while preserving automated cron job workflows with `--yes`.
- Adheres to Constitution Principle I (Understandability), Principle II (Automation), Principle V (Reliability), and Principle IX (CLI Ergonomics).

### Alternatives Considered
- *Attempting to delete the folder directly via API*: Fails with HTTP 400/409 whenever the folder contains playlists, directly violating the Tidal API contract.
- *Deleting the folder after emptying it and recreating it*: Unnecessarily destroys and recreates the folder, generating new folder IDs, changing bookmarks/links, and introducing timing/race conditions in Tidal's backend. Reusing the emptied folder container is cleaner, faster, and preserves the folder URL.
