import os
import logging
import json
import random
import time
import re
import tidalapi
from tidalapi.exceptions import ObjectNotFound
from requests.exceptions import HTTPError, RequestException

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

def format_seed_playlist_description(artist, track, track_count, genre_mix_summary=""):
    run_date = datetime.date.today().isoformat()
    desc = (
        f"Track radio generated from seed track: '{track}' by {artist}. "
        f"Generated on {run_date}. "
        f"Inserted {track_count} tracks into this playlist.{genre_mix_summary}"
    )
    if len(desc) > 500:
        desc = desc[:497] + "..."
    return desc

def create_playlist(session, name, num_tidal_tracks, num_similar_tracks, seed_tracks, final_tags, no_similar_tracks_seeds=None, folder_id=None, tracks=None, description=None):
    run_date = datetime.date.today().isoformat()
    track_ids = [t.id for t in tracks] if tracks else []

    if description is None:
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

def search_tracks(session, query, limit=50, max_retries=3, retry_delay=1):
    """
    Searches for tracks using Tidal's native v2 API (GET /v2/search).
    Falls back to legacy session.search if v2 search fails or is unavailable.
    """
    api_v2 = getattr(getattr(session, "config", None), "api_v2_location", None)
    if isinstance(api_v2, str) and api_v2.startswith("http") and hasattr(session, "request"):
        params = {"query": query, "limit": limit}
        delay = retry_delay
        for attempt in range(max_retries + 1):
            try:
                response = session.request.request(
                    "GET",
                    "search",
                    params=params,
                    base_url=session.config.api_v2_location,
                )
                data = response.json()
                items = data.get("tracks", {}).get("items", [])
                tracks = []
                for item in items:
                    try:
                        if "album" in item and isinstance(item["album"], dict):
                            item["album"].setdefault("videoCover", None)
                        t = session.parse_track(item)
                    except Exception:
                        t = type("Track", (), {
                            "id": item.get("id"),
                            "name": item.get("title", ""),
                            "title": item.get("title", ""),
                            "artist": type("Artist", (), {"name": item.get("artists", [{}])[0].get("name", "")})(),
                            "isrc": item.get("isrc"),
                        })()
                    tracks.append(t)
                return tracks
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                logging.warning(f"v2 search failed for query '{query}': {e}. Falling back to session.search...")
                break

    # Fallback to session.search
    try:
        results = session.search(query, models=[tidalapi.Track] if hasattr(tidalapi, "Track") else None, limit=limit)
        if isinstance(results, dict):
            return results.get("tracks", [])
        return getattr(results, "tracks", [])
    except Exception as e:
        logging.error(f"Search failed for query '{query}': {e}")
        return []

def search_for_track(session, track):
    query = f"{track.artist.name} - {track.title}"
    tracks = search_tracks(session, query, limit=10)
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
    tracks = search_tracks(session, search_query, limit=50)

    normalized_artist = artist_name.strip().lower()
    normalized_track = track_name.strip().lower()

    for track in tracks:
        track_artist = track.artist.name.strip().lower() if getattr(track, "artist", None) else ""
        track_title = (getattr(track, "name", None) or getattr(track, "title", "")).strip().lower()
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
            "title": track_name,
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

def get_playlists_in_folder(session, folder_id, max_retries=3, retry_delay=1):
    """
    Returns a list of playlists existing in the specified folder, handling pagination.
    Implements retry logic with exponential backoff for transient HTTP errors (5xx, 429)
    and network timeouts. Fails closed by raising exceptions if retries are exhausted.
    Returns an empty list if the folder is not found (404 / ObjectNotFound).
    """
    all_items = []
    cursor = None
    
    while True:
        params = {
            "folderId": folder_id,
            "limit": 50,
            "order": "NAME",
            "includeOnly": "PLAYLIST",
        }
        if cursor:
            params["cursor"] = cursor
            
        endpoint = "my-collection/playlists/folders"
        json_obj = None
        current_delay = retry_delay

        for attempt in range(max_retries + 1):
            try:
                response = session.request.request(
                    "GET",
                    endpoint,
                    base_url=session.config.api_v2_location,
                    params=params,
                )
                json_obj = response.json()
                break
            except ObjectNotFound:
                return []
            except (HTTPError, RequestException, Exception) as exc:
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code == 404:
                    return []

                is_transient = True
                if status_code is not None and status_code < 500 and status_code != 429:
                    is_transient = False

                if is_transient and attempt < max_retries:
                    logging.warning(
                        f"Transient error reading items in folder {folder_id} (attempt {attempt + 1}/{max_retries + 1}): {exc}. Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= 2
                    continue
                logging.error(f"Failed to read items in folder {folder_id} after {attempt + 1} attempts: {exc}")
                raise

        if isinstance(json_obj, dict) and json_obj.get("items"):
            # Format to match what tidalapi expects
            for item in json_obj["items"]:
                if isinstance(item, dict) and "data" in item:
                    if "title" in item["data"] and "name" not in item["data"]:
                        item["data"]["name"] = item["data"]["title"]
            
            playlists = {"items": [item["data"] for item in json_obj.get("items") if isinstance(item, dict) and "data" in item]}
            items = session.request.map_json(playlists, parse=session.parse_playlist)
            all_items.extend(items)
            
        cursor = json_obj.get("cursor") if isinstance(json_obj, dict) else None
        if not cursor or not isinstance(cursor, str):
            break
            
    return all_items

def get_playlist_tracks(session, playlist_id, max_retries=3, retry_delay=1):
    """
    Retrieves all tracks for a given playlist using Tidal's native v2 API
    (GET /v2/playlists/{playlist_id}/items).
    Paginates using the cursor parameter and implements retry logic with exponential backoff.
    """
    locale = getattr(session, "locale", "en_US") or "en_US"
    all_tracks = []
    cursor = None
    limit = 100

    while True:
        params = {"locale": locale, "limit": limit}
        if cursor:
            params["cursor"] = cursor

        delay = retry_delay
        page_data = None

        for attempt in range(max_retries + 1):
            try:
                response = session.request.request(
                    "GET",
                    f"playlists/{playlist_id}/items",
                    params=params,
                    base_url=session.config.api_v2_location,
                )
                page_data = response.json()
                break
            except Exception as e:
                is_404 = False
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                if status_code == 404 or isinstance(e, ObjectNotFound):
                    is_404 = True

                if is_404:
                    logging.warning(f"Playlist {playlist_id} not found: {e}")
                    return None

                if attempt < max_retries:
                    logging.warning(
                        f"Transient error reading playlist {playlist_id} items (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue

                logging.error(f"Failed to read playlist {playlist_id} items after {attempt + 1} attempts: {e}")
                return None

        if not page_data or not page_data.get("content"):
            break

        for entry in page_data["content"]:
            item = entry.get("item", {})
            item_uuid = entry.get("id")
            if not item or "id" not in item:
                continue

            try:
                if "album" in item and isinstance(item["album"], dict):
                    item["album"].setdefault("videoCover", None)
                track = session.parse_track(item)
            except Exception:
                track = type("Track", (), {
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "artist": type("Artist", (), {"name": item.get("artists", [{}])[0].get("name", "")})(),
                })()

            track.item_uuid = item_uuid
            all_tracks.append(track)

        cursor = page_data.get("cursor")
        if not cursor:
            break

    return all_tracks

def remove_tracks_from_playlist(session, playlist_id, track_ids_or_uuids, chunk_size=50, max_retries=3, retry_delay=1):
    """
    Removes items from a playlist using Tidal's native v2 API (PUT /v2/playlists/{id}/items/remove).
    If track IDs are provided instead of item UUIDs, resolves them via get_playlist_tracks.
    Chunks item UUIDs and implements retry logic for transient errors.
    """
    if not track_ids_or_uuids:
        return True

    uuids_to_remove = []
    track_ids_to_resolve = set()

    for item in track_ids_or_uuids:
        item_str = str(item)
        if "-" in item_str and len(item_str) == 36:
            uuids_to_remove.append(item_str)
        else:
            track_ids_to_resolve.add(item_str)

    if track_ids_to_resolve:
        for attempt in range(max_retries + 1):
            tracks = get_playlist_tracks(session, playlist_id)
            if tracks:
                for t in tracks:
                    if str(t.id) in track_ids_to_resolve or t.id in track_ids_to_resolve:
                        item_uuid = getattr(t, "item_uuid", None)
                        if item_uuid and item_uuid not in uuids_to_remove:
                            uuids_to_remove.append(item_uuid)
                if uuids_to_remove:
                    break
            if attempt < max_retries:
                time.sleep(0.3)

    if not uuids_to_remove:
        return True

    for i in range(0, len(uuids_to_remove), chunk_size):
        chunk = uuids_to_remove[i:i + chunk_size]
        params = {"itemUuids": ",".join(chunk)}
        current_delay = retry_delay

        for attempt in range(max_retries + 1):
            try:
                session.request.request(
                    "PUT",
                    f"playlists/{playlist_id}/items/remove",
                    params=params,
                    base_url=session.config.api_v2_location,
                )
                break
            except Exception as e:
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                is_transient = True
                if status_code is not None and status_code < 500 and status_code != 429:
                    is_transient = False

                if is_transient and attempt < max_retries:
                    logging.warning(
                        f"Transient error removing tracks from playlist {playlist_id} via v2 API (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= 2
                    continue
                logging.error(f"Failed to remove tracks from playlist {playlist_id} via v2 API after {attempt + 1} attempts: {e}")
                raise

    return True

def sync_playlist_tracks(session, playlist_id, to_add_ids, to_remove_ids):
    """
    Adds and removes tracks from an existing playlist using Tidal's native v2 API.
    """
    try:
        if to_remove_ids:
            remove_tracks_from_playlist(session, playlist_id, to_remove_ids)
        if to_add_ids:
            add_tracks_to_playlist(session, playlist_id, to_add_ids)
        return True
    except Exception as e:
        logging.error(f"Failed to sync playlist {playlist_id} via v2 API: {e}")
        return False

def delete_playlist(session, playlist_id, max_retries=3, retry_delay=1):
    """
    Deletes or removes a playlist from Tidal using the native v2 collection API
    (PUT /v2/my-collection/playlists/folders/remove?trns=trn:playlist:{id}).
    Falls back to legacy playlist.delete() if v2 removal fails.
    """
    trn = f"trn:playlist:{playlist_id}"
    params = {"trns": trn}
    delay = retry_delay

    api_v2 = getattr(getattr(session, "config", None), "api_v2_location", None)
    if isinstance(api_v2, str) and api_v2.startswith("http") and hasattr(session, "request"):
        for attempt in range(max_retries + 1):
            try:
                session.request.request(
                    "PUT",
                    "my-collection/playlists/folders/remove",
                    params=params,
                    base_url=session.config.api_v2_location,
                )
                return True
            except Exception as e:
                is_404 = False
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                if status_code == 404 or isinstance(e, ObjectNotFound):
                    is_404 = True

                if is_404:
                    return True

                if attempt < max_retries:
                    logging.warning(
                        f"Transient error deleting playlist {playlist_id} via v2 API (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue

                logging.warning(f"Could not delete playlist {playlist_id} via v2 API ({e}), falling back to legacy delete...")
                break

    try:
        playlist = tidalapi.playlist.UserPlaylist(session, playlist_id)
        playlist.delete()
        return True
    except Exception as e_fallback:
        logging.warning(f"Could not delete playlist {playlist_id}: {e_fallback}")
        return False

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
    playlist = None
    
    for attempt in range(max_retries + 1):
        try:
            playlist = session.user.create_playlist(unique_name, description, parent_id=target_folder)
            break
            
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

    if track_ids and playlist:
        try:
            add_tracks_to_playlist(session, playlist.id, track_ids)
        except Exception as e:
            logging.warning(f"Failed to add tracks via v2 API ({e}), falling back to playlist.add()...")
            playlist.add(track_ids)

    return playlist

def add_tracks_to_playlist(session_or_playlist, playlist_id_or_tracks, track_ids=None, chunk_size=50, max_retries=3, retry_delay=1):
    """
    Adds tracks to a playlist using Tidal's native v2 API (PUT /v2/playlists/{id}/items/add).
    This avoids cross-version replication lag between v2 folder creation and legacy v1 track endpoints.
    Chunks track IDs and implements retry logic for transient errors.
    Supports both signatures:
      - add_tracks_to_playlist(session, playlist_id, track_ids)
      - add_tracks_to_playlist(playlist, tracks)
    """
    if track_ids is None:
        playlist = session_or_playlist
        tracks = playlist_id_or_tracks
        if not tracks:
            return True
        session = getattr(playlist, "session", None)
        p_id = getattr(playlist, "id", None)
        ids = [getattr(t, "id", str(t)) for t in tracks]
        if session and p_id:
            return add_tracks_to_playlist(session, p_id, ids, chunk_size=chunk_size, max_retries=max_retries, retry_delay=retry_delay)
        if hasattr(playlist, "add"):
            playlist.add(ids)
            return True
        return False

    session = session_or_playlist
    playlist_id = playlist_id_or_tracks
    if not track_ids:
        return True

    str_track_ids = [str(t) for t in track_ids]

    for i in range(0, len(str_track_ids), chunk_size):
        chunk = str_track_ids[i:i + chunk_size]
        params = {"itemIds": ",".join(chunk)}
        current_delay = retry_delay

        for attempt in range(max_retries + 1):
            try:
                session.request.request(
                    "PUT",
                    f"playlists/{playlist_id}/items/add",
                    params=params,
                    base_url=session.config.api_v2_location,
                )
                break
            except Exception as e:
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                is_transient = True
                if status_code is not None and status_code < 500 and status_code != 429:
                    is_transient = False

                if is_transient and attempt < max_retries:
                    logging.warning(
                        f"Transient error adding tracks to playlist {playlist_id} via v2 API (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= 2
                    continue
                logging.error(f"Failed to add tracks to playlist {playlist_id} via v2 API after {attempt + 1} attempts: {e}")
                raise

    return True

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

