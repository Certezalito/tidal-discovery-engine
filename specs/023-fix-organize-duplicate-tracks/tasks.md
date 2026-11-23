---

description: "Task list for Fix Duplicate Tracks in Organized Playlists"
---

# Tasks: Fix Duplicate Tracks in Organized Playlists

**Input**: Design documents from `/specs/023-fix-organize-duplicate-tracks/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/sync-planner-contract.md`, `quickstart.md`

**Tests**: Targeted automated unit and service tests are included to satisfy Constitution Principle V (Reliability & Verifiability) and the Validation quality gate.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/`, `README.md` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish clean baseline verification before modifying playlist deduplication and synchronization logic

- [X] T001 Verify baseline test suite passes via `uv run pytest` from repository root

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core deduplication primitives, Tidal service hardening, and in-memory value objects that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Implement `get_playlist_dedup_key(track)` in `src/services/tidal_service.py` per `contracts/sync-planner-contract.md` and `data-model.md` (`TrackDedupGroup.dedup_key`, `PlaylistTrackOccurrence.isrc`), with clear inline rationale comments
- [X] T003 Preserve `"isrc"` in the fallback `Track` object inside `get_playlist_tracks` and add order-preserving deduplication of outgoing track IDs in `add_tracks_to_playlist` in `src/services/tidal_service.py` per `contracts/sync-planner-contract.md`
- [X] T004 Define `TrackDedupGroup`, `PlaylistTrackOccurrence`, and `PlaylistSyncPlan` dataclasses in `src/services/genre_organizer_service.py` enforcing all field constraints from `data-model.md` (`TrackDedupGroup.dedup_key`, `TrackDedupGroup.cache_key`, `TrackDedupGroup.representative_track`, `TrackDedupGroup.candidate_track_ids`, `TrackDedupGroup.canonical_track_id`, `PlaylistTrackOccurrence.track_id`, `PlaylistTrackOccurrence.isrc`, `PlaylistTrackOccurrence.item_uuid`, `PlaylistTrackOccurrence.dedup_key`, `PlaylistSyncPlan.to_add_ids`, `PlaylistSyncPlan.to_remove_items`, `PlaylistSyncPlan.duplicates_removed`)

**Checkpoint**: Foundation ready — user story implementation can now proceed

---

## Phase 3: User Story 1 - Deduplicated Track Membership in Organized Playlists (Priority: P1) 🎯 MVP

**Goal**: Ensure every newly created or built genre playlist contains each qualifying track at most once (by exact catalog ID and underlying ISRC recording), preserves distinct versions (remixes/live) and multi-genre placement, and evaluates `--min-genre-size` on unique deduplicated tracks.

**Independent Test**: Run `run_genre_organizer_sync` against a library containing duplicate catalog IDs, multi-release ISRC duplicates (single + album), distinct remix/live versions, tracks missing ISRC, overlapping genre labels, and a genre that falls below `--min-genre-size` after deduplication; verify zero repeating tracks in generated playlists and accurate post-dedup thresholding.

### Implementation & Tests for User Story 1

- [X] T005 [P] [US1] Add unit tests for `get_playlist_dedup_key`, `get_playlist_tracks` fallback ISRC preservation, and `add_tracks_to_playlist` outgoing ID deduplication in `tests/test_tidal_service.py`
- [X] T006 [US1] Refactor library aggregation, genre grouping, and post-deduplication `--min-genre-size` thresholding in `run_genre_organizer_sync` in `src/services/genre_organizer_service.py` to build deterministic `TrackDedupGroup`s (`data-model.md`: `TrackDedupGroup.dedup_key`, `TrackDedupGroup.cache_key`, `TrackDedupGroup.representative_track`, `TrackDedupGroup.candidate_track_ids`, `TrackDedupGroup.canonical_track_id`) before evaluating `min_genre_size` and creating new playlists
- [X] T007 [US1] Add unit tests for ISRC deduplication, missing-ISRC catalog ID fallback, distinct remix/live preservation, deterministic canonical release selection, multi-genre distribution preservation, and post-dedup `--min-genre-size` thresholding in `tests/test_genre_playlist_service.py`

**Checkpoint**: User Story 1 is fully functional and independently testable (MVP)

---

## Phase 4: User Story 2 - Automatic Cleanup of Existing Playlists with Duplicate Tracks (Priority: P1)

**Goal**: Automatically detect and surgically remove surplus duplicate occurrences (same catalog ID or same ISRC across releases, including 3+ copies and multi-page playlists) and all copies of obsolete tracks from existing organized playlists during a normal `organize` run without requiring a folder wipe.

**Independent Test**: Run `run_genre_organizer_sync` against existing playlists containing 2x and 3x copies of a qualifying track, two different catalog releases of the same ISRC, and 2x copies of an obsolete track; verify only surplus `item_uuid`s (plus all obsolete `item_uuid`s) are removed, leaving exactly 1 copy of each qualifying track.

### Implementation & Tests for User Story 2

- [X] T008 [US2] Implement `calculate_playlist_sync_plan(desired_groups, existing_tracks)` in `src/services/genre_organizer_service.py` per `contracts/sync-planner-contract.md` and `data-model.md` (`PlaylistTrackOccurrence.track_id`, `PlaylistTrackOccurrence.isrc`, `PlaylistTrackOccurrence.item_uuid`, `PlaylistTrackOccurrence.dedup_key`, `PlaylistSyncPlan.to_add_ids`, `PlaylistSyncPlan.to_remove_items`, `PlaylistSyncPlan.duplicates_removed`), including surgical `item_uuid` removal and degraded non-UUID fallback
- [X] T009 [US2] Update `calculate_sync_delta(desired_track_ids, existing_track_ids)` in `src/services/genre_organizer_service.py` to normalize IDs as strings and report surplus duplicate occurrences in `to_remove` while preserving backward compatibility
- [X] T010 [US2] Integrate `calculate_playlist_sync_plan` into existing-playlist synchronization and update sync logging/summary reporting (including removed duplicates) in `run_genre_organizer_sync` in `src/services/genre_organizer_service.py`
- [X] T011 [P] [US2] Add unit tests for exact duplicate cleanup (2x and 3+ copies), cross-release ISRC duplicate cleanup, obsolete duplicated track removal, multi-page playlist duplicate removal, and non-UUID fallback in `tests/test_genre_playlist_service.py`
- [X] T012 [P] [US2] Add unit tests verifying surgical `item_uuid` removal and `sync_playlist_tracks` behavior with UUIDs vs. track IDs in `tests/test_sync_playlist_tracks.py`

**Checkpoint**: User Stories 1 and 2 are both independently functional and verified

---

## Phase 5: User Story 3 - Stable Repeated Synchronization Without Churn (Priority: P2)

**Goal**: Guarantee that consecutive `organize` runs against an unchanged library (even if Tidal favorites pagination returns alternate releases in a different order) produce 0 track additions, 0 track removals, and 0 duplicate tracks.

**Independent Test**: Simulate two consecutive runs of `run_genre_organizer_sync` on an unchanged library where favorites order is reversed between runs (swapping which release of a shared ISRC appears first) and verify the second run reports `playlists_updated == 0`, `tracks_added == 0`, `tracks_removed == 0`.

### Implementation & Tests for User Story 3

- [X] T013 [US3] Verify and harden existing-copy preservation in `calculate_playlist_sync_plan` in `src/services/genre_organizer_service.py` so any existing playlist track matching a desired `TrackDedupGroup.dedup_key` (`data-model.md`) is kept without swapping to `TrackDedupGroup.canonical_track_id`
- [X] T014 [US3] Add consecutive-run idempotency tests (unchanged library with reversed pagination order, plus single-track incremental addition) in `tests/test_genre_playlist_service.py`

**Checkpoint**: All user stories are independently functional and idempotent

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-user documentation updates (Constitution Principle I) and full end-to-end validation

- [X] T015 [P] Update `README.md` to document `tde organize` track deduplication behavior (exact track ID + underlying ISRC recording deduplication, preservation of distinct versions like remixes/live, automatic duplicate cleanup on existing playlists, and post-dedup `--min-genre-size` counting)
- [X] T016 Run full test suite (`uv run pytest`) and verify all automated validation scenarios in `specs/023-fix-organize-duplicate-tracks/quickstart.md` pass cleanly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — starts immediately (`T001`).
- **Foundational (Phase 2)**: Depends on Setup (`T001`) — blocks all user stories (`T002` → `T003`, `T004` in parallel across different files).
- **User Story 1 (Phase 3)**: Depends on Phase 2 (`T002`–`T004`).
- **User Story 2 (Phase 4)**: Depends on Phase 2 (`T002`–`T004`) and integrates with `TrackDedupGroup`s from `T006`.
- **User Story 3 (Phase 5)**: Depends on Phase 4 (`T008`, `T010`).
- **Polish (Phase 6)**: Depends on Phases 3–5 completion (`T015` can run in parallel with `T014`; `T016` runs last).

### Parallel Opportunities

- **Phase 2**: `T002`/`T003` (`src/services/tidal_service.py`) and `T004` (`src/services/genre_organizer_service.py`) touch different files and can run in parallel.
- **Phase 3**: `T005` (`tests/test_tidal_service.py`) can run in parallel with `T006` (`src/services/genre_organizer_service.py`).
- **Phase 4**: `T011` (`tests/test_genre_playlist_service.py`) and `T012` (`tests/test_sync_playlist_tracks.py`) can run in parallel after `T008`–`T010`.
- **Phase 6**: `T015` (`README.md`) can run in parallel with test authoring before final verification (`T016`).

---

## Parallel Example: Phase 2 & User Story 1

```bash
# Phase 2 parallel file edits:
Task: "T002/T003 in src/services/tidal_service.py"
Task: "T004 in src/services/genre_organizer_service.py"

# Phase 4 parallel test authoring:
Task: "T011 in tests/test_genre_playlist_service.py"
Task: "T012 in tests/test_sync_playlist_tracks.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`T001`)
2. Complete Phase 2: Foundational (`T002`–`T004`)
3. Complete Phase 3: User Story 1 (`T005`–`T007`)
4. **STOP and VALIDATE**: Run `uv run pytest tests/test_tidal_service.py tests/test_genre_playlist_service.py`

### Incremental Delivery

1. Setup + Foundational → Core deduplication primitives ready
2. User Story 1 → Guaranteed duplicate-free new playlists & post-dedup thresholding (MVP)
3. User Story 2 → Automatic surgical cleanup of existing playlists with repeating tracks
4. User Story 3 → Guaranteed zero-churn idempotency across consecutive scheduled runs
5. Polish → `README.md` documentation + full `uv run pytest` verification
