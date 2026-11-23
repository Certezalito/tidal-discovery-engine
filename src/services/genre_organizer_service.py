from dataclasses import dataclass, field
from pydantic import BaseModel
from typing import Any, Optional


@dataclass
class TrackDedupGroup:
    """
    Aggregates all scanned library tracks representing one unique underlying
    recording (by ISRC) or exact catalog track (when ISRC is unavailable).

    Retaining all candidate catalog IDs allows playlist sync to preserve a
    matching release already in a playlist (avoiding release-swap churn) while
    picking a deterministic canonical ID for newly created playlists.
    """

    dedup_key: str
    cache_key: str
    representative_track: Any
    candidate_track_ids: list[str]
    canonical_track_id: str


@dataclass
class PlaylistTrackOccurrence:
    """Represents a single slot inside an existing Tidal playlist."""

    track_id: str
    isrc: str
    item_uuid: Optional[str]
    dedup_key: str


@dataclass
class PlaylistSyncPlan:
    """Minimal, duplicate-free mutations needed to reconcile an existing playlist."""

    to_add_ids: list[str] = field(default_factory=list)
    to_remove_items: list[str] = field(default_factory=list)
    duplicates_removed: int = 0


def _canonical_id_sort_key(track_id: str):
    """
    Deterministic sort key for Tidal catalog track IDs independent of API
    pagination order: numeric IDs sort ascending by integer value first,
    followed by non-numeric IDs lexicographically.
    """
    return (0, int(track_id), track_id) if track_id.isdigit() else (1, 0, track_id)


def _is_valid_item_uuid(value: Any) -> bool:
    """
    Return True when value matches Tidal v2's 36-character hyphenated item UUID
    format recognized by remove_tracks_from_playlist.
    """
    return isinstance(value, str) and "-" in value and len(value) == 36


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
    service_tier: Optional[str] = None
    fallback_triggered: bool = False
    gemini_input_tokens: int = 0
    gemini_thought_tokens: int = 0
    gemini_output_tokens: int = 0
    gemini_total_tokens: int = 0
    gemini_calls: int = 0
    gemini_model: Optional[str] = None
    gemini_est_cost_usd: Optional[float] = 0.0

def _get_tracks_batch(tracks, batch_size=100):
    for i in range(0, len(tracks), batch_size):
        yield tracks[i:i + batch_size]

def calculate_sync_delta(desired_track_ids: list, existing_track_ids: list):
    """
    Returns lists of track IDs to add and track IDs to remove to match desired state.

    Compares IDs using normalized string representations to prevent int/str
    mismatches, deduplicates desired IDs, and includes surplus duplicate
    occurrences already present in existing_track_ids in to_remove.
    """
    # Deduplicate desired IDs while preserving caller order and types
    desired_dedup = []
    desired_str_set = set()
    for d in desired_track_ids:
        d_str = str(d)
        if d_str not in desired_str_set:
            desired_str_set.add(d_str)
            desired_dedup.append(d)

    existing_str_set = {str(e) for e in existing_track_ids}

    # What's in desired but not in existing
    to_add = [tid for tid in desired_dedup if str(tid) not in existing_str_set]

    # Remove tracks not in desired AND any surplus (2nd, 3rd, ...) occurrences of desired tracks
    to_remove = []
    seen_existing_desired = set()
    for tid in existing_track_ids:
        tid_str = str(tid)
        if tid_str not in desired_str_set:
            to_remove.append(tid)
        elif tid_str in seen_existing_desired:
            to_remove.append(tid)
        else:
            seen_existing_desired.add(tid_str)

    return to_add, to_remove


def calculate_playlist_sync_plan(
    desired_groups: list[TrackDedupGroup],
    existing_tracks: list[Any],
) -> PlaylistSyncPlan:
    """
    Reconcile an existing playlist's track occurrences against desired unique
    TrackDedupGroups using recording identity (ISRC) and exact catalog track ID.

    Key guarantees:
    - Preserves the first matching existing occurrence per desired dedup_key so
      alternate catalog releases of the same recording do not churn across runs.
    - Surgically removes surplus duplicate occurrences (2nd, 3rd, ...) using each
      occurrence's Tidal v2 item_uuid so the kept copy remains untouched.
    - Removes every occurrence of obsolete tracks no longer in desired_groups.
    - When a surplus duplicate lacks a valid item_uuid, falls back to removing by
      catalog track ID and re-adding one canonical copy so exactly 1 copy remains.
    """
    from src.services.tidal_service import get_playlist_dedup_key, normalize_isrc

    # Index desired groups by canonical dedup_key and by every qualifying catalog track ID
    desired_by_key: dict[str, TrackDedupGroup] = {}
    candidate_id_to_dedup_key: dict[str, str] = {}
    for group in desired_groups:
        if group.dedup_key not in desired_by_key:
            desired_by_key[group.dedup_key] = group
        for cid in group.candidate_track_ids:
            cid_str = str(cid).strip()
            if cid_str and cid_str not in candidate_id_to_dedup_key:
                candidate_id_to_dedup_key[cid_str] = group.dedup_key

    # Convert existing playlist items into normalized PlaylistTrackOccurrence entries
    occurrences: list[PlaylistTrackOccurrence] = []
    for track in existing_tracks:
        raw_id = getattr(track, "id", None)
        track_id_str = (
            str(raw_id).strip()
            if isinstance(raw_id, (int, str)) and not isinstance(raw_id, bool)
            else ""
        )
        raw_isrc = getattr(track, "isrc", None)
        normalized_isrc = normalize_isrc(raw_isrc) if isinstance(raw_isrc, str) else ""
        raw_uuid = getattr(track, "item_uuid", None)
        item_uuid = raw_uuid if _is_valid_item_uuid(raw_uuid) else None

        # Match against desired groups by ISRC first (handles alternate releases of the
        # same recording), then by catalog ID (handles playlist items missing ISRC or
        # library tracks without ISRC), before falling back to the track's own dedup key.
        if normalized_isrc and f"isrc:{normalized_isrc}" in desired_by_key:
            occ_dedup_key = f"isrc:{normalized_isrc}"
        elif track_id_str and track_id_str in candidate_id_to_dedup_key:
            occ_dedup_key = candidate_id_to_dedup_key[track_id_str]
        else:
            occ_dedup_key = get_playlist_dedup_key(track)

        occurrences.append(
            PlaylistTrackOccurrence(
                track_id=track_id_str,
                isrc=normalized_isrc,
                item_uuid=item_uuid,
                dedup_key=occ_dedup_key,
            )
        )

    satisfied_keys: set[str] = set()
    kept_occurrence_by_key: dict[str, PlaylistTrackOccurrence] = {}
    to_remove_items: list[str] = []
    removed_track_ids_by_id: set[str] = set()
    duplicates_removed = 0

    for occ in occurrences:
        if occ.dedup_key in desired_by_key:
            if occ.dedup_key not in satisfied_keys:
                # Keep the first matching occurrence already in the playlist (zero churn).
                satisfied_keys.add(occ.dedup_key)
                kept_occurrence_by_key[occ.dedup_key] = occ
            else:
                # Surplus duplicate occurrence (same track ID or same ISRC recording).
                duplicates_removed += 1
                if occ.item_uuid is not None:
                    to_remove_items.append(occ.item_uuid)
                elif occ.track_id and occ.track_id not in removed_track_ids_by_id:
                    # Without item_uuid, removal by track_id deletes all copies of that ID.
                    to_remove_items.append(occ.track_id)
                    removed_track_ids_by_id.add(occ.track_id)
        else:
            # Non-qualifying / obsolete track: remove every copy from the playlist.
            if occ.item_uuid is not None:
                to_remove_items.append(occ.item_uuid)
            elif occ.track_id and occ.track_id not in removed_track_ids_by_id:
                to_remove_items.append(occ.track_id)
                removed_track_ids_by_id.add(occ.track_id)

    # If degraded non-UUID removal targeted a track_id that was also kept, mark its
    # dedup_key unsatisfied so one clean canonical copy is re-added after removal.
    for key, kept_occ in kept_occurrence_by_key.items():
        if kept_occ.track_id and kept_occ.track_id in removed_track_ids_by_id:
            satisfied_keys.discard(key)

    to_add_ids: list[str] = []
    seen_add_ids: set[str] = set()
    for dedup_key, group in desired_by_key.items():
        if dedup_key not in satisfied_keys:
            if group.canonical_track_id not in seen_add_ids:
                seen_add_ids.add(group.canonical_track_id)
                to_add_ids.append(group.canonical_track_id)

    return PlaylistSyncPlan(
        to_add_ids=to_add_ids,
        to_remove_items=to_remove_items,
        duplicates_removed=duplicates_removed,
    )

def run_genre_organizer_sync(
    session,
    folder_name: str,
    api_key: Optional[str] = None,
    min_genre_size: int = 5,
    db_path: Optional[str] = None,
    refresh_genres: bool = False,
    wipe_folder: bool = False,
    wipe_only: bool = False,
    flex: Optional[bool] = None,
    flex_fallback_standard: Optional[bool] = None,
) -> GenreRunSummary:
    """
    Orchestrates the full genre organizer sync workflow using SQLite caching.

    Args:
        flex: Optional toggle for Gemini flex tier inference (50% cheaper, variable turnaround).
        flex_fallback_standard: Optional toggle to fallback to standard tier inference if flex
            capacity is unavailable. Once triggered for any batch, subsequent batches within
            this run continue directly on standard tier (sticky fallback per FR-022).
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
        get_playlist_dedup_key,
        is_track_available_in_catalog,
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

    # Aggregate scanned tracks by playlist dedup_key (ISRC when available, exact
    # catalog ID otherwise) BEFORE genre grouping and min-size thresholding so:
    # 1. Duplicate catalog IDs and alternate releases of the same recording count
    #    once toward --min-genre-size (FR-002, FR-004).
    # 2. All candidate catalog IDs are preserved in deterministic sorted order so
    #    new playlists pick a stable ID while existing playlists retain whichever
    #    matching release they already contain without churn (FR-003).
    dedup_buckets: dict[str, dict[str, Any]] = {}
    for t in favorite_tracks:
        dedup_key = get_playlist_dedup_key(t)
        raw_id = getattr(t, "id", None)
        if (
            not dedup_key
            or not isinstance(raw_id, (int, str))
            or isinstance(raw_id, bool)
        ):
            continue
        track_id_str = str(raw_id).strip()
        if not track_id_str:
            continue

        if dedup_key not in dedup_buckets:
            dedup_buckets[dedup_key] = {}
        if track_id_str not in dedup_buckets[dedup_key]:
            dedup_buckets[dedup_key][track_id_str] = t

    dedup_groups: dict[str, TrackDedupGroup] = {}
    for dedup_key, id_to_track in dedup_buckets.items():
        sorted_ids = sorted(id_to_track.keys(), key=_canonical_id_sort_key)
        canonical_id = sorted_ids[0]
        rep_track = id_to_track[canonical_id]
        # Keep existing SQLite cache key format (get_track_identity_key) for backward
        # compatibility with data/genre_cache.db, falling back to dedup_key when both
        # ISRC and title/artist are absent so no track is silently dropped.
        cache_key = get_track_identity_key(rep_track) or dedup_key
        dedup_groups[dedup_key] = TrackDedupGroup(
            dedup_key=dedup_key,
            cache_key=cache_key,
            representative_track=rep_track,
            candidate_track_ids=sorted_ids,
            canonical_track_id=canonical_id,
        )

    unique_cache_keys = list(dict.fromkeys(g.cache_key for g in dedup_groups.values()))
    
    # Query SQLite database cache
    cached_genres, uncached_or_unknown_keys = cache_service.get_cached_genres(
        unique_cache_keys, refresh_genres=refresh_genres
    )
    summary.cache_hits = len(cached_genres)
    summary.cache_misses = len(uncached_or_unknown_keys)
    
    import re
    genre_groups_norm: dict[str, list[str]] = {}
    norm_to_canonical: dict[str, str] = {}
    group_primary_norm: dict[str, str] = {}
    unknown_dedup_keys: list[str] = []
    
    def add_to_genre_groups(raw_genre: str, dedup_key: str, is_sub: bool = False):
        raw_genre = raw_genre.strip()
        norm_key = re.sub(r'[^a-z0-9]', '', raw_genre.lower())
        if not norm_key:
            return
        if not is_sub:
            group_primary_norm[dedup_key] = norm_key
        if norm_key not in genre_groups_norm:
            genre_groups_norm[norm_key] = []
        if dedup_key not in genre_groups_norm[norm_key]:
            genre_groups_norm[norm_key].append(dedup_key)
        
        if norm_key not in norm_to_canonical:
            norm_to_canonical[norm_key] = raw_genre
        else:
            existing = norm_to_canonical[norm_key]
            if "-" in existing and " " in raw_genre:
                norm_to_canonical[norm_key] = raw_genre
            elif raw_genre.istitle() and not existing.istitle() and raw_genre.upper() != raw_genre:
                norm_to_canonical[norm_key] = raw_genre

    # Process cached classified tracks and group uncached tracks by cache_key so
    # Gemini is never queried twice for identical fallback cache keys.
    uncached_keys_set = set(uncached_or_unknown_keys)
    uncached_by_cache_key: dict[str, list[TrackDedupGroup]] = {}
    for group in dedup_groups.values():
        if group.cache_key in cached_genres:
            genre_data = cached_genres[group.cache_key]
            if isinstance(genre_data, dict):
                primary_genre = genre_data.get("primary_genre")
                sub_genres = genre_data.get("sub_genres", [])
            else:
                primary_genre = str(genre_data)
                sub_genres = []

            if primary_genre and primary_genre != "Unknown":
                summary.classified_tracks += 1
                add_to_genre_groups(primary_genre, group.dedup_key, is_sub=False)
                for sub in sub_genres:
                    if sub and str(sub).strip():
                        add_to_genre_groups(str(sub).strip(), group.dedup_key, is_sub=True)
        elif group.cache_key in uncached_keys_set:
            uncached_by_cache_key.setdefault(group.cache_key, []).append(group)

    uncached_cache_buckets = list(uncached_by_cache_key.items())
    if uncached_cache_buckets:
        logging.info(f"{len(uncached_cache_buckets)} tracks not cached or UNKNOWN. Querying Gemini...")
        records_to_save = []
        active_flex = flex
        from src.services.gemini_service import (
            _resolve_service_tier,
            get_token_usage,
            reset_token_usage,
        )
        initial_tier, _, _ = _resolve_service_tier(flex)
        reset_token_usage()

        def on_batch_fallback():
            nonlocal active_flex
            summary.fallback_triggered = True
            if active_flex is not False:
                logging.warning(
                    "Gemini flex capacity exhausted for batch. Sticky fallback active: subsequent batches in this run will execute directly on standard tier."
                )
                active_flex = False

        for batch in _get_tracks_batch(uncached_cache_buckets, batch_size=50):
            batch_inputs = []
            for _cache_key, bucket_groups in batch:
                t = bucket_groups[0].representative_track
                batch_inputs.append({
                    "artist": getattr(t.artist, "name", "") if getattr(t, "artist", None) else "",
                    "title": getattr(t, "title", ""),
                    "isrc": getattr(t, "isrc", "")
                })
                
            # Forward flex tier and fallback setting to Gemini batch classification (Principle VI, FR-022)
            results = classify_tracks_genres(
                api_key,
                batch_inputs,
                flex=active_flex,
                flex_fallback_standard=flex_fallback_standard,
                on_fallback=on_batch_fallback,
            )
            
            batch_records = []
            for (cache_key, bucket_groups), result in zip(batch, results):
                primary_genre = result.get("primary_genre") or result.get("genre")
                sub_genres = result.get("sub_genres") or []
                rep_track = bucket_groups[0].representative_track
                artist_name = getattr(rep_track.artist, "name", "") if getattr(rep_track, "artist", None) else ""
                title_str = getattr(rep_track, "title", "")
                
                if not primary_genre or primary_genre.strip().lower() in ("unknown", ""):
                    for g in bucket_groups:
                        unknown_dedup_keys.append(g.dedup_key)
                        summary.unknown_tracks += 1
                    rec = {
                        "track_id": cache_key,
                        "artist": artist_name,
                        "title": title_str,
                        "primary_genre": "Unknown",
                        "sub_genres": [],
                        "status": "UNKNOWN",
                    }
                    records_to_save.append(rec)
                    batch_records.append(rec)
                else:
                    genre_key = primary_genre.strip()
                    clean_subs = [str(sub).strip() for sub in sub_genres if sub and str(sub).strip()]
                    for g in bucket_groups:
                        summary.classified_tracks += 1
                        add_to_genre_groups(genre_key, g.dedup_key, is_sub=False)
                        for s_clean in clean_subs:
                            add_to_genre_groups(s_clean, g.dedup_key, is_sub=True)

                    rec = {
                        "track_id": cache_key,
                        "artist": artist_name,
                        "title": title_str,
                        "primary_genre": genre_key,
                        "sub_genres": clean_subs,
                        "status": "CLASSIFIED",
                    }
                    records_to_save.append(rec)
                    batch_records.append(rec)

            # Persist batch immediately to local SQLite cache (Principle VII)
            if batch_records:
                cache_service.save_track_genres(batch_records)

        if summary.fallback_triggered:
            summary.service_tier = "standard"
        elif active_flex is False or initial_tier == "standard":
            summary.service_tier = "standard"
        else:
            summary.service_tier = "flex"

        # Snapshot cumulative Gemini token usage across all classification batches in this run.
        token_usage = get_token_usage()
        summary.gemini_input_tokens = token_usage.get("input_tokens", 0)
        summary.gemini_thought_tokens = token_usage.get("thought_tokens", 0)
        summary.gemini_output_tokens = token_usage.get("output_tokens", 0)
        summary.gemini_total_tokens = token_usage.get("total_tokens", 0)
        summary.gemini_calls = token_usage.get("calls", 0)
        summary.gemini_model = token_usage.get("model")
        summary.gemini_est_cost_usd = token_usage.get("est_cost_usd")

    # Thresholding: Standalone playlists are created ONLY for genres and sub-genres with
    # >= min_genre_size UNIQUE deduplicated tracks (FR-004).
    # Tracks whose primary genre has < min_genre_size unique tracks are routed to "Others".
    # Sub-genres with < min_genre_size unique tracks are suppressed from standalone creation.
    final_genre_groups: dict[str, list[TrackDedupGroup]] = {}
    for norm_key, group_keys in genre_groups_norm.items():
        canonical_name = norm_to_canonical[norm_key]
        if len(group_keys) >= min_genre_size:
            final_genre_groups[canonical_name] = [dedup_groups[dk] for dk in group_keys]

    others_dedup_keys = []
    for dk, primary_norm in group_primary_norm.items():
        if primary_norm and len(genre_groups_norm.get(primary_norm, [])) < min_genre_size:
            others_dedup_keys.append(dk)

    if others_dedup_keys:
        deduped_others = list(dict.fromkeys(others_dedup_keys))
        final_genre_groups["Others"] = [dedup_groups[dk] for dk in deduped_others]

    if unknown_dedup_keys:
        deduped_unknown = list(dict.fromkeys(unknown_dedup_keys))
        final_genre_groups["Unknown"] = [dedup_groups[dk] for dk in deduped_unknown]

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
    # Per-run cache of live Tidal track availability checks so each candidate ID is
    # verified at most once across all playlists before adding to an existing playlist.
    track_availability_cache: dict[str, bool] = {}
    
    for genre_name, desired_groups in sorted_genre_groups:
        desired_track_ids = [g.canonical_track_id for g in desired_groups]
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
                
            sync_plan = calculate_playlist_sync_plan(desired_groups, existing_tracks)
            # Filter out delisted/unavailable track IDs before calling items/add so Tidal
            # cannot silently remap them onto an existing catalog track and create duplicates.
            filtered_to_add_ids = [
                tid
                for tid in sync_plan.to_add_ids
                if is_track_available_in_catalog(session, tid, cache=track_availability_cache)
            ]
            
            if filtered_to_add_ids or sync_plan.to_remove_items:
                success = sync_playlist_tracks(
                    session,
                    playlist.id,
                    to_add_ids=filtered_to_add_ids,
                    to_remove_ids=sync_plan.to_remove_items,
                )
                if success:
                    summary.playlists_updated += 1
                    summary.tracks_added += len(filtered_to_add_ids)
                    summary.tracks_removed += len(sync_plan.to_remove_items)
                    if sync_plan.duplicates_removed > 0:
                        logging.info(
                            f"Synced playlist '{playlist.name}': +{len(filtered_to_add_ids)} "
                            f"-{len(sync_plan.to_remove_items)} tracks "
                            f"(removed {sync_plan.duplicates_removed} duplicates)."
                        )
                    else:
                        logging.info(
                            f"Synced playlist '{playlist.name}': +{len(filtered_to_add_ids)} "
                            f"-{len(sync_plan.to_remove_items)} tracks."
                        )
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
