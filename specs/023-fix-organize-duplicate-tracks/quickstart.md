# Quickstart & Validation Guide: Fix Duplicate Tracks in Organized Playlists

**Feature**: `023-fix-organize-duplicate-tracks`
**Date**: 2026-11-23

## Prerequisites

- Python 3.12+ managed via `uv`
- Repository dependencies installed (`uv sync`)
- For optional live verification: valid `tidal_session.json` and `.env` (no Gemini tokens needed if tracks are already cached in `data/genre_cache.db`)

---

## 1. Automated Validation (Unit & Service Tests)

Run the full test suite to verify all deduplication, cleanup, thresholding, and idempotency scenarios without touching live Tidal playlists:

```bash
uv run pytest
```

Targeted test suites covering this feature:

```bash
uv run pytest tests/test_genre_playlist_service.py tests/test_genre_playlist_service_clean.py tests/test_sync_playlist_tracks.py tests/test_tidal_service.py
```

### Scenarios Verified by Automated Tests

1. **Exact duplicate track cleanup (`SC-002`, `FR-006`)**: Existing playlist contains `[T1 (uuid-1), T1 (uuid-2), T2 (uuid-3)]`; sync removes ONLY `uuid-2`, adds 0 tracks, and leaves `[T1, T2]`.
2. **Triple+ duplicate cleanup**: Existing playlist contains 3 copies of `T1`; sync removes 2 surplus `item_uuid`s and retains 1 copy.
3. **Same-recording / different-release deduplication (`FR-002`, `FR-003`)**: Library contains Single (`id=111, isrc=ISRC1`) and Album (`id=222, isrc=ISRC1`):
   - Existing playlist already containing `111` keeps `111` with `+0 -0` changes (no churn even if `222` sorts first).
   - Existing playlist containing BOTH `111` and `222` keeps the first and removes the second by `item_uuid`.
   - New playlist picks `canonical_track_id` deterministically regardless of library pagination order.
4. **Distinct versions preserved (`FR-002`)**: Studio track (`isrc=ISRC1`) and Remix (`isrc=ISRC2`) both remain in the playlist.
5. **Missing ISRC fallback (`FR-002`)**: Tracks without ISRC deduplicate by exact catalog `id` and are not dropped.
6. **Obsolete duplicated track removal (`FR-007`)**: Playlist contains 2 copies of removed track `T9`; both `item_uuid`s are removed.
7. **Post-dedup minimum genre size thresholding (`FR-004`)**: Genre with 4 unique recordings + 1 duplicate release (5 raw tracks, 4 unique) under `--min-genre-size 5` does NOT get a standalone playlist (primary routes to `"Others"`, sub-genre suppressed).
8. **Consecutive idempotency (`SC-003`, `FR-009`)**: Second run on unchanged library produces `tracks_added == 0`, `tracks_removed == 0`, `playlists_updated == 0`.
9. **Multi-genre distribution preserved (`SC-004`, `FR-008`)**: Track belonging to 2 qualifying genres appears once in each playlist.

---

## 2. Live Verification (Optional, Against Your Tidal Library)

1. Run `organize` once to clean up any existing duplicate tracks:
   ```bash
   uv run tde organize
   ```
   - Expected: Affected playlists log removals of surplus duplicate tracks (`-N` tracks, noting removed duplicates).
2. Immediately run `organize` a second time without modifying your Tidal favorites:
   ```bash
   uv run tde organize
   ```
   - Expected:
     - `Playlists Updated: 0`
     - `Tracks Added: 0`
     - `Tracks Removed: 0`
     - Zero playlists report `+N -N` churn.
3. Spot-check a previously affected playlist in Tidal to confirm zero repeating tracks.

---

## References

- Specification: [spec.md](spec.md)
- Data Model: [data-model.md](data-model.md)
- Service & CLI Contracts: [contracts/sync-planner-contract.md](contracts/sync-planner-contract.md)
