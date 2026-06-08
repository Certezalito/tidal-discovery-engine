with open('src/services/tidal_service.py', 'r') as f:
    data = f.read()

data = data.replace('''        # tidalapi Playlist.tracks() returns the full list
        return playlist.tracks()''', '''        return playlist.tracks_paginated()''')

with open('src/services/tidal_service.py', 'w') as f:
    f.write(data)
