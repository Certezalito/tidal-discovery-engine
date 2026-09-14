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
    playlists_wiped: int = 0
    tracks_added: int = 0
    tracks_removed: int = 0
    folder_id: Optional[str] = None
    folder_url: Optional[str] = None

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

def run_genre_organizer_sync(
    session,
    folder_name: str,
    api_key: Optional[str] = None,
    min_genre_size: int = 5,
    db_path: Optional[str] = None,
    refresh_genres: bool = False,
    wipe_folder: bool = False,
    wipe_only: bool = False,
) -> GenreRunSummary:
    """
    Orchestrates the full genre organizer sync workflow using SQLite caching.
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

    logging.info(f"Resolving destination folder '{folder_name}'...")
    folder = get_or_create_folder(session, folder_name)
    if folder:
        folder_id = getattr(folder, "id", None)
        if folder_id:
            summary.folder_id = str(folder_id)
            summary.folder_url = f"https://tidal.com/browse/folder/{folder_id}"
        elif getattr(folder, "listen_url", None):
            summary.folder_url = str(folder.listen_url)

    existing_playlists = get_playlists_in_folder(session, folder.id) if (folder and getattr(folder, "id", None)) else []

    if wipe_folder or wipe_only:
        logging.info(f"Wiping existing playlists in folder '{folder_name}'...")
        for p in existing_playlists:
            p_id = getattr(p, "id", None)
            if p_id:
                p_name = getattr(p, "name", "")
                logging.info(f"Deleting playlist '{p_name}' (id: {p_id})")
                delete_playlist(session, p_id)
                summary.playlists_wiped += 1
        existing_playlists = []
        logging.info(f"Wiped {summary.playlists_wiped} existing playlists in folder '{folder_name}'.")

    if wipe_only:
        return summary
    
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
    cached_genres, uncached_or_unknown_keys = cache_service.get_cached_genres(track_keys, refresh_genres=refresh_genres)
    summary.cache_hits = len(cached_genres)
    summary.cache_misses = len(uncached_or_unknown_keys)
    
    import re
    genre_groups_norm = {}
    norm_to_canonical = {}
    track_primary_norm = {}
    unknown_track_ids = []
    
    def add_to_genre_groups(raw_genre: str, track_id: str, is_sub: bool = False):
        raw_genre = raw_genre.strip()
        norm_key = re.sub(r'[^a-z0-9]', '', raw_genre.lower())
        if not norm_key:
            return
        if not is_sub:
            track_primary_norm[track_id] = norm_key
        if norm_key not in genre_groups_norm:
            genre_groups_norm[norm_key] = []
        if track_id not in genre_groups_norm[norm_key]:
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
            genre_data = cached_genres[key]
            if isinstance(genre_data, dict):
                primary_genre = genre_data.get("primary_genre")
                sub_genres = genre_data.get("sub_genres", [])
            else:
                primary_genre = str(genre_data)
                sub_genres = []

            if primary_genre and primary_genre != "Unknown":
                summary.classified_tracks += 1
                add_to_genre_groups(primary_genre, t.id, is_sub=False)
                for sub in sub_genres:
                    if sub and str(sub).strip():
                        add_to_genre_groups(str(sub).strip(), t.id, is_sub=True)
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
                primary_genre = result.get("primary_genre") or result.get("genre")
                sub_genres = result.get("sub_genres") or []
                key = get_track_identity_key(track)
                artist_name = getattr(track.artist, "name", "") if getattr(track, "artist", None) else ""
                title_str = getattr(track, "title", "")
                
                if not primary_genre or primary_genre.strip().lower() in ("unknown", ""):
                    unknown_track_ids.append(track.id)
                    summary.unknown_tracks += 1
                    records_to_save.append({
                        "track_id": key,
                        "artist": artist_name,
                        "title": title_str,
                        "primary_genre": "Unknown",
                        "sub_genres": [],
                        "status": "UNKNOWN",
                    })
                else:
                    summary.classified_tracks += 1
                    genre_key = primary_genre.strip()
                    add_to_genre_groups(genre_key, track.id, is_sub=False)
                    clean_subs = []
                    for sub in sub_genres:
                        if sub and str(sub).strip():
                            s_clean = str(sub).strip()
                            clean_subs.append(s_clean)
                            add_to_genre_groups(s_clean, track.id, is_sub=True)

                    records_to_save.append({
                        "track_id": key,
                        "artist": artist_name,
                        "title": title_str,
                        "primary_genre": genre_key,
                        "sub_genres": clean_subs,
                        "status": "CLASSIFIED",
                    })

        cache_service.save_track_genres(records_to_save)

    # Thresholding: Standalone playlists are created ONLY for genres and sub-genres with >= min_genre_size tracks.
    # Tracks whose primary genre has < min_genre_size tracks are routed to "Others".
    # Sub-genres with < min_genre_size tracks are suppressed from standalone playlist creation.
    final_genre_groups = {}
    for norm_key, track_ids in genre_groups_norm.items():
        canonical_name = norm_to_canonical[norm_key]
        if len(track_ids) >= min_genre_size:
            final_genre_groups[canonical_name] = track_ids

    others_track_ids = []
    for tid, primary_norm in track_primary_norm.items():
        if primary_norm and len(genre_groups_norm.get(primary_norm, [])) < min_genre_size:
            others_track_ids.append(tid)

    if others_track_ids:
        deduped_others = []
        seen_others = set()
        for tid in others_track_ids:
            if tid not in seen_others:
                seen_others.add(tid)
                deduped_others.append(tid)
        final_genre_groups["Others"] = deduped_others

    if unknown_track_ids:
        deduped_unknown = []
        seen_unknown = set()
        for tid in unknown_track_ids:
            if tid not in seen_unknown:
                seen_unknown.add(tid)
                deduped_unknown.append(tid)
        final_genre_groups["Unknown"] = deduped_unknown

    logging.info(f"Classification complete. Processing playlists in folder '{folder_name}'...")
    
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
