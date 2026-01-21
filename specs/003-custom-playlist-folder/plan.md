# Implementation Plan: Custom Tidal Playlist Folders

## Technical Context

-   **Programming Language**: Python (based on existing project structure)
-   **Tidal API Interaction**:
    -   SDK: `tidalapi` library
    -   Methods: `session.user.favorites.playlist_folders()`, `session.user.create_folder()`, `session.user.create_playlist(parent_id=...)`.
-   **CLI Framework**: `argparse` (or whatever existing CLI uses) to add `--folder` argument.
-   **Dependencies**:
    -   `tidalapi`
-   **Project Structure**:
    -   `src/services/tidal_service.py`: Update to include folder management logic (find, create, create_playlist_in_folder) with retry logic.
    -   `src/cli/main.py`: Update to accept `--folder` argument and pass it to the service.
    -   `tests/`: Unit tests for folder logic and CLI argument parsing.

## Constitution Check

| Principle | Adherence | Notes |
| :--- | :--- | :--- |
| **I. Library-First** | Yes | Logic encapsulated in `tidal_service.py`. |
| **II. CLI Interface**| Yes | Feature exposed via `--folder` flag in CLI. |
| **III. Test-First** | Yes | TDD will be followed for folder management logic. |
| **IV. Integration Testing** | Yes | Integration test will verify API calls (mocked or real). |
| **V. Simplicity** | Yes | Straightforward extension of existing service. |

-   **Initial Gate Evaluation**: PASS

## Phase 0: Research

1.  **Tidal API Error Handling**: Confirm specific exceptions raised when folder creation fails or limits are reached to implement robust error handling. Verify if `tidalapi` has built-in retry mechanisms or if manual implementation is needed.

## Phase 1: Design & Contracts

-   **Data Models** (`data-model.md`): Update to include `Folder` concept if strictly necessary (likely just internal logic).
-   **Quickstart** (`quickstart.md`): Update usage examples to include `--folder`.

## Phase 2: Implementation Plan

### Sub-Task 1: Service Logic for Folders
- **ticket-1**: (Test) Write unit tests for `get_or_create_folder` and `create_playlist_in_folder` logic, including mocking `tidalapi` responses (duplicates, case-insensitivity) and simulation of transient errors for retry testing.
- **ticket-2**: (Code) Implement `get_or_create_folder(folder_name)` in `tidal_service.py`. Handle case-insensitive search, finding most recent duplicate, and creation with exponential backoff retries.
- **ticket-3**: (Code) Implement `create_playlist_in_folder(...)` in `tidal_service.py`. Handle duplicate playlist names by appending counter/timestamp and include retry logic for placement. Implement fallback to root creation on persistent failure with non-blocking warning.

### Sub-Task 2: CLI Integration
- **ticket-4**: (Test) Write tests for CLI argument parsing to ensure `--folder` is accepted.
- **ticket-5**: (Code) Update `src/cli/main.py` to add `--folder` argument and wire it to the `tidal_service` functions.

### Sub-Task 3: Integration & Documentation
- **ticket-6**: Write integration tests verifying the flow from CLI -> Service -> Mocked API.
- **ticket-7**: Update `quickstart.md` and `README.md` with new feature usage.

## Phase 3: Review & Release

-   **Code Review**: Review against principles and spec.
-   **Testing**: Verify all tests pass.
-   **Release**: Merge to main.
