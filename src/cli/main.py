import click
import logging
import datetime
import random
from src.lib.logging import setup_logging
from src.services import tidal_service, lastfm_service

@click.command()
@click.option("--num-tidal-tracks", default=10, help="The number of random favorite tracks to select from Tidal.")
@click.option("--num-similar-tracks", default=5, help="The number of similar tracks to retrieve from Last.fm for each Tidal track.")
@click.option("--shuffle", is_flag=True, help="Shuffle the similar tracks before adding them to the playlist.")
@click.option("--playlist-name", required=True, help="The name for the new Tidal playlist. Use {date} for dynamic date.")
@click.option("--artist", help="The artist of a specific track to use as a seed.")
@click.option("--track", help="The title of a specific track to use as a seed.")
@click.option("--folder", help="Optional folder name to organize the playlist.")
def main(num_tidal_tracks, num_similar_tracks, shuffle, playlist_name, artist, track, folder):
    """
    Generates a new Tidal playlist with recommended tracks based on a selection of your favorite tracks.
    """
    setup_logging()
    logging.info("Starting playlist generation...")

    if "{date}" in playlist_name:
        run_date = datetime.date.today().strftime("%Y%m%d")
        playlist_name = playlist_name.replace("{date}", run_date)

    try:
        tidal_session = tidal_service.get_session()
        lastfm_network = lastfm_service.get_network()

        # Step 1: Build the list of seed tracks first
        seed_tracks = []
        if artist and track:
            logging.info(f"Using single seed track: {track} by {artist}")
            seed_tracks.append(lastfm_network.get_track(artist, track))
            num_tidal_tracks = 1  # Override for description
        else:
            favorite_tracks = tidal_service.get_random_favorite_tracks(tidal_session, num_tidal_tracks)
            logging.info(f"Selected {len(favorite_tracks)} favorite tracks from Tidal to use as seeds:")
            for t in favorite_tracks:
                logging.info(f"  - {t.name} by {t.artist.name}")
            seed_tracks = [lastfm_network.get_track(t.artist.name, t.name) for t in favorite_tracks]

        # Step 2: Process each seed track to get artist tags and similar tracks
        similar_tracks = []
        no_similar_tracks_seeds = []
        final_playlist_tags = []
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

        tidal_tracks_to_add = []
        for t in similar_tracks:
            tidal_track = tidal_service.search_for_track(tidal_session, t)
            if tidal_track:
                tidal_tracks_to_add.append(tidal_track)
        logging.info(f"Found {len(tidal_tracks_to_add)} tracks on Tidal to add to the playlist.")

        if not tidal_tracks_to_add:
            logging.warning("No tracks to add to the playlist. Exiting.")
            return

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

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
