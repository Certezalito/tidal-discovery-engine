# Feature Specification: Fix Duplicate Genre Playlists

**Feature Branch**: `015-cache-genre-playlists`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "the genre-playist command is buggy, its leaving duplicate playlists , its supposed to own the playlists in the folder during its operation."

## Clarifications
### Session 2026-08-11
- Q: When updating an existing genre playlist, should the system completely replace all tracks with the newly generated list, or append/merge them with the existing tracks? → A: Completely replace all tracks with the newly generated list
- Q: If the target folder already contains multiple duplicate playlists with the same genre name from previous buggy runs, what should the system do? → A: Keep one (e.g., oldest) and delete the other duplicates

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Idempotent Genre Playlist Generation (Priority: P1)

As a user running the genre-playlist command, I want the system to manage playlists in the designated folder without creating duplicates, so that my Tidal library remains perfectly organized regardless of how many times the command runs.

**Why this priority**: Core bug fix. The feature currently clutters the user's library with duplicate playlists on each run, which breaks the fundamental expectation of automation and the Idempotency quality gate.

**Independent Test**: Can be fully tested by running the `genre-playlist` command multiple times consecutively and observing that only one playlist per genre exists in the target folder.

**Acceptance Scenarios**:

1. **Given** an existing target folder containing a "Rock" genre playlist, **When** the genre-playlist command runs to sync the "Rock" genre, **Then** it updates the existing "Rock" playlist's tracks instead of creating a second "Rock" playlist.
2. **Given** multiple consecutive runs of the genre-playlist command, **When** the command completes, **Then** there is exactly one playlist per genre in the target folder, with no duplicates.
3. **Given** the command is taking ownership of the target folder, **When** it evaluates existing playlists, **Then** it accurately fetches all existing playlists (handling pagination properly) before deciding to create new ones.


### Edge Cases

- What if the target folder already contains duplicate playlists with the same genre name from previous buggy runs?
  - The system MUST keep one (e.g., the oldest) and delete the other duplicates.
- What happens when a playlist was renamed by the user outside the tool?
  - The tool relies on the exact name; if renamed, it may create a new one.
- How does the system handle playlists created outside the tool in the same folder?
  - If they match the genre name exactly, the tool takes ownership. If not, they are ignored.
- What if the folder contains hundreds of playlists requiring deep pagination?
  - The system must paginate through all results until all existing playlists are known.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST prevent the creation of duplicate genre playlists with the same name in the designated genre playlist folder.
- **FR-002**: System MUST retrieve and evaluate all existing playlists in the target folder before creating new ones.
- **FR-003**: System MUST correctly handle pagination when querying Tidal for existing playlists in the folder to ensure no existing playlist is overlooked.
- **FR-004**: System MUST update the tracks of an existing genre playlist rather than creating a new one if a match is found.
  - *Note*: Updating means completely replacing all tracks with the newly generated list to reflect the current state.
- **FR-005**: System MUST ensure that at the end of the operation, it strictly owns the target folder's state for the processed genres.

### Key Entities

- **Target Folder**: The specific Tidal folder designated to contain the generated genre playlists.
- **Genre Playlist**: A Tidal playlist dedicated to a specific music genre, which must remain unique by name within the Target Folder.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running the command 5 times consecutively results in exactly 0 duplicate genre playlists being created.
- **SC-002**: 100% of existing genre playlists in the folder are identified during execution, even if there are more than 50 (typical pagination limit).
- **SC-003**: Existing playlists are successfully updated (tracks added/removed) rather than duplicated.

## Assumptions

- Tidal API provides the ability to list all playlists within a specific folder, albeit potentially requiring pagination.
- Playlists are uniquely identified within the context of the target folder by their exact name (e.g., the genre name).
