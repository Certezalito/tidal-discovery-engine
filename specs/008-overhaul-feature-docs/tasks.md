# Tasks: Documentation Overhaul

**Input**: Design documents from `/specs/008-overhaul-feature-docs/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Not requested — tasks do not include test phases.

**Documentation**: REQUIRED — this feature IS the documentation; all tasks produce or validate README.md content.

**Organization**: Tasks grouped by user story. No code changes — all deliverables are Markdown files.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (independent content, no shared blockers)
- **[Story]**: US1 / US2 / US3 per spec.md priority order
- No story label = Setup or Foundational phase task

---

## Phase 1: Setup (Inventory & Context)

**Purpose**: Understand current state before writing any new content.

- [x] T001 Read and inventory all current top-level sections and their content in `README.md` — note what exists, what is outdated, and what can be preserved
- [x] T002 [P] Read `src/cli/main.py` and extract the authoritative list of all CLI options, their defaults, mode applicability, and required option pairs (source of truth for T009)

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Establish the 5-section README skeleton — MUST be complete before any user story content is written.

**⚠️ CRITICAL**: No user story work (Phase 3+) can begin until T003 is done.

- [x] T003 Rewrite `README.md` top-level structure to exactly: Setup → Modes → All Parameters → Troubleshooting → Scheduling — preserve any reusable content under the correct section heading, remove or relocate misplaced content

**Checkpoint**: README skeleton with correct section order exists — user story implementation can now begin

---

## Phase 3: User Story 1 — Find The Right Command Fast (Priority: P1) 🎯 MVP

**Goal**: README has clear mode-by-mode usage and a complete parameter reference so users can identify and run the correct command without trial and error.

**Independent Test**: Give the updated README to a user unfamiliar with recent features; they can run one valid command for each mode without external help.

### Implementation for User Story 1

- [x] T004 [US1] Write the Setup section in `README.md`: prerequisites, environment variables, credential setup, session file location, and install/run commands — all steps must be verifiably runnable
- [x] T005 [P] [US1] Write the Mode 1 subsection in `README.md`: mode intent in plain language, two runnable command examples (one without `--shuffle` and one with `--shuffle`), and expected outcome statements for both paths [Spec §FR-002, §DR-002]
- [x] T006 [P] [US1] Write the Mode 2 subsection in `README.md`: mode intent in plain language, two runnable command examples using `--gemini` (one without `--shuffle` and one with `--shuffle`), and expected outcome statements for both paths [Spec §FR-002, §DR-002]
- [x] T007 [P] [US1] Write the Mode 3 subsection in `README.md`: mode intent, explicit statement that `--artist` AND `--track` are both required together, at least one runnable command example, and expected outcome statement [Spec §FR-002, §FR-003, §DR-002]
- [x] T008 [US1] Add a quick-start summary at the top of the Modes section in `README.md` covering the most common use case with a single concrete command (distinct from the detailed per-mode subsections) [Spec §FR-006]
- [x] T009 [US1] Write the All Parameters section in `README.md` as the single authoritative option reference: every option with purpose, default, mode applicability, and required pairings — no option defaults or constraints defined anywhere else in README [Spec §FR-005]

**Checkpoint**: User Story 1 complete — a user can read the Modes + All Parameters sections and execute a valid command for each mode

---

## Phase 4: User Story 2 — Understand Failure and Recovery (Priority: P2)

**Goal**: Troubleshooting section documents at least two failure categories as structured prose entries with symptoms, explanation, and corrective action.

**Independent Test**: A user can locate remediation steps for a Gemini model-unavailable error and a missing-required-options error using the README only.

### Implementation for User Story 2

- [x] T010 [US2] Write the Troubleshooting entry for Gemini model-unavailable error in `README.md`: observed symptoms, behavioral explanation, explicit fallback-or-no-fallback statement, and corrective action the user can take [Spec §FR-004, §DR-003]
- [x] T011 [P] [US2] Write the Troubleshooting entry for Mode 3 missing required option pair in `README.md`: observed symptoms, explanation that both `--artist` and `--track` must be provided together, and a corrected command example as corrective action [Spec §FR-004, §FR-003]
- [x] T012 [P] [US2] Write the Troubleshooting entry for authentication or quota failure in `README.md`: observed symptoms, explanation of the fallback boundary (auth/quota errors do NOT trigger fallback), and corrective action [Spec §FR-004, §DR-003]

**Checkpoint**: User Story 2 complete — Troubleshooting section has ≥ 2 structured prose entries covering failure and fallback scenarios

---

## Phase 5: User Story 3 — Keep Documentation Consistent Over Time (Priority: P3)

**Goal**: Scheduling section complete, terminology consistent across all sections, and docs-update.md checklist validated as usable for future feature work.

**Independent Test**: A maintainer can follow `docs-update.md` for a hypothetical new feature and know exactly which README sections to update.

### Implementation for User Story 3

- [x] T013 [US3] Write the Scheduling section in `README.md`: unattended execution guidance and at least one concrete scheduler command example (e.g., cron) [Spec §FR-001, §DR-002]
- [x] T014 [US3] Audit entire `README.md` for consistent terminology — verify canonical terms for Mode 1/2/3, all flag names (e.g., `--gemini`, `--shuffle`, `--artist`, `--track`), and outcomes (deep cuts, fallback) are used identically across every section [Spec §FR-007, §DR-004]
- [x] T015 [P] [US3] Open `specs/008-overhaul-feature-docs/checklists/docs-update.md` and verify all 18 checklist items (DOC-001–DOC-018) map accurately to the final README sections — update any item that references a section title or concept that changed during implementation [Spec §DR-005]
- [x] T016 [US3] Make a final pass on `README.md`: confirm top-level section order is exactly Setup → Modes → All Parameters → Troubleshooting → Scheduling, no section duplicates normative guidance owned by another section, and zero contradictory statements exist [Spec §FR-001, §SC-003, §DR-004]

**Checkpoint**: All three user stories complete — README is structured, consistent, and the maintainer checklist is validated

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against acceptance criteria and peer review gate.

- [x] T017 [P] Run all six validation steps in `specs/008-overhaul-feature-docs/quickstart.md` against the updated `README.md` and confirm each expected result is met
- [x] T020 [US3] Perform an explicit contradiction audit between `README.md` and `specs/008-overhaul-feature-docs/quickstart.md` for mode names, option names, defaults/constraints, and fallback behavior; document pass/fail and required corrections before reviewer sign-off [Spec §SC-003]
- [ ] T018 Obtain peer review sign-off from maintainer reviewer #1 in `specs/008-overhaul-feature-docs/checklists/docs-update.md` DOC-017: confirms command-path clarity for all modes
- [ ] T019 [P] Obtain peer review sign-off from maintainer reviewer #2 in `specs/008-overhaul-feature-docs/checklists/docs-update.md` DOC-018: confirms absence of contradictory guidance and troubleshooting completeness
- [x] T021 [US3] Record the SC-004 follow-up gate in `specs/008-overhaul-feature-docs/checklists/docs-update.md` notes: on the next feature PR, maintainer reviewer #1 must verify checklist completion evidence and section updates before merge [Spec §SC-004, §DR-005]

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T001 and T002 can run in parallel
- **Foundational (Phase 2)**: Depends on Phase 1 — T003 BLOCKS all user story phases
- **User Story Phases (3, 4, 5)**: All depend on T003 — can proceed in any order or in parallel once T003 is done
- **Polish (Phase 6)**: Depends on all user story phases being complete

### User Story Dependencies

- **US1 (Phase 3)**: Starts after T003 — no dependency on US2 or US3
- **US2 (Phase 4)**: Starts after T003 — no dependency on US1 or US3
- **US3 (Phase 5)**: T013 starts after T003; T014 and T016 should run after US1 and US2 are complete (needs full README to audit); T015 can run anytime after T003

### Within Each User Story

- US1: T004 (Setup section) → independent of T005/T006/T007; T008 (quick-start) depends on T005+T006+T007; T009 (All Parameters) depends on T002
- US2: T010, T011, T012 can all be written in parallel (separate failure entries)
- US3: T013 independent; T014 + T016 should be last (full-README audit); T015 independent

### Parallel Opportunities Per Story

**Phase 3 (US1)**:
```
T002 (inventory CLI) → T009 (All Parameters)
T003 → T004 (Setup)
T003 → T005 + T006 + T007 (in parallel) → T008 (quick-start summary)
```

**Phase 4 (US2)**:
```
T003 → T010 + T011 + T012 (all in parallel)
```

**Phase 5 (US3)**:
```
T003 → T013 (Scheduling)
US1+US2 done → T014 + T016 (sequential: write then verify)
T003 → T015 (checklist verification, independent)
```

**Phase 6 (Polish)**:
```
T017 + T020 first → T018 + T019 (reviewers in parallel)
```

---

## Implementation Strategy

### MVP Scope (US1 only)
Deliver Phase 1 + Phase 2 + Phase 3 first. At that point, users can identify and run all three modes correctly — the highest-value outcome. US2 and US3 build on top.

### Suggested Order (single implementer)
1. T001 + T002 (parallel reads)
2. T003 (skeleton)
3. T004 → T005 → T006 → T007 → T008 → T009 (US1 in order)
4. T010 + T011 + T012 (US2, any order)
5. T013 → T015 → T014 → T016 (US3, finish with full-README audits)
6. T017 + T020 → T018 + T019 (Polish)
7. T021 (record SC-004 next-feature validation trigger and owner)
