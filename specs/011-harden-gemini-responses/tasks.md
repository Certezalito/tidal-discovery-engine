# Tasks: Harden Gemini Responses

**Input**: Design documents from `/specs/011-harden-gemini-responses/`
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

**Purpose**: Prepare implementation scaffolding and verify evidence boundaries for Gemini response handling.

- [X] T001 Verify current Gemini weak-response behavior and log boundary evidence in specs/011-harden-gemini-responses/research.md
- [X] T002 [P] Add/align Gemini hardening log event constants in src/lib/logging.py
- [X] T003 [P] Add test module scaffolding for Gemini hardening scenarios in tests/test_gemini_service.py
- [X] T004 [P] Add CLI integration test scaffolding for Gemini hardening + exclude-favorites attribution in tests/test_cli.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared response classification and retry primitives required by all user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Implement Gemini response classification helper for usable/unusable/retryable/fatal states in src/services/gemini_service.py
- [X] T006 Implement API status categorization helper (retryable vs non-retryable) in src/services/gemini_service.py
- [X] T007 Implement single-recovery-retry loop for unusable-empty and retryable-transient outcomes in src/services/gemini_service.py
- [X] T008 Implement normalized Gemini failure outcome builder with actionable remediation text in src/services/gemini_service.py
- [X] T009 [P] Add unit tests for response classification from parsed/candidates/prompt_feedback/finish_reason fields in tests/test_gemini_service.py
- [X] T010 [P] Add unit tests for status-code retry categorization for 429, 5xx, and 4xx terminal conditions in tests/test_gemini_service.py
- [X] T040 [P] Add unit tests for FR-012 fallback behavior on non-retryable statuses (configured fallback vs no fallback) in tests/test_gemini_service.py
- [X] T041 Implement FR-012 fallback handling branch for non-retryable statuses in src/services/gemini_service.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Recover From Weak Gemini Replies (Priority: P1) 🎯 MVP

**Goal**: Retry weak or empty Gemini responses and fail closed with Gemini-specific guidance when recovery is exhausted.

**Independent Test**: Simulate transport-success but unusable/empty Gemini responses and verify single-retry behavior, retry-success continuation, and valid-empty final-failure messaging.

### Tests for User Story 1 ⚠️

- [X] T011 [P] [US1] Add test for transport-success unusable response triggering exactly one recovery retry in tests/test_gemini_service.py
- [X] T012 [P] [US1] Add test for valid-but-empty parsed response retry then success path in tests/test_gemini_service.py
- [X] T013 [P] [US1] Add VR-007 test for valid-but-empty response receiving exactly one recovery retry before Gemini response-handling final failure in tests/test_gemini_service.py
- [X] T014 [P] [US1] Add test for retryable API failures (429/5xx) receiving exactly one recovery retry before final failure in tests/test_gemini_service.py

### Implementation for User Story 1

- [X] T015 [US1] Replace empty-parsed immediate success path with retry-aware handling in src/services/gemini_service.py
- [X] T016 [US1] Enforce exactly one recovery retry for weak responses and retryable API errors in src/services/gemini_service.py
- [X] T017 [US1] Return explicit Gemini failure exception with remediation metadata when retries are exhausted in src/services/gemini_service.py
- [X] T018 [US1] Update Gemini error-to-CLI propagation so failures stop playlist generation immediately in src/cli/main.py
- [X] T019 [US1] Add/update user-facing Gemini failure logging and messaging for weak-response exhaustion in src/cli/main.py
- [X] T020 [US1] Update quickstart behavior and failure examples for weak-response recovery in specs/011-harden-gemini-responses/quickstart.md

**Checkpoint**: User Story 1 should be fully functional and independently testable.

---

## Phase 4: User Story 2 - Keep Exclude-Favorites Behavior Correct (Priority: P2)

**Goal**: Ensure provider-side Gemini failures are not misattributed to favorites filtering while preserving normal exclude-favorites behavior after successful recovery.

**Independent Test**: Run Gemini mode with exclude-favorites enabled under weak-response and recovery-success scenarios; verify cause attribution and exclusion summaries are emitted only after real candidates reach filtering.

### Tests for User Story 2 ⚠️

- [X] T021 [P] [US2] Add CLI test verifying Gemini weak-response failure is reported before exclusion summary output in tests/test_cli.py
- [X] T022 [P] [US2] Add CLI test verifying exclude-favorites filtering runs normally after successful Gemini retry recovery in tests/test_cli.py
- [X] T023 [P] [US2] Add CLI test verifying no misleading exclusion shortfall/zero-candidate attribution on upstream Gemini failure in tests/test_cli.py

### Implementation for User Story 2

- [X] T024 [US2] Gate exclude-favorites summary logging on presence of usable recommendation candidates in src/cli/main.py
- [X] T025 [US2] Ensure Gemini failure path exits before favorites-filter shortfall messaging is emitted in src/cli/main.py
- [X] T026 [US2] Preserve and validate existing exclude-favorites filtering path for recovered Gemini recommendations in src/cli/main.py
- [X] T027 [US2] Align troubleshooting language that differentiates Gemini provider failures from favorites failures in README.md

**Checkpoint**: User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - Preserve Stable Behavior Without Regressions (Priority: P3)

**Goal**: Keep first-attempt-success Gemini runs and non-Gemini modes behaviorally stable.

**Independent Test**: Confirm first-attempt usable Gemini responses keep existing successful output behavior and non-Gemini flows remain unchanged.

### Tests for User Story 3 ⚠️

- [X] T028 [P] [US3] Add regression test verifying first-attempt usable Gemini response path remains unchanged in tests/test_gemini_service.py
- [X] T029 [P] [US3] Add regression test verifying CLI output/playlist creation remains stable for successful Gemini mode in tests/test_cli.py
- [X] T030 [P] [US3] Add regression test verifying non-Gemini modes are unchanged by Gemini hardening in tests/test_cli.py

### Implementation for User Story 3

- [X] T031 [US3] Keep legacy success-path behavior intact while integrating classification/retry primitives in src/services/gemini_service.py
- [X] T032 [US3] Ensure non-Gemini code paths in CLI bypass Gemini hardening logic entirely in src/cli/main.py
- [X] T033 [US3] Add concise regression notes for stable-success and non-Gemini behavior in specs/011-harden-gemini-responses/quickstart.md

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, consistency, and quality checks across all stories.

- [X] T034 [P] Validate terminology consistency for usable response/retry/provider failure across specs/011-harden-gemini-responses/spec.md and specs/011-harden-gemini-responses/quickstart.md
- [X] T035 [P] Validate README troubleshooting examples match implemented Gemini failure categories in README.md
- [X] T036 Run targeted Gemini hardening tests for service and CLI behavior in tests/test_gemini_service.py
- [X] T037 Run targeted Gemini + exclude-favorites attribution tests in tests/test_cli.py
- [X] T038 Run full regression suite for CLI/service paths impacted by Gemini hardening in tests/test_cli.py and tests/test_exclude_favorites.py
- [X] T039 Run lint checks and resolve any new violations in src/services/gemini_service.py and src/cli/main.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phases 3-5)**: Depend on Foundational completion.
- **Polish (Phase 6)**: Depends on completion of the user stories in scope.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Phase 2; no dependency on other user stories.
- **User Story 2 (P2)**: Starts after Phase 2 and depends on US1 retry/failure primitives.
- **User Story 3 (P3)**: Starts after Phase 2 and validates regression safety over US1/US2 integration.

### Within Each User Story

- Write targeted tests first and ensure they fail.
- Implement service/CLI behavior next.
- Update user-facing documentation for changed behavior.
- Re-run targeted tests to confirm story completion.

### Story Completion Order

- US1 (P1) -> US2 (P2) -> US3 (P3)

---

## Parallel Opportunities

- **Setup**: T002, T003, and T004 can run in parallel.
- **Foundational**: T009 and T010 can run in parallel after T005-T008.
- **US1**: T011, T012, T013, and T014 can run in parallel.
- **US2**: T021, T022, and T023 can run in parallel.
- **US3**: T028, T029, and T030 can run in parallel.
- **Polish**: T034 and T035 can run in parallel; T036 and T037 can run in parallel before T038 and T039.

---

## Parallel Example: User Story 1

```bash
# Run US1 test authoring tasks in parallel:
Task T011 in tests/test_gemini_service.py
Task T012 in tests/test_gemini_service.py
Task T013 in tests/test_gemini_service.py
Task T014 in tests/test_gemini_service.py

# After tests fail, implement service and CLI recovery pieces:
Task T015 in src/services/gemini_service.py
Task T018 in src/cli/main.py
```

## Parallel Example: User Story 2

```bash
# Run US2 attribution tests in parallel:
Task T021 in tests/test_cli.py
Task T022 in tests/test_cli.py
Task T023 in tests/test_cli.py

# Then implement logging/attribution guards:
Task T024 in src/cli/main.py
Task T025 in src/cli/main.py
```

## Parallel Example: User Story 3

```bash
# Run US3 regression tests in parallel:
Task T028 in tests/test_gemini_service.py
Task T029 in tests/test_cli.py
Task T030 in tests/test_cli.py

# Then finalize non-regression implementation:
Task T031 in src/services/gemini_service.py
Task T032 in src/cli/main.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate retry and fail-closed Gemini handling independently.
4. Demo/deploy MVP once Gemini weak-response handling is stable.

### Incremental Delivery

1. Deliver US1 to fix the core weak-response bug.
2. Deliver US2 to protect exclude-favorites attribution and behavior.
3. Deliver US3 to lock regression safety for successful and non-Gemini paths.
4. Finish with cross-cutting validation and linting.

### Parallel Team Strategy

1. One engineer completes foundational service classification/retry tasks.
2. After foundation is complete:
   - Engineer A: US1 service recovery and failure messaging.
   - Engineer B: US2 CLI attribution + docs updates.
   - Engineer C: US3 regression tests and non-Gemini safety checks.
3. Merge for final Phase 6 validation.

---

## Notes

- [P] tasks are safe for parallel execution when they touch independent files/concerns.
- Keep task ordering aligned with dependency flow and test-first validation.
- Prefer small commits per task or coherent task group.
- Stop at each story checkpoint to verify independent testability.
