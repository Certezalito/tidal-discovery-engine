# Implementation Tasks: Dedicated Radio CLI Command

**Branch**: `016-single-seed-track` | **Spec**: [specs/016-single-seed-track/spec.md](spec.md) | **Plan**: [specs/016-single-seed-track/plan.md](plan.md)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Register stable telemetry codes and helper formatting utilities needed across all single-seed radio flows.

- [X] T001 Define warning log constants (`RADIO_UNRESOLVED_TRACKS`, `SEED_NOT_RESOLVED_ON_TIDAL`) in `src/lib/logging.py`
- [X] T002 [P] Add seed track playlist description formatting utility with 500-char safety bounding in `src/services/tidal_service.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core orchestration refactoring that MUST be complete before user story implementation can begin.

**⚠️ CRITICAL**: Extracts existing single-seed pipeline wiring into a dedicated helper so `radio` can execute cleanly.

- [X] T003 Extract single-seed recommendation orchestration into reusable `generate_track_radio` function in `src/cli/main.py`
- [X] T004 [P] Implement input argument normalization and validation helper (whitespace trimming, positive count check) in `src/cli/main.py`

**Checkpoint**: Foundation ready — `generate_track_radio` is available for direct CLI wiring.

---

## Phase 3: User Story 1 - Dedicated `radio` CLI Command & Ergonomic Defaults (Priority: P1) 🎯 MVP

**Goal**: Enable listeners to generate a track radio playlist using a dedicated, ergonomic command (`radio`), defaulting `--playlist-name` to `"{artist} - {track} Radio"`, defaulting total count to 50 (1 seed + 49 recommendations), placing the seed track at Track #1, documenting seed info in playlist description metadata, and validating inputs.

**Independent Test**: Execute `python -m src.cli.main radio --artist "Underworld" --track "Born Slippy"` and verify that a 50-track playlist named `"Underworld - Born Slippy Radio"` is created with `"Born Slippy"` as Track #1 followed by 49 recommendations and seed metadata in its description.

### Tests for User Story 1 ⚠️

- [X] T005 [P] [US1] Add CLI unit tests in `tests/test_cli.py` for `radio` command with seed track placed as Track #1, default playlist naming, default total track count of 50 (1 seed + 49 recommendations), dynamic `{date}` token replacement, and seed info in playlist description
- [X] T006 [P] [US1] Add CLI unit tests in `tests/test_cli.py` for input validation errors (empty/whitespace artist/track, non-positive count, zero resolved tracks)

### Implementation for User Story 1

- [X] T007 [US1] Ensure `@cli.command("radio")` is strictly registered as `radio` and remove `track-radio` alias registration in `src/cli/main.py`
- [X] T008 [US1] Wire default playlist naming (`f"{artist} - {track} Radio"`), dynamic `{date}` token replacement, default 50 total tracks (1 seed + 49 recommendations), and resolved seed track prepending at Track #1 into `generate_track_radio` in `src/cli/main.py`
- [X] T009 [US1] Implement unresolvable track skipping with capped warning preview (up to 5 tracks), seed resolution fallback warning, and zero-track insertion failure in `src/cli/main.py`

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently (MVP Complete).

---

## Phase 4: User Story 2 - Advanced Radio Options Parity (Priority: P2)

**Goal**: Bring full feature parity to `radio` by integrating Google Gemini AI recommendations (`--gemini`), deep cuts (`--shuffle`), Tidal library favorites exclusion (`--exclude-favorites`), folder organization (`--folder`), and graceful fallback when Gemini is unavailable.

**Independent Test**: Execute `python -m src.cli.main radio --artist "Burial" --track "Archangel" --gemini --shuffle --exclude-favorites --folder "Electronic Stations"` and verify Track #1 seed placement, deep-cut AI recommendations, favorites exclusion filtering, and folder assignment.

### Tests for User Story 2 ⚠️

- [X] T010 [P] [US2] Add CLI unit tests in `tests/test_cli.py` for `radio` with `--gemini`, `--shuffle` (deep cuts), `--exclude-favorites`, and `--folder` flags
- [X] T011 [P] [US2] Add CLI unit tests in `tests/test_cli.py` for Gemini model unavailable fallback to Last.fm in `radio`

### Implementation for User Story 2

- [X] T012 [US2] Wire `--gemini`, `--shuffle`, `--exclude-favorites`, and `--folder` options into `@cli.command("radio")` in `src/cli/main.py`
- [X] T013 [US2] Integrate favorites exclusion filtering and folder placement logic within `generate_track_radio` in `src/cli/main.py`
- [X] T014 [US2] Implement Gemini model unavailable fallback to Last.fm with warning logging in `generate_track_radio` in `src/cli/main.py`

**Checkpoint**: At this point, User Stories 1 AND 2 work independently with full feature parity.

---

## Phase 5: User Story 3 - Clean Command Separation: Dedicated Discovery for Library vs. Seed Track (Priority: P3)

**Goal**: Establish a clean separation of concerns between commands: `recommend` is dedicated solely to library-favorite discovery, and single-seed parameters (`--artist` and `--track`) are removed from `recommend`.

**Independent Test**: Verify that `recommend --help` and CLI invocations reject `--artist` and `--track` with Click usage errors, while standard library recommendation continues to function.

### Tests for User Story 3 ⚠️

- [X] T015 [P] [US3] Add CLI unit tests in `tests/test_cli.py` verifying that `recommend` rejects `--artist` and `--track` options and that `track-radio` is unrecognized
- [X] T016 [P] [US3] Verify that standard library recommendation flow in `recommend` executes without single-seed parameters in `tests/test_cli.py`

### Implementation for User Story 3

- [X] T017 [US3] Remove `--artist` and `--track` CLI options and single-seed handling logic from `@cli.command("recommend")` in `src/cli/main.py`

**Checkpoint**: All user stories are functional and strict command separation is enforced.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-user documentation updates and end-to-end validation.

- [X] T018 [P] Update `README.md` to document commands and parameter tables in the strict order: `recommend`, `radio`, `genre-playlist`, removing `track-radio` alias and removing `--artist`/`--track` from `recommend`
- [X] T019 [P] Run automated test suite across all CLI test files via `uv run pytest tests/test_cli.py`
- [X] T020 Execute manual quickstart validation scenarios from `specs/016-single-seed-track/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — complete.
- **Foundational (Phase 2)**: Depends on Setup completion — complete.
- **User Stories (Phase 3+)**: Depend on Foundational phase completion.
  - User Story 1 (P1): Core `radio` command, Track #1 placement, and default options.
  - User Story 2 (P2): Extends `radio` with AI, deep cuts, favorites exclusion, and folders.
  - User Story 3 (P3): Clean separation of concerns; eliminates single-seed flags from `recommend`.
- **Polish (Phase 6)**: Depends on user story implementations being completed.

### User Story Dependencies

- **User Story 1 (P1)**: Core `radio` command, strictly registered without alias.
- **User Story 2 (P2)**: Extends `radio` with AI, deep cuts, favorites exclusion, and folders.
- **User Story 3 (P3)**: Isolates `recommend` to library favorites only.

### Parallel Opportunities

- Within US3: T015 (test) can run before T017 (implementation).
- Within Polish: T018 (docs) and T019 (test suite) can run in parallel once T007, T015, and T017 are complete.

---

## Parallel Example: User Story 3

```bash
# Launch test creation for User Story 3 in parallel:
Task: "Add CLI unit tests in tests/test_cli.py verifying that recommend rejects --artist and --track options and that track-radio is unrecognized"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1: Setup (`src/lib/logging.py`, `src/services/tidal_service.py`).
2. Complete Phase 2: Foundational (`src/cli/main.py` pipeline extraction).
3. Complete Phase 3: User Story 1 (Command `radio`, Track #1 placement, default 50 limit).
4. **VALIDATE**: Run `pytest tests/test_cli.py -k radio` to verify MVP completion.

### Incremental Delivery
1. Phase 4 (US2): Advanced options (`--gemini`, `--shuffle`, `--exclude-favorites`, `--folder`).
2. Phase 5 (US3): Strict separation on `recommend` (removal of legacy flags).
3. Phase 6 (Polish): README documentation ordered `recommend` -> `radio` -> `genre-playlist` and full test suite verification.
