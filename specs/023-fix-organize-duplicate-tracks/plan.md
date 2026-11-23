# Implementation Plan: Fix Duplicate Tracks in Organized Playlists

**Branch**: `023-fix-organize-duplicate-tracks` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/023-fix-organize-duplicate-tracks/spec.md`

## Summary

The `tde organize` command currently allows duplicate tracks to persist in organized Tidal genre playlists and causes repeated `+N -N` track churn across consecutive runs on an unchanged library. Root cause analysis identified four defects: (1) `calculate_sync_delta` uses set membership and ignores duplicate occurrences already present in a playlist, (2) library deduplication keeps whichever catalog release appeared first in Tidal favorites pagination and compares existing playlist items by catalog ID only rather than recording identity (ISRC), (3) `get_playlist_tracks` fallback parsing omits `isrc` and IDs are not consistently string-normalized, and (4) `add_tracks_to_playlist` does not deduplicate outgoing track IDs.

We will introduce a recording-aware deduplication key (`get_playlist_dedup_key`: ISRC with exact catalog ID fallback), group library tracks into deterministic `TrackDedupGroup`s prior to genre thresholding (`FR-004`), and add `calculate_playlist_sync_plan` to reconcile existing playlists using `item_uuid` for surgical duplicate removal (`FR-006`, `FR-007`) while preserving any matching release already in the playlist (`FR-003`) for guaranteed zero-churn idempotency (`FR-009`).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: `click`, `tidalapi` (0.8.10; Tidal v2 playlist item endpoints via `session.request`), `pydantic`, `sqlite3` (stdlib)
**Storage**: Local SQLite (`data/genre_cache.db`) — no schema changes required
**Testing**: `pytest` (`uv run pytest`)
**Target Platform**: Linux CLI (interactive & unattended cron execution)
**Project Type**: CLI application (`tde` / `tidal-discovery-engine`)
**Performance Goals**: Zero extra Tidal API calls per playlist during normal sync (reuses `item_uuid` already returned by `GET /v2/playlists/{id}/items`); zero API writes on unchanged consecutive runs
**Constraints**: Must remain idempotent for unattended weekly cron execution; must preserve backward compatibility with `data/genre_cache.db` cache keys and existing `calculate_sync_delta` callers; no undocumented Tidal v2 query parameters
**Scale/Scope**: ~7,000+ favorite tracks, ~450+ genre playlists, playlists spanning multiple 100-item API pages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Pre-Design Status | Post-Design Status | Notes |
|------------------|-------------------|--------------------|-------|
| **I. User-Centricity & Understandability** | PASS | PASS | Clearer sync logs noting duplicate removals; README behavior notes updated for deduplication semantics. No unverified API params guessed. |
| **II. Automation** | PASS | PASS | Automatic duplicate cleanup during standard scheduled `tde organize` runs; zero manual intervention or folder wipe required. |
| **V. Reliability & Verifiability** | PASS | PASS | Targeted automated unit/service tests covering exact duplicates, ISRC duplicates, multi-page playlists, post-dedup thresholding, and 2-run idempotency. |
| **VII. Local Caching & Performance Efficiency** | PASS | PASS | `GenreCacheService` SQLite keys (`get_track_identity_key`) remain unchanged; zero cache invalidation or extra AI calls. |
| **VIII. Grounded Metadata & Zero ISRC Hallucination** | PASS | PASS | All ISRCs originate strictly from authoritative Tidal library/playlist track objects. No Gemini changes. |
| **X. Critical Dependency Currency & Capability Discovery** | PASS | PASS | Audited `tidalapi` 0.8.10 vs upstream 0.8.11/0.9.0 in `research.md`; confirmed Tidal v2 `item_uuid` removal is superior to `tidalapi` v1 `remove_by_indices` for folder-owned playlists. |
| **XI. Human Readability & Inline Intent Documentation** | PASS | PASS | New deduplication and sync-planning logic will include clear docstrings and inline rationale comments. |
| **Batch & Synchronization Idempotency Gate** | PASS | PASS | Core goal of this fix: eliminates duplicate tracks and `+N -N` release-swapping churn across repeated runs. |

No constitutional violations exist.

## Project Structure

### Documentation (this feature)

```text
specs/023-fix-organize-duplicate-tracks/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — root cause analysis & tidalapi audit
├── data-model.md        # Phase 1 output — TrackDedupGroup, PlaylistSyncPlan
├── quickstart.md        # Phase 1 output — runnable validation scenarios
├── contracts/
│   └── sync-planner-contract.md  # Phase 1 output — service & CLI contracts
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
src/
├── cli/
│   └── main.py
├── lib/
│   ├── auth.py
│   ├── db.py
│   └── logging.py
└── services/
    ├── genre_organizer_service.py   # TrackDedupGroup, calculate_playlist_sync_plan, updated calculate_sync_delta & run_genre_organizer_sync
    ├── genre_playlist_service.py    # Legacy compatibility shim (unchanged exports)
    └── tidal_service.py             # get_playlist_dedup_key, fallback isrc preservation in get_playlist_tracks, defensive dedup in add_tracks_to_playlist

tests/
├── test_genre_playlist_service.py       # New/expanded organizer deduplication, cleanup, thresholding & idempotency tests
├── test_genre_playlist_service_clean.py # Existing regression tests
├── test_sync_playlist_tracks.py         # Playlist sync & UUID removal tests
└── test_tidal_service.py                # get_playlist_dedup_key, get_playlist_tracks fallback isrc, add_tracks_to_playlist dedup tests

README.md                                # Document duplicate-track deduplication & automatic cleanup behavior for `organize`
```

**Structure Decision**: Single-project Python CLI layout under `src/` and `tests/`, modifying only `src/services/tidal_service.py`, `src/services/genre_organizer_service.py`, their corresponding test files under `tests/`, and `README.md`.

## Complexity Tracking

No Constitution Check violations; no complexity justifications required.
