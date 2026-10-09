# Implementation Tasks: Gemini Flex Mode Support

**Feature**: [Gemini Flex Mode Support](spec.md)  
**Branch**: `021-gemini-flex-mode`  
**Plan**: [plan.md](plan.md)  
**Date**: 2026-10-09  
**Status**: Ready for Implementation  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Update dependency constraints and synchronize the environment to support the Gemini flex tier natively.

- [X] T001 Update `google-genai` dependency specification to `>=1.70.0` in `pyproject.toml` to enable native `service_tier` and `HttpOptions(timeout=...)` support per Constitution Principle X
- [X] T002 Synchronize virtual environment packages via `uv sync` to install `google-genai>=1.70.0` in `pyproject.toml` and `uv.lock`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core service layer tier resolution, timeout configuration, and capacity error classification required by all user stories.

**⚠️ CRITICAL**: No user story tasks can begin until this phase is complete.

- [X] T003 [P] Implement `_resolve_service_tier(cli_flex, dotenv_config)` in `src/services/gemini_service.py` to resolve tier (`"standard"` or `"flex"`), source identifier (`"cli"`, `"env"`, `"dotenv"`, `"default"`), and timeout (`900_000` ms for flex, `120_000` ms for standard, configurable via `GEMINI_FLEX_TIMEOUT_SECONDS`)
- [X] T004 [P] Add unit tests for `_resolve_service_tier` in `tests/test_gemini_service.py` testing CLI overrides, environment variable fallback, case-insensitivity, whitespace trimming, and invalid value fallback
- [X] T005 Update `client.models.generate_content` call in `src/services/gemini_service.py` to pass `service_tier=resolved_tier` and `http_options=types.HttpOptions(timeout=resolved_timeout_ms)` in `types.GenerateContentConfig`
- [X] T006 Add error classifications for `flex-capacity` and `flex-timeout` in `_classify_client_error` and `_build_actionable_error` in `src/services/gemini_service.py`

**Checkpoint**: Foundation ready - service tier resolution and request payload configuration can now be leveraged across all commands.

---

## Phase 3: User Story 1 - Cost-Optimized Playlist Generation with Flex Mode (Priority: P1) 🎯 MVP

**Goal**: Enable users to retrieve Gemini playlist recommendations using the discounted flex tier via `tde recommend --gemini --flex`, with `--no-flex` override support, validation requiring `--gemini`, and explicit logging/terminal confirmation of flex mode usage.

**Independent Test**: Execute `uv run tde recommend --gemini --flex --num-tidal-tracks 5 --num-similar-tracks 10` and verify the request completes via flex tier, emits structured INFO log confirmation, displays terminal notices, and adds tracks to the playlist.

### Tests for User Story 1

- [X] T007 [P] [US1] Add unit test in `tests/test_gemini_service.py` verifying `get_recommendations(..., flex=True)` configures `service_tier="flex"` in `GenerateContentConfig`
- [X] T008 [P] [US1] Add CLI test in `tests/test_cli.py` verifying `tde recommend --gemini --flex` and `tde recommend --gemini --no-flex` correctly invoke `get_recommendations` with the expected flex flag
- [X] T009 [P] [US1] Add CLI test in `tests/test_cli.py` verifying `tde recommend --flex` and `tde recommend --no-flex` without `--gemini` abort with `Error: --flex and --no-flex flags require --gemini.` and exit code 1
- [X] T040 [P] [US1] Add unit test in `tests/test_gemini_service.py` verifying structured INFO logging for service tier resolution (`tier='%s' source='%s' timeout=%sms`) on `get_recommendations` per FR-015 and SC-008
- [X] T041 [P] [US1] Add CLI test in `tests/test_cli.py` verifying `tde recommend --gemini --flex` emits explicit flex tier confirmation in logs and terminal output per FR-016 and SC-008

### Implementation for User Story 1

- [X] T010 [US1] Update `get_recommendations` signature and body in `src/services/gemini_service.py` to accept `flex: bool | None = None` and apply resolved service tier
- [X] T011 [US1] Add `@click.option("--flex/--no-flex", default=None, help="Use Google Gemini flex service tier (50% cheaper token rates, variable latency).")` to `recommend` command in `src/cli/main.py`
- [X] T012 [US1] Add CLI argument validation in `recommend` in `src/cli/main.py` rejecting `--flex` or `--no-flex` when `not gemini` with `click.ClickException("--flex and --no-flex flags require --gemini.")`
- [X] T013 [US1] Propagate `flex` parameter from `recommend` CLI handler to `gemini_service.get_recommendations` in `src/cli/main.py`
- [X] T042 [US1] Update `recommend` command completion in `src/cli/main.py` to display explicit confirmation that flex mode was utilized when creating playlist per FR-016

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently as the MVP!

---

## Phase 4: User Story 2 - Single-Seed Radio Generation with Flex Mode (Priority: P2)

**Goal**: Support `--flex / --no-flex` on `tde radio` so single-seed radio curation also benefits from the discounted flex tier with explicit logging and terminal confirmation.

**Independent Test**: Execute `uv run tde radio --artist "Daft Punk" --track "One More Time" --gemini --flex --num-tracks 10` and verify radio playlist creation succeeds under flex mode with visible confirmation.

### Tests for User Story 2

- [X] T014 [P] [US2] Add CLI test in `tests/test_cli.py` verifying `tde radio --artist ... --track ... --gemini --flex` calls `get_recommendations` with `flex=True`
- [X] T015 [P] [US2] Add CLI test in `tests/test_cli.py` verifying `tde radio --flex` or `--no-flex` without `--gemini` aborts with `Error: --flex and --no-flex flags require --gemini.` and exit code 1
- [X] T043 [P] [US2] Add CLI test in `tests/test_cli.py` verifying `tde radio --gemini --flex` emits explicit flex tier confirmation in terminal output and application logs per FR-016

### Implementation for User Story 2

- [X] T016 [US2] Add `@click.option("--flex/--no-flex", default=None, help="Use Google Gemini flex service tier (50% cheaper token rates, variable latency).")` to `radio` command in `src/cli/main.py`
- [X] T017 [US2] Add argument validation in `generate_track_radio` in `src/cli/main.py` rejecting `flex is not None and not gemini` with `click.ClickException("--flex and --no-flex flags require --gemini.")`
- [X] T018 [US2] Propagate `flex` parameter from `radio` command through `generate_track_radio` into `gemini_service.get_recommendations` in `src/cli/main.py`
- [X] T044 [US2] Update `radio` command completion in `src/cli/main.py` to display explicit confirmation that flex mode was utilized when creating radio playlist per FR-016

**Checkpoint**: At this point, User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Cost-Effective Library Genre Organization with Flex Mode (Priority: P3)

**Goal**: Support `--flex / --no-flex` on `tde organize` and alias `genre-organizer` to execute batch library track classification at 50% lower token cost with explicit confirmation in sync summaries and logs.

**Independent Test**: Execute `uv run tde organize --flex --limit 10 --dry-run` and verify batch genre classification requests route via flex tier with confirmation in summary and logs.

### Tests for User Story 3

- [X] T019 [P] [US3] Add unit test in `tests/test_gemini_service.py` verifying `classify_tracks_genres(..., flex=True)` configures `service_tier="flex"` in `GenerateContentConfig`
- [X] T020 [P] [US3] Add CLI test in `tests/test_cli_genre_organizer.py` verifying `tde organize --flex` forwards `flex=True` to `run_genre_organizer_sync`
- [X] T045 [P] [US3] Add CLI test in `tests/test_cli_genre_organizer.py` verifying `tde organize --flex` displays explicit flex service tier confirmation in sync summary and application logs per FR-016

### Implementation for User Story 3

- [X] T021 [US3] Update `classify_tracks_genres` signature and body in `src/services/gemini_service.py` to accept `flex: bool | None = None` and apply resolved service tier and timeout
- [X] T022 [US3] Update `run_genre_organizer_sync` in `src/services/genre_organizer_service.py` to accept `flex: bool | None = None` and forward it into `classify_tracks_genres`
- [X] T023 [US3] Add `@click.option("--flex/--no-flex", default=None, help="Use Google Gemini flex service tier for batch genre classification.")` to `organize` and `genre-organizer` commands in `src/cli/main.py` and forward `flex` to `run_genre_organizer_sync`
- [X] T046 [US3] Update `_execute_genre_organizer` summary in `src/cli/main.py` to display explicit flex service tier confirmation in terminal summary when flex mode is active per FR-016

**Checkpoint**: At this point, User Stories 1, 2, and 3 are all functional and testable independently.

---

## Phase 6: User Story 4 - Global Flex Mode Configuration & CLI Override (Priority: P4)

**Goal**: Support configuring `GEMINI_SERVICE_TIER=flex` in `.env` / environment for automated runs, with `--no-flex` providing an explicit CLI override to force standard tier.

**Independent Test**: Set `GEMINI_SERVICE_TIER=flex` in `.env`, run `tde recommend --gemini` to verify flex tier is used by default, then run with `--no-flex` to verify standard tier override.

### Tests for User Story 4

- [X] T024 [P] [US4] Add unit test in `tests/test_gemini_service.py` verifying `GEMINI_SERVICE_TIER=flex` in `.env` configures `service_tier="flex"` with source `"dotenv"` when no CLI flag is provided
- [X] T025 [P] [US4] Add unit test in `tests/test_gemini_service.py` verifying passing `flex=False` (`--no-flex`) overrides `GEMINI_SERVICE_TIER=flex` in `.env`, producing `service_tier="standard"` with source `"cli"`

### Implementation for User Story 4

- [X] T026 [US4] Verify and ensure `_read_dotenv_values` and `_resolve_from_env_then_dotenv` in `src/services/gemini_service.py` load `GEMINI_SERVICE_TIER` reliably
- [X] T027 [US4] Add structured logging in `src/services/gemini_service.py` logging `Gemini service tier resolution: tier='%s' source='%s' timeout=%sms` on each request per FR-015

**Checkpoint**: Global environment configuration and CLI override hierarchy are fully verified.

---

## Phase 7: User Story 5 - Transparent Liveness Feedback & Extended Timeout for Flex Latency (Priority: P5)

**Goal**: Accommodate the 1–15 minute Flex tier latency turnaround by providing upfront status notices, configuring 900s HTTP timeouts (configurable via `GEMINI_FLEX_TIMEOUT_SECONDS`), handling SIGINT (Ctrl+C) gracefully, and providing actionable timeout diagnostics.

**Independent Test**: Trigger a flex retrieval, verify upfront turnaround notice displays immediately, client timeout is 900s, and Ctrl+C exits cleanly with code 130 and "Operation canceled by user."

### Tests for User Story 5

- [X] T028 [P] [US5] Add unit test in `tests/test_gemini_service.py` verifying `GEMINI_FLEX_TIMEOUT_SECONDS=600` configures a 600,000 ms timeout, and verifying invalid/negative values fall back to the 900,000 ms default with a warning log
- [X] T029 [P] [US5] Add unit test in `tests/test_gemini_service.py` verifying a timeout during a flex tier request produces an actionable `category="flex-timeout"` error advising retry or `--no-flex`
- [X] T030 [P] [US5] Add CLI test in `tests/test_cli.py` verifying the upfront turnaround notice is emitted to stdout immediately before invoking the Gemini API when flex mode is active
- [X] T031 [P] [US5] Add CLI test in `tests/test_cli.py` verifying `KeyboardInterrupt` during flex execution prints `Operation canceled by user.` and exits with code 130

### Implementation for User Story 5

- [X] T032 [US5] Implement upfront console notice in `src/cli/main.py` informing users: `Connecting to Gemini via Flex tier (50% cost savings). Flex tier uses opportunistic capacity; response turnaround is typically 1–15 minutes. Please wait...`
- [X] T033 [US5] Add `KeyboardInterrupt` exception handling in `src/cli/main.py` across `recommend`, `radio`, and `organize` CLI handlers exiting with code 130 and message `Operation canceled by user.`
- [X] T034 [US5] Implement timeout exception classification and actionable error generation in `src/services/gemini_service.py` for `category="flex-timeout"`

**Checkpoint**: Extended latency turnaround is smoothly handled with full transparency and clean interruption mechanics.

---

## Phase 8: User Story 6 - Graceful Feedback on Flex Tier Capacity Constraints (Priority: P6)

**Goal**: Enforce strict cost protection: when flex capacity is shed or preempted (HTTP 429/503) after retries, fail fast with actionable guidance without silent fallback to full-price standard billing.

**Independent Test**: Simulate HTTP 429 Resource Exhausted on a flex request and verify immediate failure with `category="flex-capacity"` guidance advising retry or manual standard mode.

### Tests for User Story 6

- [X] T035 [P] [US6] Add unit test in `tests/test_gemini_service.py` verifying HTTP 429 on flex requests triggers one recovery retry and then raises `ValueError` with `category='flex-capacity'` and guidance without invoking standard tier

### Implementation for User Story 6

- [X] T036 [US6] Update error categorization and retry flow in `src/services/gemini_service.py` to classify capacity preemption on flex requests as `flex-capacity` and strictly prohibit falling back to standard tier

**Checkpoint**: All user stories from P1 through P6 are complete and independently verified.

---

## Phase 9: User Story 7 - Configurable Fallback to Standard Tier on Flex Unavailable (Priority: P2)

**Goal**: Enable automated and interactive users to configure automatic standard tier fallback (`--flex-fallback-standard / --no-flex-fallback-standard` CLI flags or `GEMINI_FLEX_FALLBACK_STANDARD=true/false` in `.env`) when flex capacity experiences HTTP 503 demand spikes, HTTP 429 shedding, or timeout, with clear warning logging and sticky fallback across multi-batch organization runs.

**Independent Test**: Execute requests with flex mode and fallback enabled (`--flex --flex-fallback-standard` or `GEMINI_FLEX_FALLBACK_STANDARD=true`), simulate capacity exhaustion (HTTP 503 / 429) or timeout after retries, and verify warning log emission, successful completion on standard tier without aborting, sticky standard execution on subsequent batches in `tde organize`, and strict fail-fast cost protection when fallback is disabled.

### Tests for User Story 7

- [X] T048 [P] [US7] Add unit tests in `tests/test_gemini_service.py` for `_resolve_flex_fallback_standard(cli_fallback, dotenv_config)` testing CLI flag overrides (`True`/`False`), environment variable `GEMINI_FLEX_FALLBACK_STANDARD` boolean parsing (`true`, `false`, `1`, `0`, `yes`, `no`), case-insensitivity, whitespace trimming, and invalid value fallback to `False` with warning log per FR-019 and FR-020
- [X] T049 [P] [US7] Add unit tests in `tests/test_gemini_service.py` verifying `get_recommendations` with `flex=True` and `flex_fallback_standard=True` logs a warning and falls back to standard tier inference (`service_tier="standard"`, `timeout=120_000`ms) when flex retries encounter HTTP 503, 429, or timeout per FR-008, FR-021, and SC-009
- [X] T050 [P] [US7] Add unit tests in `tests/test_gemini_service.py` verifying `get_recommendations` with `flex=True` and `flex_fallback_standard=False` fails fast with `category='flex-capacity'` when flex retries fail without invoking standard tier per FR-008, FR-020, and SC-010
- [X] T051 [P] [US7] Add unit tests in `tests/test_gemini_service.py` verifying `classify_tracks_genres` with `flex=True` and `flex_fallback_standard=True` falls back to standard tier inference with warning log when flex retries fail per FR-008, FR-021, and SC-009
- [X] T052 [P] [US7] Add CLI tests in `tests/test_cli.py` verifying `tde recommend --flex-fallback-standard` and `tde radio --flex-fallback-standard` without `--gemini` abort with exit code 1 and error message `Error: --flex-fallback-standard and --no-flex-fallback-standard flags require --gemini.` per FR-006 and SC-004
- [X] T053 [P] [US7] Add CLI tests in `tests/test_cli.py` verifying `tde recommend --gemini --flex --flex-fallback-standard` and `--no-flex-fallback-standard` correctly forward the fallback argument to `get_recommendations` per FR-018
- [X] T054 [P] [US7] Add CLI and integration tests in `tests/test_cli_genre_organizer.py` verifying `tde organize --flex --flex-fallback-standard` forwards fallback to `run_genre_organizer_sync` and implements sticky fallback where batch 1 fallback causes batch 2 to execute directly on standard tier per FR-018 and FR-022

### Implementation for User Story 7

- [X] T055 [US7] Implement `_resolve_flex_fallback_standard(cli_fallback, dotenv_config)` in `src/services/gemini_service.py` supporting CLI overrides, `GEMINI_FLEX_FALLBACK_STANDARD` environment parsing, warning on invalid values, and defaulting to `False` per FR-019 and FR-020
- [X] T056 [US7] Update `get_recommendations` in `src/services/gemini_service.py` to accept `flex_fallback_standard: bool | None = None`, resolve fallback setting, and execute standard tier fallback on flex capacity exhaustion (HTTP 503 / 429) or timeout with a warning log per FR-008, FR-021, and SC-009
- [X] T057 [US7] Update `classify_tracks_genres` in `src/services/gemini_service.py` to accept `flex_fallback_standard: bool | None = None`, resolve fallback setting, and execute standard tier fallback on flex capacity exhaustion with warning log per FR-008, FR-021, and SC-009
- [X] T058 [US7] Update `run_genre_organizer_sync` in `src/services/genre_organizer_service.py` to accept `flex_fallback_standard: bool | None = None` and implement sticky fallback state tracking across batches (`active_flex_tier`) per FR-022
- [X] T059 [US7] Add `@click.option("--flex-fallback-standard/--no-flex-fallback-standard", default=None, help="Automatically fallback to standard tier inference if flex capacity is exhausted or times out.")` to `recommend`, `radio`, `organize`, and `genre-organizer` commands in `src/cli/main.py` per FR-018
- [X] T060 [US7] Add CLI validation in `recommend` and `radio` in `src/cli/main.py` requiring `--gemini` when `--flex-fallback-standard` or `--no-flex-fallback-standard` is passed, and propagate `flex_fallback_standard` into service calls per FR-006 and FR-018

**Checkpoint**: User Story 7 is complete, providing configurable fallback to standard tier while guaranteeing default cost protection.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates, inline intent commenting, and final end-to-end verification across all user stories.

- [X] T037 [P] Update `README.md` documenting `--flex / --no-flex`, `GEMINI_SERVICE_TIER`, `GEMINI_FLEX_TIMEOUT_SECONDS`, turnaround expectations (1–15 min), and usage examples for `recommend`, `radio`, and `organize` per Constitution Principle I
- [X] T038 [P] Add clear inline intent docstrings and comments across all modified functions in `src/services/gemini_service.py`, `src/cli/main.py`, and `src/services/genre_organizer_service.py` per Constitution Principle XI
- [X] T039 Execute `quickstart.md` validation scenarios and full test suite via `uv run pytest` to ensure 100% test pass and zero regressions
- [X] T047 Execute full test suite via `uv run pytest` in `tests/` to verify all new logging and terminal confirmation tests pass with zero regressions
- [X] T061 [P] Update `README.md` documenting `--flex-fallback-standard / --no-flex-fallback-standard`, `GEMINI_FLEX_FALLBACK_STANDARD`, fallback warning behavior, and multi-batch sticky fallback per FR-010 and SC-005
- [X] T062 [P] Add inline intent docstrings and comments across all new fallback logic in `src/services/gemini_service.py`, `src/services/genre_organizer_service.py`, and `src/cli/main.py` per Constitution Principle XI
- [X] T063 Run `quickstart.md` validation scenarios (specifically Scenarios 9, 10, 11) and full test suite via `uv run pytest` in `tests/` to ensure 100% test pass and zero regressions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately - no dependencies
- **Foundational (Phase 2)**: Depends on Phase 1 completion - **BLOCKS all user stories**
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion (MVP increment)
- **User Story 2 (Phase 4)**: Depends on Phase 2 completion (can run in parallel with US1 or sequentially)
- **User Story 3 (Phase 5)**: Depends on Phase 2 completion (can run in parallel with US1/US2 or sequentially)
- **User Story 4 (Phase 6)**: Depends on Phase 2 completion (can run in parallel or sequentially)
- **User Story 5 (Phase 7)**: Depends on Phase 2 and US1 CLI wiring
- **User Story 6 (Phase 8)**: Depends on Phase 2 service layer wiring
- **User Story 7 (Phase 9)**: Depends on Phase 2 tier resolution, US1/US2/US3 service & CLI wiring
- **Polish (Phase 10)**: Depends on all user story phases being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent after Foundational phase
- **User Story 2 (P2)**: Independent after Foundational phase
- **User Story 3 (P3)**: Independent after Foundational phase
- **User Story 4 (P4)**: Independent after Foundational phase
- **User Story 5 (P5)**: Hooks into CLI handlers in US1/US2/US3 and service layer in Foundational
- **User Story 6 (P6)**: Hooks into error handling in Foundational
- **User Story 7 (P2)**: Extends service tier resolution and error handling across US1, US2, and US3 with opt-in fallback

### Parallel Opportunities

- Within Phase 2: T003 and T004 can run in parallel
- Within Phase 3 (US1): Tests T007, T008, T009, T040, T041 can run in parallel
- Within Phase 4 (US2): Tests T014, T015, T043 can run in parallel
- Within Phase 5 (US3): Tests T019, T020, T045 can run in parallel
- Within Phase 6 (US4): Tests T024, T025 can run in parallel
- Within Phase 7 (US5): Tests T028, T029, T030, T031 can run in parallel
- Within Phase 9 (US7): Tests T048, T049, T050, T051, T052, T053, T054 can run in parallel
- Within Phase 10 (Polish): T061 and T062 can run in parallel

---

## Parallel Example: User Story 7

```bash
# Launch test tasks for User Story 7 in parallel:
Task: "Add unit tests in tests/test_gemini_service.py for _resolve_flex_fallback_standard"
Task: "Add unit tests in tests/test_gemini_service.py verifying get_recommendations flex fallback"
Task: "Add unit tests in tests/test_gemini_service.py verifying get_recommendations flex fail fast"
Task: "Add unit tests in tests/test_gemini_service.py verifying classify_tracks_genres flex fallback"
Task: "Add CLI tests in tests/test_cli.py verifying --flex-fallback-standard without --gemini"
Task: "Add CLI tests in tests/test_cli.py verifying recommend fallback argument forwarding"
Task: "Add CLI and integration tests in tests/test_cli_genre_organizer.py verifying organize fallback and sticky fallback"

# Launch implementation sequentially for User Story 7:
Task: "Implement _resolve_flex_fallback_standard in src/services/gemini_service.py"
Task: "Update get_recommendations in src/services/gemini_service.py with fallback execution"
Task: "Update classify_tracks_genres in src/services/gemini_service.py with fallback execution"
Task: "Update run_genre_organizer_sync in src/services/genre_organizer_service.py with sticky fallback"
Task: "Add --flex-fallback-standard/--no-flex-fallback-standard options in src/cli/main.py"
Task: "Add CLI validation requiring --gemini in src/cli/main.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`pyproject.toml`, `uv sync`)
2. Complete Phase 2: Foundational (`_resolve_service_tier`, `GenerateContentConfig` wiring)
3. Complete Phase 3: User Story 1 (`tde recommend --gemini --flex` with logging & terminal confirmation)
4. **STOP and VALIDATE**: Run `uv run pytest tests/test_cli.py tests/test_gemini_service.py`
5. Test manually: `uv run tde recommend --gemini --flex`

### Incremental Delivery

1. Complete Setup + Foundational → Core tier resolution ready
2. Deliver US1 → MVP: Playlist recommendations in flex mode with logging & terminal confirmation
3. Deliver US2 → Radio curation in flex mode with logging & terminal confirmation
4. Deliver US3 → Library genre organization in flex mode with sync summary confirmation
5. Deliver US4 → Environment variable default & CLI override
6. Deliver US5 → Latency turnaround feedback, 900s timeout, Ctrl+C handling
7. Deliver US6 → Strict fail-fast cost protection
8. Deliver US7 → Configurable standard tier fallback with sticky multi-batch semantics
9. Polish → Documentation, inline comments & full regression suite

---

## Notes

* `[P]` tasks = different files, no dependencies
* `[Story]` label maps task to specific user story for traceability
* Each user story should be independently completable and testable
* Verify tests fail before implementing
* Commit after each task or logical group
* Stop at any checkpoint to validate story independently
* Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

