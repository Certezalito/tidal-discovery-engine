import os
import click
import logging
import datetime
import random
from src.lib.logging import setup_logging, log_cli_warning, log_cli_error, bounded_name_preview
from src.services import tidal_service, lastfm_service, gemini_service
from src.services.gemini_service import GeminiModelUnavailableError

@click.command()
@click.option("--gemini", is_flag=True, help="Use Google Gemini AI for recommendations instead of Last.fm.")
@click.option("--num-tidal-tracks", default=10, help="The number of random favorite tracks to select from Tidal.")
@click.option("--num-similar-tracks", default=5, type=int, help="The number of similar tracks to retrieve from Last.fm for each Tidal track.")
@click.option("--shuffle", is_flag=True, help="Shuffle the similar tracks before adding them to the playlist.")
@click.option("--playlist-name", required=True, help="The name for the new Tidal playlist. Use {date} for dynamic date.")
@click.option("--artist", help="The artist of a specific track to use as a seed.")
@click.option("--track", help="The title of a specific track to use as a seed.")
@click.option("--folder", help="Optional folder name to organize the playlist.")
def main(gemini, num_tidal_tracks, num_similar_tracks, shuffle, playlist_name, artist, track, folder):
    """
    Generates a new Tidal playlist with recommended tracks based on a selection of your favorite tracks.
    """
    setup_logging()
    logging.info("Starting playlist generation...")

    if (artist and not track) or (track and not artist):
        raise click.ClickException("Both --artist and --track are required together for single-seed mode.")

    if num_similar_tracks <= 0:
        raise click.ClickException("--num-similar-tracks must be a positive integer.")

    # Validate Gemini Requirement
    if gemini:
        if "GEMINI_API_KEY" not in os.environ:
            raise click.ClickException("--gemini flag requires GEMINI_API_KEY environment variable.")

    if "{date}" in playlist_name:
        run_date = datetime.date.today().strftime("%Y%m%d")
        playlist_name = playlist_name.replace("{date}", run_date)

    try:
        tidal_session = tidal_service.get_session()
        lastfm_network = lastfm_service.get_network()

        # Step 1: Build the list of seed tracks first
        seed_tracks = []
        mode3 = bool(artist and track)
        if artist and track:
            logging.info(f"Using single seed track: {track} by {artist}")
            num_tidal_tracks = 1  # Override for description
            if gemini:
                seed_track, seed_resolution = tidal_service.resolve_text_seed_track(
                    tidal_session,
                    artist,
                    track,
                )
                seed_tracks.append(seed_track)

                if seed_resolution == "ambiguous":
                    log_cli_warning(
                        "MODE3_SEED_AMBIGUOUS",
                        "Single-seed input did not match uniquely; using best available Tidal candidate for Gemini context.",
                        artist=artist,
                        track=track,
                    )
                elif seed_resolution == "text_only":
                    log_cli_warning(
                        "MODE3_SEED_NOT_FOUND",
                        "Single-seed input was not found in Tidal search; using text-only seed context for Gemini.",
                        artist=artist,
                        track=track,
                    )
            else:
                seed_tracks.append(lastfm_network.get_track(artist, track))
        else:
            favorite_tracks = tidal_service.get_random_favorite_tracks(tidal_session, num_tidal_tracks)
            logging.info(f"Selected {len(favorite_tracks)} favorite tracks from Tidal to use as seeds:")
            for t in favorite_tracks:
                logging.info(f"  - {t.name} by {t.artist.name}")
            seed_tracks = [lastfm_network.get_track(t.artist.name, t.name) for t in favorite_tracks]

        tidal_tracks_to_add = []
        no_similar_tracks_seeds = []
        use_gemini = gemini

        if use_gemini:
            # --- GEMINI RECOMMENDATION PATH ---
            logging.info("Branch: Using Gemini AI for recommendations.")

            # Calculate total tracks needed
            total_count = len(seed_tracks) * num_similar_tracks
            unresolved_recommendations = []

            try:
                recommendations = gemini_service.get_recommendations(
                    api_key=os.environ["GEMINI_API_KEY"],
                    seed_tracks=seed_tracks,
                    count=total_count,
                    shuffle=shuffle,
                )
            except GeminiModelUnavailableError as model_error:
                if mode3:
                    log_cli_warning(
                        "MODE3_GEMINI_FALLBACK",
                        "Configured Gemini model unavailable in single-seed mode; falling back to Last.fm recommendations.",
                        reason="model_unavailable",
                    )
                    logging.warning(str(model_error))
                    use_gemini = False
                    recommendations = []
                else:
                    raise

            if use_gemini:
                logging.info(f"Gemini returned {len(recommendations)} suggestions. Resolving tracks...")

                for item in recommendations:
                    try:
                        artist_name = item.get("artist")
                        track_title = item.get("title")
                        isrc = item.get("isrc")

                        if not artist_name or not track_title:
                            unresolved_recommendations.append("unknown-artist - unknown-track")
                            continue

                        found_track = None

                        # Try ISRC first when available, then fallback to search.
                        if isrc:
                            found_track = tidal_service.get_track_by_isrc(tidal_session, isrc)
                            if found_track:
                                logging.info(f"  + Resolved via ISRC ({isrc}): {found_track.name} by {found_track.artist.name}")

                        if not found_track:
                            if isrc:
                                logging.warning(
                                    f"  - ISRC Lookup Failed ({isrc}). Falling back to search for: '{track_title}' by '{artist_name}'"
                                )

                            class SearchQuery:
                                def __init__(self, a, t):
                                    self.artist = type("obj", (object,), {"name": a})
                                    self.title = t

                            search_query = SearchQuery(artist_name, track_title)
                            found_track = tidal_service.search_for_track(tidal_session, search_query)

                        if found_track:
                            tidal_tracks_to_add.append(found_track)
                        else:
                            unresolved_recommendations.append(f"{artist_name} - {track_title}")

                    except Exception as e:
                        unresolved_recommendations.append(str(item))
                        logging.error(f"Error processing item {item}: {e}")

                if unresolved_recommendations:
                    preview = bounded_name_preview(unresolved_recommendations, max_items=5)
                    log_cli_warning(
                        "MODE3_UNRESOLVED_TRACKS",
                        "One or more Gemini recommendations could not be matched on Tidal and were skipped.",
                        skipped_count=len(unresolved_recommendations),
                        preview="; ".join(preview),
                    )

        if not use_gemini:
            # --- STANDARD LAST.FM PATH ---
            # Step 2: Process each seed track to get artist tags and similar tracks
            similar_tracks = []
            # no_similar_tracks_seeds initialized above
            final_playlist_tags = [] # Only used locally here, overwritten later
            
            logging.info("Fetching artist tags and similar tracks for seeds:")
            for t in seed_tracks:
                try:
                    # Get similar tracks
                    found_tracks = lastfm_service.get_similar_tracks(lastfm_network, t, 1000 if shuffle else num_similar_tracks)

                    # Get and log top tags for the artist
                    tags = lastfm_service.get_top_tags_for_artist(lastfm_network, t.artist.name)
                    tag_log = f"(Artist Tags: {', '.join(tags)})" if tags else "(Artist Tags: None found)"
                    logging.info(f"  - Processing: {t.title} by {t.artist.name} {tag_log}")

                    if not found_tracks:
                        no_similar_tracks_seeds.append(t)
                    else:
                        if tags:
                            final_playlist_tags.extend(tags)
                        similar_tracks.extend(found_tracks)
                except Exception as e:
                    logging.warning(f"Could not process track '{t.title}': {e}")
            
            if shuffle:
                random.shuffle(similar_tracks)
                total_tracks_to_get = num_similar_tracks * len(seed_tracks)
                similar_tracks = similar_tracks[:total_tracks_to_get]

            logging.info(f"Found {len(similar_tracks)} similar tracks on Last.fm.")

            # tidal_tracks_to_add initialized above
            for t in similar_tracks:
                tidal_track = tidal_service.search_for_track(tidal_session, t)
                if tidal_track:
                    tidal_tracks_to_add.append(tidal_track)
                    
        logging.info(f"Found {len(tidal_tracks_to_add)} tracks on Tidal to add to the playlist.")

        if not tidal_tracks_to_add:
            message = "No tracks could be inserted into the playlist after recommendation resolution."
            log_cli_error("ZERO_TRACKS_INSERTED", message, mode="mode3" if mode3 else "default")
            raise click.ClickException(message)

        # Step 4: Get artist tags for the final playlist tracks
        final_playlist_tags = []
        logging.info("Fetching artist tags for tracks in the new playlist:")
        for t in tidal_tracks_to_add:
            try:
                tags = lastfm_service.get_top_tags_for_artist(lastfm_network, t.artist.name)
                final_playlist_tags.extend(tags)
            except Exception as e:
                logging.warning(f"Could not get tags for artist {t.artist.name}: {e}")

        folder_id = None
        if folder:
            try:
                folder_obj = tidal_service.get_or_create_folder(tidal_session, folder)
                folder_id = folder_obj.id
                logging.info(f"Target folder: {folder_obj.name} (ID: {folder_obj.id})")
            except Exception as e:
                logging.error(f"Failed to process folder '{folder}': {e}. Proceeding without folder.")

        playlist = tidal_service.create_playlist(
            tidal_session, playlist_name, num_tidal_tracks, num_similar_tracks, seed_tracks, final_playlist_tags, no_similar_tracks_seeds, folder_id=folder_id, tracks=tidal_tracks_to_add
        )

        if not playlist or not playlist.id:
            logging.error("Failed to create playlist. The API did not return a valid playlist object.")
            return

        logging.info(f"Playlist '{playlist.name}' created with ID: {playlist.id}")
        logging.info(f"Successfully added {len(tidal_tracks_to_add)} tracks to the playlist.")

        playlist_url = f"https://tidal.com/browse/playlist/{playlist.id}"
        logging.info(f"Playlist available at: {playlist_url}")
        click.echo(f"\nPlaylist '{playlist_name}' created successfully!")
        click.echo(f"View it here: {playlist_url}")

    except click.ClickException:
        raise
    except Exception as e:
        log_cli_error("PLAYLIST_GENERATION_FAILED", "Unhandled error during playlist generation.", details=str(e))
        raise click.ClickException(str(e))

if __name__ == "__main__":
    main()
