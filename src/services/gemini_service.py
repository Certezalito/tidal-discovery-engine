import os
import time
import logging
import threading
from contextlib import contextmanager
from typing import Any, Callable
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import dotenv_values


DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
_DEFAULT_WARNING_EMITTED = False
RECOVERY_RETRY_LIMIT = 1
RETRY_BACKOFF_SECONDS = 2.0
DEFAULT_FLEX_RETRY_LIMIT = 5                # Flex mode allows up to 5 progressive retries for capacity spikes
DEFAULT_FLEX_BACKOFF_SCHEDULE = [5.0, 10.0, 20.0, 30.0, 60.0]  # Progressive backoff schedule (seconds)

# Service tier and timeout constants for Gemini inference (Principle VI: Cost Efficiency)
DEFAULT_SERVICE_TIER = "standard"
DEFAULT_STANDARD_TIMEOUT_MS = 120_000      # 2 minutes default interactive timeout
DEFAULT_FLEX_TIMEOUT_SECONDS = 900          # 15 minutes default flex tier turnaround timeout
DEFAULT_FLEX_HEARTBEAT_INTERVAL_SECONDS = 15.0  # Periodic heartbeat interval during flex queue waiting

_BLOCKING_FINISH_REASONS = {
    "SAFETY",
    "BLOCKLIST",
    "PROHIBITED_CONTENT",
    "MALFORMED_FUNCTION_CALL",
    "UNEXPECTED_TOOL_CALL",
}


class GeminiModelUnavailableError(ValueError):
    """Raised when the configured Gemini model is unavailable or not found."""

class Song(BaseModel):
    artist: str
    title: str
    isrc: str | None = None  # Make ISRC optional

class GenreClassificationResult(BaseModel):
    isrc: str | None = None
    title: str | None = None
    artist: str | None = None
    primary_genre: str | None = None
    sub_genres: list[str] = Field(default_factory=list, description="Up to 3 specific sub-genres, excluding broad umbrella categories")
    genre: str | None = None  # Legacy alias for backward compatibility



def _extract_error_code(error):
    code = getattr(error, "code", None)
    if code is None:
        return None

    try:
        return int(code)
    except (TypeError, ValueError):
        return None


def _is_retryable_status_code(code):
    return code == 429 or (code is not None and code >= 500)


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
        return "gemini-flash-latest"

    return normalized


def _read_dotenv_values():
    try:
        return dotenv_values(".env")
    except Exception as exc:
        logging.warning(f"Unable to read .env for Gemini model configuration: {exc}")
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
        return normalized, source

    if not _DEFAULT_WARNING_EMITTED:
        logging.warning(
            "GEMINI_MODEL is missing or blank; using default model '%s' for this CLI invocation.",
            DEFAULT_GEMINI_MODEL,
        )
        _DEFAULT_WARNING_EMITTED = True

    return DEFAULT_GEMINI_MODEL, "default"


def _resolve_fallback_model(dotenv_config):
    raw_value, _ = _resolve_from_env_then_dotenv("GEMINI_FALLBACK_MODEL", dotenv_config)
    return _normalize_model_name(raw_value)


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
    Resolves whether to automatically fallback to standard tier on flex capacity exhaustion (FR-017 - FR-020).

    Precedence:
    1. Explicit CLI flag:
       cli_fallback is True  -> (True, 'cli')
       cli_fallback is False -> (False, 'cli')
    2. Environment Variable / .env (GEMINI_FLEX_FALLBACK_STANDARD):
       'true', '1', 'yes'    -> (True, source)
       'false', '0', 'no'    -> (False, source)
       unrecognized          -> warning logged, returns (False, 'default')
    3. Default:
       (False, 'default')

    Returns:
        tuple[bool, str]: (fallback_enabled, source_identifier)
    """
    if dotenv_config is None:
        dotenv_config = _read_dotenv_values()

    if cli_fallback is True:
        return True, "cli"
    if cli_fallback is False:
        return False, "cli"

    # Check primary GEMINI_FLEX_FALLBACK_STANDARD, then alias GEMINI_SERVICE_TIER_FALLBACK
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

    if "timeout" in message or "timed out" in message or "deadline" in message:
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


def _classify_response_state(response):
    prompt_feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(prompt_feedback, "block_reason", None)
    if block_reason and str(block_reason).upper() not in {"UNSPECIFIED", "BLOCK_REASON_UNSPECIFIED"}:
        return "unusable-blocked", f"prompt_feedback.block_reason={block_reason}"

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason and str(finish_reason).upper() in _BLOCKING_FINISH_REASONS:
            return "unusable-blocked", f"candidate.finish_reason={finish_reason}"

    parsed = getattr(response, "parsed", None)
    if not parsed:
        return "unusable-empty", "empty parsed response"

    normalized = []
    for item in parsed:
        if hasattr(item, "model_dump"):
            row = item.model_dump()
        elif isinstance(item, dict):
            row = item
        else:
            row = {
                "artist": getattr(item, "artist", None),
                "title": getattr(item, "title", None),
                "isrc": getattr(item, "isrc", None),
            }

        if row.get("artist") and row.get("title"):
            normalized.append(row)

    if not normalized:
        return "unusable-empty", "parsed recommendations missing artist/title"

    return "usable", normalized


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
    if recovery_retries is None:
        recovery_retries = _resolve_retry_limit(service_tier)
    max_attempts = recovery_retries + 1

    for attempt in range(1, max_attempts + 1):
        try:
            with _flex_heartbeat(service_tier, timeout_ms):
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=1,
                        top_p=0.95,
                        top_k=64,
                        max_output_tokens=8192,
                        response_mime_type='application/json',
                        response_schema=list[Song],
                        service_tier=service_tier,
                        http_options=types.HttpOptions(timeout=timeout_ms),
                    )
                )

            state, payload = _classify_response_state(response)
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

        except genai.errors.ClientError as error:
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

        except genai.errors.ServerError as error:
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
        except Exception as error:
            msg_lower = str(error).lower()
            if "timeout" in msg_lower or "timed out" in msg_lower or isinstance(error, TimeoutError):
                category, _ = _classify_client_error(error, service_tier=service_tier)
                message = _build_actionable_error(model_name, category, error)
                logging.error(message)
                raise ValueError(message) from error
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
    Generates song recommendations using Google Gemini.

    Args:
        api_key (str): The Google Gemini API key.
        seed_tracks (list): A list of seed track objects (expected to have artist.name and name/title attributes).
        count (int): The total number of unique recommendations requested.
        shuffle (bool): If True, requests "deep cuts" / obscure tracks. If False, requests popular/similar tracks.
        flex (bool | None): Explicit flex toggle. True forces flex tier, False forces standard tier,
            None defers to GEMINI_SERVICE_TIER environment configuration.
        flex_fallback_standard (bool | None): Explicit fallback toggle. True enables fallback to standard tier
            on flex capacity exhaustion or timeout, False disables it, None defers to environment (FR-017 - FR-021).
        on_fallback (Any | None): Optional callback invoked when fallback to standard tier is triggered.

    Returns:
        list[dict]: A list of dictionaries with keys 'artist', 'title', 'isrc'.
    """
    # Initialize Client
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        logging.error(f"Failed to initialize Gemini Client: {e}")
        raise ValueError("Invalid Gemini API Configuration") from e

    # Construct Seed List
    seed_descriptions = _build_seed_descriptions(seed_tracks)
    seeds_text = "\n".join(seed_descriptions)

    # Prompt Construction
    base_instruction = (
        f"I will provide a list of {len(seed_tracks)} songs I like. "
        f"Please generate a list of up to {count} NEW song recommendations based on this taste profile."
    )

    if shuffle:
        # Deep-cuts intent
        style_instruction = (
            "STYLE: I am looking for 'Deep Cuts'. "
            "Please ignore popular hits. Focus on lesser-known, underground, "
            "or B-side tracks that share the vibe/genre of the seeds but are not mainstream."
        )
    else:
        # Standard intent
        style_instruction = (
            "STYLE: Please find popular or highly-rated songs that match the vibe of the seeds. "
            "Focus on high relevance."
        )

    # Note: Explicit JSON instructions are less critical with response_schema, but good for context
    format_instruction = "Output a list of songs with artist and title."

    full_prompt = (
        f"{base_instruction}\n\n"
        f"{style_instruction}\n\n"
        f"{format_instruction}\n\n"
        f"SEEDS:\n{seeds_text}"
    )

    logging.info(f"Gemini Service: specific prompt style={'Deep Cuts' if shuffle else 'Standard'}")

    dotenv_config = _read_dotenv_values()
    primary_model, model_source = _resolve_primary_model(dotenv_config)
    fallback_model = _resolve_fallback_model(dotenv_config)
    logging.info(
        "Gemini model resolution: primary='%s' source=%s fallback=%s",
        primary_model,
        model_source,
        fallback_model if fallback_model else "none",
    )

    # Resolve service tier (Principle VI: Cost Efficiency; Principle IX: CLI Ergonomics)
    # CLI flag takes precedence over GEMINI_SERVICE_TIER in env/.env
    tier, source, timeout_ms = _resolve_service_tier(flex, dotenv_config)
    logging.info(
        "Gemini service tier resolution: tier='%s' source='%s' timeout=%sms",
        tier,
        source,
        timeout_ms,
    )

    fallback_standard, _ = _resolve_flex_fallback_standard(flex_fallback_standard, dotenv_config)
    retry_limit = _resolve_retry_limit(tier, dotenv_config)

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

    except genai.errors.ClientError as primary_error:
        category, can_use_fallback = _classify_client_error(primary_error, service_tier=tier)

        if tier == "flex" and fallback_standard and category in ("flex-capacity", "flex-timeout"):
            code = _extract_error_code(primary_error) or 429
            logging.warning(
                "Gemini flex capacity unavailable (HTTP %s / timeout). Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD).",
                code,
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
            except genai.errors.ClientError as fallback_error:
                fallback_category, _ = _classify_client_error(fallback_error, service_tier=tier)
                message = _build_actionable_error(fallback_model, fallback_category, fallback_error)
                logging.error(message)
                raise ValueError(message) from fallback_error
            except genai.errors.ServerError as fallback_server_error:
                fallback_server_category = _classify_server_error(fallback_server_error, service_tier=tier)
                message = _build_actionable_error(fallback_model, fallback_server_category, fallback_server_error)
                logging.error(message)
                raise ValueError(message) from fallback_server_error
            except ValueError:
                raise
            except Exception as fallback_unexpected_error:
                message = _build_actionable_error(fallback_model, "client", fallback_unexpected_error)
                logging.error(message)
                raise ValueError(message) from fallback_unexpected_error

        message = _build_actionable_error(primary_model, category, primary_error)
        logging.error(message)
        if can_use_fallback and (not fallback_model or fallback_model == primary_model):
            raise GeminiModelUnavailableError(message) from primary_error
        raise ValueError(message) from primary_error

    except genai.errors.ServerError as e:
        server_category = _classify_server_error(e, service_tier=tier)
        if tier == "flex" and fallback_standard and server_category in ("flex-capacity", "flex-timeout"):
            code = _extract_error_code(e) or 503
            logging.warning(
                "Gemini flex capacity unavailable (HTTP %s / timeout). Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD).",
                code,
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
        message = _build_actionable_error(primary_model, server_category, e)
        logging.error(message)
        raise ValueError(message) from e
    except ValueError as e:
        if tier == "flex" and fallback_standard and ("category='flex-timeout'" in str(e) or "category='flex-capacity'" in str(e)):
            logging.warning(
                "Gemini flex capacity unavailable (HTTP 503 / timeout). Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD)."
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
        raise
    except Exception as e:
        msg_lower = str(e).lower()
        if tier == "flex" and fallback_standard and ("timeout" in msg_lower or "timed out" in msg_lower or isinstance(e, TimeoutError)):
            logging.warning(
                "Gemini flex capacity unavailable (HTTP timeout). Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD)."
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
        message = _build_actionable_error(primary_model, "client", e)
        logging.error(message)
        raise ValueError(message) from e


def classify_tracks_genres(
    api_key: str,
    tracks: list,
    flex: bool | None = None,
    flex_fallback_standard: bool | None = None,
    on_fallback: Any | None = None,
) -> list[dict]:
    """
    Classifies a list of tracks into genres using Gemini.
    
    Args:
        api_key (str): The Google Gemini API key.
        tracks (list): A list of dicts with 'artist', 'title', 'isrc'.
        flex (bool | None): Explicit flex toggle. True forces flex tier, False forces standard tier,
            None defers to GEMINI_SERVICE_TIER environment configuration.
        flex_fallback_standard (bool | None): Explicit fallback toggle. True enables fallback to standard tier
            on flex capacity exhaustion or timeout, False disables it, None defers to environment (FR-017 - FR-021).
        on_fallback (Any | None): Optional callback invoked when fallback to standard tier is triggered.
        
    Returns:
        list[dict]: A list of dicts with keys 'artist', 'title', 'isrc', 'genre', 'primary_genre', 'sub_genres'.
    """
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        logging.error(f"Failed to initialize Gemini Client: {e}")
        raise ValueError("Invalid Gemini API Configuration") from e

    descriptions = []
    for t in tracks:
        isrc_part = f" (ISRC: {t.get('isrc')})" if t.get("isrc") else ""
        descriptions.append(f"- {t.get('artist')} - {t.get('title')}{isrc_part}")
    
    seeds_text = "\n".join(descriptions)

    full_prompt = (
        "I will provide a list of songs.\n"
        "For each song:\n"
        "1. Identify the 'primary_genre': exactly ONE specific, recognized musical genre that best captures the core identity of the track.\n"
        "   - Do NOT use overly broad, generic umbrella terms like 'Rock', 'Pop', 'Alternative', 'Music', or 'Electronic' if a more descriptive primary genre applies (e.g., use 'Indie Rock', 'Synthpop', 'Math Rock', 'Deep House').\n"
        "2. Identify 'sub_genres': up to 3 specific sub-genres or micro-genres that accurately characterize the track's distinctive elements (e.g., 'Dance-Punk', 'Post-Punk Revival', 'Art Punk').\n"
        "   - Strictly EXCLUDE broad umbrella categories from sub_genres.\n"
        "   - If no distinctive sub-genres apply, return an empty list.\n\n"
        "Return the output strictly in the requested JSON structure.\n"
        "Do not invent genres; use established standard music genres.\n\n"
        f"SONGS:\n{seeds_text}"
    )

    dotenv_config = _read_dotenv_values()
    primary_model, _ = _resolve_primary_model(dotenv_config)

    # Resolve service tier (Principle VI: Cost Efficiency; Principle IX: CLI Ergonomics)
    tier, source, timeout_ms = _resolve_service_tier(flex, dotenv_config)
    logging.info(
        "Gemini service tier resolution: tier='%s' source='%s' timeout=%sms",
        tier,
        source,
        timeout_ms,
    )

    fallback_standard, _ = _resolve_flex_fallback_standard(flex_fallback_standard, dotenv_config)
    max_retries = _resolve_retry_limit(tier, dotenv_config)
    max_attempts = max_retries + 1

    for attempt in range(1, max_attempts + 1):
        try:
            with _flex_heartbeat(tier, timeout_ms):
                response = client.models.generate_content(
                    model=primary_model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        response_mime_type='application/json',
                        response_schema=list[GenreClassificationResult],
                        service_tier=tier,
                        http_options=types.HttpOptions(timeout=timeout_ms),
                    )
                )
            
            parsed = getattr(response, "parsed", None)
            if not parsed:
                if attempt < max_attempts:
                    continue
                return []
                
            results = []
            for item in parsed:
                if hasattr(item, "model_dump"):
                    row = item.model_dump()
                elif isinstance(item, dict):
                    row = item
                else:
                    row = {
                        "artist": getattr(item, "artist", None),
                        "title": getattr(item, "title", None),
                        "isrc": getattr(item, "isrc", None),
                        "primary_genre": getattr(item, "primary_genre", getattr(item, "genre", None)),
                        "sub_genres": getattr(item, "sub_genres", []),
                    }

                primary_genre = row.get("primary_genre") or row.get("genre")
                if primary_genre:
                    primary_genre = str(primary_genre).strip()
                sub_genres_raw = row.get("sub_genres") or []
                if not isinstance(sub_genres_raw, list):
                    sub_genres_raw = [str(sub_genres_raw)] if sub_genres_raw else []
                # Clean and cap sub-genres to at most 3
                sub_genres = [str(s).strip() for s in sub_genres_raw if s and str(s).strip()][:3]

                row["primary_genre"] = primary_genre
                row["genre"] = primary_genre  # Legacy alias
                row["sub_genres"] = sub_genres
                results.append(row)
                
            logging.info("Gemini track classifications retrieved successfully (tier='%s').", tier)
            return results
            
        except genai.errors.ClientError as e:
            category, _ = _classify_client_error(e, service_tier=tier)
            code = _extract_error_code(e)
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
                continue

            if tier == "flex" and fallback_standard and category in ("flex-capacity", "flex-timeout"):
                logging.warning(
                    "Gemini flex capacity unavailable (HTTP %s / timeout). Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD).",
                    code or 429,
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

            message = _build_actionable_error(primary_model, category, e)
            logging.error(message)
            raise ValueError(message) from e
        except genai.errors.ServerError as e:
            code = _extract_error_code(e) or 503
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
                continue

            server_category = _classify_server_error(e, service_tier=tier)
            if tier == "flex" and fallback_standard and server_category in ("flex-capacity", "flex-timeout"):
                logging.warning(
                    "Gemini flex capacity unavailable (HTTP %s / timeout). Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD).",
                    code,
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

            message = _build_actionable_error(primary_model, server_category, e)
            logging.error(message)
            raise ValueError(message) from e
        except Exception as error:
            msg_lower = str(error).lower()
            if "timeout" in msg_lower or "timed out" in msg_lower or isinstance(error, TimeoutError):
                if tier == "flex" and fallback_standard:
                    logging.warning(
                        "Gemini flex capacity unavailable (HTTP timeout). Falling back to standard tier as configured (GEMINI_FLEX_FALLBACK_STANDARD)."
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
                category, _ = _classify_client_error(error, service_tier=tier)
                message = _build_actionable_error(primary_model, category, error)
                logging.error(message)
                raise ValueError(message) from error
            raise
            
    return []
