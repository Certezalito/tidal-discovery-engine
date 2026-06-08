with open('src/services/tidal_service.py', 'r') as f:
    data = f.read()

data = data.replace('''        if to_remove_ids:
            for track_id in to_remove_ids:
                playlist.remove_by_id(track_id)''', '''        if to_remove_ids:
            playlist.delete_by_id(to_remove_ids)''')

with open('src/services/tidal_service.py', 'w') as f:
    f.write(data)
