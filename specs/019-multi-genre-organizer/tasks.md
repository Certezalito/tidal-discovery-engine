# Tasks: Multi-Genre Track Organization & Folder Wipe

**Feature Branch**: `019-multi-genre-organizer`  
**Input Specifications**: [`specs/019-multi-genre-organizer/spec.md`](spec.md), [`specs/019-multi-genre-organizer/plan.md`](plan.md), [`specs/019-multi-genre-organizer/data-model.md`](data-model.md), [`specs/019-multi-genre-organizer/contracts/cli-contract.md`](contracts/cli-contract.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify dependencies and test environment readiness

- [x] T001 Verify virtual environment and test dependencies in `.venv/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema migration and cache service extensions that block all user stories

**⚠️ CRITICAL**: Must complete before user story implementation can begin

- [x] T002 Update database schema migration to add `sub_genres TEXT` column to `track_genre_cache` in `src/lib/db.py`
- [x] T003 Update `GenreCacheService` methods (`get_cached_genres`, `save_track_genres`) for JSON `sub_genres` serialization in `src/services/genre_cache_service.py`
- [x] T004 [P] Add unit tests for `sub_genres` column persistence and backwards compatibility in `tests/test_genre_cache_service.py`

**Checkpoint**: Database and cache service support multi-genre storage.

---

## Phase 3: User Story 1 - Multi-Genre Classification and Persistent Caching (Priority: P1) 🎯 MVP

**Goal**: Query Gemini for 1 primary genre and up to 3 specific sub-genres (excluding broad umbrella tags) and persist them in the local SQLite cache.

**Independent Test**: Classify a sample track (e.g., "Foals - Tron") and assert that both `primary_genre` ("Math Rock") and `sub_genres` (["Dance-Punk", "Post-Punk Revival"]) are returned and saved to `data/genre_cache.db`.

### Tests for User Story 1
- [x] T005 [P] [US1] Add unit tests for Gemini multi-genre structured JSON schema and prompt output parsing in `tests/test_gemini_service.py`

### Implementation for User Story 1
- [x] T006 [US1] Update `GenreClassificationResult` Pydantic model with `primary_genre` and `sub_genres: list[str]` in `src/services/gemini_service.py`
- [x] T007 [US1] Update `classify_tracks_genres` prompt to forbid broad umbrella categories and extract up to 3 sub-genres in `src/services/gemini_service.py`
- [x] T008 [US1] Integrate `sub_genres` handling into the classification batch loop in `src/services/genre_organizer_service.py`

**Checkpoint**: Tracks are classified into primary and sub-genres and cached locally.

---

## Phase 4: User Story 2 - Multi-Playlist Distribution for Qualifying Genres (Priority: P1)

**Goal**: Assign each track to its primary genre playlist AND each of its qualifying sub-genre playlists, deduplicating track additions so that tracks appear in multiple relevant playlists.

**Independent Test**: Run playlist grouping on tracks with multiple genres and verify that each track ID is present in all its corresponding qualifying genre buckets.

### Tests for User Story 2
- [x] T009 [P] [US2] Add unit tests for multi-playlist grouping and track deduplication across primary and sub-genres in `tests/test_genre_playlist_service.py`

### Implementation for User Story 2
- [x] T010 [US2] Refactor genre grouping logic in `src/services/genre_organizer_service.py` to map each track to both its `primary_genre` and all `sub_genres`
- [x] T011 [US2] Update playlist synchronization diffing to idempotently update all primary and sub-genre playlists in `src/services/genre_organizer_service.py`

**Checkpoint**: Tracks are distributed across qualifying primary and sub-genre playlists in Tidal.

---

## Phase 5: User Story 3 - Thresholding and Minimum Genre Size Enforcement (Priority: P1)

**Goal**: Enforce a default minimum genre size of 5 tracks (`--min-genre-size 5`) and suppress standalone playlist creation for any primary or sub-genre with fewer than 5 tracks. Primary genres < 5 tracks are grouped into "Others"; sub-genres < 5 tracks are suppressed.

**Independent Test**: Verify that in a library with primary genres (e.g. 6 tracks, 2 tracks) and sub-genres (e.g. 5 tracks, 1 track), dedicated playlists are created ONLY for genres with >= 5 tracks, primary genres with 2 tracks route to "Others", and NO standalone playlist is created for 1-track sub-genres.

### Tests for User Story 3
- [x] T012 [P] [US3] Update unit tests in `tests/test_genre_playlist_service.py` verifying sub-genres < `--min-genre-size` are suppressed and genres >= `--min-genre-size` receive dedicated playlists
- [x] T013 [P] [US3] Update CLI tests in `tests/test_cli_genre_organizer.py` and `tests/test_cli.py` to verify `--min-genre-size` defaults to 5

### Implementation for User Story 3
- [x] T014 [US3] Update thresholding logic in `src/services/genre_organizer_service.py` so sub-genres with fewer than `min_genre_size` tracks are suppressed from playlist creation
- [x] T015 [US3] Update `--min-genre-size` default from 10 to 5 in `src/cli/main.py`

**Checkpoint**: Default threshold is 5, and all sub-threshold genre playlists (< 5 tracks) are strictly suppressed.

---

## Phase 6: User Story 4 - Clean-Slate Target Folder Wiping (Priority: P2)

**Goal**: Provide an opt-in folder wipe capability (`--wipe-folder` / `--wipe` and `--wipe-only` with `--yes` / `-y` override) that deletes all existing playlists inside the designated Tidal folder while keeping the folder container intact for fresh playlist generation.

**Independent Test**: Run `organize` with `--wipe-folder --yes` on a folder containing existing playlists, and verify that all pre-existing playlists are deleted and new genre playlists are created inside the same folder container.

### Tests for User Story 4
- [x] T019 [P] [US4] Add unit tests in `tests/test_genre_playlist_service.py` verifying `run_genre_organizer_sync` wipes all existing playlists in the target folder when `wipe_folder=True` or `wipe_only=True` and populates `summary.playlists_wiped`
- [x] T020 [P] [US4] Add CLI unit tests in `tests/test_cli_genre_organizer.py` verifying `--wipe-folder`, `--wipe`, `--wipe-only`, `--yes` / `-y`, and interactive confirmation prompts (including abort on 'n')

### Implementation for User Story 4
- [x] T021 [US4] Update `GenreRunSummary` in `src/services/genre_organizer_service.py` to include `playlists_wiped: int = 0`
- [x] T022 [US4] Implement folder wipe and wipe-only execution logic in `src/services/genre_organizer_service.py` to delete playlists via `delete_playlist(session, pl.id)` while reusing the target folder container
- [x] T023 [US4] Add `--wipe-folder`, `--wipe`, `--wipe-only`, and `--yes` / `-y` flags with interactive confirmation handling in `src/cli/main.py`
- [x] T024 [US4] Update CLI summary display in `src/cli/main.py` to report `Playlists Wiped:` when $> 0$

**Checkpoint**: Folders can be safely wiped clean on demand, interactively or via automated scripts, with accurate reporting.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, end-to-end validation, and full test suite verification

- [x] T025 [P] Update `README.md` to document `--wipe-folder` / `--wipe`, `--wipe-only`, and `--yes` / `-y` flags with usage examples
- [x] T026 Update and execute validation scenarios in `specs/019-multi-genre-organizer/quickstart.md`
- [x] T027 Run complete regression test suite via `pytest tests/` to verify all 4 user stories

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Complete [x].
- **Foundational (Phase 2)**: Complete [x].
- **User Story 1 (Phase 3)**: Complete [x].
- **User Story 2 (Phase 4)**: Complete [x].
- **User Story 3 (Phase 5)**: Complete [x].
- **User Story 4 (Phase 6)**: Builds on existing organizer sync pipeline; can proceed immediately.
- **Polish (Phase 7)**: Depends on User Story 4 completion.

### User Story Dependencies
- **User Story 4**: Operates directly on Tidal folder playlist resolution and sync in `genre_organizer_service.py` and `main.py`.

### Parallel Opportunities
- T019 and T020 can be implemented in parallel (service tests vs CLI tests).
- T021 and T022 can be implemented sequentially (model then service logic).
- T025 (README documentation) can proceed in parallel with test and implementation tasks.

---

## Parallel Example: User Story 4

```bash
# Launch test creation for User Story 4 in parallel:
Task: "Add unit tests in tests/test_genre_playlist_service.py"
Task: "Add CLI unit tests in tests/test_cli_genre_organizer.py"

# Launch documentation updates in parallel:
Task: "Update README.md with folder wipe options"
```

---

## Implementation Strategy

### Incremental Delivery
1. Add service-level and CLI-level tests for folder wiping (T019, T020).
2. Update `GenreRunSummary` model with `playlists_wiped` (T021).
3. Implement folder wipe & wipe-only in `genre_organizer_service.py` (T022).
4. Add CLI flags and confirmation prompt in `src/cli/main.py` (T023).
5. Update CLI summary table output (T024).
6. Update `README.md` and execute quickstart scenarios (T025, T026).
7. Run complete test suite to ensure zero regressions (T027).
