# Tasks: Tidal Playlist Generator

**Input**: Design documents from `/specs/001-tidal-playlist-generator/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create project structure per implementation plan in `src/` and `tests/`
- [X] T002 Initialize Python project with `uv` and create `pyproject.toml`
- [X] T003 [P] Add `click`, `python-dotenv`, `requests`, `tidalapi`, and `pylast` to `pyproject.toml`
- [X] T004 [P] Create `.gitignore` file
- [X] T005 [P] Create `.env.example` file for credentials

---

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T006 Implement credential loading from `.env` file in `src/lib/auth.py`
- [X] T007 Implement logging setup to console and `project.log` in `src/lib/logging.py`
- [X] T008 Implement the basic CLI structure with `click` in `src/cli/main.py`

---

## Phase 3: User Story 1 - Generate a playlist from favorite tracks (Priority: P1) 🎯 MVP

**Goal**: Generate a new Tidal playlist with recommended tracks based on a selection of the user's favorite tracks.

**Independent Test**: Run the CLI tool with the required arguments and verify that a new playlist is created in the user's Tidal account with the expected tracks.

### Implementation for User Story 1

- [X] T009 [US1] Implement Tidal authentication flow in `src/services/tidal_service.py`
- [X] T010 [US1] Implement function to get random favorite tracks from Tidal in `src/services/tidal_service.py`
- [X] T011 [US1] Implement function to get similar tracks from Last.fm in `src/services/lastfm_service.py`
- [X] T012 [US1] Implement function to create a new playlist in Tidal in `src/services/tidal_service.py`
- [X] T013 [US1] Implement function to search for tracks on Tidal in `src/services/tidal_service.py`
- [X] T014 [US1] Implement function to add tracks to a playlist in Tidal in `src/services/tidal_service.py`
- [X] T015 [US1] Integrate the services and implement the main logic in `src/cli/main.py`
- [X] T016 [US1] Add error handling for API errors and missing data
- [X] T017 [US1] Add logging for all major operations

---

## Final Phase: Polish & Cross-Cutting Concerns

- [X] T018 Create `README.md` with setup and usage instructions
- [X] T019 Add documentation on how to schedule the script with `cron` and Windows Task Scheduler to `README.md`
- [X] T020 Perform final end-to-end testing
