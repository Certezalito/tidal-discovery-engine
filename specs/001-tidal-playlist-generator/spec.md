# Feature Specification: Tidal Playlist Generator

**Feature Branch**: `001-tidal-playlist-generator`
**Created**: 2025-11-07
**Status**: Draft
**Input**: User description: "Create a personalized music discovery tool that seamlessly integrates with a user's Tidal library, leverages Last.fm's recommendation engine, and automates the creation of new playlists to enrich the user's listening experience."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate a playlist from favorite tracks (Priority: P1)

As a user, I want to generate a new Tidal playlist with recommended tracks based on a selection of my favorite tracks, so that I can discover new music tailored to my tastes.

**Why this priority**: This is the core functionality of the application and delivers the primary value to the user.

**Independent Test**: The user can run the CLI tool with the required arguments and verify that a new playlist is created in their Tidal account with the expected tracks.

**Acceptance Scenarios**:

1.  **Given** a user with a Tidal account and favorite tracks, **When** the user runs the CLI tool with a specified number of favorite tracks to use as seeds and a name for the new playlist, **Then** a new playlist is created in their Tidal account with that name, and the playlist contains tracks similar to the selected favorite tracks.
2.  **Given** a user has already generated a playlist, **When** they run the tool again with the same playlist name, **Then** a new playlist is created with a unique identifier in the name to avoid conflicts.

### Edge Cases

-   What happens when the user has no favorite tracks in Tidal?
-   How does the system handle a user providing invalid credentials for Tidal or Last.fm?
-   What happens if Last.fm returns no similar tracks for a given seed track?
-   How does the system handle tracks that are found on Last.fm but not available on Tidal?

## Requirements *(mandatory)*

### Functional Requirements

-   **FR-001**: The system MUST allow a user to securely connect to their Tidal account.
-   **FR-002**: The system MUST fetch a user-specified number of random tracks from the user's "Favorite Tracks" on Tidal.
-   **FR-003**: The system MUST query the Last.fm API to find a user-specified number of similar tracks for each selected Tidal track.
-   **FR-004**: The system MUST provide an option to shuffle the similar tracks, fetching a large pool and randomly selecting from it.
-   **FR-005**: The system MUST create a new playlist in the user's Tidal account with a user-specified name.
-   **FR-005**: The system MUST populate the new playlist's description with the date of creation and the parameters used for generation. **Note:** The Tidal API has a 500-character limit for playlist descriptions.
-   **FR-006**: The system MUST search for the similar tracks on Tidal and add them to the new playlist.
-   **FR-007**: The system MUST store the Last.fm API key in a `.env` file.
-   **FR-008**: The system MUST perform a one-time interactive login to create a `tidal_session.json` file.
-   **FR-009**: The system MUST use the `tidal_session.json` file to automatically refresh credentials for non-interactive, scheduled execution.
-   **FR-010**: The system MUST log its operations to both the console and a log file.

### Key Entities *(include if feature involves data)*

-   **Track**: Represents a single song, with attributes like title, artist, and album.
-   **Playlist**: Represents a collection of tracks, with a name and description.
-   **User**: Represents the user of the application, with credentials for Tidal and Last.fm.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new playlist is created in the user's Tidal account within 60 seconds of running the command.
- **SC-002**: The generated playlist contains at least 80% of the requested number of similar tracks.
- **SC-003**: The application can be run successfully as a scheduled task without user intervention.
