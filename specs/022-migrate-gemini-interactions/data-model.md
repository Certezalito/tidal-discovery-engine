# Phase 1 Data Model: Migrate to Current Gemini Interaction Method

**Feature**: `022-migrate-gemini-interactions`  
**Date**: 2026-11-19  
**Source Spec**: [spec.md](./spec.md)

## Structured Output Schemas (Pydantic)

All Gemini Interactions API calls enforce JSON Schema structured output via `response_format={"type": "text", "mime_type": "application/json", "schema": <Model>.model_json_schema()}` and validate the returned `interaction.output_text` via `<Model>.model_validate_json(...)`.

### 1. `Song` (Track Recommendation Item)
Represents a single AI-generated song suggestion strictly grounded in human-readable attributes (Constitution Principle VIII: Zero ISRC Hallucination).

| Field | Type | Required | Constraints / Notes |
|-------|------|----------|---------------------|
| `artist` | `str` | Yes | Non-empty artist name; trimmed during normalization. |
| `title` | `str` | Yes | Non-empty track title; trimmed during normalization. |

*Note*: `isrc` is intentionally omitted from the prompt and structured schema so Gemini is never asked or permitted to hallucinate ISRCs. Normalized output dicts returned to callers (`get_recommendations`) contain `{"artist": str, "title": str}` (and `isrc: None` only if needed for backward-compatible dict key consumers, never populated by AI).

### 2. `RecommendationList` (Structured Wrapper for `get_recommendations`)
Top-level JSON object wrapper required by the Interactions API `response_format` schema contract.

| Field | Type | Required | Constraints / Notes |
|-------|------|----------|---------------------|
| `songs` | `list[Song]` | Yes | Ordered list of recommended songs; capped at requested `count` after validation. |

### 3. `GenreClassificationResult` (Track Genre Classification Item)
Represents the multi-genre categorization for a single library track in `classify_tracks_genres`.

| Field | Type | Required | Constraints / Notes |
|-------|------|----------|---------------------|
| `isrc` | `str \| None` | No | Echoed from input library track metadata (never synthesized for unknown tracks). |
| `title` | `str \| None` | No | Track title from input batch. |
| `artist` | `str \| None` | No | Artist name from input batch. |
| `primary_genre` | `str \| None` | No | Exactly 1 specific, recognized musical genre (avoiding broad umbrella labels when specific styles apply). |
| `sub_genres` | `list[str]` | No (default `[]`) | Up to 3 specific sub-genres; cleaned, trimmed, and capped at 3 items post-validation. |

*Normalization*: Output dicts retain the legacy `"genre"` alias equal to `"primary_genre"` for full read/write compatibility with existing `GenreCacheService` SQLite rows (`data/genre_cache.db`).

### 4. `GenreClassificationList` (Structured Wrapper for `classify_tracks_genres`)
Top-level JSON object wrapper required by the Interactions API `response_format` schema contract.

| Field | Type | Required | Constraints / Notes |
|-------|------|----------|---------------------|
| `classifications` | `list[GenreClassificationResult]` | Yes | List of classified tracks corresponding to the input batch. |

---

## Domain Configuration & Runtime Entities

### 5. `ResolvedModelConfig`
Logical configuration resolved per Gemini invocation from `os.environ` → `.env` → built-in default.

| Attribute | Type | Resolution Rules |
|-----------|------|------------------|
| `primary_model` | `str` | Normalized `GEMINI_MODEL`. Blank/unset/`latest`/`auto`/`flash-latest` → `gemini-flash-latest`. Deprecated legacy prefixes (`gemini-1.5-*`, `gemini-2.0-*`, `gemini-2.5-*`) → substituted with `gemini-flash-latest` + `WARNING` log. |
| `model_source` | `str` | `"env"`, `"dotenv"`, or `"default"`. |
| `fallback_model` | `str \| None` | Normalized `GEMINI_FALLBACK_MODEL`. Deprecated legacy prefixes also substituted with `gemini-flash-latest` + `WARNING` log; ignored if identical to `primary_model`. |

### 6. `InteractionRequestConfig`
Logical configuration passed to `client.interactions.create(...)` and `genai.Client(...)`.

| Attribute | Type | Values & Rules |
|-----------|------|----------------|
| `model` | `str` | Active resolved model ID (`primary_model` or `fallback_model`). |
| `input` | `str` | Minimal, token-efficient prompt string (Principle VI). |
| `store` | `bool` | Always `False` (FR-009: strictly stateless, privacy-first). |
| `service_tier` | `str` | `"standard"` (default) or `"flex"` (resolved via CLI flag > env > `.env` > default). |
| `response_format` | `dict` | `{"type": "text", "mime_type": "application/json", "schema": <Wrapper>.model_json_schema()}`. |
| `generation_config` | `dict` | `{"thinking_level": "medium"}` for recommendations; `{"thinking_level": "minimal"}` (falling back to `"low"` on models that do not support `"minimal"`) for genre classification. No `temperature`, `top_p`, or `top_k`. |
| `timeout_ms` | `int` | `120_000` ms (`standard`) or `GEMINI_FLEX_TIMEOUT_SECONDS * 1000` (default `900_000` ms for `flex`), passed via `genai.Client(api_key=..., http_options={"timeout": timeout_ms})`. |

---

## State Transitions

### Interaction Response Evaluation State Machine
```text
[client.interactions.create(...)]
        │
        ├── Exception raised
        │     ├── 400 + unsupported thinking_level="minimal" ─► Downgrade to thinking_level="low" (same attempt, no retry penalty)
        │     ├── Retryable (429 / 5xx) & attempts remaining ─► Sleep backoff (standard: 2s; flex: 5/10/20/30/60s) ─► Retry
        │     ├── Flex exhausted / timeout & fallback_standard=True ─► Log WARNING, invoke on_fallback(), re-run on tier="standard"
        │     ├── Primary model 404/unavailable & fallback_model set ─► Log WARNING, retry with fallback_model
        │     ├── Primary model 404/unavailable & no fallback_model ─► Raise GeminiModelUnavailableError (radio falls back to Last.fm)
        │     └── Non-retryable (401/403/400/exhausted) ─► Raise ValueError(actionable_error)
        │
        └── Interaction returned
              ├── status in {"failed", "cancelled"} or interaction.error set ─► "unusable-blocked"
              ├── output_text empty / invalid JSON / fails Pydantic validation ─► "unusable-empty"
              │     └── If attempts remaining ─► Sleep backoff ─► Single recovery retry (FR-011)
              │     └── Else ─► Raise ValueError(category="response-handling")
              └── Validated non-empty payload ─► "usable" ─► Return normalized list[dict]
```
