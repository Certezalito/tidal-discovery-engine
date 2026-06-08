# Tasks: Genre Playlists

**Input**: Design documents from /specs/012-genre-playlists/

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish CLI entry points and service scaffolding for genre-playlist workflow.

- [x] T001 Add genre-playlist CLI options and command path in src/cli/main.py
[x] T001b Add `--min-genre-size` CLI option with default of 2 in src/cli/main.py
- [x] T002 Add genre-playlist logging constants and helper messages in src/lib/logging.py
- [x] T003 Create orchestration scaffold for genre playlist runs in src/services/genre_playlist_service.py
- [x] T003b [P] [US1] Add CLI test for folder name precedence (CLI argument overrides configuration) in tests/test_cli.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared mechanics required by all user stories.

**CRITICAL**: Complete this phase before starting user-story work.

- [x] T004 Implement full-library retrieval with pagination/retry in src/services/tidal_service.py
- [x] T005 Implement Gemini genre classification adapter for library tracks in src/services/gemini_service.py
- [x] T006 Implement track identity normalization utilities for sync comparison in src/services/tidal_service.py
- [x] T007 Implement folder playlist discovery helpers for deterministic genre playlist resolution in src/services/tidal_service.py
- [x] T008 Implement reusable playlist membership read helpers for sync operations in src/services/tidal_service.py
- [x] T009 Implement orchestration-level run summary model for scan/classify/create/sync metrics in src/services/genre_playlist_service.py

**Checkpoint**: Foundation ready. User stories can proceed.

---

## Phase 3: User Story 1 - Sort Library into Genre Playlists (Priority: P1) MVP

**Goal**: Build genre playlists from the full Tidal library using Gemini, enforcing a single best-match genre per track, handling Unknown fallback, grouping niche genres into "Others", sorting by ascending track count, and caching classifications locally while bypassing Unknowns.

**Independent Test**: Run the genre-playlist command against a test library and verify folder creation, genre playlists, single-genre placement per track, local cache creation, Unknown handling, "Others" grouping threshold, and ascending track count processing order.

### Tests for User Story 1

- [x] T010 [P] [US1] Add CLI test for first-run folder and genre playlist creation in tests/test_cli.py
[x] T010b [P] [US1] Add CLI test for `--min-genre-size` threshold grouping into "Others" in tests/test_cli.py
- [x] T011 [P] [US1] Add Gemini classification test for single best-match genre and Unknown fallback handling in tests/test_gemini_service.py
- [x] T011b [P] [US1] Add test for accuracy evaluation protocol (sample set, scoring approach) in tests/test_gemini_service.py
- [x] T011c [P] [US1] Add service test verifying local JSON/DB cache write on classification hit and bypass on Unknown miss in tests/test_genre_playlist_service.py
[x] T011d [P] [US1] Add service test verifying playlist orchestration executes in ascending track count order in tests/test_genre_playlist_service.py

### Implementation for User Story 1

- [x] T012 [US1] Implement genre grouping and Unknown assignment from classification output in src/services/genre_playlist_service.py
- [x] T012b [US1] Implement local cache read/write adapter (file or DB) for Gemini classifications in src/services/genre_playlist_service.py
[x] T012c [US1] Implement "Others" grouping logic for genre groups below the `--min-genre-size` threshold in src/services/genre_playlist_service.py
[x] T012d [US1] Implement sorting of genre groups by ascending track count prior to playlist processing in src/services/genre_playlist_service.py
- [x] T013 [US1] Implement first-run folder and per-genre playlist creation flow in src/services/genre_playlist_service.py
- [x] T014 [US1] Implement first-run track insertion pipeline for grouped single-genre memberships in src/services/genre_playlist_service.py
- [x] T015 [US1] Wire CLI command path to orchestration service and options in src/cli/main.py
- [x] T016 [US1] Add progress and completion logging for scan, classify, and create steps in src/cli/main.py

**Checkpoint**: User Story 1 independently functional and demoable.

---

## Phase 4: User Story 2 - Update Existing Genre Playlists (Priority: P2)

**Goal**: Re-run the command and sync existing genre playlists by adding new library tracks and removing tracks no longer in the library, processing in ascending track count order.

**Independent Test**: Run command once, change library membership, run again, and verify playlist membership matches desired genre sets with no duplicates.

### Tests for User Story 2

- [x] T017 [P] [US2] Add service test for sync delta calculation add/remove semantics in tests/test_tidal_service.py
- [x] T018 [P] [US2] Add CLI rerun test verifying no duplicate playlists and synced membership in tests/test_cli.py
- [x] T018b [P] [US2] Add benchmarking task to measure rerun sync runtime (must be <20% of initial run) in tests/test_genre_playlist_service.py

### Implementation for User Story 2

- [x] T019 [US2] Implement desired-vs-existing membership diff generation per genre playlist in src/services/genre_playlist_service.py
- [x] T020 [US2] Implement per-playlist sync operations for additions and removals in src/services/tidal_service.py
- [x] T021 [US2] Integrate rerun sync orchestration with idempotence safeguards in src/services/genre_playlist_service.py
- [x] T022 [US2] Add rerun summary metrics for playlists updated, tracks added, and tracks removed in src/cli/main.py

**Checkpoint**: User Stories 1 and 2 both functional independently.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final quality, documentation, and resilience checks.

- [x] T023 Update end-user usage and behavior notes for genre workflow in README.md
[x] T023b Update README.md to document `--min-genre-size` usage, "Others" grouping, and "Updated date" sorting behavior
- [x] T024 [P] Add edge-case test coverage for empty libraries and existing non-genre playlists in tests/test_cli.py
- [x] T024b [P] Add edge-case test coverage for a corrupted or unreadable cache file in tests/test_genre_playlist_service.py
- [x] T025 [P] Add pagination/rate-limit boundary regression test for large libraries in tests/test_tidal_service.py
- [x] T026 Validate quickstart scenarios and adjust wording for observed behavior in specs/012-genre-playlists/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): No dependencies
- Foundational (Phase 2): Depends on Setup completion and blocks all user stories
- User Story 1 (Phase 3): Depends on Foundational completion
- User Story 2 (Phase 4): Depends on Foundational completion and builds on playlist artifacts created in User Story 1
- Polish (Phase 5): Depends on completion of desired user stories

### User Story Dependencies

- US1 (P1): No dependency on US2
- US2 (P2): Depends on US1 behavior to have existing genre playlists to sync

### Within Each User Story

- Tests should be implemented before or alongside implementation tasks
- Service logic before CLI wiring for story behavior
- Logging/summary after core flow implementation

---

## Parallel Opportunities

- T010 and T011 can run in parallel after Phase 2 completion
- T017 and T018 can run in parallel after US1 checkpoint
- T024 and T025 can run in parallel during Phase 5

---

## Parallel Example: User Story 1

- Run T010 and T011 together after T009
- Then run T012 and T013 sequentially, followed by T014, T015, T016

## Parallel Example: User Story 2

- Run T017 and T018 together after US1 checkpoint
- Then run T019, T020, T021, and finish with T022

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1 and Phase 2
2. Complete Phase 3 (US1)
3. Validate independently with US1 test criteria

### Incremental Delivery

1. Deliver US1 for first-run genre organization value
2. Deliver US2 for deterministic rerun sync behavior
3. Finish polish and documentation

### Team Parallelization

1. One developer on CLI wiring/logging tasks in src/cli/main.py
2. One developer on sync/retrieval helpers in src/services/tidal_service.py
3. One developer on orchestration logic in src/services/genre_playlist_service.py and related tests
