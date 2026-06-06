from pydantic import BaseModel

class GenreRunSummary(BaseModel):
    library_tracks_scanned: int = 0
    classified_tracks: int = 0
    unknown_tracks: int = 0
    playlists_created: int = 0
    playlists_updated: int = 0
    tracks_added: int = 0
    tracks_removed: int = 0

def _get_tracks_batch(tracks, batch_size=100):
    for i in range(0, len(tracks), batch_size):
        yield tracks[i:i + batch_size]

def calculate_sync_delta(desired_track_ids: list, existing_track_ids: list):
    """
    Returns lists of track IDs to add and track IDs to remove to match desired state.
    Duplicate existing IDs are handled safely.
    """
    # Deduplicate desired to avoid trying to add the same track twice
    # Preserve order if possible, but sets are fine
    desired_dedup = []
    seen = set()
    for d in desired_track_ids:
        if d not in seen:
            seen.add(d)
            desired_dedup.append(d)

    desired_set = set(desired_dedup)
    existing_set = set(existing_track_ids)
    
    # What's in desired but not in existing
    to_add = [tid for tid in desired_dedup if tid not in existing_set]
    
    # What's in existing but not in desired
    to_remove = [tid for tid in existing_track_ids if tid not in desired_set]
    
    return to_add, to_remove

CACHE_FILE = ".tde_genre_cache.json"

def _load_cache():
    import json
    import os
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_cache(cache):
    import json
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        import logging
        logging.warning(f"Failed to save genre cache: {e}")

def run_genre_playlist_sync(session, folder_name: str, api_key: str = None) -> GenreRunSummary:
    """
    Orchestrates the full genre playlist sync workflow.
    """
    import os
    import logging
    from src.lib.logging import GENRE_PLAYLIST_SCAN_STARTED, GENRE_PLAYLIST_SUMMARY
    from src.services.tidal_service import (
        fetch_all_favorite_tracks,
        get_or_create_folder,
        get_playlists_in_folder,
        create_playlist_in_folder,
        get_playlist_tracks,
        sync_playlist_tracks,
        get_track_identity_key
    )
    from src.services.gemini_service import classify_tracks_genres

    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    summary = GenreRunSummary()
    
    logging.info(f"[{GENRE_PLAYLIST_SCAN_STARTED}] Fetching full Tidal library...")
    favorite_tracks, pages = fetch_all_favorite_tracks(session)
    summary.library_tracks_scanned = len(favorite_tracks)
    logging.info(f"Loaded {summary.library_tracks_scanned} tracks across {pages} pages.")

    if not favorite_tracks:
        logging.warning("Library is empty. Nothing to process.")
        return summary

    # Deduplicate tracks by identity key
    unique_tracks = {}
    for t in favorite_tracks:
        key = get_track_identity_key(t)
        if key and key not in unique_tracks:
            unique_tracks[key] = t

    tracks_to_classify = list(unique_tracks.values())
    
    # Load cache
    genre_cache = _load_cache()
    
    logging.info("Classifying tracks via Gemini in batches...")
    
    # Mapping of genre -> list of track IDs
    genre_groups = {}
    unknown_track_ids = []
    
    # Filter tracks that need classification
    unclassified_tracks = []
    for t in tracks_to_classify:
        key = get_track_identity_key(t)
        if key in genre_cache:
            genre = genre_cache[key]
            if not genre:
                unknown_track_ids.append(t.id)
                summary.unknown_tracks += 1
            else:
                summary.classified_tracks += 1
                genre_key = genre.strip()
                if genre_key not in genre_groups:
                    genre_groups[genre_key] = []
                genre_groups[genre_key].append(t.id)
        else:
            unclassified_tracks.append(t)
            
    if unclassified_tracks:
        logging.info(f"{len(unclassified_tracks)} tracks not in cache, asking Gemini...")
        
    for batch in _get_tracks_batch(unclassified_tracks, batch_size=50):
        # Prepare inputs
        batch_inputs = []
        for t in batch:
            batch_inputs.append({
                "artist": getattr(t.artist, "name", "") if getattr(t, "artist", None) else "",
                "title": getattr(t, "title", ""),
                "isrc": getattr(t, "isrc", "")
            })
            
        # Call Gemini adapter
        results = classify_tracks_genres(api_key, batch_inputs)
        
        # Merge back to original tracks based on zip/order
        for track, result in zip(batch, results):
            genre = result.get("genre")
            key = get_track_identity_key(track)
            
            # Save to cache
            if not genre:
                unknown_track_ids.append(track.id)
                summary.unknown_tracks += 1
            else:
                # Save to cache only on hit
                if key:
                    genre_cache[key] = genre

                summary.classified_tracks += 1
                genre_key = genre.strip()
                if genre_key not in genre_groups:
                    genre_groups[genre_key] = []
                genre_groups[genre_key].append(track.id)

    # Save cache if we did any API calls
    if unclassified_tracks:
        _save_cache(genre_cache)

    if unknown_track_ids:
        genre_groups["Unknown"] = unknown_track_ids

    logging.info(f"Classification complete. Resolving folder '{folder_name}'...")
    folder = get_or_create_folder(session, folder_name)
    
    existing_playlists = get_playlists_in_folder(session, folder.id)
    # Build dictionary of normalized name -> playlist_id
    # Ensure lowercase comparison
    playlist_map = {p.name.lower(): p for p in existing_playlists if p.name}
    
    logging.info(f"Syncing {len(genre_groups)} genre playlists...")
    
    for genre_name, desired_track_ids in genre_groups.items():
        search_name = genre_name.lower()
        if search_name in playlist_map:
            # Sync existing
            playlist = playlist_map[search_name]
            existing_tracks = get_playlist_tracks(session, playlist.id)
            existing_track_ids = [t.id for t in existing_tracks]
            
            to_add, to_remove = calculate_sync_delta(desired_track_ids, existing_track_ids)
            
            if to_add or to_remove:
                sync_playlist_tracks(session, playlist.id, to_add_ids=to_add, to_remove_ids=to_remove)
                summary.playlists_updated += 1
                summary.tracks_added += len(to_add)
                summary.tracks_removed += len(to_remove)
                logging.info(f"Synced playlist '{playlist.name}': +{len(to_add)} -{len(to_remove)} tracks.")
            else:
                logging.info(f"Playlist '{playlist.name}' is up to date.")
        else:
            # Create new
            create_playlist_in_folder(
                session, 
                name=genre_name, 
                description=f"Auto-generated genre playlist for {genre_name}.", 
                folder_id=folder.id, 
                track_ids=desired_track_ids
            )
            summary.playlists_created += 1
            summary.tracks_added += len(desired_track_ids)
            logging.info(f"Created playlist '{genre_name}' with {len(desired_track_ids)} tracks.")

    return summary
