# Feature Specification: Fix Duplicate Tracks in Organized Playlists

**Feature Branch**: `023-fix-organize-duplicate-tracks`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "there's a bug in the organize feature, tracks are repeating in the organized playlist"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deduplicated Track Membership in Organized Playlists (Priority: P1)

As a user organizing my music library by genre, I want every organized genre playlist to contain each qualifying track at most once, so that I do not hear the same track repeated while listening to a genre playlist.

**Why this priority**: This is the core bug reported by the user. Repeating tracks degrade the listening experience and violate the core expectation that organized playlists accurately and cleanly reflect the user's library.

**Independent Test**: Can be fully tested by running the organize command against a library that includes duplicate track occurrences or overlapping genre assignments and verifying that every generated genre playlist contains zero repeating tracks.

**Acceptance Scenarios**:

1. **Given** a user library containing tracks mapped to a qualifying genre, **When** the organize command creates a new genre playlist, **Then** each qualifying track appears in that playlist exactly once.
2. **Given** a library where the same track is encountered more than once during library scanning or genre grouping, **When** the organize command builds the target track list for a genre playlist, **Then** duplicate entries are collapsed so the track is added only once.
3. **Given** a track that belongs to multiple distinct qualifying genres (e.g., a primary genre and a qualifying sub-genre), **When** the organize command runs, **Then** the track appears exactly once in each of those distinct genre playlists.

---

### User Story 2 - Automatic Cleanup of Existing Playlists with Duplicate Tracks (Priority: P1)

As a user whose existing organized playlists already contain repeating tracks from earlier runs, I want running the organize command to automatically remove extra duplicate occurrences from those playlists without requiring a folder wipe, so that my playlists are repaired cleanly on the next run.

**Why this priority**: Users running the organize feature regularly already have affected playlists in their library. Repairing them automatically during normal synchronization resolves the issue without forcing destructive manual cleanup or wiping playlists.

**Independent Test**: Can be fully tested by taking an existing organized genre playlist that contains 2 or more copies of the same track, running the organize command once, and verifying that exactly 1 copy of the track remains while all other qualifying tracks are preserved.

**Acceptance Scenarios**:

1. **Given** an existing organized playlist containing 2 or more copies of a qualifying track, **When** the organize command runs, **Then** all extra copies are removed so exactly 1 copy of that track remains in the playlist.
2. **Given** an existing organized playlist containing multiple copies of a track that no longer belongs in that genre or library, **When** the organize command runs, **Then** all copies of that track are removed from the playlist.
3. **Given** a large existing organized playlist spanning multiple pages of tracks, **When** the organize command evaluates the playlist, **Then** duplicates located on any page of the playlist are detected and removed.

---

### User Story 3 - Stable Repeated Synchronization Without Churn (Priority: P2)

As a user running the organize command on a recurring schedule, I want consecutive runs against an unchanged library to make zero changes to already-organized playlists, so that automated runs remain predictable, fast, and do not repeatedly add and remove the same tracks.

**Why this priority**: Scheduled unattended execution is a core workflow. If synchronization repeatedly adds and removes tracks on every run, it creates unnecessary playlist churn, noisy logs, and wasted API calls.

**Independent Test**: Can be fully tested by running the organize command twice consecutively on an unmodified library and verifying that the second run reports every playlist as up to date with 0 tracks added and 0 tracks removed.

**Acceptance Scenarios**:

1. **Given** an organized genre folder that was just synchronized, **When** the organize command is run again with no changes to the user's library, **Then** 0 tracks are added, 0 tracks are removed, and all playlists remain free of duplicate tracks.
2. **Given** an existing playlist where one new qualifying track is added to the user's library, **When** the organize command runs, **Then** only that single new track is added without re-adding or duplicating any existing tracks.

---

### Edge Cases

- What happens when a track appears multiple times in the scanned library (for example, across paginated library results or duplicate saved entries)? The track is deduplicated before playlist synchronization so it appears at most once per playlist.
- What happens when an existing playlist contains 3 or more copies of the same track? All surplus copies are removed while retaining exactly one copy of the qualifying track.
- What happens when a track is classified under overlapping genre labels (e.g., identical primary genre and sub-genre, or variant casing/punctuation that normalizes to the same playlist name)? The track is added to that playlist only once.
- What happens when a playlist is large enough to require batched additions or removals? Deduplication is enforced across the entire playlist, not only within individual batches.
- What happens when a user has multiple versions of a song in their library? If two entries represent the exact same underlying recording released on different albums or compilations (e.g., single release and album release), only one entry is kept per playlist; genuinely different recordings (such as remixes, live performances, or acoustic versions) are treated as distinct tracks and preserved.
- What happens when a track lacks a recording identifier? Deduplication falls back to exact catalog track identity so the track is still prevented from repeating in the playlist.
- What happens when deduplicating tracks causes a genre's unique track count to drop below the configured minimum genre size (default 5)? The genre is evaluated against the threshold using its unique deduplicated track count (primary genres below the threshold route to "Others"; sub-genres below the threshold do not get a standalone playlist, and any previously existing playlist that drops below the threshold is removed).

## Clarifications

### Session 2026-11-23
- Q: When determining whether a track is repeating in an organized playlist, what should count as a duplicate? → A: Exact same catalog track entry OR the same underlying recording across different releases (removes identical track entries and album/single/compilation re-releases of the same recording, while preserving distinct versions such as remixes or live recordings).
- Q: When a library contains multiple releases of the same underlying recording, which single copy should be kept in the organized playlist? → A: Keep whichever matching copy is already in the playlist; for new playlists (or when no copy is currently present), select one copy deterministically so repeated runs remain stable with zero churn.
- Q: Should the minimum genre size threshold (default 5 tracks) be counted after deduplicating tracks? → A: Yes — evaluate the minimum genre size threshold using unique deduplicated tracks only.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST guarantee that every organized genre playlist contains each qualifying track at most once after an organize run completes.
- **FR-002**: System MUST deduplicate tracks within each organized playlist by exact catalog track identity AND by underlying recording identity (so identical recordings released on different albums, singles, or compilations appear at most once per playlist, while genuinely distinct recordings such as remixes or live versions are preserved) before determining playlist additions and removals. When recording identity is unavailable for a track, System MUST still deduplicate by exact catalog track identity.
- **FR-003**: When multiple catalog releases of the same underlying recording qualify for a playlist, System MUST preserve a matching copy already present in the playlist to avoid unnecessary churn; when no copy is yet present, System MUST choose one copy deterministically so repeated runs select the same track.
- **FR-004**: System MUST evaluate the minimum genre size threshold (default 5 tracks) using unique deduplicated tracks per genre so that standalone playlists are only created or retained when they meet the minimum size after deduplication.
- **FR-005**: System MUST retrieve and inspect the complete current track list of each existing organized playlist (including playlists spanning multiple pages) before calculating sync changes.
- **FR-006**: When an existing organized playlist contains multiple copies of a qualifying track, System MUST remove the extra duplicate copies so that exactly one copy remains.
- **FR-007**: When an existing organized playlist contains multiple copies of a track that no longer qualifies for that playlist, System MUST remove all copies of that track.
- **FR-008**: System MUST preserve multi-genre assignment behavior: a track qualifying for multiple distinct genre playlists MUST appear once in each of those playlists.
- **FR-009**: System MUST ensure consecutive organize runs on an unchanged library are idempotent, resulting in zero track additions, zero track removals, and zero duplicate tracks on subsequent runs.
- **FR-010**: System MUST accurately report track additions, track removals (including removed duplicate occurrences), and up-to-date playlists in the run logs and completion summary.

### Key Entities

- **Library Track**: A track from the user's music library being organized, represented by its identifying metadata (catalog identity, artist, title, and recording attributes) and its assigned genre classifications.
- **Organized Genre Playlist**: A managed playlist within the target genre folder representing a qualifying genre (or fallback category such as "Others" / "Unknown"), whose membership must consist of unique qualifying tracks.
- **Playlist Sync Operation**: The reconciliation process that compares a playlist's current track entries against its desired unique track list and applies only the additions and removals required to achieve a duplicate-free match.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of organized genre playlists contain 0 duplicate tracks after an organize run completes, regardless of playlist size.
- **SC-002**: 100% of pre-existing organized playlists containing duplicate tracks are cleaned to 0 duplicate tracks in a single standard organize run without requiring a folder wipe.
- **SC-003**: Consecutive organize runs on an unchanged library result in 0 tracks added and 0 tracks removed across 100% of managed playlists on the second run.
- **SC-004**: 100% of tracks qualifying for multiple distinct genres appear exactly once in each of their qualifying genre playlists.

## Assumptions

- The organize command continues to own track membership for managed playlists inside the designated target genre folder.
- Deduplication is scoped per individual playlist; a track appearing once in one genre playlist and once in another genre playlist is expected multi-genre behavior.
- Repairing existing playlists with repeating tracks occurs automatically during a normal organize run without requiring a new CLI flag or a folder wipe.
- Existing CLI arguments, default target folder name, minimum genre size threshold, and caching behavior remain unchanged.
