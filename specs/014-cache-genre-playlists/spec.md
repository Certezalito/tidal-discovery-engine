# Feature Specification: Genre Playlist Database Caching & Optimization

**Feature Branch**: `014-cache-genre-playlists`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "looking to improve the genre playlists command as it pertains to gemini token costs/efficiency/database building and caching. this feature is neat but i find it expensive, need to cache discovered genres discovered via gemini in a database and rely on those in the future vs making new calls to gemini. obviously undiscovered track genres would need the gmeni call for metadata. also the command needs to set a min threshold of x, in which the genres are lumped into an "other" type playlist where they are obscure or have no other matching tracks in the genre. No track should be in multiple genres, only the best genre fit playlist. this command is meant to be a periodic run and not expensive todo so, a nice categorization of such in a dedicated playlist folderwithin tidal. the command will update the playlists or remove them where there are no track matches."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cost-Efficient Genre Assignment via Database Caching (Priority: P1)

As a user running the genre playlist command periodically on my Tidal library, I want all previously analyzed tracks to read their genre classification from a local persistent database cache rather than calling Gemini AI, so that repeat runs execute quickly and incur minimal AI token costs.

**Why this priority**: Directly addresses the primary user pain point regarding high Gemini API costs and token usage during periodic library scans.

**Independent Test**: Can be tested by running the genre categorization command twice on the same library. The second run must query zero Gemini API tokens for previously analyzed tracks, pulling classifications entirely from the local cache database.

**Acceptance Scenarios**:

1. **Given** a library containing tracks that have already been classified by Gemini in a previous run, **When** the genre playlist command is executed, **Then** the system retrieves track genre classifications directly from the local database cache without invoking Gemini.
2. **Given** a library containing new or previously unclassified tracks, **When** the genre playlist command is executed, **Then** the system calls Gemini AI only for those uncached tracks, stores the new genre classifications in the local database cache, and assigns the track to its primary best-fit genre.
3. **Given** a track was previously classified as "Unknown" due to a lookup failure or missing metadata, **When** the command is executed on a subsequent run, **Then** the system re-attempts Gemini classification for that "Unknown" track and updates the database cache if a valid genre is identified.

---

### User Story 2 - Obscure Genre Thresholding & Best-Fit Grouping (Priority: P2)

As a user with a diverse music library, I want genres with fewer tracks than a configurable minimum threshold (X) to be grouped into a single "Others" playlist, so that my Tidal folder contains a clean set of major genre playlists without playlist sprawl.

**Why this priority**: Prevents cluttering Tidal with dozens of single-track or obscure genre playlists while maintaining full library categorization.

**Independent Test**: Can be tested by running the command with a threshold (e.g., `--min-genre-size 5`) on a library containing sparse genres (e.g., 2 tracks in Synthwave). The tracks in those sparse genres must be grouped into the "Others" playlist, while genres meeting or exceeding 5 tracks receive their own dedicated playlist.

**Acceptance Scenarios**:

1. **Given** a track is categorized into a primary genre, **When** genre playlists are being generated/updated, **Then** the track is assigned to exactly one playlist corresponding to its single best-fit genre.
2. **Given** the user sets a minimum threshold X (via `--min-genre-size` CLI flag or default configuration), **When** the final track count for a genre is less than X, **Then** all tracks belonging to that genre are grouped together into an "Others" playlist rather than creating individual sparse playlists.
3. **Given** a genre formerly below threshold X grows to meet or exceed X on a subsequent library scan, **When** the command runs, **Then** a dedicated genre playlist is created/updated for that genre and its tracks are removed from the "Others" playlist.

---

### User Story 3 - Idempotent Playlist Folder Synchronization (Priority: P3)

As a user executing periodic library updates, I want the system to synchronize my Tidal folder by updating track lists, creating new playlists when needed, and removing empty or obsolete genre playlists, so that my Tidal account stays organized automatically.

**Why this priority**: Ensures the playlist folder reflects the exact current state of the user's library without leaving orphaned or empty playlists behind.

**Independent Test**: Can be tested by removing all tracks of a specific genre from the Tidal library and re-running the command. The system must update or remove the corresponding empty genre playlist from the Tidal playlist folder.

**Acceptance Scenarios**:

1. **Given** genre playlists exist in the target Tidal folder, **When** the command syncs the folder, **Then** it adds newly added library tracks, removes tracks no longer in the library, and ensures no duplicate tracks exist in any playlist.
2. **Given** a genre playlist in the Tidal folder no longer contains any library tracks (or falls to zero due to track deletions), **When** the command completes synchronization, **Then** the empty playlist is deleted or emptied cleanly from Tidal.
3. **Given** multiple playlists are updated or created, **When** the command finishes, **Then** playlists are updated in ascending order of track count so that Tidal's "Updated Date" sorting lists the largest playlists first.

---

### Edge Cases

- What happens if the local database file is locked or corrupt? The system must log a clear error, attempt safe recovery or recreate the database schema without crashing.
- How does the system handle Gemini API rate limits or quota errors when fetching uncached tracks? The system must save all successfully resolved track genres to the database before exiting gracefully or retrying with backoff.
- What happens if all tracks in the library fit into genres below threshold X? All tracks are grouped cleanly into the single "Others" playlist.
- What happens if a user lowers threshold X on a subsequent run? Sparse genres that now meet the lower threshold are split out of "Others" and given dedicated playlists in Tidal.

## Clarifications

### Session 2026-07-23

- Q: What local database engine should be used for track genre caching? → A: SQLite (lightweight, zero-config, embedded file).
- Q: How should tracks mapped to "Unknown" genre be handled in cache? → A: Store in cache with "Unknown" status, but re-query Gemini on future runs until resolved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store all discovered track-to-genre mappings in a local, persistent database (e.g., SQLite) associated with unique track identifiers (ISRC or Tidal track ID).
- **FR-002**: System MUST check the local database cache before making any external Gemini API calls for track metadata or genre classification.
- **FR-003**: System MUST invoke Gemini AI only for tracks not present in the local database cache or tracks previously stored with an "Unknown" or unclassified state.
- **FR-004**: System MUST ensure every track is mapped to exactly one primary best-fit genre, strictly avoiding multi-genre playlist duplication for a single track.
- **FR-005**: System MUST support a configurable minimum track threshold X (via CLI flag `--min-genre-size` with a default of 5) below which tracks in rare or obscure genres are assigned to an "Others" playlist.
- **FR-006**: System MUST create, update, or sync playlists within a user-specified Tidal folder, adding new matching tracks and removing deleted library tracks.
- **FR-007**: System MUST delete or remove obsolete genre playlists from the Tidal folder when a genre no longer has any matching library tracks.
- **FR-008**: System MUST order playlist update operations by track count ascending so that sorting by "Updated date" in Tidal displays larger playlists at the top.
- **FR-009**: System MUST provide clear CLI feedback indicating cache hits, new Gemini queries performed, token cost savings, and playlist folder sync status.

### Key Entities

- **Track Genre Cache**: Persistent record mapping a track (ID/ISRC, artist, title) to its primary genre, classification source, and timestamp.
- **Genre Assignment**: Representation of a library track's placement into a single target playlist ("Named Genre", "Others", or "Unknown").
- **Tidal Playlist Folder**: Container in the user's Tidal account holding all synchronized genre playlists.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Repeat execution of the genre playlist command on an unchanged library results in a 100% cache hit rate for track genres, executing zero Gemini API token calls.
- **SC-002**: Execution time for a 5,000-track library on subsequent cached runs is reduced by at least 80% compared to the initial un-cached run.
- **SC-003**: 100% of library tracks are assigned to exactly one playlist without duplicate track entries across different genre playlists.
- **SC-004**: All genre playlists with fewer tracks than the threshold X are consolidated into the "Others" playlist without orphan playlists remaining in Tidal.

