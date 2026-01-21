# Tasks: Update README Examples

**Input**: Design documents from `/specs/004-update-readme-examples/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: This is a documentation-only feature. Tests refer to manual verification steps.

**Organization**: Tasks are grouped by user story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization

- [x] T001 Create feature branch `004-update-readme-examples`

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure

- [x] T002 Verify `README.md` exists and is writable

## Phase 3: User Story 1 - Comprehensive Documentation (Priority: P1) 🎯 MVP

**Goal**: Update README to include comprehensive usage examples for all parameters.

**Independent Test**: Review `README.md`, ensure "Organizing Playlists" section exists and all table parameters appear in code blocks.

### Implementation for User Story 1

- [x] T003 [US1] Add "Organizing Playlists" section to `README.md` with example command using `--folder` (from `quickstart.md`)
- [x] T004 [US1] Review and update existing "Modifier: Adding Variety with Shuffle" example in `README.md` to ensuring clarity
- [x] T005 [US1] Cross-check "All Parameters" table in `README.md` against examples to ensure 100% coverage (add/update examples if missing)

## Final Phase: Polish & Cross-Cutting Concerns

- [x] T006 Manual verification of `README.md` rendering and syntax correctness

## Dependencies

- **US1** depends on **T002** (File existence)

## Parallel Execution Opportunities

- T003 and T004 involves editing different sections of the same file, so likely sequential or requiring careful merge.

## Implementation Strategy

1.  **Add New Content**: Insert the new section first.
2.  **Refine Existing**: Audit and polish existing examples.
3.  **Verify**: Final check against the parameters table.
