# Feature Specification: Dedicated Radio Command

**Feature Branch**: `016-single-seed-track`  
**Created**: 2026-09-03  
**Status**: Draft  
**Input**: User description: "i want a new branch, the goal is to make the \"Single Seed Track\" thing its own command" / "make the seed track track #1 and set the default limit to 50" / "lets remove the track-radio alias thing, i don't care for it" / "in the documentation, lets put recomend before radio, then genre-playlist" / "also i dont need the legacy single seed flag"

## Clarifications

### Session 2026-09-03

- Q: What should the primary CLI command name be for this dedicated single-track discovery flow? → A: `radio` for optimal ergonomics and alignment with streaming service terminology (the `track-radio` alias is removed per user request).
- Q: Should `--playlist-name` remain a strictly required option, or should it be optional with an automatic default name? → A: Optional with default `"{artist} - {track} Radio"` (supports custom override and dynamic `{date}` formatting).
- Q: What should the default recommendation limit (`--num-tracks`) be? → A: 50 tracks (providing volume parity with the legacy recommendation experience).
- Q: Should the seed track itself be included as the first track in the generated playlist, or should the playlist contain only recommended tracks? → A: The seed track MUST be inserted as Track #1 in the playlist, followed by the recommended tracks. Seed track details (title and artist) MUST also be documented in the playlist description metadata.
- Q: Should `--num-tracks` represent the total number of tracks in the generated playlist (including the seed track), or strictly the number of recommendations appended after the seed track? → A: Total playlist size: the final playlist contains up to N total tracks (1 seed track at Track #1 + N - 1 recommendations). If the seed track cannot be catalog-resolved, N recommendations are used.
- Q: In what order should the CLI commands and their parameter tables be presented in the user documentation (README)? → A: `recommend` first, followed by `radio`, and then `genre-playlist`.
- Q: Should the legacy single-seed flags (`--artist` and `--track`) be retained on the `recommend` command with deprecation warnings? → A: No. The legacy single-seed flags are completely removed from `recommend`, ensuring clean separation between library discovery (`recommend`) and single-seed track discovery (`radio`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dedicated Radio Command Execution (Priority: P1)

As a music listener wanting recommendations built from a specific song, I can run a dedicated `radio` command providing the artist and track name directly, so I can generate a targeted playlist starting with the seed song without dealing with irrelevant library-sampling parameters.

**Why this priority**: This is the core purpose of the feature. Separating track-based generation into its own command simplifies the CLI interface and removes confusion between favorite-library discovery and single-song exploration.

**Independent Test**: Execute the new dedicated `radio` command with valid `--artist` and `--track` options (omitting `--playlist-name` and `--num-tracks`). Verify that the command succeeds, automatically names the playlist `"{artist} - {track} Radio"`, places the resolved seed track as Track #1, populates the playlist description with the seed track details, and fills the playlist with 49 similar track recommendations (50 tracks total) by default.

**Acceptance Scenarios**:

1. **Given** a user provides a valid artist and track title to the `radio` command without specifying `--playlist-name` or `--num-tracks`, **When** the command executes, **Then** the system creates a new playlist titled `"{artist} - {track} Radio"` with a description referencing the seed track, placing the seed track at Track #1 followed by 49 recommendations derived from that seed track (50 tracks total).
2. **Given** a user invokes `radio` without providing both an artist and a track title, **When** input validation runs, **Then** the command rejects the execution immediately with a clear message explaining that both artist and track are required.
3. **Given** a user specifies a custom playlist name with a dynamic `{date}` token (e.g., `--playlist-name "Track Vibes {date}"`), **When** the playlist is created, **Then** the token is replaced with the current date formatted as `YYYYMMDD`.
4. **Given** recommendations are generated for a seed track, **When** the playlist is assembled, **Then** the seed track is placed at Track #1, followed by up to `num_tracks - 1` recommended tracks, and the playlist description explicitly documents the seed track title and artist.

---

### User Story 2 - Full Feature Parity with Recommendation Providers & Filters (Priority: P2)

As a music listener exploring tracks from a single seed, I can use AI-powered recommendations, deep-cut shuffling, favorite exclusions, and folder organization in the new command, matching the capabilities previously available in the combined mode.

**Why this priority**: Users who currently use the single-seed mode in the general recommendation command rely on AI suggestions, deep cuts, and favorite filtering. The dedicated command must provide identical capability parity.

**Independent Test**: Run `radio` with AI recommendation enabled, deep-cut shuffling enabled, favorite exclusion enabled, and folder placement specified. Verify that the created playlist starts with the seed track, excludes existing favorites from the recommendations, applies deep-cut exploration, and is placed in the designated folder.

**Acceptance Scenarios**:

1. **Given** a user runs `radio` with the AI recommendation option enabled, **When** suggestions are retrieved, **Then** the system uses the AI provider to generate recommendations tailored to the seed track.
2. **Given** a user enables deep-cut shuffling alongside AI recommendations in `radio`, **When** suggestions are gathered, **Then** the system prioritizes lesser-known and underground tracks fitting the seed song's style.
3. **Given** a user enables the exclude-favorites option in `radio`, **When** recommendations are processed, **Then** any tracks already saved in the user's library favorites are omitted from the resulting recommendations.
4. **Given** a user runs `radio` without specifying a folder, **When** playlist creation succeeds, **Then** the playlist is organized inside the `"Radio"` folder on Tidal by default; if a custom `--folder` name is specified, the playlist is organized inside that custom folder.

---

### User Story 3 - Clean Command Separation: Dedicated Discovery for Library vs. Seed Track (Priority: P3)

As a user running the `recommend` command, I use it exclusively for Tidal favorite library-based discovery; single-seed parameters (`--artist` and `--track`) are eliminated from `recommend`, ensuring each CLI command has a single, unambiguous purpose and avoiding command bloat.

**Why this priority**: Eliminating legacy options from `recommend` produces a clean separation of concerns: `recommend` operates on library favorites, and `radio` operates on single-seed tracks.

**Independent Test**: Inspect `recommend --help` and verify that `--artist` and `--track` are not recognized or listed. Execute `recommend` without seed parameters to verify library discovery continues to work as expected.

**Acceptance Scenarios**:

1. **Given** a user consults the options for the `recommend` command, **When** reviewing `recommend --help`, **Then** the single-seed parameters `--artist` and `--track` are not present.
2. **Given** a user runs the general `recommend` command without artist or track parameters, **When** the command executes, **Then** it operates solely in library-discovery mode.
3. **Given** a user consults user documentation (README), **When** reading the CLI usage guide, **Then** the documentation presents the commands in the order `recommend`, `radio`, and `genre-playlist`, with `recommend` documenting library-only discovery without single-seed flags, and `radio` documented as a dedicated command with concrete examples and parameters.

---

### Edge Cases

- **Missing one seed component**: User supplies `--artist` but omits `--track`, or supplies `--track` but omits `--artist` in `radio`. System must reject with a specific error stating both are required together.
- **Empty or whitespace seed values**: User supplies empty strings (`""`) or whitespace-only inputs for artist or track in `radio`. System must reject these as invalid inputs before querying recommendation engines.
- **Zero or negative track count**: User requests a track count of 0 or a negative integer. System must fail validation with guidance to provide a positive number.
- **Unresolvable seed track**: The specified seed track cannot be resolved in the music catalog. System must log an informative warning, proceed to assemble the playlist from up to `num_tracks` resolved recommendations, and record the seed track text in the playlist description metadata.
- **Zero resolvable recommendations**: None of the recommended tracks can be found or inserted into the user's music service. System must report an actionable failure and avoid claiming success.
- **Partial resolvable recommendations**: Some recommended tracks cannot be resolved in the music catalog. System must insert all resolvable tracks, emit a warning listing the count and up to the first 5 skipped track titles, and consider the run successful if at least one track was added.
- **Missing AI credentials**: User requests AI recommendations without configuring the required AI service credentials. System must fail immediately with actionable instructions on how to set up the credentials.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated CLI command named `radio` dedicated to generating playlists from a single seed track.
- **FR-002**: The `radio` command MUST require both an artist name (`--artist`) and a track title (`--track`).
- **FR-003**: The `radio` command MUST support an optional destination playlist name (`--playlist-name`) that defaults to `"{artist} - {track} Radio"`, and MUST support dynamic `{date}` token replacement with the current date in `YYYYMMDD` format when specified.
- **FR-004**: The `radio` command MUST allow users to specify the desired total playlist track count (`--num-tracks`) with a default of 50 (composed of 1 seed track at Track #1 followed by 49 recommendation tracks), and MUST accept `--num-similar-tracks` as a backward-compatible alias.
- **FR-005**: The `radio` command MUST validate that the requested track count is a positive integer greater than zero.
- **FR-006**: The `radio` command MUST support an AI recommendation flag (`--gemini`) to source recommendations from generative AI instead of external music database similarity.
- **FR-007**: The `radio` command MUST support a shuffle flag (`--shuffle`), which triggers deep-cut and underground discovery when combined with AI recommendations, and randomizes track ordering when using standard catalog similarity.
- **FR-008**: The `radio` command MUST organize the created playlist into a dedicated folder on Tidal named `"Radio"` by default, and MUST support the `--folder` option to allow overriding the destination folder with a custom name.
- **FR-009**: The `radio` command MUST support an exclude-favorites flag (`--exclude-favorites`) to filter out tracks that already exist in the user's saved library favorites.
- **FR-010**: The `radio` command MUST gracefully handle unresolvable recommendation tracks by inserting all valid tracks and logging a warning summary containing the skipped count and up to the first 5 skipped track titles.
- **FR-011**: The `radio` command MUST treat the run as a failure if zero tracks (neither seed nor recommendations) can be resolved and added to the destination playlist.
- **FR-012**: The `recommend` command MUST NOT include `--artist` or `--track` parameters, reserving its usage strictly for library-favorite-based playlist discovery.
- **FR-013**: Single-seed track playlist generation MUST be accessible exclusively through the dedicated `radio` command.
- **FR-014**: All track resolution in `radio` MUST rely exclusively on authoritative catalog text search (artist and title) and MUST NOT request or utilize synthetic catalog identifiers or ISRCs from AI models.
- **FR-015**: The system documentation (README) MUST present the CLI commands and parameter tables in the order `recommend`, `radio`, and `genre-playlist`, with clear command examples and parameter explanations, documenting `recommend` strictly for library discovery without legacy single-seed parameters.
- **FR-016**: The `radio` command MUST insert the resolved seed track as the first track (Track #1) in the generated playlist, followed by up to `num_tracks - 1` recommended tracks (yielding `num_tracks` total tracks), and MUST include the seed track information (track title and artist name) in the created playlist's description metadata. If the seed track cannot be resolved on Tidal, the system MUST log a warning and assemble the playlist from `num_tracks` resolved recommendations.

### Key Entities *(include if feature involves data)*

- **Single Seed Specification**: The input criteria defining the starting point of music discovery, containing mandatory artist name and track title, plus optional desired total track count (default 50).
- **Playlist Destination**: The target container in the music streaming service, defined by a name (with optional date placeholder), description metadata noting seed track origin, and an optional folder hierarchy.
- **Recommendation Set**: The list of suggested tracks returned by either music database similarity or AI generation, filtered to remove library duplicates and unresolvable catalog entries, appended after Track #1.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can execute the dedicated `radio` command to create a complete recommended playlist in under 30 seconds for standard recommendation counts (up to 50 tracks).
- **SC-002**: 100% of `radio` command executions with missing or whitespace-only artist or track inputs are rejected before external recommendation queries are initiated.
- **SC-003**: 100% of `radio` runs with the exclude-favorites option enabled successfully filter out all tracks already present in the user's favorites snapshot from the recommendation set.
- **SC-004**: 100% of `recommend` command options are dedicated to library-favorites discovery; `--artist` and `--track` are completely absent from `recommend` options and help text.
- **SC-005**: All CLI options, defaults, and examples for `recommend`, `radio`, and `genre-playlist` are documented in the project README in that specific order (`recommend` before `radio`, then `genre-playlist`), allowing first-time users to copy and run working command examples without reference to source code.
- **SC-006**: In scenarios where partial recommendations fail catalog resolution, 100% of runs with at least one resolvable track complete playlist creation and log a capped summary of skipped tracks.
- **SC-007**: 100% of playlists created via `radio` where the seed track is resolvable place the seed track at Track #1 and include the seed track's title and artist in the playlist description metadata.

## Assumptions

- **Command Naming**: The primary CLI command name is established solely as `radio` for maximum ergonomics and industry familiarity.
- **Command Separation Strategy**: Rather than retaining single-seed flags on `recommend` with a deprecation warning, single-seed parameters are removed entirely from `recommend`. `recommend` is strictly for library-favorite discovery, and `radio` is strictly for single-seed discovery.
- **Parameter Naming & Default**: The parameter for recommendation count in `radio` uses `--num-tracks` as its primary flag (with `--num-similar-tracks` preserved as an alias) and defaults to 50 tracks, matching the volume of the legacy recommendation flow.
- **Seed Track Placement & Total Count Math**: `--num-tracks` governs total playlist size: Track #1 is the seed track, followed by `num_tracks - 1` recommendations (yielding exactly `num_tracks` items). If the seed is unresolvable on Tidal, `num_tracks` recommendations are used.
- **Playlist Naming**: `--playlist-name` is optional with default `"{artist} - {track} Radio"` in `radio` to minimize user typing while preserving customization.
- **Zero ISRC Hallucination**: AI recommendations in `radio` adhere strictly to Principle VIII of the project constitution, querying AI only for artist and title strings and resolving tracks through authoritative catalog search.
