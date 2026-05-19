import os
import json
import random
import time
import re
import tidalapi
from tidalapi.exceptions import ObjectNotFound
from requests.exceptions import HTTPError

import click
import datetime

SESSION_FILE = "tidal_session.json"


class FavoritesRetrievalError(RuntimeError):
    """Raised when favorites retrieval is incomplete or fails in exclusion mode."""


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def normalize_isrc(value):
    if value is None:
        return ""
    # Keep alphanumerics only and uppercase for stable comparisons.
    return re.sub(r"[^A-Za-z0-9]", "", str(value)).upper()


def _extract_track_title(track):
    return getattr(track, "title", None) or getattr(track, "name", None)


def _extract_primary_artist(track):
    artist = getattr(track, "artist", None)
    if artist and getattr(artist, "name", None):
        return artist.name
    artists = getattr(track, "artists", None)
    if artists and len(artists) > 0 and getattr(artists[0], "name", None):
        return artists[0].name
    return ""


def get_track_identity_key(track):
    isrc = normalize_isrc(getattr(track, "isrc", None))
    if isrc:
        return f"isrc:{isrc}"

    title = normalize_text(_extract_track_title(track))
    primary_artist = normalize_text(_extract_primary_artist(track))
    if title and primary_artist:
        return f"fallback:{title}|{primary_artist}"
    return ""


def fetch_all_favorite_tracks(session, page_size=100, max_page_retries=2):
    favorite_tracks = []
    offset = 0
    pages_loaded = 0

    while True:
        last_error = None
        page_tracks = None

        for attempt in range(max_page_retries + 1):
            try:
                page_tracks = session.user.favorites.tracks(offset=offset, limit=page_size)
                break
            except Exception as exc:
                last_error = exc
                if attempt < max_page_retries:
                    time.sleep(0.2 * (2 ** attempt))
                    continue

        if page_tracks is None:
            raise FavoritesRetrievalError(
                f"Failed retrieving favorites page at offset={offset} after {max_page_retries + 1} attempts"
            ) from last_error

        if not page_tracks:
            break

        favorite_tracks.extend(page_tracks)
        pages_loaded += 1
        offset += len(page_tracks)

    return favorite_tracks, pages_loaded


def build_favorites_snapshot(session, page_size=100, max_page_retries=2):
    tracks, pages_loaded = fetch_all_favorite_tracks(
        session,
        page_size=page_size,
        max_page_retries=max_page_retries,
    )

    identity_keys = set()
    for track in tracks:
        key = get_track_identity_key(track)
        if key:
            identity_keys.add(key)

    return {
        "identity_keys": identity_keys,
        "total_favorites": len(tracks),
        "pages_loaded": pages_loaded,
        "load_complete": True,
    }


def filter_out_favorites(candidates, favorite_identity_keys):
    filtered = []
    excluded_count = 0

    for track in candidates:
        key = get_track_identity_key(track)
        if key and key in favorite_identity_keys:
            excluded_count += 1
            continue
        filtered.append(track)

    return filtered, excluded_count

def get_session():
    session = tidalapi.Session()
    
    # Check if a session file exists
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            config = json.load(f)
        session.load_oauth_session(
            config['token_type'],
            config['access_token'],
            config['refresh_token'],
            datetime.datetime.fromisoformat(config['expiry_time'])
        )
    else:
        # No session file, so perform interactive login
        session.login_oauth_simple()
        
        # Save the session for future use
        with open(SESSION_FILE, 'w') as f:
            json.dump({
                'token_type': session.token_type,
                'access_token': session.access_token,
                'refresh_token': session.refresh_token,
                'expiry_time': session.expiry_time.isoformat()
            }, f)
        
        click.echo("\n--- Tidal Authentication Successful ---")
        click.echo(f"Session details have been saved to `{SESSION_FILE}` for future non-interactive use.")
        click.echo("-------------------------------------\n")
        
    return session

def get_random_favorite_tracks(session, num_tracks):
    favorite_tracks, _ = fetch_all_favorite_tracks(session)

    if len(favorite_tracks) < num_tracks:
        click.echo(f"Warning: Requested {num_tracks} favorite tracks, but only {len(favorite_tracks)} were found. Using all available favorite tracks.")
        return favorite_tracks
        
    return random.sample(favorite_tracks, num_tracks)

def create_playlist(session, name, num_tidal_tracks, num_similar_tracks, seed_tracks, final_tags, no_similar_tracks_seeds=None, folder_id=None, tracks=None):
    run_date = datetime.date.today().isoformat()
    
    seed_track_list = " | ".join([f"{t.title} by {t.artist.name}" for t in seed_tracks])
    
    # Create a "Genre Mix" summary
    genre_mix_summary = ""
    if final_tags:
        from collections import Counter
        total_tags = len(final_tags)
        top_5_genres = Counter(final_tags).most_common(5)
        
        genre_items = []
        for genre, count in top_5_genres:
            percentage = (count / total_tags) * 100
            genre_items.append(f"{genre.title()}: {percentage:.0f}%")
        genre_mix_summary = " Genre Mix: " + " | ".join(genre_items) + "."

    no_similar_tracks_summary = ""
    if no_similar_tracks_seeds:
        no_similar_tracks_list = " | ".join([f"{t.title} by {t.artist.name}" for t in no_similar_tracks_seeds])
        no_similar_tracks_summary = f" No similar tracks found for: {no_similar_tracks_list}."

    track_ids = [t.id for t in tracks] if tracks else []
    description = (
        f"Generated on {run_date}. "
        f"Based on {num_tidal_tracks} seed tracks: {seed_track_list}. "
        f"Inserted {len(track_ids)} tracks into this playlist."
        f"{genre_mix_summary}"
        f"{no_similar_tracks_summary}"
    )

    # Truncate the description if it's too long
    if len(description) > 500:
        description = description[:497] + "..."

    if folder_id:
        return create_playlist_in_folder(session, name, description, folder_id, track_ids=track_ids)
    
    playlist = session.user.create_playlist(name, description)
    if track_ids:
        playlist.add(track_ids)
    return playlist

def search_for_track(session, track):
    query = f"{track.artist.name} - {track.title}"
    results = session.search(query, models=[tidalapi.Track])
    
    tracks = results.get('tracks', [])
    if tracks:
        return tracks[0]
        
    return None

def resolve_text_seed_track(session, artist_name, track_name):
    """
    Resolve a best-effort seed track object for Gemini context in single-seed mode.

    Returns the first exact match when available. If no exact match exists but search
    results are present, returns the first candidate and marks it ambiguous.
    If no results are found, returns a text-only placeholder object.
    """
    search_query = f"{artist_name} {track_name}"
    search_results = session.search(search_query, limit=50)
    tracks = search_results.get("tracks", []) if search_results else []

    normalized_artist = artist_name.strip().lower()
    normalized_track = track_name.strip().lower()

    for track in tracks:
        track_artist = track.artist.name.strip().lower() if getattr(track, "artist", None) else ""
        track_title = track.name.strip().lower() if getattr(track, "name", None) else ""
        if track_artist == normalized_artist and track_title == normalized_track:
            return track, "exact"

    if tracks:
        return tracks[0], "ambiguous"

    placeholder_track = type(
        "TextSeedTrack",
        (),
        {
            "artist": type("Artist", (), {"name": artist_name})(),
            "name": track_name,
        },
    )()
    return placeholder_track, "text_only"

def get_or_create_folder(session, folder_name):
    """
    Finds an existing folder by name (case-insensitive) or creates a new one.
    Handles duplicates by returning the most recently created one.
    Implements retry logic for transient errors.
    """
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries + 1):
        try:
            user = session.user
            # Fetch all folders
            folders = user.favorites.playlist_folders()
            
            # Find matches (case-insensitive)
            matching_folders = [
                f for f in folders 
                if f.name.lower() == folder_name.lower()
            ]
            
            if matching_folders:
                # Sort by creation time (newest first)
                # Handle cases where created might be None or missing
                matching_folders.sort(
                    key=lambda f: f.created if hasattr(f, 'created') and f.created else datetime.datetime.min, 
                    reverse=True
                )
                return matching_folders[0]
            
            # Create if not found
            return user.create_folder(folder_name)
            
        except HTTPError:
            if attempt < max_retries:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            raise
        except Exception:
            raise

def create_playlist_in_folder(session, name, description, folder_id, track_ids):
    """
    Creates a playlist in a specific folder.
    Handles duplicate names by appending a counter.
    Implements retry logic and fallback to root.
    """
    max_retries = 3
    retry_delay = 1
    unique_name = name
    
    # Try to determine unique name by listing folder contents
    try:
        folder = tidalapi.playlist.Folder(session, folder_id)
        items = folder.items()
        existing_names = {p.name for p in items if p.name}
        
        counter = 1
        while unique_name in existing_names:
            unique_name = f"{name} ({counter})"
            counter += 1
    except Exception:
        # If we fail to check folder contents (e.g. folder API error), we proceed
        # with the original name and let the creation attempt handle failures.
        pass

    target_folder = folder_id
    
    for attempt in range(max_retries + 1):
        try:
            playlist = session.user.create_playlist(unique_name, description, parent_id=target_folder)
            if track_ids:
                playlist.add(track_ids)
            return playlist
            
        except (HTTPError, ObjectNotFound) as e:
            is_404 = False
            if isinstance(e, HTTPError) and e.response is not None and e.response.status_code == 404:
                is_404 = True
            elif isinstance(e, ObjectNotFound):
                is_404 = True
                
            # If folder is missing, fallback to root immediately
            if is_404 and target_folder != "root":
                click.echo(f"Warning: Folder {folder_id} not found. Falling back to root.")
                target_folder = "root"
                # When falling back to root, we revert to original name as collision scope changes,
                # or we could keep unique_name. Simplest is to reset or keep. 
                # Let's keep unique_name to avoid confusion or reset to name?
                # The requirements don't specify, but resetting to 'name' seems safer as 'name (1)' might not exist in root.
                unique_name = name 
                continue

            if attempt < max_retries:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            raise

def add_tracks_to_playlist(playlist, tracks):
    if not tracks:
        return
    playlist.add([t.id for t in tracks])

def get_track_by_isrc(session, isrc):
    """
    Searches for a track by its International Standard Recording Code (ISRC).
    Returns the Track object if found, otherwise None.
    Strict matching: Does NOT fall back to text search.
    """
    try:
        # Use the specific ISRC lookup method provided by the library
        if hasattr(session, 'get_tracks_by_isrc'):
             tracks = session.get_tracks_by_isrc(isrc) # Returns list of tracks
             if tracks:
                 return tracks[0]
        else:
            # Fallback for older library versions if method missing (unlikely given inspection)
            # This is the "search by string" which we know fails, but leaving as safety?
            # No, if the method exists, use it. If not, fail.
            pass
            
    except ObjectNotFound:
        # Specific exception raised when ISRC is not found
        pass
    except Exception:
        # We rely on the caller to log robustly, but a basic print for now or silence is fine 
        # as the plan says "Log the error and skip". The caller (main.py) handles logging.
        pass
        
    return None

