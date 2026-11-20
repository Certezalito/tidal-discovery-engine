---

description: "Actionable, dependency-ordered task list for migrating Tidal Discovery Engine to the Gemini Interactions API"
---

# Tasks: Migrate to Current Gemini Interaction Method

**Input**: Design documents from `/specs/022-migrate-gemini-interactions/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/gemini-service-contract.md`, `quickstart.md`

**Tests**: Included as required by Constitution Principle V (*Reliability & Verifiability*) and Quality Gate (*Validation*): every behavior-changing code path must have targeted automated validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., `US1`, `US2`, `US3`, `US4`)
- Exact file paths are included in every task description.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Upgrade the Gemini SDK dependency to the Interactions API baseline and verify the installed SDK surface before modifying service code.

- [X] T001 Update `google-genai` minimum dependency constraint from `>=1.70.0` to `>=2.25.0` with an explanatory comment referencing Interactions API support (Constitution Principle X) in `pyproject.toml`
- [X] T002 Run `uv sync` to resolve and update `uv.lock` with `google-genai>=2.25.0` and verify the installed `client.interactions.create` signature and exception classes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Interactions API infrastructure in `src/services/gemini_service.py` that MUST be complete before any user story migration begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Remove `from google.genai import types` and add a shared Interactions client factory helper (`_create_genai_client`) configuring `genai.Client(api_key=api_key, http_options={"timeout": timeout_ms})` per `data-model.md` (`InteractionRequestConfig.timeout_ms`) in `src/services/gemini_service.py`
- [X] T004 Unify HTTP status code extraction (`_extract_error_code` reading both `.status_code` and `.code`) and exception classification helpers (`_is_client_error`, `_is_server_error`, `_is_timeout_error`) across `genai.errors` and Interactions client exceptions per `contracts/gemini-service-contract.md` in `src/services/gemini_service.py`
- [X] T005 Implement shared Interactions response text extraction (`_extract_interaction_text` reading `interaction.output_text` with fallback to trailing `model_output` step text parts) and terminal status checks (`failed`, `cancelled`, `interaction.error`) per `data-model.md` in `src/services/gemini_service.py`
- [X] T006 Implement shared Interactions request builder helper enforcing stateless `store=False`, top-level `response_format`, `service_tier`, and `generation_config` (omitting retired `temperature`, `top_p`, `top_k`) per `data-model.md` (`InteractionRequestConfig.model`, `InteractionRequestConfig.input`, `InteractionRequestConfig.store`, `InteractionRequestConfig.service_tier`, `InteractionRequestConfig.response_format`, `InteractionRequestConfig.generation_config`) in `src/services/gemini_service.py`

**Checkpoint**: Foundation ready — user story migration phases can now proceed.

---

## Phase 3: User Story 1 - Seamless Playlist & Radio Discovery with Current Gemini Interface (Priority: P1) 🎯 MVP

**Goal**: Migrate playlist (`recommend --gemini`) and single-seed radio (`radio --gemini`) recommendation generation to `client.interactions.create(...)` with strict artist+title-only Pydantic structured outputs, `store=False`, and `thinking_level="medium"`.

**Independent Test**: Run `tests/test_gemini_service.py` recommendation tests and `tests/test_cli.py` to confirm `recommend --gemini` (standard & `--shuffle` deep cuts) and `radio --gemini` dispatch via `client.interactions.create(...)`, enforce artist+title-only schemas (zero ISRC), set `store=False` and `thinking_level="medium"`, and recover from unusable responses with one retry.

### Implementation for User Story 1

- [X] T007 [US1] Tighten `Song` Pydantic schema to strictly human-readable fields (removing `isrc` per Principle VIII) and add top-level `RecommendationList` wrapper model per `data-model.md` (`Song.artist`, `Song.title`, `RecommendationList.songs`) in `src/services/gemini_service.py`
- [X] T008 [US1] Migrate `_classify_response_state`, `_generate_recommendations_with_model`, and `get_recommendations` to call `client.interactions.create(...)` with `store=False`, `generation_config={"thinking_level": "medium"}`, `response_format` using `RecommendationList.model_json_schema()`, and `RecommendationList.model_validate_json(...)` per `data-model.md` (`InteractionRequestConfig.model`, `InteractionRequestConfig.input`, `InteractionRequestConfig.store`, `InteractionRequestConfig.response_format`, `InteractionRequestConfig.generation_config`, `RecommendationList.songs`) in `src/services/gemini_service.py`
- [X] T009 [US1] Update and add targeted unit tests for Interactions API recommendation calls (`client.interactions.create`, `store=False`, `thinking_level="medium"`, no deprecated sampling params, strict artist+title schema without ISRC, deep-cuts prompt, empty/blocked interaction single recovery retry) in `tests/test_gemini_service.py`
- [X] T010 [P] [US1] Run `uv run pytest tests/test_gemini_service.py tests/test_cli.py -v` to verify User Story 1 recommendation and CLI flows independently

**Checkpoint**: User Story 1 (MVP) is complete and independently validated.

---

## Phase 4: User Story 2 - Uninterrupted Library Genre Organization (Priority: P2)

**Goal**: Migrate batch library track genre classification (`organize` / `genre-organizer`) to `client.interactions.create(...)` with `GenreClassificationList` structured outputs, `store=False`, `thinking_level="minimal"` (with `"low"` compatibility downgrade on models that do not support `"minimal"`), and 100% SQLite genre cache compatibility.

**Independent Test**: Run `tests/test_gemini_service.py` genre classification tests and `tests/test_cli_genre_organizer.py` to confirm `classify_tracks_genres` dispatches via `client.interactions.create(...)`, sets `store=False`, uses `thinking_level="minimal"` with automatic `"low"` fallback on unsupported models, returns `primary_genre`, legacy `genre` alias, and up to 3 `sub_genres`, and preserves existing SQLite cache behavior.

### Implementation for User Story 2

- [X] T011 [US2] Add `GenreClassificationList` Pydantic wrapper model and align `GenreClassificationResult` fields per `data-model.md` (`GenreClassificationResult.isrc`, `GenreClassificationResult.title`, `GenreClassificationResult.artist`, `GenreClassificationResult.primary_genre`, `GenreClassificationResult.sub_genres`, `GenreClassificationList.classifications`) in `src/services/gemini_service.py`
- [X] T012 [US2] Migrate `classify_tracks_genres` to call `client.interactions.create(...)` with `store=False`, `response_format` using `GenreClassificationList.model_json_schema()`, `GenreClassificationList.model_validate_json(...)`, and `generation_config={"thinking_level": "minimal"}` with automatic compatibility downgrade to `"low"` on models that reject `"minimal"` per `data-model.md` (`InteractionRequestConfig.store`, `InteractionRequestConfig.response_format`, `InteractionRequestConfig.generation_config`, `GenreClassificationList.classifications`) in `src/services/gemini_service.py`
- [X] T013 [US2] Update and add targeted unit tests for Interactions API genre classification (`client.interactions.create`, `store=False`, `thinking_level="minimal"`, automatic `"minimal"`→`"low"` downgrade on 400 invalid thinking level, 1 primary genre + up to 3 sub-genres + legacy `genre` alias) in `tests/test_gemini_service.py`
- [X] T014 [P] [US2] Run `uv run pytest tests/test_gemini_service.py tests/test_cli_genre_organizer.py tests/test_genre_cache_service.py -v` to verify User Story 2 genre classification and cache continuity independently

**Checkpoint**: User Stories 1 and 2 are both complete and independently validated.

---

## Phase 5: User Story 3 - Preserved Default Model & Smooth Configuration Upgrade (Priority: P2)

**Goal**: Retain `gemini-flash-latest` as the built-in default (and `latest`/`auto`/`flash-latest` alias target), automatically substitute deprecated legacy `gemini-1.5-*`, `gemini-2.0-*`, and `gemini-2.5-*` identifiers with `gemini-flash-latest` plus a clear warning log, and preserve `GEMINI_FALLBACK_MODEL` and `tde radio --gemini` Last.fm fallback.

**Independent Test**: Run `tests/test_gemini_service.py` model resolution tests and `tests/test_cli.py` radio fallback tests to confirm default `gemini-flash-latest`, automatic substitution + warning for `1.5`/`2.0`/`2.5` models, custom `GEMINI_FALLBACK_MODEL` recovery, and `GeminiModelUnavailableError` propagation.

### Implementation for User Story 3

- [X] T015 [US3] Add deprecated legacy model detection (`gemini-1.5-*`, `gemini-2.0-*`, `gemini-2.5-*`) and automatic substitution to `gemini-flash-latest` with a clear `WARNING` log in `_resolve_primary_model` and `_resolve_fallback_model` per `data-model.md` (`ResolvedModelConfig.primary_model`, `ResolvedModelConfig.model_source`, `ResolvedModelConfig.fallback_model`) in `src/services/gemini_service.py`
- [X] T016 [US3] Verify primary-to-fallback model recovery (`GEMINI_FALLBACK_MODEL`) and `GeminiModelUnavailableError` propagation on Interactions 404/unavailable errors in `src/services/gemini_service.py`
- [X] T017 [US3] Add targeted unit tests for `gemini-flash-latest` default/aliases, deprecated `1.5`/`2.0`/`2.5` substitution + warning on both `GEMINI_MODEL` and `GEMINI_FALLBACK_MODEL`, custom fallback model recovery, and `GeminiModelUnavailableError` in `tests/test_gemini_service.py`

**Checkpoint**: User Stories 1, 2, and 3 are complete and independently validated.

---

## Phase 6: User Story 4 - Preserved Cost Controls, Flex Mode & Actionable Diagnostics (Priority: P3)

**Goal**: Preserve full standard/flex service-tier routing, client timeout configuration (`http_options={"timeout": timeout_ms}`), heartbeat logging, progressive capacity retries, strict fail-fast cost protection by default, opt-in `--flex-fallback-standard` (including sticky batch fallback), `Ctrl+C` exit `130`, and 10-category actionable diagnostics across Interactions exceptions.

**Independent Test**: Run `tests/test_gemini_service.py` flex/diagnostic tests and `tests/test_cli.py` flex/SIGINT tests to verify client timeout injection, `service_tier="flex"`, fail-fast default vs opt-in standard fallback (with fresh standard-timeout client), sticky `on_fallback`, and all 10 error categories.

### Implementation for User Story 4

- [X] T018 [US4] Verify and refine flex/standard client timeout isolation (`http_options={"timeout": timeout_ms}`), top-level `service_tier` routing, heartbeat logging, progressive backoff retries, fail-fast default cost protection, opt-in standard fallback (`on_fallback`), and 10-category error classification across Interactions exceptions per `data-model.md` (`InteractionRequestConfig.service_tier`, `InteractionRequestConfig.timeout_ms`) and `contracts/gemini-service-contract.md` in `src/services/gemini_service.py`
- [X] T019 [US4] Update and expand flex tier, timeout, sticky fallback, and Interactions exception categorization tests (covering both `genai.errors` and Interactions `.status_code` / `TimeoutError` exceptions) in `tests/test_gemini_service.py`

**Checkpoint**: All 4 user stories are complete and independently validated.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-user documentation updates, inline readability/comment hygiene, and full end-to-end regression verification.

- [X] T020 [P] Update `README.md` to document the Gemini Interactions API migration, retained `gemini-flash-latest` default, deprecated `1.5`/`2.0`/`2.5` auto-substitution warning, stateless privacy (`store=False`), and task-tailored reasoning effort (`medium` for `recommend`/`radio`, `minimal` for `organize`) per FR-015 and Constitution Principle I
- [X] T021 [P] Update `.env.example` comments to reflect deprecated legacy model auto-substitution and current Gemini Interactions behavior per FR-015
- [X] T022 Review and refine inline intent comments and docstrings in `src/services/gemini_service.py`, removing any obsolete `generateContent` / `GenerateContentConfig` comments per Constitution Principle XI
- [X] T023 Run `quickstart.md` validation checks: verify zero `generate_content` / `GenerateContentConfig` references remain in `src/` and run the full automated test suite (`uv run pytest -v`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Starts immediately (`T001` → `T002`).
- **Phase 2 (Foundational)**: Depends on Phase 1 (`T002`). Blocks all user story phases (`T003` → `T004`, `T005`, `T006`).
- **Phase 3 (US1 - MVP)**: Depends on Phase 2. Delivers full playlist & radio recommendation migration (`T007` → `T008` → `T009` → `T010`).
- **Phase 4 (US2)**: Depends on Phase 2. Can follow US1 sequentially since both edit `src/services/gemini_service.py` (`T011` → `T012` → `T013` → `T014`).
- **Phase 5 (US3)**: Depends on Phase 2. Modifies model resolution in `src/services/gemini_service.py` (`T015` → `T016` → `T017`).
- **Phase 6 (US4)**: Depends on Phases 3 and 4 (`get_recommendations` and `classify_tracks_genres` migrated) to verify full flex/fallback parity (`T018` → `T019`).
- **Phase 7 (Polish)**: Depends on Phases 3–6 (`T020` and `T021` can run in parallel; then `T022` → `T023`).

### Parallel Opportunities

- **Phase 7 Docs**: `T020` (`README.md`) and `T021` (`.env.example`) touch separate files and can run in parallel.
- **Verification Tasks**: `T010` and `T014` run isolated pytest targets as checkpoints after US1 and US2 respectively.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`T001`–`T002`).
2. Complete Phase 2: Foundational (`T003`–`T006`).
3. Complete Phase 3: User Story 1 (`T007`–`T010`).
4. **STOP and VALIDATE**: Confirm `recommend --gemini` and `radio --gemini` pass all unit and CLI tests on the Interactions API.

### Incremental Delivery

1. Setup + Foundational → Interactions API core ready.
2. Add User Story 1 (MVP: `recommend` & `radio`) → Validate independently.
3. Add User Story 2 (`organize` genre classification + `minimal`/`low` thinking guard) → Validate independently.
4. Add User Story 3 (deprecated legacy model auto-substitution + fallback) → Validate independently.
5. Add User Story 4 (flex tier timeout/retry/fallback parity & unified diagnostics) → Validate independently.
6. Complete Phase 7 (docs, inline comment hygiene, zero legacy API grep check, full `uv run pytest -v`).
