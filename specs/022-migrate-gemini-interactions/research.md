# Phase 0 Research: Migrate to Current Gemini Interaction Method

**Feature**: `022-migrate-gemini-interactions`  
**Date**: 2026-11-19  
**Authoritative Sources Consulted**:
- Project `gemini-api-dev` skill & `references/migration.md`
- Official Gemini API Documentation:
  - [Migrating to the Interactions API](https://ai.google.dev/gemini-api/docs/migrate-to-interactions.md.txt)
  - [Interactions API Overview](https://ai.google.dev/gemini-api/docs/interactions.md.txt)
  - [Interactions API Reference](https://ai.google.dev/static/api/interactions.md.txt)
  - [Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output.md.txt)
  - [Flex Inference](https://ai.google.dev/gemini-api/docs/flex-inference.md.txt)
  - [Gemini Thinking](https://ai.google.dev/gemini-api/docs/thinking.md.txt)
  - [Gemini Models](https://ai.google.dev/gemini-api/docs/models.md.txt)
- PyPI (`google-genai` package metadata — latest `3.6.1`, requires Python `>=3.11`)

---

## Research Decisions

### R-001: Minimum `google-genai` SDK Version Requirement
- **Decision**: Upgrade the minimum dependency constraint in `pyproject.toml` from `google-genai>=1.70.0` to `google-genai>=2.25.0` (resolving to the current `3.6.1` release via `uv`).
- **Rationale**: Per `gemini-api-dev` skill and Constitution Principle X (*Critical Dependency Currency & Capability Discovery*), SDK versions `>=2.0.0` automatically target the current Interactions API steps schema (`Api-Revision: 2026-05-20`) and `>=2.25.0` is the documented minimum supported version for the current Interactions API surface, convenience properties (`interaction.output_text`), `service_tier`, and `thinking_level`.
- **Alternatives Considered**:
  - Keeping `google-genai>=1.70.0`: Rejected because 1.x uses the legacy `generateContent` schema and lacks the 2.x/3.x Interactions steps schema and response helpers.
  - Pinning an exact version (`==3.6.1`): Rejected because lower-bound constraints (`>=2.25.0`) follow existing project conventions in `pyproject.toml` and allow security/patch upgrades.

### R-002: Interactions API Invocation Pattern & Removal of Legacy `types.*` Wrappers
- **Decision**: Replace all `client.models.generate_content(..., config=types.GenerateContentConfig(...))` calls in `src/services/gemini_service.py` with `client.interactions.create(...)` using plain Python arguments and dictionaries (`model`, `input`, `store=False`, `service_tier`, `response_format`, `generation_config`). Remove `from google.genai import types` entirely.
- **Rationale**: Official Interactions API documentation and `references/migration.md` confirm that `client.interactions.create()` does not use `types.GenerateContentConfig`, `types.Tool`, `types.Content`, or `types.Part`. Removing legacy `types.*` wrappers eliminates deprecated `generateContent` coupling.
- **Alternatives Considered**:
  - Maintaining dual `generateContent` + `interactions` code paths: Rejected because FR-001 requires completely retiring legacy content-generation calls.

### R-003: Structured Outputs via Pydantic Wrapper Models & `response_format`
- **Decision**: Define Pydantic wrapper models (`RecommendationList` wrapping `songs: list[Song]` and `GenreClassificationList` wrapping `classifications: list[GenreClassificationResult]`), pass:
  ```python
  response_format={
      "type": "text",
      "mime_type": "application/json",
      "schema": WrapperModel.model_json_schema(),
  }
  ```
  as a top-level argument to `client.interactions.create(...)`, and validate `interaction.output_text` via `WrapperModel.model_validate_json(...)` (with a fallback helper to extract text from `model_output` steps if `output_text` is absent on mock/custom objects). Keep `Song` strictly limited to `artist: str` and `title: str` (removing the optional `isrc` field from the prompt/schema per Constitution Principle VIII: Zero ISRC Hallucination; downstream dictionaries retain compatibility without asking Gemini for ISRCs).
- **Rationale**: Official Interactions API Structured Output docs specify `response_format={"type": "text", "mime_type": "application/json", "schema": Model.model_json_schema()}` where the top-level schema is a JSON object (`Enforces that the generated response is a JSON object that complies with the JSON schema specified in this field`). Wrapping lists inside an object model guarantees valid top-level JSON object schemas across all Gemini models while keeping Pydantic validation strict and idiomatic per the Constitution Quality Gate (*Gemini SDK Idioms & Schema Standards*).
- **Alternatives Considered**:
  - Passing a bare `list[Song]` JSON array schema via `TypeAdapter`: Rejected because the Interactions API reference explicitly specifies that `response_format` enforces a top-level JSON object; wrapping in `RecommendationList` / `GenreClassificationList` avoids schema rejection.
  - Parsing raw JSON with `json.loads()` without Pydantic: Rejected because the Constitution mandates Pydantic structured output schemas.

### R-004: Default Model Retention (`gemini-flash-latest`) & Deprecated Model Substitution
- **Decision**: Retain `DEFAULT_GEMINI_MODEL = "gemini-flash-latest"` (and alias mapping `latest`, `auto`, `flash-latest` → `gemini-flash-latest`) per Clarification Session 2026-11-19 (FR-006). Add a deprecation detector matching `gemini-1.5-*`, `gemini-2.0-*`, and `gemini-2.5-*` (case-insensitive) in `_resolve_primary_model` and `_resolve_fallback_model` that automatically substitutes `gemini-flash-latest` and logs a `WARNING` advising the user to update `.env` (FR-007).
- **Rationale**: Official Gemini Models documentation confirms `gemini-flash-latest` is a maintained alias pointing to the latest Flash release (with 2-week advance email notices before hot-swaps). Automatically substituting retired `1.5`/`2.0`/`2.5` families preserves unattended cron reliability (Principle II) while guiding users toward current configuration (Principle I).
- **Alternatives Considered**:
  - Hardcoding `gemini-3.8-flash` as default: Explicitly rejected by user during `/speckit-clarify` in favor of retaining `gemini-flash-latest`.
  - Failing fast on deprecated models: Explicitly rejected by user during `/speckit-clarify` in favor of automatic substitution with a warning.

### R-005: Stateless Privacy Posture (`store=False`)
- **Decision**: Pass `store=False` on every `client.interactions.create(...)` call across `get_recommendations` and `classify_tracks_genres`.
- **Rationale**: Per Clarification Session 2026-11-19 (FR-009) and official Interactions API docs, Interactions API stores turns server-side by default (`store=True`: 55 days paid / 1 day free). Tidal Discovery Engine never uses `previous_interaction_id` or `background=True`, so `store=False` has zero functional downside and strictly protects user listening-history privacy.
- **Alternatives Considered**:
  - Leaving `store=True` default: Rejected by user during `/speckit-clarify`.

### R-006: Task-Appropriate `thinking_level` & Cross-Model Compatibility
- **Decision**: Pass `generation_config={"thinking_level": level}` (omitting deprecated `temperature`, `top_p`, `top_k` per FR-008):
  - For creative recommendations (`get_recommendations` used by `recommend` and `radio`): `thinking_level="medium"`.
  - For high-volume batch genre classification (`classify_tracks_genres` used by `organize`): target `thinking_level="minimal"` per FR-016, with automatic compatibility protection: if the resolved model does not support `"minimal"` (per official Gemini Thinking docs, `gemini-3.8-flash`, `gemini-4-*`, and `gemini-3.1-pro-preview` only support `low`, `medium`, `high` and reject `minimal`), downgrade cleanly to `"low"` (either proactively for known non-`minimal` models or reactively on a 400 invalid-`thinking_level` error without consuming retry budget) and log at `INFO`/`DEBUG` level!
- **Rationale**: Official Gemini Thinking docs explicitly state that `minimal` is supported on `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3.6-flash`, and `gemini-3-flash-preview`, but **not supported on `gemini-3.8-flash` or Gemini 4 models**. Because `gemini-flash-latest` may point to `gemini-3.8-flash` (or a future Flash model), proactive/reactive fallback from `minimal` → `low` guarantees `tde organize` never crashes with HTTP 400 while still using `minimal` on every model that supports it (`*-flash-lite`, etc.)!
- **Alternatives Considered**:
  - Unconditionally sending `thinking_level="minimal"` on `organize` with no fallback: Rejected because official docs prove `gemini-3.8-flash` rejects `minimal` with a 400 client error, which would break `tde organize` out of the box when `gemini-flash-latest` maps to `gemini-3.8-flash`.
  - Sending `low` everywhere on `organize`: Rejected because FR-016 specifies `minimal` for `organize`, and `minimal` works natively on Flash-Lite and 3.6-Flash models.

### R-007: Per-Request Client Timeouts & Flex Inference Parity
- **Decision**: Instantiate `genai.Client(api_key=api_key, http_options={"timeout": timeout_ms})` using the resolved tier timeout (`120_000` ms for `standard`, `900_000` ms default or `GEMINI_FLEX_TIMEOUT_SECONDS * 1000` for `flex`) and pass `service_tier=tier` (`"standard"` or `"flex"`) as a top-level argument to `client.interactions.create(...)`.
- **Rationale**: Official Flex Inference docs show `client = genai.Client(http_options={"timeout": 900000})` combined with `client.interactions.create(..., service_tier="flex")`. Note that when falling back from `flex` to `standard` (via recursive call with `flex=False`), the fallback call constructs a fresh client with `standard_timeout_ms` (`120_000` ms) and `service_tier="standard"`, preserving exact timeout isolation!
- **Alternatives Considered**:
  - Passing `types.HttpOptions` inside `GenerateContentConfig`: No longer applicable because `GenerateContentConfig` is retired in the Interactions API.

### R-008: Interaction Status, Error Extraction, and Exception Compatibility
- **Decision**:
  1. **Interaction response state classification** (`_classify_interaction_state`): Inspect `interaction.status`:
     - If `status in {"failed", "cancelled"}` (or `interaction.error` is set): classify as `unusable-blocked` / failed with `interaction.error` details.
     - Extract text via `interaction.output_text` (falling back to concatenating `text` parts from trailing `model_output` steps in `interaction.steps`).
     - Validate JSON against `RecommendationList` (or `GenreClassificationList`). If empty or invalid JSON/schema, classify as `unusable-empty` and trigger the single recovery retry (FR-011).
  2. **Unified error code extraction & exception catching**: Extract HTTP status code from `getattr(error, "status_code", None)` OR `getattr(error, "code", None)` so both `genai.errors.ClientError` / `ServerError` / `APIError` AND `google-genai` Interactions client exceptions (e.g., Stainless `APIStatusError`, `RateLimitError`, `InternalServerError`, `APITimeoutError`, `APIConnectionError`) are classified identically into the 10 documented categories (`auth`, `permission`, `quota`, `unavailable/not-found`, `flex-capacity`, `flex-timeout`, `timeout`, `response-handling`, `server`, `client`)!
- **Rationale**: `google-genai` 2.x/3.x Interactions client may raise either `genai.errors` subclasses or `_interactions` HTTP status/timeout exceptions depending on transport layer. Unified status-code and timeout detection ensures zero unhandled SDK exceptions leak past `gemini_service.py` and preserves 100% of existing retry, fallback, and diagnostic contracts.
- **Alternatives Considered**:
  - Catching only `genai.errors.ClientError` / `ServerError`: Rejected because Interactions client methods in `google-genai >= 2.0` can raise Stainless-derived `APIStatusError` / `APITimeoutError` exceptions that do not inherit from `genai.errors.ClientError`.

### R-009: Scope of Codebase & Test Impact
- **Decision**: Keep all Gemini API migration changes encapsulated inside `src/services/gemini_service.py` (preserving public function signatures for `get_recommendations`, `classify_tracks_genres`, `_resolve_service_tier`, and `GeminiModelUnavailableError`), so `src/cli/main.py` and `src/services/genre_organizer_service.py` require **zero** signature changes! Update `pyproject.toml` (`uv.lock`), `tests/test_gemini_service.py` (and any CLI/organizer tests that mock Gemini calls), `README.md`, and `.env.example`.
- **Rationale**: Honors Constitution Principle IV (*Extensibility*: loose coupling via `gemini_service` boundary) and Principle I (*User-Centricity*: zero breaking changes to CLI commands or flags).
- **Alternatives Considered**:
  - Creating a second parallel service module (`gemini_interactions_service.py`): Rejected as unnecessary indirection; `gemini_service.py` is already the single cohesive service abstraction for Gemini.
