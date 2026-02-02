import os
import logging
from pydantic import BaseModel
from google import genai
from google.genai import types

class Song(BaseModel):
    artist: str
    title: str
    isrc: str

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
    seed_descriptions = []
    for t in seed_tracks:
        artist = t.artist.name if hasattr(t, 'artist') else "Unknown Artist"
        title = t.name if hasattr(t, 'name') else (t.title if hasattr(t, 'title') else "Unknown Title")
        seed_descriptions.append(f"- {artist} - {title}")
    
    seeds_text = "\n".join(seed_descriptions)

    # Prompt Construction
    base_instruction = (
        f"I will provide a list of {len(seed_tracks)} songs I like. "
        f"Please generate a list of exactly {count} NEW song recommendations based on this taste profile.\n"
        "IMPORTANT: You must provide a valid US-based ISRC (starting with 'US') for every track. "
        "If you cannot find a high-confidence US ISRC, do not include the track."
    )

    style_instruction = ""
    if shuffle:
        # Deep Cuts Logic
        style_instruction = (
            "STYLE: I am looking for 'Deep Cuts'. "
            "Please ignore popular hits. Focus on lesser-known, underground, "
            "or B-side tracks that share the vibe/genre of the seeds but are not mainstream."
        )
    else:
        # Standard Logic
        style_instruction = (
            "STYLE: Please find popular or highly-rated songs that match the vibe of the seeds. "
            "Focus on high relevance."
        )

    # Note: Explicit JSON instructions are less critical with response_schema, but good for context
    format_instruction = "Output a list of songs with artist, title, and ISRC."

    full_prompt = (
        f"{base_instruction}\n\n"
        f"{style_instruction}\n\n"
        f"{format_instruction}\n\n"
        f"SEEDS:\n{seeds_text}"
    )

    logging.info(f"Gemini Service: specific prompt style={'Deep Cuts' if shuffle else 'Standard'}")

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
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
        
        # Parse Pydantic Response
        if response.parsed:
            # Convert Pydantic models to dicts
            return [req.model_dump() for req in response.parsed]
        else:
            logging.warning("Gemini returned empty parsed response.")
            return []

    except genai.errors.ClientError as e:
        logging.error(f"Gemini Client Error (Auth/Invalid Request): {e}")
        raise ValueError(f"Gemini API Client Error: {e}") from e
    except genai.errors.ServerError as e:
        logging.error(f"Gemini Server Error: {e}")
        return []
    except Exception as e:
        # General catch-all for Pydantic validation errors or network issues
        logging.error(f"Gemini Unexpected Error: {e}")
        return []
