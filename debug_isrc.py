import tidalapi
import json
import os
import datetime

SESSION_FILE = "tidal_session.json"

def get_session():
    session = tidalapi.Session()
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            config = json.load(f)
        session.load_oauth_session(
            config['token_type'],
            config['access_token'],
            config['refresh_token'],
            datetime.datetime.fromisoformat(config['expiry_time'])
        )
    return session

session = get_session()

# Validating flow
print("\n--- Validating Lookup Flow ---")
tracks = session.user.favorites.tracks(limit=1)
if tracks:
    t = tracks[0]
    print(f"Seed Track: {t.name} (ISRC: {t.isrc})")
    
    try:
        lookup_tracks = session.get_tracks_by_isrc(t.isrc)
        print(f"Lookup Result: Found {len(lookup_tracks)}")
    except Exception as e:
        print(f"Lookup Failed: {e}")
else:
    print("No favorites found to test.")



