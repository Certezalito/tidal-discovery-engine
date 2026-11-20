import logging
import os
import re
import threading
import time
from contextlib import contextmanager
from typing import Any

from dotenv import dotenv_values
from google import genai
from pydantic import BaseModel, Field, ValidationError


# Built-in default model retained per FR-006 so users automatically track Google's latest Flash release.
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
# Interactions API v1beta is required for dynamic aliases (gemini-flash-latest), preview models, and flex tier.
DEFAULT_GEMINI_API_VERSION = "v1beta"
_DEFAULT_WARNING_EMITTED = False

# Recovery retry settings for standard and flex service tiers.
RECOVERY_RETRY_LIMIT = 1
RETRY_BACKOFF_SECONDS = 2.0
DEFAULT_FLEX_RETRY_LIMIT = 5  # Flex mode allows up to 5 progressive retries for capacity spikes
DEFAULT_FLEX_BACKOFF_SCHEDULE = [5.0, 10.0, 20.0, 30.0, 60.0]  # Progressive backoff schedule (seconds)

# Service tier and timeout constants for Gemini inference (Principle VI: Cost Efficiency).
DEFAULT_SERVICE_TIER = "standard"
DEFAULT_STANDARD_TIMEOUT_MS = 120_000  # 2 minutes default interactive timeout
DEFAULT_FLEX_TIMEOUT_SECONDS = 900  # 15 minutes default flex tier turnaround timeout
DEFAULT_FLEX_HEARTBEAT_INTERVAL_SECONDS = 15.0  # Periodic heartbeat interval during flex queue waiting

# Task-tailored thinking levels on current-generation Gemini models (FR-016, Principle VI).
# Creative music curation benefits from deeper reasoning ("medium"), whereas high-volume batch
# genre classification targets "minimal" thinking to minimize hidden thought tokens and latency.
RECOMMENDATION_THINKING_LEVEL = "medium"
CLASSIFICATION_THINKING_LEVEL = "minimal"
CLASSIFICATION_THINKING_FALLBACK_LEVEL = "low"

# Deprecated legacy Gemini model families (1.5, 2.0, 2.5) automatically substituted with
# DEFAULT_GEMINI_MODEL plus a warning log so existing .env setups and cron jobs keep running (FR-007).
_DEPRECATED_LEGACY_MODEL_PATTERN = re.compile(
    r"^gemini-(?:1\.5|2\.0|2\.5)(?:[-.].*)?$",
    re.IGNORECASE,
)

# Models documented by Google as supporting low/medium/high thinking but rejecting "minimal".
# Proactively downgrading avoids an unnecessary 400 round-trip; reactive 400 fallback also protects
# dynamic aliases like gemini-flash-latest if they point to one of these models upstream.
_NON_MINIMAL_THINKING_MODEL_PATTERNS = (
    re.compile(r"^gemini-3\.8-flash(?:[-.].*)?$", re.IGNORECASE),
    re.compile(r"^gemini-4(?:[-.].*)?$", re.IGNORECASE),
    re.compile(r"^gemini-3(?:\.1)?-pro(?:[-.].*)?$", re.IGNORECASE),
)

# Terminal Interaction statuses that indicate the response failed or was canceled before completion.
_UNUSABLE_INTERACTION_STATUSES = {"failed", "cancelled"}


class GeminiModelUnavailableError(ValueError):
    """Raised when the configured Gemini model is unavailable or not found."""


class Song(BaseModel):
    """
    Strictly human-readable song suggestion returned by Gemini (Principle VIII: Zero ISRC Hallucination).
    ISRCs are intentionally excluded so the model is never prompted or allowed to fabricate catalog codes.
    """

    artist: str
    title: str


class RecommendationList(BaseModel):
    """Top-level JSON object wrapper required by the Interactions API response_format schema contract."""

    songs: list[Song] = Field(default_factory=list)


class GenreClassificationResult(BaseModel):
    """Structured multi-genre categorization for a single library track."""

    isrc: str | None = None
    title: str | None = None
    artist: str | None = None
    primary_genre: str | None = None
    sub_genres: list[str] = Field(
        default_factory=list,
        description="Up to 3 specific sub-genres, excluding broad umbrella categories",
    )
    genre: str | None = None  # Legacy alias preserved for backward compatibility with GenreCacheService


class CompactGenreClassification(BaseModel):
    """
    Token-optimized wire schema for Gemini batch genre classification (Principle VI).
    Uses short field names and track index IDs instead of echoing artist, title, and ISRC
    back from the model; Python maps each `id` back to the authoritative input track metadata.
    """

    id: int = Field(description="Zero-based index of the input song")
    p: str | None = Field(
        default=None,
        description="Single specific primary genre (avoid generic umbrella labels like Rock/Pop/Electronic when specific styles apply)",
    )
    s: list[str] = Field(
        default_factory=list,
        description="Up to 3 specific sub-genres or micro-genres, excluding broad umbrella categories",
    )


class GenreClassificationList(BaseModel):
    """Top-level JSON object wrapper required by the Interactions API response_format schema contract."""

    classifications: list[CompactGenreClassification] = Field(default_factory=list)


def _create_genai_client(api_key: str, timeout_ms: int):
    """
    Creates a google-genai Client configured with the resolved request timeout in milliseconds
    and the v1beta Interactions API version (required for aliases like gemini-flash-latest,
    preview models, and preview flex inference).
    """
    try:
        return genai.Client(
            api_key=api_key,
            http_options={"timeout": timeout_ms, "api_version": DEFAULT_GEMINI_API_VERSION},
        )
    except Exception as exc:
        logging.error("Failed to initialize Gemini Client: %s", exc)
        raise ValueError("Invalid Gemini API Configuration") from exc


def _extract_error_code(error) -> int | None:
    """
    Extracts an HTTP status code from either legacy genai.errors exceptions (`.code`)
    or Interactions API SDK exceptions (`.status_code`).
    """
    for attr in ("status_code", "code"):
        raw = getattr(error, attr, None)
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                continue
    return None


def _is_timeout_error(error) -> bool:
    """Identifies standard TimeoutError, SDK APITimeoutError, and deadline/timeout error messages."""
    if isinstance(error, TimeoutError):
        return True
    if "timeout" in type(error).__name__.lower():
        return True
    message = str(error).lower()
    return "timeout" in message or "timed out" in message or "deadline" in message


def _is_server_error(error) -> bool:
    """Identifies 5xx server failures across genai.errors.ServerError and Interactions APIStatusError."""
    if isinstance(error, genai.errors.ServerError):
        return True
    code = _extract_error_code(error)
    return code is not None and code >= 500


def _is_client_error(error) -> bool:
    """Identifies 4xx client failures across genai.errors.ClientError and Interactions APIStatusError."""
    if isinstance(error, genai.errors.ClientError):
        return True
    code = _extract_error_code(error)
    return code is not None and 400 <= code < 500


def _is_retryable_status_code(code: int | None) -> bool:
    return code == 429 or (code is not None and code >= 500)


def _is_unsupported_minimal_thinking_error(error, thinking_level: str) -> bool:
    """
    Detects HTTP 400 validation errors caused by requesting thinking_level='minimal' on a model
    (such as gemini-3.8-flash or Gemini 4) that only supports low/medium/high thinking levels.
    """
    if thinking_level != CLASSIFICATION_THINKING_LEVEL:
        return False
    code = _extract_error_code(error)
    if code not in (None, 400, 422):
        return False
    message = str(error).lower()
    return (
        "thinking_level" in message
        or ("thinking" in message and ("minimal" in message or "unsupported" in message or "not supported" in message or "invalid" in message))
    )


def _resolve_classification_thinking_level(model_name: str) -> str:
    """
    Selects the lowest supported thinking_level for batch genre classification (FR-016).
    Targets 'minimal' to conserve tokens, proactively falling back to 'low' for model families
    known not to support 'minimal' so requests avoid an unnecessary 400 round-trip.
    """
    for pattern in _NON_MINIMAL_THINKING_MODEL_PATTERNS:
        if pattern.match(model_name or ""):
            logging.info(
                "Model '%s' does not support thinking_level='%s'; using '%s' for genre classification.",
                model_name,
                CLASSIFICATION_THINKING_LEVEL,
                CLASSIFICATION_THINKING_FALLBACK_LEVEL,
            )
            return CLASSIFICATION_THINKING_FALLBACK_LEVEL
    return CLASSIFICATION_THINKING_LEVEL


def _build_interaction_request(
    model_name: str,
    prompt: str,
    response_schema_model: type[BaseModel],
    service_tier: str,
    thinking_level: str,
) -> dict[str, Any]:
    """
    Builds the plain-dict keyword payload for client.interactions.create(...).
    Enforces:
    - Stateless privacy-first execution (store=False, FR-009)
    - Structured JSON Schema output via top-level response_format (FR-003, Principle VI)
    - Service tier routing (standard vs flex, FR-012)
    - Current-generation thinking_level without retired sampling controls (FR-008, FR-016)
    """
    return {
        "model": model_name,
        "input": prompt,
        "store": False,
        "service_tier": service_tier,
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": response_schema_model.model_json_schema(),
        },
        "generation_config": {
            "thinking_level": thinking_level,
        },
    }


def _extract_interaction_text(interaction) -> str | None:
    """
    Extracts final text from an Interaction object.
    Prefers the official SDK convenience property `interaction.output_text`, falling back to
    concatenating text content blocks from the trailing `model_output` steps in `interaction.steps`.
    """
    output_text = getattr(interaction, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    steps = getattr(interaction, "steps", None) or []
    collected_chunks: list[str] = []
    # Walk backward across trailing model_output steps to match SDK output_text semantics.
    for step in reversed(steps):
        step_type = step.get("type") if isinstance(step, dict) else getattr(step, "type", None)
        if step_type != "model_output":
            if collected_chunks:
                break
            continue

        content_items = step.get("content") if isinstance(step, dict) else getattr(step, "content", None)
        step_texts: list[str] = []
        for item in content_items or []:
            item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
            item_text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
            if (item_type in (None, "text")) and isinstance(item_text, str) and item_text:
                step_texts.append(item_text)
        if step_texts:
            collected_chunks.insert(0, "".join(step_texts))

    joined = "".join(collected_chunks).strip()
    return joined if joined else None


def _check_interaction_terminal_failure(interaction) -> str | None:
    """
    Inspects an Interaction for failed/cancelled status or an explicit provider error payload.
    Returns a diagnostic detail string when unusable, or None when the interaction may be parsed.
    """
    status = getattr(interaction, "status", None)
    if status and str(status).strip().lower() in _UNUSABLE_INTERACTION_STATUSES:
        error_detail = getattr(interaction, "error", None)
        if error_detail:
            return f"interaction.status={status}, error={error_detail}"
        return f"interaction.status={status}"

    error_detail = getattr(interaction, "error", None)
    if error_detail:
        return f"interaction.error={error_detail}"

    return None


def _normalize_seed_track(track):
    artist_obj = getattr(track, "artist", None)
    artist_name = getattr(artist_obj, "name", None)
    title = getattr(track, "name", None) or getattr(track, "title", None)

    normalized_artist = str(artist_name).strip() if artist_name else "Unknown Artist"
    normalized_title = str(title).strip() if title else "Unknown Title"
    return {"artist": normalized_artist, "title": normalized_title}


def _build_seed_descriptions(seed_tracks):
    descriptions = []
    for track in seed_tracks:
        normalized = _normalize_seed_track(track)
        descriptions.append(f"- {normalized['artist']} - {normalized['title']}")
    return descriptions


def _cap_recommendations(recommendations, count):
    if count <= 0:
        return []
    return recommendations[:count]


def _normalize_model_name(value):
    if value is None:
        return None

    normalized = str(value).strip()
    if not normalized:
        return None

    if normalized.lower() in {"latest", "auto", "flash-latest"}:
        return DEFAULT_GEMINI_MODEL

    return normalized


def _substitute_deprecated_model(model_name: str, env_var_name: str) -> str:
    """
    Replaces deprecated legacy Gemini model families (gemini-1.5-*, gemini-2.0-*, gemini-2.5-*)
    with DEFAULT_GEMINI_MODEL and logs a warning so unattended schedules keep running (FR-007).
    """
    if _DEPRECATED_LEGACY_MODEL_PATTERN.match(model_name):
        logging.warning(
            "Configured %s '%s' is a deprecated legacy Gemini model; automatically substituting '%s'. "
            "Please update your configuration to a current model or leave %s blank.",
            env_var_name,
            model_name,
            DEFAULT_GEMINI_MODEL,
            env_var_name,
        )
        return DEFAULT_GEMINI_MODEL
    return model_name


def _read_dotenv_values():
    try:
        return dotenv_values(".env")
    except Exception as exc:
        logging.warning("Unable to read .env for Gemini model configuration: %s", exc)
        return {}


def _resolve_from_env_then_dotenv(key, dotenv_config):
    env_value = os.environ.get(key)
    if env_value is not None:
        return env_value, "env"

    dotenv_value = dotenv_config.get(key)
    if dotenv_value is not None:
        return dotenv_value, "dotenv"

    return None, "default"


def _resolve_primary_model(dotenv_config):
    global _DEFAULT_WARNING_EMITTED

    raw_value, source = _resolve_from_env_then_dotenv("GEMINI_MODEL", dotenv_config)
    normalized = _normalize_model_name(raw_value)

    if normalized:
        resolved = _substitute_deprecated_model(normalized, "GEMINI_MODEL")
        return resolved, source

    if not _DEFAULT_WARNING_EMITTED:
        logging.warning(
            "GEMINI_MODEL is missing or blank; using default model '%s' for this CLI invocation.",
            DEFAULT_GEMINI_MODEL,
        )
        _DEFAULT_WARNING_EMITTED = True

    return DEFAULT_GEMINI_MODEL, "default"


def _resolve_fallback_model(dotenv_config):
    raw_value, _ = _resolve_from_env_then_dotenv("GEMINI_FALLBACK_MODEL", dotenv_config)
    normalized = _normalize_model_name(raw_value)
    if not normalized:
        return None
    return _substitute_deprecated_model(normalized, "GEMINI_FALLBACK_MODEL")


def _resolve_organize_model(dotenv_config):
    """
    Resolves the Gemini model for library genre organization (`tde organize`).
    Precedence: GEMINI_ORGANIZE_MODEL (env -> .env) -> GEMINI_MODEL (env -> .env) -> gemini-flash-latest.
    Automatically substitutes deprecated legacy 1.5/2.0/2.5 models with DEFAULT_GEMINI_MODEL.
    """
    raw_value, source = _resolve_from_env_then_dotenv("GEMINI_ORGANIZE_MODEL", dotenv_config)
    normalized = _normalize_model_name(raw_value)
    if normalized:
        resolved = _substitute_deprecated_model(normalized, "GEMINI_ORGANIZE_MODEL")
        return resolved, source
    return _resolve_primary_model(dotenv_config)


def _resolve_flex_timeout_seconds(dotenv_config):
    """
    Resolves client timeout in seconds for Gemini flex tier requests (Principle I & V).
    Reads GEMINI_FLEX_TIMEOUT_SECONDS from os.environ, then .env, defaulting to 900 seconds (15 min).
    Non-positive or non-integer values log a warning and fall back to the 900-second default.
    """
    raw_value, _ = _resolve_from_env_then_dotenv("GEMINI_FLEX_TIMEOUT_SECONDS", dotenv_config)
    if raw_value is None or not str(raw_value).strip():
        return DEFAULT_FLEX_TIMEOUT_SECONDS

    try:
        val = int(str(raw_value).strip())
        if val <= 0:
            logging.warning(
                "Invalid GEMINI_FLEX_TIMEOUT_SECONDS '%s'; defaulting to %s seconds.",
                raw_value,
                DEFAULT_FLEX_TIMEOUT_SECONDS,
            )
            return DEFAULT_FLEX_TIMEOUT_SECONDS
        return val
    except (ValueError, TypeError):
        logging.warning(
            "Invalid GEMINI_FLEX_TIMEOUT_SECONDS '%s'; defaulting to %s seconds.",
            raw_value,
            DEFAULT_FLEX_TIMEOUT_SECONDS,
        )
        return DEFAULT_FLEX_TIMEOUT_SECONDS


def _resolve_service_tier(cli_flex=None, dotenv_config=None):
    """
    Resolves the target Gemini inference tier, configuration source, and client timeout in milliseconds.

    Precedence:
    1. Explicit CLI flag:
       cli_flex is True  -> ('flex', 'cli', timeout_ms)
       cli_flex is False -> ('standard', 'cli', timeout_ms)
    2. Environment Variable (GEMINI_SERVICE_TIER):
       'flex'            -> ('flex', source, timeout_ms)
       'standard'        -> ('standard', source, timeout_ms)
       unrecognized      -> warning logged, returns ('standard', 'default', timeout_ms)
    3. Default:
       ('standard', 'default', timeout_ms)

    Returns:
        tuple[str, str, int]: (tier, source, timeout_ms)
    """
    if dotenv_config is None:
        dotenv_config = _read_dotenv_values()

    flex_timeout_s = _resolve_flex_timeout_seconds(dotenv_config)
    flex_timeout_ms = flex_timeout_s * 1000
    standard_timeout_ms = DEFAULT_STANDARD_TIMEOUT_MS

    if cli_flex is True:
        return "flex", "cli", flex_timeout_ms
    if cli_flex is False:
        return "standard", "cli", standard_timeout_ms

    raw_tier, source = _resolve_from_env_then_dotenv("GEMINI_SERVICE_TIER", dotenv_config)
    if raw_tier is not None:
        normalized = str(raw_tier).strip().lower()
        if normalized == "flex":
            return "flex", source, flex_timeout_ms
        elif normalized == "standard":
            return "standard", source, standard_timeout_ms
        elif normalized:
            logging.warning(
                "Unrecognized GEMINI_SERVICE_TIER '%s'; defaulting to 'standard'.",
                raw_tier,
            )
    return "standard", "default", standard_timeout_ms


def _resolve_flex_fallback_standard(cli_fallback=None, dotenv_config=None):
    """
    Resolves whether to automatically fall back to standard tier on flex capacity exhaustion.

    Precedence:
    1. Explicit CLI flag (`--flex-fallback-standard` / `--no-flex-fallback-standard`)
    2. Environment Variable / .env (`GEMINI_FLEX_FALLBACK_STANDARD`, alias `GEMINI_SERVICE_TIER_FALLBACK`)
    3. Default: (False, 'default') for strict cost protection (Principle VI).
    """
    if dotenv_config is None:
        dotenv_config = _read_dotenv_values()

    if cli_fallback is True:
        return True, "cli"
    if cli_fallback is False:
        return False, "cli"

    # Check primary GEMINI_FLEX_FALLBACK_STANDARD, then alias GEMINI_SERVICE_TIER_FALLBACK.
    raw_val, source = _resolve_from_env_then_dotenv("GEMINI_FLEX_FALLBACK_STANDARD", dotenv_config)
    var_name = "GEMINI_FLEX_FALLBACK_STANDARD"
    if raw_val is None:
        raw_val, source = _resolve_from_env_then_dotenv("GEMINI_SERVICE_TIER_FALLBACK", dotenv_config)
        var_name = "GEMINI_SERVICE_TIER_FALLBACK"

    if raw_val is not None:
        norm = str(raw_val).strip().lower()
        if norm in ("true", "1", "yes", "standard"):
            return True, source
        elif norm in ("false", "0", "no", "none", "off"):
            return False, source
        elif norm:
            logging.warning(
                "Invalid %s '%s'; defaulting to false.",
                var_name,
                raw_val,
            )
            return False, "default"

    return False, "default"


def _resolve_flex_max_retries(dotenv_config=None):
    if dotenv_config is None:
        dotenv_config = {}
    env_val = os.environ.get("GEMINI_FLEX_MAX_RETRIES")
    if env_val is None:
        env_val = dotenv_config.get("GEMINI_FLEX_MAX_RETRIES")

    if env_val is not None:
        try:
            val = int(str(env_val).strip())
            if val > 0:
                return val
            logging.warning("GEMINI_FLEX_MAX_RETRIES must be positive. Falling back to %d.", DEFAULT_FLEX_RETRY_LIMIT)
        except (ValueError, TypeError):
            logging.warning("Invalid GEMINI_FLEX_MAX_RETRIES '%s'. Falling back to %d.", env_val, DEFAULT_FLEX_RETRY_LIMIT)

    return DEFAULT_FLEX_RETRY_LIMIT


def _resolve_retry_limit(service_tier="standard", dotenv_config=None):
    if service_tier == "flex":
        return _resolve_flex_max_retries(dotenv_config)
    return RECOVERY_RETRY_LIMIT


def _get_retry_backoff(attempt: int, service_tier: str = "standard") -> float:
    if service_tier == "flex":
        idx = min(attempt - 1, len(DEFAULT_FLEX_BACKOFF_SCHEDULE) - 1)
        return DEFAULT_FLEX_BACKOFF_SCHEDULE[max(0, idx)]
    return RETRY_BACKOFF_SECONDS


def _classify_client_error(error, service_tier="standard"):
    code = _extract_error_code(error)
    message = str(error).lower()

    if _is_timeout_error(error):
        if service_tier == "flex":
            return "flex-timeout", False
        return "timeout", False

    if code == 404 or ("model" in message and ("not found" in message or "unavailable" in message)):
        return "unavailable/not-found", True
    if code == 401 or "api key" in message or "unauthorized" in message or "authentication" in message:
        return "auth", False
    if code == 403 or "permission" in message or "forbidden" in message:
        return "permission", False
    if code == 429 or "quota" in message or "rate limit" in message or "resource exhausted" in message:
        if service_tier == "flex":
            return "flex-capacity", False
        return "quota", False
    if code in {400, 422}:
        return "client", False

    return "client", False


def _classify_server_error(error, service_tier="standard"):
    code = _extract_error_code(error)
    message = str(error).lower()
    if service_tier == "flex" and (code == 503 or "demand" in message or "unavailable" in message or "capacity" in message):
        return "flex-capacity"
    return "server"


def _classify_response_state(interaction):
    """
    Validates an Interaction response for song recommendations.
    Checks terminal status/errors first, then validates structured JSON against RecommendationList
    via Pydantic and normalizes to strict artist/title-only dicts (Principle VIII).
    """
    terminal_failure = _check_interaction_terminal_failure(interaction)
    if terminal_failure:
        return "unusable-blocked", terminal_failure

    raw_text = _extract_interaction_text(interaction)
    if not raw_text:
        return "unusable-empty", "empty interaction output"

    try:
        parsed_wrapper = RecommendationList.model_validate_json(raw_text)
    except ValidationError as exc:
        return "unusable-empty", f"invalid structured recommendation JSON: {exc}"

    normalized = []
    for song in parsed_wrapper.songs:
        artist = song.artist.strip() if song.artist else ""
        title = song.title.strip() if song.title else ""
        if artist and title:
            normalized.append({"artist": artist, "title": title})

    if not normalized:
        return "unusable-empty", "parsed recommendations missing artist/title"

    return "usable", normalized


def _parse_genre_classification_interaction(interaction, tracks: list[dict] | None = None):
    """
    Validates a compact index-keyed Interaction response for track genre classification and maps
    each returned `id` back onto the authoritative input track metadata (`artist`, `title`, `isrc`).
    Returns (state, payload) where state is 'usable', 'unusable-blocked', or 'unusable-empty'.
    """
    terminal_failure = _check_interaction_terminal_failure(interaction)
    if terminal_failure:
        return "unusable-blocked", terminal_failure

    raw_text = _extract_interaction_text(interaction)
    if not raw_text:
        return "unusable-empty", "empty interaction output"

    try:
        parsed_wrapper = GenreClassificationList.model_validate_json(raw_text)
    except ValidationError as exc:
        return "unusable-empty", f"invalid structured genre classification JSON: {exc}"

    if not parsed_wrapper.classifications:
        return "unusable-empty", "empty genre classification list"

    def _clean_item(item: CompactGenreClassification) -> tuple[str | None, list[str]]:
        primary_genre = item.p.strip() if isinstance(item.p, str) and item.p.strip() else None
        sub_genres_raw = item.s or []
        # Clean and cap sub-genres to at most 3 items per spec (FR-005).
        sub_genres = [str(s).strip() for s in sub_genres_raw if s and str(s).strip()][:3]
        return primary_genre, sub_genres

    # When input tracks are supplied, map by zero-based index so omitted or out-of-order IDs
    # can never shift classifications onto the wrong track in downstream zip() loops.
    if tracks is not None:
        by_id: dict[int, tuple[str | None, list[str]]] = {}
        for item in parsed_wrapper.classifications:
            if 0 <= item.id < len(tracks) and item.id not in by_id:
                by_id[item.id] = _clean_item(item)

        if not by_id:
            return "unusable-empty", "genre classification IDs did not match any input tracks"

        results = []
        for idx, track in enumerate(tracks):
            primary_genre, sub_genres = by_id.get(idx, (None, []))
            results.append(
                {
                    "artist": track.get("artist"),
                    "title": track.get("title"),
                    "isrc": track.get("isrc"),
                    "primary_genre": primary_genre,
                    "genre": primary_genre,  # Legacy alias retained for GenreCacheService SQLite rows
                    "sub_genres": sub_genres,
                }
            )
        return "usable", results

    # Fallback when called directly without tracks context (e.g. isolated parser tests).
    results = []
    for item in parsed_wrapper.classifications:
        primary_genre, sub_genres = _clean_item(item)
        results.append(
            {
                "id": item.id,
                "primary_genre": primary_genre,
                "genre": primary_genre,
                "sub_genres": sub_genres,
            }
        )
    return "usable", results


def _build_actionable_error(model_id, category, error):
    guidance = {
        "unavailable/not-found": "Verify GEMINI_MODEL or GEMINI_FALLBACK_MODEL and ensure the model is available to your account.",
        "auth": "Verify GEMINI_API_KEY and account authentication settings.",
        "quota": "Check Gemini quota/rate limits and retry later.",
        "permission": "Verify account permissions for the configured model.",
        "flex-capacity": "Gemini flex tier capacity is temporarily unavailable due to demand. Retry later, or run with --no-flex (or without --flex) to use the standard tier.",
        "flex-timeout": "Gemini flex tier request timed out due to extended capacity queueing. Retry later, or run with --no-flex to use the standard tier.",
        "timeout": "Gemini request timed out. Check network connectivity and retry later.",
        "response-handling": "Gemini returned an unusable structured response after one recovery retry. Retry later or adjust model configuration.",
        "server": "Gemini service returned a transient server error. Retry later.",
        "client": "Review request configuration and model identifiers.",
    }

    return (
        f"Gemini request failed. model='{model_id}', category='{category}', "
        f"details='{error}'. Next step: {guidance.get(category, guidance['client'])}"
    )


@contextmanager
def _flex_heartbeat(
    service_tier: str,
    timeout_ms: int,
    interval_seconds: float = DEFAULT_FLEX_HEARTBEAT_INTERVAL_SECONDS,
):
    """
    Periodically logs an informational heartbeat during long-running flex requests so the user
    knows the process is actively waiting in Google's opportunistic capacity queue.
    Zero-overhead and immediate return when service_tier != 'flex'.
    """
    if service_tier != "flex":
        yield
        return

    stop_event = threading.Event()
    start_time = time.time()
    timeout_seconds = int(timeout_ms / 1000)

    def _heartbeat_worker():
        while not stop_event.wait(interval_seconds):
            elapsed = int(time.time() - start_time)
            logging.info(
                "Waiting for Gemini Flex opportunistic capacity... (elapsed: %ds / timeout: %ds)",
                elapsed,
                timeout_seconds,
            )

    worker = threading.Thread(target=_heartbeat_worker, daemon=True)
    worker.start()
    try:
        yield
    finally:
        stop_event.set()
        worker.join(timeout=0.5)


def _generate_recommendations_with_model(
    client,
    model_name,
    full_prompt,
    recovery_retries=None,
    service_tier="standard",
    timeout_ms=DEFAULT_STANDARD_TIMEOUT_MS,
):
    """
    Executes a recommendation request via the Gemini Interactions API with retry handling
    for transient capacity/server errors and single-retry recovery for unusable structured outputs.
    """
    if recovery_retries is None:
        recovery_retries = _resolve_retry_limit(service_tier)
    max_attempts = recovery_retries + 1

    request_kwargs = _build_interaction_request(
        model_name=model_name,
        prompt=full_prompt,
        response_schema_model=RecommendationList,
        service_tier=service_tier,
        thinking_level=RECOMMENDATION_THINKING_LEVEL,
    )

    for attempt in range(1, max_attempts + 1):
        try:
            with _flex_heartbeat(service_tier, timeout_ms):
                interaction = client.interactions.create(**request_kwargs)

            state, payload = _classify_response_state(interaction)
            if state == "usable":
                return payload

            if attempt < max_attempts:
                logging.warning(
                    "Gemini response unusable for model '%s' (reason=%s). Retrying...",
                    model_name,
                    payload,
                )
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue

            message = _build_actionable_error(model_name, "response-handling", payload)
            logging.error(message)
            raise ValueError(message)

        except Exception as error:
            if _is_timeout_error(error):
                category, _ = _classify_client_error(error, service_tier=service_tier)
                message = _build_actionable_error(model_name, category, error)
                logging.error(message)
                raise ValueError(message) from error

            if _is_server_error(error):
                code = _extract_error_code(error) or 503
                if attempt < max_attempts:
                    backoff = _get_retry_backoff(attempt, service_tier)
                    if service_tier == "flex":
                        logging.info(
                            "Gemini flex capacity busy (HTTP %s demand spike). Waiting %.0fs for opportunistic capacity to free up (retry %d/%d)...",
                            code,
                            backoff,
                            attempt,
                            recovery_retries,
                        )
                    else:
                        logging.warning(
                            "Gemini server error for model '%s'. Retrying in %.1fs...",
                            model_name,
                            backoff,
                        )
                    time.sleep(backoff)
                    continue
                raise

            if _is_client_error(error):
                status_code = _extract_error_code(error)
                category, _ = _classify_client_error(error, service_tier=service_tier)
                if _is_retryable_status_code(status_code) and attempt < max_attempts:
                    backoff = _get_retry_backoff(attempt, service_tier)
                    if service_tier == "flex":
                        logging.info(
                            "Gemini flex capacity constrained (HTTP %s). Waiting %.0fs for opportunistic capacity to free up (retry %d/%d)...",
                            status_code,
                            backoff,
                            attempt,
                            recovery_retries,
                        )
                    else:
                        logging.warning(
                            "Gemini retryable client error for model '%s' (code=%s, category=%s). Retrying in %.1fs...",
                            model_name,
                            status_code,
                            category,
                            backoff,
                        )
                    time.sleep(backoff)
                    continue
                raise

            raise

    message = _build_actionable_error(model_name, "response-handling", "unknown response state")
    logging.error(message)
    raise ValueError(message)


def get_recommendations(
    api_key: str,
    seed_tracks: list,
    count: int,
    shuffle: bool = False,
    flex: bool | None = None,
    flex_fallback_standard: bool | None = None,
    on_fallback: Any | None = None,
) -> list[dict]:
    """
    Generates song recommendations using the Google Gemini Interactions API.

    Args:
        api_key (str): The Google Gemini API key.
        seed_tracks (list): A list of seed track objects (expected to have artist.name and name/title attributes).
        count (int): The total number of unique recommendations requested.
        shuffle (bool): If True, requests "deep cuts" / obscure tracks. If False, requests popular/similar tracks.
        flex (bool | None): Explicit flex toggle. True forces flex tier, False forces standard tier,
            None defers to GEMINI_SERVICE_TIER environment configuration.
        flex_fallback_standard (bool | None): Explicit fallback toggle. True enables fallback to standard tier
            on flex capacity exhaustion or timeout, False disables it, None defers to environment.
        on_fallback (Any | None): Optional callback invoked when fallback to standard tier is triggered.

    Returns:
        list[dict]: A list of dictionaries with strictly grounded human-readable keys 'artist' and 'title'.
    """
    # Construct minimal, token-efficient prompt (Principle VI & Principle VIII: artist/title only).
    seed_descriptions = _build_seed_descriptions(seed_tracks)
    seeds_text = "\n".join(seed_descriptions)

    base_instruction = (
        f"I will provide a list of {len(seed_tracks)} songs I like. "
        f"Please generate a list of up to {count} NEW song recommendations based on this taste profile."
    )

    if shuffle:
        style_instruction = (
            "STYLE: I am looking for 'Deep Cuts'. "
            "Please ignore popular hits. Focus on lesser-known, underground, "
            "or B-side tracks that share the vibe/genre of the seeds but are not mainstream."
        )
    else:
        style_instruction = (
            "STYLE: Please find popular or highly-rated songs that match the vibe of the seeds. "
            "Focus on high relevance."
        )

    format_instruction = "Output a JSON object containing a 'songs' list with artist and title only."

    full_prompt = (
        f"{base_instruction}\n\n"
        f"{style_instruction}\n\n"
        f"{format_instruction}\n\n"
        f"SEEDS:\n{seeds_text}"
    )

    logging.info("Gemini Service: specific prompt style=%s", "Deep Cuts" if shuffle else "Standard")

    dotenv_config = _read_dotenv_values()
    primary_model, model_source = _resolve_primary_model(dotenv_config)
    fallback_model = _resolve_fallback_model(dotenv_config)
    logging.info(
        "Gemini model resolution: primary='%s' source=%s fallback=%s",
        primary_model,
        model_source,
        fallback_model if fallback_model else "none",
    )

    # Resolve service tier and timeout BEFORE instantiating genai.Client so client http_options
    # enforce the exact tier timeout (standard: 120s, flex: 900s default).
    tier, source, timeout_ms = _resolve_service_tier(flex, dotenv_config)
    logging.info(
        "Gemini service tier resolution: tier='%s' source='%s' timeout=%sms",
        tier,
        source,
        timeout_ms,
    )

    client = _create_genai_client(api_key, timeout_ms)
    fallback_standard, _ = _resolve_flex_fallback_standard(flex_fallback_standard, dotenv_config)
    retry_limit = _resolve_retry_limit(tier, dotenv_config)

    def _run_standard_tier_fallback(code_label: str | int) -> list[dict]:
        logging.warning(
            "Gemini flex capacity unavailable (%s). Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD).",
            code_label,
        )
        if on_fallback:
            on_fallback()
        return get_recommendations(
            api_key=api_key,
            seed_tracks=seed_tracks,
            count=count,
            shuffle=shuffle,
            flex=False,
            flex_fallback_standard=False,
            on_fallback=on_fallback,
        )

    try:
        generated = _generate_recommendations_with_model(
            client,
            primary_model,
            full_prompt,
            recovery_retries=retry_limit,
            service_tier=tier,
            timeout_ms=timeout_ms,
        )
        logging.info("Gemini recommendations retrieved successfully (tier='%s').", tier)
        return _cap_recommendations(generated, count)

    except ValueError as err:
        if tier == "flex" and fallback_standard and (
            "category='flex-timeout'" in str(err) or "category='flex-capacity'" in str(err)
        ):
            return _run_standard_tier_fallback("HTTP 503 / timeout")
        raise

    except Exception as primary_error:
        if _is_timeout_error(primary_error):
            if tier == "flex" and fallback_standard:
                return _run_standard_tier_fallback("HTTP timeout")
            category, _ = _classify_client_error(primary_error, service_tier=tier)
            message = _build_actionable_error(primary_model, category, primary_error)
            logging.error(message)
            raise ValueError(message) from primary_error

        if _is_server_error(primary_error):
            server_category = _classify_server_error(primary_error, service_tier=tier)
            if tier == "flex" and fallback_standard and server_category in ("flex-capacity", "flex-timeout"):
                code = _extract_error_code(primary_error) or 503
                return _run_standard_tier_fallback(f"HTTP {code} / timeout")
            message = _build_actionable_error(primary_model, server_category, primary_error)
            logging.error(message)
            raise ValueError(message) from primary_error

        if _is_client_error(primary_error):
            category, can_use_fallback = _classify_client_error(primary_error, service_tier=tier)

            if tier == "flex" and fallback_standard and category in ("flex-capacity", "flex-timeout"):
                code = _extract_error_code(primary_error) or 429
                return _run_standard_tier_fallback(f"HTTP {code} / timeout")

            if can_use_fallback and fallback_model and fallback_model != primary_model:
                logging.warning(
                    "Primary model '%s' unavailable; attempting fallback model '%s'.",
                    primary_model,
                    fallback_model,
                )
                try:
                    generated = _generate_recommendations_with_model(
                        client,
                        fallback_model,
                        full_prompt,
                        recovery_retries=retry_limit,
                        service_tier=tier,
                        timeout_ms=timeout_ms,
                    )
                    return _cap_recommendations(generated, count)
                except ValueError:
                    raise
                except Exception as fallback_error:
                    if _is_server_error(fallback_error):
                        fb_category = _classify_server_error(fallback_error, service_tier=tier)
                    elif _is_client_error(fallback_error) or _is_timeout_error(fallback_error):
                        fb_category, _ = _classify_client_error(fallback_error, service_tier=tier)
                    else:
                        fb_category = "client"
                    message = _build_actionable_error(fallback_model, fb_category, fallback_error)
                    logging.error(message)
                    raise ValueError(message) from fallback_error

            message = _build_actionable_error(primary_model, category, primary_error)
            logging.error(message)
            if can_use_fallback and (not fallback_model or fallback_model == primary_model):
                raise GeminiModelUnavailableError(message) from primary_error
            raise ValueError(message) from primary_error

        message = _build_actionable_error(primary_model, "client", primary_error)
        logging.error(message)
        raise ValueError(message) from primary_error


def classify_tracks_genres(
    api_key: str,
    tracks: list,
    flex: bool | None = None,
    flex_fallback_standard: bool | None = None,
    on_fallback: Any | None = None,
) -> list[dict]:
    """
    Classifies a batch of tracks into primary and sub-genres using the Google Gemini Interactions API.

    Args:
        api_key (str): The Google Gemini API key.
        tracks (list): A list of dicts with 'artist', 'title', and optional 'isrc'.
        flex (bool | None): Explicit flex toggle. True forces flex tier, False forces standard tier,
            None defers to GEMINI_SERVICE_TIER environment configuration.
        flex_fallback_standard (bool | None): Explicit fallback toggle. True enables fallback to standard tier
            on flex capacity exhaustion or timeout, False disables it, None defers to environment.
        on_fallback (Any | None): Optional callback invoked when fallback to standard tier is triggered.

    Returns:
        list[dict]: A list of dicts with keys 'artist', 'title', 'isrc', 'genre', 'primary_genre', 'sub_genres'.
    """
    # Use compact zero-based indices and omit ISRCs from the prompt (Principle VI & VIII).
    # Authoritative artist, title, and ISRC values are re-attached locally by track index.
    descriptions = [
        f"{idx}: {t.get('artist')} - {t.get('title')}"
        for idx, t in enumerate(tracks)
    ]
    seeds_text = "\n".join(descriptions)

    full_prompt = (
        "Classify each numbered song below into established music genres.\n"
        "For each song index `id`:\n"
        "1. `p`: exactly ONE specific primary genre (do NOT use generic umbrella terms like 'Rock', 'Pop', 'Alternative', 'Music', or 'Electronic' when a specific genre applies; e.g. 'Indie Rock', 'Synthpop', 'Math Rock', 'Deep House').\n"
        "2. `s`: up to 3 specific sub-genres/micro-genres (strictly exclude broad umbrella categories; empty list if none apply).\n\n"
        "Return ONLY JSON under `classifications` with `{id, p, s}` entries (do not repeat artist or title).\n\n"
        f"SONGS:\n{seeds_text}"
    )

    dotenv_config = _read_dotenv_values()
    primary_model, model_source = _resolve_organize_model(dotenv_config)
    logging.info(
        "Gemini organize model resolution: model='%s' source=%s",
        primary_model,
        model_source,
    )

    # Resolve service tier and timeout BEFORE instantiating genai.Client (Principle VI, FR-012).
    tier, source, timeout_ms = _resolve_service_tier(flex, dotenv_config)
    logging.info(
        "Gemini service tier resolution: tier='%s' source='%s' timeout=%sms",
        tier,
        source,
        timeout_ms,
    )

    client = _create_genai_client(api_key, timeout_ms)
    fallback_standard, _ = _resolve_flex_fallback_standard(flex_fallback_standard, dotenv_config)
    max_retries = _resolve_retry_limit(tier, dotenv_config)
    max_attempts = max_retries + 1

    # Target minimal thinking for high-volume batch classification; downgrade cleanly to 'low'
    # if the resolved model does not support 'minimal' (FR-016 + official Gemini Thinking matrix).
    thinking_level = _resolve_classification_thinking_level(primary_model)

    def _run_standard_tier_fallback(code_label: str | int) -> list[dict]:
        logging.warning(
            "Gemini flex capacity unavailable (%s). Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD).",
            code_label,
        )
        if on_fallback:
            on_fallback()
        return classify_tracks_genres(
            api_key,
            tracks,
            flex=False,
            flex_fallback_standard=False,
            on_fallback=on_fallback,
        )

    attempt = 1
    while attempt <= max_attempts:
        request_kwargs = _build_interaction_request(
            model_name=primary_model,
            prompt=full_prompt,
            response_schema_model=GenreClassificationList,
            service_tier=tier,
            thinking_level=thinking_level,
        )
        try:
            with _flex_heartbeat(tier, timeout_ms):
                interaction = client.interactions.create(**request_kwargs)

            state, payload = _parse_genre_classification_interaction(interaction, tracks=tracks)
            if state == "usable":
                logging.info("Gemini track classifications retrieved successfully (tier='%s').", tier)
                return payload

            if attempt < max_attempts:
                logging.warning(
                    "Gemini genre classification unusable for model '%s' (reason=%s). Retrying...",
                    primary_model,
                    payload,
                )
                time.sleep(RETRY_BACKOFF_SECONDS)
                attempt += 1
                continue

            return []

        except Exception as error:
            # Reactive thinking_level downgrade: if a dynamic alias (e.g. gemini-flash-latest)
            # routes to a model rejecting 'minimal', switch to 'low' without burning a retry attempt.
            if _is_unsupported_minimal_thinking_error(error, thinking_level):
                logging.info(
                    "Model '%s' rejected thinking_level='%s'; retrying with thinking_level='%s'.",
                    primary_model,
                    thinking_level,
                    CLASSIFICATION_THINKING_FALLBACK_LEVEL,
                )
                thinking_level = CLASSIFICATION_THINKING_FALLBACK_LEVEL
                continue

            if _is_timeout_error(error):
                if tier == "flex" and fallback_standard:
                    return _run_standard_tier_fallback("HTTP timeout")
                category, _ = _classify_client_error(error, service_tier=tier)
                message = _build_actionable_error(primary_model, category, error)
                logging.error(message)
                raise ValueError(message) from error

            if _is_server_error(error):
                code = _extract_error_code(error) or 503
                if attempt < max_attempts:
                    backoff = _get_retry_backoff(attempt, tier)
                    if tier == "flex":
                        logging.info(
                            "Gemini flex capacity busy (HTTP %s demand spike). Waiting %.0fs for opportunistic capacity to free up (retry %d/%d)...",
                            code,
                            backoff,
                            attempt,
                            max_retries,
                        )
                    else:
                        logging.warning(
                            "Gemini server error for model '%s'. Retrying in %.1fs...",
                            primary_model,
                            backoff,
                        )
                    time.sleep(backoff)
                    attempt += 1
                    continue

                server_category = _classify_server_error(error, service_tier=tier)
                if tier == "flex" and fallback_standard and server_category in ("flex-capacity", "flex-timeout"):
                    return _run_standard_tier_fallback(f"HTTP {code} / timeout")

                message = _build_actionable_error(primary_model, server_category, error)
                logging.error(message)
                raise ValueError(message) from error

            if _is_client_error(error):
                category, _ = _classify_client_error(error, service_tier=tier)
                code = _extract_error_code(error)
                if _is_retryable_status_code(code) and attempt < max_attempts:
                    backoff = _get_retry_backoff(attempt, tier)
                    if tier == "flex":
                        logging.info(
                            "Gemini flex capacity constrained (HTTP %s). Waiting %.0fs for opportunistic capacity to free up (retry %d/%d)...",
                            code,
                            backoff,
                            attempt,
                            max_retries,
                        )
                    else:
                        logging.warning(
                            "Gemini retryable client error for model '%s' (code=%s, category=%s). Retrying in %.1fs...",
                            primary_model,
                            code,
                            category,
                            backoff,
                        )
                    time.sleep(backoff)
                    attempt += 1
                    continue

                if tier == "flex" and fallback_standard and category in ("flex-capacity", "flex-timeout"):
                    return _run_standard_tier_fallback(f"HTTP {code or 429} / timeout")

                message = _build_actionable_error(primary_model, category, error)
                logging.error(message)
                raise ValueError(message) from error

            raise

    return []
