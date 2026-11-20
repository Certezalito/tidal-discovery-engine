# Service & CLI Interface Contract: Gemini Interactions Migration

**Feature**: `022-migrate-gemini-interactions`  
**Date**: 2026-11-19  
**Source Spec**: [spec.md](../spec.md)

## 1. Public Python Service Contract (`src/services/gemini_service.py`)

All existing callers (`src/cli/main.py` and `src/services/genre_organizer_service.py`) MUST continue to work with zero breaking signature changes.

### `get_recommendations(...) -> list[dict]`
```python
def get_recommendations(
    api_key: str,
    seed_tracks: list,
    count: int,
    shuffle: bool = False,
    flex: bool | None = None,
    flex_fallback_standard: bool | None = None,
    on_fallback: Any | None = None,
) -> list[dict]:
```
- **Input**: Tidal seed tracks, desired recommendation count, deep-cuts toggle (`shuffle`), service-tier controls (`flex`, `flex_fallback_standard`, `on_fallback`).
- **Behavior**:
  - Resolves primary/fallback models (applying `gemini-flash-latest` default and deprecated `1.5`/`2.0`/`2.5` auto-substitution with warning).
  - Resolves service tier and timeout (`standard`: `120_000` ms; `flex`: `GEMINI_FLEX_TIMEOUT_SECONDS * 1000`, default `900_000` ms).
  - Instantiates `genai.Client(api_key=api_key, http_options={"timeout": timeout_ms})`.
  - Dispatches `client.interactions.create(...)` with:
    - `model=<resolved_model>`
    - `input=<prompt>`
    - `store=False`
    - `service_tier=<tier>`
    - `response_format={"type": "text", "mime_type": "application/json", "schema": RecommendationList.model_json_schema()}`
    - `generation_config={"thinking_level": "medium"}`
  - Validates response via `RecommendationList.model_validate_json(...)` and returns up to `count` normalized dicts (`{"artist": str, "title": str}`).
- **Errors**:
  - Raises `GeminiModelUnavailableError` when the primary model is unavailable/not-found and no distinct `GEMINI_FALLBACK_MODEL` is configured (allowing `tde radio --gemini` to fall back to Last.fm).
  - Raises `ValueError` with standardized actionable diagnostic message (`model='...', category='...', details='...'. Next step: ...`) for all other terminal failures.

### `classify_tracks_genres(...) -> list[dict]`
```python
def classify_tracks_genres(
    api_key: str,
    tracks: list,
    flex: bool | None = None,
    flex_fallback_standard: bool | None = None,
    on_fallback: Any | None = None,
) -> list[dict]:
```
- **Input**: Batch of track dicts (`artist`, `title`, optional `isrc`) and service-tier controls.
- **Behavior**:
  - Resolves primary model (applying `gemini-flash-latest` default and deprecated-model auto-substitution with warning) and service tier/timeout.
  - Instantiates `genai.Client(api_key=api_key, http_options={"timeout": timeout_ms})`.
  - Dispatches `client.interactions.create(...)` with:
    - `model=<resolved_model>`
    - `input=<prompt>`
    - `store=False`
    - `service_tier=<tier>`
    - `response_format={"type": "text", "mime_type": "application/json", "schema": GenreClassificationList.model_json_schema()}`
    - `generation_config={"thinking_level": "minimal"}` (automatically downgrading to `"low"` if the target model does not support `"minimal"`).
  - Validates response via `GenreClassificationList.model_validate_json(...)` and returns normalized dicts with keys `artist`, `title`, `isrc`, `primary_genre`, `genre` (legacy alias), and `sub_genres` (list of up to 3 strings).
  - Invokes `on_fallback()` on flex-to-standard transition so `genre_organizer_service.py` enforces sticky standard tier for subsequent batches.

---

## 2. Error Classification Contract

Both `genai.errors` exceptions (`ClientError`, `ServerError`, `APIError`) and Interactions HTTP/timeout exceptions (carrying `.status_code` or `.code`, or `TimeoutError`) MUST map consistently to:

| Category | Trigger Condition | Retryable? | Fallback Trigger |
|----------|-------------------|------------|------------------|
| `unavailable/not-found` | HTTP `404` or model not found/unavailable message | No | `GEMINI_FALLBACK_MODEL` (or Last.fm in `radio`) |
| `auth` | HTTP `401` or API key / unauthorized / authentication error | No | None |
| `permission` | HTTP `403` or permission / forbidden error | No | None |
| `quota` | HTTP `429` (on `standard` tier) or quota/rate-limit error | Yes (standard: 1 retry) | None |
| `flex-capacity` | HTTP `429` or `503` (on `flex` tier) or capacity/demand message | Yes (flex: progressive retries) | Standard tier if `flex_fallback_standard=True` |
| `flex-timeout` | Timeout/deadline exceeded on `flex` tier | No (after timeout) | Standard tier if `flex_fallback_standard=True` |
| `timeout` | Timeout/deadline exceeded on `standard` tier | No | None |
| `response-handling` | `status in {"failed", "cancelled"}`, `interaction.error`, empty `output_text`, or invalid JSON/schema | Yes (1 recovery retry) | None |
| `server` | HTTP `5xx` (non-flex-capacity) | Yes | None |
| `client` | HTTP `400`/`422` or other client error | No (except `minimal`→`low` thinking compatibility retry) | None |

---

## 3. CLI & Configuration Compatibility Contract

Zero breaking changes across all commands, flags, aliases, and `.env` keys:
- **Commands**: `tde recommend`, `tde radio`, `tde organize` (alias `tde genre-organizer`), plus `tidal-discovery-engine` and `python -m src.cli.main`.
- **Flags**: `--gemini`, `--shuffle`, `--exclude-favorites`, `--flex` / `--no-flex`, `--flex-fallback-standard` / `--no-flex-fallback-standard`, `--refresh-genres`, `--wipe-folder` / `--wipe`, `--wipe-only`, `--yes` / `-y`.
- **Environment / `.env` Keys**: `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-flash-latest`), `GEMINI_FALLBACK_MODEL`, `GEMINI_SERVICE_TIER`, `GEMINI_FLEX_TIMEOUT_SECONDS`, `GEMINI_FLEX_MAX_RETRIES`, `GEMINI_FLEX_FALLBACK_STANDARD`, `GEMINI_SERVICE_TIER_FALLBACK`.
- **Exit Behavior**: `SIGINT` (`Ctrl+C`) prints `Operation canceled by user.` and exits with code `130`.
