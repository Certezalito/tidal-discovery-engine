# Feature Specification: Exclude Favorite Tracks

**Feature Branch**: `010-exclude-favorite-tracks`  
**Created**: 2026-05-07  
**Status**: Draft  
**Input**: User description: "add a new optional parameter to exclude existing favorite tracks"

## Clarifications

### Session 2026-05-07

- Q: What should happen when favorites retrieval fails while exclusion is enabled? -> A: Abort with a clear error message and no playlist output.
- Q: What should happen when only a partial favorites list is retrieved? -> A: Treat partial retrieval as failure; abort with clear error and no playlist output.
- Q: What fallback identity rule should be used when ISRC is missing? -> A: Match by normalized title plus primary artist.
- Q: How should large/paginated favorites retrieval handle transient page failures? -> A: Fetch all pages with up to 2 retries per failed page, then fail closed.
- Q: How should favorites data be stored during exclusion filtering? -> A: In-memory only for the current run; no persistence to disk.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover Only New Music (Priority: P1)

A user runs the discovery engine to generate playlist recommendations. They want to avoid being shown tracks they already have saved as favorites in their Tidal library, so they enable the exclusion option to receive a cleaner set of genuinely new suggestions.

**Why this priority**: This is the primary value of the feature — users who already track favorites want discovery results to feel fresh and non-redundant.

**Independent Test**: Can be fully tested by running the discovery engine with the exclusion flag enabled against a Tidal account that has known favorite tracks, then verifying that none of the returned playlist tracks appear in the user's favorites list.

**Acceptance Scenarios**:

1. **Given** a user has saved favorite tracks in their Tidal account, **When** they run the discovery engine with the exclude-favorites option enabled, **Then** none of the recommended tracks in the output playlist are present in the user's Tidal favorites list.
2. **Given** a user enables the exclude-favorites option, **When** the engine generates more candidate tracks than needed due to exclusions, **Then** the final playlist still meets the requested track count (filling with additional non-favorite candidates).
3. **Given** a user enables the exclude-favorites option and all recommended candidates are already favorites, **Then** the engine informs the user that no new tracks could be found and produces an empty or partial playlist with an explanatory message.

---

### User Story 2 - Opt-In Behavior with No Change to Default (Priority: P2)

A user who does not use the exclusion option continues to receive exactly the same behavior as before — the parameter is strictly optional and off by default.

**Why this priority**: Backwards compatibility ensures existing workflows are not disrupted.

**Independent Test**: Can be fully tested by running the discovery engine without the exclusion flag and confirming the output is identical to the pre-feature baseline behavior.

**Acceptance Scenarios**:

1. **Given** a user runs the discovery engine without specifying the exclude-favorites option, **When** the results are returned, **Then** the behavior and output are identical to the current baseline (no favorites lookup, no filtering).
2. **Given** a user explicitly sets the exclusion option to its default off value, **When** the engine runs, **Then** no favorites lookup is performed.

---

### User Story 3 - Partial Favorites Fetch Failure (Priority: P3)

A user enables the exclusion option, but the system encounters an error fetching their favorites (e.g., Tidal API timeout or permission issue). The engine handles the failure gracefully rather than crashing.

**Why this priority**: Resilience is important for a good user experience but is secondary to the core feature functioning correctly.

**Independent Test**: Can be tested by simulating a favorites-fetch failure and confirming the engine exits with a clear error message and no playlist output.

**Acceptance Scenarios**:

1. **Given** a user enables the exclusion option and the favorites list cannot be retrieved, **When** the engine encounters the error, **Then** it aborts, emits a clear error message describing the failure, and does not output a playlist.
2. **Given** a favorites fetch returns a partial result, **When** the engine detects incomplete favorites data, **Then** it treats the result as a failure, aborts, and emits a clear error message indicating that exclusion requires a complete favorites list.

---

### Edge Cases

- What happens when the user's favorites list is empty? The option is accepted silently and no filtering occurs; no warning is shown.
- What happens when the entire recommended set overlaps with favorites? The output playlist is empty or truncated, and the user receives an informative message.
- What happens when the favorites list is very large (thousands of tracks)? The system paginates through the full favorites list and retries transient page failures up to 2 times per page before failing closed.
- How does the system handle duplicate ISRCs across favorites and recommended tracks (same track, different Tidal IDs)? Tracks are compared by a stable identifier (ISRC first, then normalized title + primary artist) to catch duplicates regardless of Tidal internal ID.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an optional command-line parameter (e.g., `--exclude-favorites`) that, when enabled, causes the engine to filter out tracks already saved in the user's Tidal favorites from the recommendation output.
- **FR-002**: The parameter MUST be off by default; omitting it MUST result in behavior identical to the current behavior before this feature.
- **FR-003**: When the parameter is enabled, the system MUST fetch the user's current Tidal favorites track list before generating or finalizing the recommendation playlist.
- **FR-004**: The system MUST compare recommended tracks against favorites using a stable track identifier (ISRC where available, falling back to normalized title + primary artist) to avoid false positives from different Tidal internal IDs.
- **FR-005**: When filtering removes candidates and the playlist falls below the requested track count, the system MUST attempt to supplement the playlist with additional non-favorite candidates to meet the count, if additional candidates are available.
- **FR-006**: When no additional candidates are available and the playlist cannot be fully populated, the system MUST inform the user with a clear message indicating the shortfall and the reason (all remaining candidates were favorites).
- **FR-007**: When the favorites fetch fails while exclusion is enabled, the system MUST abort execution, display a descriptive error message, and produce no playlist output.
- **FR-008**: The system MUST NOT perform any favorites lookup when the parameter is not enabled, to avoid unnecessary API calls.
- **FR-009**: When favorites retrieval is incomplete (partial pages, truncated responses, or interrupted pagination), the system MUST treat it as a fetch failure and apply FR-007 behavior.
- **FR-010**: When exclusion is enabled, favorites retrieval MUST paginate through the complete favorites list and retry failed page requests up to 2 times per page; if any required page still fails, the system MUST apply FR-007 behavior.
- **FR-011**: Favorites data used for exclusion filtering MUST be held in memory only for the active run and MUST NOT be persisted to disk.

### Documentation & Understandability Requirements *(mandatory)*

- **DR-001**: The README and quickstart MUST be updated to document the new optional parameter, its purpose, and a concrete usage example showing it in action.
- **DR-002**: The CLI help text for the new parameter MUST include a plain-language description explaining what "exclude existing favorites" means, so users understand the behavior without needing external documentation.
- **DR-003**: Error and warning messages produced when favorites fetch fails MUST include guidance on possible causes (permissions, network) and corrective steps.
- **DR-004**: The term used for the parameter (`--exclude-favorites` or equivalent) MUST be consistent across the spec, quickstart, README, and CLI help output.

### Validation Requirements *(mandatory)*

- **VR-001**: An automated test MUST verify that, when the exclusion flag is enabled and mock favorites are provided, the output playlist contains no tracks present in the mock favorites.
- **VR-002**: An automated test MUST verify that, when the exclusion flag is not provided, the favorites lookup is never invoked (no calls to the favorites fetch service).
- **VR-003**: An automated test MUST verify the fallback/supplement behavior when filtering reduces the playlist below the requested count.
- **VR-004**: An automated test MUST verify that a favorites-fetch failure (including partial retrieval) produces the expected error message and no playlist output rather than an unhandled exception.
- **VR-005**: An automated test MUST verify that favorites pagination retries failed page requests up to 2 times and fails closed if a required page remains unavailable.
- **VR-006**: An automated test MUST verify that enabling exclusion does not create or write any local favorites cache files.

### Evidence & Unknowns Requirements *(mandatory)*

- **ER-001**: The exact Tidal API endpoint or SDK method for retrieving a user's favorite tracks MUST be confirmed against the existing `tidal_service.py` implementation or the tidalapi library documentation before implementation begins.
- **ER-002**: The ISRC-based deduplication strategy should be verified against existing ISRC handling in the codebase (see `debug_isrc.py`, `inspect_tidal_isrc.py`) to confirm ISRCs are reliably available for favorites.
- **ER-003**: It is assumed that the tidalapi library exposes a method to retrieve the authenticated user's full favorites track list; this must be confirmed.

### Key Entities *(include if feature involves data)*

- **FavoriteTrack**: A track saved by the user to their Tidal favorites library. Identified by ISRC (preferred) or normalized title + primary artist pair. Fetched once per session when exclusion is enabled.
- **RecommendedTrack**: A candidate track returned by the discovery/recommendation pipeline before playlist finalization. Compared against the favorites set to determine inclusion.
- **ExclusionFilter**: The runtime component that accepts a set of FavoriteTracks and a list of RecommendedTracks and returns only those recommended tracks not present in favorites.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When the exclusion flag is enabled, 100% of tracks in the final output playlist are absent from the user's Tidal favorites list (zero favorites leaked into output).
- **SC-002**: When the exclusion flag is not provided, the output is byte-for-byte identical to the pre-feature baseline for the same inputs (no regression).
- **SC-003**: Fetching and filtering favorites for a typical library (up to 2,000 favorites), including pagination and retry logic, adds no more than 5 seconds to total execution time.
- **SC-004**: All new code paths introduced by this feature are covered by automated tests that pass in CI before merge.
- **SC-005**: Users encountering the "all candidates are favorites" edge case receive a clear, actionable message rather than a confusing empty output with no explanation.

## Assumptions

- The user is already authenticated with Tidal; the feature relies on the existing authentication mechanism and does not introduce new auth flows.
- The tidalapi library provides a method to retrieve the authenticated user's favorite tracks list; implementation details will be confirmed during the planning phase.
- ISRC availability for favorites may not be 100%; a normalized title + artist fallback is acceptable for deduplication when ISRC is absent.
- The existing playlist generation pipeline produces a superset of candidates that can be drawn from when filtering removes tracks; if not, the shortfall message behavior applies.
- Mobile/web UI changes are out of scope; this is a CLI-only parameter.
- Pagination of large favorites lists is handled transparently — the full favorites list is loaded before filtering begins.
- Favorites data for exclusion filtering is ephemeral and in-memory only; no favorites data is persisted between runs.
