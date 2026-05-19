# Tasks: Exclude Existing Favorite Tracks

**Input**: Design documents from `/specs/010-exclude-favorite-tracks/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include targeted validation tasks for every behavior-changing story.
Pure documentation-only work may use documentation validation tasks instead of
runtime tests when justified in the specification.

**Documentation**: Documentation tasks are REQUIRED for every feature and MUST
cover user-facing behavior changes with clear examples.

**Evidence**: When implementation depends on unknown external facts, include
explicit clarification or source-verification tasks instead of guessing.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare feature branch docs and test scaffolding for implementation.

- [X] T001 Verify and record authoritative favorites retrieval + ISRC evidence in specs/010-exclude-favorite-tracks/research.md
- [X] T002 [P] Create feature test module skeleton in tests/test_exclude_favorites.py
- [X] T003 [P] Add exclusion feature logging event IDs/constants in src/lib/logging.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared exclusion primitives used by all stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Implement identity normalization helpers (ISRC/title/artist) in src/services/tidal_service.py
- [X] T005 Implement complete favorites pagination loader with per-page retry budget in src/services/tidal_service.py
- [X] T006 [P] Implement in-memory favorites snapshot builder (identity key set) in src/services/tidal_service.py
- [X] T007 [P] Implement reusable exclusion filter function for candidate tracks in src/services/tidal_service.py
- [X] T008 Add unit tests for identity normalization and exclusion-key derivation in tests/test_tidal_service.py
- [X] T009 Add unit tests for favorites pagination retry/fail-closed behavior in tests/test_tidal_service.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Discover Only New Music (Priority: P1) 🎯 MVP

**Goal**: Users can enable `--exclude-favorites` and receive playlists with favorite tracks removed while preserving requested count when possible.

**Independent Test**: Run CLI with `--exclude-favorites` and mocked favorites/candidates, then verify no output track matches the favorites set and supplementation is attempted when available.

### Tests for User Story 1 ⚠️

- [X] T010 [P] [US1] Add CLI-path test verifying favorites are excluded when flag is enabled in tests/test_exclude_favorites.py
- [X] T011 [P] [US1] Add CLI-path test verifying supplement behavior fills requested count when extra non-favorite candidates exist in tests/test_exclude_favorites.py
- [X] T012 [P] [US1] Add CLI-path test verifying informative shortfall when all remaining candidates are favorites in tests/test_exclude_favorites.py

### Implementation for User Story 1

- [X] T013 [US1] Add `--exclude-favorites` Click option and parameter plumbing in src/cli/main.py
- [X] T014 [US1] Load favorites snapshot only when exclusion flag is enabled in src/cli/main.py
- [X] T015 [US1] Apply exclusion filter to Gemini candidate resolution flow before playlist creation in src/cli/main.py
- [X] T016 [US1] Apply exclusion filter to Last.fm candidate resolution flow before playlist creation in src/cli/main.py
- [X] T017 [US1] Implement supplementation loop for non-favorite candidates when filtered result is below target in src/cli/main.py
- [X] T018 [US1] Add user-facing warning for partial final playlist when no additional non-favorite candidates exist in src/cli/main.py
- [X] T019 [US1] Update quickstart usage examples for exclusion flag in specs/010-exclude-favorite-tracks/quickstart.md

**Checkpoint**: User Story 1 should be fully functional and independently testable.

---

## Phase 4: User Story 2 - Opt-In Behavior with No Change to Default (Priority: P2)

**Goal**: Default behavior remains unchanged when exclusion option is absent/off.

**Independent Test**: Run CLI without `--exclude-favorites`; verify no favorites-loading function is called and output behavior follows baseline path.

### Tests for User Story 2 ⚠️

- [X] T020 [P] [US2] Add regression test asserting no favorites lookup call when flag is absent in tests/test_exclude_favorites.py
- [X] T021 [P] [US2] Add regression test asserting favorites lookup is never called across default mode, Gemini mode, and single-seed mode when exclusion flag is absent in tests/test_exclude_favorites.py
- [X] T022 [P] [US2] Add regression test that compares deterministic output artifacts with exclusion disabled against pre-feature baseline for identical inputs in tests/test_exclude_favorites.py

### Implementation for User Story 2

- [X] T023 [US2] Gate favorites retrieval behind explicit exclusion flag check in src/cli/main.py
- [X] T024 [US2] Preserve baseline candidate ordering/selection path when exclusion flag is disabled in src/cli/main.py
- [X] T025 [US2] Update CLI help text to clarify optional opt-in semantics for `--exclude-favorites` in src/cli/main.py
- [X] T026 [US2] Add README option documentation and non-exclusion baseline example in README.md

**Checkpoint**: User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - Favorites Fetch Failure Fails Closed (Priority: P3)

**Goal**: Exclusion mode aborts with clear guidance when favorites retrieval fails or is incomplete.

**Independent Test**: Simulate favorites page failure/partial retrieval with retries exhausted and verify clear error output plus no playlist creation.

### Tests for User Story 3 ⚠️

- [X] T027 [P] [US3] Add CLI-path test verifying fail-closed behavior on favorites retrieval failure in tests/test_exclude_favorites.py
- [X] T028 [P] [US3] Add CLI-path test verifying fail-closed behavior on incomplete pagination after retries in tests/test_exclude_favorites.py
- [X] T029 [P] [US3] Add test verifying exclusion mode writes no disk cache artifacts in tests/test_exclude_favorites.py

### Implementation for User Story 3

- [X] T030 [US3] Raise explicit exclusion-mode retrieval error with corrective guidance in src/services/tidal_service.py
- [X] T031 [US3] Convert favorites retrieval errors to ClickException abort path in src/cli/main.py
- [X] T032 [US3] Add structured logging for retry exhaustion and fail-closed abort in src/cli/main.py
- [X] T033 [US3] Add user-facing README troubleshooting guidance for favorites retrieval failures in README.md

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, consistency, and quality checks across all stories.

- [X] T034 [P] Validate README and quickstart terminology consistency for `--exclude-favorites` across README.md and specs/010-exclude-favorite-tracks/quickstart.md
- [X] T035 [P] Run targeted test suite for exclusion feature paths in tests/test_exclude_favorites.py
- [X] T036 Run full regression test suite for CLI + tidal service paths in tests/test_cli.py and tests/test_tidal_service.py
- [X] T037 [P] Run lint checks and resolve any new violations in src/cli/main.py and src/services/tidal_service.py
- [X] T038 Add timed integration validation for favorites exclusion path with a typical library fixture (~2,000 favorites) and assert added runtime is <= 5 seconds in tests/test_exclude_favorites.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phases 3-5)**: Depend on Foundational completion.
- **Polish (Phase 6)**: Depends on completion of the user stories in scope.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Phase 2; no dependency on other user stories.
- **User Story 2 (P2)**: Starts after Phase 2; validates non-flag behavior independently.
- **User Story 3 (P3)**: Starts after Phase 2; focuses on fail-closed error handling independently.

### Within Each User Story

- Write targeted tests first and ensure they fail.
- Implement feature logic next.
- Update user-facing documentation for changed behavior.
- Re-run targeted tests to confirm story completion.

---

## Parallel Opportunities

- **Setup**: T002 and T003 can run in parallel.
- **Foundational**: T006 and T007 can run in parallel after T004/T005.
- **US1**: T010, T011, and T012 can run in parallel.
- **US2**: T020 and T021 can run in parallel.
- **US3**: T026, T027, and T028 can run in parallel.
- **Polish**: T033, T034, and T036 can run in parallel before final regression task T035.

---

## Parallel Example: User Story 1

```bash
# Run US1 test authoring tasks in parallel:
Task T010 in tests/test_exclude_favorites.py
Task T011 in tests/test_exclude_favorites.py
Task T012 in tests/test_exclude_favorites.py

# Then implement both recommendation branches in parallel once plumbing exists:
Task T015 in src/cli/main.py
Task T016 in src/cli/main.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate zero-leak exclusion + supplementation behavior.
4. Demo/deploy MVP if acceptable.

### Incremental Delivery

1. Deliver US1 for immediate end-user value.
2. Deliver US2 to lock regression safety for existing users.
3. Deliver US3 to harden failure-path reliability and guidance.
4. Finish with cross-cutting polish and full regression.

### Parallel Team Strategy

1. One engineer completes foundational service tasks.
2. Then split by story:
   - Engineer A: US1 implementation and tests.
   - Engineer B: US2 regression and docs.
   - Engineer C: US3 failure-path handling and tests.
3. Merge at Phase 6 for full-suite validation.

---

## Notes

- [P] tasks are safe for parallel execution when they touch independent files/concerns.
- Keep task ordering aligned with dependency flow and test-first validation.
- Prefer small commits per task or coherent task group.
- Stop at each story checkpoint to verify independent testability.
