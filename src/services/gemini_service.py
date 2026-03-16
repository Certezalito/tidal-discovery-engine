import os
import logging
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import dotenv_values


DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
_DEFAULT_WARNING_EMITTED = False


class GeminiModelUnavailableError(ValueError):
    """Raised when the configured Gemini model is unavailable or not found."""

class Song(BaseModel):
    artist: str
    title: str
    isrc: str | None = None  # Make ISRC optional


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
    return normalized or None


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


def _classify_client_error(error):
    message = str(error).lower()

    if "model" in message and ("not found" in message or "unavailable" in message):
        return "unavailable/not-found", True
    if "permission" in message or "forbidden" in message:
        return "permission", False
    if "quota" in message or "rate limit" in message or "resource exhausted" in message:
        return "quota", False
    if "api key" in message or "unauthorized" in message or "authentication" in message or "auth" in message:
        return "auth", False

    return "client", False


def _build_actionable_error(model_id, category, error):
    guidance = {
        "unavailable/not-found": "Verify GEMINI_MODEL or GEMINI_FALLBACK_MODEL and ensure the model is available to your account.",
        "auth": "Verify GEMINI_API_KEY and account authentication settings.",
        "quota": "Check Gemini quota/rate limits and retry later.",
        "permission": "Verify account permissions for the configured model.",
        "client": "Review request configuration and model identifiers.",
    }

    return (
        f"Gemini request failed. model='{model_id}', category='{category}', "
        f"details='{error}'. Next step: {guidance.get(category, guidance['client'])}"
    )


def _generate_recommendations_with_model(client, model_name, full_prompt):
    response = client.models.generate_content(
        model=model_name,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=64,
            max_output_tokens=8192,
            response_mime_type='application/json',
            response_schema=list[Song]
        )
    )

    if response.parsed:
        return [req.model_dump() for req in response.parsed]

    logging.warning("Gemini returned empty parsed response for model '%s'.", model_name)
    return []

def get_recommendations(api_key, seed_tracks, count, shuffle=False):
    """
    Generates song recommendations using Google Gemini.

    Args:
        api_key (str): The Google Gemini API key.
        seed_tracks (list): A list of seed track objects (expected to have artist.name and name/title attributes).
        count (int): The total number of unique recommendations requested.
        shuffle (bool): If True, requests "deep cuts" / obscure tracks. If False, requests popular/similar tracks.

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

    try:
        generated = _generate_recommendations_with_model(client, primary_model, full_prompt)
        return _cap_recommendations(generated, count)

    except genai.errors.ClientError as primary_error:
        category, can_use_fallback = _classify_client_error(primary_error)

        if can_use_fallback and fallback_model and fallback_model != primary_model:
            logging.warning(
                "Primary model '%s' unavailable; attempting fallback model '%s'.",
                primary_model,
                fallback_model,
            )
            try:
                generated = _generate_recommendations_with_model(client, fallback_model, full_prompt)
                return _cap_recommendations(generated, count)
            except genai.errors.ClientError as fallback_error:
                fallback_category, _ = _classify_client_error(fallback_error)
                message = _build_actionable_error(fallback_model, fallback_category, fallback_error)
                logging.error(message)
                raise ValueError(message) from fallback_error
            except genai.errors.ServerError as fallback_server_error:
                logging.error(f"Gemini Server Error on fallback model '{fallback_model}': {fallback_server_error}")
                return []
            except Exception as fallback_unexpected_error:
                logging.error(f"Gemini Unexpected Error on fallback model '{fallback_model}': {fallback_unexpected_error}")
                return []

        message = _build_actionable_error(primary_model, category, primary_error)
        logging.error(message)
        if can_use_fallback and (not fallback_model or fallback_model == primary_model):
            raise GeminiModelUnavailableError(message) from primary_error
        raise ValueError(message) from primary_error

    except genai.errors.ServerError as e:
        logging.error(f"Gemini Server Error: {e}")
        return []
    except Exception as e:
        # General catch-all for Pydantic validation errors or network issues
        logging.error(f"Gemini Unexpected Error: {e}")
        return []
