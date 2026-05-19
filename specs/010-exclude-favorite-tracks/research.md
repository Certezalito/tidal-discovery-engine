# Research: Exclude Existing Favorite Tracks

**Feature**: 010-exclude-favorite-tracks  
**Date**: 2026-05-08  
**Status**: Complete

## Decision 1: Favorites retrieval source and method

- Decision: Use the existing `tidal_service` retrieval path based on `session.user.favorites.tracks(offset=..., limit=...)` pagination to build the full favorites set when exclusion is enabled.
- Rationale: The repository already uses this method in `get_random_favorite_tracks`; reusing the same API surface reduces integration risk and keeps architecture consistent.
- Alternatives considered:
  - Call a different favorites endpoint directly from CLI code: rejected because it breaks service layering and duplicates integration logic.
  - Resolve favorites through search-only heuristics: rejected because it cannot guarantee full-list coverage.

## Decision 2: Track identity and dedup strategy

- Decision: Compare tracks by ISRC first; when ISRC is unavailable, compare normalized title + primary artist.
- Rationale: Existing code and diagnostics (`get_track_by_isrc`, `debug_isrc.py`) confirm ISRC is available and useful, while fallback matching preserves coverage when ISRC is missing.
- Alternatives considered:
  - ISRC-only matching: rejected because missing ISRC values would leak favorites into output.
  - Title-only fallback: rejected due to high false-positive collision risk.
  - Title + all artists + album fallback: rejected as higher complexity for limited incremental benefit.

## Decision 3: Failure and partial retrieval policy

- Decision: Fail closed when favorites retrieval fails or is partial; abort with clear error and no playlist output.
- Rationale: User explicitly opted into excluding favorites; producing an unfiltered playlist would violate user intent and create silent correctness regressions.
- Alternatives considered:
  - Proceed unfiltered with warning: rejected due to correctness and trust concerns.
  - Proceed with partial data: rejected because it creates nondeterministic exclusion quality.

## Decision 4: Pagination retry policy

- Decision: Fetch all favorites pages with up to 2 retries per failed page; if a required page still fails, abort under fail-closed policy.
- Rationale: Matches existing reliability patterns in `tidal_service` (bounded retries for transient failures) while preserving complete-data requirement.
- Alternatives considered:
  - No retries: rejected as too brittle under transient network/API instability.
  - Time-boxed or partial fetch: rejected due to incomplete exclusion guarantees.

## Decision 5: Data retention boundary

- Decision: Keep favorites exclusion data in memory only for the active run; do not persist cache files.
- Rationale: 10,000-track key sets are memory-feasible for this CLI and in-memory handling best aligns with privacy and simplicity goals.
- Alternatives considered:
  - Disk cache with TTL: rejected because it introduces stale-data and privacy concerns.
  - Disk cache of hashed identifiers: rejected because it adds complexity without clear user value for current scope.

## Decision 6: Performance and scale target interpretation

- Decision: Preserve spec target of <=5s additional runtime for typical libraries (up to ~2,000 favorites), and treat larger libraries as best-effort with same algorithmic path.
- Rationale: Keeps acceptance criteria measurable while avoiding premature optimization for outlier account sizes.
- Alternatives considered:
  - Hard memory/time ceilings in implementation contract: rejected until benchmark evidence warrants stronger constraints.
  - Removing performance target: rejected because it weakens verifiability.

## Implementation Verification Notes

- Verified during implementation that favorites retrieval uses `session.user.favorites.tracks(offset=..., limit=...)` pagination in `src/services/tidal_service.py`.
- Verified ISRC-based identity path via `get_track_by_isrc` and normalization helpers in `src/services/tidal_service.py`.
- Confirmed exclusion mode design remains in-memory only with no favorites cache writes.
