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

## Decision 3: Support multi-genre placement for a single track

- Decision: A track can belong to multiple genre playlists when Gemini returns multiple genres.
- Rationale: This was explicitly clarified and improves discoverability for cross-genre tracks.
- Alternatives considered:
  - Primary-genre-only assignment: rejected because it loses relevant genre associations.
  - Combined compound-genre playlist naming: rejected due to playlist explosion and poor usability.

## Decision 4: Implement sync semantics (add missing, remove stale)

- Decision: On reruns, sync each genre playlist to current library-derived membership: add new matching tracks and remove tracks no longer in the source set.
- Rationale: Clarified requirement for deterministic upkeep and avoids stale playlists over time.
- Alternatives considered:
  - Append-only updates: rejected because stale tracks persist forever.
  - Full delete/recreate playlists each run: rejected due to churn and unnecessary API overhead.

## Decision 5: Treat orchestration logic as the implementation focus

- Decision: Keep implementation concentrated in workflow orchestration (classification batching, grouping, folder/playlist reconciliation, sync application, and progress reporting), using existing helper capabilities for session, folder, and playlist operations.
- Rationale: Existing code already handles core building blocks (auth/session, folder creation, playlist creation, Gemini integration), matching user guidance that only code logic remains.
- Alternatives considered:
  - Refactor all service boundaries first: rejected as out-of-scope for this feature.
  - Add persistent cache/database before logic completion: rejected because current requirements do not demand persistence.

## Decision 6: Validate with targeted CLI/service tests

- Decision: Add focused tests for classification-to-playlist mapping, `Unknown` handling, and sync behavior on rerun.
- Rationale: Constitution requires behavior-changing paths to be verifiable; this feature changes orchestration behavior across multiple services.
- Alternatives considered:
  - Manual-only validation: rejected due to regression risk.
  - Broad end-to-end tests only: rejected because they are slower and less diagnostic than targeted unit/integration tests.
