from pydantic import BaseModel
from typing import Optional

class GenreRunSummary(BaseModel):
    library_tracks_scanned: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    classified_tracks: int = 0
    unknown_tracks: int = 0
    playlists_created: int = 0
    playlists_updated: int = 0
    playlists_deleted: int = 0
    duplicate_playlists_deleted: int = 0
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

def run_genre_playlist_sync(
    session,
    folder_name: str,
    api_key: Optional[str] = None,
    min_genre_size: int = 10,
    db_path: Optional[str] = None,
) -> GenreRunSummary:
    """
    Orchestrates the full genre playlist sync workflow using SQLite caching.
    """
    import os
    import logging
    from src.lib.logging import GENRE_PLAYLIST_SCAN_STARTED
    from src.services.tidal_service import (
        fetch_all_favorite_tracks,
        get_or_create_folder,
        get_playlists_in_folder,
        create_playlist_in_folder,
        get_playlist_tracks,
        sync_playlist_tracks,
        get_track_identity_key,
        delete_playlist,
    )
    from src.services.gemini_service import classify_tracks_genres
    from src.services.genre_cache_service import GenreCacheService

    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    summary = GenreRunSummary()
    cache_service = GenreCacheService(db_path=db_path) if db_path else GenreCacheService()
    
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

    tracks_to_process = list(unique_tracks.values())
    track_keys = [get_track_identity_key(t) for t in tracks_to_process]
    
    # Query SQLite database cache
    cached_genres, uncached_or_unknown_keys = cache_service.get_cached_genres(track_keys)
    summary.cache_hits = len(cached_genres)
    summary.cache_misses = len(uncached_or_unknown_keys)
    
    import re
    genre_groups_norm = {}
    norm_to_canonical = {}
    unknown_track_ids = []
    
    def add_to_genre_groups(raw_genre, track_id):
        raw_genre = raw_genre.strip()
        norm_key = re.sub(r'[^a-z0-9]', '', raw_genre.lower())
        if norm_key not in genre_groups_norm:
            genre_groups_norm[norm_key] = []
        genre_groups_norm[norm_key].append(track_id)
        
        if norm_key not in norm_to_canonical:
            norm_to_canonical[norm_key] = raw_genre
        else:
            existing = norm_to_canonical[norm_key]
            if "-" in existing and " " in raw_genre:
                norm_to_canonical[norm_key] = raw_genre
            elif raw_genre.istitle() and not existing.istitle() and raw_genre.upper() != raw_genre:
                norm_to_canonical[norm_key] = raw_genre

    # Process cached classified tracks
    uncached_keys_set = set(uncached_or_unknown_keys)
    uncached_tracks = []
    for t in tracks_to_process:
        key = get_track_identity_key(t)
        if key in cached_genres:
            genre = cached_genres[key]
            summary.classified_tracks += 1
            add_to_genre_groups(genre, t.id)
        elif key in uncached_keys_set:
            uncached_tracks.append(t)
            
    if uncached_tracks:
        logging.info(f"{len(uncached_tracks)} tracks not cached or UNKNOWN. Querying Gemini...")
        records_to_save = []
        for batch in _get_tracks_batch(uncached_tracks, batch_size=50):
            batch_inputs = []
            for t in batch:
                batch_inputs.append({
                    "artist": getattr(t.artist, "name", "") if getattr(t, "artist", None) else "",
                    "title": getattr(t, "title", ""),
                    "isrc": getattr(t, "isrc", "")
                })
                
            results = classify_tracks_genres(api_key, batch_inputs)
            
            for track, result in zip(batch, results):
                genre = result.get("genre")
                key = get_track_identity_key(track)
                artist_name = getattr(track.artist, "name", "") if getattr(track, "artist", None) else ""
                title_str = getattr(track, "title", "")
                
                if not genre or genre.strip().lower() in ("unknown", ""):
                    unknown_track_ids.append(track.id)
                    summary.unknown_tracks += 1
                    records_to_save.append({
                        "track_id": key,
                        "artist": artist_name,
                        "title": title_str,
                        "primary_genre": "Unknown",
                        "status": "UNKNOWN",
                    })
                else:
                    summary.classified_tracks += 1
                    genre_key = genre.strip()
                    add_to_genre_groups(genre_key, track.id)
                    records_to_save.append({
                        "track_id": key,
                        "artist": artist_name,
                        "title": title_str,
                        "primary_genre": genre_key,
                        "status": "CLASSIFIED",
                    })

        cache_service.save_track_genres(records_to_save)

    genre_groups = {}
    for norm_key, track_ids in genre_groups_norm.items():
        canonical_name = norm_to_canonical[norm_key]
        genre_groups[canonical_name] = track_ids

    # Thresholding: route genres < min_genre_size into "Others"
    others_track_ids = []
    final_genre_groups = {}
    for genre_name, track_ids in genre_groups.items():
        if len(track_ids) < min_genre_size:
            others_track_ids.extend(track_ids)
        else:
            final_genre_groups[genre_name] = track_ids
            
    if others_track_ids:
        final_genre_groups["Others"] = others_track_ids

    if unknown_track_ids:
        final_genre_groups["Unknown"] = unknown_track_ids

    logging.info(f"Classification complete. Resolving folder '{folder_name}'...")
    folder = get_or_create_folder(session, folder_name)
    
    existing_playlists = get_playlists_in_folder(session, folder.id)
    
    grouped_playlists = {}
    for p in existing_playlists:
        if not p.name:
            continue
        # Strip trailing " (1)", " (2)", etc. that might have been added by previous duplicate creations
        normalized_name = re.sub(r'\s*\(\d+\)$', '', p.name).strip()
        key = normalized_name.lower()
        if key not in grouped_playlists:
            grouped_playlists[key] = []
        grouped_playlists[key].append(p)
        
    playlist_map = {}
    for search_name, pls in grouped_playlists.items():
        if len(pls) > 1:
            def sort_key(p):
                val = getattr(p, 'created', None)
                if val is not None:
                    import datetime
                    if isinstance(val, datetime.datetime):
                        return val.timestamp()
                    return str(val)
                return str(getattr(p, 'id', ''))
                
            try:
                pls_sorted = sorted(pls, key=sort_key)
            except Exception:
                pls_sorted = pls
                
            playlist_to_keep = pls_sorted[0]
            playlists_to_delete = pls_sorted[1:]
            
            playlist_map[search_name] = playlist_to_keep
            
            for p_del in playlists_to_delete:
                logging.info(f"Removing duplicate playlist '{p_del.name}' (id: {p_del.id}) from folder...")
                delete_playlist(session, p_del.id)
                summary.playlists_deleted += 1
                summary.duplicate_playlists_deleted += 1
        elif len(pls) == 1:
            playlist_map[search_name] = pls[0]
    
    # Process obsolete/empty playlists whose genre no longer exists in desired groups
    active_desired_names_lower = {g.lower() for g in final_genre_groups.keys()}
    for search_name, existing_pl in list(playlist_map.items()):
        if search_name not in active_desired_names_lower:
            logging.info(f"Removing obsolete playlist '{existing_pl.name}' from folder...")
            delete_playlist(session, existing_pl.id)
            summary.playlists_deleted += 1
            playlist_map.pop(search_name, None)

    logging.info(f"Syncing {len(final_genre_groups)} genre playlists...")
    
    # Sort genre groups by ascending track count so Tidal "Updated Date" lists largest playlists first
    sorted_genre_groups = sorted(final_genre_groups.items(), key=lambda item: len(item[1]))
    
    for genre_name, desired_track_ids in sorted_genre_groups:
        search_name = genre_name.lower()
        if search_name in playlist_map:
            playlist = playlist_map[search_name]
            existing_tracks = get_playlist_tracks(session, playlist.id)
            
            if existing_tracks is None:
                logging.warning(f"Playlist '{playlist.name}' (id: {playlist.id}) is inaccessible. Recreating...")
                create_playlist_in_folder(
                    session, 
                    name=genre_name, 
                    description=f"Auto-generated genre playlist for {genre_name}.", 
                    folder_id=folder.id, 
                    track_ids=desired_track_ids
                )
                summary.playlists_created += 1
                summary.tracks_added += len(desired_track_ids)
                logging.info(f"Recreated playlist '{genre_name}' with {len(desired_track_ids)} tracks.")
                continue
                
            existing_track_ids = [t.id for t in existing_tracks]
            
            to_add, to_remove = calculate_sync_delta(desired_track_ids, existing_track_ids)
            
            if to_add or to_remove:
                success = sync_playlist_tracks(session, playlist.id, to_add_ids=to_add, to_remove_ids=to_remove)
                if success:
                    summary.playlists_updated += 1
                    summary.tracks_added += len(to_add)
                    summary.tracks_removed += len(to_remove)
                    logging.info(f"Synced playlist '{playlist.name}': +{len(to_add)} -{len(to_remove)} tracks.")
                else:
                    logging.warning(f"Skipping updates to '{playlist.name}' due to sync errors.")
            else:
                logging.info(f"Playlist '{playlist.name}' is up to date.")
        else:
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
