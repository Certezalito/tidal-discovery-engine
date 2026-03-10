# Tasks: Gemini Model Env Configuration

**Input**: Design documents from /specs/006-gemini-model-env/
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: No explicit TDD requirement in the feature spec, so test-writing tasks are not mandated in this task list. Validation is captured through quickstart verification tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare operator-facing configuration artifacts before service-layer changes.

- [x] T001 Create env template entries for GEMINI_API_KEY, GEMINI_MODEL, and GEMINI_FALLBACK_MODEL in .env.example
- [x] T002 Document Gemini model environment variables and precedence overview in README.md
- [x] T003 [P] Sync feature quickstart setup prerequisites with repository usage conventions in specs/006-gemini-model-env/quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared configuration-resolution primitives required by all user stories.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [x] T004 Add model defaults and normalization helpers (trim + empty-to-missing) in src/services/gemini_service.py
- [x] T005 Add primary model resolution routine with precedence env -> .env -> default in src/services/gemini_service.py
- [x] T006 Add startup warning-once guard for default-model usage in src/services/gemini_service.py
- [x] T007 Add provider-error classification helper for model unavailable/not-found detection in src/services/gemini_service.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Configure Model Without Code Edits (Priority: P1) 🎯 MVP

**Goal**: Operators can switch Gemini model IDs via environment settings only.

**Independent Test**: Set GEMINI_MODEL, run a Gemini-backed CLI command, then change GEMINI_MODEL and verify the next run uses the new model without source changes.

### Implementation for User Story 1

- [x] T008 [US1] Replace hardcoded Gemini model argument with resolved primary model in src/services/gemini_service.py
- [x] T009 [US1] Add logging of selected model and source (env/.env/default) in src/services/gemini_service.py
- [x] T010 [P] [US1] Add operator example for runtime model override using exported GEMINI_MODEL in README.md
- [x] T011 [US1] Add US1 verification procedure and expected outcomes in specs/006-gemini-model-env/quickstart.md

**Checkpoint**: User Story 1 is independently functional and testable (MVP).

---

## Phase 4: User Story 2 - Safe Fallback When Config Is Missing (Priority: P2)

**Goal**: Missing or blank primary model config does not break runs and remains backward compatible.

**Independent Test**: Remove or blank GEMINI_MODEL, run a Gemini-backed CLI command, and verify one startup warning plus successful execution via default model.

### Implementation for User Story 2

- [x] T012 [US2] Apply missing/blank primary-model branch to use default model in src/services/gemini_service.py
- [x] T013 [US2] Emit at most one warning per CLI invocation when default primary model is selected in src/services/gemini_service.py
- [x] T014 [P] [US2] Document missing/blank GEMINI_MODEL behavior and compatibility guarantee in README.md
- [x] T015 [US2] Add no-config validation scenario and expected warning behavior in specs/006-gemini-model-env/quickstart.md

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Understand Configuration Errors Quickly (Priority: P3)

**Goal**: Invalid model configuration returns actionable feedback and uses fallback only for unavailable/not-found primary models.

**Independent Test**: Set an invalid primary model; verify actionable error output and fallback behavior only when provider indicates unavailable/not-found.

### Implementation for User Story 3

- [x] T016 [US3] Implement fallback attempt only for unavailable/not-found primary-model responses in src/services/gemini_service.py
- [x] T017 [US3] Prevent fallback on auth/quota/permission failures and emit actionable configuration errors containing model ID, failure category, and corrective guidance in src/services/gemini_service.py
- [x] T018 [P] [US3] Document invalid-model troubleshooting and non-fallback error boundaries in README.md
- [x] T019 [US3] Add invalid-model and fallback-boundary verification scenarios in specs/006-gemini-model-env/quickstart.md

**Checkpoint**: All user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final alignment, verification, and release readiness.

- [x] T020 [P] Align contract wording with implemented behavior in specs/006-gemini-model-env/contracts/gemini-model-env-contract.md
- [x] T021 [P] Run end-to-end quickstart walkthrough and capture final notes in specs/006-gemini-model-env/quickstart.md
- [x] T022 Run project quality checks and document outcomes using the quickstart verification evidence template in specs/006-gemini-model-env/quickstart.md
- [x] T023 Compare baseline vs post-change behavior with GEMINI_MODEL and GEMINI_FALLBACK_MODEL unset; record parity evidence using the quickstart verification evidence template in specs/006-gemini-model-env/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): no dependencies.
- Foundational (Phase 2): depends on Phase 1 and blocks all user stories.
- User Stories (Phases 3-5): depend on Phase 2 completion.
- Polish (Phase 6): depends on completion of desired user stories.

### User Story Dependencies

- US1 (P1): starts after Phase 2; no dependency on other user stories.
- US2 (P2): starts after Phase 2; functionally independent from US1.
- US3 (P3): starts after Phase 2; functionally independent from US1 and US2.

### Recommended Delivery Order

- MVP: Phase 1 -> Phase 2 -> Phase 3 (US1).
- Incremental: add Phase 4 (US2), then Phase 5 (US3), then Phase 6 polish.

## Parallel Opportunities

- Setup: T003 can run in parallel with T001-T002.
- Foundational: T006 and T007 can proceed in parallel after T004-T005 scaffolding is in place.
- US1: T010 can run in parallel with T008-T009.
- US2: T014 can run in parallel with T012-T013.
- US3: T018 can run in parallel with T016-T017.
- Polish: T020 and T021 can run in parallel before T022-T023.

## Parallel Example: User Story 1

- Run T008 and T009 sequentially in src/services/gemini_service.py.
- Run T010 in README.md in parallel once model-source behavior is stable.
- Complete T011 after implementation to validate the story independently.

## Parallel Example: User Story 2

- Execute T012 and T013 in src/services/gemini_service.py.
- Execute T014 in README.md concurrently.
- Finalize T015 in quickstart with validation evidence.

## Parallel Example: User Story 3

- Implement T016 and T017 in src/services/gemini_service.py.
- Document T018 in README.md concurrently.
- Finalize T019 with reproducible verification steps.

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate US1 independently using quickstart steps.
4. Demo/deploy MVP.

### Incremental Delivery

1. Add US2 (Phase 4), validate, demo/deploy.
2. Add US3 (Phase 5), validate, demo/deploy.
3. Complete Phase 6 polish and final checks.

### Team Parallelization

1. Collaborate on Phase 1 and Phase 2.
2. After foundation, assign US1/US2/US3 to different developers.
3. Merge each story after independent verification.
