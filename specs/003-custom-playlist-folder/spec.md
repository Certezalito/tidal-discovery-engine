# Feature Specification: Custom Tidal Playlist Folders

**Feature Branch**: `003-custom-playlist-folder`
**Created**: 2026-01-15
**Status**: Draft
**Input**: User description: "I want tidal to put the generated playlist in a folder of my naming"

## Clarifications

### Session 2026-01-15

- Q: If the user specifies a folder name that matches multiple existing folders, which one should be used? → A: Use the most recently created folder.
- Q: Should the folder name matching be case-sensitive? → A: Case-insensitive matching (e.g., "Pop" == "pop").
- Q: If the system creates a new folder but fails to add the playlist to it, what should happen to the empty folder? → A: Keep the empty folder.
- Q: How should the system handle folder names containing slashes (e.g., "Rock/Classics")? → A: Treat slashes as part of the folder name.
- Q: If a playlist with the same name already exists in the target folder, how should the system proceed? → A: Append a timestamp or counter to the new playlist name.
- Q: Should we implement automatic retries for transient network errors during folder creation? → A: Implement exponential backoff retries (e.g., 3 attempts) for transient errors.
- Q: How prominent should the notification be when falling back to root creation or renaming? → A: Log a warning to stderr/console but continue execution without interruption.

## User Scenarios & Testing

### User Story 1 - Organize Playlists in Folders (Priority: P1)

As a user, I want to specify a folder name when generating a playlist so that I can keep my Tidal collection organized.

**Why this priority**: Core request from the user.

**Independent Test**: Run the generator with a folder argument and verify the playlist appears inside that folder in the Tidal account.

**Acceptance Scenarios**:

1.  **Given** a folder "My AI Mixes" does not exist, **When** I generate a playlist specifying this folder, **Then** the folder is created and the playlist is placed inside it.
2.  **Given** a folder "My AI Mixes" already exists, **When** I generate a playlist specifying this folder, **Then** the playlist is added to the existing folder without creating a duplicate.
3.  **Given** no folder is specified, **When** I generate a playlist, **Then** it is created at the root level (default behavior).

## Functional Requirements

1.  **Input Mechanism**: The system must accept an optional folder name parameter from the user. Special characters, including slashes, must be treated as literal parts of the folder name.
2.  **Folder Existence Check**: The system must verify if a folder with the specified name already exists in the user's Tidal account. If multiple folders exist with the same name, the system must select the most recently created one. Matching must be case-insensitive.
3.  **Folder Creation**: If the specified folder does not exist, the system must create it.
4.  **Playlist Placement**: The generated playlist must be added to the specified folder. If a playlist with the same name already exists in the folder, the system must append a counter or timestamp to the new playlist's title to avoid duplicates (e.g., "My Playlist (1)").
5.  **Error Handling**: The system must implement exponential backoff retries (up to 3 attempts) for transient network errors during API operations. If folder creation or placement fails after retries (or due to permanent errors like API limits/permissions), the system must default to creating the playlist at the root level and log a non-blocking warning to stderr/console.
    *   **Exceptions**: Critical errors such as Authentication Failure must abort the operation immediately without fallback.
    *   **Final Failure State**: If the fallback (root level creation) also fails, the system must log a fatal error and exit. Any successfully created empty folders are preserved to avoid accidental data loss.

## Success Criteria

-   **Quantitative**: 100% of playlists generated with a folder argument are located within that folder in the Tidal account.
-   **Qualitative**: Users can easily find their generated playlists grouped together, reducing clutter in their main playlist view.

## Assumptions & Dependencies

-   **Assumption**: The Tidal API supports creating folders and moving playlists into them. Confirmed via `tidalapi` methods: `playlist_folders()`, `create_folder()`, and `create_playlist(parent_id=...)`.
-   **Dependency**: Requires authenticated access to the user's Tidal account with write permissions.

## Key Entities

-   **Folder**: A container for playlists (Name, ID).
-   **Playlist**: The generated music list.

## Constraints

-   Must handle potential duplicate folder names gracefully (e.g., use the first match).
