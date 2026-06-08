with open('src/services/tidal_service.py', 'r') as f:
    data = f.read()

data = data.replace('''        if to_remove_ids:
            playlist.delete_by_id(to_remove_ids)
        if to_add_ids:
            playlist.add(to_add_ids)''', '''        if to_remove_ids:
            playlist.delete_by_id([str(x) for x in to_remove_ids])
        if to_add_ids:
            playlist.add([str(x) for x in to_add_ids])''')

with open('src/services/tidal_service.py', 'w') as f:
    f.write(data)
