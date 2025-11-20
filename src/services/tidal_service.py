import os
import json
import random
import tidalapi
import click
import datetime

SESSION_FILE = "tidal_session.json"

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
        
        click.echo(f"\n--- Tidal Authentication Successful ---")
        click.echo(f"Session details have been saved to `{SESSION_FILE}` for future non-interactive use.")
        click.echo("-------------------------------------\n")
        
    return session

def get_random_favorite_tracks(session, num_tracks):
    favorites = session.user.favorites.tracks()
    return random.sample(favorites, num_tracks)

def create_playlist(session, name, num_tidal_tracks, num_similar_tracks, seed_tracks, final_tags):
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

    description = (
        f"Generated on {run_date}. "
        f"Based on {num_tidal_tracks} seed tracks: {seed_track_list}. "
        f"Found {num_similar_tracks} similar tracks for each via Last.fm."
        f"{genre_mix_summary}"
    )

    # Truncate the description if it's too long
    if len(description) > 500:
        description = description[:497] + "..."
        
    return session.user.create_playlist(name, description)

def search_for_track(session, track):
    query = f"{track.artist.name} - {track.title}"
    results = session.search(query, models=[tidalapi.Track])
    if results['tracks']:
        return results['tracks'][0]
    return None

def add_tracks_to_playlist(playlist, tracks):
    playlist.add([track.id for track in tracks])
