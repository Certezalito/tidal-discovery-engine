# Research: Genre Playlists

**Feature**: 012-genre-playlists  
**Date**: 2026-06-05  
**Status**: Complete

## Decision 1: Reuse existing Tidal library pagination utilities

- Decision: Build genre playlist orchestration on top of existing full-library fetch patterns in `src/services/tidal_service.py` rather than introducing a new fetch subsystem.
- Rationale: The repository already includes tested paging/retry patterns for favorites retrieval. Reusing these patterns reduces risk and aligns with the user note that groundwork is largely complete.
- Alternatives considered:
  - New custom paginator per feature: rejected due to duplicate logic and additional failure surface.
  - One-shot library fetch without paging safeguards: rejected because it is fragile for large libraries.

## Decision 2: Use Gemini as the primary genre classifier with explicit Unknown fallback

- Decision: Use Gemini as the genre source and map tracks with missing/low-confidence genre outcomes into a dedicated `Unknown` playlist.
- Rationale: The feature clarifications selected Gemini for deeper catalog coverage, but classification cannot be guaranteed for every track. A deterministic fallback prevents silent drops.
- Alternatives considered:
  - Skip unknown tracks: rejected because it breaks library completeness and user trust.
  - Force single fallback genre for all uncertain tracks: rejected because `Unknown` is clearer and audit-friendly.

## Decision 3: Enforce single-genre placement for each track

- Decision: A track is assigned to exactly one genre playlist (the best match returned by Gemini).
- Rationale: The spec was explicitly clarified to state "Primary genre only (best match)".
- Alternatives considered:
  - Multi-genre assignment: rejected because the spec clarification overrode this behavior.

## Decision 3b: Cache classifications locally

- Decision: Store successful Gemini classifications in a local JSON file (`.tde_genre_cache.json`). "Unknown" results will NOT be cached.
- Rationale: Full-library classification is expensive and slow. Caching speeds up reruns (SC-003). Skipping "Unknown" caches ensures previously unclassified tracks get another chance on subsequent runs, satisfying FR-011.
- Alternatives considered:
  - SQLite database: rejected for now as JSON is simpler and suffices for thousands of text mappings.
  - No caching: rejected because hitting Gemini for 5,000 tracks every run violates the <20% rerun time constraint.

## Decision 4: Minimize playlist sprawl with an "Others" threshold

- Decision: Group genres containing fewer than a configured threshold (default: 2) of tracks into a single "Others" playlist.
- Rationale: Highly specific Gemini classifications can result in dozens of single-track playlists. A threshold reduces clutter (FR-012) and improves folder readability. 
- Alternatives considered:
  - No threshold: rejected because it leads to unacceptable playlist sprawl.
  - Hardcoded threshold: rejected because users have different definitions of a "niche" genre based on their library size.

## Decision 5: Sync playlists in ascending size order

- Decision: After grouping tracks, perform Tidal playlist creation/sync operations in ascending order of their final track count.
- Rationale: Tidal updates the "Updated date" field when tracks are added/removed. By touching the largest playlists last, users sorting the folder by "Updated date" descending will see their most populated genre playlists at the top (FR-013).
- Alternatives considered:
  - Custom API sorting: rejected because Tidal's API does not allow manual arbitrary sorting inside a folder.
  - Alphabetical processing: rejected because it doesn't prioritize the user's primary genres.

## Decision 6: Implement sync semantics (add missing, remove stale)

- Decision: On reruns, sync each genre playlist to current library-derived membership: add new matching tracks and remove tracks no longer in the source set.
- Rationale: Clarified requirement for deterministic upkeep and avoids stale playlists over time.
- Alternatives considered:
  - Append-only updates: rejected because stale tracks persist forever.
  - Full delete/recreate playlists each run: rejected due to churn and unnecessary API overhead.

## Decision 7: Treat orchestration logic as the implementation focus

- Decision: Keep implementation concentrated in workflow orchestration (classification batching, grouping, folder/playlist reconciliation, sync application, and progress reporting), using existing helper capabilities for session, folder, and playlist operations.
- Rationale: Existing code already handles core building blocks (auth/session, folder creation, playlist creation, Gemini integration), matching user guidance that only code logic remains.
- Alternatives considered:
  - Refactor all service boundaries first: rejected as out-of-scope for this feature.
  - Add persistent cache/database before logic completion: rejected because current requirements do not demand persistence.

## Decision 8: Validate with targeted CLI/service tests

- Decision: Add focused tests for classification-to-playlist mapping, `Unknown` handling, and sync behavior on rerun.
- Rationale: Constitution requires behavior-changing paths to be verifiable; this feature changes orchestration behavior across multiple services.
- Alternatives considered:
  - Manual-only validation: rejected due to regression risk.
  - Broad end-to-end tests only: rejected because they are slower and less diagnostic than targeted unit/integration tests.
