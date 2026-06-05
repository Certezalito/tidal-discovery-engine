# Feature Specification: Genre Playlists

**Feature Branch**: `012-genre-playlists`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "I want to build a new spec, where this project will read my entire library and sort the tracks into genres, build playlists for each genre and put them in a specified folder."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sort Library into Genre Playlists (Priority: P1)

As a user, I want to run a command that reads my entire Tidal library, categorizes the tracks by genre, and automatically creates a playlist for each genre within a designated folder, so that my music is organized automatically.

**Why this priority**: This is the core functionality requested by the user, providing immediate value by automating the organization of their library.

**Independent Test**: Can be fully tested by running the command with a test account containing a small library of known genres and verifying that the correct playlists are created in the specified folder with the correct tracks.

**Acceptance Scenarios**:

1. **Given** a user has tracks in their library and specifies a folder name, **When** the genre sorting command is executed, **Then** the system creates the folder (if it doesn't exist), creates a playlist for each identified genre within that folder, and adds the appropriate tracks to each playlist.
2. **Given** a user's library has tracks with no identifiable genre, **When** the genre sorting command is executed, **Then** those tracks are placed in a default "Unknown" playlist.

---

### User Story 2 - Update Existing Genre Playlists (Priority: P2)

As a user who has previously sorted my library, I want to run the command again to process newly added tracks and add them to the existing genre playlists without duplicating tracks or playlists.

**Why this priority**: Users will continue to add music to their library over time, so the tool must be able to update the organization incrementally without destroying previous work.

**Independent Test**: Can be fully tested by running the command once, adding a new track to the library, running the command again, and verifying only the new track was added to the appropriate genre playlist.

**Acceptance Scenarios**:

1. **Given** the specified folder and some genre playlists already exist, **When** the command is executed, **Then** the system syncs the playlists by adding new tracks found in the library and removing tracks that are no longer in the library, without creating duplicate tracks.

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when a track has multiple genres?
- How does the system handle API rate limits when reading a very large library (e.g., 10,000+ tracks)?
- What happens if the specified folder already exists but contains non-genre playlists?
- What happens if the user's library is completely empty?

## Clarifications

### Session 2026-06-04

- Q: Which service should be used to determine the genre? → A: Use Gemini
- Q: Should tracks with multiple genres go into multiple playlists, a primary genre playlist, or a combined genre playlist? How should missing genres be handled? → A: Add to multiple, missing to "Unknown"
- Q: Should existing tracks in the playlists be preserved, cleared and recreated, or should we only append new tracks? → A: Sync (add new, remove deleted)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST be able to read all tracks from the user's Tidal library, handling pagination to ensure all tracks are retrieved.
- **FR-002**: System MUST determine the genre(s) for each track in the library using Gemini.
- **FR-003**: System MUST resolve cases where a track has multiple genres or no genre by adding the track to multiple genre playlists, and placing tracks with no genre into an "Unknown" playlist.
- **FR-004**: System MUST allow the user to specify the name of the destination folder for the genre playlists via a CLI argument (which overrides configuration) or a default configuration.
- **FR-005**: System MUST create the specified folder in the user's Tidal account if it does not already exist.
- **FR-006**: System MUST create a playlist for each unique genre identified, placing it inside the specified folder.
- **FR-007**: System MUST add the corresponding tracks to each genre playlist.
- **FR-008**: System MUST update existing genre playlists if the command is run multiple times by syncing the playlists (adding new tracks and removing deleted tracks from the library).
- **FR-009**: System MUST provide clear CLI feedback on progress, especially for large libraries (e.g., number of tracks processed, playlists created).

### Key Entities

- **Library Track**: A track saved in the user's Tidal library.
- **Genre**: A categorization label applied to a track.
- **Playlist Folder**: A container in Tidal used to group multiple playlists together.
- **Genre Playlist**: A Tidal playlist dedicated to a specific genre, containing matching library tracks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The system correctly categorizes at least 90% of a user's library tracks into appropriate genre playlists.
- **SC-002**: The tool successfully processes a library of 5,000 tracks without timing out or crashing.
- **SC-003**: Running the tool a second time on an unmodified library takes less than 20% of the time of the initial run and creates no duplicate tracks in the playlists.
- **SC-004**: All generated playlists are correctly nested within the single user-specified folder in Tidal.

## Assumptions

- The Tidal API supports reading the entire user library via pagination.
- The Tidal API supports creating folders and placing playlists inside those folders.
- The user has a stable internet connection capable of sustaining potentially long-running API operations for large libraries.
- The chosen service for genre resolution has sufficient rate limits to support analyzing thousands of tracks in a single session.
