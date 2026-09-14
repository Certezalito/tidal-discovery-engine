# Feature Specification: Multi-Genre Track Organization & Folder Wipe

**Feature Branch**: `019-multi-genre-organizer`

**Created**: 2026-09-10

**Last Revised**: 2026-09-14

**Status**: Draft

**Input**: User description: "i want to revise this spec, i want a wipe the folder type feature that the organize command uses" (prior revisions: minimum genre size 5, multi-genre classification and SQLite caching).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Genre Classification and Persistent Caching (Priority: P1)

As a music listener organizing my library, I want the system to categorize tracks into their primary genre and specific sub-genres (excluding generic broad umbrella genres like "Rock" or "Pop") and store this information in the local database cache, so that my music collection has rich and granular genre metadata without requiring repetitive AI calls.

**Why this priority**: Sourcing and persisting both primary and sub-genres is the foundation for multi-playlist organization and prevents repeated token costs on subsequent runs.

**Independent Test**: Can be tested by classifying a test set of tracks (e.g., "Foals - Tron") and verifying that the database cache records both the primary genre (e.g., "Math Rock") and specific sub-genres (e.g., "Dance-Punk", "Post-Punk Revival"), while excluding broad umbrella tags.

**Acceptance Scenarios**:

1. **Given** a new or unclassified track in the library, **When** the organize command runs, **Then** the AI service is prompted to return exactly one primary genre and up to 3 specific sub-genres, excluding broad umbrella genres.
2. **Given** classification results are returned, **When** the results are saved, **Then** the database cache persists the primary genre and all sub-genres alongside the track identity.
3. **Given** a track has already been classified with primary and sub-genres in the local cache, **When** the organize command is executed again, **Then** the full genre profile is loaded directly from the database without invoking the AI service.

---

### User Story 2 - Multi-Playlist Distribution for Qualifying Genres (Priority: P1)

As a user with an organized Tidal playlist collection, I want songs to be added to their primary genre playlist as well as each of their qualifying sub-genre playlists, so that tracks appear in both core and specialized rotations whenever a genre meets the minimum threshold.

**Why this priority**: Solves the core user frustration where songs assigned only to niche micro-genres are isolated and rarely listened to. Placing them across their primary and qualifying sub-genre playlists ensures balanced discovery.

**Independent Test**: Can be tested by running the organize command with a track assigned to 1 primary genre and 2 sub-genres where both sub-genres meet the minimum genre size threshold, and verifying that all 3 playlists contain the track.

**Acceptance Scenarios**:

1. **Given** a track has 1 primary genre and qualifying sub-genres (each with >= 5 tracks across the library), **When** genre playlists are generated and synchronized, **Then** the track is added to the playlist corresponding to the primary genre AND to each qualifying sub-genre playlist.
2. **Given** a track has identical or overlapping primary and sub-genre labels (e.g., "Math Rock" in both), **When** playlists are generated, **Then** duplicate entries are consolidated so the track is added to that playlist exactly once.
3. **Given** a track has a primary genre but all its sub-genres have fewer than the minimum genre size in the library, **When** playlists are generated, **Then** the track is added only to its primary genre playlist (or "Others" if the primary genre is also below threshold).

---

### User Story 3 - Thresholding and Minimum Genre Size Enforcement (Priority: P1)

As a user who wants an orderly Tidal playlist folder without clutter, I want a default minimum genre size of 5 tracks and strict suppression of smaller genre playlists, so that sparse genres and 1-track sub-genres do not create excessive, cluttered playlists.

**Why this priority**: Prevents playlist sprawl. In a typical library, AI classification generates dozens of micro sub-genres containing only 1 or 2 tracks. Creating standalone playlists for these creates clutter. Enforcing a strict minimum threshold of 5 tracks ensures all created genre playlists are substantial.

**Independent Test**: Can be tested by running the organize command on a library containing a primary genre with 6 tracks, a sub-genre with 5 tracks, a primary genre with 2 tracks, and a sub-genre with 1 track. Verify that standalone playlists are created ONLY for the genres with >= 5 tracks, the primary genre with 2 tracks is routed to "Others", and NO standalone playlist is created for the 1-track sub-genre.

**Acceptance Scenarios**:

1. **Given** a primary genre or sub-genre has 5 or more tracks (or >= configured `--min-genre-size`), **When** playlists are synchronized, **Then** a dedicated standalone playlist is created/updated for that genre.
2. **Given** a primary genre has fewer than 5 tracks (or < configured `--min-genre-size`), **When** playlists are synchronized, **Then** its tracks are consolidated into the "Others" playlist and no standalone playlist is created for that primary genre.
3. **Given** a sub-genre has fewer than 5 tracks (or < configured `--min-genre-size`), **When** playlists are synchronized, **Then** NO standalone playlist is created for that sub-genre, and its tracks are not added to any sub-genre playlist.
4. **Given** an existing genre playlist in the target folder no longer meets the minimum threshold or has zero qualifying tracks, **When** synchronization completes, **Then** the obsolete playlist is removed from the Tidal folder.

---

### User Story 4 - Clean-Slate Target Folder Wiping (Priority: P2)

As a user reorganizing my music library or testing different genre configurations, I want the ability to wipe/clean all existing playlists from the target Tidal folder when running the organize command, so that I can eliminate stale, duplicate, or orphaned playlists and start with a clean, freshly synchronized folder.

**Why this priority**: While incremental sync manages updates, users frequently experiment with thresholds, re-tagging, or manual reorganization. Wiping the folder provides a deterministic, clean reset mechanism on demand without requiring tedious manual playlist deletion in the Tidal UI.

**Independent Test**: Can be tested by placing multiple pre-existing playlists into a test folder, running the organize command with the wipe option enabled, and verifying that all pre-existing playlists are deleted from the folder before new genre playlists are created and synchronized.

**Acceptance Scenarios**:

1. **Given** a target Tidal folder containing existing playlists, **When** the organize command is executed with `--wipe-folder`, **Then** all existing playlists within that specific folder are deleted prior to creating or updating genre playlists.
2. **Given** a target Tidal folder that is empty or does not yet exist, **When** the organize command is executed with the wipe option enabled, **Then** the folder is resolved/created and synchronization proceeds normally without error.
3. **Given** the organize command is executed WITHOUT the wipe option, **When** synchronization runs, **Then** existing playlists are preserved and updated incrementally, and only obsolete playlists are deleted.
4. **Given** pre-existing playlists exist in other folders or at the root library level, **When** the wipe option is executed on the target folder, **Then** only playlists residing inside the specified target folder are affected; playlists outside the folder remain untouched.
5. **Given** a wipe operation is invoked in an interactive terminal without `--yes` (or `-y`), **When** the command initiates, **Then** the user is prompted to confirm the deletion displaying the folder name and count of playlists to be deleted, aborting without changes if declined.
6. **Given** the user passes `--yes` (or `-y`) alongside `--wipe-folder`, **When** the command runs, **Then** the interactive confirmation prompt is bypassed and deletion proceeds immediately.
7. **Given** the user runs `organize --wipe-only` (or `--wipe-folder --wipe-only`), **When** execution completes, **Then** all playlists in the target folder are wiped and the command exits without querying Gemini or generating new playlists.
8. **Given** a folder wipe is performed, **When** the command completes, **Then** the summary output reports the count of playlists wiped as part of the execution summary.

---

### Edge Cases

- What happens if the target folder contains playlists not created by the organize tool (e.g. manually created by the user)? When wipe is enabled, all playlists inside the designated folder are removed, as the folder is designated specifically for the organize tool.
- What happens if the Tidal API fails while deleting a playlist during a wipe? The system logs the failure, attempts to continue wiping remaining playlists, and reports errors without crashing.
- What happens if the AI service returns broad genres (e.g., "Rock", "Pop") despite prompt instructions? The system filters out a predefined blacklist of ultra-broad genres or prompts specifically against high-level taxonomy terms.
- How are existing database records (from previous single-genre runs) handled? Existing single-genre records are retained and used as primary-genre-only during regular runs to avoid unwanted API costs; running the command with the `--refresh-genres` flag triggers Gemini re-classification to backfill sub-genres for existing tracks.
- What happens if a track has no recognizable genre at all? It is assigned to the "Unknown" category, placed in the "Unknown" playlist, and flagged for re-evaluation on future runs.
- What happens if a sub-genre name contains punctuation or differing case (e.g., "Dance-Punk" vs "Dance Punk")? The system normalizes names so they map to the same canonical playlist name.
- What happens if no primary genres are below the threshold? The "Others" playlist is omitted, and only qualifying genre playlists are created.

---

## Clarifications

### Session 2026-09-10
- Q: How should existing database cache records (which currently only store a single primary genre) be upgraded to include sub-genres? → A: Option A: Explicit CLI flag (`--refresh-genres`). Existing cached tracks remain primary-genre only until the user runs `organize --refresh-genres`, giving explicit control over AI token costs.

### Session 2026-09-13 (Specification Revision)
- Q: What is the default minimum genre size and how should sub-genres with fewer tracks than the threshold be handled?
  - A: The minimum genre size default is updated from 10 to **5** (`--min-genre-size 5`).
  - Smaller genre playlists will **NOT** be made. Any genre or sub-genre with fewer than `--min-genre-size` tracks (default: 5) will not receive a standalone playlist.
  - Primary genres below threshold are grouped into "Others". Sub-genres below threshold are suppressed entirely from standalone playlist creation.

### Session 2026-09-14 (Specification Revision - Folder Wipe)
- Q: Should wiping the folder prompt for interactive confirmation when running in a terminal unless a `--yes`/`-y` flag is provided?
  - A: Yes (Option A). The system prompts for interactive confirmation in terminal sessions (displaying the folder name and the number of playlists to be deleted) unless `--yes` / `-y` is provided. Non-interactive executions bypass the prompt when `--yes` / `-y` is passed.
- Q: Should the wipe feature support a wipe-only mode that leaves the folder completely empty without generating playlists?
  - A: Yes (Option A). The system supports a `--wipe-only` flag (or `organize --wipe-only`), which empties the folder and exits without querying AI or generating new playlists.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST prompt the AI classification service to return one primary genre and up to 3 specific sub-genres per track, explicitly forbidding broad umbrella genres (such as "Music", "Rock", "Pop", "Alternative").
- **FR-002**: The system MUST persist both the primary genre and the list of sub-genres for each track in the local SQLite database cache.
- **FR-003**: The database schema MUST support storing and querying multiple genre tags per track while remaining compatible with existing cached data.
- **FR-004**: The default value of `--min-genre-size` MUST be 5 tracks.
- **FR-005**: The system MUST NOT create a standalone playlist for any primary genre or sub-genre that contains fewer tracks than the configured `--min-genre-size` (default: 5).
- **FR-006**: The system MUST assign tracks whose primary genre has fewer than `--min-genre-size` tracks to the consolidated "Others" playlist.
- **FR-007**: The system MUST assign tracks to each identified sub-genre playlist ONLY when that sub-genre has at least `--min-genre-size` tracks across the library. Sub-genres with fewer tracks MUST be suppressed from standalone playlist creation.
- **FR-008**: The system MUST deduplicate genres per track to prevent duplicate track additions to the same playlist.
- **FR-009**: The system MUST apply standard name normalization (casing, spacing, punctuation) to ensure matching sub-genres map to a single canonical playlist name.
- **FR-010**: The system MUST synchronize playlist contents idempotently by adding missing tracks and removing tracks that are no longer part of that genre.
- **FR-011**: The system MUST sort playlist synchronization in ascending order of track count to preserve the "Updated date" sorting behavior in Tidal.
- **FR-012**: The system MUST remove obsolete or previously created genre playlists from the target Tidal folder if their track count falls below `--min-genre-size` or they no longer have qualifying tracks.
- **FR-013**: The system MUST provide progress logging and a run summary showing the total primary genres, sub-genres, and playlists created/synced/deleted/wiped, along with the direct URL link to the destination Tidal folder.
- **FR-014**: The system MUST support an explicit CLI flag (`--refresh-genres`) that forces the re-classification of existing cached tracks to backfill sub-genres from the AI service.
- **FR-015**: The system MUST support an explicit CLI option (`--wipe-folder` / `--wipe`) on the `organize` command (and `genre-organizer` alias) that deletes all existing playlists within the target folder before new playlists are created.
- **FR-016**: The system MUST support a `--wipe-only` flag on the `organize` command (and `genre-organizer` alias) that deletes all existing playlists within the target folder and terminates without creating or synchronizing any playlists.
- **FR-017**: When a wipe operation is requested in an interactive terminal environment, the system MUST prompt the user for confirmation (displaying the folder name and the count of playlists to be deleted) before proceeding, unless a `--yes` / `-y` flag is provided.
- **FR-018**: When running in a non-interactive environment (or when `--yes` / `-y` is passed), the system MUST proceed with wiping without prompting.
- **FR-019**: The system MUST restrict folder wiping strictly to playlists inside the user-specified destination folder (`--folder`), preserving all playlists outside the target folder.
- **FR-020**: The system MUST accurately record and report the number of playlists wiped in both the log and the completion summary table.

### Key Entities

- **Track Genre Profile**: Contains the track's persistent identity (`track_id`), artist name, song title, `primary_genre`, list of `sub_genres`, classification `status` (`CLASSIFIED` or `UNKNOWN`), and timestamp.
- **Genre Playlist**: A Tidal playlist inside the designated folder representing either a qualifying primary genre, a qualifying sub-genre, "Others", or "Unknown", containing all qualifying tracks.
- **Target Folder**: A named Tidal playlist folder (default: "Genres") that contains the synchronized genre playlists and acts as the bounded scope for sync, cleanup, and wipe operations.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero standalone playlists are created for any genre or sub-genre with fewer than `--min-genre-size` (default: 5) tracks.
- **SC-002**: Every genre and sub-genre with at least `--min-genre-size` tracks receives a dedicated standalone playlist containing all associated tracks.
- **SC-003**: 100% of tracks with primary genres smaller than `--min-genre-size` are captured in the "Others" playlist, ensuring no library tracks with known classifications are excluded from organization.
- **SC-004**: Repeat executions on an unmodified library incur zero additional AI classification tokens, retrieving all primary and sub-genres from the local database cache.
- **SC-005**: AI classifications contain zero high-level umbrella categories from the restricted list (e.g., "Rock", "Pop", "General").
- **SC-006**: 100% of generated playlists have unique names with no duplicate playlists or duplicate tracks within any playlist.
- **SC-007**: When the wipe folder option is enabled, 100% of pre-existing playlists within the target folder are deleted prior to playlist generation, resulting in a clean folder containing only freshly synchronized playlists.
- **SC-008**: When `--wipe-only` is passed, the target folder is left containing exactly 0 playlists, and 0 Gemini API calls or new playlist creations occur.
- **SC-009**: 0 playlists outside the specified target folder are deleted or altered during a wipe operation.
- **SC-010**: The execution summary accurately reports the count of wiped playlists and includes the direct browser URL to the target folder.

---

## Assumptions

- A single song can belong to multiple qualifying playlists (its primary genre playlist, plus qualifying sub-genre playlists that each have at least 5 tracks).
- If a sub-genre has fewer than 5 tracks in the user's library, the song is still preserved in its primary genre playlist (or "Others"), so suppressing sparse sub-genres prevents playlist clutter without losing song organization.
- The default value for `--min-genre-size` is 5 tracks.
- Users can still adjust `--min-genre-size` via the CLI argument if they want a higher or lower threshold (e.g., `--min-genre-size 10` or `--min-genre-size 3`).
- Sub-genre names will be normalized into Title Case canonical display names.
- Folder wiping is opt-in via `--wipe-folder` (or alias `--wipe`); default execution preserves and incrementally updates existing playlists.
- Interactive terminal sessions prompt for confirmation before deleting playlists during a wipe unless `--yes` / `-y` is provided.
