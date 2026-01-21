# Tasks: Custom Tidal Playlist Folders

**Input**: Design documents from `/specs/003-custom-playlist-folder/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create feature branch `feature/003-custom-playlist-folder`
- [X] T002 Research Tidal API error handling and update `specs/003-custom-playlist-folder/research.md` with findings

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [X] T003 Update `src/services/tidal_service.py` to import necessary Tidal API classes/methods for folder management

## Phase 3: User Story 1 - Organize Playlists in Folders (Priority: P1) 🎯 MVP

**Goal**: Allow users to specify a folder name when generating a playlist, organizing their collection.

**Independent Test**: Run the generator with `--folder "My AI Mixes"` and verify the playlist appears inside that folder in the Tidal account.

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T004 [US1] Write unit tests for `get_or_create_folder` in `tests/test_tidal_service.py` (mocking duplicate/case-insensitive scenarios)
- [X] T005 [US1] Write unit tests for `create_playlist_in_folder` in `tests/test_tidal_service.py` (mocking duplicate playlist names)
- [X] T006 [US1] Write unit tests for CLI argument parsing in `tests/test_cli.py` to ensure `--folder` is accepted
- [ ] T007 [US1] Write integration tests verifying CLI -> Service -> Mocked API flow in `tests/test_integration.py`

### Implementation for User Story 1

- [X] T008 [US1] Implement `get_or_create_folder(folder_name)` in `src/services/tidal_service.py` handling case-insensitive search, creation, and exponential backoff retries from T002
- [X] T009 [US1] Implement `create_playlist_in_folder(...)` in `src/services/tidal_service.py` handling duplicate playlist names (append counter), retry logic, and fallback to root creation on persistent failure with non-blocking warning (from T002)
- [X] T010 [US1] Update `src/cli/main.py` to add `--folder` argument and wire it to `tidal_service` functions

## Final Phase: Polish & Cross-Cutting Concerns

- [X] T011 Update `quickstart.md` and `README.md` with new feature usage instructions
- [X] T012 Manual verification of the full workflow against a real Tidal account (if possible)

## Dependencies

- **US1** depends on **Foundational** tasks (T003)
- **T008** and **T009** (Implementation) depend on **T004** and **T005** (Tests) respectively (Test-First)
- **T010** (CLI) depends on **T008** and **T009** (Service logic)

## Parallel Execution Opportunities

- **T004** and **T005** (Service Tests) can be written in parallel with **T006** (CLI Tests).
- **T008** and **T009** can be implemented in parallel if different developers work on them (though they are in the same file, merge conflict risk is low if functions are distinct).

## Implementation Strategy

1.  **MVP First**: Focus entirely on User Story 1 as it covers the core request.
2.  **Test-Driven**: Write tests for the service logic first to handle the edge cases (duplicates, casing) correctly.
3.  **Mocking**: Heavily rely on mocking `tidalapi` to avoid spamming the real API during development and testing.
