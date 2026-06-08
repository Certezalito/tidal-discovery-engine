import re
with open('src/services/tidal_service.py', 'r') as f:
    data = f.read()

old_func = re.search(r'def create_playlist_in_folder.*?(?=def add_tracks_to_playlist)', data, flags=re.DOTALL)
if old_func:
    # We will manually replace the function body
    pass
