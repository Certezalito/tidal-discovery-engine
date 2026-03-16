# Tasks: Gemini Support for Single-Seed Mode

**Input**: Design documents from `/specs/007-gemini-mode3-support/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Automated test tasks are intentionally omitted because the feature specification did not explicitly request TDD or mandatory new test creation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare feature documentation and command examples needed before implementation.

- [X] T001 Baseline-audit existing Mode 3 quickstart coverage before feature edits in `specs/007-gemini-mode3-support/quickstart.md`
- [X] T002 Baseline-audit existing README Mode 3 coverage before feature edits in `README.md`
- [X] T003 [P] Record requirement-to-task traceability notes (FR-001 through FR-017) for auditability in `specs/007-gemini-mode3-support/research.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core CLI/service scaffolding that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Introduce/adjust Mode 3 Gemini route selection entry points in `src/cli/main.py`
- [X] T005 [P] Add request-normalization helper structure for single-seed Gemini context in `src/services/gemini_service.py`
- [X] T006 [P] Add reusable skipped-track warning formatter (count + first five names) in `src/lib/logging.py`
- [X] T007 Wire Mode 3 playlist insertion outcome handling surface for partial-success reporting in `src/services/tidal_service.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Generate single-seed playlist with Gemini (Priority: P1) 🎯 MVP

**Goal**: Enable Mode 3 (`--artist` + `--track`) to use Gemini recommendations while preserving non-Gemini Mode 3 behavior.

**Independent Test**: Run Mode 3 command with `--artist`, `--track`, and `--gemini` and verify playlist creation from Gemini path; run the same command without `--gemini` and verify baseline non-Gemini behavior remains.

### Implementation for User Story 1

- [X] T008 [US1] Implement Mode 3 + `--gemini` orchestration branch in `src/cli/main.py`
- [X] T009 [US1] Implement single-seed Gemini recommendation generation using artist/track text context in `src/services/gemini_service.py`
- [X] T010 [US1] Integrate Gemini Mode 3 recommendation flow into playlist creation pipeline in `src/services/tidal_service.py`
- [X] T011 [US1] Ensure non-Gemini Mode 3 code path remains unchanged when `--gemini` is not provided in `src/cli/main.py`
- [X] T012 [US1] Add operator-facing logs for Mode 3 Gemini execution start/end status in `src/cli/main.py`
- [X] T013 [US1] Update Mode 3 README usage and parameter semantics for `--gemini` and `--gemini --shuffle` in `README.md`
- [X] T014 [US1] Update Mode 3 Gemini quickstart examples and verification expectations in `specs/007-gemini-mode3-support/quickstart.md`

**Checkpoint**: User Story 1 is fully functional and testable as an MVP increment.

---

## Phase 4: User Story 2 - Deep-cuts behavior in single-seed Gemini mode (Priority: P2)

**Goal**: Support `--shuffle` in Mode 3 Gemini as deep-cuts intent, consistent with existing Gemini semantics.

**Independent Test**: Run Mode 3 with `--artist`, `--track`, `--gemini`, and `--shuffle`; verify deep-cuts intent is used and output remains valid.

### Implementation for User Story 2

- [X] T015 [US2] Apply deep-cuts prompt/intention selection for Mode 3 when `--shuffle` is enabled in `src/services/gemini_service.py`
- [X] T016 [US2] Pass Mode 3 shuffle intent flags through CLI orchestration into Gemini service calls in `src/cli/main.py`
- [X] T017 [US2] Ensure Mode 3 non-shuffle Gemini behavior remains standard intent in `src/services/gemini_service.py`
- [X] T018 [US2] Add concise deep-cuts mode logging marker for Mode 3 runs in `src/cli/main.py`

**Checkpoint**: User Stories 1 and 2 work independently and together.

---

## Phase 5: User Story 3 - Validation and resilient failure handling (Priority: P3)

**Goal**: Provide robust validation, best-effort recommendation counts, and partial-success behavior with clear skipped-track warnings.

**Independent Test**: Validate missing artist/track pair rejection, constrained recommendation best-effort output, and unresolved-track skip warnings (count + first five names).

### Implementation for User Story 3

- [X] T019 [US3] Enforce paired `--artist` and `--track` validation in Gemini Mode 3 command path in `src/cli/main.py`
- [X] T020 [US3] Implement best-effort recommendation cap logic bounded by `--num-similar-tracks` in `src/services/gemini_service.py`
- [X] T021 [US3] Implement unresolved-track skip-and-continue insertion handling in `src/services/tidal_service.py`
- [X] T022 [US3] Emit skipped-track warning containing skipped count and up to first five names in `src/cli/main.py`
- [X] T023 [US3] Ensure Gemini model/provider failures in Mode 3 return actionable error output aligned with existing behavior in `src/services/gemini_service.py`
- [X] T024 [US3] Enforce Mode 3 fallback boundary behavior in `src/services/gemini_service.py` so fallback occurs only for unavailable or not-found model failures.
- [X] T025 [US3] Enforce no-fallback behavior for auth, quota, and permission failures in `src/services/gemini_service.py` while preserving actionable error fields.
- [X] T026 [US3] Implement explicit zero-inserted outcome handling as failure status in `src/services/tidal_service.py`.
- [X] T027 [US3] Add `--num-similar-tracks` non-positive validation path in `src/cli/main.py` with corrective message.

**Checkpoint**: All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency updates and operator validation.

- [X] T028 [P] Verify README Mode 3 Gemini docs remain synchronized with implemented behavior in `README.md`
- [X] T029 [P] Verify quickstart scenarios remain synchronized with implemented behavior in `specs/007-gemini-mode3-support/quickstart.md`
- [X] T030 Run manual quickstart validation steps and record outcomes in `specs/007-gemini-mode3-support/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories
- **User Story Phases (Phase 3-5)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on completion of all target user stories

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Phase 2; no dependency on other stories
- **User Story 2 (P2)**: Starts after Phase 2; depends functionally on Gemini Mode 3 path from US1
- **User Story 3 (P3)**: Starts after Phase 2; can be implemented after US1 route is in place for failure-path alignment

### Within Each User Story

- CLI wiring before end-to-end integration
- Gemini generation updates before Tidal insertion handling
- Output and logging refinements after core behavior is implemented

### Parallel Opportunities

- Phase 1: T003 can run in parallel with T001-T002
- Phase 2: T005-T006 can run in parallel after T004 starts; T007 can proceed once service interfaces are stable
- Story phases: intra-story tasks marked [P] are intentionally limited to avoid same-file merge conflicts
- Phase 6: T028 and T029 can run in parallel

---

## Parallel Example: User Story 1

```bash
# After foundational completion, split work across files:
Task: "Implement single-seed Gemini recommendation generation using artist/track text context in src/services/gemini_service.py"
Task: "Integrate Gemini Mode 3 recommendation flow into playlist creation pipeline in src/services/tidal_service.py"
```

---

## Parallel Example: User Story 3

```bash
# Failure-path and insertion handling can be worked in tandem:
Task: "Implement best-effort recommendation cap logic bounded by --num-similar-tracks in src/services/gemini_service.py"
Task: "Implement unresolved-track skip-and-continue insertion handling in src/services/tidal_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate independent Mode 3 + Gemini standard flow.
4. Demo/deploy MVP increment.

### Incremental Delivery

1. Deliver US1 for baseline Mode 3 Gemini support.
2. Add US2 for deep-cuts behavior with `--shuffle`.
3. Add US3 for robust validation and resilient partial-success behavior.
4. Finish with documentation and quickstart verification.

### Parallel Team Strategy

1. One developer updates CLI orchestration in `src/cli/main.py`.
2. One developer implements Gemini generation behavior in `src/services/gemini_service.py`.
3. One developer implements insertion resilience in `src/services/tidal_service.py`.
4. Documentation tasks proceed in parallel during polish phase.

---

## Notes

- [P] tasks indicate parallelizable work in different files.
- [USx] labels map every story-phase task directly to its user story.
- Each user story is independently testable through the stated CLI command flows.
- Preserve backward compatibility for non-Gemini Mode 3 behavior while adding Gemini support.
