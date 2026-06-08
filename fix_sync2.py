with open('src/services/tidal_service.py', 'r') as f:
    data = f.read()
    
data = data.replace('''def sync_playlist_tracks(session, playlist_id, to_add_ids, to_remove_ids):
    """
    Adds and removes tracks from an existing playlist.
    """
    try:
        playlist = tidalapi.playlist.UserPlaylist(session, playlist_id)
        if to_remove_ids:
            playlist.delete_by_id([str(x) for x in to_remove_ids])
        if to_add_ids:
            playlist.add([str(x) for x in to_add_ids])
    except Exception as e:
        logging.error(f"Failed to sync playlist {playlist_id}: {e}")
        raise''', '''def sync_playlist_tracks(session, playlist_id, to_add_ids, to_remove_ids):
    """
    Adds and removes tracks from an existing playlist.
    """
    try:
        playlist = tidalapi.playlist.UserPlaylist(session, playlist_id)
        if to_remove_ids:
            # chunk by 50 to avoid 412/405 errors
            for i in range(0, len(to_remove_ids), 50):
                playlist.delete_by_id([str(x) for x in to_remove_ids[i:i+50]])
        if to_add_ids:
            # chunk by 50
            for i in range(0, len(to_add_ids), 50):
                playlist.add([str(x) for x in to_add_ids[i:i+50]])
    except Exception as e:
        logging.error(f"Failed to sync playlist {playlist_id}: {e}")
        raise''')
        
with open('src/services/tidal_service.py', 'w') as f:
    f.write(data)
